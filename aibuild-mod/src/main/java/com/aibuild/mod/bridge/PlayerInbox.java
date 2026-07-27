package com.aibuild.mod.bridge;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentLinkedQueue;

/**
 * Thread-safe queue of player messages typed with /aichat while an agent is
 * running. {@link BridgeHttpServer} piggybacks the drained messages onto the
 * next JSON response as {@code "player_messages":[...]} (see bridge-http-api.md).
 */
public final class PlayerInbox {
    private final ConcurrentLinkedQueue<String> queue = new ConcurrentLinkedQueue<>();

    public void add(String message) {
        queue.add(message);
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
}
