package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * set_blocks_from_file: JSON mode batching/summary/validation and .schem mode
 * (v2/v3, offset, air skipping) through the full MCP dispatch against MockBackend.
 * The mock plays set_blocks (recording entry counts per job_id) and job_status.
 */
class SetBlocksFromFileTest {

    @TempDir
    Path tempDir;

    private MockBackend backend;
    private TestRig rig;
    private final Map<String, Integer> jobs = new ConcurrentHashMap<>();
    private final AtomicInteger jobSeq = new AtomicInteger();

    @BeforeEach
    void setUp() throws Exception {
        backend = new MockBackend();
        backend.on("/tools/set_blocks", req -> {
            try {
                int n = TestRig.MAPPER.readTree(req.body()).get("blocks").size();
                String id = "job-" + jobSeq.incrementAndGet();
                jobs.put(id, n);
                return MockBackend.Canned.json("{\"job_id\":\"" + id + "\"}");
            } catch (Exception e) {
                return MockBackend.Canned.json(500, "{\"error\":\"mock parse failure\"}");
            }
        });
        backend.on("/tools/job_status", req -> {
            String id = req.query() != null && req.query().startsWith("id=")
                    ? req.query().substring(3) : "";
            int n = jobs.getOrDefault(id, 0);
            return MockBackend.Canned.json("{\"job_id\":\"" + id + "\",\"state\":\"done\",\"total\":"
                    + n + ",\"placed\":" + n + ",\"failed\":0,\"errors\":[]}");
        });
        rig = new TestRig(backend.baseUrl());
    }

    @AfterEach
    void tearDown() {
        backend.close();
    }

    // ----- helpers -----

    private static String textOf(JsonNode resp) {
        return resp.get("result").get("content").get(0).get("text").asText();
    }

    private static String argsJson(Object... pairs) {
        ObjectNode args = TestRig.MAPPER.createObjectNode();
        for (int i = 0; i < pairs.length; i += 2) {
            String key = (String) pairs[i];
            Object value = pairs[i + 1];
            switch (value) {
                case String s -> args.put(key, s);
                case Boolean b -> args.put(key, b);
                case int[] v -> {
                    ArrayNode array = args.putArray(key);
                    for (int x : v) {
                        array.add(x);
                    }
                }
                default -> throw new IllegalArgumentException("unsupported value: " + value);
            }
        }
        return args.toString();
    }

    private Path writeJsonFile(String name, int count, boolean bareArray) throws IOException {
        ArrayNode blocks = TestRig.MAPPER.createArrayNode();
        for (int i = 0; i < count; i++) {
            ObjectNode b = blocks.addObject();
            b.put("x", i % 64);
            b.put("y", 64);
            b.put("z", i / 64);
            b.put("block", "minecraft:stone");
        }
        JsonNode root = blocks;
        if (!bareArray) {
            ObjectNode wrapper = TestRig.MAPPER.createObjectNode();
            wrapper.set("blocks", blocks);
            wrapper.put("note", "extra fields are ignored");
            root = wrapper;
        }
        Path file = tempDir.resolve(name);
        Files.writeString(file, TestRig.MAPPER.writeValueAsString(root));
        return file;
    }

    private List<Integer> batchSizes() throws IOException {
        List<Integer> sizes = new java.util.ArrayList<>();
        for (MockBackend.Request req : backend.requestsTo("/tools/set_blocks")) {
            sizes.add(TestRig.MAPPER.readTree(req.body()).get("blocks").size());
        }
        return sizes;
    }

    // ----- JSON mode -----

    @Test
    void jsonBatchesOf4096WithRemainderAndSummary() throws Exception {
        Path file = writeJsonFile("big.json", 9000, false);
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                argsJson("path", file.toString())));
        assertFalse(resp.get("result").get("isError").asBoolean(), textOf(resp));
        assertEquals(List.of(4096, 4096, 808), batchSizes());
        assertEquals(3, backend.requestsTo("/tools/job_status").size(),
                "each batch job is polled once (mock answers done immediately)");
        String text = textOf(resp);
        assertTrue(text.contains("Sent 9000 entries in 3 batch(es)"), text);
        assertTrue(text.contains("Placed: 9000, failed: 0."), text);
    }

    @Test
    void bareArrayFormatAccepted() throws Exception {
        Path file = writeJsonFile("bare.json", 3, true);
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                argsJson("path", file.toString())));
        assertFalse(resp.get("result").get("isError").asBoolean(), textOf(resp));
        assertEquals(List.of(3), batchSizes());
        assertTrue(textOf(resp).contains("Placed: 3, failed: 0."), textOf(resp));
    }

    @Test
    void missingFileIsErrorWithoutHttp() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                argsJson("path", tempDir.resolve("nope.json").toString())));
        assertTrue(resp.get("result").get("isError").asBoolean());
        assertTrue(textOf(resp).contains("File not found"), textOf(resp));
        assertEquals(0, backend.requests().size(), "no HTTP request may be sent");
    }

    @Test
    void invalidJsonIsErrorWithoutHttp() throws Exception {
        Path file = tempDir.resolve("broken.json");
        Files.writeString(file, "{\"blocks\":[{");
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                argsJson("path", file.toString())));
        assertTrue(resp.get("result").get("isError").asBoolean());
        assertTrue(textOf(resp).contains("invalid JSON"), textOf(resp));
        assertEquals(0, backend.requests().size(), "corrupt file must not trigger any request");
    }

    @Test
    void jsonObjectWithoutBlocksArrayIsErrorWithoutHttp() throws Exception {
        Path file = tempDir.resolve("empty.json");
        Files.writeString(file, "{}");
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                argsJson("path", file.toString())));
        assertTrue(resp.get("result").get("isError").asBoolean());
        assertTrue(textOf(resp).contains("blocks"), textOf(resp));
        assertEquals(0, backend.requests().size());
    }

    @Test
    void jobFailuresCountedWithExamples() throws Exception {
        backend.on("/tools/job_status", req -> MockBackend.Canned.json(
                "{\"job_id\":\"job-1\",\"state\":\"done\",\"total\":10,\"placed\":5,\"failed\":5,"
                        + "\"errors\":[\"minecraft:xyz is not a valid block\"]}"));
        Path file = writeJsonFile("ten.json", 10, false);
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                argsJson("path", file.toString())));
        assertFalse(resp.get("result").get("isError").asBoolean(), "partial failure is data, not a tool error");
        String text = textOf(resp);
        assertTrue(text.contains("Placed: 5, failed: 5."), text);
        assertTrue(text.contains("minecraft:xyz is not a valid block"), text);
    }

    @Test
    void rejectedBatchCountsAllItsEntriesAsFailed() throws Exception {
        backend.on("/tools/set_blocks", MockBackend.Canned.json(400,
                "{\"error\":\"site not confirmed\"}"));
        Path file = writeJsonFile("small.json", 5, false);
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                argsJson("path", file.toString())));
        assertTrue(resp.get("result").get("isError").asBoolean(), "everything failed -> isError");
        String text = textOf(resp);
        assertTrue(text.contains("Placed: 0, failed: 5."), text);
        assertTrue(text.contains("rejected: HTTP 400: site not confirmed"), text);
        assertEquals(0, backend.requestsTo("/tools/job_status").size(), "no job_id -> no poll");
    }

    @Test
    void invalidEntriesDroppedAndCountedAsFailed() throws Exception {
        Path file = tempDir.resolve("mixed.json");
        Files.writeString(file, "[{\"x\":0,\"y\":64,\"z\":0,\"block\":\"minecraft:stone\"},"
                + "{\"x\":1,\"y\":64,\"z\":0},"
                + "{\"x\":2,\"y\":64,\"z\":0,\"block\":\"minecraft:glass\"}]");
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                argsJson("path", file.toString())));
        assertFalse(resp.get("result").get("isError").asBoolean(), textOf(resp));
        assertEquals(List.of(2), batchSizes(), "the entry missing \"block\" must not be sent");
        String text = textOf(resp);
        assertTrue(text.contains("1 invalid entries dropped"), text);
        assertTrue(text.contains("Placed: 2, failed: 1."), text);
    }

    // ----- .schem mode -----

    /** 3x2x2, all stone except air at (0,0,0) and (1,1,1), file Offset [10,60,-5]. */
    private Path writeSchemV2(String name) throws IOException {
        int[] indices = new int[12];
        java.util.Arrays.fill(indices, 1);
        indices[0] = 0;                          // (0,0,0)
        indices[1 + 1 * 3 + 1 * 3 * 2] = 0;      // (1,1,1)
        Path file = tempDir.resolve(name);
        Files.write(file, SchemFixtures.schematic(2, 3, 2, 2, new int[]{10, 60, -5},
                Map.of("minecraft:air", 0, "minecraft:stone", 1), indices, 0));
        return file;
    }

    @Test
    void schemV2AppliesOffsetAndSkipsAir() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                argsJson("path", writeSchemV2("house.schem").toString())));
        assertFalse(resp.get("result").get("isError").asBoolean(), textOf(resp));
        assertEquals(List.of(10), batchSizes(), "12 positions - 2 air");
        JsonNode blocks = TestRig.MAPPER
                .readTree(backend.requestsTo("/tools/set_blocks").get(0).body()).get("blocks");
        boolean sawOffsetMapping = false;
        for (JsonNode b : blocks) {
            assertEquals("minecraft:stone", b.get("block").asText(), "air must be skipped");
            if (b.get("x").asInt() == 11 && b.get("y").asInt() == 60 && b.get("z").asInt() == -5) {
                sawOffsetMapping = true; // local (1,0,0) + Offset [10,60,-5]
            }
        }
        assertTrue(sawOffsetMapping, "file Offset must shift coordinates");
        String text = textOf(resp);
        assertTrue(text.contains("Sponge Schematic v2"), text);
        assertTrue(text.contains("Skipped 2 air entries."), text);
        assertTrue(text.contains("Placed: 10, failed: 0."), text);
    }

    @Test
    void schemPlaceAirKeepsAirEntries() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                argsJson("path", writeSchemV2("air.schem").toString(), "place_air", true)));
        assertFalse(resp.get("result").get("isError").asBoolean(), textOf(resp));
        assertEquals(List.of(12), batchSizes(), "place_air=true sends air too");
        JsonNode blocks = TestRig.MAPPER
                .readTree(backend.requestsTo("/tools/set_blocks").get(0).body()).get("blocks");
        long air = 0;
        for (JsonNode b : blocks) {
            if (b.get("block").asText().equals("minecraft:air")) {
                air++;
            }
        }
        assertEquals(2, air);
    }

    @Test
    void schemExplicitOffsetOverridesFileOffset() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                argsJson("path", writeSchemV2("override.schem").toString(), "offset", new int[]{0, 0, 0})));
        assertFalse(resp.get("result").get("isError").asBoolean(), textOf(resp));
        JsonNode blocks = TestRig.MAPPER
                .readTree(backend.requestsTo("/tools/set_blocks").get(0).body()).get("blocks");
        boolean sawOriginMapping = false;
        for (JsonNode b : blocks) {
            if (b.get("x").asInt() == 1 && b.get("y").asInt() == 0 && b.get("z").asInt() == 0) {
                sawOriginMapping = true; // local (1,0,0), explicit offset [0,0,0] wins over [10,60,-5]
            }
        }
        assertTrue(sawOriginMapping, "explicit offset argument must override the file Offset");
        assertTrue(textOf(resp).contains("origin offset [0, 0, 0]"), textOf(resp));
    }

    @Test
    void schemV3SupportedAndBlockEntitiesReported() throws Exception {
        int[] indices = new int[8];
        java.util.Arrays.fill(indices, 1);
        Path file = tempDir.resolve("v3.schem");
        Files.write(file, SchemFixtures.schematic(3, 2, 2, 2, null,
                Map.of("minecraft:air", 0, "minecraft:glass", 1), indices, 1));
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                argsJson("path", file.toString())));
        assertFalse(resp.get("result").get("isError").asBoolean(), textOf(resp));
        assertEquals(List.of(8), batchSizes());
        String text = textOf(resp);
        assertTrue(text.contains("Sponge Schematic v3"), text);
        assertTrue(text.contains("Ignored 1 block entities."), text);
    }

    @Test
    void corruptSchemIsErrorWithoutHttp() throws Exception {
        Path file = tempDir.resolve("junk.schem");
        Files.write(file, new byte[]{9, 8, 7, 6, 5});
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                argsJson("path", file.toString())));
        assertTrue(resp.get("result").get("isError").asBoolean());
        assertTrue(textOf(resp).contains("Failed to process"), textOf(resp));
        assertEquals(0, backend.requests().size());
    }
}
