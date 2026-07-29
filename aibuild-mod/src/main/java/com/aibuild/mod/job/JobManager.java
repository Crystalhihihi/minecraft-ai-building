package com.aibuild.mod.job;

import com.aibuild.mod.AiBuildMod;
import com.aibuild.mod.bridge.SiteGate;
import com.aibuild.mod.config.AgentConfig;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Tracks jobs and advances them from the end-of-server-tick event.
 * All methods run on the server main thread unless noted otherwise.
 *
 * Every submitted build job is snapshotted synchronously at submit time
 * (before any of its blocks are placed), unless it is an undo job or has no
 * blocks at all. Tick stepping is wall-clock budgeted via
 * {@code tick_budget_ms} (default 10ms per job per tick).
 *
 * Additionally:
 * - folds every BuildJob's placed-count into a lifetime counter (read by
 *   AgentRunner for the per-build consumption report);
 * - carries the current build-session tag (set by AgentRunner) that stamps
 *   snapshot metadata for {@code /aiundo all} grouping;
 * - runs the undo-all queue: restores a group of snapshots one at a time,
 *   newest first, advancing from tick() after the step loop (submitting a job
 *   mutates {@link #jobs}, so it must not happen during iteration).
 */
public final class JobManager {
    /** Maximum blocks a single job may touch (same source as the selection volume limit). */
    public static final int MAX_JOB_BLOCKS = 262144;
    /** Maximum entries in one set_blocks request body. */
    public static final int MAX_SET_BLOCKS_ENTRIES = 4096;

    private final AgentConfig config;
    private final Map<String, Job> jobs = new LinkedHashMap<>();

    /** Total blocks ever placed by BuildJobs (main-thread writes, volatile reads). */
    private volatile long lifetimePlaced;
    /** Snapshot session tag for jobs submitted while an agent build session is open; null otherwise. */
    private String currentBuildSession;

    // undo-all queue state
    private final Deque<Integer> undoAllQueue = new ArrayDeque<>();
    private int undoAllTotal;
    private String undoAllLabel = "";
    private UndoJob activeUndoAll;

    public JobManager(AgentConfig config) {
        this.config = config;
    }

    public BuildJob submitFill(ServerLevel level, BlockPos min, BlockPos max, BlockState state,
                               FillMode mode, SiteGate.Bounds bounds, String description) {
        BuildJob job = BuildJob.forFill(min, max, state, mode, bounds, description);
        SnapshotManager.capture(level, min, max, description, currentBuildSession);
        jobs.put(job.id(), job);
        return job;
    }

    public BuildJob submitPlacements(ServerLevel level, List<Placement> placements,
                                     SiteGate.Bounds bounds, String description) {
        BuildJob job = BuildJob.forPlacements(placements, bounds, description);
        if (job.boxMin() != null) {
            SnapshotManager.capture(level, job.boxMin(), job.boxMax(), description, currentBuildSession);
        } else {
            AiBuildMod.LOGGER.warn("[aibuild] job submitted with no blocks ({}); skipping snapshot", description);
        }
        jobs.put(job.id(), job);
        return job;
    }

    /** Snapshot restore: never creates a new snapshot itself. */
    public UndoJob submitUndo(ServerLevel level, StructureTemplate template, BlockPos origin,
                              int snapshotSeq, String description) {
        UndoJob job = new UndoJob(template, origin, snapshotSeq, description);
        jobs.put(job.id(), job);
        return job;
    }

    public Job get(String id) {
        return jobs.get(id);
    }

    public boolean anyRunning() {
        for (Job job : jobs.values()) {
            if (job.isRunning()) {
                return true;
            }
        }
        return false;
    }

    /** Blocks ever placed by build jobs (safe to read from any thread). */
    public long lifetimePlaced() {
        return lifetimePlaced;
    }

    /** Opens a build session: subsequently submitted jobs' snapshots are stamped with {@code tag}. */
    public void beginBuildSession(String tag) {
        currentBuildSession = tag;
    }

    /** Closes the build session; later jobs fall back to the "unknown session" group. */
    public void endBuildSession() {
        currentBuildSession = null;
    }

    public boolean undoAllActive() {
        return activeUndoAll != null || !undoAllQueue.isEmpty();
    }

    /**
     * Queues a group of snapshots for sequential undo (the deque must be
     * newest-first). Returns the group size. Restoration starts on the next tick.
     */
    public int startUndoAll(ServerLevel level, List<SnapshotManager.Meta> newestFirst, String label) {
        undoAllQueue.clear();
        for (SnapshotManager.Meta m : newestFirst) {
            undoAllQueue.addLast(m.seq());
        }
        undoAllTotal = newestFirst.size();
        undoAllLabel = label;
        activeUndoAll = null;
        return undoAllTotal;
    }

    public void tick(MinecraftServer server) {
        if (jobs.isEmpty() && !undoAllActive()) {
            return;
        }
        ServerLevel level = server.overworld(); // v1: overworld only
        long budgetNanos = Math.max(1L, config.tickBudgetMs()) * 1_000_000L;
        for (Job job : jobs.values()) {
            if (!job.isRunning()) {
                continue;
            }
            try {
                job.step(level, budgetNanos);
            } catch (Exception e) {
                job.fail(level, "unexpected error: " + e);
                AiBuildMod.LOGGER.error("[aibuild] job {} aborted", job.id(), e);
            }
            if (job instanceof BuildJob bj) {
                lifetimePlaced += bj.placedCount() - bj.reportedPlaced;
                bj.reportedPlaced = bj.placedCount();
            }
        }
        advanceUndoAll(level);
    }

    /** Drives the undo-all queue: one restore job at a time, launched outside the step loop. */
    private void advanceUndoAll(ServerLevel level) {
        if (activeUndoAll != null) {
            if (activeUndoAll.isRunning()) {
                return;
            }
            if (!activeUndoAll.succeeded()) {
                undoAllQueue.clear();
                activeUndoAll = null;
                announce(level.getServer(), "[aibuild] undo all 中止:快照恢复失败,剩余 " + undoAllQueue.size() + " 份未恢复");
                return;
            }
            activeUndoAll = null;
        }
        if (undoAllQueue.isEmpty()) {
            if (undoAllTotal > 0) {
                announce(level.getServer(), "[aibuild] undo all 完成:" + undoAllLabel + " 的 " + undoAllTotal + " 份快照全部恢复");
                undoAllTotal = 0;
            }
            return;
        }
        int seq = undoAllQueue.poll();
        int k = undoAllTotal - undoAllQueue.size();
        try {
            SnapshotManager.Loaded snap = SnapshotManager.load(level, seq);
            activeUndoAll = submitUndo(level, snap.template(), snap.meta().min(), seq,
                    undoAllLabel + " " + k + "/" + undoAllTotal);
            announce(level.getServer(), "[aibuild] undo all " + k + "/" + undoAllTotal
                    + ": 恢复快照 build-" + seq + " (" + snap.meta().description() + ")");
        } catch (Exception e) {
            undoAllQueue.clear();
            announce(level.getServer(), "[aibuild] undo all 中止:快照 build-" + seq + " 读取失败: " + e.getMessage());
        }
    }

    private void announce(MinecraftServer server, String msg) {
        AiBuildMod.LOGGER.info(msg);
        if (!server.getPlayerList().getPlayers().isEmpty()) {
            server.getPlayerList().broadcastSystemMessage(Component.literal(msg), false);
        }
    }
}
