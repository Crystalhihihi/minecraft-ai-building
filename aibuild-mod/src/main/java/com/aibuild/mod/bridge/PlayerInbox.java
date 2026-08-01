package com.aibuild.mod.bridge;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentLinkedQueue;

/**
 * Thread-safe queue of player messages typed with /aichat while an agent is
 * running. {@link BridgeHttpServer} piggybacks the drained messages onto the
 * next JSON response as {@code "player_messages":[...]} (see bridge-http-api.md).
 * {@link #take(long)} additionally supports the ask_player endpoint: it blocks
 * until the next message arrives (or the wait slice expires).
 */
public final class PlayerInbox {
    private final ConcurrentLinkedQueue<String> queue = new ConcurrentLinkedQueue<>();
    private final Object monitor = new Object();

    public void add(String message) {
        queue.add(message);
        synchronized (monitor) {
            monitor.notifyAll();
        }
    }

    /** Removes and returns all queued messages (empty list when none). */
    public List<String> drain() {
        List<String> out = new ArrayList<>();
        String msg;
        while ((msg = queue.poll()) != null) {
            out.add(msg);
        }
        return out;
    }

    /**
     * Waits up to {@code timeoutMillis} for the next player message; returns
     * null on expiry. Used by ask_player's short-poll loop (20 s slices).
     */
    public String take(long timeoutMillis) throws InterruptedException {
        long deadline = System.currentTimeMillis() + timeoutMillis;
        while (true) {
            String msg = queue.poll();
            if (msg != null) {
                return msg;
            }
            long remaining = deadline - System.currentTimeMillis();
            if (remaining <= 0) {
                return null;
            }
            synchronized (monitor) {
                monitor.wait(remaining);
            }
        }
    }
}
