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
import java.nio.charset.StandardCharsets;
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
        backfillTokenUsage();
        persist();
        refreshBridgeJson();
    }

    /**
     * One-shot token-bill backfill for sessions restored from disk that have a
     * kimi session id but no recorded usage yet (they ran before billing
     * existed): sums their wire.jsonl usage records once. Absolute totals, so
     * re-running it on later starts is a no-op. Best-effort.
     */
    private void backfillTokenUsage() {
        int backfilled = 0;
        for (AgentSession s : sessions.values()) {
            if (s.kimiSessionId() == null || s.totalTokens() > 0) {
                continue;
            }
            try {
                TokenUsage total = TokenUsage.sumWireRecords(s.kimiSessionId());
                if (total == null) {
                    continue;
                }
                synchronized (s) {
                    s.tokenInput = Math.max(s.tokenInput, total.input());
                    s.tokenOutput = Math.max(s.tokenOutput, total.output());
                    s.tokenCacheRead = Math.max(s.tokenCacheRead, total.cacheRead());
                }
                backfilled++;
            } catch (Exception e) {
                AiBuildMod.LOGGER.warn("[aibuild] token usage backfill failed for session #{}", s.no(), e);
            }
        }
        if (backfilled > 0) {
            AiBuildMod.LOGGER.info("[aibuild] backfilled token usage for {} session(s)", backfilled);
        }
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
        // @path: read the real task brief from a file under the aibuild root
        // (RCON/chat command length limits make long inline descriptions impossible).
        if (description.startsWith("@")) {
            Path root = aibuildRoot().toAbsolutePath().normalize();
            Path taskFile = root.resolve(description.substring(1)).normalize();
            if (!taskFile.startsWith(root) || !Files.isRegularFile(taskFile)) {
                throw new IOException("task file not found under aibuild root: " + description.substring(1));
            }
            description = Files.readString(taskFile, StandardCharsets.UTF_8).trim();
        }

        AgentSession s = createSession(description, anchor, selection);
        // intake gate: unless escaped, an interviewer agent (a real LLM — it
        // reads the request, decides what to ask and how much) runs BEFORE the
        // builder spawns. Escape words skip it entirely.
        if (config.intakeEnabled() && !skipsIntake(description)) {
            s.status = AgentSession.Status.INTAKE;
            try {
                Path dir = prepareWorkDir(s);
                WorkDir.writeTask(dir, s.description, anchor, selection);
                try {
                    String terrain = TerrainSummary.generate(server.overworld(), anchor.getX(), anchor.getZ(), 64);
                    WorkDir.writeTerrain(dir, anchor, 64, terrain);
                } catch (Exception e) {
                    AiBuildMod.LOGGER.warn("[aibuild] terrain summary generation failed; continuing without terrain.json", e);
                }
                runnerFor(s).startIntake();
            } catch (IOException | RuntimeException e) {
                s.status = AgentSession.Status.FAILED;
                s.lastError = "intake spawn failed: " + e.getMessage();
                s.endedAtMillis = System.currentTimeMillis();
                persist();
                throw e;
            }
            persist();
            refreshBridgeJson();
            return "session #" + s.no() + " 已创建,访谈 agent 启动中——它先问清楚再开工 (说「跳过」= 直接造)";
        }
        launch(s, anchor, selection);
        String brief = description.length() > 60 ? description.substring(0, 60) + "…" : description;
        return "agent started (session #" + s.no() + "): " + brief + (selection != null
                ? " (bounds: " + selection.describe() + ")"
                : " (no selection — AI will propose a site for confirmation)");
    }

    /** Creates and registers a session (stays INTAKE or launches immediately). */
    private AgentSession createSession(String description, BlockPos anchor, SiteGate.Bounds selection) {
        int no = nextSessionNo++;
        AgentSession s = new AgentSession(no, UUID.randomUUID().toString(), "sessions/s" + no);
        s.description = description;
        s.anchor = anchor;
        s.sessionTag = "b" + TAG_STAMP.format(LocalDateTime.now()) + "-s" + no;
        s.gate().setOnChange(this::persist);
        s.gate().beginSession(selection);
        sessions.put(no, s);
        tokenIndex.put(s.token(), s);
        return s;
    }

    /** Spawns the agent process: work dir + task.json + terrain, then startNew. */
    private void launch(AgentSession s, BlockPos anchor, SiteGate.Bounds selection) throws IOException {
        try {
            Path dir = prepareWorkDir(s);
            WorkDir.writeTask(dir, s.description, anchor, selection);
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
    }

    /**
     * /aichat: queues the message into the newest RUNNING session's inbox, or
     * resumes the newest resumable session (has a kimi session id) with
     * {@code kimi -r}. Resuming counts toward the concurrency cap.
     */
    public synchronized String chat(String message) throws IOException {
        AgentSession intake = latestIntake();
        if (intake != null) {
            AgentRunner r = runnerFor(intake);
            if (r.isProcessAlive()) {
                intake.inbox().add(message);
                return "[已排队到访谈会话 #" + intake.no() + ",AI 下次行动时送达] " + message;
            }
            if (intake.description.contains("[访谈确认]")) {
                // interview done but the launch was cap-blocked — retry (idempotent)
                completeIntake(intake);
                return "会话 #" + intake.no() + " 开工重试中——/aistatus 查看";
            }
            if (intake.kimiSessionId() != null) {
                if (countRunning() >= config.maxConcurrentAgents()) {
                    throw new IllegalStateException("已达最大并发 " + config.maxConcurrentAgents() + " 个会话,无法续跑访谈——先 /aicancel");
                }
                prepareWorkDir(intake);
                r.resume(message);
                persist();
                return "resuming intake session #" + intake.no() + " (访谈继续): " + message;
            }
            throw new IllegalStateException("会话 #" + intake.no() + " 访谈进程不在且无会话记录——/aicancel 后重新 /aibuild");
        }
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
        AgentSession s = no != null ? sessions.get(no) : latestActive();
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
            if (s.status() == AgentSession.Status.INTAKE) {
                sb.append(" | 访谈进行中(/aichat 回答,「跳过」=直接造)");
                out.add(sb.toString());
                continue;
            }
            SiteGate.Bounds active = s.gate().activeBounds();
            String gateNote = switch (s.gate().state()) {
                case CONFIRMED -> " bounds confirmed " + (active != null ? active.describe() : "?");
                case PENDING_CONFIRMATION -> " proposal PENDING " + (active != null ? active.describe() : "?");
                case AWAITING_PROPOSAL -> " awaiting proposal";
                case UNBOUND -> " unbound";
            };
            sb.append(" |").append(gateNote);
            sb.append(" | ").append(s.statsSummary());
            if (s.totalTokens() > 0) {
                sb.append(" | ").append(s.tokenSummary());
            }
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

    /** Occupied-map entry: one session (any status) with confirmed bounds. */
    public record OccupiedSite(int sessionNo, SiteGate.Bounds bounds) {
    }

    /**
     * The occupied map: confirmed bounds of EVERY session that has one, any
     * status (DONE/FAILED/CANCELLED/RUNNING — tiny test boxes count too).
     * Used by analyze_site to keep new builds off previously built ground.
     */
    public synchronized List<OccupiedSite> occupiedSites() {
        List<OccupiedSite> out = new ArrayList<>();
        for (AgentSession s : sessions.values()) {
            SiteGate.Bounds b = s.gate().currentBounds();
            if (b != null) {
                out.add(new OccupiedSite(s.no(), b));
            }
        }
        return out;
    }

    /**
     * Occupied-map overlap for the propose_site soft warning: non-RUNNING
     * sessions (excluding {@code self}) whose confirmed bounds intersect
     * {@code b}. RUNNING sessions are covered by the hard 409 in
     * {@link #findConflict}; these historical overlaps only warn, never block.
     */
    public synchronized List<AgentSession> occupiedOverlap(AgentSession self, SiteGate.Bounds b) {
        List<AgentSession> out = new ArrayList<>();
        for (AgentSession s : sessions.values()) {
            if (s == self || s.status() == AgentSession.Status.RUNNING) {
                continue;
            }
            SiteGate.Bounds other = s.gate().currentBounds();
            if (other != null && other.intersects(b)) {
                out.add(s);
            }
        }
        return out;
    }

    // ------------------------------------------------------------------ runner support

    /** (Re)writes the session's working directory (mcp.json carries the current port + session token; manual matches the phase). */
    public Path prepareWorkDir(AgentSession s) throws IOException {
        Path dir = WorkDir.prepare(s.workDir(aibuildRoot()), bridge.port(), s.token(),
                s.status() == AgentSession.Status.INTAKE);
        // Shared style library: cards authored by past interviewers/builders
        // are available in every session (shared copy is the source of truth).
        Path shared = sharedStylesDir();
        if (Files.isDirectory(shared)) {
            Path target = dir.resolve("styles");
            Files.createDirectories(target);
            try (var stream = Files.list(shared)) {
                for (Path card : stream.filter(p -> p.toString().endsWith(".json")).toList()) {
                    Files.copy(card, target.resolve(card.getFileName().toString()),
                            StandardCopyOption.REPLACE_EXISTING);
                }
            }
        }
        return dir;
    }

    /** User-authored style cards live here and are seeded into every session's styles/. */
    private Path sharedStylesDir() {
        return aibuildRoot().resolve("shared_styles");
    }

    /**
     * Promotes NEW style cards from a session's styles/ into the shared
     * library (write-if-absent; bundled defaults are skipped). Called at
     * intake handoff and on session termination.
     */
    public void promoteSharedStyles(AgentSession s) {
        try {
            Path styles = s.workDir(aibuildRoot()).resolve("styles");
            if (!Files.isDirectory(styles)) {
                return;
            }
            Path shared = sharedStylesDir();
            try (var stream = Files.list(styles)) {
                for (Path card : stream.filter(p -> p.toString().endsWith(".json")).toList()) {
                    if (WorkDir.DEFAULT_ASSETS.contains("styles/" + card.getFileName().toString())) {
                        continue; // bundled default, not user-authored
                    }
                    Path target = shared.resolve(card.getFileName().toString());
                    if (!Files.exists(target)) {
                        Files.createDirectories(shared);
                        Files.copy(card, target);
                        AiBuildMod.LOGGER.info("[aibuild] #{} promoted new style card {} to shared library",
                                s.no(), card.getFileName());
                        broadcast("[aibuild] #" + s.no() + " 新风格卡 " + card.getFileName() + " 已收入共享库");
                    }
                }
            }
        } catch (IOException e) {
            AiBuildMod.LOGGER.warn("[aibuild] #{} style card promotion failed", s.no(), e);
        }
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

    // ------------------------------------------------------------------ intake interview

    private static final List<String> INTAKE_SKIP_WORDS = List.of("随便", "你定", "直接造");
    /** intake_brief.md is appended verbatim into the task description — cap it. */
    private static final int INTAKE_BRIEF_MAX_CHARS = 4000;

    private static boolean skipsIntake(String description) {
        for (String w : INTAKE_SKIP_WORDS) {
            if (description.contains(w)) {
                return true;
            }
        }
        return false;
    }

    private AgentSession latestIntake() {
        AgentSession latest = null;
        for (AgentSession s : sessions.values()) {
            if (s.status() == AgentSession.Status.INTAKE) {
                latest = s;
            }
        }
        return latest;
    }

    /** Newest session that can be cancelled: INTAKE (newest first) or RUNNING. */
    private AgentSession latestActive() {
        AgentSession latest = latestRunning();
        AgentSession intake = latestIntake();
        return intake != null && (latest == null || intake.no() > latest.no()) ? intake : latest;
    }

    /**
     * Interview handoff (called by AgentRunner on the interviewer's clean exit,
     * or by /aichat as a cap-blocked retry). Idempotent: the brief is appended
     * once; later calls only retry the launch.
     */
    public synchronized void completeIntake(AgentSession s) {
        try {
            if (!s.description.contains("[访谈确认]")) {
                String brief = readIntakeBrief(s);
                if (brief != null) {
                    s.description = s.description + "\n\n[访谈确认]\n" + brief;
                } else {
                    AiBuildMod.LOGGER.warn("[aibuild] #{} interviewer exited without intake_brief.md — building from the raw description", s.no());
                    broadcast("[aibuild] #" + s.no() + " 访谈 agent 没留下纪要,按原描述直接开工");
                }
            }
            if (countRunning() >= config.maxConcurrentAgents()) {
                broadcast("[aibuild] #" + s.no() + " 访谈完成,但并发已满——/aicancel 其他会话后再 /aichat 任意内容开工");
                persist();
                return;
            }
            s.status = AgentSession.Status.RUNNING;
            promoteSharedStyles(s); // interviewer-authored draft cards → shared library
            // 访谈可能聊了许久——s.anchor 是 /aibuild 那一刻的旧位置;选址说"玩家附近"
            // 时锚的应是此刻的玩家。无在线玩家(RCON)时退回原锚点/出生点。
            BlockPos anchor = s.anchor;
            var online = server.getPlayerList().getPlayers();
            if (!online.isEmpty()) {
                anchor = online.get(0).blockPosition();
            }
            if (anchor == null) {
                anchor = server.overworld().getRespawnData().pos();
            }
            broadcast("[aibuild] #" + s.no() + " 访谈完成,建造 agent 开工");
            launch(s, anchor, s.gate().currentBounds());
        } catch (IOException | RuntimeException e) {
            s.status = AgentSession.Status.FAILED;
            s.lastError = "intake handoff failed: " + e.getMessage();
            s.endedAtMillis = System.currentTimeMillis();
            persist();
            broadcast("[aibuild] #" + s.no() + " 访谈交接失败: " + e.getMessage() + " — /aichat 可续");
        }
    }

    /** The interviewer's work product, or null when missing/blank. */
    private String readIntakeBrief(AgentSession s) {
        try {
            Path file = s.workDir(aibuildRoot()).resolve("intake_brief.md");
            if (!Files.isRegularFile(file)) {
                return null;
            }
            String text = Files.readString(file, StandardCharsets.UTF_8).trim();
            if (text.isEmpty()) {
                return null;
            }
            return text.length() > INTAKE_BRIEF_MAX_CHARS ? text.substring(0, INTAKE_BRIEF_MAX_CHARS) : text;
        } catch (IOException e) {
            AiBuildMod.LOGGER.warn("[aibuild] #{} failed to read intake_brief.md", s.no(), e);
            return null;
        }
    }
}
