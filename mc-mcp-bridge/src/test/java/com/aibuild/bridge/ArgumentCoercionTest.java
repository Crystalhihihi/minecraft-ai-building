package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Postel coercion (ArgumentCoercer): string-typed arguments from small models
 * ("64", "[0,0]", "true") are parsed against the tool inputSchema before dispatch
 * and must map to the same HTTP request as properly typed ones. Strings that
 * cannot be parsed must still fail with isError:true and no HTTP request.
 * (get_job_status and search_blocks only take strings - nothing to coerce.)
 */
class ArgumentCoercionTest {

    @TempDir
    Path tempDir;

    private MockBackend backend;
    private TestRig rig;

    @BeforeEach
    void setUp() throws Exception {
        backend = new MockBackend();
        backend.on("/tools/fill", MockBackend.Canned.json("{\"job_id\":\"job-1\"}"));
        backend.on("/tools/set_blocks", MockBackend.Canned.json("{\"job_id\":\"job-2\"}"));
        backend.on("/tools/set_block", MockBackend.Canned.json("{\"job_id\":\"job-3\"}"));
        backend.on("/tools/job_status", MockBackend.Canned.json(
                "{\"job_id\":\"job-2\",\"state\":\"done\",\"total\":2,\"placed\":2,\"failed\":0,\"errors\":[]}"));
        backend.on("/tools/get_block", MockBackend.Canned.json("{\"block\":\"minecraft:stone\"}"));
        backend.on("/tools/get_region_summary", MockBackend.Canned.json("{\"text\":\"summary\"}"));
        backend.on("/tools/get_terrain_summary", MockBackend.Canned.json("{\"text\":\"terrain\"}"));
        backend.on("/tools/render_region", MockBackend.Canned.png(TestImages.png64()));
        backend.on("/tools/propose_site", MockBackend.Canned.json(
                "{\"status\":\"pending_confirmation\",\"message\":\"ok\"}"));
        rig = new TestRig(backend.baseUrl());
        System.setProperty("aibuild.bridge.fileRoot", tempDir.toString());
    }

    @AfterEach
    void tearDown() {
        System.clearProperty("aibuild.bridge.fileRoot");
        backend.close();
    }

    private MockBackend.Request soleRequest(String path) {
        assertEquals(1, backend.requests().size(), "expected exactly 1 HTTP request");
        MockBackend.Request req = backend.requests().get(0);
        assertEquals(path, req.path());
        return req;
    }

    private JsonNode bodyOf(MockBackend.Request req) throws Exception {
        return TestRig.MAPPER.readTree(req.body());
    }

    private String callForError(String tool, String args) throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, tool, args));
        assertTrue(resp.get("result").get("isError").asBoolean(), "expected isError:true, got: " + resp);
        return resp.get("result").get("content").get(0).get("text").asText();
    }

    // ----- per-tool string-typed arguments -----

    @Test
    void fillCoercesStringifiedBoxes() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "fill",
                "{\"min\":\"[1,2,3]\",\"max\":\"[4,5,6]\",\"block\":\"minecraft:stone_bricks\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        JsonNode body = bodyOf(soleRequest("/tools/fill"));
        assertEquals("[1,2,3]", body.get("min").toString());
        assertEquals("[4,5,6]", body.get("max").toString());
        assertTrue(body.get("min").get(0).isInt(), "elements must be integers, not strings");
    }

    @Test
    void setBlocksCoercesStringifiedArrayAndNestedCoords() throws Exception {
        // The whole blocks array is a string, and the coords inside are strings too.
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks",
                "{\"blocks\":\"[{\\\"x\\\":\\\"0\\\",\\\"y\\\":\\\"64\\\",\\\"z\\\":\\\"0\\\","
                        + "\\\"block\\\":\\\"minecraft:oak_planks\\\"},"
                        + "{\\\"x\\\":\\\"1\\\",\\\"y\\\":\\\"64\\\",\\\"z\\\":\\\"0\\\","
                        + "\\\"block\\\":\\\"minecraft:torch\\\"}]\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        JsonNode body = bodyOf(soleRequest("/tools/set_blocks"));
        assertEquals(2, body.get("blocks").size());
        JsonNode first = body.get("blocks").get(0);
        assertTrue(first.get("x").isInt() && first.get("y").isInt() && first.get("z").isInt(),
                "nested string coords must be coerced: " + first);
        assertEquals(64, first.get("y").asInt());
        assertEquals("minecraft:torch", body.get("blocks").get(1).get("block").asText());
    }

    @Test
    void setBlockCoercesStringCoords() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_block",
                "{\"x\":\"1\",\"y\":\"64\",\"z\":\"-2\",\"block\":\"minecraft:torch\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        JsonNode body = bodyOf(soleRequest("/tools/set_block"));
        assertEquals("{\"x\":1,\"y\":64,\"z\":-2,\"block\":\"minecraft:torch\"}", body.toString());
    }

    @Test
    void getBlockCoercesStringCoords() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "get_block", "{\"x\":\"1\",\"y\":\"2\",\"z\":\"3\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        assertEquals("{\"x\":1,\"y\":2,\"z\":3}", bodyOf(soleRequest("/tools/get_block")).toString());
    }

    @Test
    void regionSummaryCoercesStringifiedBoxes() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "get_region_summary",
                "{\"min\":\"[0,60,0]\",\"max\":\"[9,70,9]\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        JsonNode body = bodyOf(soleRequest("/tools/get_region_summary"));
        assertEquals("[0,60,0]", body.get("min").toString());
        assertEquals("[9,70,9]", body.get("max").toString());
    }

    @Test
    void terrainSummaryCoercesCenterAndRadius() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "get_terrain_summary",
                "{\"center\":\"[100,200]\",\"radius\":\"64\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        JsonNode body = bodyOf(soleRequest("/tools/get_terrain_summary"));
        assertEquals("[100,200]", body.get("center").toString());
        assertEquals(64, body.get("radius").asInt());
    }

    @Test
    void renderRegionCoercesStringAngles() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "render_region",
                "{\"min\":\"[0,0,0]\",\"max\":\"[9,9,9]\",\"azimuth\":\"30\",\"elevation\":\"60\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        JsonNode body = bodyOf(soleRequest("/tools/render_region"));
        assertEquals(30, body.get("azimuth").asInt());
        assertEquals(60, body.get("elevation").asInt());
    }

    @Test
    void proposeSiteCoercesStringifiedBoxes() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "propose_site",
                "{\"min\":\"[0,0,0]\",\"max\":\"[31,15,31]\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        JsonNode body = bodyOf(soleRequest("/tools/propose_site"));
        assertEquals("[31,15,31]", body.get("max").toString());
    }

    @Test
    void setBlocksFromFileCoercesOffsetAndPlaceAir() throws Exception {
        // 2x1x1 schem: air at (0,0,0), stone at (1,0,0), no file offset.
        Path schem = tempDir.resolve("pair.schem");
        Files.write(schem, SchemFixtures.schematic(2, 2, 1, 1, null,
                Map.of("minecraft:air", 0, "minecraft:stone", 1), new int[]{0, 1}, 0));
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks_from_file",
                "{\"path\":\"" + schem.toString().replace("\\", "\\\\") + "\","
                        + "\"offset\":\"[5,5,5]\",\"place_air\":\"true\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        assertEquals(1, backend.requestsTo("/tools/set_blocks").size());
        MockBackend.Request req = backend.requestsTo("/tools/set_blocks").get(0);
        JsonNode blocks = bodyOf(req).get("blocks");
        assertEquals(2, blocks.size(), "place_air=\"true\" (string) must keep the air entry");
        assertEquals(5, blocks.get(0).get("x").asInt(), "string offset must be applied");
        assertEquals(6, blocks.get(1).get("x").asInt());
        assertEquals(5, blocks.get(1).get("y").asInt());
    }

    // ----- lenient forms that must also work -----

    @Test
    void mixedStringElementsInsideRealArrayAreCoerced() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "fill",
                "{\"min\":[\"1\",\"2\",3],\"max\":[4,5,6],\"block\":\"minecraft:glass\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        JsonNode body = bodyOf(soleRequest("/tools/fill"));
        assertEquals("[1,2,3]", body.get("min").toString());
    }

    @Test
    void integralDoubleInIntegerSlotIsCoerced() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_block",
                "{\"x\":1.0,\"y\":64.0,\"z\":-2.0,\"block\":\"minecraft:torch\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        JsonNode body = bodyOf(soleRequest("/tools/set_block"));
        assertEquals("{\"x\":1,\"y\":64,\"z\":-2,\"block\":\"minecraft:torch\"}", body.toString());
    }

    @Test
    void decimalStringInIntegerSlotIsCoerced() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "get_terrain_summary",
                "{\"center\":[100,200],\"radius\":\"64.0\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        assertEquals(64, bodyOf(soleRequest("/tools/get_terrain_summary")).get("radius").asInt());
    }

    // ----- logging -----

    @Test
    void coercionIsLoggedToStderr() throws Exception {
        PrintStream originalErr = System.err;
        ByteArrayOutputStream captured = new ByteArrayOutputStream();
        System.setErr(new PrintStream(captured, true, StandardCharsets.UTF_8));
        try {
            rig.call(TestRig.toolsCall(1, "get_terrain_summary",
                    "{\"center\":\"[100,200]\",\"radius\":\"64\"}"));
        } finally {
            System.setErr(originalErr);
        }
        String logs = captured.toString(StandardCharsets.UTF_8);
        assertTrue(logs.contains("coerced center: string -> array"), logs);
        assertTrue(logs.contains("coerced radius: string -> integer"), logs);
    }

    // ----- strings that genuinely cannot be parsed must stay errors -----

    @Test
    void unparseableIntegerStringIsErrorWithoutHttp() throws Exception {
        String text = callForError("set_block",
                "{\"x\":\"sixty-four\",\"y\":64,\"z\":0,\"block\":\"minecraft:stone\"}");
        assertTrue(text.contains("\"x\""), text);
        assertTrue(text.contains("integer"), text);
        assertEquals(0, backend.requests().size(), "no HTTP request may be sent");
    }

    @Test
    void nonIntegralStringInIntegerSlotIsError() throws Exception {
        String text = callForError("set_block",
                "{\"x\":\"1.5\",\"y\":64,\"z\":0,\"block\":\"minecraft:stone\"}");
        assertTrue(text.contains("\"x\""), text);
        assertEquals(0, backend.requests().size());
    }

    @Test
    void unparseableArrayStringIsErrorWithoutHttp() throws Exception {
        String text = callForError("fill",
                "{\"min\":\"not-an-array\",\"max\":[1,1,1],\"block\":\"minecraft:stone\"}");
        assertTrue(text.contains("\"min\""), text);
        assertTrue(text.contains("array"), text);
        assertEquals(0, backend.requests().size());
    }

    @Test
    void arrayWithUnparseableElementIsErrorWithoutHttp() throws Exception {
        // The string parses as a JSON array, but its elements are not integers.
        String text = callForError("fill",
                "{\"min\":\"[\\\"a\\\",2,3]\",\"max\":[1,1,1],\"block\":\"minecraft:stone\"}");
        assertTrue(text.contains("min[0]"), text);
        assertEquals(0, backend.requests().size());
    }

    @Test
    void unparseableBooleanStringIsErrorWithoutHttp() throws Exception {
        String text = callForError("set_blocks_from_file",
                "{\"path\":\"whatever.json\",\"place_air\":\"yes\"}");
        assertTrue(text.contains("place_air"), text);
        assertTrue(text.contains("boolean"), text);
        assertEquals(0, backend.requests().size(), "coercion fails before the file is even checked");
    }

    @Test
    void unparseableNumberStringIsErrorWithoutHttp() throws Exception {
        String text = callForError("render_region",
                "{\"min\":[0,0,0],\"max\":[1,1,1],\"azimuth\":\"thirty\"}");
        assertTrue(text.contains("azimuth"), text);
        assertEquals(0, backend.requests().size());
    }

    @Test
    void unparseableNestedBlocksEntryIsErrorWithoutHttp() throws Exception {
        String text = callForError("set_blocks",
                "{\"blocks\":\"[{\\\"x\\\":\\\"zero\\\",\\\"y\\\":64,\\\"z\\\":0,"
                        + "\\\"block\\\":\\\"minecraft:stone\\\"}]\"}");
        assertTrue(text.contains("blocks[0].x"), text);
        assertEquals(0, backend.requests().size());
    }

    @Test
    void errorNamesTheTool() throws Exception {
        String text = callForError("get_block", "{\"x\":\"?\",\"y\":0,\"z\":0}");
        assertTrue(text.contains("get_block"), text);
    }

    // ----- untouched behavior -----

    @Test
    void alreadyTypedArgumentsPassThroughUnchanged() throws Exception {
        rig.call(TestRig.toolsCall(1, "fill",
                "{\"min\":[1,2,3],\"max\":[4,5,6],\"block\":\"minecraft:stone_bricks\",\"mode\":\"hollow\"}"));
        assertEquals("{\"min\":[1,2,3],\"max\":[4,5,6],\"block\":\"minecraft:stone_bricks\","
                + "\"mode\":\"hollow\"}", bodyOf(soleRequest("/tools/fill")).toString());
    }
}
