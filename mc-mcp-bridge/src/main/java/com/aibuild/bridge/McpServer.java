package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;

/**
 * Newline-delimited JSON-RPC 2.0 stdio loop (MCP server side).
 *
 * Protocol behavior mirrors the Phase-0 reference implementation
 * (scratch/phase0/mcptest/fake-mcp-server.js, verified against kimi 0.29.2):
 * - one JSON message per line on stdin, one reply per line on stdout, flushed per message
 * - initialize echoes the client's protocolVersion; capabilities only declares {"tools":{}}
 * - notifications/* get no reply; ping replies with {}; ids are echoed verbatim
 * - unknown method -> -32601; unknown tool -> -32602
 * - business errors are normal results with isError:true (handled by ToolDispatcher)
 *
 * stdout carries protocol only; all logging goes to stderr.
 */
public final class McpServer {

    public static final String SERVER_NAME = "mc-mcp-bridge";
    public static final String SERVER_VERSION = "1.0.0";
    static final String DEFAULT_PROTOCOL_VERSION = "2025-06-18";

    private final ObjectMapper mapper = new ObjectMapper();
    private final ToolDispatcher dispatcher;
    private final PrintWriter err;

    public McpServer(ToolDispatcher dispatcher, PrintWriter err) {
        this.dispatcher = dispatcher;
        this.err = err;
    }

    /** Serve requests until stdin EOF. Sequential: each line is handled before the next is read. */
    public void serve(InputStream in, OutputStream out) throws IOException {
        BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(out, StandardCharsets.UTF_8));
        String line;
        while ((line = reader.readLine()) != null) {
            line = line.trim();
            if (line.isEmpty()) {
                continue;
            }
            JsonNode msg;
            try {
                msg = mapper.readTree(line);
            } catch (Exception e) {
                err.println("[mc-mcp-bridge] bad json line, ignored");
                err.flush();
                continue;
            }
            ObjectNode response = handle(msg);
            if (response != null) {
                writer.write(mapper.writeValueAsString(response));
                writer.newLine();
                writer.flush();
            }
        }
    }

    /** @return the response object, or null when no reply should be sent (notifications etc.) */
    ObjectNode handle(JsonNode msg) {
        JsonNode id = msg.get("id");
        String method = msg.path("method").asText("");
        err.println("[mc-mcp-bridge] recv method=" + (method.isEmpty() ? "(response)" : method));
        err.flush();

        switch (method) {
            case "initialize" -> {
                String clientVersion = msg.path("params").path("protocolVersion").asText(null);
                ObjectNode result = mapper.createObjectNode();
                result.put("protocolVersion",
                        clientVersion != null && !clientVersion.isEmpty() ? clientVersion : DEFAULT_PROTOCOL_VERSION);
                result.putObject("capabilities").putObject("tools");
                ObjectNode serverInfo = result.putObject("serverInfo");
                serverInfo.put("name", SERVER_NAME);
                serverInfo.put("version", SERVER_VERSION);
                return result(id, result);
            }
            case "ping" -> {
                return result(id, mapper.createObjectNode());
            }
            case "tools/list" -> {
                ObjectNode result = mapper.createObjectNode();
                result.set("tools", Tools.definitions(mapper));
                return result(id, result);
            }
            case "tools/call" -> {
                JsonNode params = msg.path("params");
                String name = params.path("name").asText("");
                if (!Tools.isKnown(name)) {
                    return error(id, -32602, "Unknown tool: " + name);
                }
                return result(id, dispatcher.call(name, params.get("arguments")));
            }
            default -> {
                if (method.startsWith("notifications/")) {
                    return null; // notifications get no reply
                }
                if (id != null && !id.isNull()) {
                    return error(id, -32601, "Method not found: " + method);
                }
                return null;
            }
        }
    }

    private ObjectNode result(JsonNode id, JsonNode result) {
        ObjectNode response = mapper.createObjectNode();
        response.put("jsonrpc", "2.0");
        response.set("id", id);
        response.set("result", result);
        return response;
    }

    private ObjectNode error(JsonNode id, int code, String message) {
        ObjectNode response = mapper.createObjectNode();
        response.put("jsonrpc", "2.0");
        response.set("id", id);
        ObjectNode error = response.putObject("error");
        error.put("code", code);
        error.put("message", message);
        return response;
    }
}
