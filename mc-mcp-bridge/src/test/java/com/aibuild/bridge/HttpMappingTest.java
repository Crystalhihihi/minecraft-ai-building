package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Each tool must hit the exact HTTP method/path/body from docs/specs/bridge-http-api.md,
 * always carrying the X-Aibuild-Token header. */
class HttpMappingTest {

    private MockBackend backend;
    private TestRig rig;

    @BeforeEach
    void setUp() throws Exception {
        backend = new MockBackend();
        backend.on("/tools/fill", MockBackend.Canned.json("{\"job_id\":\"job-1\"}"));
        backend.on("/tools/set_blocks", MockBackend.Canned.json("{\"job_id\":\"job-2\"}"));
        backend.on("/tools/set_block", MockBackend.Canned.json("{\"job_id\":\"job-3\"}"));
        backend.on("/tools/job_status", MockBackend.Canned.json(
                "{\"job_id\":\"job-1\",\"state\":\"done\",\"total\":10,\"placed\":10,\"failed\":0,\"errors\":[]}"));
        backend.on("/tools/get_block", MockBackend.Canned.json(
                "{\"block\":\"minecraft:oak_stairs\",\"properties\":{\"facing\":\"north\"}}"));
        backend.on("/tools/get_region_summary", MockBackend.Canned.json("{\"text\":\"summary\"}"));
        backend.on("/tools/get_terrain_summary", MockBackend.Canned.json("{\"text\":\"terrain\"}"));
        backend.on("/tools/render_region", MockBackend.Canned.png(TestImages.png64()));
        backend.on("/tools/propose_site", MockBackend.Canned.json(
                "{\"status\":\"pending_confirmation\",\"message\":\"等待玩家确认\"}"));
        rig = new TestRig(backend.baseUrl());
    }

    @AfterEach
    void tearDown() {
        backend.close();
    }

    private MockBackend.Request soleRequest(String path) {
        assertEquals(1, backend.requests().size(), "expected exactly 1 HTTP request");
        MockBackend.Request req = backend.requests().get(0);
        assertEquals(path, req.path());
        assertEquals(TestRig.TOKEN, req.token(), "X-Aibuild-Token header");
        return req;
    }

    @Test
    void fillPostsContractBody() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "fill",
                "{\"min\":[1,2,3],\"max\":[4,5,6],\"block\":\"minecraft:stone_bricks\",\"mode\":\"hollow\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        MockBackend.Request req = soleRequest("/tools/fill");
        assertEquals("POST", req.method());
        assertEquals("application/json", req.contentType());
        JsonNode body = TestRig.MAPPER.readTree(req.body());
        assertEquals("[1,2,3]", body.get("min").toString());
        assertEquals("[4,5,6]", body.get("max").toString());
        assertEquals("minecraft:stone_bricks", body.get("block").asText());
        assertEquals("hollow", body.get("mode").asText());
    }

    @Test
    void fillWithoutModeOmitsIt() throws Exception {
        rig.call(TestRig.toolsCall(1, "fill",
                "{\"min\":[0,0,0],\"max\":[1,1,1],\"block\":\"minecraft:glass\"}"));
        JsonNode body = TestRig.MAPPER.readTree(soleRequest("/tools/fill").body());
        assertFalse(body.has("mode"), "mode is optional; backend defaults to replace");
    }

    @Test
    void setBlocksPostsArray() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks",
                "{\"blocks\":[{\"x\":0,\"y\":64,\"z\":0,\"block\":\"minecraft:oak_planks\"},"
                        + "{\"x\":1,\"y\":64,\"z\":0,\"block\":\"minecraft:torch\"}]}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        MockBackend.Request req = soleRequest("/tools/set_blocks");
        assertEquals("POST", req.method());
        JsonNode body = TestRig.MAPPER.readTree(req.body());
        assertEquals(2, body.get("blocks").size());
        assertEquals("minecraft:torch", body.get("blocks").get(1).get("block").asText());
    }

    @Test
    void setBlockPostsSingle() throws Exception {
        rig.call(TestRig.toolsCall(1, "set_block",
                "{\"x\":1,\"y\":64,\"z\":-2,\"block\":\"minecraft:torch\"}"));
        MockBackend.Request req = soleRequest("/tools/set_block");
        assertEquals("POST", req.method());
        JsonNode body = TestRig.MAPPER.readTree(req.body());
        assertEquals(1, body.get("x").asInt());
        assertEquals(64, body.get("y").asInt());
        assertEquals(-2, body.get("z").asInt());
        assertEquals("minecraft:torch", body.get("block").asText());
    }

    @Test
    void jobStatusUsesGetWithQueryParam() throws Exception {
        rig.call(TestRig.toolsCall(1, "get_job_status", "{\"job_id\":\"job 1/x\"}"));
        MockBackend.Request req = soleRequest("/tools/job_status");
        assertEquals("GET", req.method());
        assertEquals("id=job+1%2Fx", req.query(), "job_id must be URL-encoded in the query string");
    }

    @Test
    void getBlockPostsCoords() throws Exception {
        rig.call(TestRig.toolsCall(1, "get_block", "{\"x\":1,\"y\":2,\"z\":3}"));
        MockBackend.Request req = soleRequest("/tools/get_block");
        assertEquals("POST", req.method());
        assertEquals("{\"x\":1,\"y\":2,\"z\":3}", TestRig.MAPPER.readTree(req.body()).toString());
    }

    @Test
    void regionSummaryPostsBox() throws Exception {
        rig.call(TestRig.toolsCall(1, "get_region_summary",
                "{\"min\":[0,60,0],\"max\":[9,70,9]}"));
        MockBackend.Request req = soleRequest("/tools/get_region_summary");
        assertEquals("POST", req.method());
        JsonNode body = TestRig.MAPPER.readTree(req.body());
        assertEquals("[0,60,0]", body.get("min").toString());
        assertEquals("[9,70,9]", body.get("max").toString());
    }

    @Test
    void terrainSummaryPostsCenterAndRadius() throws Exception {
        rig.call(TestRig.toolsCall(1, "get_terrain_summary",
                "{\"center\":[100,200],\"radius\":64}"));
        MockBackend.Request req = soleRequest("/tools/get_terrain_summary");
        assertEquals("POST", req.method());
        JsonNode body = TestRig.MAPPER.readTree(req.body());
        assertEquals("[100,200]", body.get("center").toString());
        assertEquals(64, body.get("radius").asInt());
    }

    @Test
    void renderRegionPostsBoxAndView() throws Exception {
        rig.call(TestRig.toolsCall(1, "render_region",
                "{\"min\":[0,0,0],\"max\":[9,9,9],\"azimuth\":30,\"elevation\":60}"));
        MockBackend.Request req = soleRequest("/tools/render_region");
        assertEquals("POST", req.method());
        JsonNode body = TestRig.MAPPER.readTree(req.body());
        assertEquals(30, body.get("azimuth").asInt());
        assertEquals(60, body.get("elevation").asInt());
    }

    @Test
    void proposeSitePostsBox() throws Exception {
        rig.call(TestRig.toolsCall(1, "propose_site",
                "{\"min\":[0,0,0],\"max\":[31,15,31]}"));
        MockBackend.Request req = soleRequest("/tools/propose_site");
        assertEquals("POST", req.method());
        JsonNode body = TestRig.MAPPER.readTree(req.body());
        assertEquals("[31,15,31]", body.get("max").toString());
    }

    @Test
    void everyRequestCarriesToken() throws Exception {
        // All requests above asserted the token; here call three different tools in one batch.
        rig.exchange(
                TestRig.toolsCall(1, "set_block", "{\"x\":0,\"y\":0,\"z\":0,\"block\":\"minecraft:stone\"}"),
                TestRig.toolsCall(2, "get_block", "{\"x\":0,\"y\":0,\"z\":0}"),
                TestRig.toolsCall(3, "get_job_status", "{\"job_id\":\"j\"}"));
        assertEquals(3, backend.requests().size());
        for (MockBackend.Request req : backend.requests()) {
            assertEquals(TestRig.TOKEN, req.token());
        }
        String body0 = new String(backend.requests().get(0).body(), StandardCharsets.UTF_8);
        assertTrue(body0.contains("minecraft:stone"));
    }
}
