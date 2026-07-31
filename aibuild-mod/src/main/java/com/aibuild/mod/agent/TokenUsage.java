package com.aibuild.mod.agent;

import com.aibuild.mod.AiBuildMod;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.IOException;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Token billing for one build session. The kimi CLI's stream-json stdout does
 * NOT carry usage (verified against 0.30.0 logs: assistant/tool/meta lines
 * only — {@code turn.step.completed} events, which carry usage, are dropped by
 * the CLI's print-mode writer), so the real source is the CLI's own session
 * store: {@code <kimiHome>/sessions/wd_<dir>_<hash>/session_<id>/agents/<agent>/wire.jsonl}
 * holds one
 * {@code {"type":"usage.record","usage":{"inputOther":N,"output":N,"inputCacheRead":N,"inputCacheCreation":N},"usageScope":"turn"}}
 * line per LLM call. A build session maps to ONE kimi session (self-heal
 * {@code kimi -c} and /aichat {@code kimi -r} continue it), so summing the
 * whole wire yields absolute totals — idempotent across processes and server
 * restarts (callers keep the max).
 *
 * Component mapping follows the CLI's own transcript vocabulary:
 * input = inputOther + inputCacheCreation, cacheRead = inputCacheRead,
 * output = output.
 *
 * {@link #fromStreamJson(JsonObject)} additionally accepts usage objects on
 * stream-json lines (both the kimi wire key names and OpenAI-style
 * input_tokens/output_tokens/cache_read_input_tokens) as a safety net for CLI
 * versions that do emit them.
 */
public record TokenUsage(long input, long output, long cacheRead) {

    /** Usage carried by a stream-json line, or null when the line has none (the common case). */
    public static TokenUsage fromStreamJson(JsonObject line) {
        if (!line.has("usage") || !line.get("usage").isJsonObject()) {
            return null;
        }
        JsonObject u = line.getAsJsonObject("usage");
        long in = num(u, "inputOther", "input_tokens") + num(u, "inputCacheCreation", "cache_creation_input_tokens");
        long out = num(u, "output", "output_tokens");
        long cache = num(u, "inputCacheRead", "cache_read_input_tokens");
        return in == 0 && out == 0 && cache == 0 ? null : new TokenUsage(in, out, cache);
    }

    /**
     * Sums all {@code usage.record} lines across every agent wire of the kimi
     * session (main agent + subagents), or null when the session store cannot
     * be located/read. Absolute totals for the whole kimi session.
     */
    public static TokenUsage sumWireRecords(String kimiSessionId) {
        Path home = kimiHome();
        if (home == null) {
            return null;
        }
        Path dir = findSessionDir(home, kimiSessionId);
        if (dir == null) {
            return null;
        }
        Path agents = dir.resolve("agents");
        if (!Files.isDirectory(agents)) {
            return null;
        }
        long in = 0;
        long out = 0;
        long cache = 0;
        try (DirectoryStream<Path> ds = Files.newDirectoryStream(agents)) {
            for (Path agentDir : ds) {
                Path wire = agentDir.resolve("wire.jsonl");
                if (!Files.isRegularFile(wire)) {
                    continue;
                }
                for (String line : Files.readAllLines(wire)) {
                    if (!line.contains("\"usage.record\"")) {
                        continue;
                    }
                    try {
                        JsonObject o = JsonParser.parseString(line).getAsJsonObject();
                        if (!o.has("type") || !"usage.record".equals(o.get("type").getAsString())
                                || !o.has("usage") || !o.get("usage").isJsonObject()) {
                            continue;
                        }
                        JsonObject u = o.getAsJsonObject("usage");
                        in += num(u, "inputOther") + num(u, "inputCacheCreation");
                        out += num(u, "output");
                        cache += num(u, "inputCacheRead");
                    } catch (Exception ignored) {
                        // 跳过坏行 — 账单以能解析的行为准
                    }
                }
            }
        } catch (IOException e) {
            AiBuildMod.LOGGER.warn("[aibuild] failed to read kimi wire files under {}", agents, e);
            return null;
        }
        return new TokenUsage(in, out, cache);
    }

    /** kimi home: {@code KIMI_CODE_HOME} env, else {@code ~/.kimi-code}. */
    private static Path kimiHome() {
        String env = System.getenv("KIMI_CODE_HOME");
        if (env != null && !env.isBlank()) {
            return Path.of(env);
        }
        String userHome = System.getProperty("user.home");
        return userHome == null ? null : Path.of(userHome, ".kimi-code");
    }

    /** session_index.jsonl lookup; fallback: scan {@code sessions/wd_* /session_&lt;id&gt;}. */
    private static Path findSessionDir(Path home, String sessionId) {
        Path index = home.resolve("session_index.jsonl");
        if (Files.isRegularFile(index)) {
            try {
                for (String line : Files.readAllLines(index)) {
                    if (!line.contains(sessionId)) {
                        continue;
                    }
                    try {
                        JsonObject o = JsonParser.parseString(line).getAsJsonObject();
                        if (o.has("sessionId") && sessionId.equals(o.get("sessionId").getAsString())
                                && o.has("sessionDir")) {
                            return Path.of(o.get("sessionDir").getAsString());
                        }
                    } catch (Exception ignored) {
                        // 跳过坏行
                    }
                }
            } catch (IOException ignored) {
                // 索引读不了就走目录扫描
            }
        }
        Path root = home.resolve("sessions");
        if (Files.isDirectory(root)) {
            try (DirectoryStream<Path> ds = Files.newDirectoryStream(root)) {
                for (Path wd : ds) {
                    Path candidate = wd.resolve(sessionId);
                    if (Files.isDirectory(candidate)) {
                        return candidate;
                    }
                }
            } catch (IOException ignored) {
                // 找不到就放弃 — 本次不记账
            }
        }
        return null;
    }

    private static long num(JsonObject o, String... keys) {
        for (String k : keys) {
            if (o.has(k) && o.get(k).isJsonPrimitive() && o.get(k).getAsJsonPrimitive().isNumber()) {
                return o.get(k).getAsLong();
            }
        }
        return 0;
    }
}
