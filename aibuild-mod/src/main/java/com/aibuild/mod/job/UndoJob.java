package com.aibuild.mod.job;

import com.aibuild.mod.AiBuildMod;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Vec3i;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructurePlaceSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

/**
 * Frame-sliced snapshot restore ("undo"). Never places the template
 * atomically: each tick restores horizontal Y-slices of
 * {@value #SLICE_LAYERS} layers via repeated
 * {@code StructureTemplate.placeInWorld} calls whose
 * {@code StructurePlaceSettings.setBoundingBox} limits placement to the
 * current slice (verified against 1.21.11: placeInWorld skips blocks whose
 * world position falls outside the settings bounding box). Block entities are
 * restored natively by placeInWorld. Progress goes to the chat bar like a
 * normal build job; on success the consumed snapshot is deleted.
 *
 * The slice bounding box is world-space (template origin + slice offsets).
 */
public final class UndoJob implements Job {
    public enum State { RUNNING, DONE, FAILED }

    /** Y layers restored per placeInWorld call. */
    private static final int SLICE_LAYERS = 4;

    private final String id = UUID.randomUUID().toString();
    private final StructureTemplate template;
    private final BlockPos origin;
    private final Vec3i size;
    private final int snapshotSeq;
    private final String description;
    private final long total;
    private final int minCx, minCz, maxCx, maxCz;
    private final List<Long> forcedChunks = new ArrayList<>();
    private boolean ticketsAcquired;
    private int cursorY;
    private final int maxY;
    private long placed;
    private State state = State.RUNNING;
    private int nextBroadcastThreshold = 10;

    public UndoJob(StructureTemplate template, BlockPos origin, int snapshotSeq, String description) {
        this.template = template;
        this.origin = origin;
        this.size = template.getSize();
        this.snapshotSeq = snapshotSeq;
        this.description = description;
        this.total = (long) size.getX() * size.getY() * size.getZ();
        this.cursorY = origin.getY();
        this.maxY = origin.getY() + size.getY() - 1;
        this.minCx = origin.getX() >> 4;
        this.maxCx = (origin.getX() + size.getX() - 1) >> 4;
        this.minCz = origin.getZ() >> 4;
        this.maxCz = (origin.getZ() + size.getZ() - 1) >> 4;
    }

    @Override
    public String id() {
        return id;
    }

    @Override
    public boolean isRunning() {
        return state == State.RUNNING;
    }

    /** True once the restore completed (and the snapshot was consumed). */
    public boolean succeeded() {
        return state == State.DONE;
    }

    @Override
    public void fail(ServerLevel level, String reason) {
        state = State.FAILED;
        if (ticketsAcquired) {
            ChunkSupport.releaseTickets(level, forcedChunks);
        }
        announce(level.getServer(), "[aibuild] undo " + shortId() + " aborted: " + reason);
    }

    @Override
    public void step(ServerLevel level, long budgetNanos) {
        if (!ticketsAcquired) {
            ChunkSupport.acquireTickets(level, minCx, minCz, maxCx, maxCz, forcedChunks);
            ticketsAcquired = true;
        }
        long start = System.nanoTime();
        StructurePlaceSettings settings = new StructurePlaceSettings();
        do {
            int sliceTop = Math.min(maxY, cursorY + SLICE_LAYERS - 1);
            settings.setBoundingBox(new BoundingBox(
                    origin.getX(), cursorY, origin.getZ(),
                    origin.getX() + size.getX() - 1, sliceTop, origin.getZ() + size.getZ() - 1));
            template.placeInWorld(level, origin, origin, settings, level.getRandom(), 2);
            placed += (long) (sliceTop - cursorY + 1) * size.getX() * size.getZ();
            cursorY = sliceTop + 1;
        } while (cursorY <= maxY && System.nanoTime() - start < budgetNanos);
        // refresh every chunk this job covers so clients see the restored slices
        for (long packed : forcedChunks) {
            ChunkSupport.finalizeChunk(level, packed);
        }
        if (cursorY > maxY) {
            state = State.DONE;
            ChunkSupport.releaseTickets(level, forcedChunks);
            SnapshotManager.delete(level.getServer(), snapshotSeq);
        }
        broadcastProgress(level.getServer(), state == State.DONE);
    }

    private void broadcastProgress(MinecraftServer server, boolean finished) {
        int pct = total == 0 ? 100 : (int) (placed * 100L / total);
        while (nextBroadcastThreshold < 100 && nextBroadcastThreshold <= pct) {
            announce(server, "[aibuild] undo " + shortId() + " " + nextBroadcastThreshold + "% (" + placed + "/" + total + ")");
            nextBroadcastThreshold += 10;
        }
        if (finished) {
            announce(server, "[aibuild] undo " + shortId() + " done: restored snapshot build-" + snapshotSeq
                    + " (" + description + ")");
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
        o.addProperty("failed", 0);
        o.add("errors", new JsonArray());
        return o;
    }
}
