package com.aibuild.mod.agent;

import com.aibuild.mod.AiBuildMod;
import com.aibuild.mod.config.AgentConfig;
import com.aibuild.mod.job.JobManager;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Process engine for ONE build session (E3: the old global single-agent lock
 * is gone — AgentSessionManager owns one runner per session and enforces the
 * max_concurrent_agents cap instead).
 *
 * Spawns the headless agent CLI (kimi) in the session's own working directory,
 * parses its stream-json stdout line by line (assistant text -> game chat,
 * tool_calls -> one merged chat line per assistant message, meta lines ->
 * kimi session id), enforces the two timeouts (dual-channel silence + hard
 * cap), and supports /aicancel via destroyForcibly.
 *
 * Self-heal (the 429 fix): when the process dies ABNORMALLY (non-zero exit
 * without the mod killing it — rate limits, crashes), the runner automatically
 * re-spawns {@code kimi -c -p "<continue the task>"} in the same working
 * directory after 30 s, up to {@value #MAX_SELF_HEAL_ATTEMPTS} consecutive
 * times. Deliberate kills (/aicancel, idle/hard timeouts, server stopping)
 * never self-heal. Every attempt is logged and broadcast; after the third
 * consecutive failure the session is FAILED with its work dir kept intact.
 *
 * Consumption stats (turns / tool calls / blocks / wall time) accumulate into
 * the {@link AgentSession} across processes (resumes and self-heals) and are
 * reported on the session's terminal exit.
 */
public final class AgentRunner {
    private static final DateTimeFormatter LOG_STAMP = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss");
    /** stream-json MCP tool prefix, stripped for chat display and stats. */
    private static final String MCP_PREFIX = "mcp__aibuild__";
    /** Consecutive abnormal exits tolerated before the session is declared failed. */
    private static final int MAX_SELF_HEAL_ATTEMPTS = 3;
    /** Delay before each automatic {@code kimi -c} resume. */
    private static final long SELF_HEAL_DELAY_MS = 30_000L;
    /** Prompt used for automatic resumes (the session's conversation is continued with -c). */
    private static final String SELF_HEAL_PROMPT =
            "The previous run was interrupted (rate limit or crash). Read plan.md and task.json "
                    + "in the current directory to reconstruct your working state, then continue "
                    + "the building task until it is done.";

    private final AgentConfig config;
    private final AgentSession session;
    private final JobManager jobManager;
    private final AgentSessionManager manager;

    private Process process;
    private BufferedWriter logWriter;
    private volatile long lastIoMillis;
    private long startedMillis;
    /** Null while running normally; set before killing so onExit reports the right cause. */
    private String stopReason;
    /** Bumped on every spawn/cancel; stale self-heal threads check it before re-spawning. */
    private int spawnGeneration;

    AgentRunner(AgentConfig config, AgentSession session, JobManager jobManager, AgentSessionManager manager) {
        this.config = config;
        this.session = session;
        this.jobManager = jobManager;
        this.manager = manager;
    }

    private String tag() {
        return "#" + session.no();
    }

    public synchronized boolean isProcessAlive() {
        return process != null && process.isAlive();
    }

    // ------------------------------------------------------------------ spawns

    /** Spawn arg prefix: command plus optional configured model (-m). */
    private List<String> newArgs(String... tail) {
        List<String> args = new ArrayList<>();
        args.add(config.resolvedAgentCommand());
        if (config.agentModel() != null && !config.agentModel().isBlank()) {
            args.add("-m");
            args.add(config.agentModel());
        }
        args.addAll(List.of(tail));
        return args;
    }

    /** First spawn of the session: fresh task (task.json was written by the manager). */
    public synchronized void startNew() throws IOException {
        List<String> args = newArgs(
                "-p", "Read AGENTS.md and task.json in the current directory, then carry out the building task described in task.json.",
                "--output-format", "stream-json");
        spawn(args);
        manager.broadcast("[aibuild] " + tag() + " agent started: " + session.description());
    }

    /** INTAKE spawn: the interviewer agent (work dir AGENTS.md is the interview manual). */
    public synchronized void startIntake() throws IOException {
        List<String> args = newArgs(
                "-p", "Read AGENTS.md and task.json in the current directory, then carry out the pre-build interview described in AGENTS.md.",
                "--output-format", "stream-json");
        spawn(args);
        manager.broadcast("[aibuild] " + tag() + " 访谈 agent 已启动,它会先问清楚再开工 (说「跳过」= 不问直接造): " + session.description());
    }

    /** Manual resume via /aichat: continues the session's kimi conversation. */
    public synchronized void resume(String message) throws IOException {
        if (session.kimiSessionId() == null) {
            throw new IOException("no session to resume");
        }
        List<String> args = newArgs(
                "-r", session.kimiSessionId(),
                "-p", message,
                "--output-format", "stream-json");
        spawn(args);
        manager.broadcast("[aibuild] " + tag() + " agent resumed (session " + session.kimiSessionId() + "): " + message);
    }

    /** /aicancel (or manager-initiated stop): kills the process or aborts a pending self-heal. */
    public synchronized void cancel(String reason) {
        spawnGeneration++; // stale self-heal threads give up
        Process p = process;
        if (p != null && p.isAlive()) {
            stopReason = reason;
            p.destroyForcibly();
            AiBuildMod.LOGGER.info("[aibuild] {} agent process killed: {}", tag(), reason);
        } else if (session.status() == AgentSession.Status.RUNNING
                || session.status() == AgentSession.Status.INTAKE) {
            // between self-heal retries (process already dead): finalize as cancelled now
            session.status = AgentSession.Status.CANCELLED;
            session.endedAtMillis = System.currentTimeMillis();
            manager.broadcast("[aibuild] " + tag() + " agent stopped: " + reason
                    + ". Blocks placed so far remain; /aichat can continue the session.");
            broadcastConsumption();
            manager.persist();
        }
    }

    public synchronized void onServerStopping() {
        spawnGeneration++; // no self-heal across a restart
        Process p = process;
        if (p != null && p.isAlive()) {
            stopReason = "server stopping";
            p.destroyForcibly();
        }
    }

    private void spawn(List<String> args) throws IOException {
        Path dir = session.workDir(manager.aibuildRoot());
        this.stopReason = null;
        this.startedMillis = System.currentTimeMillis();
        this.lastIoMillis = startedMillis;
        this.spawnGeneration++;
        synchronized (session) {
            session.placedBaseline = session.sessionTag() != null ? jobManager.placedForTag(session.sessionTag()) : 0L;
            session.wallStartMillis = startedMillis;
        }

        Path logFile = dir.resolve("logs").resolve("agent-" + LOG_STAMP.format(LocalDateTime.now()) + ".log");
        this.logWriter = Files.newBufferedWriter(logFile, StandardCharsets.UTF_8);
        AiBuildMod.LOGGER.info("[aibuild] {} spawning agent: {} (cwd={}, log={})", tag(), String.join(" ", args), dir, logFile);

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

        Thread stdout = pump(p.inputReader(StandardCharsets.UTF_8), "s" + session.no() + "-stdout", this::handleStdoutLine);
        Thread stderr = pump(p.errorReader(StandardCharsets.UTF_8), "s" + session.no() + "-stderr", line -> log("stderr | " + line));
        Thread waiter = daemon("aibuild-agent-s" + session.no() + "-wait", () -> {
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
        Thread watchdog = daemon("aibuild-agent-s" + session.no() + "-watchdog", this::watchLoop);
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
                        AiBuildMod.LOGGER.warn("[aibuild] {} error handling agent {} line", tag(), name, e);
                    }
                }
            } catch (IOException e) {
                AiBuildMod.LOGGER.debug("[aibuild] {} agent {} stream closed: {}", tag(), name, e.toString());
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
        // Token 账单的 stream-json 通道: 当前 kimi 版本(0.30.0)的 stream-json 不带
        // usage(见 TokenUsage 注释),这里是面向未来版本的兜底;真正的来源是 foldStats
        // 里的 wire.jsonl 汇总。
        TokenUsage usage = TokenUsage.fromStreamJson(o);
        if (usage != null) {
            synchronized (session) {
                session.tokenInput += usage.input();
                session.tokenOutput += usage.output();
                session.tokenCacheRead += usage.cacheRead();
            }
        }
        String role = o.has("role") && o.get("role").isJsonPrimitive() ? o.get("role").getAsString() : "";
        switch (role) {
            case "assistant" -> {
                synchronized (session) {
                    session.turns++;
                }
                String text = extractText(o.get("content"));
                if (!text.isBlank()) {
                    manager.broadcast("[AI" + tag() + "] " + text);
                }
                forwardToolCalls(o);
            }
            case "meta" -> {
                String type = o.has("type") && o.get("type").isJsonPrimitive() ? o.get("type").getAsString() : "";
                if ("session.resume_hint".equals(type) && o.has("session_id")) {
                    String id = o.get("session_id").getAsString();
                    session.kimiSessionId = id;
                    try {
                        Files.writeString(session.workDir(manager.aibuildRoot()).resolve(".session_id"),
                                id + System.lineSeparator());
                    } catch (IOException e) {
                        AiBuildMod.LOGGER.warn("[aibuild] {} failed to persist session id", tag(), e);
                    }
                    manager.persist();
                    AiBuildMod.LOGGER.info("[aibuild] {} agent session id: {}", tag(), id);
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
     * tool collapse into a count ("[AI#2] 调用 fill ×3、render_region ×1").
     * Also folds the calls into the session's consumption stats.
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
        synchronized (session) {
            session.toolCalls += total;
            perMessage.forEach((name, count) -> session.toolCounts.merge(name, count, Integer::sum));
        }
        StringBuilder sb = new StringBuilder("[AI").append(tag()).append("] 调用 ");
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
        manager.broadcast(sb.toString());
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
                AiBuildMod.LOGGER.warn("[aibuild] {} killing agent: {}", tag(), reason);
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
        synchronized (this) {
            if (process == null) {
                return;
            }
            process = null;
            reason = stopReason;
        }
        closeLog();
        foldStats();

        if ("server stopping".equals(reason)) {
            // Keep status RUNNING on disk so the next server start detects the
            // interruption and offers the resume hint (old state.json semantics).
            manager.broadcast("[aibuild] " + tag() + " agent stopped: server stopping."
                    + " Blocks placed so far remain; /aichat can continue the session after restart.");
            manager.persist();
            return;
        }
        if (reason != null && reason.startsWith("cancelled")) {
            terminate(AgentSession.Status.CANCELLED, null,
                    "[aibuild] " + tag() + " agent stopped: " + reason
                            + ". Blocks placed so far remain; /aichat can continue the session.");
            return;
        }
        if (reason != null) { // idle/hard timeout — 看门狗判定卡死: 走自愈自动续跑
            if (session.status() == AgentSession.Status.INTAKE) {
                // 访谈不自愈(设计): 播报可手动续
                terminate(AgentSession.Status.FAILED, reason,
                        "[aibuild] " + tag() + " 访谈 agent 卡死被看门狗终止: " + reason + " — /aichat 可续");
                return;
            }
            int attempt;
            synchronized (session) {
                session.resumeAttempts++;
                attempt = session.resumeAttempts;
            }
            if (attempt <= MAX_SELF_HEAL_ATTEMPTS) {
                session.lastError = reason + " — watchdog auto-resume " + attempt + "/" + MAX_SELF_HEAL_ATTEMPTS + " in 30s";
                AiBuildMod.LOGGER.warn("[aibuild] {} watchdog kill ({}); self-heal {}/{} in 30s",
                        tag(), reason, attempt, MAX_SELF_HEAL_ATTEMPTS);
                manager.broadcast("[aibuild] " + tag() + " 看门狗: " + reason
                        + " — 判定卡死,杀进程,30s 后自动续跑 (自愈 " + attempt + "/" + MAX_SELF_HEAL_ATTEMPTS + ")");
                manager.persist();
                scheduleSelfHeal();
            } else {
                terminate(AgentSession.Status.FAILED,
                        reason + " — after " + MAX_SELF_HEAL_ATTEMPTS + " self-heal attempts",
                        "[aibuild] " + tag() + " 看门狗连续 " + MAX_SELF_HEAL_ATTEMPTS
                                + " 次自愈仍卡死 — 宣告失败,现场保留;/aichat 可手动续跑");
            }
            return;
        }
        if (session.status() == AgentSession.Status.INTAKE) {
            // interviewer exited: clean exit hands off to the builder; anything
            // else fails the interview (no self-heal — /aichat resumes it).
            if (code == 0) {
                synchronized (session) {
                    session.resumeAttempts = 0;
                }
                manager.completeIntake(session);
            } else {
                terminate(AgentSession.Status.FAILED,
                        "intake exit code " + code + " — /aichat 可续",
                        "[aibuild] " + tag() + " 访谈 agent 异常退出 (code " + code + ") — /aichat 可续");
            }
            return;
        }
        if (code == 0) {
            synchronized (session) {
                session.resumeAttempts = 0;
            }
            terminate(AgentSession.Status.DONE, null, "[aibuild] " + tag() + " agent finished (exit 0).");
            return;
        }
        // abnormal exit (429 rate limit, crash, …): self-heal with `kimi -c`
        int attempt;
        synchronized (session) {
            session.resumeAttempts++;
            attempt = session.resumeAttempts;
        }
        if (attempt <= MAX_SELF_HEAL_ATTEMPTS) {
            session.lastError = "exit code " + code + " — auto-resume " + attempt + "/" + MAX_SELF_HEAL_ATTEMPTS + " in 30s";
            AiBuildMod.LOGGER.warn("[aibuild] {} agent exited abnormally (code {}); self-heal {}/{} in {}s",
                    tag(), code, attempt, MAX_SELF_HEAL_ATTEMPTS, SELF_HEAL_DELAY_MS / 1000);
            manager.broadcast("[aibuild] " + tag() + " agent 异常退出 (code " + code + ") — 30s 后自动续跑 (自愈 "
                    + attempt + "/" + MAX_SELF_HEAL_ATTEMPTS + ")");
            manager.persist();
            scheduleSelfHeal();
        } else {
            terminate(AgentSession.Status.FAILED,
                    "exit code " + code + " after " + MAX_SELF_HEAL_ATTEMPTS
                            + " self-heal attempts — work dir kept; /aichat 可续",
                    "[aibuild] " + tag() + " agent 连续 " + MAX_SELF_HEAL_ATTEMPTS
                            + " 次自愈失败 (last exit code " + code + ") — 宣告失败,现场保留在 "
                            + session.workDir(manager.aibuildRoot()) + ";/aichat 可手动续跑");
        }
    }

    /** Terminal transition: status + error + broadcast + consumption report + persist. */
    private void terminate(AgentSession.Status status, String error, String chatMessage) {
        session.status = status;
        // Always overwrite: a DONE/CANCELLED session must not keep a stale
        // error from an earlier self-heal attempt.
        session.lastError = error;
        session.endedAtMillis = System.currentTimeMillis();
        manager.promoteSharedStyles(session); // builder-authored cards → shared library
        manager.broadcast(chatMessage);
        broadcastConsumption();
        manager.persist();
    }

    /** Folds this process's placed-blocks delta and wall time into the session totals. */
    private void foldStats() {
        synchronized (session) {
            if (session.sessionTag() != null) {
                session.blocksPlaced += Math.max(0, jobManager.placedForTag(session.sessionTag()) - session.placedBaseline);
            }
            session.wallMillis += Math.max(0, System.currentTimeMillis() - session.wallStartMillis);
        }
        harvestTokenUsage();
    }

    /**
     * Token 账单: 从 kimi 会话存储(wire.jsonl)汇总本会话的 usage.record 绝对总量,
     * 取 max 写回 — 自愈续跑 / /aichat 续聊跑的是同一个 kimi session,wire 单调增长,
     * 所以跨进程、跨服务器重启都不会重复计数(见 TokenUsage)。
     */
    private void harvestTokenUsage() {
        String kimiId = session.kimiSessionId();
        if (kimiId == null) {
            return;
        }
        try {
            TokenUsage total = TokenUsage.sumWireRecords(kimiId);
            if (total == null) {
                return;
            }
            synchronized (session) {
                session.tokenInput = Math.max(session.tokenInput, total.input());
                session.tokenOutput = Math.max(session.tokenOutput, total.output());
                session.tokenCacheRead = Math.max(session.tokenCacheRead, total.cacheRead());
            }
        } catch (Exception e) {
            AiBuildMod.LOGGER.warn("[aibuild] {} failed to harvest token usage", tag(), e);
        }
    }

    private void scheduleSelfHeal() {
        final int generation;
        synchronized (this) {
            generation = spawnGeneration;
        }
        Thread t = daemon("aibuild-agent-s" + session.no() + "-selfheal", () -> {
            try {
                Thread.sleep(SELF_HEAL_DELAY_MS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
            synchronized (this) {
                if (generation != spawnGeneration || process != null || manager.isServerStopping()
                        || session.status() != AgentSession.Status.RUNNING) {
                    AiBuildMod.LOGGER.info("[aibuild] {} self-heal aborted (superseded/cancelled/stopping)", tag());
                    return;
                }
            }
            try {
                manager.prepareWorkDir(session); // refresh mcp.json (port/token) before the resume
                List<String> args = newArgs(
                        "-c", "-p", SELF_HEAL_PROMPT,
                        "--output-format", "stream-json");
                spawn(args);
                AiBuildMod.LOGGER.info("[aibuild] {} self-heal resume spawned (kimi -c)", tag());
                manager.broadcast("[aibuild] " + tag() + " 自愈续跑已启动 (kimi -c)");
            } catch (IOException e) {
                AiBuildMod.LOGGER.error("[aibuild] {} self-heal spawn failed", tag(), e);
                terminate(AgentSession.Status.FAILED,
                        "self-heal spawn failed: " + e.getMessage() + " — work dir kept; /aichat 可续",
                        "[aibuild] " + tag() + " 自愈续跑启动失败: " + e.getMessage() + ";/aichat 可手动续跑");
            }
        });
        t.start();
    }

    /**
     * "[aibuild] #2 本次建造:N 轮 / M 次工具调用 / X 块 / T 分 T 秒 (top: fill ×12, ...)",
     * followed by the one-shot token bill line. Only called on terminal
     * transitions (terminate + the dead-process /aicancel branch), so the bill
     * is broadcast exactly once per session ending.
     */
    private void broadcastConsumption() {
        int turns, toolCalls;
        Map<String, Integer> toolCounts;
        long placed, wallMillis;
        synchronized (session) {
            turns = session.turns;
            toolCalls = session.toolCalls;
            toolCounts = new LinkedHashMap<>(session.toolCounts);
            placed = session.blocksPlaced;
            wallMillis = session.wallMillis;
        }
        long secs = Math.max(0, wallMillis / 1000);
        StringBuilder sb = new StringBuilder("[aibuild] ").append(tag()).append(" 本次建造:")
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
        manager.broadcast(sb.toString());
        broadcastTokenBill();
    }

    /**
     * Token 账单一行(输入/输出/缓存命中 + 粗估费用感受),仅在会话终结时随
     * {@link #broadcastConsumption()} 播一次。静默跳过:回填失败(wire.jsonl
     * 找不到/读不了)或没有 kimi session 时三项皆为 0 — 不播,也不报错刷屏。
     */
    private void broadcastTokenBill() {
        long input, output, cacheRead;
        synchronized (session) {
            input = session.tokenInput;
            output = session.tokenOutput;
            cacheRead = session.tokenCacheRead;
        }
        if (input + output + cacheRead <= 0) {
            return;
        }
        manager.broadcast("[aibuild] " + tag() + " token 账单: "
                + AgentSession.formatTokens(input) + " 输入 / "
                + AgentSession.formatTokens(output) + " 输出 / "
                + AgentSession.formatTokens(cacheRead) + " 缓存命中 — "
                + roughCost(input, output, cacheRead, config.agentModel()));
    }

    /**
     * 粗估费用感受:只表数量级,以实际账单为准。按会话模型分档:
     * deepseek/*(V4-Flash, 2026-08 官价:输入 ¥1/M、输出 ¥2/M、缓存读 ¥0.02/M,峰谷浮动忽略);
     * 其余按 Kimi K2 量级价(输入 ¥4/M、输出 ¥16/M、缓存读 ¥1/M)。
     */
    private static String roughCost(long input, long output, long cacheRead, String model) {
        boolean flash = model != null && model.toLowerCase(java.util.Locale.ROOT).contains("deepseek");
        double inRate = flash ? 1.0 : 4.0;
        double outRate = flash ? 2.0 : 16.0;
        double cacheRate = flash ? 0.02 : 1.0;
        double yuan = input * inRate / 1_000_000 + output * outRate / 1_000_000 + cacheRead * cacheRate / 1_000_000;
        if (yuan < 0.01) {
            return "粗估费用不到 1 分钱";
        }
        return "粗估费用约 ¥" + (yuan < 1
                ? String.format(java.util.Locale.ROOT, "%.2f", yuan)
                : String.format(java.util.Locale.ROOT, "%.1f", yuan)) + "(量级参考)";
    }

    // ------------------------------------------------------------------ logging

    private synchronized void log(String line) {
        if (logWriter == null) {
            return;
        }
        try {
            logWriter.write(line);
            logWriter.newLine();
            logWriter.flush();
        } catch (IOException e) {
            AiBuildMod.LOGGER.debug("[aibuild] {} agent log write failed: {}", tag(), e.toString());
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
