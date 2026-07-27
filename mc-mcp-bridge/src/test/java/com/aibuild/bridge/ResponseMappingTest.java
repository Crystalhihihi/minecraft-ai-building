package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Mod JSON -> MCP text: "text" field wins, otherwise compact JSON; player_messages appended. */
class ResponseMappingTest {

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

    private JsonNode textContent(JsonNode resp) {
        JsonNode result = resp.get("result");
        assertEquals("text", result.get("content").get(0).get("type").asText());
        return result;
    }

    @Test
    void textFieldIsUsedAsToolText() throws Exception {
        backend.on("/tools/get_region_summary", MockBackend.Canned.json(
                "{\"text\":\"方块统计: stone x100\\n第64层: ###\"}"));
        JsonNode result = textContent(rig.call(TestRig.toolsCall(1, "get_region_summary",
                "{\"min\":[0,0,0],\"max\":[9,9,9]}")));
        assertFalse(result.get("isError").asBoolean());
        String text = result.get("content").get(0).get("text").asText();
        assertTrue(text.contains("方块统计: stone x100"), "Chinese text must survive UTF-8 round-trip");
        assertTrue(text.contains("###"));
    }

    @Test
    void jsonWithoutTextFieldBecomesCompactJson() throws Exception {
        backend.on("/tools/fill", MockBackend.Canned.json("{\"job_id\":\"mock-1\"}"));
        JsonNode result = textContent(rig.call(TestRig.toolsCall(1, "fill",
                "{\"min\":[0,0,0],\"max\":[1,1,1],\"block\":\"minecraft:stone\"}")));
        assertEquals("{\"job_id\":\"mock-1\"}", result.get("content").get(0).get("text").asText());
    }

    @Test
    void playerMessagesAreAppendedWithPrefix() throws Exception {
        backend.on("/tools/get_block", MockBackend.Canned.json(
                "{\"block\":\"minecraft:stone\",\"player_messages\":[\"加油\",\"换个颜色\"]}"));
        JsonNode result = textContent(rig.call(TestRig.toolsCall(1, "get_block",
                "{\"x\":0,\"y\":64,\"z\":0}")));
        String text = result.get("content").get(0).get("text").asText();
        assertTrue(text.startsWith("{\"block\":\"minecraft:stone\"}"), text);
        assertTrue(text.contains("[玩家消息] 加油"), text);
        assertTrue(text.contains("[玩家消息] 换个颜色"), text);
    }

    @Test
    void playerMessagesAppendedToTextFieldToo() throws Exception {
        backend.on("/tools/get_region_summary", MockBackend.Canned.json(
                "{\"text\":\"summary\",\"player_messages\":[\"盖高一点\"]}"));
        JsonNode result = textContent(rig.call(TestRig.toolsCall(1, "get_region_summary",
                "{\"min\":[0,0,0],\"max\":[1,1,1]}")));
        assertEquals("summary\n[玩家消息] 盖高一点", result.get("content").get(0).get("text").asText());
    }

    @Test
    void proposeSitePendingConfirmationPassesThrough() throws Exception {
        backend.on("/tools/propose_site", MockBackend.Canned.json(
                "{\"status\":\"pending_confirmation\",\"message\":\"等待玩家确认\"}"));
        JsonNode result = textContent(rig.call(TestRig.toolsCall(1, "propose_site",
                "{\"min\":[0,0,0],\"max\":[9,9,9]}")));
        assertFalse(result.get("isError").asBoolean());
        String text = result.get("content").get(0).get("text").asText();
        assertTrue(text.contains("pending_confirmation"), text);
        assertTrue(text.contains("等待玩家确认"), text);
    }
}
