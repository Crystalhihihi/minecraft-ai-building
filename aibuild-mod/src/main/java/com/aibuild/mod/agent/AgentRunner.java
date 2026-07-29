package com.aibuild.mod.agent;

import com.aibuild.mod.AiBuildMod;
import com.aibuild.mod.bridge.BridgeHttpServer;
import com.aibuild.mod.bridge.PlayerInbox;
import com.aibuild.mod.bridge.SiteGate;
import com.aibuild.mod.bridge.TerrainSummary;
import com.aibuild.mod.config.AgentConfig;
import com.aibuild.mod.job.JobManager;
import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Spawns the headless agent CLI (kimi) in the per-world working directory,
 * parses its stream-json stdout line by line (assistant text -> game chat,
 * tool_calls -> one merged chat line per assistant message, meta lines ->
 * session id), enforces the two timeouts (dual-channel silence + hard cap),
 * and supports /aicancel via destroyForcibly.
 *
 * Lifecycle: one agent at a time. The "already running" check and the spawn
 * are atomic via {@link #launchGuard} CAS (a guard held from spawn until
 * onExit), closing the double-start race where a fast-dying first process let
 * a second /aibuild through.
 *
 * Per build session it also: writes {@code <world>/aibuild/state.json}
 * (running/finished/cancelled + description + snapshot session tag) for
 * crash/shutdown resume hints, stamps snapshots with a build-session tag via
 * {@link JobManager#beginBuildSession}, and broadcasts a consumption report
 * (turns / tool calls / blocks placed / wall time) on agent exit.
 */
public final class AgentRunner {
    private static final DateTimeFormatter LOG_STAMP = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss");
    private static final Gson GSON = new Gson();
    /** stream-json MCP tool prefix, stripped for chat display and stats. */
    private static final String MCP_PREFIX = "mcp__aibuild__";

    private final AgentConfig config;
    private final PlayerInbox inbox;
    private final BridgeHttpServer bridge;
    private final SiteGate gate;
    private final JobManager jobManager;

    private MinecraftServer server;
    private String sessionId;

    private Process process;
    private Path workDir;
    private BufferedWriter logWriter;
    private volatile long lastIoMillis;
    private long startedMillis;
    /** Null while running normally; set before killing so onExit reports the right cause. */
    private String stopReason;
    /** Held from a successful CAS in startBuild/startChat until onExit (or spawn failure). */
    private final AtomicBoolean launchGuard = new AtomicBoolean(false);

    // per-build consumption counters (reset in startBuild, accumulate across /aichat resumes)
    private int buildTurns;
    private int buildToolCalls;
    private final Map<String, Integer> buildToolCounts = new LinkedHashMap<>();
    private long buildPlacedStart;
    private long buildWallStartMillis;
    private String buildDescription;
    /** Snapshot session tag ("b<timestamp>"); restored from state.json for resumes. */
    private String buildSessionTag;
    /** Description of an unfinished build detected at server start; shown to joining players. */
    private String pendingResumeHint;

    public AgentRunner(AgentConfig config, PlayerInbox inbox, BridgeHttpServer bridge, SiteGate gate, JobManager jobManager) {
        this.config = config;
        this.inbox = inbox;
        this.bridge = bridge;
        this.gate = gate;
        this.jobManager = jobManager;
    }

    public synchronized void onServerStarted(MinecraftServer server) {
        this.server = server;
        this.sessionId = null;
        this.pendingResumeHint = null;
        Path sessionFile = WorkDir.dirOf(server).resolve(".session_id");
        try {
            if (Files.isRegularFile(sessionFile)) {
                String id = Files.readString(sessionFile).trim();
                if (!id.isEmpty()) {
                    this.sessionId = id;
                    AiBuildMod.LOGGER.info("[aibuild] restored agent session id {} from {}", id, sessionFile);
                }
            }
        } catch (IOException e) {
            AiBuildMod.LOGGER.warn("[aibuild] could not read {}", sessionFile, e);
        }
        // crash/shutdown detection: a state.json still saying "running" means
        // the previous server died (or stopped) mid-build without an onExit.
        JsonObject state = readState();
        if (state != null && "running".equals(optString(state, "status"))) {
            buildDescription = optString(state, "description");
            buildSessionTag = optString(state, "session");
            if (sessionId != null) {
                pendingResumeHint = buildDescription != null ? buildDescription : "(无描述)";
                broadcast("[aibuild] 上次建造未完成:" + pendingResumeHint + ",输入 /aichat 继续");
            } else {
                AiBuildMod.LOGGER.warn("[aibuild] previous build died mid-run ({}) but no .session_id to resume with",
                        buildDescription);
            }
        }
    }

    public synchronized void onServerStopping() {
        if (process != null) {
            stopReason = "server stopping";
            process.destroyForcibly();
        }
    }

    public synchronized boolean isRunning() {
        return launchGuard.get();
    }

    public synchronized boolean hasSession() {
        return sessionId != null;
    }

    public void enqueuePlayerMessage(String message) {
        inbox.add(message);
    }

    /** Sends the unfinished-build hint to a joining player (registered on ServerPlayConnectionEvents.JOIN). */
    public void onPlayerJoin(ServerPlayer player) {
        String hint;
        synchronized (this) {
            hint = pendingResumeHint;
        }
        if (hint != null) {
            player.sendSystemMessage(Component.literal("[aibuild] 上次建造未完成:" + hint + ",输入 /aichat 继续"));
        }
    }

    // ------------------------------------------------------------------ spawns

    /**
     * Starts a new build session. When {@code selection} is non-null the write
     * tools are immediately bound to it; otherwise the session starts
     * unconfirmed and the AI's first tool call must be propose_site.
     * Called on the server main thread (from command execution) — the terrain
     * summary samples the world inline.
     *
     * The running-check + spawn is atomic via {@link #launchGuard}: a second
     * /aibuild issued while the first agent is starting (or a first process
     * that died instantly) is always rejected.
     */
    public synchronized void startBuild(String description, BlockPos anchor, SiteGate.Bounds selection) throws IOException {
        if (!launchGuard.compareAndSet(false, true)) {
            throw new IllegalStateException("an agent is already running");
        }
        try {
            gate.beginSession(selection);
            Path dir = WorkDir.prepare(server, bridge.port(), bridge.token());
            WorkDir.writeTask(dir, description, anchor, selection);
            try {
                String terrain = TerrainSummary.generate(server.overworld(), anchor.getX(), anchor.getZ(), 64);
                WorkDir.writeTerrain(dir, anchor, 64, terrain);
            } catch (Exception e) {
                AiBuildMod.LOGGER.warn("[aibuild] terrain summary generation failed; continuing without terrain.json", e);
            }
            // consumption counters start fresh for the new build
            buildTurns = 0;
            buildToolCalls = 0;
            buildToolCounts.clear();
            buildPlacedStart = jobManager.lifetimePlaced();
            buildWallStartMillis = System.currentTimeMillis();
            buildDescription = description;
            buildSessionTag = "b" + LOG_STAMP.format(LocalDateTime.now());
            jobManager.beginBuildSession(buildSessionTag);
            pendingResumeHint = null;
            writeState("running");
            List<String> args = List.of(
                    config.resolvedAgentCommand(),
                    "-p", "Read AGENTS.md and task.json in the current directory, then carry out the building task described in task.json.",
                    "--output-format", "stream-json");
            spawn(dir, args);
            broadcast(selection != null
                    ? "[aibuild] agent started: " + description + " (bounds: " + selection.describe() + ")"
                    : "[aibuild] agent started: " + description + " (no selection — AI will propose a site for confirmation)");
        } catch (IOException | RuntimeException e) {
            jobManager.endBuildSession();
            launchGuard.set(false);
            throw e;
        }
    }

    public synchronized void startChat(String message) throws IOException {
        if (!launchGuard.compareAndSet(false, true)) {
            throw new IllegalStateException("an agent is already running");
        }
        try {
            if (sessionId == null) {
                throw new IOException("no session to resume");
            }
            Path dir = WorkDir.prepare(server, bridge.port(), bridge.token());
            // continue the same snapshot session if we know it (from state.json); otherwise the
            // resume predates session tagging and snapshots join the "unknown session" group
            jobManager.beginBuildSession(buildSessionTag);
            pendingResumeHint = null;
            writeState("running");
            List<String> args = List.of(
                    config.resolvedAgentCommand(),
                    "-r", sessionId,
                    "-p", message,
                    "--output-format", "stream-json");
            spawn(dir, args);
            broadcast("[aibuild] agent resumed (session " + sessionId + "): " + message);
        } catch (IOException | RuntimeException e) {
            jobManager.endBuildSession();
            launchGuard.set(false);
            throw e;
        }
    }

    public synchronized void cancel() {
        if (process != null && process.isAlive()) {
            stopReason = "cancelled by /aicancel";
            process.destroyForcibly();
            AiBuildMod.LOGGER.info("[aibuild] agent process killed by /aicancel");
        }
    }

    private void spawn(Path dir, List<String> args) throws IOException {
        this.workDir = dir;
        this.stopReason = null;
        this.startedMillis = System.currentTimeMillis();
        this.lastIoMillis = startedMillis;

        Path logFile = dir.resolve("logs").resolve("agent-" + LOG_STAMP.format(LocalDateTime.now()) + ".log");
        this.logWriter = Files.newBufferedWriter(logFile, StandardCharsets.UTF_8);
        AiBuildMod.LOGGER.info("[aibuild] spawning agent: {} (cwd={}, log={})", String.join(" ", args), dir, logFile);

        ProcessBuilder pb = new ProcessBuilder(new ArrayList<>(args));
        pb.directory(dir.toFile());
        Process p;
        try {
            p = pb.start();
        } catch (IOException e) {
            closeLog();
            throw new IOException("failed to spawn agent command '" + args.get(0) + "': " + e.getMessage(), e);
        }
        this.process = p;

        Thread stdout = pump(p.inputReader(StandardCharsets.UTF_8), "stdout", this::handleStdoutLine);
        Thread stderr = pump(p.errorReader(StandardCharsets.UTF_8), "stderr", line -> log("stderr | " + line));
        Thread waiter = daemon("aibuild-agent-wait", () -> {
            int code;
            try {
                code = p.waitFor();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
            try {
                stdout.join(5000);
                stderr.join(5000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            onExit(code);
        });
        Thread watchdog = daemon("aibuild-agent-watchdog", this::watchLoop);
        stdout.start();
        stderr.start();
        waiter.start();
        watchdog.start();
    }

    // ------------------------------------------------------------------ io

    private Thread pump(BufferedReader reader, String name, java.util.function.Consumer<String> handler) {
        return daemon("aibuild-agent-" + name, () -> {
            String line;
            try {
                while ((line = reader.readLine()) != null) {
                    lastIoMillis = System.currentTimeMillis();
                    try {
                        handler.accept(line);
                    } catch (Exception e) {
                        AiBuildMod.LOGGER.warn("[aibuild] error handling agent {} line", name, e);
                    }
                }
            } catch (IOException e) {
                AiBuildMod.LOGGER.debug("[aibuild] agent {} stream closed: {}", name, e.toString());
            }
        });
    }

    private void handleStdoutLine(String line) {
        log("stdout | " + line);
        JsonObject o;
        try {
            JsonElement el = JsonParser.parseString(line);
            if (!el.isJsonObject()) {
                return;
            }
            o = el.getAsJsonObject();
        } catch (Exception e) {
            return; // not JSON — already in the log file
        }
        String role = o.has("role") && o.get("role").isJsonPrimitive() ? o.get("role").getAsString() : "";
        switch (role) {
            case "assistant" -> {
                synchronized (this) {
                    buildTurns++;
                }
                String text = extractText(o.get("content"));
                if (!text.isBlank()) {
                    broadcast("[AI] " + text);
                }
                forwardToolCalls(o);
            }
            case "meta" -> {
                String type = o.has("type") && o.get("type").isJsonPrimitive() ? o.get("type").getAsString() : "";
                if ("session.resume_hint".equals(type) && o.has("session_id")) {
                    String id = o.get("session_id").getAsString();
                    synchronized (this) {
                        this.sessionId = id;
                    }
                    try {
                        Files.writeString(workDir.resolve(".session_id"), id + System.lineSeparator());
                    } catch (IOException e) {
                        AiBuildMod.LOGGER.warn("[aibuild] failed to persist session id", e);
                    }
                    AiBuildMod.LOGGER.info("[aibuild] agent session id: {}", id);
                }
            }
            default -> {
                // tool results etc.: log file only
            }
        }
    }

    /**
     * Forwards an assistant message's tool_calls to the chat bar, throttled to
     * ONE merged line per assistant message: consecutive calls of the same
     * tool collapse into a count ("[AI] 调用 fill ×3、render_region ×1").
     * Also folds the calls into the per-build consumption stats.
     * stream-json shape (verified against agent logs):
     * {@code {"role":"assistant","tool_calls":[{"type":"function","function":{"name":"mcp__aibuild__fill","arguments":"..."}}]}}.
     */
    private void forwardToolCalls(JsonObject assistant) {
        if (!assistant.has("tool_calls") || !assistant.get("tool_calls").isJsonArray()) {
            return;
        }
        Map<String, Integer> perMessage = new LinkedHashMap<>(); // first-seen order
        for (JsonElement el : assistant.getAsJsonArray("tool_calls")) {
            String name = toolName(el);
            if (name != null) {
                perMessage.merge(name, 1, Integer::sum);
            }
        }
        if (perMessage.isEmpty()) {
            return;
        }
        int total = perMessage.values().stream().mapToInt(Integer::intValue).sum();
        synchronized (this) {
            buildToolCalls += total;
            perMessage.forEach((name, count) -> buildToolCounts.merge(name, count, Integer::sum));
        }
        StringBuilder sb = new StringBuilder("[AI] 调用 ");
        boolean first = true;
        for (Map.Entry<String, Integer> e : perMessage.entrySet()) {
            if (!first) {
                sb.append("、");
            }
            sb.append(e.getKey());
            if (e.getValue() > 1) {
                sb.append(" ×").append(e.getValue());
            }
            first = false;
        }
        broadcast(sb.toString());
    }

    /** Extracts and shortens a tool name from a tool_calls entry ("mcp__aibuild__fill" -> "fill"). */
    private static String toolName(JsonElement el) {
        try {
            JsonObject fn = el.getAsJsonObject().getAsJsonObject("function");
            String name = fn.get("name").getAsString();
            return name.startsWith(MCP_PREFIX) ? name.substring(MCP_PREFIX.length()) : name;
        } catch (Exception e) {
            return null; // malformed entry — ignore (raw line already in the log file)
        }
    }

    private static String extractText(JsonElement content) {
        if (content == null || content.isJsonNull()) {
            return "";
        }
        if (content.isJsonPrimitive()) {
            return content.getAsString();
        }
        if (content.isJsonArray()) {
            StringBuilder sb = new StringBuilder();
            for (JsonElement part : content.getAsJsonArray()) {
                if (part.isJsonObject()) {
                    JsonObject po = part.getAsJsonObject();
                    if (po.has("text") && po.get("text").isJsonPrimitive()) {
                        if (sb.length() > 0) {
                            sb.append('\n');
                        }
                        sb.append(po.get("text").getAsString());
                    }
                }
            }
            return sb.toString();
        }
        return "";
    }

    // ------------------------------------------------------------------ lifecycle

    private void watchLoop() {
        long idleLimit = config.idleTimeoutMinutes() * 60_000L;
        long hardLimit = config.hardTimeoutMinutes() * 60_000L;
        while (true) {
            Process p;
            synchronized (this) {
                p = process;
            }
            if (p == null || !p.isAlive()) {
                return;
            }
            long now = System.currentTimeMillis();
            String reason = null;
            if (now - lastIoMillis > idleLimit) {
                reason = "idle timeout (" + config.idleTimeoutMinutes() + " min without any stdout/stderr output)";
            } else if (now - startedMillis > hardLimit) {
                reason = "hard timeout (" + config.hardTimeoutMinutes() + " min)";
            }
            if (reason != null) {
                synchronized (this) {
                    stopReason = reason;
                }
                AiBuildMod.LOGGER.warn("[aibuild] killing agent: {}", reason);
                p.destroyForcibly();
                return;
            }
            try {
                Thread.sleep(2000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }

    private void onExit(int code) {
        String reason;
        int turns, toolCalls;
        Map<String, Integer> toolCounts;
        long placed, wallMillis;
        synchronized (this) {
            if (process == null) {
                return;
            }
            process = null;
            reason = stopReason;
            turns = buildTurns;
            toolCalls = buildToolCalls;
            toolCounts = new LinkedHashMap<>(buildToolCounts);
            placed = jobManager.lifetimePlaced() - buildPlacedStart;
            wallMillis = System.currentTimeMillis() - buildWallStartMillis;
            launchGuard.set(false);
        }
        closeLog();
        if (reason != null) {
            broadcast("[aibuild] agent stopped: " + reason + ". Blocks placed so far remain; /aichat can continue the session.");
        } else if (code == 0) {
            broadcast("[aibuild] agent finished (exit 0).");
        } else {
            broadcast("[aibuild] agent exited with code " + code + " — see work dir logs; /aichat can continue the session.");
        }
        // state.json: a graceful server stop mid-build keeps "running" so the
        // next start offers the resume hint; /aicancel and timeouts are final.
        String status = reason == null ? "finished"
                : "server stopping".equals(reason) ? "running" : "cancelled";
        synchronized (this) {
            writeState(status);
        }
        jobManager.endBuildSession();
        broadcast(consumptionReport(turns, toolCalls, toolCounts, placed, wallMillis));
    }

    /** "本次建造:N 轮 / M 次工具调用 / X 块 / T 分 T 秒 (top: fill ×12, ...)" */
    private static String consumptionReport(int turns, int toolCalls, Map<String, Integer> toolCounts,
                                            long placed, long wallMillis) {
        long secs = Math.max(0, wallMillis / 1000);
        StringBuilder sb = new StringBuilder("[aibuild] 本次建造:")
                .append(turns).append(" 轮 / ")
                .append(toolCalls).append(" 次工具调用 / ")
                .append(placed).append(" 块 / ")
                .append(secs / 60).append(" 分 ").append(secs % 60).append(" 秒");
        if (!toolCounts.isEmpty()) {
            List<Map.Entry<String, Integer>> top = new ArrayList<>(toolCounts.entrySet());
            top.sort((a, b) -> Integer.compare(b.getValue(), a.getValue()));
            sb.append(" (top: ");
            for (int i = 0; i < Math.min(5, top.size()); i++) {
                if (i > 0) {
                    sb.append(", ");
                }
                sb.append(top.get(i).getKey()).append(" ×").append(top.get(i).getValue());
            }
            sb.append(")");
        }
        return sb.toString();
    }

    // ------------------------------------------------------------------ state.json

    private Path stateFile() {
        return WorkDir.dirOf(server).resolve("state.json");
    }

    /** Writes the build state (status/description/session tag) for crash resume hints. Best-effort. */
    private void writeState(String status) {
        try {
            JsonObject o = new JsonObject();
            o.addProperty("status", status);
            if (buildDescription != null) {
                o.addProperty("description", buildDescription);
            }
            if (buildSessionTag != null) {
                o.addProperty("session", buildSessionTag);
            }
            o.addProperty("updated", Instant.now().toString());
            Files.writeString(stateFile(), GSON.toJson(o) + System.lineSeparator());
        } catch (Exception e) {
            AiBuildMod.LOGGER.warn("[aibuild] failed to write state.json ({})", status, e);
        }
    }

    private JsonObject readState() {
        try {
            Path file = stateFile();
            if (!Files.isRegularFile(file)) {
                return null;
            }
            return JsonParser.parseString(Files.readString(file)).getAsJsonObject();
        } catch (Exception e) {
            AiBuildMod.LOGGER.warn("[aibuild] failed to read state.json", e);
            return null;
        }
    }

    private static String optString(JsonObject o, String key) {
        return o.has(key) && o.get(key).isJsonPrimitive() ? o.get(key).getAsString() : null;
    }

    private void broadcast(String message) {
        AiBuildMod.LOGGER.info("[aibuild-chat] {}", message);
        MinecraftServer s;
        synchronized (this) {
            s = server;
        }
        if (s != null) {
            s.execute(() -> s.getPlayerList().broadcastSystemMessage(Component.literal(message), false));
        }
    }

    private synchronized void log(String line) {
        if (logWriter == null) {
            return;
        }
        try {
            logWriter.write(line);
            logWriter.newLine();
            logWriter.flush();
        } catch (IOException e) {
            AiBuildMod.LOGGER.debug("[aibuild] agent log write failed: {}", e.toString());
        }
    }

    private synchronized void closeLog() {
        if (logWriter != null) {
            try {
                logWriter.close();
            } catch (IOException ignored) {
            }
            logWriter = null;
        }
    }

    private static Thread daemon(String name, Runnable runnable) {
        Thread t = new Thread(runnable, name);
        t.setDaemon(true);
        return t;
    }
}
