package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** tools/list: all 12 tools present, each with a usable description and valid JSON Schema object. */
class ToolsListTest {

    private final TestRig rig = new TestRig("http://127.0.0.1:1");

    @Test
    void listsAllTwelveTools() throws Exception {
        JsonNode resp = rig.call("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}");
        JsonNode tools = resp.get("result").get("tools");
        assertEquals(12, tools.size());
        Set<String> names = new HashSet<>();
        tools.forEach(t -> names.add(t.get("name").asText()));
        assertEquals(Set.of("fill", "set_blocks", "set_blocks_from_file", "set_block", "get_job_status",
                "get_block", "search_blocks", "get_region_summary", "get_terrain_summary",
                "render_region", "propose_site", "ask_player"), names);
    }

    @Test
    void everyToolHasDescriptionAndValidInputSchema() throws Exception {
        JsonNode resp = rig.call("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}");
        for (JsonNode tool : resp.get("result").get("tools")) {
            String name = tool.get("name").asText();
            assertTrue(tool.hasNonNull("description") && !tool.get("description").asText().isBlank(),
                    name + " needs a description");
            JsonNode schema = tool.get("inputSchema");
            assertTrue(schema != null && schema.isObject(), name + " inputSchema must be an object");
            assertEquals("object", schema.get("type").asText(), name + " schema type");
            assertTrue(schema.has("properties") && schema.get("properties").isObject(),
                    name + " schema needs properties");
            assertTrue(schema.has("required") && schema.get("required").isArray(),
                    name + " schema needs a required array");
            for (var it = schema.get("properties").fields(); it.hasNext(); ) {
                var prop = it.next();
                assertTrue(prop.getValue().has("type"), name + "." + prop.getKey() + " needs a type");
            }
        }
    }

    @Test
    void setBlocksSchemaCapsBatchAt4096() throws Exception {
        JsonNode resp = rig.call("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}");
        for (JsonNode tool : resp.get("result").get("tools")) {
            if (tool.get("name").asText().equals("set_blocks")) {
                JsonNode blocks = tool.get("inputSchema").get("properties").get("blocks");
                assertEquals(4096, blocks.get("maxItems").asInt());
                return;
            }
        }
        throw new AssertionError("set_blocks tool not found");
    }
}
