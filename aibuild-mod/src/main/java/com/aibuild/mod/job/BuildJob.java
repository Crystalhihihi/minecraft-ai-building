package com.aibuild.mod.job;

import com.aibuild.mod.AiBuildMod;
import com.aibuild.mod.bridge.SiteGate;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.NoSuchElementException;
import java.util.UUID;

/**
 * An asynchronous placement job. All mutable state is touched on the server
 * main thread only (submitted via {@code server.execute()}, stepped from the
 * end-of-tick event, serialized for status queries on the same thread).
 *
 * Phase 5 upgrades:
 * - stepping is wall-clock budgeted (nanoseconds per tick) instead of a fixed
 *   block count;
 * - blocks are placed with flag 2 (client updates, no neighbor-update cascade)
 *   instead of flag 3;
 * - placements iterate chunk-bucketed (fill iterates chunk-major; placement
 *   lists are sorted by chunk), and each finished chunk is finalized once:
 *   light flush + full chunk packet + unsaved flag ({@link ChunkSupport});
 * - the job's chunk range is force-loaded on the first step and released on
 *   completion/abort, so "chunk not loaded" failures no longer occur.
 */
public final class BuildJob implements Job {
    public enum State { RUNNING, DONE, FAILED }

    private static final int MAX_STORED_ERRORS = 50;

    private final String id = UUID.randomUUID().toString();
    private final int total;
    private final Iterator<Placement> tasks;
    /** Allowed build range (SiteGate); null means "no bound" (legacy/direct submissions). */
    private final SiteGate.Bounds bounds;
    private final String description;
    /** Tight block box of this job's own placements (snapshot/ticket range); null when empty. */
    private final BlockPos boxMin;
    private final BlockPos boxMax;
    private final int minCx, minCz, maxCx, maxCz;
    private final List<Long> forcedChunks = new ArrayList<>();
    private boolean ticketsAcquired;
    /** Chunk currently being filled; finalized when the cursor moves to the next chunk. */
    private long openChunk = Long.MIN_VALUE;
    private Runnable onDone;
    private int placed;
    /** Last placed-count JobManager folded into its lifetime counter (main thread only). */
    long reportedPlaced;
    private int failed;
    private State state = State.RUNNING;
    private final List<String> errors = new ArrayList<>();
    private int nextBroadcastThreshold = 10;

    private BuildJob(int total, Iterator<Placement> tasks, SiteGate.Bounds bounds,
                     String description, BlockPos boxMin, BlockPos boxMax) {
        this.total = total;
        this.tasks = tasks;
        this.bounds = bounds;
        this.description = description;
        this.boxMin = boxMin;
        this.boxMax = boxMax;
        if (boxMin != null) {
            this.minCx = boxMin.getX() >> 4;
            this.maxCx = boxMax.getX() >> 4;
            this.minCz = boxMin.getZ() >> 4;
            this.maxCz = boxMax.getZ() >> 4;
        } else {
            this.minCx = 1;
            this.maxCx = 0;
            this.minCz = 1;
            this.maxCz = 0;
        }
    }

    public static BuildJob forPlacements(List<Placement> placements, SiteGate.Bounds bounds, String description) {
        List<Placement> sorted = new ArrayList<>(placements); // copy: callers may pass immutable lists
        sorted.sort(Comparator
                .comparingLong((Placement p) -> ChunkPos.asLong(p.pos().getX() >> 4, p.pos().getZ() >> 4))
                .thenComparingInt(p -> p.pos().getY()));
        BlockPos boxMin = null;
        BlockPos boxMax = null;
        if (!sorted.isEmpty()) {
            int minX = Integer.MAX_VALUE, minY = Integer.MAX_VALUE, minZ = Integer.MAX_VALUE;
            int maxX = Integer.MIN_VALUE, maxY = Integer.MIN_VALUE, maxZ = Integer.MIN_VALUE;
            for (Placement p : sorted) {
                minX = Math.min(minX, p.pos().getX());
                minY = Math.min(minY, p.pos().getY());
                minZ = Math.min(minZ, p.pos().getZ());
                maxX = Math.max(maxX, p.pos().getX());
                maxY = Math.max(maxY, p.pos().getY());
                maxZ = Math.max(maxZ, p.pos().getZ());
            }
            boxMin = new BlockPos(minX, minY, minZ);
            boxMax = new BlockPos(maxX, maxY, maxZ);
        }
        return new BuildJob(sorted.size(), sorted.iterator(), bounds, description, boxMin, boxMax);
    }

    public static BuildJob forFill(BlockPos min, BlockPos max, BlockState state, FillMode mode,
                                   SiteGate.Bounds bounds, String description) {
        int dx = max.getX() - min.getX() + 1;
        int dy = max.getY() - min.getY() + 1;
        int dz = max.getZ() - min.getZ() + 1;
        int total = dx * dy * dz;
        if (mode == FillMode.OUTLINE) {
            // interior cells are skipped entirely by the iterator
            long inner = (long) Math.max(dx - 2, 0) * Math.max(dy - 2, 0) * Math.max(dz - 2, 0);
            total = (int) (total - inner);
        }
        return new BuildJob(total, new FillIterator(min, max, state, mode), bounds, description, min, max);
    }

    @Override
    public String id() {
        return id;
    }

    public String description() {
        return description;
    }

    /** Blocks placed so far (main thread only; packaged for JobManager's lifetime counter). */
    long placedCount() {
        return placed;
    }

    /** Tight box of this job's placements (min corner), or null when the job is empty. */
    public BlockPos boxMin() {
        return boxMin;
    }

    public BlockPos boxMax() {
        return boxMax;
    }

    public void setOnDone(Runnable onDone) {
        this.onDone = onDone;
    }

    @Override
    public boolean isRunning() {
        return state == State.RUNNING;
    }

    @Override
    public void fail(ServerLevel level, String reason) {
        if (errors.size() < MAX_STORED_ERRORS) {
            errors.add(reason);
        }
        finish(level, State.FAILED);
    }

    /** Places blocks until the wall-clock budget is spent. Called once per tick on the main thread. */
    @Override
    public void step(ServerLevel level, long budgetNanos) {
        if (!ticketsAcquired) {
            ChunkSupport.acquireTickets(level, minCx, minCz, maxCx, maxCz, forcedChunks);
            ticketsAcquired = true;
        }
        long start = System.nanoTime();
        do {
            Placement p = tasks.next();
            if (bounds != null && !bounds.contains(p.pos())) {
                recordFailure(p, "out_of_bounds");
            } else if (level.isOutsideBuildHeight(p.pos())) {
                recordFailure(p, "outside build height");
            } else if (!level.hasChunkAt(p.pos())) {
                recordFailure(p, "chunk not loaded");
            } else if (p.keepOnly() && !level.getBlockState(p.pos()).isAir()) {
                placed++; // processed without error; block intentionally left untouched
            } else {
                long chunkKey = ChunkPos.asLong(p.pos().getX() >> 4, p.pos().getZ() >> 4);
                if (chunkKey != openChunk) {
                    if (openChunk != Long.MIN_VALUE) {
                        ChunkSupport.finalizeChunk(level, openChunk);
                    }
                    openChunk = chunkKey;
                }
                level.setBlock(p.pos(), p.state(), 2);
                placed++;
            }
        } while (tasks.hasNext() && System.nanoTime() - start < budgetNanos);
        if (!tasks.hasNext()) {
            finish(level, State.DONE);
        }
        broadcastProgress(level.getServer(), state != State.RUNNING);
    }

    private void finish(ServerLevel level, State newState) {
        if (openChunk != Long.MIN_VALUE) {
            ChunkSupport.finalizeChunk(level, openChunk);
            openChunk = Long.MIN_VALUE;
        }
        state = newState;
        if (ticketsAcquired) {
            ChunkSupport.releaseTickets(level, forcedChunks);
        }
        if (newState == State.DONE && onDone != null) {
            try {
                onDone.run();
            } catch (Exception e) {
                AiBuildMod.LOGGER.warn("[aibuild] job {} onDone hook failed", shortId(), e);
            }
        }
    }

    private void recordFailure(Placement p, String reason) {
        failed++;
        if (errors.size() < MAX_STORED_ERRORS) {
            errors.add(p.pos().getX() + "," + p.pos().getY() + "," + p.pos().getZ() + ": " + reason);
        }
    }

    private void broadcastProgress(MinecraftServer server, boolean finished) {
        int pct = total == 0 ? 100 : (int) ((placed + failed) * 100L / total);
        while (nextBroadcastThreshold < 100 && nextBroadcastThreshold <= pct) {
            announce(server, "[aibuild] job " + shortId() + " " + nextBroadcastThreshold + "% ("
                    + (placed + failed) + "/" + total + ")");
            nextBroadcastThreshold += 10;
        }
        if (finished) {
            announce(server, "[aibuild] job " + shortId() + (state == State.DONE ? " done: " : " failed: ")
                    + placed + " placed, " + failed + " failed");
        }
    }

    private void announce(MinecraftServer server, String msg) {
        AiBuildMod.LOGGER.info(msg);
        if (!server.getPlayerList().getPlayers().isEmpty()) {
            server.getPlayerList().broadcastSystemMessage(Component.literal(msg), false);
        }
    }

    private String shortId() {
        return id.substring(0, 8);
    }

    @Override
    public JsonObject toJson() {
        JsonObject o = new JsonObject();
        o.addProperty("job_id", id);
        o.addProperty("state", state.name().toLowerCase(Locale.ROOT));
        o.addProperty("total", total);
        o.addProperty("placed", placed);
        o.addProperty("failed", failed);
        JsonArray errs = new JsonArray();
        for (String e : errors) {
            errs.add(e);
        }
        o.add("errors", errs);
        return o;
    }

    /**
     * Lazily walks a fill box chunk-major (each chunk fully before the next)
     * without materializing the position list, so the stepper can finalize
     * chunks one by one. Within a chunk: x, then z, then y (bottom-up columns).
     */
    private static final class FillIterator implements Iterator<Placement> {
        private final int minX, minY, minZ, maxX, maxY, maxZ;
        private final int minCx, minCz, maxCx, maxCz;
        private final BlockState state;
        private final FillMode mode;
        private int cx, cz, x, y, z;
        private Placement next;
        private boolean nextComputed;

        FillIterator(BlockPos min, BlockPos max, BlockState state, FillMode mode) {
            this.minX = min.getX();
            this.minY = min.getY();
            this.minZ = min.getZ();
            this.maxX = max.getX();
            this.maxY = max.getY();
            this.maxZ = max.getZ();
            this.minCx = minX >> 4;
            this.maxCx = maxX >> 4;
            this.minCz = minZ >> 4;
            this.maxCz = maxZ >> 4;
            this.state = state;
            this.mode = mode;
            this.cx = minCx;
            this.cz = minCz;
            this.x = Math.max(minX, minCx << 4);
            this.y = minY;
            this.z = Math.max(minZ, minCz << 4);
        }

        @Override
        public boolean hasNext() {
            ensureNext();
            return next != null;
        }

        @Override
        public Placement next() {
            ensureNext();
            if (next == null) {
                throw new NoSuchElementException();
            }
            Placement result = next;
            next = null;
            nextComputed = false;
            return result;
        }

        private void ensureNext() {
            if (!nextComputed) {
                next = computeNext();
                nextComputed = true;
            }
        }

        private Placement computeNext() {
            while (cx <= maxCx) {
                int x1 = Math.min(maxX, (cx << 4) + 15);
                int z0 = Math.max(minZ, cz << 4);
                int z1 = Math.min(maxZ, (cz << 4) + 15);
                if (x <= x1) {
                    BlockPos pos = new BlockPos(x, y, z);
                    advance(z0);
                    boolean shell = pos.getX() == minX || pos.getX() == maxX
                            || pos.getY() == minY || pos.getY() == maxY
                            || pos.getZ() == minZ || pos.getZ() == maxZ;
                    switch (mode) {
                        case REPLACE:
                            return new Placement(pos, state, false);
                        case KEEP:
                            return new Placement(pos, state, true);
                        case HOLLOW:
                            return new Placement(pos, shell ? state : Blocks.AIR.defaultBlockState(), false);
                        case OUTLINE:
                            if (shell) {
                                return new Placement(pos, state, false);
                            }
                            break; // interior untouched
                    }
                    continue;
                }
                // chunk exhausted: move to the next chunk column
                cz++;
                if (cz > maxCz) {
                    cz = minCz;
                    cx++;
                }
                x = Math.max(minX, cx << 4);
                z = Math.max(minZ, cz << 4);
                y = minY;
            }
            return null;
        }

        /** Advances y fastest, then z, then x, within the current chunk. */
        private void advance(int z0) {
            y++;
            if (y > maxY) {
                y = minY;
                z++;
                if (z > Math.min(maxZ, (cz << 4) + 15)) {
                    z = z0;
                    x++;
                }
            }
        }
    }
}
