package com.aibuild.mod.bridge;

import net.minecraft.core.BlockPos;

/**
 * Per-agent-session build-bounds gate. A session has at most one allowed
 * range: either the player's wand selection (bound at /aibuild time) or an
 * AI-proposed site confirmed by a player via /aiconfirm.
 *
 * States: UNBOUND (no session) → AWAITING_PROPOSAL → PENDING_CONFIRMATION →
 * CONFIRMED (or back to AWAITING_PROPOSAL on /aireject). Write tools must
 * call {@link #currentBounds()} and reject with 409 when it returns null;
 * jobs re-check every placement against the returned bounds snapshot.
 *
 * All mutating methods are synchronized (touched from the server main thread
 * and from HTTP worker threads).
 */
public final class SiteGate {
    /** Selection / proposal volume limit (64^3), same source as the job block limit. */
    public static final long MAX_VOLUME = 262144L;

    public enum State { UNBOUND, AWAITING_PROPOSAL, PENDING_CONFIRMATION, CONFIRMED }

    /** Normalized, inclusive box. Immutable. */
    public record Bounds(int minX, int minY, int minZ, int maxX, int maxY, int maxZ) {
        public static Bounds of(BlockPos a, BlockPos b) {
            return new Bounds(
                    Math.min(a.getX(), b.getX()), Math.min(a.getY(), b.getY()), Math.min(a.getZ(), b.getZ()),
                    Math.max(a.getX(), b.getX()), Math.max(a.getY(), b.getY()), Math.max(a.getZ(), b.getZ()));
        }

        public static Bounds of(int[] min, int[] max) {
            return new Bounds(
                    Math.min(min[0], max[0]), Math.min(min[1], max[1]), Math.min(min[2], max[2]),
                    Math.max(min[0], max[0]), Math.max(min[1], max[1]), Math.max(min[2], max[2]));
        }

        public boolean contains(BlockPos p) {
            return p.getX() >= minX && p.getX() <= maxX
                    && p.getY() >= minY && p.getY() <= maxY
                    && p.getZ() >= minZ && p.getZ() <= maxZ;
        }

        public long volume() {
            return (long) (maxX - minX + 1) * (maxY - minY + 1) * (maxZ - minZ + 1);
        }

        public String describe() {
            return "[" + minX + " " + minY + " " + minZ + " ~ " + maxX + " " + maxY + " " + maxZ + "]"
                    + " size " + (maxX - minX + 1) + "x" + (maxY - minY + 1) + "x" + (maxZ - minZ + 1)
                    + " volume " + volume();
        }
    }

    private State state = State.UNBOUND;
    private Bounds bounds;
    private Bounds proposal;

    /** Starts a fresh session: bound to the selection when given, else the AI must propose a site. */
    public synchronized void beginSession(Bounds selection) {
        if (selection != null) {
            state = State.CONFIRMED;
            bounds = selection;
        } else {
            state = State.AWAITING_PROPOSAL;
            bounds = null;
        }
        proposal = null;
    }

    /** Allowed range for write tools, or null while unconfirmed (→ HTTP 409). */
    public synchronized Bounds currentBounds() {
        return state == State.CONFIRMED ? bounds : null;
    }

    public synchronized State state() {
        return state;
    }

    /**
     * Records a proposed site (state → PENDING_CONFIRMATION).
     * Returns false when a range is already confirmed or another proposal is pending.
     */
    public synchronized boolean propose(Bounds b) {
        if (state == State.CONFIRMED || state == State.PENDING_CONFIRMATION) {
            return false;
        }
        proposal = b;
        state = State.PENDING_CONFIRMATION;
        return true;
    }

    /** Confirms the pending proposal; returns it (now the allowed range), or null when none pending. */
    public synchronized Bounds confirm() {
        if (state != State.PENDING_CONFIRMATION) {
            return null;
        }
        bounds = proposal;
        proposal = null;
        state = State.CONFIRMED;
        return bounds;
    }

    /** Rejects the pending proposal; returns it, or null when none pending. State → AWAITING_PROPOSAL. */
    public synchronized Bounds reject() {
        if (state != State.PENDING_CONFIRMATION) {
            return null;
        }
        Bounds rejected = proposal;
        proposal = null;
        state = State.AWAITING_PROPOSAL;
        return rejected;
    }
}
