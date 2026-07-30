package com.aibuild.mod.agent;

import com.aibuild.mod.AiBuildMod;
import com.aibuild.mod.bridge.BridgeHttpServer;
import com.aibuild.mod.bridge.SiteGate;
import com.aibuild.mod.bridge.TerrainSummary;
import com.aibuild.mod.config.AgentConfig;
import com.aibuild.mod.job.JobManager;
import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Registry of build sessions (E3: multi-agent concurrency). Each session
 * ({@link AgentSession}) owns its agent process (via a per-session
 * {@link AgentRunner}), working directory ({@code <world>/aibuild/sessions/s<n>/}),
 * bridge token, SiteGate and inbox; {@code max_concurrent_agents} (default 4)
 * running sessions are allowed at once — /aibuild is rejected only at the cap.
 *
 * The whole registry is persisted to {@code <world>/aibuild/sessions.json} on
 * EVERY change (status, gate, kimi session id, stats); on server start it is
 * loaded back so confirmed sites and resumable sessions survive restarts.
 * Pre-E3 worlds (single {@code state.json} + {@code .session_id}) are migrated
 * into session #1 on first load.
 *
 * Token routing for the bridge: every session gets a random token at creation
 * (persisted); the bridge resolves a request's X-Aibuild-Token to its session
 * via {@link #sessionForToken(String)} and falls back to
 * {@link #defaultSession()} for the master token.
 */
public final class AgentSessionManager {
    private static final Gson GSON = new Gson();
    private static final DateTimeFormatter TAG_STAMP = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss");
    /** /aistatus prints at most this many sessions (newest). */
    private static final int STATUS_LIST_LIMIT = 15;

    private final AgentConfig config;
    private final JobManager jobManager;
    private final Map<Integer, AgentSession> sessions = new LinkedHashMap<>();
    private final Map<Integer, AgentRunner> runners = new LinkedHashMap<>();
    private final Map<String, AgentSession> tokenIndex = new ConcurrentHashMap<>();

    private MinecraftServer server;
    private BridgeHttpServer bridge;
    private int nextSessionNo = 1;
    private volatile boolean stopping;

    public AgentSessionManager(AgentConfig config, JobManager jobManager) {
        this.config = config;
        this.jobManager = jobManager;
    }

    /** The bridge is constructed after the manager (it resolves tokens through it); wired once at init. */
    public void attachBridge(BridgeHttpServer bridge) {
        this.bridge = bridge;
    }

    public AgentConfig config() {
        return config;
    }

    public boolean isServerStopping() {
        return stopping;
    }

    // ------------------------------------------------------------------ lifecycle

    public synchronized void onServerStarted(MinecraftServer server) {
        this.server = server;
        this.stopping = false;
        sessions.clear();
        runners.clear();
        tokenIndex.clear();
        nextSessionNo = 1;

        Path file = aibuildRoot().resolve("sessions.json");
        boolean loaded = false;
        if (Files.isRegularFile(file)) {
            try {
                JsonObject o = JsonParser.parseString(Files.readString(file)).getAsJsonObject();
                nextSessionNo = Math.max(1, o.has("next_session_no") ? o.get("next_session_no").getAsInt() : 1);
                for (JsonElement el : o.getAsJsonArray("sessions")) {
                    AgentSession s = AgentSession.fromJson(el.getAsJsonObject());
                    postLoad(s);
                    sessions.put(s.no(), s);
                    nextSessionNo = Math.max(nextSessionNo, s.no() + 1);
                }
                loaded = true;
                AiBuildMod.LOGGER.info("[aibuild] restored {} session(s) from {}", sessions.size(), file);
            } catch (Exception e) {
                AiBuildMod.LOGGER.error("[aibuild] failed to load {} — starting with an empty registry", file, e);
            }
        }
        if (!loaded) {
            migrateLegacyState();
        }
        for (AgentSession s : sessions.values()) {
            s.gate().setOnChange(this::persist);
        }
        persist();
        refreshBridgeJson();
    }

    public synchronized void onServerStopping() {
        stopping = true;
        for (AgentRunner r : runners.values()) {
            r.onServerStopping();
        }
        // Running sessions stay "running" on disk: on the next start they are
        // detected as interrupted (same semantics as the old state.json).
        persist();
    }

    /** Sends resume hints for interrupted sessions to a joining player. */
    public void onPlayerJoin(ServerPlayer player) {
        AgentSession hint;
        synchronized (this) {
            hint = sessions.values().stream()
                    .filter(s -> s.status() == AgentSession.Status.FAILED && s.kimiSessionId() != null)
                    .reduce((a, b) -> b) // latest
                    .orElse(null);
        }
        if (hint != null) {
            player.sendSystemMessage(Component.literal("[aibuild] 会话 #" + hint.no() + " 未完成:"
                    + hint.description() + ",输入 /aichat 继续"));
        }
    }

    /** A session found "running" on disk lost its process with the server: mark interrupted, keep everything else. */
    private void postLoad(AgentSession s) {
        if (s.status() == AgentSession.Status.RUNNING) {
            s.status = AgentSession.Status.FAILED;
            s.lastError = "server stopped/restarted while running — /aichat 可续";
            s.endedAtMillis = System.currentTimeMillis();
        }
        if (s.sessionTag == null) {
            s.sessionTag = "b" + TAG_STAMP.format(LocalDateTime.now()) + "-s" + s.no();
        }
        tokenIndex.put(s.token(), s);
    }

    /** Pre-E3 worlds: state.json + .session_id in the aibuild root become migrated session #1. */
    private void migrateLegacyState() {
        Path root = aibuildRoot();
        Path stateFile = root.resolve("state.json");
        if (!Files.isRegularFile(stateFile)) {
            return;
        }
        try {
            JsonObject state = JsonParser.parseString(Files.readString(stateFile)).getAsJsonObject();
            AgentSession s = new AgentSession(1, UUID.randomUUID().toString(), AgentSession.LEGACY_WORK_DIR);
            s.description = state.has("description") ? state.get("description").getAsString() : "( migrated legacy build )";
            s.sessionTag = state.has("session") ? state.get("session").getAsString() : null;
            String status = state.has("status") ? state.get("status").getAsString() : "";
            switch (status) {
                case "finished" -> s.status = AgentSession.Status.DONE;
                case "cancelled" -> s.status = AgentSession.Status.CANCELLED;
                default -> {
                    s.status = AgentSession.Status.FAILED;
                    s.lastError = "interrupted (migrated from state.json) — /aichat 可续";
                }
            }
            Path idFile = root.resolve(".session_id");
            if (Files.isRegularFile(idFile)) {
                String id = Files.readString(idFile).trim();
                if (!id.isEmpty()) {
                    s.kimiSessionId = id;
                }
            }
            s.endedAtMillis = System.currentTimeMillis();
            if (s.sessionTag == null) {
                s.sessionTag = "b" + TAG_STAMP.format(LocalDateTime.now()) + "-s1";
            }
            sessions.put(s.no(), s);
            tokenIndex.put(s.token(), s);
            nextSessionNo = 2;
            AiBuildMod.LOGGER.info("[aibuild] migrated legacy state.json into session #1 (status={}, kimi session {})",
                    s.status(), s.kimiSessionId());
        } catch (Exception e) {
            AiBuildMod.LOGGER.warn("[aibuild] legacy state.json migration failed; ignoring it", e);
        }
    }

    // ------------------------------------------------------------------ commands API

    /**
     * Creates and launches a new build session. Rejects only when
     * {@code max_concurrent_agents} sessions are running, or when a wand
     * selection overlaps another running session's bounds.
     */
    public synchronized String startBuild(String description, BlockPos anchor, SiteGate.Bounds selection) throws IOException {
        int running = countRunning();
        if (running >= config.maxConcurrentAgents()) {
            throw new IllegalStateException("已达最大并发 " + config.maxConcurrentAgents()
                    + " 个会话——/aistatus 查看,/aicancel 取消或等其完成");
        }
        if (selection != null) {
            AgentSession conflict = findConflict(null, selection);
            if (conflict != null) {
                throw new IllegalStateException("选区与会话 #" + conflict.no() + " 的边界相交 ("
                        + conflict.gate().activeBounds().describe() + ")——换一块不相交的区域");
            }
        }

        int no = nextSessionNo++;
        AgentSession s = new AgentSession(no, UUID.randomUUID().toString(), "sessions/s" + no);
        s.description = description;
        s.sessionTag = "b" + TAG_STAMP.format(LocalDateTime.now()) + "-s" + no;
        s.gate().setOnChange(this::persist);
        s.gate().beginSession(selection);
        sessions.put(no, s);
        tokenIndex.put(s.token(), s);
        try {
            Path dir = prepareWorkDir(s);
            WorkDir.writeTask(dir, description, anchor, selection);
            try {
                String terrain = TerrainSummary.generate(server.overworld(), anchor.getX(), anchor.getZ(), 64);
                WorkDir.writeTerrain(dir, anchor, 64, terrain);
            } catch (Exception e) {
                AiBuildMod.LOGGER.warn("[aibuild] terrain summary generation failed; continuing without terrain.json", e);
            }
            runnerFor(s).startNew();
        } catch (IOException | RuntimeException e) {
            s.status = AgentSession.Status.FAILED;
            s.lastError = "spawn failed: " + e.getMessage();
            s.endedAtMillis = System.currentTimeMillis();
            persist();
            throw e;
        }
        persist();
        refreshBridgeJson();
        return "agent started (session #" + no + "): " + description + (selection != null
                ? " (bounds: " + selection.describe() + ")"
                : " (no selection — AI will propose a site for confirmation)");
    }

    /**
     * /aichat: queues the message into the newest RUNNING session's inbox, or
     * resumes the newest resumable session (has a kimi session id) with
     * {@code kimi -r}. Resuming counts toward the concurrency cap.
     */
    public synchronized String chat(String message) throws IOException {
        AgentSession running = latestRunning();
        if (running != null) {
            running.inbox().add(message);
            return "[已排队到会话 #" + running.no() + ",AI 下次行动时送达] " + message;
        }
        AgentSession resumable = sessions.values().stream()
                .filter(s -> s.kimiSessionId() != null && s.status() != AgentSession.Status.RUNNING)
                .reduce((a, b) -> b)
                .orElse(null);
        if (resumable == null) {
            throw new IllegalStateException("no agent session to continue — start one with /aibuild");
        }
        if (countRunning() >= config.maxConcurrentAgents()) {
            throw new IllegalStateException("已达最大并发 " + config.maxConcurrentAgents() + " 个会话,无法续跑——先 /aicancel");
        }
        AgentRunner r = runnerFor(resumable);
        resumable.status = AgentSession.Status.RUNNING;
        resumable.resumeAttempts = 0;
        resumable.lastError = null;
        resumable.endedAtMillis = null;
        prepareWorkDir(resumable);
        r.resume(message);
        persist();
        return "resuming session #" + resumable.no() + " (kimi session " + resumable.kimiSessionId() + ")";
    }

    /** /aicancel [n]: kills session n's process (or aborts its pending self-heal); without n, the newest running. */
    public synchronized String cancel(Integer no) {
        AgentSession s = no != null ? sessions.get(no) : latestRunning();
        if (s == null) {
            throw new IllegalStateException(no != null ? "会话 #" + no + " 不存在" : "no agent is running");
        }
        AgentRunner r = runners.get(s.no());
        boolean alive = r != null && r.isProcessAlive();
        if (!alive && s.status() != AgentSession.Status.RUNNING) {
            throw new IllegalStateException("会话 #" + s.no() + " 未在运行 (status: "
                    + s.status().name().toLowerCase(java.util.Locale.ROOT) + ")");
        }
        if (r != null) {
            r.cancel("cancelled by /aicancel");
        }
        persist();
        return "会话 #" + s.no() + " cancelled";
    }

    /** /aistatus: one summary line plus one line per session (newest first, capped). */
    public synchronized List<String> statusLines() {
        List<String> out = new ArrayList<>();
        out.add("sessions: " + sessions.size() + " total, " + countRunning() + " running (max "
                + config.maxConcurrentAgents() + ")");
        List<AgentSession> newestFirst = new ArrayList<>(sessions.values());
        newestFirst.sort((a, b) -> Integer.compare(b.no(), a.no()));
        int shown = 0;
        for (AgentSession s : newestFirst) {
            if (++shown > STATUS_LIST_LIMIT) {
                out.add("… (" + (newestFirst.size() - STATUS_LIST_LIMIT) + " older sessions omitted)");
                break;
            }
            StringBuilder sb = new StringBuilder("#").append(s.no())
                    .append(" [").append(s.status().name().toLowerCase(java.util.Locale.ROOT)).append("] ")
                    .append(s.description());
            SiteGate.Bounds active = s.gate().activeBounds();
            String gateNote = switch (s.gate().state()) {
                case CONFIRMED -> " bounds confirmed " + (active != null ? active.describe() : "?");
                case PENDING_CONFIRMATION -> " proposal PENDING " + (active != null ? active.describe() : "?");
                case AWAITING_PROPOSAL -> " awaiting proposal";
                case UNBOUND -> " unbound";
            };
            sb.append(" |").append(gateNote);
            sb.append(" | ").append(s.statsSummary());
            if (s.kimiSessionId() != null) {
                sb.append(" | kimi ").append(s.kimiSessionId(), 0, Math.min(8, s.kimiSessionId().length())).append("…");
            }
            if (s.lastError != null) {
                sb.append(" | err: ").append(s.lastError);
            }
            out.add(sb.toString());
        }
        return out;
    }

    /** /aiconfirm: confirms the NEWEST pending proposal (its session gets the player message). */
    public synchronized String confirm() {
        AgentSession s = latestPending();
        if (s == null) {
            throw new IllegalStateException("no pending site proposal");
        }
        SiteGate.Bounds confirmed = s.gate().confirm();
        s.inbox().add("玩家已确认选址 " + confirmed.describe() + ";写工具已解锁,请在该范围内施工");
        persist();
        return "#" + s.no() + " site confirmed: " + confirmed.describe();
    }

    /** /aireject: rejects the NEWEST pending proposal. */
    public synchronized String reject() {
        AgentSession s = latestPending();
        if (s == null) {
            throw new IllegalStateException("no pending site proposal");
        }
        SiteGate.Bounds rejected = s.gate().reject();
        s.inbox().add("玩家拒绝了选址 " + rejected.describe() + ";请重新 propose_site 选择其他位置");
        persist();
        return "#" + s.no() + " site rejected: " + rejected.describe() + " — AI has been asked to propose elsewhere";
    }

    /** /aiundo guard: any session with a live (or self-heal-pending) agent. */
    public synchronized boolean anyRunning() {
        return countRunning() > 0;
    }

    // ------------------------------------------------------------------ bridge routing

    /** Session owning this bridge token, or null (master token / unknown). */
    public AgentSession sessionForToken(String token) {
        return token == null ? null : tokenIndex.get(token);
    }

    /**
     * Default session for requests bearing the master token (compat for
     * token-less tooling): the newest RUNNING session, or null when none —
     * write tools then answer 409.
     */
    public AgentSession defaultSession() {
        synchronized (this) {
            return latestRunning();
        }
    }

    /**
     * First RUNNING session whose confirmed bounds or pending proposal
     * intersects {@code b} (excluding {@code self}), or null. Spatial
     * isolation: overlapping proposals get a 409 naming the conflicting session.
     */
    public synchronized AgentSession findConflict(AgentSession self, SiteGate.Bounds b) {
        for (AgentSession s : sessions.values()) {
            if (s == self || s.status() != AgentSession.Status.RUNNING) {
                continue;
            }
            SiteGate.Bounds other = s.gate().activeBounds();
            if (other != null && other.intersects(b)) {
                return s;
            }
        }
        return null;
    }

    // ------------------------------------------------------------------ runner support

    /** (Re)writes the session's working directory (mcp.json carries the current port + session token). */
    public Path prepareWorkDir(AgentSession s) throws IOException {
        return WorkDir.prepare(s.workDir(aibuildRoot()), bridge.port(), s.token());
    }

    public Path aibuildRoot() {
        return WorkDir.dirOf(server);
    }

    public MinecraftServer server() {
        return server;
    }

    AgentRunner runnerFor(AgentSession s) {
        return runners.computeIfAbsent(s.no(), k -> new AgentRunner(config, s, jobManager, this));
    }

    public void broadcast(String message) {
        AiBuildMod.LOGGER.info("[aibuild-chat] {}", message);
        MinecraftServer s;
        synchronized (this) {
            s = server;
        }
        if (s != null) {
            s.execute(() -> s.getPlayerList().broadcastSystemMessage(Component.literal(message), false));
        }
    }

    // ------------------------------------------------------------------ persistence

    /** Writes the whole registry to sessions.json (tmp + atomic move). Best-effort; called on every change. */
    public synchronized void persist() {
        if (server == null) {
            return;
        }
        try {
            JsonObject o = new JsonObject();
            o.addProperty("version", 1);
            o.addProperty("next_session_no", nextSessionNo);
            o.addProperty("updated", Instant.now().toString());
            JsonArray arr = new JsonArray();
            for (AgentSession s : sessions.values()) {
                arr.add(s.toJson());
            }
            o.add("sessions", arr);
            Path file = aibuildRoot().resolve("sessions.json");
            Path tmp = aibuildRoot().resolve("sessions.json.tmp");
            Files.writeString(tmp, GSON.toJson(o) + System.lineSeparator());
            try {
                Files.move(tmp, file, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } catch (IOException atomicFailed) {
                Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING);
            }
        } catch (Exception e) {
            AiBuildMod.LOGGER.warn("[aibuild] failed to persist sessions.json", e);
        }
    }

    /** Rewrites bridge.json (port + master token + per-session tokens) for external tooling. */
    public void refreshBridgeJson() {
        BridgeHttpServer b = bridge;
        if (b == null) {
            return;
        }
        Map<Integer, String> tokens = new LinkedHashMap<>();
        synchronized (this) {
            for (AgentSession s : sessions.values()) {
                tokens.put(s.no(), s.token());
            }
        }
        b.refreshBridgeJson(tokens);
    }

    // ------------------------------------------------------------------ internals

    private AgentSession latestRunning() {
        AgentSession latest = null;
        for (AgentSession s : sessions.values()) {
            if (s.status() == AgentSession.Status.RUNNING) {
                latest = s;
            }
        }
        return latest;
    }

    private AgentSession latestPending() {
        AgentSession latest = null;
        for (AgentSession s : sessions.values()) {
            if (s.status() == AgentSession.Status.RUNNING
                    && s.gate().state() == SiteGate.State.PENDING_CONFIRMATION
                    && (latest == null || s.gate().proposalAtMillis() >= latest.gate().proposalAtMillis())) {
                latest = s;
            }
        }
        return latest;
    }

    private int countRunning() {
        int n = 0;
        for (AgentSession s : sessions.values()) {
            if (s.status() == AgentSession.Status.RUNNING) {
                n++;
            }
        }
        return n;
    }
}
