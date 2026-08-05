package com.aibuild.bridge;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonToken;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.MissingNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.InvalidPathException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * set_blocks_from_file: a bridge-local tool with no HTTP endpoint of its own
 * (docs/specs/bridge-http-api.md). Reads a block file - a JSON block list or a
 * Sponge .schem - and streams entries to the mod as set_blocks batches of at
 * most 4096 entries, waiting for each job to finish before sending the next.
 * Returns placed/failed totals plus the first few failure examples.
 *
 * JSON files are parsed twice with the streaming API (validate fully, then
 * send) so a corrupt file never triggers a partial placement and memory stays
 * bounded for 100k+ entry files.
 */
final class BlocksFilePlacer {

    private static final int BATCH_SIZE = Tools.SET_BLOCKS_MAX_ENTRIES;
    private static final long JOB_POLL_INTERVAL_MS = 200;
    private static final long JOB_DEADLINE_MS = 120_000;
    private static final int MAX_EXAMPLES = 3;
    /** Loose shape check for palette strings: namespaced id with optional [state] properties. */
    private static final Pattern BLOCK_STATE_ID = Pattern.compile(
            "[a-z0-9_.-]+:[a-z0-9_/.-]+(\\[[a-z0-9_]+=[a-z0-9_]+(,[a-z0-9_]+=[a-z0-9_]+)*])?");

    private final McBackendClient backend;
    private final ObjectMapper mapper = new ObjectMapper();

    BlocksFilePlacer(McBackendClient backend) {
        this.backend = backend;
    }

    /** Runs the tool; never throws - bad input and IO failures become isError text results. */
    ObjectNode call(JsonNode args) {
        String pathArg = args.path("path").asText("").strip();
        if (pathArg.isEmpty()) {
            return text("set_blocks_from_file needs a non-empty \"path\" argument.", true);
        }
        Path path;
        try {
            // Path fence (B9): the bridge runs with the session work dir as cwd and
            // every legit block file lives there — resolve against cwd and refuse
            // escapes. Bare Path.of allowed absolute/.. reads of arbitrary files.
            // Tests override the fence root via -Daibuild.bridge.fileRoot=<dir>.
            Path root = java.util.Optional.ofNullable(System.getProperty("aibuild.bridge.fileRoot"))
                    .map(Path::of).orElse(Path.of("")).toAbsolutePath().normalize();
            path = root.resolve(pathArg).normalize();
            if (!path.startsWith(root)) {
                return text("path must stay inside the session working directory", true);
            }
        } catch (InvalidPathException e) {
            return text("Invalid path \"" + pathArg + "\": " + e.getMessage(), true);
        }
        if (!Files.isRegularFile(path)) {
            return text("File not found: " + path.toAbsolutePath(), true);
        }
        int[] explicitOffset = null;
        JsonNode offsetNode = args.get("offset");
        if (offsetNode != null && !offsetNode.isNull()) {
            if (!offsetNode.isArray() || offsetNode.size() != 3
                    || !offsetNode.get(0).isInt() || !offsetNode.get(1).isInt()
                    || !offsetNode.get(2).isInt()) {
                return text("\"offset\" must be an array of exactly 3 integers [x,y,z].", true);
            }
            explicitOffset = new int[]{offsetNode.get(0).asInt(), offsetNode.get(1).asInt(),
                    offsetNode.get(2).asInt()};
        }
        boolean placeAir = args.path("place_air").asBoolean(false);
        try {
            Stats stats = path.getFileName().toString().toLowerCase(Locale.ROOT).endsWith(".schem")
                    ? placeFromSchem(path, explicitOffset, placeAir)
                    : placeFromJson(path);
            return text(stats.render(), stats.allFailed());
        } catch (IOException e) {
            return text("Failed to process " + pathArg + ": " + e.getMessage(), true);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return text("Interrupted while placing " + pathArg, true);
        }
    }

    // ----- JSON mode -----

    private Stats placeFromJson(Path path) throws IOException, InterruptedException {
        // Pass 1: validate the whole file parses, so a corrupt file sends nothing.
        try (JsonParser parser = mapper.getFactory().createParser(path.toFile())) {
            streamJsonEntries(parser, new NoOpSink());
        } catch (IOException e) {
            throw new IOException("invalid JSON: " + e.getMessage(), e);
        }
        // Pass 2: stream entries into batches.
        Stats stats = new Stats(path.getFileName() + " (JSON block list)");
        BatchSender sender = new BatchSender(stats);
        try (JsonParser parser = mapper.getFactory().createParser(path.toFile())) {
            streamJsonEntries(parser, sender);
        }
        sender.flush();
        return stats;
    }

    /** Accepts either {"blocks":[...]} (extra fields ignored) or a bare [...] array. */
    private void streamJsonEntries(JsonParser parser, EntrySink sink)
            throws IOException, InterruptedException {
        JsonToken first = parser.nextToken();
        if (first == JsonToken.START_ARRAY) {
            streamEntryArray(parser, sink);
            return;
        }
        if (first != JsonToken.START_OBJECT) {
            throw new IOException("expected {\"blocks\":[...]} object or [...] array at top level");
        }
        boolean foundBlocks = false;
        JsonToken token;
        while ((token = parser.nextToken()) != JsonToken.END_OBJECT) {
            if (token == null) {
                throw new IOException("unexpected end of file inside top-level object");
            }
            String field = parser.currentName();
            JsonToken value = parser.nextToken();
            if ("blocks".equals(field) && value == JsonToken.START_ARRAY) {
                foundBlocks = true;
                streamEntryArray(parser, sink);
            } else if (value != null) {
                parser.skipChildren(); // no-op for scalars
            }
        }
        if (!foundBlocks) {
            throw new IOException("JSON object has no \"blocks\" array");
        }
    }

    private void streamEntryArray(JsonParser parser, EntrySink sink)
            throws IOException, InterruptedException {
        JsonToken token;
        while ((token = parser.nextToken()) != JsonToken.END_ARRAY) {
            if (token == null) {
                throw new IOException("unexpected end of file inside blocks array");
            }
            if (token != JsonToken.START_OBJECT) {
                sink.invalid("array item is not an object");
                parser.skipChildren();
                continue;
            }
            Integer x = null;
            Integer y = null;
            Integer z = null;
            String block = null;
            while ((token = parser.nextToken()) != JsonToken.END_OBJECT) {
                if (token == null) {
                    throw new IOException("unexpected end of file inside block entry");
                }
                String field = parser.currentName();
                parser.nextToken(); // move to the value
                switch (field) {
                    case "x" -> x = readInt(parser);
                    case "y" -> y = readInt(parser);
                    case "z" -> z = readInt(parser);
                    case "block" -> block = readString(parser);
                    default -> parser.skipChildren();
                }
            }
            if (x == null || y == null || z == null || block == null || block.isBlank()) {
                sink.invalid("entry with missing/invalid x,y,z,block");
            } else {
                sink.entry(x, y, z, block);
            }
        }
    }

    private static Integer readInt(JsonParser parser) throws IOException {
        if (parser.currentToken() == JsonToken.VALUE_NUMBER_INT) {
            return parser.getIntValue();
        }
        parser.skipChildren();
        return null;
    }

    private static String readString(JsonParser parser) throws IOException {
        if (parser.currentToken() == JsonToken.VALUE_STRING) {
            return parser.getText();
        }
        parser.skipChildren();
        return null;
    }

    // ----- .schem mode -----

    private Stats placeFromSchem(Path path, int[] explicitOffset, boolean placeAir)
            throws IOException, InterruptedException {
        SchematicParser.Schematic schem = SchematicParser.parse(Files.readAllBytes(path));
        int[] offset = explicitOffset != null ? explicitOffset : schem.offset();
        Stats stats = new Stats(path.getFileName() + " (Sponge Schematic v" + schem.version() + ", "
                + schem.width() + "x" + schem.height() + "x" + schem.length()
                + ", dataVersion " + schem.dataVersion()
                + ", origin offset " + Arrays.toString(offset) + ")");
        stats.skippedBlockEntities = schem.blockEntityCount();

        String[] palette = schem.paletteByIndex();
        boolean[] badPalette = new boolean[palette.length];
        for (int i = 0; i < palette.length; i++) {
            badPalette[i] = palette[i] == null || !BLOCK_STATE_ID.matcher(palette[i]).matches();
            if (badPalette[i]) {
                stats.example("palette index " + i + " unusable: "
                        + (palette[i] == null ? "(no block state defined)" : palette[i]));
            }
        }

        BatchSender sender = new BatchSender(stats);
        for (int y = 0; y < schem.height(); y++) {
            for (int z = 0; z < schem.length(); z++) {
                for (int x = 0; x < schem.width(); x++) {
                    int idx = schem.indexAt(x, y, z);
                    if (idx < 0 || idx >= palette.length || badPalette[idx]) {
                        stats.invalid++;
                        continue;
                    }
                    String block = palette[idx];
                    if (!placeAir && isAir(block)) {
                        stats.skippedAir++;
                        continue;
                    }
                    sender.entry(offset[0] + x, offset[1] + y, offset[2] + z, block);
                }
            }
        }
        sender.flush();
        return stats;
    }

    private static boolean isAir(String block) {
        return "minecraft:air".equals(block) || "minecraft:cave_air".equals(block)
                || "minecraft:void_air".equals(block);
    }

    // ----- batching, job polling, result aggregation -----

    private interface EntrySink {
        void entry(int x, int y, int z, String block) throws IOException, InterruptedException;

        void invalid(String reason);
    }

    private static final class NoOpSink implements EntrySink {
        @Override
        public void entry(int x, int y, int z, String block) {
        }

        @Override
        public void invalid(String reason) {
        }
    }

    private final class BatchSender implements EntrySink {
        private final Stats stats;
        private ArrayNode batch = mapper.createArrayNode();

        BatchSender(Stats stats) {
            this.stats = stats;
        }

        @Override
        public void entry(int x, int y, int z, String block) throws InterruptedException {
            ObjectNode b = batch.addObject();
            b.put("x", x);
            b.put("y", y);
            b.put("z", z);
            b.put("block", block);
            stats.entries++;
            if (batch.size() >= BATCH_SIZE) {
                flush();
            }
        }

        @Override
        public void invalid(String reason) {
            stats.invalid++;
            stats.example(reason);
        }

        void flush() throws InterruptedException {
            if (batch.isEmpty()) {
                return;
            }
            int n = batch.size();
            ObjectNode body = mapper.createObjectNode();
            body.set("blocks", batch);
            batch = mapper.createArrayNode();
            stats.batches++;
            McBackendClient.Response resp;
            try {
                resp = backend.postJson("/tools/set_blocks", body);
            } catch (IOException e) {
                stats.failed += n;
                stats.example("batch of " + n + " not sent: backend unreachable (" + e.getMessage() + ")");
                return;
            }
            stats.collectPlayerMessages(resp);
            if (!resp.isSuccess()) {
                stats.failed += n;
                stats.example("batch of " + n + " rejected: " + httpError(resp));
                return;
            }
            String jobId = parse(resp).path("job_id").asText("");
            if (jobId.isEmpty()) {
                stats.failed += n;
                stats.example("batch of " + n + ": set_blocks response has no job_id");
                return;
            }
            awaitJob(jobId, n);
        }

        private void awaitJob(String jobId, int batchSize) throws InterruptedException {
            long deadline = System.currentTimeMillis() + JOB_DEADLINE_MS;
            while (true) {
                McBackendClient.Response resp;
                try {
                    resp = backend.get("/tools/job_status?id="
                            + URLEncoder.encode(jobId, StandardCharsets.UTF_8));
                } catch (IOException e) {
                    stats.failed += batchSize;
                    stats.example("job " + jobId + ": status poll failed (" + e.getMessage() + ")");
                    return;
                }
                stats.collectPlayerMessages(resp);
                if (!resp.isSuccess()) {
                    stats.failed += batchSize;
                    stats.example("job " + jobId + ": status poll got " + httpError(resp));
                    return;
                }
                JsonNode json = parse(resp);
                String state = json.path("state").asText("");
                if ("done".equals(state) || "failed".equals(state)) {
                    stats.placed += json.path("placed").asInt(0);
                    stats.failed += json.path("failed").asInt(0);
                    JsonNode errors = json.path("errors");
                    if (errors.isArray()) {
                        for (JsonNode error : errors) {
                            stats.example("job " + jobId + ": " + error.asText());
                        }
                    }
                    return;
                }
                if (System.currentTimeMillis() >= deadline) {
                    stats.failed += batchSize;
                    stats.example("job " + jobId + ": still \"" + state + "\" after "
                            + JOB_DEADLINE_MS / 1000 + "s, giving up");
                    return;
                }
                Thread.sleep(JOB_POLL_INTERVAL_MS);
            }
        }
    }

    private final class Stats {
        private final String header;
        long entries;             // valid entries sent to the mod
        long invalid;             // entries dropped before sending (counted as failed)
        long skippedAir;
        int batches;
        long placed;              // placement outcomes reported by the mod
        long failed;
        int skippedBlockEntities;
        private final List<String> examples = new ArrayList<>();
        private final Set<String> playerMessages = new LinkedHashSet<>();

        Stats(String header) {
            this.header = header;
        }

        void example(String message) {
            if (examples.size() < MAX_EXAMPLES) {
                examples.add(message);
            }
        }

        void collectPlayerMessages(McBackendClient.Response resp) {
            JsonNode messages = parse(resp).path("player_messages");
            if (messages.isArray()) {
                for (JsonNode message : messages) {
                    playerMessages.add(message.asText());
                }
            }
        }

        boolean allFailed() {
            return placed == 0 && failed + invalid > 0;
        }

        String render() {
            StringBuilder sb = new StringBuilder(header).append('\n');
            sb.append("Sent ").append(entries).append(" entries in ").append(batches)
                    .append(" batch(es) of at most ").append(BATCH_SIZE).append(".");
            if (skippedAir > 0) {
                sb.append(" Skipped ").append(skippedAir).append(" air entries.");
            }
            if (invalid > 0) {
                sb.append(" ").append(invalid).append(" invalid entries dropped (counted as failed).");
            }
            if (skippedBlockEntities > 0) {
                sb.append(" Ignored ").append(skippedBlockEntities).append(" block entities.");
            }
            sb.append("\nPlaced: ").append(placed).append(", failed: ").append(failed + invalid)
                    .append(".");
            if (!examples.isEmpty()) {
                sb.append("\nFirst failures:");
                for (String example : examples) {
                    sb.append("\n - ").append(example);
                }
            }
            for (String message : playerMessages) {
                sb.append("\n[玩家消息] ").append(message);
            }
            return sb.toString();
        }
    }

    private JsonNode parse(McBackendClient.Response resp) {
        try {
            JsonNode json = mapper.readTree(resp.body());
            return json == null ? MissingNode.getInstance() : json;
        } catch (Exception e) {
            return MissingNode.getInstance();
        }
    }

    private String httpError(McBackendClient.Response resp) {
        StringBuilder sb = new StringBuilder("HTTP ").append(resp.status());
        JsonNode json = parse(resp);
        if (json.path("error").isTextual()) {
            sb.append(": ").append(json.path("error").asText());
        } else {
            String body = new String(resp.body(), StandardCharsets.UTF_8).strip();
            if (!body.isEmpty()) {
                sb.append(": ").append(body.length() <= 120 ? body : body.substring(0, 120) + "...");
            }
        }
        return sb.toString();
    }

    private ObjectNode text(String message, boolean isError) {
        ObjectNode result = mapper.createObjectNode();
        ArrayNode content = result.putArray("content");
        ObjectNode item = content.addObject();
        item.put("type", "text");
        item.put("text", message);
        result.put("isError", isError);
        return result;
    }
}
