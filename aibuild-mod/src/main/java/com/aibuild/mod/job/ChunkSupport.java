package com.aibuild.mod.job;

import com.aibuild.mod.AiBuildMod;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.network.protocol.game.ClientboundLevelChunkWithLightPacket;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.LevelChunk;

import java.util.List;

/**
 * Shared chunk plumbing for bulk edits: force-loading (tickets) for the job
 * area, and the per-chunk finalization needed after flag-2 placements
 * (one full chunk packet + dirty flag).
 *
 * Verified against 1.21.11 (mojmap):
 * - {@code ServerLevel.setChunkForced(int, int, boolean)} — same mechanism as
 *   /forceload; persists in the save until released, so jobs must always
 *   release on completion/abort.
 * - {@code ThreadedLevelLightEngine.runLightUpdates()} must NOT be called from
 *   the server thread (throws UnsupportedOperationException — verified by a
 *   server crash). Lighting after flag-2 edits is left to the light engine's
 *   own queue: it schedules itself and pushes ClientboundLightUpdatePacket to
 *   tracking players when done, so the chunk packet below (blocks + current
 *   light) is eventually corrected automatically.
 * - {@code ServerChunkCache.chunkMap} is public;
 *   {@code ChunkMap.getPlayers(ChunkPos, boolean)} lists tracking players.
 * - {@code ClientboundLevelChunkWithLightPacket(LevelChunk, LevelLightEngine,
 *   BitSet, BitSet)} with null bitsets sends full block + light data.
 * - Never throws: a failing finalize must not take the server down via the
 *   tick event (it did once — see Phase 5 notes).
 */
final class ChunkSupport {
    private ChunkSupport() {
    }

    /** Force-loads every chunk in [minCx..maxCx] x [minCz..maxCz]; appends packed positions to out. */
    static void acquireTickets(ServerLevel level, int minCx, int minCz, int maxCx, int maxCz, List<Long> out) {
        for (int cx = minCx; cx <= maxCx; cx++) {
            for (int cz = minCz; cz <= maxCz; cz++) {
                level.setChunkForced(cx, cz, true);
                out.add(ChunkPos.asLong(cx, cz));
            }
        }
    }

    static void releaseTickets(ServerLevel level, List<Long> forcedChunks) {
        for (long packed : forcedChunks) {
            level.setChunkForced(ChunkPos.getX(packed), ChunkPos.getZ(packed), false);
        }
        forcedChunks.clear();
    }

    /**
     * Resends the chunk (blocks + current light data) to all tracking players
     * and marks it dirty for saving. Queued light updates are left to the
     * light engine itself (see class javadoc).
     */
    static void finalizeChunk(ServerLevel level, long packedPos) {
        try {
            ChunkPos pos = new ChunkPos(packedPos);
            LevelChunk chunk = level.getChunk(pos.x, pos.z);
            ClientboundLevelChunkWithLightPacket packet =
                    new ClientboundLevelChunkWithLightPacket(chunk, level.getLightEngine(), null, null);
            for (ServerPlayer player : level.getChunkSource().chunkMap.getPlayers(pos, false)) {
                player.connection.send(packet);
            }
            chunk.markUnsaved();
        } catch (Exception e) {
            AiBuildMod.LOGGER.warn("[aibuild] failed to finalize chunk {}", new ChunkPos(packedPos), e);
        }
    }
}
