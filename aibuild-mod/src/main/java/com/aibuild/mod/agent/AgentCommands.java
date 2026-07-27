package com.aibuild.mod.agent;

import com.mojang.brigadier.CommandDispatcher;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;

import static com.mojang.brigadier.arguments.StringArgumentType.getString;
import static com.mojang.brigadier.arguments.StringArgumentType.greedyString;
import static net.minecraft.commands.Commands.argument;
import static net.minecraft.commands.Commands.literal;

/**
 * /aibuild <description> — spawn the agent on a new build task.
 * /aichat <message>     — queue mid-build, or resume the session with `kimi -r`.
 * /aicancel             — destroyForcibly the agent process.
 *
 * Usable by players (op level 2+) and by RCON/console; with no player source
 * the anchor falls back to the overworld spawn point and feedback goes to the log.
 */
public final class AgentCommands {
    private final AgentRunner runner;

    public AgentCommands(AgentRunner runner) {
        this.runner = runner;
    }

    public void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(literal("aibuild")
                .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                .then(argument("description", greedyString())
                        .executes(ctx -> aibuild(ctx.getSource(), getString(ctx, "description")))));
        dispatcher.register(literal("aichat")
                .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                .then(argument("message", greedyString())
                        .executes(ctx -> aichat(ctx.getSource(), getString(ctx, "message")))));
        dispatcher.register(literal("aicancel")
                .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                .executes(ctx -> aicancel(ctx.getSource())));
    }

    private int aibuild(CommandSourceStack src, String description) {
        if (runner.isRunning()) {
            src.sendFailure(Component.literal("[aibuild] an agent is already running — wait for it or /aicancel first"));
            return 0;
        }
        BlockPos anchor = anchorOf(src);
        try {
            runner.startBuild(description, anchor);
        } catch (Exception e) {
            src.sendFailure(Component.literal("[aibuild] failed to start agent: " + e.getMessage()));
            return 0;
        }
        src.sendSuccess(() -> Component.literal("[aibuild] agent started: " + description), false);
        return 1;
    }

    private int aichat(CommandSourceStack src, String message) {
        if (runner.isRunning()) {
            runner.enqueuePlayerMessage(message);
            src.sendSuccess(() -> Component.literal("[已排队,AI 下次行动时送达] " + message), false);
            return 1;
        }
        if (!runner.hasSession()) {
            src.sendFailure(Component.literal("[aibuild] no agent session to continue — start one with /aibuild"));
            return 0;
        }
        try {
            runner.startChat(message);
        } catch (Exception e) {
            src.sendFailure(Component.literal("[aibuild] failed to resume session: " + e.getMessage()));
            return 0;
        }
        src.sendSuccess(() -> Component.literal("[aibuild] resuming session with your message"), false);
        return 1;
    }

    private int aicancel(CommandSourceStack src) {
        if (!runner.isRunning()) {
            src.sendFailure(Component.literal("[aibuild] no agent is running"));
            return 0;
        }
        runner.cancel();
        src.sendSuccess(() -> Component.literal("[aibuild] agent cancelled"), false);
        return 1;
    }

    private static BlockPos anchorOf(CommandSourceStack src) {
        if (src.getEntity() instanceof ServerPlayer player) {
            return player.blockPosition();
        }
        // RCON / console: anchor on the overworld spawn point.
        return src.getServer().overworld().getRespawnData().pos();
    }
}
