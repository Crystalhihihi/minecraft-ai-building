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
    public static final String SET_BLOCKS_FROM_FILE = "set_blocks_from_file";
    public static final String SET_BLOCK = "set_block";
    public static final String GET_JOB_STATUS = "get_job_status";
    public static final String GET_BLOCK = "get_block";
    public static final String SEARCH_BLOCKS = "search_blocks";
    public static final String GET_REGION_SUMMARY = "get_region_summary";
    public static final String GET_TERRAIN_SUMMARY = "get_terrain_summary";
    public static final String RENDER_REGION = "render_region";
    public static final String PROPOSE_SITE = "propose_site";
    public static final String ASK_PLAYER = "ask_player";

    public static final int SET_BLOCKS_MAX_ENTRIES = 4096;

    public static List<String> names() {
        return List.of(FILL, SET_BLOCKS, SET_BLOCKS_FROM_FILE, SET_BLOCK, GET_JOB_STATUS, GET_BLOCK,
                SEARCH_BLOCKS, GET_REGION_SUMMARY, GET_TERRAIN_SUMMARY, RENDER_REGION, PROPOSE_SITE,
                ASK_PLAYER);
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
                        + "Max " + SET_BLOCKS_MAX_ENTRIES + " entries per request; split larger batches. "
                        + "For more than a few hundred blocks prefer set_blocks_from_file instead.",
                schema(mapper, new String[][]{{"blocks", "blockList"}}, "blocks")));
        tools.add(tool(mapper, SET_BLOCKS_FROM_FILE,
                "Place many blocks from a local file - the recommended channel for large or procedural "
                        + "builds: write a small generator script (any language) that computes the geometry "
                        + "and emits the file, then call this tool once instead of many set_blocks calls. "
                        + "The bridge streams the file to the mod in batches of " + SET_BLOCKS_MAX_ENTRIES
                        + " set_blocks jobs and blocks until every job finishes, reporting placed/failed totals. "
                        + "path: a JSON file ({\"blocks\":[{\"x\":..,\"y\":..,\"z\":..,\"block\":\"minecraft:...\"}]}"
                        + " or a bare array of such entries) or a .schem file (Sponge Schematic v2/v3, "
                        + "e.g. WorldEdit //schem save). For .schem: air entries are skipped unless "
                        + "place_air=true; the file's Offset is used as placement origin unless the offset "
                        + "argument is given (explicit wins); block entities are ignored.",
                schema(mapper, new String[][]{
                                {"path", "filePath"}, {"offset", "offsetVec"}, {"place_air", "placeAir"}},
                        "path")));
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
        tools.add(tool(mapper, SEARCH_BLOCKS,
                "Search block ids by substring (fuzzy, up to 16 matches). Use it to find the exact "
                        + "namespaced id before building when unsure - e.g. \"stained_glass\" returns "
                        + "minecraft:white_stained_glass etc. Empty list means no match.",
                schema(mapper, new String[][]{{"query", "query"}}, "query")));
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
                        + "mode: auto (default; GL render when a client is available, else top-down), gl, or "
                        + "topdown (server-side map-style raster, always works). projection: persp (default) or "
                        + "ortho (GL mode only). Call after building to self-check proportions and materials.",
                schema(mapper, new String[][]{
                                {"min", "boxCorner"}, {"max", "boxCorner"},
                                {"azimuth", "angle"}, {"elevation", "angle"},
                                {"mode", "renderMode"}, {"projection", "renderProjection"}},
                        "min", "max")));
        tools.add(tool(mapper, PROPOSE_SITE,
                "Propose a build site (closed-interval box) when the player gave no manual selection. "
                        + "Must be the FIRST tool call in that case; write tools stay locked until the "
                        + "player confirms the site.",
                schema(mapper, new String[][]{{"min", "boxCorner"}, {"max", "boxCorner"}},
                        "min", "max")));
        tools.add(tool(mapper, ASK_PLAYER,
                "Ask the player ONE question and WAIT for the answer. The question appears in the "
                        + "game chat with clickable option buttons; the player's reply (clicked option "
                        + "or free text) comes back as this tool's result. Exactly ONE question per "
                        + "call — an answer can change what you ask next, so never batch. Each call "
                        + "waits ~60 s; on status \"waiting\" call again with the SAME question to "
                        + "keep waiting — waiting has no limit, NEVER give up just because the player "
                        + "is slow. Only when the player says 跳过/随便/你定 may you stop asking.",
                schema(mapper, new String[][]{{"questions", "questionList"}}, "questions")));
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
            case "renderMode" -> {
                node.put("type", "string");
                node.put("description", "Render path, default \"auto\": GL render when the game client is "
                        + "available (single player), otherwise the top-down raster; \"gl\" and \"topdown\" "
                        + "force a path (gl still falls back to topdown when no client is available).");
                ArrayNode e = node.putArray("enum");
                e.add("auto").add("gl").add("topdown");
            }
            case "renderProjection" -> {
                node.put("type", "string");
                node.put("description", "Camera projection for the GL render path, default \"persp\".");
                ArrayNode e = node.putArray("enum");
                e.add("persp").add("ortho");
            }
            case "filePath" -> {
                node.put("type", "string");
                node.put("description", "Path to a block file on the machine running the bridge: a JSON "
                        + "block list or a .schem file (Sponge Schematic v2/v3). Relative paths resolve "
                        + "against the bridge process working directory.");
            }
            case "offsetVec" -> {
                node.put("type", "array");
                node.put("description", "Placement origin offset [x,y,z], integers, added to every block "
                        + "position. Optional; overrides the file's own Offset for .schem files.");
                node.put("minItems", 3);
                node.put("maxItems", 3);
                node.putObject("items").put("type", "integer");
            }
            case "placeAir" -> {
                node.put("type", "boolean");
                node.put("description", "Also place air blocks from .schem files. Optional, default false "
                        + "(air entries are skipped).");
            }
            case "query" -> {
                node.put("type", "string");
                node.put("description", "Substring to match against block ids, e.g. \"stained_glass\".");
            }
            case "questionList" -> {
                node.put("type", "array");
                node.put("description", "Exactly ONE question (answers can change later questions, "
                        + "so never batch). May carry up to 6 clickable options.");
                node.put("minItems", 1);
                node.put("maxItems", 1);
                ObjectNode item = node.putObject("items");
                item.put("type", "object");
                item.put("additionalProperties", false);
                ObjectNode ip = item.putObject("properties");
                ObjectNode q = mapper.createObjectNode();
                q.put("type", "string");
                q.put("description", "The question text, e.g. \"想要什么风格?\".");
                ip.set("q", q);
                ObjectNode options = mapper.createObjectNode();
                options.put("type", "array");
                options.put("description", "Clickable answer options shown as buttons, max 6. "
                        + "Free-text answers are always possible, so options are conveniences, not a closed set.");
                options.put("maxItems", 6);
                options.putObject("items").put("type", "string");
                ip.set("options", options);
                ArrayNode ir = item.putArray("required");
                ir.add("q");
            }
            default -> throw new IllegalArgumentException("unknown schema fragment: " + kind);
        }
        return node;
    }
}
