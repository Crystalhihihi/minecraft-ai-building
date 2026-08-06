package com.aibuild.mod.config;

import com.aibuild.mod.AiBuildMod;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Mod configuration in {@code <gameDir>/aibuild/config.json}. Written with
 * defaults on first run; missing keys fall back to defaults.
 */
public record AgentConfig(String agentCommand, String agentModel, long idleTimeoutMinutes, long hardTimeoutMinutes, long tickBudgetMs,
                          int maxConcurrentAgents, boolean intakeEnabled) {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    private static final long DEFAULT_IDLE_TIMEOUT_MINUTES = 8;
    private static final long DEFAULT_HARD_TIMEOUT_MINUTES = 60;
    private static final long DEFAULT_TICK_BUDGET_MS = 10;
    private static final int DEFAULT_MAX_CONCURRENT_AGENTS = 4;
    private static final boolean DEFAULT_INTAKE_ENABLED = true;

    public static AgentConfig load(Path gameDir) {
        Path path = gameDir.resolve("aibuild").resolve("config.json");
        String defaultCommand = defaultAgentCommand();
        if (!Files.isRegularFile(path)) {
            AgentConfig defaults = new AgentConfig(defaultCommand, "", DEFAULT_IDLE_TIMEOUT_MINUTES,
                    DEFAULT_HARD_TIMEOUT_MINUTES, DEFAULT_TICK_BUDGET_MS, DEFAULT_MAX_CONCURRENT_AGENTS, DEFAULT_INTAKE_ENABLED);
            try {
                Files.createDirectories(path.getParent());
                Files.writeString(path, GSON.toJson(defaults.toJson()) + System.lineSeparator());
                AiBuildMod.LOGGER.info("[aibuild] wrote default config to {}", path);
            } catch (IOException e) {
                AiBuildMod.LOGGER.warn("[aibuild] could not write default config {}", path, e);
            }
            return defaults;
        }
        try {
            JsonObject o = JsonParser.parseString(Files.readString(path)).getAsJsonObject();
            String command = o.has("agent_command") ? o.get("agent_command").getAsString() : defaultCommand;
            String model = o.has("agent_model") ? o.get("agent_model").getAsString() : "";
            long idle = o.has("idle_timeout_minutes") ? o.get("idle_timeout_minutes").getAsLong() : DEFAULT_IDLE_TIMEOUT_MINUTES;
            long hard = o.has("hard_timeout_minutes") ? o.get("hard_timeout_minutes").getAsLong() : DEFAULT_HARD_TIMEOUT_MINUTES;
            long budget = o.has("tick_budget_ms") ? o.get("tick_budget_ms").getAsLong() : DEFAULT_TICK_BUDGET_MS;
            int maxAgents = o.has("max_concurrent_agents") ? o.get("max_concurrent_agents").getAsInt() : DEFAULT_MAX_CONCURRENT_AGENTS;
            boolean intake = o.has("intake_enabled") ? o.get("intake_enabled").getAsBoolean() : DEFAULT_INTAKE_ENABLED;
            return new AgentConfig(command, model, idle, hard, budget, Math.max(1, maxAgents), intake);
        } catch (Exception e) {
            AiBuildMod.LOGGER.warn("[aibuild] failed to parse {}, using defaults", path, e);
            return new AgentConfig(defaultCommand, "", DEFAULT_IDLE_TIMEOUT_MINUTES,
                    DEFAULT_HARD_TIMEOUT_MINUTES, DEFAULT_TICK_BUDGET_MS, DEFAULT_MAX_CONCURRENT_AGENTS, DEFAULT_INTAKE_ENABLED);
        }
    }

    /**
     * The command to spawn. A configured absolute path that no longer exists
     * falls back to plain {@code "kimi"} (resolved via PATH).
     */
    public String resolvedAgentCommand() {
        if (agentCommand != null && !agentCommand.isBlank()) {
            if (Files.exists(Path.of(agentCommand))) {
                return agentCommand;
            }
            AiBuildMod.LOGGER.warn("[aibuild] configured agent_command '{}' not found, falling back to 'kimi' on PATH", agentCommand);
        }
        return "kimi";
    }

    private JsonObject toJson() {
        JsonObject o = new JsonObject();
        o.addProperty("agent_command", agentCommand);
        o.addProperty("agent_model", agentModel);
        o.addProperty("idle_timeout_minutes", idleTimeoutMinutes);
        o.addProperty("hard_timeout_minutes", hardTimeoutMinutes);
        o.addProperty("tick_budget_ms", tickBudgetMs);
        o.addProperty("max_concurrent_agents", maxConcurrentAgents);
        o.addProperty("intake_enabled", intakeEnabled);
        return o;
    }

    private static String defaultAgentCommand() {
        Path userLevel = Path.of(System.getProperty("user.home"), ".kimi-code", "bin", "kimi.exe");
        return Files.exists(userLevel) ? userLevel.toString() : "kimi";
    }
}
