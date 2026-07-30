package com.aibuild.mod.bridge;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
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
 * Since E3 every build session owns one SiteGate instance; the session
 * manager persists gate state (see {@link #toJson()}/{@link #restore}) so
 * confirmed sites survive a server restart, and checks new proposals against
 * other running sessions' {@link #activeBounds()} for spatial isolation.
 *
 * All mutating methods are synchronized (touched from the server main thread
 * and from HTTP worker threads). The {@link #setOnChange onChange} hook fires
 * AFTER the gate lock is released, so a hook that persists the registry
 * cannot deadlock against manager→gate call paths.
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

        /** Inclusive-box intersection (touching faces count as intersecting). */
        public boolean intersects(Bounds o) {
            return minX <= o.maxX && maxX >= o.minX
                    && minY <= o.maxY && maxY >= o.minY
                    && minZ <= o.maxZ && maxZ >= o.minZ;
        }

        public long volume() {
            return (long) (maxX - minX + 1) * (maxY - minY + 1) * (maxZ - minZ + 1);
        }

        public String describe() {
            return "[" + minX + " " + minY + " " + minZ + " ~ " + maxX + " " + maxY + " " + maxZ + "]"
                    + " size " + (maxX - minX + 1) + "x" + (maxY - minY + 1) + "x" + (maxZ - minZ + 1)
                    + " volume " + volume();
        }

        public JsonArray toJson() {
            JsonArray a = new JsonArray();
            a.add(minX);
            a.add(minY);
            a.add(minZ);
            a.add(maxX);
            a.add(maxY);
            a.add(maxZ);
            return a;
        }

        public static Bounds fromJson(JsonArray a) {
            return new Bounds(a.get(0).getAsInt(), a.get(1).getAsInt(), a.get(2).getAsInt(),
                    a.get(3).getAsInt(), a.get(4).getAsInt(), a.get(5).getAsInt());
        }
    }

    private State state = State.UNBOUND;
    private Bounds bounds;
    private Bounds proposal;
    /** Wall-clock of the last accepted proposal; routes /aiconfirm to the newest pending session. */
    private long proposalAtMillis;
    private Runnable onChange;

    /** Starts a fresh session: bound to the selection when given, else the AI must propose a site. */
    public void beginSession(Bounds selection) {
        synchronized (this) {
            if (selection != null) {
                state = State.CONFIRMED;
                bounds = selection;
            } else {
                state = State.AWAITING_PROPOSAL;
                bounds = null;
            }
            proposal = null;
        }
        fireChange();
    }

    /** Allowed range for write tools, or null while unconfirmed (→ HTTP 409). */
    public synchronized Bounds currentBounds() {
        return state == State.CONFIRMED ? bounds : null;
    }

    /**
     * Bounds relevant for cross-session overlap checks: the confirmed range,
     * or the pending proposal while awaiting confirmation. Null otherwise.
     */
    public synchronized Bounds activeBounds() {
        if (state == State.CONFIRMED) {
            return bounds;
        }
        if (state == State.PENDING_CONFIRMATION) {
            return proposal;
        }
        return null;
    }

    public synchronized State state() {
        return state;
    }

    public synchronized long proposalAtMillis() {
        return proposalAtMillis;
    }

    /**
     * Records a proposed site (state → PENDING_CONFIRMATION).
     * Returns false when a range is already confirmed or another proposal is pending.
     */
    public boolean propose(Bounds b) {
        synchronized (this) {
            if (state == State.CONFIRMED || state == State.PENDING_CONFIRMATION) {
                return false;
            }
            proposal = b;
            proposalAtMillis = System.currentTimeMillis();
            state = State.PENDING_CONFIRMATION;
        }
        fireChange();
        return true;
    }

    /** Confirms the pending proposal; returns it (now the allowed range), or null when none pending. */
    public Bounds confirm() {
        Bounds confirmed;
        synchronized (this) {
            if (state != State.PENDING_CONFIRMATION) {
                return null;
            }
            bounds = proposal;
            proposal = null;
            state = State.CONFIRMED;
            confirmed = bounds;
        }
        fireChange();
        return confirmed;
    }

    /** Rejects the pending proposal; returns it, or null when none pending. State → AWAITING_PROPOSAL. */
    public Bounds reject() {
        Bounds rejected;
        synchronized (this) {
            if (state != State.PENDING_CONFIRMATION) {
                return null;
            }
            rejected = proposal;
            proposal = null;
            state = State.AWAITING_PROPOSAL;
        }
        fireChange();
        return rejected;
    }

    /** Persistence hook, invoked after every mutation (outside the gate lock). */
    public synchronized void setOnChange(Runnable onChange) {
        this.onChange = onChange;
    }

    public synchronized JsonObject toJson() {
        JsonObject o = new JsonObject();
        o.addProperty("state", state.name().toLowerCase(java.util.Locale.ROOT));
        if (bounds != null) {
            o.add("bounds", bounds.toJson());
        }
        if (proposal != null) {
            o.add("proposal", proposal.toJson());
            o.addProperty("proposal_at", proposalAtMillis);
        }
        return o;
    }

    /** Restores gate state from persisted JSON (server restart); fires no change hook. */
    public synchronized void restore(JsonObject o) {
        String s = o.has("state") ? o.get("state").getAsString() : "unbound";
        state = switch (s) {
            case "awaiting_proposal" -> State.AWAITING_PROPOSAL;
            case "pending_confirmation" -> State.PENDING_CONFIRMATION;
            case "confirmed" -> State.CONFIRMED;
            default -> State.UNBOUND;
        };
        bounds = o.has("bounds") && o.get("bounds").isJsonArray() ? Bounds.fromJson(o.getAsJsonArray("bounds")) : null;
        proposal = o.has("proposal") && o.get("proposal").isJsonArray() ? Bounds.fromJson(o.getAsJsonArray("proposal")) : null;
        proposalAtMillis = o.has("proposal_at") ? o.get("proposal_at").getAsLong() : 0L;
    }

    private void fireChange() {
        Runnable hook;
        synchronized (this) {
            hook = onChange;
        }
        if (hook != null) {
            hook.run();
        }
    }
}
