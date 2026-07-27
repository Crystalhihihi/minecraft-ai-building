package com.aibuild.mod.agent;

import com.aibuild.mod.AiBuildMod;
import com.aibuild.mod.bridge.BridgeHttpServer;
import com.aibuild.mod.bridge.PlayerInbox;
import com.aibuild.mod.config.AgentConfig;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;

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
import java.util.List;

/**
 * Spawns the headless agent CLI (kimi) in the per-world working directory,
 * parses its stream-json stdout line by line (assistant text -> game chat,
 * meta lines -> session id), enforces the two timeouts (dual-channel silence
 * + hard cap), and supports /aicancel via destroyForcibly.
 *
 * Lifecycle: one agent at a time, guarded by {@code synchronized} on state
 * transitions. Reader/watchdog/waiter threads are daemons.
 */
public final class AgentRunner {
    private static final DateTimeFormatter LOG_STAMP = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss");

    private final AgentConfig config;
    private final PlayerInbox inbox;
    private final BridgeHttpServer bridge;

    private MinecraftServer server;
    private String sessionId;

    private Process process;
    private Path workDir;
    private BufferedWriter logWriter;
    private volatile long lastIoMillis;
    private long startedMillis;
    /** Null while running normally; set before killing so onExit reports the right cause. */
    private String stopReason;

    public AgentRunner(AgentConfig config, PlayerInbox inbox, BridgeHttpServer bridge) {
        this.config = config;
        this.inbox = inbox;
        this.bridge = bridge;
    }

    public synchronized void onServerStarted(MinecraftServer server) {
        this.server = server;
        this.sessionId = null;
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
    }

    public synchronized void onServerStopping() {
        if (process != null) {
            stopReason = "server stopping";
            process.destroyForcibly();
        }
    }

    public synchronized boolean isRunning() {
        return process != null && process.isAlive();
    }

    public synchronized boolean hasSession() {
        return sessionId != null;
    }

    public void enqueuePlayerMessage(String message) {
        inbox.add(message);
    }

    // ------------------------------------------------------------------ spawns

    public synchronized void startBuild(String description, BlockPos anchor) throws IOException {
        ensureNotRunning();
        Path dir = WorkDir.prepare(server, bridge.port(), bridge.token());
        WorkDir.writeTask(dir, description, anchor);
        List<String> args = List.of(
                config.resolvedAgentCommand(),
                "-p", "Read AGENTS.md and task.json in the current directory, then carry out the building task described in task.json.",
                "--output-format", "stream-json");
        spawn(dir, args);
        broadcast("[aibuild] agent started: " + description);
    }

    public synchronized void startChat(String message) throws IOException {
        ensureNotRunning();
        if (sessionId == null) {
            throw new IOException("no session to resume");
        }
        Path dir = WorkDir.prepare(server, bridge.port(), bridge.token());
        List<String> args = List.of(
                config.resolvedAgentCommand(),
                "-r", sessionId,
                "-p", message,
                "--output-format", "stream-json");
        spawn(dir, args);
        broadcast("[aibuild] agent resumed (session " + sessionId + "): " + message);
    }

    public synchronized void cancel() {
        if (process != null && process.isAlive()) {
            stopReason = "cancelled by /aicancel";
            process.destroyForcibly();
            AiBuildMod.LOGGER.info("[aibuild] agent process killed by /aicancel");
        }
    }

    private void ensureNotRunning() {
        if (isRunning()) {
            throw new IllegalStateException("an agent is already running");
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
                String text = extractText(o.get("content"));
                if (!text.isBlank()) {
                    broadcast("[AI] " + text);
                }
                // tool_calls and everything else: log file only (line already logged above)
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
        synchronized (this) {
            if (process == null) {
                return;
            }
            process = null;
            reason = stopReason;
        }
        closeLog();
        if (reason != null) {
            broadcast("[aibuild] agent stopped: " + reason + ". Blocks placed so far remain; /aichat can continue the session.");
        } else if (code == 0) {
            broadcast("[aibuild] agent finished (exit 0).");
        } else {
            broadcast("[aibuild] agent exited with code " + code + " — see work dir logs; /aichat can continue the session.");
        }
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
