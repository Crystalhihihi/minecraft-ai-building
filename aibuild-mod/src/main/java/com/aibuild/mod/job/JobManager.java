package com.aibuild.mod.job;

import com.aibuild.mod.AiBuildMod;
import com.aibuild.mod.bridge.SiteGate;
import com.aibuild.mod.config.AgentConfig;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Tracks jobs and advances them from the end-of-server-tick event.
 * All methods run on the server main thread.
 *
 * Every submitted build job is snapshotted synchronously at submit time
 * (before any of its blocks are placed), unless it is an undo job or has no
 * blocks at all. Tick stepping is wall-clock budgeted via
 * {@code tick_budget_ms} (default 10ms per job per tick).
 */
public final class JobManager {
    /** Maximum blocks a single job may touch (same source as the selection volume limit). */
    public static final int MAX_JOB_BLOCKS = 262144;
    /** Maximum entries in one set_blocks request body. */
    public static final int MAX_SET_BLOCKS_ENTRIES = 4096;

    private final AgentConfig config;
    private final Map<String, Job> jobs = new LinkedHashMap<>();

    public JobManager(AgentConfig config) {
        this.config = config;
    }

    public BuildJob submitFill(ServerLevel level, BlockPos min, BlockPos max, BlockState state,
                               FillMode mode, SiteGate.Bounds bounds, String description) {
        BuildJob job = BuildJob.forFill(min, max, state, mode, bounds, description);
        SnapshotManager.capture(level, min, max, description);
        jobs.put(job.id(), job);
        return job;
    }

    public BuildJob submitPlacements(ServerLevel level, List<Placement> placements,
                                     SiteGate.Bounds bounds, String description) {
        BuildJob job = BuildJob.forPlacements(placements, bounds, description);
        if (job.boxMin() != null) {
            SnapshotManager.capture(level, job.boxMin(), job.boxMax(), description);
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

    public void tick(MinecraftServer server) {
        if (jobs.isEmpty()) {
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
        }
    }
}
