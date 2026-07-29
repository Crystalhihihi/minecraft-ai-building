package com.aibuild.mod.bridge;

import com.aibuild.mod.AiBuildMod;
import com.aibuild.mod.job.BuildJob;
import com.aibuild.mod.job.FillMode;
import com.aibuild.mod.job.Job;
import com.aibuild.mod.job.JobManager;
import com.aibuild.mod.job.Placement;
import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonSyntaxException;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.chat.Style;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * Minimal embedded HTTP API (JDK {@link com.sun.net.httpserver}) for the
 * mc-mcp-bridge. Binds 127.0.0.1 on a random port with a random bearer token,
 * written to {@code <gameDir>/aibuild/bridge.json} on server start.
 *
 * HTTP threads only serialize JSON; every world operation is dispatched to
 * the server main thread via {@link MinecraftServer#execute} and awaited with
 * a timeout.
 */
public final class BridgeHttpServer {
    private static final Gson GSON = new Gson();
    private static final int MAIN_THREAD_TIMEOUT_SECONDS = 30;

    private final JobManager jobManager;
    private final PlayerInbox inbox;
    private final SiteGate gate;
    private HttpServer http;
    private String token;
    private int port = -1;
    private MinecraftServer server;

    public BridgeHttpServer(JobManager jobManager, PlayerInbox inbox, SiteGate gate) {
        this.jobManager = jobManager;
        this.inbox = inbox;
        this.gate = gate;
    }

    public void start(MinecraftServer server, Path gameDir) throws IOException {
        this.server = server;
        this.token = UUID.randomUUID().toString();

        http = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        http.createContext("/tools/fill", ex -> handle(ex, "POST", this::fill));
        http.createContext("/tools/set_blocks", ex -> handle(ex, "POST", this::setBlocks));
        http.createContext("/tools/set_block", ex -> handle(ex, "POST", this::setBlock));
        http.createContext("/tools/job_status", ex -> handle(ex, "GET", this::jobStatus));
        http.createContext("/tools/get_block", ex -> handle(ex, "POST", this::getBlock));
        http.createContext("/tools/search_blocks", ex -> handle(ex, "POST", this::searchBlocks));
        http.createContext("/tools/propose_site", ex -> handle(ex, "POST", this::proposeSite));
        http.createContext("/tools/get_terrain_summary", ex -> handle(ex, "POST", this::getTerrainSummary));
        http.setExecutor(Executors.newCachedThreadPool(r -> {
            Thread t = new Thread(r, "aibuild-http");
            t.setDaemon(true);
            return t;
        }));
        http.start();

        port = http.getAddress().getPort();
        Path dir = gameDir.resolve("aibuild");
        Files.createDirectories(dir);
        JsonObject info = new JsonObject();
        info.addProperty("port", port);
        info.addProperty("token", token);
        Path bridgeJson = dir.resolve("bridge.json");
        Files.writeString(bridgeJson, GSON.toJson(info));
        AiBuildMod.LOGGER.info("[aibuild] bridge http server listening on 127.0.0.1:{} (credentials in {})", port, bridgeJson);
    }

    public int port() {
        return port;
    }

    public String token() {
        return token;
    }

    public void stop() {
        if (http != null) {
            http.stop(0);
            http = null;
        }
    }

    // ------------------------------------------------------------------ plumbing

    @FunctionalInterface
    private interface Endpoint {
        JsonObject handle(HttpExchange exchange) throws Exception;
    }

    private static final class ApiError extends Exception {
        final int status;
        final JsonObject body;

        ApiError(int status, JsonObject body) {
            super(body.toString());
            this.status = status;
            this.body = body;
        }
    }

    private void handle(HttpExchange ex, String method, Endpoint endpoint) throws IOException {
        try {
            if (!token.equals(ex.getRequestHeaders().getFirst("X-Aibuild-Token"))) {
                send(ex, 403, error("forbidden"));
                return;
            }
            if (!method.equalsIgnoreCase(ex.getRequestMethod())) {
                send(ex, 405, error("method not allowed"));
                return;
            }
            send(ex, 200, endpoint.handle(ex));
        } catch (ApiError e) {
            send(ex, e.status, e.body);
        } catch (Exception e) {
            AiBuildMod.LOGGER.error("[aibuild] error handling {} {}", ex.getRequestMethod(), ex.getRequestURI(), e);
            send(ex, 500, error("internal error: " + e.getMessage()));
        } finally {
            ex.close();
        }
    }

    /** Runs a task on the server main thread and waits for the result (with a timeout). */
    private <T> T onMainThread(Callable<T> task) throws Exception {
        CompletableFuture<T> future = new CompletableFuture<>();
        server.execute(() -> {
            try {
                future.complete(task.call());
            } catch (Throwable t) {
                future.completeExceptionally(t);
            }
        });
        try {
            return future.get(MAIN_THREAD_TIMEOUT_SECONDS, TimeUnit.SECONDS);
        } catch (ExecutionException e) {
            if (e.getCause() instanceof Exception cause) {
                throw cause;
            }
            throw e;
        }
    }

    private void send(HttpExchange ex, int status, JsonObject body) {
        try {
            // Piggyback queued player messages onto every JSON response (except
            // auth failures, which by definition do not reach the agent).
            if (status != 403) {
                List<String> messages = inbox.drain();
                if (!messages.isEmpty()) {
                    JsonArray arr = new JsonArray();
                    for (String m : messages) {
                        arr.add(m);
                    }
                    body.add("player_messages", arr);
                }
            }
            byte[] bytes = GSON.toJson(body).getBytes(StandardCharsets.UTF_8);
            ex.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
            ex.sendResponseHeaders(status, bytes.length);
            try (OutputStream os = ex.getResponseBody()) {
                os.write(bytes);
            }
        } catch (IOException e) {
            AiBuildMod.LOGGER.warn("[aibuild] failed to send http response", e);
        }
    }

    private static JsonObject error(String message) {
        JsonObject o = new JsonObject();
        o.addProperty("error", message);
        return o;
    }

    private static ApiError badRequest(String message) {
        return new ApiError(400, error(message));
    }

    private static ApiError invalidBlock(BlockSpecParser.InvalidBlockException e) {
        JsonObject body = error(e.getMessage());
        JsonArray suggestions = new JsonArray();
        for (String s : e.suggestions()) {
            suggestions.add(s);
        }
        body.add("suggestions", suggestions);
        return new ApiError(400, body);
    }

    // ------------------------------------------------------------------ endpoints

    private JsonObject fill(HttpExchange ex) throws Exception {
        JsonObject body = readJsonBody(ex);
        int[] min = vec3(body, "min");
        int[] max = vec3(body, "max");
        String blockSpec = requiredString(body, "block");
        FillMode mode;
        try {
            mode = FillMode.parse(optString(body, "mode", "replace"));
        } catch (IllegalArgumentException e) {
            throw badRequest(e.getMessage());
        }

        int minX = Math.min(min[0], max[0]);
        int minY = Math.min(min[1], max[1]);
        int minZ = Math.min(min[2], max[2]);
        int maxX = Math.max(min[0], max[0]);
        int maxY = Math.max(min[1], max[1]);
        int maxZ = Math.max(min[2], max[2]);
        long volume = (long) (maxX - minX + 1) * (maxY - minY + 1) * (maxZ - minZ + 1);
        if (volume > JobManager.MAX_JOB_BLOCKS) {
            throw badRequest("fill volume " + volume + " exceeds limit of " + JobManager.MAX_JOB_BLOCKS + " blocks");
        }

        SiteGate.Bounds bounds = requireBounds();
        BlockPos minPos = new BlockPos(minX, minY, minZ);
        BlockPos maxPos = new BlockPos(maxX, maxY, maxZ);
        BuildJob job = onMainThread(() -> {
            BlockState state = parseBlock(blockSpec);
            return jobManager.submitFill(server.overworld(), minPos, maxPos, state, mode, bounds,
                    "fill " + blockSpec + " " + minPos.toShortString() + " ~ " + maxPos.toShortString());
        });
        return jobId(job);
    }

    private JsonObject setBlocks(HttpExchange ex) throws Exception {
        JsonObject body = readJsonBody(ex);
        JsonArray entries = requiredArray(body, "blocks");
        if (entries.size() > JobManager.MAX_SET_BLOCKS_ENTRIES) {
            throw badRequest("set_blocks accepts at most " + JobManager.MAX_SET_BLOCKS_ENTRIES
                    + " entries per request, got " + entries.size());
        }
        record RawEntry(int x, int y, int z, String spec) {
        }
        List<RawEntry> raw = new ArrayList<>(entries.size());
        for (JsonElement el : entries) {
            if (!el.isJsonObject()) {
                throw badRequest("each set_blocks entry must be an object {x,y,z,block}");
            }
            JsonObject o = el.getAsJsonObject();
            raw.add(new RawEntry(requiredInt(o, "x"), requiredInt(o, "y"), requiredInt(o, "z"), requiredString(o, "block")));
        }
        SiteGate.Bounds bounds = requireBounds();
        BuildJob job = onMainThread(() -> {
            List<Placement> placements = new ArrayList<>(raw.size());
            for (RawEntry r : raw) {
                placements.add(new Placement(new BlockPos(r.x(), r.y(), r.z()), parseBlock(r.spec()), false));
            }
            return jobManager.submitPlacements(server.overworld(), placements, bounds,
                    "set_blocks " + raw.size() + " blocks");
        });
        return jobId(job);
    }

    private JsonObject setBlock(HttpExchange ex) throws Exception {
        JsonObject body = readJsonBody(ex);
        int x = requiredInt(body, "x");
        int y = requiredInt(body, "y");
        int z = requiredInt(body, "z");
        String blockSpec = requiredString(body, "block");
        SiteGate.Bounds bounds = requireBounds();
        BuildJob job = onMainThread(() -> jobManager.submitPlacements(server.overworld(),
                List.of(new Placement(new BlockPos(x, y, z), parseBlock(blockSpec), false)), bounds,
                "set_block " + blockSpec + " @ " + x + " " + y + " " + z));
        return jobId(job);
    }

    private JsonObject searchBlocks(HttpExchange ex) throws Exception {
        JsonObject body = readJsonBody(ex);
        String query = requiredString(body, "query");
        JsonArray matches = new JsonArray();
        for (String match : BlockSpecParser.search(query, 16)) {
            matches.add(match);
        }
        JsonObject res = new JsonObject();
        res.add("matches", matches);
        return res;
    }

    private JsonObject jobStatus(HttpExchange ex) throws Exception {
        String id = queryParam(ex, "id");
        if (id == null || id.isEmpty()) {
            throw badRequest("missing query parameter 'id'");
        }
        Job job = onMainThread(() -> jobManager.get(id));
        if (job == null) {
            throw new ApiError(404, error("unknown job_id: " + id));
        }
        return job.toJson();
    }

    private JsonObject getBlock(HttpExchange ex) throws Exception {
        JsonObject body = readJsonBody(ex);
        BlockPos pos = new BlockPos(requiredInt(body, "x"), requiredInt(body, "y"), requiredInt(body, "z"));
        return onMainThread(() -> {
            BlockState state = server.overworld().getBlockState(pos);
            JsonObject res = new JsonObject();
            res.addProperty("block", BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString());
            JsonObject props = new JsonObject();
            state.getValues().forEach((property, value) -> props.addProperty(property.getName(), propertyValue(property, value)));
            res.add("properties", props);
            return res;
        });
    }

    private JsonObject proposeSite(HttpExchange ex) throws Exception {
        JsonObject body = readJsonBody(ex);
        SiteGate.Bounds proposal = SiteGate.Bounds.of(vec3(body, "min"), vec3(body, "max"));
        if (proposal.volume() > SiteGate.MAX_VOLUME) {
            throw badRequest("proposed volume " + proposal.volume() + " exceeds limit of " + SiteGate.MAX_VOLUME + " blocks");
        }
        return onMainThread(() -> {
            if (!gate.propose(proposal)) {
                String why = gate.state() == SiteGate.State.CONFIRMED
                        ? "site already confirmed for this session: " + gate.currentBounds().describe()
                        : "another site proposal is already pending confirmation";
                throw new ApiError(409, error(why));
            }
            broadcastProposal(proposal);
            JsonObject res = new JsonObject();
            res.addProperty("status", "pending_confirmation");
            res.addProperty("message", "等待玩家确认(/aiconfirm 或 /aireject);确认前写工具保持锁定");
            return res;
        });
    }

    private JsonObject getTerrainSummary(HttpExchange ex) throws Exception {
        JsonObject body = readJsonBody(ex);
        JsonArray center = requiredArray(body, "center");
        if (center.size() != 2) {
            throw badRequest("'center' must be [x,z]");
        }
        int cx = center.get(0).getAsInt();
        int cz = center.get(1).getAsInt();
        int radius = requiredInt(body, "radius");
        if (radius < 1 || radius > TerrainSummary.MAX_RADIUS) {
            throw badRequest("radius must be between 1 and " + TerrainSummary.MAX_RADIUS);
        }
        String text = onMainThread(() -> TerrainSummary.generate(server.overworld(), cx, cz, radius));
        JsonObject res = new JsonObject();
        res.addProperty("text", text);
        return res;
    }

    /** Bounds gate for write tools: 409 while the session has no confirmed range. */
    private SiteGate.Bounds requireBounds() throws ApiError {
        SiteGate.Bounds bounds = gate.currentBounds();
        if (bounds == null) {
            throw new ApiError(409, error("site not confirmed"));
        }
        return bounds;
    }

    /**
     * Sends the site proposal to every online player with clickable
     * [确认]/[拒绝] buttons (ClickEvent.RunCommand → /aiconfirm, /aireject;
     * verified against 1.21.11: ClickEvent is an interface of records, the
     * client trims the optional leading "/" before sending the command).
     * With nobody online the message is logged and RCON/console can run the
     * same commands.
     */
    private void broadcastProposal(SiteGate.Bounds b) {
        MutableComponent msg = Component.literal("[aibuild] AI proposes build site " + b.describe() + "  ");
        msg.append(Component.literal("[确认]").withStyle(Style.EMPTY
                .withColor(ChatFormatting.GREEN).withBold(true)
                .withClickEvent(new ClickEvent.RunCommand("/aiconfirm"))));
        msg.append(Component.literal("  "));
        msg.append(Component.literal("[拒绝]").withStyle(Style.EMPTY
                .withColor(ChatFormatting.RED).withBold(true)
                .withClickEvent(new ClickEvent.RunCommand("/aireject"))));
        AiBuildMod.LOGGER.info("[aibuild] site proposed: {}", b.describe());
        server.getPlayerList().broadcastSystemMessage(msg, false);
    }

    // ------------------------------------------------------------------ helpers

    private BlockState parseBlock(String spec) throws ApiError {
        try {
            return BlockSpecParser.parse(server, spec);
        } catch (BlockSpecParser.InvalidBlockException e) {
            throw invalidBlock(e);
        }
    }

    private static JsonObject jobId(BuildJob job) {
        JsonObject res = new JsonObject();
        res.addProperty("job_id", job.id());
        return res;
    }

    private static JsonObject readJsonBody(HttpExchange ex) throws IOException, ApiError {
        String body = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        try {
            JsonElement el = JsonParser.parseString(body.isBlank() ? "{}" : body);
            if (!el.isJsonObject()) {
                throw badRequest("request body must be a JSON object");
            }
            return el.getAsJsonObject();
        } catch (JsonSyntaxException | IllegalStateException e) {
            throw badRequest("malformed JSON body");
        }
    }

    private static String queryParam(HttpExchange ex, String name) {
        String query = ex.getRequestURI().getRawQuery();
        if (query == null) {
            return null;
        }
        for (String pair : query.split("&")) {
            int eq = pair.indexOf('=');
            String key = eq >= 0 ? pair.substring(0, eq) : pair;
            if (key.equals(name)) {
                return eq >= 0 ? pair.substring(eq + 1) : "";
            }
        }
        return null;
    }

    private static int[] vec3(JsonObject body, String name) throws ApiError {
        JsonArray arr = requiredArray(body, name);
        if (arr.size() != 3) {
            throw badRequest("'" + name + "' must be [x,y,z]");
        }
        int[] out = new int[3];
        for (int i = 0; i < 3; i++) {
            JsonElement el = arr.get(i);
            if (!el.isJsonPrimitive() || !el.getAsJsonPrimitive().isNumber()) {
                throw badRequest("'" + name + "' must contain integers");
            }
            out[i] = el.getAsInt();
        }
        return out;
    }

    private static JsonArray requiredArray(JsonObject body, String name) throws ApiError {
        if (!body.has(name) || !body.get(name).isJsonArray()) {
            throw badRequest("missing or invalid '" + name + "' array");
        }
        return body.getAsJsonArray(name);
    }

    private static int requiredInt(JsonObject body, String name) throws ApiError {
        if (!body.has(name) || !body.get(name).isJsonPrimitive() || !body.get(name).getAsJsonPrimitive().isNumber()) {
            throw badRequest("missing or invalid integer '" + name + "'");
        }
        return body.get(name).getAsInt();
    }

    private static String requiredString(JsonObject body, String name) throws ApiError {
        if (!body.has(name) || !body.get(name).isJsonPrimitive() || !body.get(name).getAsJsonPrimitive().isString()) {
            throw badRequest("missing or invalid string '" + name + "'");
        }
        return body.get(name).getAsString();
    }

    private static String optString(JsonObject body, String name, String fallback) throws ApiError {
        if (!body.has(name) || body.get(name).isJsonNull()) {
            return fallback;
        }
        return requiredString(body, name);
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static String propertyValue(Property<?> property, Comparable<?> value) {
        return ((Property) property).getName(value);
    }
}
