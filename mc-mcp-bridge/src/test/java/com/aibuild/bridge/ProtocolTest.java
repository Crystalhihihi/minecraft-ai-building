package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Protocol layer: JSON-RPC framing, initialize, ping, notifications, ids, unknown methods/tools. */
class ProtocolTest {

    // Never actually called by these tests; protocol handling needs no backend.
    private final TestRig rig = new TestRig("http://127.0.0.1:1");

    @Test
    void initializeEchoesClientProtocolVersion() throws Exception {
        JsonNode resp = rig.call("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\","
                + "\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},"
                + "\"clientInfo\":{\"name\":\"kimi\",\"version\":\"0.29.2\"}}}");
        assertEquals("2.0", resp.get("jsonrpc").asText());
        assertEquals(1, resp.get("id").asInt());
        JsonNode result = resp.get("result");
        assertEquals("2024-11-05", result.get("protocolVersion").asText());
        assertTrue(result.get("capabilities").has("tools"));
        assertEquals(1, result.get("capabilities").size(), "capabilities must only declare tools");
        assertEquals(McpServer.SERVER_NAME, result.get("serverInfo").get("name").asText());
    }

    @Test
    void initializeFallsBackToDefaultVersion() throws Exception {
        JsonNode resp = rig.call("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"initialize\",\"params\":{}}");
        assertEquals(McpServer.DEFAULT_PROTOCOL_VERSION, resp.get("result").get("protocolVersion").asText());
    }

    @Test
    void numericAndStringIdsAreEchoedVerbatim() throws Exception {
        JsonNode numeric = rig.call("{\"jsonrpc\":\"2.0\",\"id\":42,\"method\":\"ping\"}");
        assertTrue(numeric.get("id").isNumber());
        assertEquals(42, numeric.get("id").asInt());

        JsonNode string = rig.call("{\"jsonrpc\":\"2.0\",\"id\":\"req-abc-123\",\"method\":\"ping\"}");
        assertTrue(string.get("id").isTextual());
        assertEquals("req-abc-123", string.get("id").asText());
    }

    @Test
    void notificationsGetNoReply() throws Exception {
        List<JsonNode> responses = rig.exchange(
                "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}",
                "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/cancelled\",\"params\":{\"requestId\":1}}",
                "{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"ping\"}");
        assertEquals(1, responses.size(), "only the ping may produce output");
        assertEquals(7, responses.get(0).get("id").asInt());
    }

    @Test
    void pingReturnsEmptyObject() throws Exception {
        JsonNode resp = rig.call("{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"ping\"}");
        assertTrue(resp.has("result"));
        assertEquals(0, resp.get("result").size());
        assertFalse(resp.has("error"));
    }

    @Test
    void unknownMethodReturns32601() throws Exception {
        JsonNode resp = rig.call("{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"resources/list\"}");
        assertEquals(-32601, resp.get("error").get("code").asInt());
        assertTrue(resp.get("error").get("message").asText().contains("resources/list"));
    }

    @Test
    void unknownToolReturns32602() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(5, "nope_not_a_tool", "{}"));
        assertEquals(-32602, resp.get("error").get("code").asInt());
        assertTrue(resp.get("error").get("message").asText().contains("nope_not_a_tool"));
    }

    @Test
    void malformedJsonLineIsIgnored() throws Exception {
        List<JsonNode> responses = rig.exchange(
                "{this is not json",
                "{\"jsonrpc\":\"2.0\",\"id\":8,\"method\":\"ping\"}");
        assertEquals(1, responses.size());
        assertEquals(8, responses.get(0).get("id").asInt());
    }
}
