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
import java.util.List;

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
    private static final String DEFAULTS_RESOURCE_ROOT = "/assets/aibuild/defaults/";
    /**
     * Content assets (style cards, pattern generators + parameter cards, the
     * block-id cheat sheet) shipped inside the mod jar and released to the
     * working directory on prepare(). Write-if-absent: files the user or the
     * agent edited in the work dir are NEVER overwritten.
     */
    private static final List<String> DEFAULT_ASSETS = List.of(
            "styles/medieval_tower.json",
            "styles/plains_cabin.json",
            "styles/waterfront_dock.json",
            "styles/stilt_house.json",
            "styles/nordic_villa.json",
            "patterns/gable_roof.py",
            "patterns/gable_roof.json",
            "patterns/hip_roof.py",
            "patterns/hip_roof.json",
            "patterns/crenellation.py",
            "patterns/crenellation.json",
            "patterns/buttress.py",
            "patterns/buttress.json",
            "patterns/arch_window.py",
            "patterns/arch_window.json",
            "patterns/road_segment.py",
            "patterns/road_segment.json",
            "patterns/terraform_pad.py",
            "patterns/terraform_pad.json",
            "patterns/quadruped_statue.py",
            "patterns/quadruped_statue.json",
            "blocks.md");

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
        extractDefaults(dir);
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

    /**
     * Releases the bundled default assets (styles/, patterns/, blocks.md) into
     * the working directory. Write-if-absent: an existing file is left
     * untouched so user/agent edits and self-saved style cards survive.
     */
    private static void extractDefaults(Path dir) throws IOException {
        int written = 0;
        for (String rel : DEFAULT_ASSETS) {
            Path target = dir.resolve(rel);
            if (Files.exists(target)) {
                continue;
            }
            byte[] bytes;
            try (InputStream in = WorkDir.class.getResourceAsStream(DEFAULTS_RESOURCE_ROOT + rel)) {
                if (in == null) {
                    throw new IOException("bundled resource " + DEFAULTS_RESOURCE_ROOT + rel + " missing from mod jar");
                }
                bytes = in.readAllBytes();
            }
            Files.createDirectories(target.getParent());
            Files.write(target, bytes);
            written++;
        }
        if (written > 0) {
            AiBuildMod.LOGGER.info("[aibuild] released {} default asset file(s) into {}", written, dir);
        }
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

            ## Style cards (MANDATORY — pick one BEFORE planning)

            The `styles/` directory holds style cards (JSON): quantified
            constraints, not adjectives. Before writing plan.md you MUST read
            the cards and pick the ONE that best matches the task description
            (e.g. a medieval tower / castle -> medieval_tower.json, a cabin on
            flat grassland -> plains_cabin.json, anything touching water ->
            waterfront_dock.json, a house on a slope -> stilt_house.json, a
            modern minimalist house -> nordic_villa.json). Then:

            - Use ONLY blocks from the card's materials lists (primary /
              secondary / accent / roof / windows) for the parts they describe.
              `blocks.md` in this directory is the quick id reference; anything
              outside both the card and blocks.md needs a reason in plan.md.
            - Respect the card's proportions (height/width ratio, storey
              height), roof type, and window rhythm. The style card governs
              MATERIALS; the pattern library below governs SHAPES — combine
              them (card materials as pattern params).
            - If no card fits well, pick the closest one and note the
              deviation in plan.md. To break a card's constraint on purpose,
              say so in chat first.
            - When the player says they like a build, save its parameters as a
              NEW card file in `styles/` (never overwrite existing cards).

            ## Pattern library (MANDATORY — assemble shapes, don't invent them)

            The `patterns/` directory holds parameterized generator scripts:
            `<name>.py` (zero-dependency, runs with plain `python`) plus a
            `<name>.json` parameter card (params, ranges, when_to_use). For
            these elements you MUST run the matching script instead of
            free-handing the shape:

            - gable / hip roof          -> gable_roof.py / hip_roof.py
            - crenellation (castle top) -> crenellation.py
            - buttress                  -> buttress.py
            - arched window             -> arch_window.py
            - road / path segment       -> road_segment.py
            - building pad / terrace    -> terraform_pad.py
            - quadruped statue          -> quadruped_statue.py

            Workflow: read the .json card -> choose params (origin = world
            coords of the element, sizes tuned to your build and the terrain,
            materials from your style card) -> run
            `python patterns/<name>.py --params '{...}' --out <element>.json`
            with your shell tool -> place with `set_blocks_from_file`. Only
            build free-hand what no pattern covers.

            ## Tools (MCP server `aibuild`)

            Write tools are ASYNC: they return `job_id` immediately, blocks are
            placed in the background. ALWAYS confirm with `get_job_status` before
            building on top of previous work. Write tools are locked (409) until
            the site is confirmed (see above).

            | tool | use |
            | --- | --- |
            | `fill(min, max, block, mode?)` | main workhorse. mode: replace (default) / keep / outline / hollow |
            | `set_blocks([{x,y,z,block}...])` | batch detail work, <= 4096 entries per call |
            | `set_blocks_from_file(path, offset?, place_air?)` | AVAILABLE. Places blocks listed in a file: JSON (`{"blocks":[{x,y,z,block}...]}`) or a `.schem` file. The bridge reads the file and batches automatically. THE channel for large generated shapes — never paste thousands of coordinates into tool args |
            | `set_block(x, y, z, block)` | single-block fixes |
            | `get_job_status(job_id)` | poll until state=done; check placed/failed counts |
            | `get_block(x, y, z)` | point query, returns block id + properties |
            | `search_blocks(query)` | AVAILABLE. Fuzzy search of block ids (e.g. "stained_glass") — use it instead of guessing ids |
            | `get_terrain_summary(center, radius)` | AVAILABLE. ASCII heightmap + water/flatness stats + flat candidates; radius <= 128 |
            | `propose_site(min, max)` | AVAILABLE. Required FIRST call when task.json has no bounds; then await confirmation |
            | `get_region_summary(min, max)` | AVAILABLE. Block-type counts + per-layer ASCII plan of a box (max 64^3). Cheap on tokens; use it to verify structure instead of many get_block calls |
            | `render_region(min, max, azimuth?, elevation?, mode?, projection?)` | AVAILABLE. Renders the box to a PNG image you can SEE. azimuth/elevation in degrees (default 45/45). mode: auto (default), gl (true 3D render, needs the game client open), topdown (map-style raster, always works). projection: persp (default) / ortho. Volume <= 262144 (64^3) |

            ## Mandatory visual self-check (DO NOT SKIP)

            You have eyes via `render_region` — use them. Before you declare the
            build finished you MUST:

            1. Call `render_region` on the whole build at least once and actually
               LOOK at the image. Compare against the quality floor: MC-native
               proportions (door 2 high, storey 3-4 high, walls 1 thick), height/width
               ratio 1:1~4:1, roof material distinct from walls, windows placed with
               rhythm (not random), structure connects to the terrain (not floating,
               not half-buried).
            2. Fix every flaw you spot, then render AGAIN to confirm the fix.
               You need at least 2 render rounds (render -> fix -> render) before
               completion; more if problems persist. Try a second azimuth (e.g. 45
               and 225) to see all faces.
            3. `get_region_summary` complements the renders: use it to check block
               counts and per-layer shapes match plan.md.
            4. Every render is also saved to `renders/` in this directory — the
               player reviews those files, so they must show the build clearly.

            A completion claim without at least 2 inspected renders is invalid.

            ## Rules

            1. BATCH FIRST. One `fill` beats 100 `set_block` calls. One `set_blocks`
               batch beats 100 singles. Plan the whole shape, then issue few large calls.
            2. CODE MODELING. For any curved, organic, or repetitive geometry
               (spheres, domes, arches, sloped roofs, statues, roads, walls with
               rhythm): do NOT compute coordinates in your head — you are bad at
               mental coordinate math and great at writing code. Write a small
               generator script (Python) in this directory that computes the block
               list and writes it as JSON, run it with your shell tool, then place
               via `set_blocks_from_file`. This costs zero extra tokens and is
               dramatically more accurate.
            3. Block ids are full namespaced ids, e.g. `minecraft:stone_bricks`.
               `blocks.md` in this directory lists the common building ids —
               check it FIRST. Still unsure? Call `search_blocks` — don't
               guess. Invalid ids come back with suggestions — use them.
            4. Before you start, write a short `plan.md` in this directory: the
               style card you picked (name it), shape, dimensions, materials
               from that card, which patterns you will run with which params,
               layer-by-layer sketch. Keep it brief.
            5. Build BOTTOM-UP: foundations first, then walls, then roof/details.
               Wait for each job's `get_job_status` = done (and failed == 0) before
               depending on its blocks. If failures say `out_of_bounds`, you placed
               outside the confirmed range — redo those parts inside it.
            6. Self-check when finished: follow the "Mandatory visual self-check"
               section above — at least 2 render_region rounds plus a
               get_region_summary cross-check. Fix any mismatches.
            7. A tool response may end with `[玩家消息] ...` lines — these are live
               messages from the player. Treat them as instructions and adapt.
            8. Creative-mode semantics: blocks appear out of nowhere, no physics
               worries, floating is allowed but ugly — connect to the ground unless
               the task says otherwise.
            """;
}
