package com.aibuild.mod.job;

import com.aibuild.mod.AiBuildMod;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.state.BlockState;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Tracks build jobs and advances them from the end-of-server-tick event.
 * All methods run on the server main thread.
 */
public final class JobManager {
    /** Blocks placed per tick per job. */
    public static final int BLOCKS_PER_TICK = 4096;
    /** Maximum blocks a single job may touch (same source as the selection volume limit). */
    public static final int MAX_JOB_BLOCKS = 262144;
    /** Maximum entries in one set_blocks request body. */
    public static final int MAX_SET_BLOCKS_ENTRIES = 4096;

    private final Map<String, BuildJob> jobs = new LinkedHashMap<>();

    public BuildJob submitFill(BlockPos min, BlockPos max, BlockState state, FillMode mode) {
        BuildJob job = BuildJob.forFill(min, max, state, mode);
        jobs.put(job.id(), job);
        return job;
    }

    public BuildJob submitPlacements(List<Placement> placements) {
        BuildJob job = BuildJob.forPlacements(placements);
        jobs.put(job.id(), job);
        return job;
    }

    public BuildJob get(String id) {
        return jobs.get(id);
    }

    public void tick(MinecraftServer server) {
        if (jobs.isEmpty()) {
            return;
        }
        ServerLevel level = server.overworld(); // v1: overworld only
        for (BuildJob job : jobs.values()) {
            if (!job.isRunning()) {
                continue;
            }
            try {
                job.step(level, BLOCKS_PER_TICK);
            } catch (Exception e) {
                job.fail("unexpected error: " + e);
                AiBuildMod.LOGGER.error("[aibuild] job {} aborted", job.id(), e);
            }
        }
    }
}
