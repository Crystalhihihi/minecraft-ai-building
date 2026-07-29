package com.aibuild.mod.agent;

import com.aibuild.mod.bridge.SiteGate;
import com.aibuild.mod.job.JobManager;
import com.aibuild.mod.job.SnapshotManager;
import com.aibuild.mod.job.UndoJob;
import com.aibuild.mod.selection.Selection;
import com.aibuild.mod.selection.SelectionManager;
import com.mojang.brigadier.CommandDispatcher;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

import static com.mojang.brigadier.arguments.StringArgumentType.getString;
import static com.mojang.brigadier.arguments.StringArgumentType.greedyString;
import static net.minecraft.commands.Commands.argument;
import static net.minecraft.commands.Commands.literal;

/**
 * /aibuild <description> — spawn the agent on a new build task. When the
 *   command source has a complete wand selection, the build is bound to it;
 *   otherwise the AI must propose_site and wait for player confirmation.
 * /aichat <message>     — queue mid-build, or resume the session with `kimi -r`.
 * /aicancel             — destroyForcibly the agent process.
 * /aiselect [clear]     — show or clear your selection (console uses a shared slot).
 * /aiselect set <from> <to> — set both corners (op tool; also how headless
 *   servers bind a selection for /aibuild).
 * /aiconfirm /aireject  — confirm or reject a pending AI site proposal.
 * /aiundo               — restore the newest pre-build snapshot (frame-sliced).
 * /aiundo all           — restore ALL snapshots of the newest build session,
 *   sequentially (newest first), with "k/n" chat progress.
 *
 * Usable by players (op level 2+) and by RCON/console; with no player source
 * the anchor falls back to the overworld spawn point and feedback goes to the log.
 */
public final class AgentCommands {
    private final AgentRunner runner;
    private final SelectionManager selections;
    private final SiteGate gate;
    private final JobManager jobManager;

    public AgentCommands(AgentRunner runner, SelectionManager selections, SiteGate gate, JobManager jobManager) {
        this.runner = runner;
        this.selections = selections;
        this.gate = gate;
        this.jobManager = jobManager;
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
        dispatcher.register(literal("aiselect")
                .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                .executes(ctx -> aiselectShow(ctx.getSource()))
                .then(literal("clear")
                        .executes(ctx -> aiselectClear(ctx.getSource())))
                .then(literal("set")
                        .then(argument("from", BlockPosArgument.blockPos())
                                .then(argument("to", BlockPosArgument.blockPos())
                                        .executes(ctx -> aiselectSet(ctx.getSource(),
                                                BlockPosArgument.getBlockPos(ctx, "from"),
                                                BlockPosArgument.getBlockPos(ctx, "to")))))));
        dispatcher.register(literal("aiconfirm")
                .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                .executes(ctx -> aiconfirm(ctx.getSource())));
        dispatcher.register(literal("aireject")
                .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                .executes(ctx -> aireject(ctx.getSource())));
        dispatcher.register(literal("aiundo")
                .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                .executes(ctx -> aiundo(ctx.getSource()))
                .then(literal("all")
                        .executes(ctx -> aiundoAll(ctx.getSource()))));
    }

    private int aibuild(CommandSourceStack src, String description) {
        if (runner.isRunning()) {
            src.sendFailure(Component.literal("[aibuild] an agent is already running — wait for it or /aicancel first"));
            return 0;
        }
        BlockPos anchor = anchorOf(src);
        Selection selection = selections.get(ownerOf(src));
        SiteGate.Bounds bounds = selection.isComplete() ? selection.toBounds() : null;
        try {
            runner.startBuild(description, anchor, bounds);
        } catch (Exception e) {
            src.sendFailure(Component.literal("[aibuild] failed to start agent: " + e.getMessage()));
            return 0;
        }
        String note = bounds != null
                ? " (bounds: " + bounds.describe() + ")"
                : " (no selection — AI will propose a site and wait for /aiconfirm)";
        src.sendSuccess(() -> Component.literal("[aibuild] agent started: " + description + note), false);
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

    private int aiselectShow(CommandSourceStack src) {
        Selection selection = selections.get(ownerOf(src));
        src.sendSuccess(() -> Component.literal("[aibuild] selection: " + selection.describe()), false);
        return 1;
    }

    private int aiselectClear(CommandSourceStack src) {
        selections.clear(ownerOf(src));
        src.sendSuccess(() -> Component.literal("[aibuild] selection cleared"), false);
        return 1;
    }

    private int aiselectSet(CommandSourceStack src, BlockPos from, BlockPos to) {
        String error = selections.set(ownerOf(src), from, to);
        if (error != null) {
            src.sendFailure(Component.literal("[aibuild] " + error));
            return 0;
        }
        Selection selection = selections.get(ownerOf(src));
        src.sendSuccess(() -> Component.literal("[aibuild] selection set: " + selection.toBounds().describe()), false);
        return 1;
    }

    private int aiconfirm(CommandSourceStack src) {
        SiteGate.Bounds confirmed = gate.confirm();
        if (confirmed == null) {
            src.sendFailure(Component.literal("[aibuild] no pending site proposal"));
            return 0;
        }
        runner.enqueuePlayerMessage("玩家已确认选址 " + confirmed.describe() + ";写工具已解锁,请在该范围内施工");
        src.sendSuccess(() -> Component.literal("[aibuild] site confirmed: " + confirmed.describe()), true);
        return 1;
    }

    private int aireject(CommandSourceStack src) {
        SiteGate.Bounds rejected = gate.reject();
        if (rejected == null) {
            src.sendFailure(Component.literal("[aibuild] no pending site proposal"));
            return 0;
        }
        runner.enqueuePlayerMessage("玩家拒绝了选址 " + rejected.describe() + ";请重新 propose_site 选择其他位置");
        src.sendSuccess(() -> Component.literal("[aibuild] site rejected: " + rejected.describe()
                + " — AI has been asked to propose elsewhere"), true);
        return 1;
    }

    /**
     * Restores the newest snapshot as a frame-sliced undo job (progress in
     * chat; the snapshot is consumed on success). Refused while an agent or a
     * build job is still running.
     */
    private int aiundo(CommandSourceStack src) {
        if (runner.isRunning()) {
            src.sendFailure(Component.literal("[aibuild] agent 运行中,禁止 undo——先 /aicancel 或等其完成"));
            return 0;
        }
        if (jobManager.anyRunning()) {
            src.sendFailure(Component.literal("[aibuild] 仍有建造 job 在运行,等它结束后再 undo"));
            return 0;
        }
        ServerLevel level = src.getServer().overworld();
        SnapshotManager.Loaded snapshot;
        try {
            snapshot = SnapshotManager.latest(level);
        } catch (IOException | RuntimeException e) {
            src.sendFailure(Component.literal("[aibuild] 快照读取失败(可能已损坏): " + e.getMessage()));
            return 0;
        }
        if (snapshot == null) {
            src.sendFailure(Component.literal("[aibuild] 没有可恢复的快照——还没有建造被记录,或快照已用完"));
            return 0;
        }
        SnapshotManager.Meta meta = snapshot.meta();
        UndoJob job = jobManager.submitUndo(level, snapshot.template(), meta.min(), meta.seq(),
                meta.description());
        src.sendSuccess(() -> Component.literal("[aibuild] 正在恢复快照 build-" + meta.seq()
                + " (" + meta.description() + ", " + meta.volume() + " blocks),job " + job.id().substring(0, 8)), true);
        return 1;
    }

    /**
     * Restores every snapshot of the NEWEST build session (snapshots are
     * stamped with a session tag; untagged ones form the "unknown session"
     * group, also consumable). Restores sequentially, newest first, as
     * frame-sliced undo jobs with "k/n" chat progress. Single /aiundo is unchanged.
     */
    private int aiundoAll(CommandSourceStack src) {
        if (runner.isRunning()) {
            src.sendFailure(Component.literal("[aibuild] agent 运行中,禁止 undo——先 /aicancel 或等其完成"));
            return 0;
        }
        if (jobManager.anyRunning() || jobManager.undoAllActive()) {
            src.sendFailure(Component.literal("[aibuild] 仍有建造/恢复 job 在运行,等它结束后再 undo"));
            return 0;
        }
        ServerLevel level = src.getServer().overworld();
        List<SnapshotManager.Meta> all = SnapshotManager.list(level);
        if (all.isEmpty()) {
            src.sendFailure(Component.literal("[aibuild] 没有可恢复的快照——还没有建造被记录,或快照已用完"));
            return 0;
        }
        String target = all.get(0).session(); // newest snapshot's session
        List<SnapshotManager.Meta> group = new ArrayList<>();
        for (SnapshotManager.Meta m : all) {
            if (Objects.equals(m.session(), target)) {
                group.add(m);
            }
        }
        String label = target != null ? "会话 " + target : "未知会话";
        int n = jobManager.startUndoAll(level, group, label);
        src.sendSuccess(() -> Component.literal("[aibuild] undo all:回退" + label + "的 " + n
                + " 份快照(最新优先,逐个分帧恢复)"), true);
        return 1;
    }

    private static BlockPos anchorOf(CommandSourceStack src) {
        if (src.getEntity() instanceof ServerPlayer player) {
            return player.blockPosition();
        }
        // RCON / console: anchor on the overworld spawn point.
        return src.getServer().overworld().getRespawnData().pos();
    }

    /** Selection owner: the player, or a shared console slot for RCON/console sources. */
    private static UUID ownerOf(CommandSourceStack src) {
        if (src.getEntity() instanceof ServerPlayer player) {
            return player.getUUID();
        }
        return SelectionManager.CONSOLE_UUID;
    }
}
