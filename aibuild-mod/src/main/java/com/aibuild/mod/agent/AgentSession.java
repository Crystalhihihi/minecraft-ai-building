package com.aibuild.mod.agent;

import com.aibuild.mod.bridge.PlayerInbox;
import com.aibuild.mod.bridge.SiteGate;
import com.google.gson.JsonObject;

import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * One build session: an agent process (via {@link AgentRunner}) bound to its
 * own working directory, bridge token, {@link SiteGate} bounds gate and
 * {@link PlayerInbox}. This is the persistent record — everything except the
 * live process survives a server restart through
 * {@code <world>/aibuild/sessions.json} (written by AgentSessionManager on
 * every change).
 *
 * Status lifecycle: RUNNING (process alive or between self-heal retries) →
 * DONE (exit 0) / FAILED (abnormal exit after retries, timeouts, interrupted
 * by a server restart) / CANCELLED (/aicancel). DONE/FAILED/CANCELLED
 * sessions keep their kimi session id and gate state, so /aichat can resume
 * them with the confirmed site intact.
 */
public final class AgentSession {
    public enum Status { RUNNING, DONE, FAILED, CANCELLED }

    /** Work dir of the pre-E3 single-session era: the aibuild root itself. */
    public static final String LEGACY_WORK_DIR = ".";

    final int no;
    final String token;
    /** Relative to {@code <world>/aibuild}: "sessions/s&lt;no&gt;", or "." for migrated legacy sessions. */
    final String workDirName;
    final SiteGate gate = new SiteGate();
    final PlayerInbox inbox = new PlayerInbox();

    String description = "";
    volatile Status status = Status.RUNNING;
    volatile String kimiSessionId;
    /** Snapshot session tag ("b<timestamp>-s<no>") stamping this session's snapshots for /aiundo all. */
    String sessionTag;
    volatile String lastError;
    /** Consecutive abnormal exits so far; reset by a clean exit or a manual /aichat resume. */
    int resumeAttempts;

    // consumption stats, accumulated across processes of this session (resumes included)
    int turns;
    int toolCalls;
    final Map<String, Integer> toolCounts = new LinkedHashMap<>();
    long blocksPlaced;
    long wallMillis;
    // token 账单(同样跨进程累计): input = 非缓存输入 + 缓存创建, cacheRead = 缓存读取
    long tokenInput;
    long tokenOutput;
    long tokenCacheRead;

    long createdAtMillis = System.currentTimeMillis();
    Long endedAtMillis;

    // transient per-process baselines (captured at spawn by AgentRunner)
    transient long placedBaseline;
    transient long wallStartMillis;

    AgentSession(int no, String token, String workDirName) {
        this.no = no;
        this.token = token;
        this.workDirName = workDirName;
    }

    public int no() {
        return no;
    }

    public String token() {
        return token;
    }

    public SiteGate gate() {
        return gate;
    }

    public PlayerInbox inbox() {
        return inbox;
    }

    public String description() {
        return description;
    }

    public Status status() {
        return status;
    }

    public String kimiSessionId() {
        return kimiSessionId;
    }

    public String sessionTag() {
        return sessionTag;
    }

    public String lastError() {
        return lastError;
    }

    public Path workDir(Path aibuildRoot) {
        return LEGACY_WORK_DIR.equals(workDirName) ? aibuildRoot : aibuildRoot.resolve(workDirName);
    }

    /** Short consumption summary: "12 轮 / 34 调用 / 125 块 / 2 分 10 秒". */
    public synchronized String statsSummary() {
        long secs = Math.max(0, wallMillis / 1000);
        return turns + " 轮 / " + toolCalls + " 调用 / " + blocksPlaced + " 块 / "
                + (secs / 60) + " 分 " + (secs % 60) + " 秒";
    }

    public synchronized long totalTokens() {
        return tokenInput + tokenOutput + tokenCacheRead;
    }

    /** Short token bill: "12.3k in / 4.5k out / 112.3k cache" (cache part omitted when zero). */
    public synchronized String tokenSummary() {
        String s = formatTokens(tokenInput) + " in / " + formatTokens(tokenOutput) + " out";
        return tokenCacheRead > 0 ? s + " / " + formatTokens(tokenCacheRead) + " cache" : s;
    }

    static String formatTokens(long n) {
        return n >= 1000 ? String.format(java.util.Locale.ROOT, "%.1fk", n / 1000.0) : Long.toString(n);
    }

    // ------------------------------------------------------------------ sessions.json

    synchronized JsonObject toJson() {
        JsonObject o = new JsonObject();
        o.addProperty("no", no);
        o.addProperty("description", description);
        o.addProperty("status", status.name().toLowerCase(java.util.Locale.ROOT));
        o.addProperty("token", token);
        o.addProperty("work_dir", workDirName);
        if (kimiSessionId != null) {
            o.addProperty("kimi_session_id", kimiSessionId);
        }
        if (sessionTag != null) {
            o.addProperty("session_tag", sessionTag);
        }
        o.add("gate", gate.toJson());
        JsonObject stats = new JsonObject();
        stats.addProperty("turns", turns);
        stats.addProperty("tool_calls", toolCalls);
        stats.addProperty("blocks_placed", blocksPlaced);
        stats.addProperty("wall_ms", wallMillis);
        stats.addProperty("token_in", tokenInput);
        stats.addProperty("token_out", tokenOutput);
        stats.addProperty("token_cache_read", tokenCacheRead);
        JsonObject tools = new JsonObject();
        toolCounts.forEach((name, count) -> tools.addProperty(name, count));
        stats.add("tools", tools);
        o.add("stats", stats);
        if (lastError != null) {
            o.addProperty("last_error", lastError);
        }
        o.addProperty("resume_attempts", resumeAttempts);
        o.addProperty("created_at", createdAtMillis);
        if (endedAtMillis != null) {
            o.addProperty("ended_at", endedAtMillis);
        }
        return o;
    }

    static AgentSession fromJson(JsonObject o) {
        AgentSession s = new AgentSession(
                o.get("no").getAsInt(),
                o.get("token").getAsString(),
                o.has("work_dir") ? o.get("work_dir").getAsString() : LEGACY_WORK_DIR);
        s.description = o.has("description") ? o.get("description").getAsString() : "";
        s.status = switch (o.has("status") ? o.get("status").getAsString() : "failed") {
            case "running" -> Status.RUNNING;
            case "done" -> Status.DONE;
            case "cancelled" -> Status.CANCELLED;
            default -> Status.FAILED;
        };
        s.kimiSessionId = o.has("kimi_session_id") ? o.get("kimi_session_id").getAsString() : null;
        s.sessionTag = o.has("session_tag") ? o.get("session_tag").getAsString() : null;
        if (o.has("gate") && o.get("gate").isJsonObject()) {
            s.gate.restore(o.getAsJsonObject("gate"));
        }
        if (o.has("stats") && o.get("stats").isJsonObject()) {
            JsonObject stats = o.getAsJsonObject("stats");
            s.turns = stats.has("turns") ? stats.get("turns").getAsInt() : 0;
            s.toolCalls = stats.has("tool_calls") ? stats.get("tool_calls").getAsInt() : 0;
            s.blocksPlaced = stats.has("blocks_placed") ? stats.get("blocks_placed").getAsLong() : 0;
            s.wallMillis = stats.has("wall_ms") ? stats.get("wall_ms").getAsLong() : 0;
            s.tokenInput = stats.has("token_in") ? stats.get("token_in").getAsLong() : 0;
            s.tokenOutput = stats.has("token_out") ? stats.get("token_out").getAsLong() : 0;
            s.tokenCacheRead = stats.has("token_cache_read") ? stats.get("token_cache_read").getAsLong() : 0;
            if (stats.has("tools") && stats.get("tools").isJsonObject()) {
                for (Map.Entry<String, com.google.gson.JsonElement> e : stats.getAsJsonObject("tools").entrySet()) {
                    s.toolCounts.put(e.getKey(), e.getValue().getAsInt());
                }
            }
        }
        s.lastError = o.has("last_error") ? o.get("last_error").getAsString() : null;
        s.resumeAttempts = o.has("resume_attempts") ? o.get("resume_attempts").getAsInt() : 0;
        s.createdAtMillis = o.has("created_at") ? o.get("created_at").getAsLong() : s.createdAtMillis;
        s.endedAtMillis = o.has("ended_at") ? o.get("ended_at").getAsLong() : null;
        return s;
    }
}
