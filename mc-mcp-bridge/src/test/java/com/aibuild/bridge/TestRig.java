package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

/** Feeds request lines through McpServer (batch mode, sequential) and parses the output lines. */
final class TestRig {

    static final String TOKEN = "test-token-123";
    static final ObjectMapper MAPPER = new ObjectMapper();

    final McpServer server;

    TestRig(String baseUrl) {
        McBackendClient backend = new McBackendClient(new BridgeConfig(baseUrl, TOKEN, 5_000));
        server = new McpServer(new ToolDispatcher(backend), new PrintWriter(new StringWriter(), true));
    }

    /** Send request lines, return parsed response objects. Every stdout line must parse as JSON. */
    List<JsonNode> exchange(String... lines) throws Exception {
        String input = String.join("\n", lines) + "\n";
        ByteArrayInputStream in = new ByteArrayInputStream(input.getBytes(StandardCharsets.UTF_8));
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        server.serve(in, out);
        String output = out.toString(StandardCharsets.UTF_8);
        List<JsonNode> responses = new ArrayList<>();
        for (String line : output.split("\n")) {
            if (line.isBlank()) {
                continue;
            }
            try {
                responses.add(MAPPER.readTree(line));
            } catch (Exception e) {
                fail("stdout line is not valid JSON: " + line);
            }
        }
        return responses;
    }

    /** Convenience: one request, exactly one response. */
    JsonNode call(String requestLine) throws Exception {
        List<JsonNode> responses = exchange(requestLine);
        assertTrue(responses.size() == 1, "expected exactly 1 response, got " + responses.size());
        return responses.get(0);
    }

    static String toolsCall(int id, String name, String argumentsJson) {
        return "{\"jsonrpc\":\"2.0\",\"id\":" + id + ",\"method\":\"tools/call\",\"params\":{\"name\":\""
                + name + "\",\"arguments\":" + argumentsJson + "}}";
    }

    static String toolsCall(String id, String name, String argumentsJson) {
        return "{\"jsonrpc\":\"2.0\",\"id\":\"" + id + "\",\"method\":\"tools/call\",\"params\":{\"name\":\""
                + name + "\",\"arguments\":" + argumentsJson + "}}";
    }
}
