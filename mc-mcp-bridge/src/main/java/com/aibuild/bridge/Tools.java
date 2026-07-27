package com.aibuild.bridge;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.List;

/**
 * MCP tool definitions (tools/list). Names and HTTP mapping follow
 * docs/specs/bridge-http-api.md; schemas use closed-interval [x,y,z] boxes.
 */
public final class Tools {

    private Tools() {
    }

    public static final String FILL = "fill";
    public static final String SET_BLOCKS = "set_blocks";
    public static final String SET_BLOCK = "set_block";
    public static final String GET_JOB_STATUS = "get_job_status";
    public static final String GET_BLOCK = "get_block";
    public static final String GET_REGION_SUMMARY = "get_region_summary";
    public static final String GET_TERRAIN_SUMMARY = "get_terrain_summary";
    public static final String RENDER_REGION = "render_region";
    public static final String PROPOSE_SITE = "propose_site";

    public static final int SET_BLOCKS_MAX_ENTRIES = 4096;

    public static List<String> names() {
        return List.of(FILL, SET_BLOCKS, SET_BLOCK, GET_JOB_STATUS, GET_BLOCK,
                GET_REGION_SUMMARY, GET_TERRAIN_SUMMARY, RENDER_REGION, PROPOSE_SITE);
    }

    public static boolean isKnown(String name) {
        return names().contains(name);
    }

    public static ArrayNode definitions(ObjectMapper mapper) {
        ArrayNode tools = mapper.createArrayNode();
        tools.add(tool(mapper, FILL,
                "Fill a closed-interval box [min..max] with a block, like the vanilla /fill command. "
                        + "Asynchronous: returns a job_id; poll get_job_status for placed/failed counts. "
                        + "Coordinates are world block coords, y is up; block is a namespaced id like \"minecraft:stone_bricks\". "
                        + "mode: replace (default), keep (only replace air), outline, hollow.",
                schema(mapper, new String[][]{
                                {"min", "boxCorner"}, {"max", "boxCorner"},
                                {"block", "blockId"}, {"mode", "fillMode"}},
                        "min", "max", "block")));
        tools.add(tool(mapper, SET_BLOCKS,
                "Place many individual blocks in one request (fine-grained edits). "
                        + "Asynchronous: returns a job_id; poll get_job_status. "
                        + "Max " + SET_BLOCKS_MAX_ENTRIES + " entries per request; split larger batches.",
                schema(mapper, new String[][]{{"blocks", "blockList"}}, "blocks")));
        tools.add(tool(mapper, SET_BLOCK,
                "Place a single block at (x,y,z). Asynchronous: returns a job_id. Use for small fixes.",
                schema(mapper, new String[][]{
                                {"x", "coord"}, {"y", "coord"}, {"z", "coord"}, {"block", "blockId"}},
                        "x", "y", "z", "block")));
        tools.add(tool(mapper, GET_JOB_STATUS,
                "Poll progress of an asynchronous write job. Returns state (running|done|failed) "
                        + "plus placed/failed counts; always check after a write to catch partial failures.",
                schema(mapper, new String[][]{{"job_id", "jobId"}}, "job_id")));
        tools.add(tool(mapper, GET_BLOCK,
                "Query the block at a single position. Returns the block id and its block-state properties.",
                schema(mapper, new String[][]{{"x", "coord"}, {"y", "coord"}, {"z", "coord"}},
                        "x", "y", "z")));
        tools.add(tool(mapper, GET_REGION_SUMMARY,
                "Summarize a closed-interval box: block-type counts plus a per-layer ASCII plan. "
                        + "Cheap on tokens; use instead of many get_block calls.",
                schema(mapper, new String[][]{{"min", "boxCorner"}, {"max", "boxCorner"}},
                        "min", "max")));
        tools.add(tool(mapper, GET_TERRAIN_SUMMARY,
                "Summarize terrain around center=[x,z] within radius: height map, water, slope, flatness "
                        + "(with ASCII height map). Use to scout a build site before proposing one.",
                schema(mapper, new String[][]{{"center", "xzCenter"}, {"radius", "radius"}},
                        "center", "radius")));
        tools.add(tool(mapper, RENDER_REGION,
                "Render a closed-interval box to a PNG image (returned as image content) so you can "
                        + "visually inspect your build. azimuth/elevation are degrees, optional, default 45/45. "
                        + "Call after building to self-check proportions and materials.",
                schema(mapper, new String[][]{
                                {"min", "boxCorner"}, {"max", "boxCorner"},
                                {"azimuth", "angle"}, {"elevation", "angle"}},
                        "min", "max")));
        tools.add(tool(mapper, PROPOSE_SITE,
                "Propose a build site (closed-interval box) when the player gave no manual selection. "
                        + "Must be the FIRST tool call in that case; write tools stay locked until the "
                        + "player confirms the site.",
                schema(mapper, new String[][]{{"min", "boxCorner"}, {"max", "boxCorner"}},
                        "min", "max")));
        return tools;
    }

    private static ObjectNode tool(ObjectMapper mapper, String name, String description, ObjectNode inputSchema) {
        ObjectNode tool = mapper.createObjectNode();
        tool.put("name", name);
        tool.put("description", description);
        tool.set("inputSchema", inputSchema);
        return tool;
    }

    /**
     * @param props pairs of {propertyName, kind} where kind selects a prebuilt JSON-Schema fragment
     */
    private static ObjectNode schema(ObjectMapper mapper, String[][] props, String... required) {
        ObjectNode schema = mapper.createObjectNode();
        schema.put("type", "object");
        schema.put("additionalProperties", false);
        ObjectNode properties = schema.putObject("properties");
        for (String[] prop : props) {
            properties.set(prop[0], fragment(mapper, prop[1]));
        }
        ArrayNode req = schema.putArray("required");
        for (String r : required) {
            req.add(r);
        }
        return schema;
    }

    private static ObjectNode fragment(ObjectMapper mapper, String kind) {
        ObjectNode node = mapper.createObjectNode();
        switch (kind) {
            case "boxCorner" -> {
                node.put("type", "array");
                node.put("description", "World block position [x,y,z], integers, y is up. Box bounds are inclusive.");
                node.put("minItems", 3);
                node.put("maxItems", 3);
                node.putObject("items").put("type", "integer");
            }
            case "xzCenter" -> {
                node.put("type", "array");
                node.put("description", "Horizontal center [x,z], integers.");
                node.put("minItems", 2);
                node.put("maxItems", 2);
                node.putObject("items").put("type", "integer");
            }
            case "blockId" -> {
                node.put("type", "string");
                node.put("description", "Namespaced block id, e.g. \"minecraft:stone_bricks\".");
            }
            case "fillMode" -> {
                node.put("type", "string");
                node.put("description", "Fill mode, default \"replace\".");
                ArrayNode e = node.putArray("enum");
                e.add("replace").add("keep").add("outline").add("hollow");
            }
            case "blockList" -> {
                node.put("type", "array");
                node.put("description", "Blocks to place, max " + SET_BLOCKS_MAX_ENTRIES + " entries.");
                node.put("minItems", 1);
                node.put("maxItems", SET_BLOCKS_MAX_ENTRIES);
                ObjectNode item = node.putObject("items");
                item.put("type", "object");
                item.put("additionalProperties", false);
                ObjectNode ip = item.putObject("properties");
                ip.set("x", fragment(mapper, "coord"));
                ip.set("y", fragment(mapper, "coord"));
                ip.set("z", fragment(mapper, "coord"));
                ip.set("block", fragment(mapper, "blockId"));
                ArrayNode ir = item.putArray("required");
                ir.add("x").add("y").add("z").add("block");
            }
            case "coord" -> {
                node.put("type", "integer");
                node.put("description", "World block coordinate.");
            }
            case "jobId" -> {
                node.put("type", "string");
                node.put("description", "Job id returned by a write tool.");
            }
            case "radius" -> {
                node.put("type", "integer");
                node.put("description", "Radius in blocks around the center.");
                node.put("minimum", 1);
            }
            case "angle" -> {
                node.put("type", "number");
                node.put("description", "Degrees; optional, defaults to 45.");
            }
            default -> throw new IllegalArgumentException("unknown schema fragment: " + kind);
        }
        return node;
    }
}
