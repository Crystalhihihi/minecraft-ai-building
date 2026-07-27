package com.aibuild.mod.selection;

import com.aibuild.mod.AiBuildMod;
import com.aibuild.mod.agent.WorkDir;
import com.aibuild.mod.bridge.SiteGate;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Per-player wand selections, in memory and persisted per world at
 * {@code <world>/aibuild/selection-<uuid>.json}. Loaded lazily from disk the
 * first time a player's selection is queried in a server session.
 *
 * RCON/console has no player identity; commands executed there use
 * {@link #CONSOLE_UUID} so headless servers (and tests) can still bind a
 * selection to /aibuild.
 *
 * All entry points run on the server main thread.
 */
public final class SelectionManager {
    public static final UUID CONSOLE_UUID = new UUID(0L, 0L);

    private final Map<UUID, Selection> selections = new ConcurrentHashMap<>();
    private MinecraftServer server;

    public void onServerStarted(MinecraftServer server) {
        this.server = server;
        this.selections.clear();
    }

    public void onServerStopping() {
        this.server = null;
        this.selections.clear();
    }

    /** Current selection for the owner (never null; {@link Selection#EMPTY} when unset). */
    public Selection get(UUID owner) {
        return selections.computeIfAbsent(owner, this::load);
    }

    /** Wand left-click: set corner 1 and echo. */
    public void setFirst(ServerPlayer player, BlockPos pos) {
        UUID owner = player.getUUID();
        Selection updated = get(owner).withCorner1(pos);
        selections.put(owner, updated);
        save(owner, updated);
        player.sendSystemMessage(Component.literal("[aibuild] selection corner 1 = ("
                + pos.getX() + " " + pos.getY() + " " + pos.getZ() + ")" + echoSuffix(updated)));
    }

    /** Wand right-click: set corner 2 (rejected when the resulting volume is over the limit). */
    public void setSecond(ServerPlayer player, BlockPos pos) {
        UUID owner = player.getUUID();
        Selection updated = get(owner).withCorner2(pos);
        String error = volumeError(updated);
        if (error != null) {
            player.sendSystemMessage(Component.literal("[aibuild] " + error + " — corner 2 not set"));
            return;
        }
        selections.put(owner, updated);
        save(owner, updated);
        player.sendSystemMessage(Component.literal("[aibuild] selection corner 2 = ("
                + pos.getX() + " " + pos.getY() + " " + pos.getZ() + ")" + echoSuffix(updated)));
    }

    /**
     * /aiselect set: replace both corners at once. Returns an error message, or
     * null on success (selection stored + persisted).
     */
    public String set(UUID owner, BlockPos a, BlockPos b) {
        Selection updated = new Selection(a, b);
        String error = volumeError(updated);
        if (error != null) {
            return error;
        }
        selections.put(owner, updated);
        save(owner, updated);
        return null;
    }

    public void clear(UUID owner) {
        selections.put(owner, Selection.EMPTY);
        save(owner, Selection.EMPTY);
    }

    private static String echoSuffix(Selection s) {
        if (s.isComplete()) {
            return " — complete: " + s.toBounds().describe();
        }
        return " (set the other corner to complete the selection)";
    }

    /** Error message when the selection volume exceeds the limit, else null. */
    private static String volumeError(Selection s) {
        if (!s.isComplete()) {
            return null;
        }
        long volume = s.toBounds().volume();
        if (volume > SiteGate.MAX_VOLUME) {
            return "selection volume " + volume + " exceeds limit of " + SiteGate.MAX_VOLUME + " blocks";
        }
        return null;
    }

    // ------------------------------------------------------------------ persistence

    private Path file(UUID owner) {
        return WorkDir.dirOf(server).resolve("selection-" + owner + ".json");
    }

    private Selection load(UUID owner) {
        if (server == null) {
            return Selection.EMPTY;
        }
        Path path = file(owner);
        if (!Files.isRegularFile(path)) {
            return Selection.EMPTY;
        }
        try {
            JsonObject o = JsonParser.parseString(Files.readString(path)).getAsJsonObject();
            BlockPos c1 = o.has("corner1") ? readPos(o.getAsJsonArray("corner1")) : null;
            BlockPos c2 = o.has("corner2") ? readPos(o.getAsJsonArray("corner2")) : null;
            Selection s = new Selection(c1, c2);
            if (s.isComplete() && volumeError(s) != null) {
                AiBuildMod.LOGGER.warn("[aibuild] ignoring over-limit selection in {}", path);
                return Selection.EMPTY;
            }
            return s;
        } catch (Exception e) {
            AiBuildMod.LOGGER.warn("[aibuild] could not read selection from {}", path, e);
            return Selection.EMPTY;
        }
    }

    private void save(UUID owner, Selection s) {
        if (server == null) {
            return;
        }
        Path path = file(owner);
        try {
            if (!s.isComplete() && s.corner1() == null && s.corner2() == null) {
                Files.deleteIfExists(path);
                return;
            }
            Files.createDirectories(path.getParent());
            JsonObject o = new JsonObject();
            if (s.corner1() != null) {
                o.add("corner1", writePos(s.corner1()));
            }
            if (s.corner2() != null) {
                o.add("corner2", writePos(s.corner2()));
            }
            Files.writeString(path, o + System.lineSeparator());
        } catch (IOException e) {
            AiBuildMod.LOGGER.warn("[aibuild] could not persist selection to {}", path, e);
        }
    }

    private static BlockPos readPos(JsonArray arr) {
        return new BlockPos(arr.get(0).getAsInt(), arr.get(1).getAsInt(), arr.get(2).getAsInt());
    }

    private static JsonArray writePos(BlockPos p) {
        JsonArray arr = new JsonArray();
        arr.add(p.getX());
        arr.add(p.getY());
        arr.add(p.getZ());
        return arr;
    }
}
