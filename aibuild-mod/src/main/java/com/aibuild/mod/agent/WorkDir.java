package com.aibuild.mod.agent;

import com.aibuild.mod.AiBuildMod;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.storage.LevelResource;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;

/**
 * Prepares and maintains the per-world agent working directory at
 * {@code <world>/aibuild/}: MCP config pointing at the bundled bridge jar,
 * the AGENTS.md construction manual, the per-task task.json, and the
 * extracted mc-mcp-bridge.jar.
 */
public final class WorkDir {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final String BRIDGE_JAR_RESOURCE = "/assets/aibuild/mc-mcp-bridge.jar";
    private static final String BRIDGE_JAR_NAME = "mc-mcp-bridge.jar";

    private WorkDir() {
    }

    public static Path dirOf(MinecraftServer server) {
        return server.getWorldPath(LevelResource.ROOT).resolve("aibuild");
    }

    /**
     * Ensures the working directory is fully set up for the current server
     * session (mcp.json is rewritten every call because the bridge port/token
     * change on every server start). Returns the directory.
     */
    public static Path prepare(MinecraftServer server, int bridgePort, String bridgeToken) throws IOException {
        Path dir = dirOf(server);
        Files.createDirectories(dir.resolve(".kimi-code"));
        Files.createDirectories(dir.resolve("logs"));
        extractBridgeJar(dir);
        writeMcpJson(dir, bridgePort, bridgeToken);
        Files.writeString(dir.resolve("AGENTS.md"), AGENTS_MD);
        return dir;
    }

    public static void writeTask(Path dir, String description, BlockPos anchor) throws IOException {
        JsonObject task = new JsonObject();
        task.addProperty("description", description);
        task.addProperty("anchor", anchor.getX() + " " + anchor.getY() + " " + anchor.getZ());
        task.addProperty("timestamp", Instant.now().toString());
        Files.writeString(dir.resolve("task.json"), GSON.toJson(task) + System.lineSeparator());
    }

    private static void extractBridgeJar(Path dir) throws IOException {
        Path target = dir.resolve(BRIDGE_JAR_NAME);
        byte[] bytes;
        try (InputStream in = WorkDir.class.getResourceAsStream(BRIDGE_JAR_RESOURCE)) {
            if (in == null) {
                throw new IOException("bundled resource " + BRIDGE_JAR_RESOURCE + " missing from mod jar");
            }
            bytes = in.readAllBytes();
        }
        if (Files.isRegularFile(target) && Files.size(target) == bytes.length) {
            return; // already extracted, same size
        }
        Files.write(target, bytes);
        AiBuildMod.LOGGER.info("[aibuild] extracted bridge jar to {}", target);
    }

    private static void writeMcpJson(Path dir, int port, String token) throws IOException {
        JsonObject args = new JsonObject();
        String jar = dir.resolve(BRIDGE_JAR_NAME).toAbsolutePath().toString();
        JsonObject server = new JsonObject();
        server.addProperty("command", "java");
        com.google.gson.JsonArray argv = new com.google.gson.JsonArray();
        argv.add("-jar");
        argv.add(jar);
        argv.add("--port");
        argv.add(String.valueOf(port));
        argv.add("--token");
        argv.add(token);
        server.add("args", argv);
        JsonObject servers = new JsonObject();
        servers.add("aibuild", server);
        JsonObject root = new JsonObject();
        root.add("mcpServers", servers);
        Files.writeString(dir.resolve(".kimi-code").resolve("mcp.json"), GSON.toJson(root) + System.lineSeparator());
    }

    /** Construction manual loaded automatically by the agent CLI at startup. */
    private static final String AGENTS_MD = """
            # aibuild — Minecraft Construction Manual

            You are a building agent working inside a Minecraft world. You build by
            calling the `aibuild` MCP tools; you have no eyes and no body, only the
            tools. The current task is in `task.json` in this directory — read it
            first. `task.json` is authoritative: build what `description` says.

            ## Coordinates

            - +x = east, -x = west; +y = up; +z = south, -z = north.
            - Every box is given as `min:[x,y,z]` / `max:[x,y,z]`, both INCLUSIVE.
              Example: min [0,200,0], max [4,204,4] is a solid 5x5x5 cube (125 blocks).
            - `anchor` in task.json is the reference point chosen by the player.
              The build must stay within 16 blocks of the anchor (chebyshev distance
              on x/z; y may go up/down as needed within reason).

            ## Tools (MCP server `aibuild`)

            Write tools are ASYNC: they return `job_id` immediately, blocks are
            placed in the background. ALWAYS confirm with `get_job_status` before
            building on top of previous work.

            | tool | use |
            | --- | --- |
            | `fill(min, max, block, mode?)` | main workhorse. mode: replace (default) / keep / outline / hollow |
            | `set_blocks([{x,y,z,block}...])` | batch detail work, <= 4096 entries per call |
            | `set_block(x, y, z, block)` | single-block fixes |
            | `get_job_status(job_id)` | poll until state=done; check placed/failed counts |
            | `get_block(x, y, z)` | point query, returns block id + properties |
            | `get_region_summary(min, max)` | block stats + per-layer ASCII plan (NOT available in this milestone — will error) |
            | `get_terrain_summary(center, radius)` | heightmap/slope summary (NOT available in this milestone — will error) |
            | `render_region(min, max, azimuth?, elevation?)` | PNG render (NOT available in this milestone — will error) |
            | `propose_site(min, max)` | site proposal flow (NOT available in this milestone — do not call) |

            ## Rules

            1. BATCH FIRST. One `fill` beats 100 `set_block` calls. One `set_blocks`
               batch beats 100 singles. Plan the whole shape, then issue few large calls.
            2. Block ids are full namespaced ids, e.g. `minecraft:stone_bricks`.
               Invalid ids come back with suggestions — use them, don't guess wildly.
            3. Before you start, write a short `plan.md` in this directory: shape,
               dimensions, materials, layer-by-layer sketch. Keep it brief.
            4. Build BOTTOM-UP: foundations first, then walls, then roof/details.
               Wait for each job's `get_job_status` = done (and failed == 0) before
               depending on its blocks.
            5. Self-check when finished: `get_region_summary` if it works, otherwise
               sample key points with `get_block` (corners, center, top) and confirm
               they match the plan. Fix any mismatches.
            6. A tool response may end with `[玩家消息] ...` lines — these are live
               messages from the player. Treat them as instructions and adapt.
            7. The world is superflat creative-mode semantics: blocks appear out of
               nowhere, no physics worries, floating is allowed but ugly — connect
               to the ground unless the task says otherwise.
            """;
}
