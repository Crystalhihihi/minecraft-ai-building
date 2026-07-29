package com.aibuild.mod.job;

import com.google.gson.JsonObject;
import net.minecraft.server.level.ServerLevel;

/**
 * Anything the {@link JobManager} advances once per server tick. All methods
 * run on the server main thread.
 */
public interface Job {
    String id();

    boolean isRunning();

    /** Advances the job within the given wall-clock budget (nanoseconds). */
    void step(ServerLevel level, long budgetNanos);

    void fail(ServerLevel level, String reason);

    JsonObject toJson();
}
