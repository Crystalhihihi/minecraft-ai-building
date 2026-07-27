package com.aibuild.mod.agent;

import com.aibuild.mod.AiBuildMod;
import com.aibuild.mod.bridge.SiteGate;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
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

    public static void writeTask(Path dir, String description, BlockPos anchor, SiteGate.Bounds bounds) throws IOException {
        JsonObject task = new JsonObject();
        task.addProperty("description", description);
        task.addProperty("anchor", anchor.getX() + " " + anchor.getY() + " " + anchor.getZ());
        if (bounds != null) {
            JsonObject b = new JsonObject();
            b.add("min", vec(bounds.minX(), bounds.minY(), bounds.minZ()));
            b.add("max", vec(bounds.maxX(), bounds.maxY(), bounds.maxZ()));
            task.add("bounds", b);
        }
        task.addProperty("timestamp", Instant.now().toString());
        Files.writeString(dir.resolve("task.json"), GSON.toJson(task) + System.lineSeparator());
    }

    /** Terrain summary around the anchor, generated before spawn (see TerrainSummary). */
    public static void writeTerrain(Path dir, BlockPos anchor, int radius, String text) throws IOException {
        JsonObject terrain = new JsonObject();
        terrain.add("center", vec(anchor.getX(), anchor.getZ()));
        terrain.addProperty("radius", radius);
        terrain.addProperty("text", text);
        Files.writeString(dir.resolve("terrain.json"), GSON.toJson(terrain) + System.lineSeparator());
    }

    private static JsonArray vec(int... values) {
        JsonArray arr = new JsonArray();
        for (int v : values) {
            arr.add(v);
        }
        return arr;
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

            ## Site and bounds (READ CAREFULLY)

            - If `task.json` contains a `bounds` object: that range is a HARD limit
              handed down by the player. Every block you place must be inside it;
              out-of-bounds blocks are recorded as failed (`out_of_bounds`).
            - If `task.json` has NO `bounds`: your FIRST tool call must be
              `propose_site(min, max)` (volume <= 262144, i.e. at most 64x64x64).
              Pick the site from `terrain.json` (see below), near the anchor unless
              the task says otherwise. After proposing, WAIT: write tools return
              `409 site not confirmed` until the player confirms. Poll with a read
              tool (e.g. `get_block` on a corner of the proposed area); the player's
              decision arrives as a `[玩家消息]` line attached to a tool response.
              - Confirmed → build strictly inside the CONFIRMED range.
              - Rejected → propose a DIFFERENT site; do not retry the same box.
            - `terrain.json` (written when the task started) contains a terrain
              summary around the anchor (radius 64): ASCII heightmap, water/tree
              cover, flatness stats and up to 3 flat candidate spots. Use it to
              choose and orient the build. To scout elsewhere, call
              `get_terrain_summary(center, radius)` (radius <= 128).

            ## Tools (MCP server `aibuild`)

            Write tools are ASYNC: they return `job_id` immediately, blocks are
            placed in the background. ALWAYS confirm with `get_job_status` before
            building on top of previous work. Write tools are locked (409) until
            the site is confirmed (see above).

            | tool | use |
            | --- | --- |
            | `fill(min, max, block, mode?)` | main workhorse. mode: replace (default) / keep / outline / hollow |
            | `set_blocks([{x,y,z,block}...])` | batch detail work, <= 4096 entries per call |
            | `set_block(x, y, z, block)` | single-block fixes |
            | `get_job_status(job_id)` | poll until state=done; check placed/failed counts |
            | `get_block(x, y, z)` | point query, returns block id + properties |
            | `get_terrain_summary(center, radius)` | AVAILABLE. ASCII heightmap + water/flatness stats + flat candidates; radius <= 128 |
            | `propose_site(min, max)` | AVAILABLE. Required FIRST call when task.json has no bounds; then await confirmation |
            | `get_region_summary(min, max)` | NOT available in this milestone — will error |
            | `render_region(min, max, azimuth?, elevation?)` | NOT available in this milestone — will error |

            ## Rules

            1. BATCH FIRST. One `fill` beats 100 `set_block` calls. One `set_blocks`
               batch beats 100 singles. Plan the whole shape, then issue few large calls.
            2. Block ids are full namespaced ids, e.g. `minecraft:stone_bricks`.
               Invalid ids come back with suggestions — use them, don't guess wildly.
            3. Before you start, write a short `plan.md` in this directory: shape,
               dimensions, materials, layer-by-layer sketch. Keep it brief.
            4. Build BOTTOM-UP: foundations first, then walls, then roof/details.
               Wait for each job's `get_job_status` = done (and failed == 0) before
               depending on its blocks. If failures say `out_of_bounds`, you placed
               outside the confirmed range — redo those parts inside it.
            5. Self-check when finished: `get_region_summary` if it works, otherwise
               sample key points with `get_block` (corners, center, top) and confirm
               they match the plan. Fix any mismatches.
            6. A tool response may end with `[玩家消息] ...` lines — these are live
               messages from the player. Treat them as instructions and adapt.
            7. Creative-mode semantics: blocks appear out of nowhere, no physics
               worries, floating is allowed but ugly — connect to the ground unless
               the task says otherwise.
            """;
}
