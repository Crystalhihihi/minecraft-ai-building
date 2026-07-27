package com.aibuild.mod.job;

import com.aibuild.mod.AiBuildMod;
import com.aibuild.mod.bridge.SiteGate;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.NoSuchElementException;
import java.util.UUID;

/**
 * An asynchronous placement job. All mutable state is touched on the server
 * main thread only (submitted via {@code server.execute()}, stepped from the
 * end-of-tick event, serialized for status queries on the same thread).
 */
public final class BuildJob {
    public enum State { RUNNING, DONE, FAILED }

    private static final int MAX_STORED_ERRORS = 50;

    private final String id = UUID.randomUUID().toString();
    private final int total;
    private final Iterator<Placement> tasks;
    /** Allowed build range snapshot; null means "no bound" (legacy/direct submissions). */
    private final SiteGate.Bounds bounds;
    private int placed;
    private int failed;
    private State state = State.RUNNING;
    private final List<String> errors = new ArrayList<>();
    private int nextBroadcastThreshold = 10;

    private BuildJob(int total, Iterator<Placement> tasks, SiteGate.Bounds bounds) {
        this.total = total;
        this.tasks = tasks;
        this.bounds = bounds;
    }

    public static BuildJob forPlacements(List<Placement> placements, SiteGate.Bounds bounds) {
        return new BuildJob(placements.size(), placements.iterator(), bounds);
    }

    public static BuildJob forFill(BlockPos min, BlockPos max, BlockState state, FillMode mode, SiteGate.Bounds bounds) {
        int dx = max.getX() - min.getX() + 1;
        int dy = max.getY() - min.getY() + 1;
        int dz = max.getZ() - min.getZ() + 1;
        int total = dx * dy * dz;
        if (mode == FillMode.OUTLINE) {
            // interior cells are skipped entirely by the iterator
            long inner = (long) Math.max(dx - 2, 0) * Math.max(dy - 2, 0) * Math.max(dz - 2, 0);
            total = (int) (total - inner);
        }
        return new BuildJob(total, new FillIterator(min, max, state, mode), bounds);
    }

    public String id() {
        return id;
    }

    public boolean isRunning() {
        return state == State.RUNNING;
    }

    public void fail(String reason) {
        this.state = State.FAILED;
        if (errors.size() < MAX_STORED_ERRORS) {
            errors.add(reason);
        }
    }

    /** Places up to {@code budget} blocks. Called once per tick on the main thread. */
    public void step(ServerLevel level, int budget) {
        int processed = 0;
        while (processed < budget && tasks.hasNext()) {
            Placement p = tasks.next();
            processed++;
            if (bounds != null && !bounds.contains(p.pos())) {
                recordFailure(p, "out_of_bounds");
                continue;
            }
            if (level.isOutsideBuildHeight(p.pos())) {
                recordFailure(p, "outside build height");
                continue;
            }
            if (!level.hasChunkAt(p.pos())) {
                recordFailure(p, "chunk not loaded");
                continue;
            }
            if (p.keepOnly() && !level.getBlockState(p.pos()).isAir()) {
                placed++; // processed without error; block intentionally left untouched
                continue;
            }
            level.setBlock(p.pos(), p.state(), 3);
            placed++;
        }
        if (!tasks.hasNext()) {
            state = State.DONE;
        }
        broadcastProgress(level.getServer(), state == State.DONE);
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
            announce(server, "[aibuild] job " + shortId() + " done: " + placed + " placed, " + failed + " failed");
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

    /** Lazily walks a fill box without materializing the position list. */
    private static final class FillIterator implements Iterator<Placement> {
        private final int minX, minY, minZ, maxX, maxY, maxZ;
        private final BlockState state;
        private final FillMode mode;
        private int x, y, z;
        private Placement next;
        private boolean nextComputed;

        FillIterator(BlockPos min, BlockPos max, BlockState state, FillMode mode) {
            this.minX = min.getX();
            this.minY = min.getY();
            this.minZ = min.getZ();
            this.maxX = max.getX();
            this.maxY = max.getY();
            this.maxZ = max.getZ();
            this.state = state;
            this.mode = mode;
            this.x = minX;
            this.y = minY;
            this.z = minZ;
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
            while (y <= maxY) {
                BlockPos pos = new BlockPos(x, y, z);
                advance();
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
            }
            return null;
        }

        private void advance() {
            x++;
            if (x > maxX) {
                x = minX;
                z++;
                if (z > maxZ) {
                    z = minZ;
                    y++;
                }
            }
        }
    }
}
