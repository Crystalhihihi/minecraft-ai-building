package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

/** HTTP errors and network failures must surface as isError:true results with readable text. */
class ErrorMappingTest {

    private MockBackend backend;
    private TestRig rig;

    @BeforeEach
    void setUp() throws Exception {
        backend = new MockBackend();
        rig = new TestRig(backend.baseUrl());
    }

    @AfterEach
    void tearDown() {
        backend.close();
    }

    private String callForError(String tool, String args) throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, tool, args));
        JsonNode result = resp.get("result");
        assertTrue(result.get("isError").asBoolean(), "expected isError:true, got: " + resp);
        assertTrue(resp.get("error") == null, "business errors must be results, not JSON-RPC errors");
        JsonNode content = result.get("content").get(0);
        return content.get("text").asText();
    }

    @Test
    void forbidden403() throws Exception {
        backend.on("/tools/fill", MockBackend.Canned.json(403, "{\"error\":\"forbidden\"}"));
        String text = callForError("fill", "{\"min\":[0,0,0],\"max\":[1,1,1],\"block\":\"minecraft:stone\"}");
        assertTrue(text.contains("403"), text);
        assertTrue(text.contains("forbidden"), text);
    }

    @Test
    void badRequest400WithSuggestions() throws Exception {
        backend.on("/tools/set_block", MockBackend.Canned.json(400,
                "{\"error\":\"unknown block id: minecraft:stone_brikcs\","
                        + "\"suggestions\":[\"minecraft:stone_bricks\",\"minecraft:stone\"]}"));
        String text = callForError("set_block", "{\"x\":0,\"y\":0,\"z\":0,\"block\":\"minecraft:stone_brikcs\"}");
        assertTrue(text.contains("400"), text);
        assertTrue(text.contains("unknown block id"), text);
        assertTrue(text.contains("minecraft:stone_bricks"), "suggestions must be listed: " + text);
    }

    @Test
    void conflict409() throws Exception {
        backend.on("/tools/fill", MockBackend.Canned.json(409, "{\"error\":\"site not confirmed\"}"));
        String text = callForError("fill", "{\"min\":[0,0,0],\"max\":[1,1,1],\"block\":\"minecraft:stone\"}");
        assertTrue(text.contains("409"), text);
        assertTrue(text.contains("site not confirmed"), text);
    }

    @Test
    void internalError500() throws Exception {
        backend.on("/tools/get_block", MockBackend.Canned.json(500, "{\"error\":\"world not loaded\"}"));
        String text = callForError("get_block", "{\"x\":0,\"y\":0,\"z\":0}");
        assertTrue(text.contains("500"), text);
        assertTrue(text.contains("world not loaded"), text);
    }

    @Test
    void connectionRefusedIsReadableError() throws Exception {
        backend.close(); // nothing listening now
        String text = callForError("get_block", "{\"x\":0,\"y\":0,\"z\":0}");
        assertTrue(text.contains(backend.baseUrl()), "error should name the backend URL: " + text);
        assertTrue(text.toLowerCase().contains("fail") || text.contains("mod"), text);
    }
}
