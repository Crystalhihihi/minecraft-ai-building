package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.StringJoiner;

/**
 * Maps MCP tools/call invocations to aibuild mod HTTP endpoints and maps the
 * responses back to MCP tool results (see docs/specs/bridge-http-api.md).
 */
public final class ToolDispatcher {

    private final McBackendClient backend;
    private final BlocksFilePlacer filePlacer;
    private final ObjectMapper mapper = new ObjectMapper();

    public ToolDispatcher(McBackendClient backend) {
        this.backend = backend;
        this.filePlacer = new BlocksFilePlacer(backend);
    }

    /**
     * Execute a tool call. {@code name} must be a known tool (checked by caller).
     * Never throws for backend problems: failures become isError:true results.
     */
    public ObjectNode call(String name, JsonNode arguments) {
        JsonNode args = (arguments == null || arguments.isNull()) ? mapper.createObjectNode() : arguments;
        try {
            return switch (name) {
                case Tools.FILL -> jsonResult(backend.postJson("/tools/fill", args));
                case Tools.SET_BLOCKS -> setBlocks(args);
                case Tools.SET_BLOCKS_FROM_FILE -> filePlacer.call(args);
                case Tools.SET_BLOCK -> jsonResult(backend.postJson("/tools/set_block", args));
                case Tools.GET_JOB_STATUS -> jsonResult(backend.get("/tools/job_status?id="
                        + URLEncoder.encode(args.path("job_id").asText(""), StandardCharsets.UTF_8)));
                case Tools.GET_BLOCK -> jsonResult(backend.postJson("/tools/get_block", args));
                case Tools.SEARCH_BLOCKS -> searchBlocks(args);
                case Tools.GET_REGION_SUMMARY -> jsonResult(backend.postJson("/tools/get_region_summary", args));
                case Tools.GET_TERRAIN_SUMMARY -> jsonResult(backend.postJson("/tools/get_terrain_summary", args));
                case Tools.RENDER_REGION -> renderResult(backend.postJson("/tools/render_region", args));
                case Tools.PROPOSE_SITE -> jsonResult(backend.postJson("/tools/propose_site", args));
                default -> throw new IllegalArgumentException("unknown tool: " + name);
            };
        } catch (IOException e) {
            return textResult("Failed to reach aibuild mod backend at " + backend.baseUrl()
                    + " (" + e.getClass().getSimpleName() + ": " + e.getMessage() + "). "
                    + "Is the game running with the aibuild mod loaded?", true);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return textResult("Interrupted while calling aibuild mod backend", true);
        }
    }

    private ObjectNode setBlocks(JsonNode args) throws IOException, InterruptedException {
        JsonNode blocks = args.get("blocks");
        if (blocks != null && blocks.isArray() && blocks.size() > Tools.SET_BLOCKS_MAX_ENTRIES) {
            return textResult("set_blocks accepts at most " + Tools.SET_BLOCKS_MAX_ENTRIES
                    + " entries per request, got " + blocks.size()
                    + ". Split the batch into multiple requests.", true);
        }
        return jsonResult(backend.postJson("/tools/set_blocks", args));
    }

    /** search_blocks: POST the query, format the matches array as a readable list. */
    private ObjectNode searchBlocks(JsonNode args) throws IOException, InterruptedException {
        String query = args.path("query").asText("").strip();
        if (query.isEmpty()) {
            return textResult("search_blocks needs a non-empty \"query\" string.", true);
        }
        ObjectNode body = mapper.createObjectNode();
        body.put("query", query);
        McBackendClient.Response resp = backend.postJson("/tools/search_blocks", body);
        if (!resp.isSuccess()) {
            return errorResult(resp);
        }
        JsonNode json = tryParse(new String(resp.body(), StandardCharsets.UTF_8));
        List<String> matches = new ArrayList<>();
        if (json != null && json.path("matches").isArray()) {
            for (JsonNode match : json.path("matches")) {
                matches.add(match.asText());
            }
        }
        String text;
        if (matches.isEmpty()) {
            text = "No blocks match \"" + query + "\".";
        } else {
            StringBuilder sb = new StringBuilder(matches.size() + " block(s) match \"" + query + "\":");
            for (String match : matches) {
                sb.append('\n').append(match);
            }
            text = sb.toString();
        }
        return textResult(appendPlayerMessages(text, json == null ? null : json.get("player_messages")),
                false);
    }

    /** Map a JSON-endpoint response to MCP content. */
    private ObjectNode jsonResult(McBackendClient.Response resp) {
        if (!resp.isSuccess()) {
            return errorResult(resp);
        }
        String bodyText = new String(resp.body(), StandardCharsets.UTF_8);
        JsonNode json = tryParse(bodyText);
        String text;
        JsonNode playerMessages = null;
        if (json != null && json.isObject()) {
            playerMessages = json.get("player_messages");
            JsonNode textField = json.get("text");
            if (textField != null && textField.isTextual()) {
                text = textField.asText();
            } else {
                // player_messages is appended separately below; keep it out of the compact JSON
                if (playerMessages != null && json instanceof ObjectNode objectNode) {
                    objectNode.remove("player_messages");
                }
                text = compact(json);
            }
        } else {
            text = bodyText;
        }
        text = appendPlayerMessages(text, playerMessages);
        return textResult(text, false);
    }

    private String appendPlayerMessages(String text, JsonNode playerMessages) {
        if (playerMessages != null && playerMessages.isArray() && !playerMessages.isEmpty()) {
            StringBuilder sb = new StringBuilder(text);
            for (JsonNode msg : playerMessages) {
                sb.append("\n[玩家消息] ").append(msg.asText());
            }
            return sb.toString();
        }
        return text;
    }

    /** Map a render response: PNG bytes become MCP image content. */
    private ObjectNode renderResult(McBackendClient.Response resp) {
        if (!resp.isSuccess()) {
            return errorResult(resp);
        }
        String contentType = resp.contentType() == null ? "" : resp.contentType().toLowerCase();
        if (contentType.startsWith("image/png")) {
            ObjectNode result = mapper.createObjectNode();
            ArrayNode content = result.putArray("content");
            ObjectNode image = content.addObject();
            image.put("type", "image");
            image.put("data", Base64.getEncoder().encodeToString(resp.body()));
            image.put("mimeType", "image/png");
            result.put("isError", false);
            return result;
        }
        return textResult("Unexpected render response (HTTP " + resp.status() + ", Content-Type "
                + resp.contentType() + "): " + excerpt(resp), true);
    }

    /** HTTP 4xx/5xx -> isError:true with a readable message (400 suggestions listed). */
    private ObjectNode errorResult(McBackendClient.Response resp) {
        StringBuilder sb = new StringBuilder("HTTP ").append(resp.status());
        String bodyText = new String(resp.body(), StandardCharsets.UTF_8);
        JsonNode json = tryParse(bodyText);
        if (json != null && json.isObject()) {
            JsonNode error = json.get("error");
            if (error != null && error.isTextual()) {
                sb.append(": ").append(error.asText());
            }
            JsonNode suggestions = json.get("suggestions");
            if (suggestions != null && suggestions.isArray() && !suggestions.isEmpty()) {
                StringJoiner joiner = new StringJoiner(", ");
                suggestions.forEach(s -> joiner.add(s.asText()));
                sb.append(" (did you mean: ").append(joiner).append("?)");
            }
        } else if (!bodyText.isBlank()) {
            sb.append(": ").append(bodyText.strip());
        }
        return textResult(sb.toString(), true);
    }

    private ObjectNode textResult(String text, boolean isError) {
        ObjectNode result = mapper.createObjectNode();
        ArrayNode content = result.putArray("content");
        ObjectNode item = content.addObject();
        item.put("type", "text");
        item.put("text", text);
        result.put("isError", isError);
        return result;
    }

    private JsonNode tryParse(String body) {
        try {
            return mapper.readTree(body);
        } catch (Exception e) {
            return null;
        }
    }

    private String compact(JsonNode json) {
        try {
            return mapper.writeValueAsString(json);
        } catch (Exception e) {
            return json.toString();
        }
    }

    private String excerpt(McBackendClient.Response resp) {
        String body = new String(resp.body(), StandardCharsets.UTF_8).strip();
        return body.length() <= 200 ? body : body.substring(0, 200) + "...";
    }
}
