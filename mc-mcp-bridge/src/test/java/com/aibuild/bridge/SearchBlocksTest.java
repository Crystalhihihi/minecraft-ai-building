package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** search_blocks: POST /tools/search_blocks {"query":...} and format the matches list as text. */
class SearchBlocksTest {

    private MockBackend backend;
    private TestRig rig;

    @BeforeEach
    void setUp() throws Exception {
        backend = new MockBackend();
        backend.on("/tools/search_blocks", MockBackend.Canned.json(
                "{\"matches\":[\"minecraft:white_stained_glass\",\"minecraft:orange_stained_glass\"]}"));
        rig = new TestRig(backend.baseUrl());
    }

    @AfterEach
    void tearDown() {
        backend.close();
    }

    private static String textOf(JsonNode resp) {
        return resp.get("result").get("content").get(0).get("text").asText();
    }

    @Test
    void postsQueryAndFormatsMatches() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "search_blocks", "{\"query\":\"stained_glass\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        assertEquals(1, backend.requests().size());
        MockBackend.Request req = backend.requests().get(0);
        assertEquals("/tools/search_blocks", req.path());
        assertEquals("POST", req.method());
        assertEquals(TestRig.TOKEN, req.token());
        assertEquals("{\"query\":\"stained_glass\"}",
                TestRig.MAPPER.readTree(req.body()).toString());
        String text = textOf(resp);
        assertTrue(text.startsWith("2 block(s) match \"stained_glass\":"), text);
        assertTrue(text.contains("minecraft:white_stained_glass"), text);
        assertTrue(text.contains("minecraft:orange_stained_glass"), text);
    }

    @Test
    void emptyMatchListReadsAsNoMatches() throws Exception {
        backend.on("/tools/search_blocks", MockBackend.Canned.json("{\"matches\":[]}"));
        JsonNode resp = rig.call(TestRig.toolsCall(1, "search_blocks", "{\"query\":\"unobtainium\"}"));
        assertFalse(resp.get("result").get("isError").asBoolean());
        assertEquals("No blocks match \"unobtainium\".", textOf(resp));
    }

    @Test
    void backendErrorBecomesIsError() throws Exception {
        backend.on("/tools/search_blocks", MockBackend.Canned.json(500, "{\"error\":\"boom\"}"));
        JsonNode resp = rig.call(TestRig.toolsCall(1, "search_blocks", "{\"query\":\"glass\"}"));
        assertTrue(resp.get("result").get("isError").asBoolean());
        assertTrue(textOf(resp).contains("HTTP 500: boom"), textOf(resp));
    }

    @Test
    void blankQueryRejectedLocallyWithoutHttp() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "search_blocks", "{\"query\":\"  \"}"));
        assertTrue(resp.get("result").get("isError").asBoolean());
        assertTrue(textOf(resp).contains("query"), textOf(resp));
        assertEquals(0, backend.requests().size(), "no HTTP request may be sent");
    }
}
