package com.aibuild.mod.bridge;

import com.aibuild.mod.AiBuildMod;
import com.aibuild.mod.agent.AgentSession;
import com.aibuild.mod.agent.AgentSessionManager;
import com.aibuild.mod.agent.WorkDir;
import com.aibuild.mod.job.BuildJob;
import com.aibuild.mod.job.FillMode;
import com.aibuild.mod.job.Job;
import com.aibuild.mod.job.JobManager;
import com.aibuild.mod.job.Placement;
import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonSyntaxException;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.chat.Style;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * Minimal embedded HTTP API (JDK {@link com.sun.net.httpserver}) for the
 * mc-mcp-bridge. Binds 127.0.0.1 on a random port with a random master bearer
 * token, written to {@code <gameDir>/aibuild/bridge.json} on server start.
 *
 * E3 multi-token routing: every build session gets its own token (written to
 * that session's .kimi-code/mcp.json, listed in bridge.json). A request's
 * X-Aibuild-Token resolves to its session via the AgentSessionManager — write
 * tools then gate on THAT session's SiteGate, propose_site checks overlap
 * against other running sessions, and player_messages piggyback drains that
 * session's inbox. The master token keeps working for external tooling: it
 * routes to the newest RUNNING session (a "default session"), or — when none
 * is running — read-only endpoints still work while write endpoints answer
 * 409 (a deliberate choice over silently mixing sessions).
 *
 * HTTP threads only serialize JSON; every world operation is dispatched to
 * the server main thread via {@link MinecraftServer#execute} and awaited with
 * a timeout.
 */
public final class BridgeHttpServer {
    private static final Gson GSON = new Gson();
    private static final int MAIN_THREAD_TIMEOUT_SECONDS = 30;
    /** GL render wait must stay below the bridge's default HTTP timeout (30 s). */
    private static final int GL_RENDER_TIMEOUT_SECONDS = 25;
    private static final DateTimeFormatter RENDER_FILE_STAMP = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss_SSS");

    private final JobManager jobManager;
    private final AgentSessionManager sessions;
    private HttpServer http;
    private String masterToken;
    private int port = -1;
    private MinecraftServer server;
    private Path gameDir;

    public BridgeHttpServer(JobManager jobManager, AgentSessionManager sessions) {
        this.jobManager = jobManager;
        this.sessions = sessions;
    }

    public void start(MinecraftServer server, Path gameDir) throws IOException {
        this.server = server;
        this.gameDir = gameDir;
        this.masterToken = UUID.randomUUID().toString();

        http = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        http.createContext("/tools/fill", ex -> handle(ex, "POST", this::fill));
        http.createContext("/tools/set_blocks", ex -> handle(ex, "POST", this::setBlocks));
        http.createContext("/tools/set_block", ex -> handle(ex, "POST", this::setBlock));
        http.createContext("/tools/job_status", ex -> handle(ex, "GET", this::jobStatus));
        http.createContext("/tools/get_block", ex -> handle(ex, "POST", this::getBlock));
        http.createContext("/tools/search_blocks", ex -> handle(ex, "POST", this::searchBlocks));
        http.createContext("/tools/propose_site", ex -> handle(ex, "POST", this::proposeSite));
        http.createContext("/tools/confirm_site", ex -> handle(ex, "POST", this::confirmSite));
        http.createContext("/tools/get_terrain_summary", ex -> handle(ex, "POST", this::getTerrainSummary));
        http.createContext("/tools/analyze_site", ex -> handle(ex, "POST", this::analyzeSite));
        http.createContext("/tools/get_region_summary", ex -> handle(ex, "POST", this::getRegionSummary));
        http.createContext("/tools/render_region", ex -> handleBinary(ex, "POST", this::renderRegion));
        http.createContext("/tools/ask_player", ex -> handle(ex, "POST", this::askPlayer));
        http.setExecutor(Executors.newCachedThreadPool(r -> {
            Thread t = new Thread(r, "aibuild-http");
            t.setDaemon(true);
            return t;
        }));
        http.start();

        port = http.getAddress().getPort();
        refreshBridgeJson(Map.of());
        AiBuildMod.LOGGER.info("[aibuild] bridge http server listening on 127.0.0.1:{} (credentials in {})",
                port, gameDir.resolve("aibuild").resolve("bridge.json"));
    }

    public int port() {
        return port;
    }

    /** Rewrites bridge.json: port + master token + the registry's per-session tokens. */
    public void refreshBridgeJson(Map<Integer, String> sessionTokens) {
        try {
            Path dir = gameDir.resolve("aibuild");
            Files.createDirectories(dir);
            JsonObject info = new JsonObject();
            info.addProperty("port", port);
            info.addProperty("token", masterToken);
            JsonObject tokens = new JsonObject();
            sessionTokens.forEach((no, token) -> tokens.addProperty(String.valueOf(no), token));
            info.add("sessions", tokens);
            Files.writeString(dir.resolve("bridge.json"), GSON.toJson(info));
        } catch (Exception e) {
            AiBuildMod.LOGGER.warn("[aibuild] failed to write bridge.json", e);
        }
    }

    public void stop() {
        if (http != null) {
            http.stop(0);
            http = null;
        }
    }

    // ------------------------------------------------------------------ plumbing

    @FunctionalInterface
    private interface Endpoint {
        JsonObject handle(HttpExchange exchange, AgentSession session) throws Exception;
    }

    private static final class ApiError extends Exception {
        final int status;
        final JsonObject body;

        ApiError(int status, JsonObject body) {
            super(body.toString());
            this.status = status;
            this.body = body;
        }
    }

    /**
     * Resolves the request token: a session token → that session; the master
     * token → the newest RUNNING session ("default session"), or null when
     * none is running. Unknown tokens → 403.
     */
    private AgentSession resolveSession(HttpExchange ex) {
        String header = ex.getRequestHeaders().getFirst("X-Aibuild-Token");
        if (header == null) {
            return null;
        }
        AgentSession s = sessions.sessionForToken(header);
        if (s != null) {
            return s;
        }
        return masterToken.equals(header) ? sessions.defaultSession() : null;
    }

    private boolean authorized(HttpExchange ex) {
        String header = ex.getRequestHeaders().getFirst("X-Aibuild-Token");
        return header != null && (masterToken.equals(header) || sessions.sessionForToken(header) != null);
    }

    private void handle(HttpExchange ex, String method, Endpoint endpoint) throws IOException {
        AgentSession session = null;
        try {
            if (!authorized(ex)) {
                send(ex, 403, error("forbidden"), null);
                return;
            }
            if (!method.equalsIgnoreCase(ex.getRequestMethod())) {
                send(ex, 405, error("method not allowed"), null);
                return;
            }
            session = resolveSession(ex);
            send(ex, 200, endpoint.handle(ex, session), session);
        } catch (ApiError e) {
            send(ex, e.status, e.body, session);
        } catch (Exception e) {
            AiBuildMod.LOGGER.error("[aibuild] error handling {} {}", ex.getRequestMethod(), ex.getRequestURI(), e);
            send(ex, 500, error("internal error: " + e.getMessage()), session);
        } finally {
            ex.close();
        }
    }

    /** Runs a task on the server main thread and waits for the result (with a timeout). */
    private <T> T onMainThread(Callable<T> task) throws Exception {
        CompletableFuture<T> future = new CompletableFuture<>();
        server.execute(() -> {
            try {
                future.complete(task.call());
            } catch (Throwable t) {
                future.completeExceptionally(t);
            }
        });
        try {
            return future.get(MAIN_THREAD_TIMEOUT_SECONDS, TimeUnit.SECONDS);
        } catch (ExecutionException e) {
            if (e.getCause() instanceof Exception cause) {
                throw cause;
            }
            throw e;
        }
    }

    // ------------------------------------------------------------------ binary plumbing (render_region)

    @FunctionalInterface
    private interface BinaryEndpoint {
        PngReply handle(HttpExchange exchange, AgentSession session) throws Exception;
    }

    /** PNG body plus the render path actually used ("gl" or "topdown"), sent as a header. */
    private record PngReply(byte[] pngBytes, String renderMode) {
    }

    private void handleBinary(HttpExchange ex, String method, BinaryEndpoint endpoint) throws IOException {
        try {
            if (!authorized(ex)) {
                send(ex, 403, error("forbidden"), null);
                return;
            }
            if (!method.equalsIgnoreCase(ex.getRequestMethod())) {
                send(ex, 405, error("method not allowed"), null);
                return;
            }
            PngReply reply = endpoint.handle(ex, resolveSession(ex));
            ex.getResponseHeaders().set("Content-Type", "image/png");
            ex.getResponseHeaders().set("X-Aibuild-Render-Mode", reply.renderMode());
            ex.sendResponseHeaders(200, reply.pngBytes().length);
            try (OutputStream os = ex.getResponseBody()) {
                os.write(reply.pngBytes());
            }
        } catch (ApiError e) {
            send(ex, e.status, e.body, null);
        } catch (Exception e) {
            AiBuildMod.LOGGER.error("[aibuild] error handling {} {}", ex.getRequestMethod(), ex.getRequestURI(), e);
            send(ex, 500, error("internal error: " + e.getMessage()), null);
        } finally {
            ex.close();
        }
    }

    private void send(HttpExchange ex, int status, JsonObject body, AgentSession session) {
        try {
            // Piggyback the session's queued player messages onto every JSON
            // response (except auth failures, which by definition do not reach
            // the agent). Each session drains only its own inbox.
            if (status != 403 && session != null) {
                List<String> messages = session.inbox().drain();
                if (!messages.isEmpty()) {
                    JsonArray arr = new JsonArray();
                    for (String m : messages) {
                        arr.add(m);
                    }
                    body.add("player_messages", arr);
                }
            }
            byte[] bytes = GSON.toJson(body).getBytes(StandardCharsets.UTF_8);
            ex.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
            ex.sendResponseHeaders(status, bytes.length);
            try (OutputStream os = ex.getResponseBody()) {
                os.write(bytes);
            }
        } catch (IOException e) {
            AiBuildMod.LOGGER.warn("[aibuild] failed to send http response", e);
        }
    }

    private static JsonObject error(String message) {
        JsonObject o = new JsonObject();
        o.addProperty("error", message);
        return o;
    }

    private static ApiError badRequest(String message) {
        return new ApiError(400, error(message));
    }

    private static ApiError invalidBlock(BlockSpecParser.InvalidBlockException e) {
        JsonObject body = error(e.getMessage());
        JsonArray suggestions = new JsonArray();
        for (String s : e.suggestions()) {
            suggestions.add(s);
        }
        body.add("suggestions", suggestions);
        return new ApiError(400, body);
    }

    // ------------------------------------------------------------------ endpoints

    private JsonObject fill(HttpExchange ex, AgentSession session) throws Exception {
        AgentSession s = requireSession(session);
        JsonObject body = readJsonBody(ex);
        int[] min = vec3(body, "min");
        int[] max = vec3(body, "max");
        String blockSpec = requiredString(body, "block");
        FillMode mode;
        try {
            mode = FillMode.parse(optString(body, "mode", "replace"));
        } catch (IllegalArgumentException e) {
            throw badRequest(e.getMessage());
        }

        int minX = Math.min(min[0], max[0]);
        int minY = Math.min(min[1], max[1]);
        int minZ = Math.min(min[2], max[2]);
        int maxX = Math.max(min[0], max[0]);
        int maxY = Math.max(min[1], max[1]);
        int maxZ = Math.max(min[2], max[2]);
        long volume = (long) (maxX - minX + 1) * (maxY - minY + 1) * (maxZ - minZ + 1);
        if (volume > JobManager.MAX_JOB_BLOCKS) {
            throw badRequest("fill volume " + volume + " exceeds limit of " + JobManager.MAX_JOB_BLOCKS + " blocks");
        }

        SiteGate.Bounds bounds = requireBounds(s);
        BlockPos minPos = new BlockPos(minX, minY, minZ);
        BlockPos maxPos = new BlockPos(maxX, maxY, maxZ);
        BuildJob job = onMainThread(() -> {
            BlockState state = parseBlock(blockSpec);
            return jobManager.submitFill(server.overworld(), minPos, maxPos, state, mode, bounds,
                    "fill " + blockSpec + " " + minPos.toShortString() + " ~ " + maxPos.toShortString(),
                    s.sessionTag());
        });
        return jobId(job);
    }

    private JsonObject setBlocks(HttpExchange ex, AgentSession session) throws Exception {
        AgentSession s = requireSession(session);
        JsonObject body = readJsonBody(ex);
        JsonArray entries = requiredArray(body, "blocks");
        if (entries.size() > JobManager.MAX_SET_BLOCKS_ENTRIES) {
            throw badRequest("set_blocks accepts at most " + JobManager.MAX_SET_BLOCKS_ENTRIES
                    + " entries per request, got " + entries.size());
        }
        record RawEntry(int x, int y, int z, String spec) {
        }
        List<RawEntry> raw = new ArrayList<>(entries.size());
        for (JsonElement el : entries) {
            if (!el.isJsonObject()) {
                throw badRequest("each set_blocks entry must be an object {x,y,z,block}");
            }
            JsonObject o = el.getAsJsonObject();
            raw.add(new RawEntry(requiredInt(o, "x"), requiredInt(o, "y"), requiredInt(o, "z"), requiredString(o, "block")));
        }
        SiteGate.Bounds bounds = requireBounds(s);
        BuildJob job = onMainThread(() -> {
            List<Placement> placements = new ArrayList<>(raw.size());
            for (RawEntry r : raw) {
                placements.add(new Placement(new BlockPos(r.x(), r.y(), r.z()), parseBlock(r.spec()), false));
            }
            return jobManager.submitPlacements(server.overworld(), placements, bounds,
                    "set_blocks " + raw.size() + " blocks", s.sessionTag());
        });
        return jobId(job);
    }

    private JsonObject setBlock(HttpExchange ex, AgentSession session) throws Exception {
        AgentSession s = requireSession(session);
        JsonObject body = readJsonBody(ex);
        int x = requiredInt(body, "x");
        int y = requiredInt(body, "y");
        int z = requiredInt(body, "z");
        String blockSpec = requiredString(body, "block");
        SiteGate.Bounds bounds = requireBounds(s);
        BuildJob job = onMainThread(() -> jobManager.submitPlacements(server.overworld(),
                List.of(new Placement(new BlockPos(x, y, z), parseBlock(blockSpec), false)), bounds,
                "set_block " + blockSpec + " @ " + x + " " + y + " " + z, s.sessionTag()));
        return jobId(job);
    }

    private JsonObject searchBlocks(HttpExchange ex, AgentSession session) throws Exception {
        JsonObject body = readJsonBody(ex);
        String query = requiredString(body, "query");
        JsonArray matches = new JsonArray();
        for (String match : BlockSpecParser.search(query, 16)) {
            matches.add(match);
        }
        JsonObject res = new JsonObject();
        res.add("matches", matches);
        return res;
    }

    private JsonObject jobStatus(HttpExchange ex, AgentSession session) throws Exception {
        String id = queryParam(ex, "id");
        if (id == null || id.isEmpty()) {
            throw badRequest("missing query parameter 'id'");
        }
        Job job = onMainThread(() -> jobManager.get(id));
        if (job == null) {
            throw new ApiError(404, error("unknown job_id: " + id));
        }
        return job.toJson();
    }

    private JsonObject getBlock(HttpExchange ex, AgentSession session) throws Exception {
        JsonObject body = readJsonBody(ex);
        BlockPos pos = new BlockPos(requiredInt(body, "x"), requiredInt(body, "y"), requiredInt(body, "z"));
        return onMainThread(() -> {
            BlockState state = server.overworld().getBlockState(pos);
            JsonObject res = new JsonObject();
            res.addProperty("block", BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString());
            JsonObject props = new JsonObject();
            state.getValues().forEach((property, value) -> props.addProperty(property.getName(), propertyValue(property, value)));
            res.add("properties", props);
            return res;
        });
    }

    private JsonObject proposeSite(HttpExchange ex, AgentSession session) throws Exception {
        AgentSession s = requireSession(session);
        JsonObject body = readJsonBody(ex);
        SiteGate.Bounds proposal = SiteGate.Bounds.of(vec3(body, "min"), vec3(body, "max"));
        if (proposal.volume() > SiteGate.MAX_VOLUME) {
            throw badRequest("proposed volume " + proposal.volume() + " exceeds limit of " + SiteGate.MAX_VOLUME + " blocks");
        }
        return onMainThread(() -> {
            AgentSession conflict = sessions.findConflict(s, proposal);
            if (conflict != null) {
                SiteGate.Bounds other = conflict.gate().activeBounds();
                throw new ApiError(409, error("proposed site intersects the bounds of running session #"
                        + conflict.no() + " (" + (other != null ? other.describe() : "?")
                        + ") — pick a non-overlapping area"));
            }
            if (!s.gate().propose(proposal)) {
                String why = s.gate().state() == SiteGate.State.CONFIRMED
                        ? "site already confirmed for this session: " + s.gate().currentBounds().describe()
                        : "another site proposal is already pending confirmation";
                throw new ApiError(409, error(why));
            }
            broadcastProposal(s, proposal);
            JsonObject res = new JsonObject();
            res.addProperty("status", "pending_confirmation");
            res.addProperty("session", s.no());
            res.addProperty("message", "等待玩家确认(/aiconfirm 或 /aireject);确认前写工具保持锁定");
            // 已占用地图软警告: 与历史会话(DONE/FAILED/CANCELLED)的 confirmed bounds
            // 相交时附加 warning — 不拦截,只提醒 AI 这块地盖过东西(RUNNING 相交已在上面 409)。
            List<AgentSession> overlaps = sessions.occupiedOverlap(s, proposal);
            if (!overlaps.isEmpty()) {
                StringBuilder warn = new StringBuilder("warning: overlaps previously built area of ");
                for (int i = 0; i < overlaps.size(); i++) {
                    if (i > 0) {
                        warn.append(", ");
                    }
                    warn.append("session #").append(overlaps.get(i).no());
                }
                res.addProperty("warning", warn.toString());
            }
            return res;
        });
    }

    private JsonObject getTerrainSummary(HttpExchange ex, AgentSession session) throws Exception {
        JsonObject body = readJsonBody(ex);
        JsonArray center = requiredArray(body, "center");
        if (center.size() != 2) {
            throw badRequest("'center' must be [x,z]");
        }
        int cx = center.get(0).getAsInt();
        int cz = center.get(1).getAsInt();
        int radius = requiredInt(body, "radius");
        if (radius < 1 || radius > TerrainSummary.MAX_RADIUS) {
            throw badRequest("radius must be between 1 and " + TerrainSummary.MAX_RADIUS);
        }
        String text = onMainThread(() -> TerrainSummary.generate(server.overworld(), cx, cz, radius));
        JsonObject res = new JsonObject();
        res.addProperty("text", text);
        return res;
    }

    /**
     * confirm_site (master token only): directly confirm bounds on the newest
     * session — the tooling backdoor for manual block pours (gallery / large
     * scenes), where spawning an AI session just to unlock writes is absurd.
     * Volume cap still applies.
     */
    private JsonObject confirmSite(HttpExchange ex, AgentSession session) throws Exception {
        String header = ex.getRequestHeaders().getFirst("X-Aibuild-Token");
        if (!masterToken.equals(header)) {
            throw new ApiError(403, error("confirm_site requires the master token"));
        }
        AgentSession s = session != null ? session : sessions.latestAny();
        if (s == null) {
            throw new ApiError(409, error("no session exists in this world — run /aibuild once first"));
        }
        JsonObject body = readJsonBody(ex);
        SiteGate.Bounds b = SiteGate.Bounds.of(vec3(body, "min"), vec3(body, "max"));
        if (b.volume() > SiteGate.MAX_VOLUME) {
            throw badRequest("volume " + b.volume() + " exceeds limit of " + SiteGate.MAX_VOLUME);
        }
        SiteGate.Bounds finalB = b;
        return onMainThread(() -> {
            s.gate().confirmDirect(finalB);
            JsonObject res = new JsonObject();
            res.addProperty("status", "confirmed");
            res.addProperty("session", s.no());
            res.addProperty("bounds", finalB.describe());
            return res;
        });
    }

    /**
     * analyze_site: read-only site-selection scout (master token works with no
     * running session, like get_terrain_summary). Per 16x16 candidate tile:
     * ground mean/stddev, cut+fill estimate, water share, tree count, and the
     * conflict list against the occupied map (all sessions' confirmed bounds).
     */
    private JsonObject analyzeSite(HttpExchange ex, AgentSession session) throws Exception {
        JsonObject body = readJsonBody(ex);
        JsonArray center = requiredArray(body, "center");
        if (center.size() != 2) {
            throw badRequest("'center' must be [x,z]");
        }
        int cx = center.get(0).getAsInt();
        int cz = center.get(1).getAsInt();
        int radius = requiredInt(body, "radius");
        if (radius < 1 || radius > SiteAnalyzer.MAX_RADIUS) {
            throw badRequest("radius must be between 1 and " + SiteAnalyzer.MAX_RADIUS);
        }
        List<AgentSessionManager.OccupiedSite> occupied = sessions.occupiedSites();
        String text = onMainThread(() -> SiteAnalyzer.generate(server.overworld(), cx, cz, radius, occupied));
        JsonObject res = new JsonObject();
        res.addProperty("text", text);
        return res;
    }

    private JsonObject getRegionSummary(HttpExchange ex, AgentSession session) throws Exception {
        JsonObject body = readJsonBody(ex);
        BlockPos[] box = regionBox(body);
        String text = onMainThread(() -> RegionSummary.generate(server.overworld(), box[0], box[1]));
        JsonObject res = new JsonObject();
        res.addProperty("text", text);
        return res;
    }

    /**
     * render_region: PNG of the region. mode=auto|gl|topdown (default auto);
     * projection=persp|ortho (default persp, GL path only). GL rendering is
     * only possible in a client environment (single player: integrated server
     * shares the JVM with the client); when it is unavailable or fails, the
     * server-side top-down raster is returned instead, transparently to the
     * caller (the actual path is reported via the X-Aibuild-Render-Mode
     * response header). The PNG is also written to the session's
     * {@code renders/} dir (or the aibuild root's for session-less requests)
     * so the player can look at what the AI saw.
     */
    private PngReply renderRegion(HttpExchange ex, AgentSession session) throws Exception {
        JsonObject body = readJsonBody(ex);
        BlockPos[] box = regionBox(body);
        BlockPos minPos = box[0];
        BlockPos maxPos = box[1];
        float azimuth = (float) optDouble(body, "azimuth", 45.0);
        float elevation = (float) optDouble(body, "elevation", 45.0);
        String mode = optString(body, "mode", "auto");
        if (!mode.equals("auto") && !mode.equals("gl") && !mode.equals("topdown")) {
            throw badRequest("'mode' must be one of: auto, gl, topdown");
        }
        String projection = optString(body, "projection", "persp");
        if (!projection.equals("persp") && !projection.equals("ortho")) {
            throw badRequest("'projection' must be one of: persp, ortho");
        }

        byte[] png = null;
        String usedMode = null;
        if (!mode.equals("topdown")) {
            RenderHooks.GlRegionRenderer gl = RenderHooks.glRenderer();
            if (gl != null) {
                try {
                    png = gl.renderPng(minPos, maxPos, azimuth, elevation, projection.equals("ortho"))
                            .get(GL_RENDER_TIMEOUT_SECONDS, TimeUnit.SECONDS);
                    usedMode = "gl";
                } catch (Exception e) {
                    AiBuildMod.LOGGER.warn("[aibuild] GL render failed, falling back to topdown", e);
                }
            } else if (mode.equals("gl")) {
                AiBuildMod.LOGGER.info("[aibuild] render_region mode=gl but no client renderer "
                        + "(dedicated server?) — falling back to topdown");
            }
        }
        if (png == null) {
            png = onMainThread(() -> TopDownRenderer.renderPng(server.overworld(), minPos, maxPos));
            usedMode = "topdown";
        }

        try {
            Path root = WorkDir.dirOf(server);
            Path rendersDir = (session != null ? session.workDir(root) : root).resolve("renders");
            Files.createDirectories(rendersDir);
            String stamp = RENDER_FILE_STAMP.format(LocalDateTime.now());
            Files.write(rendersDir.resolve("render_" + stamp + "_" + usedMode + ".png"), png);
        } catch (IOException e) {
            AiBuildMod.LOGGER.warn("[aibuild] failed to save render to renders/ dir", e);
        }
        return new PngReply(png, usedMode);
    }

    /** Parses and normalizes (per-axis sorted) min/max from the request body; enforces the volume cap. */
    private BlockPos[] regionBox(JsonObject body) throws ApiError {
        int[] min = vec3(body, "min");
        int[] max = vec3(body, "max");
        int minX = Math.min(min[0], max[0]);
        int minY = Math.min(min[1], max[1]);
        int minZ = Math.min(min[2], max[2]);
        int maxX = Math.max(min[0], max[0]);
        int maxY = Math.max(min[1], max[1]);
        int maxZ = Math.max(min[2], max[2]);
        long volume = (long) (maxX - minX + 1) * (maxY - minY + 1) * (maxZ - minZ + 1);
        if (volume > SiteGate.MAX_VOLUME) {
            throw badRequest("region volume " + volume + " exceeds limit of " + SiteGate.MAX_VOLUME + " blocks");
        }
        return new BlockPos[]{new BlockPos(minX, minY, minZ), new BlockPos(maxX, maxY, maxZ)};
    }

    /** Write tools need a session-bound token; the master token alone is not enough. */
    private AgentSession requireSession(AgentSession session) throws ApiError {
        if (session == null) {
            throw new ApiError(409, error("no build session is bound to this request "
                    + "(master token with no running session) — use a session token from that session's .kimi-code/mcp.json"));
        }
        return session;
    }

    /** Bounds gate for write tools: 409 while the session has no confirmed range. */
    private SiteGate.Bounds requireBounds(AgentSession session) throws ApiError {
        if (session.status() == AgentSession.Status.INTAKE) {
            throw new ApiError(409, error("intake interview in progress — write tools unlock when the build phase starts"));
        }
        SiteGate.Bounds bounds = session.gate().currentBounds();
        if (bounds == null) {
            throw new ApiError(409, error("site not confirmed"));
        }
        return bounds;
    }

    /**
     * Sends the site proposal to every online player with clickable
     * [确认]/[拒绝] buttons (ClickEvent.RunCommand → /aiconfirm, /aireject;
     * verified against 1.21.11: ClickEvent is an interface of records, the
     * client trims the optional leading "/" before sending the command).
     * With nobody online the message is logged and RCON/console can run the
     * same commands. /aiconfirm acts on the NEWEST pending session.
     */
    private void broadcastProposal(AgentSession session, SiteGate.Bounds b) {
        MutableComponent msg = Component.literal("[aibuild] #" + session.no()
                + " AI proposes build site " + b.describe() + "  ");
        msg.append(Component.literal("[确认]").withStyle(Style.EMPTY
                .withColor(ChatFormatting.GREEN).withBold(true)
                .withClickEvent(new ClickEvent.RunCommand("/aiconfirm"))));
        msg.append(Component.literal("  "));
        msg.append(Component.literal("[拒绝]").withStyle(Style.EMPTY
                .withColor(ChatFormatting.RED).withBold(true)
                .withClickEvent(new ClickEvent.RunCommand("/aireject"))));
        AiBuildMod.LOGGER.info("[aibuild] #{} site proposed: {}", session.no(), b.describe());
        server.getPlayerList().broadcastSystemMessage(msg, false);
    }

    /** ask_player: one wait slice per request — the agent re-calls to keep waiting.
     * 45 s, comfortably under the kimi MCP client tool timeout (default 60 s):
     * a 60 s slice raced the client timeout and the agent saw errors instead of
     * "waiting", which made it give up waiting and rush ahead (实测翻车). */
    private static final long ASK_WAIT_SLICE_MS = 45_000L;
    /** Caps so a confused agent cannot flood the chat bar. */
    private static final int ASK_MAX_OPTIONS = 6;

    /**
     * ask_player endpoint: broadcasts the interviewer's question (options as
     * clickable buttons that emit /aichat), then waits one slice for the
     * player's answer. The answer rides back as the tool RESULT (not the
     * player_messages piggyback), so asking becomes an explicit, un-skippable
     * action — the interviewer cannot "forget" to ask. ONE question per call
     * (answers can change later questions); extra questions are dropped with a
     * warning. Re-calls with the SAME question are not re-broadcast (chat-bar
     * flood guard, fingerprint kept on the session).
     */
    private JsonObject askPlayer(HttpExchange ex, AgentSession session) throws Exception {
        AgentSession s = requireSession(session);
        JsonObject body = readJsonBody(ex);
        JsonArray questions = requiredArray(body, "questions");
        boolean truncated = questions.size() > 1;
        JsonArray one = new JsonArray();
        if (questions.size() > 0 && questions.get(0).isJsonObject()) {
            one.add(questions.get(0));
        }
        if (one.isEmpty()) {
            throw badRequest("questions must contain at least one object {q, options?}");
        }
        String fingerprint = one.toString();
        if (!fingerprint.equals(s.lastAskFingerprint)) {
            s.lastAskFingerprint = fingerprint;
            onMainThread(() -> {
                broadcastQuestions(s, one);
                return null;
            });
        }
        String first = s.inbox().take(ASK_WAIT_SLICE_MS);
        JsonObject res = new JsonObject();
        if (first == null) {
            res.addProperty("status", "waiting");
            res.addProperty("text", "玩家暂未回复(已等 45 秒)。继续调用 ask_player(同一问题)等待即可——"
                    + "等待没有次数上限,玩家去忙/想问题很正常,绝不能因为等待而自行收尾;"
                    + "只有玩家说「跳过/随便/你定」才能提前结束访谈。");
            return res;
        }
        List<String> answers = new ArrayList<>();
        answers.add(first);
        answers.addAll(s.inbox().drain());
        res.addProperty("status", "answered");
        StringBuilder text = new StringBuilder();
        if (truncated) {
            text.append("(注意:一次只能问一个问题,多余问题已被丢弃——上一个回答可能改变你下一个问题)\n");
        }
        text.append("玩家回复:");
        for (String a : answers) {
            text.append("\n- ").append(a);
        }
        res.addProperty("text", text.toString());
        return res;
    }

    /** Renders ask_player questions to the chat bar with clickable option buttons. */
    private void broadcastQuestions(AgentSession s, JsonArray questions) {
        server.getPlayerList().broadcastSystemMessage(Component.literal("[aibuild] #" + s.no()
                + " AI 提问(点选项 = 快速回答;自由回答:聊天栏输入 /aichat 你的回答;「跳过」= 不问直接造):"), false);
        int qi = 0;
        for (JsonElement el : questions) {
            if (!el.isJsonObject()) {
                continue;
            }
            qi++;
            JsonObject q = el.getAsJsonObject();
            String text = q.has("q") ? q.get("q").getAsString() : "";
            server.getPlayerList().broadcastSystemMessage(
                    Component.literal("[AI#" + s.no() + "] 问题" + qi + ": " + text), false);
            if (!q.has("options") || !q.get("options").isJsonArray()) {
                continue;
            }
            MutableComponent opts = Component.literal("    ");
            int oi = 0;
            for (JsonElement oe : q.getAsJsonArray("options")) {
                if (++oi > ASK_MAX_OPTIONS) {
                    break;
                }
                String opt = oe.getAsString();
                opts.append(Component.literal("[" + opt + "]").withStyle(Style.EMPTY
                        .withColor(ChatFormatting.AQUA)
                        .withClickEvent(new ClickEvent.RunCommand("/aichat 问题" + qi + ": " + opt))));
                opts.append(Component.literal("  "));
            }
            if (oi > 0) {
                server.getPlayerList().broadcastSystemMessage(opts, false);
            }
        }
        AiBuildMod.LOGGER.info("[aibuild] #{} ask_player: {} question(s) broadcast", s.no(), questions.size());
    }

    // ------------------------------------------------------------------ helpers

    private BlockState parseBlock(String spec) throws ApiError {
        try {
            return BlockSpecParser.parse(server, spec);
        } catch (BlockSpecParser.InvalidBlockException e) {
            throw invalidBlock(e);
        }
    }

    private static JsonObject jobId(BuildJob job) {
        JsonObject res = new JsonObject();
        res.addProperty("job_id", job.id());
        return res;
    }

    private static JsonObject readJsonBody(HttpExchange ex) throws IOException, ApiError {
        String body = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        try {
            JsonElement el = JsonParser.parseString(body.isBlank() ? "{}" : body);
            if (!el.isJsonObject()) {
                throw badRequest("request body must be a JSON object");
            }
            return el.getAsJsonObject();
        } catch (JsonSyntaxException | IllegalStateException e) {
            throw badRequest("malformed JSON body");
        }
    }

    private static String queryParam(HttpExchange ex, String name) {
        String query = ex.getRequestURI().getRawQuery();
        if (query == null) {
            return null;
        }
        for (String pair : query.split("&")) {
            int eq = pair.indexOf('=');
            String key = eq >= 0 ? pair.substring(0, eq) : pair;
            if (key.equals(name)) {
                return eq >= 0 ? pair.substring(eq + 1) : "";
            }
        }
        return null;
    }

    private static int[] vec3(JsonObject body, String name) throws ApiError {
        JsonArray arr = requiredArray(body, name);
        if (arr.size() != 3) {
            throw badRequest("'" + name + "' must be [x,y,z]");
        }
        int[] out = new int[3];
        for (int i = 0; i < 3; i++) {
            JsonElement el = arr.get(i);
            if (!el.isJsonPrimitive() || !el.getAsJsonPrimitive().isNumber()) {
                throw badRequest("'" + name + "' must contain integers");
            }
            out[i] = el.getAsInt();
        }
        return out;
    }

    private static JsonArray requiredArray(JsonObject body, String name) throws ApiError {
        if (!body.has(name) || !body.get(name).isJsonArray()) {
            throw badRequest("missing or invalid '" + name + "' array");
        }
        return body.getAsJsonArray(name);
    }

    private static int requiredInt(JsonObject body, String name) throws ApiError {
        if (!body.has(name) || !body.get(name).isJsonPrimitive() || !body.get(name).getAsJsonPrimitive().isNumber()) {
            throw badRequest("missing or invalid integer '" + name + "'");
        }
        return body.get(name).getAsInt();
    }

    private static String requiredString(JsonObject body, String name) throws ApiError {
        if (!body.has(name) || !body.get(name).isJsonPrimitive() || !body.get(name).getAsJsonPrimitive().isString()) {
            throw badRequest("missing or invalid string '" + name + "'");
        }
        return body.get(name).getAsString();
    }

    private static String optString(JsonObject body, String name, String fallback) throws ApiError {
        if (!body.has(name) || body.get(name).isJsonNull()) {
            return fallback;
        }
        return requiredString(body, name);
    }

    private static double optDouble(JsonObject body, String name, double fallback) throws ApiError {
        if (!body.has(name) || body.get(name).isJsonNull()) {
            return fallback;
        }
        JsonElement el = body.get(name);
        if (!el.isJsonPrimitive() || !el.getAsJsonPrimitive().isNumber()) {
            throw badRequest("'" + name + "' must be a number");
        }
        return el.getAsDouble();
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static String propertyValue(Property<?> property, Comparable<?> value) {
        return ((Property) property).getName(value);
    }
}
