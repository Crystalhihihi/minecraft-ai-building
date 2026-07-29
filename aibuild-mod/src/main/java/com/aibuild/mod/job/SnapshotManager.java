package com.aibuild.mod.job;

import com.aibuild.mod.AiBuildMod;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Vec3i;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;
import net.minecraft.world.level.storage.LevelResource;
import org.jetbrains.annotations.Nullable;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Pre-build world snapshots, stored under {@code <world>/aibuild/snapshots/}:
 * {@code build-<seq>.nbt} (a {@link StructureTemplate} captured with
 * {@code fillFromWorld}, block entities included) plus {@code build-<seq>.json}
 * metadata (seq/bounds/time/description). The newest {@value #KEEP} snapshots
 * are kept; older ones are pruned after every capture.
 *
 * Everything runs on the server main thread.
 */
public final class SnapshotManager {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final int KEEP = 10;
    /** Never snapshot more than the per-job block limit (sparse set_blocks could span huge boxes). */
    private static final long MAX_SNAPSHOT_VOLUME = JobManager.MAX_JOB_BLOCKS;
    private static final Pattern NBT_NAME = Pattern.compile("build-(\\d+)\\.nbt");

    private SnapshotManager() {
    }

    /**
     * @param session build-session tag stamping the snapshot (null = "unknown
     *                session", e.g. direct curl builds); {@code /aiundo all}
     *                groups by this tag
     */
    public record Meta(int seq, int minX, int minY, int minZ, int maxX, int maxY, int maxZ,
                       String description, String timestamp, @Nullable String session) {
        public BlockPos min() {
            return new BlockPos(minX, minY, minZ);
        }

        public BlockPos max() {
            return new BlockPos(maxX, maxY, maxZ);
        }

        public long volume() {
            return (long) (maxX - minX + 1) * (maxY - minY + 1) * (maxZ - minZ + 1);
        }
    }

    public record Loaded(Meta meta, StructureTemplate template) {
    }

    public static Path dirOf(MinecraftServer server) {
        return server.getWorldPath(LevelResource.ROOT).resolve("aibuild").resolve("snapshots");
    }

    /**
     * Captures the inclusive box synchronously. Returns the snapshot seq, or
     * -1 when skipped (oversized box) or failed (logged).
     *
     * @param session build-session tag for {@code /aiundo all} grouping, or null
     */
    public static int capture(ServerLevel level, BlockPos min, BlockPos max, String description, @Nullable String session) {
        long volume = (long) (max.getX() - min.getX() + 1) * (max.getY() - min.getY() + 1) * (max.getZ() - min.getZ() + 1);
        if (volume > MAX_SNAPSHOT_VOLUME) {
            AiBuildMod.LOGGER.warn("[aibuild] snapshot skipped: box volume {} exceeds {} ({} — {})",
                    volume, MAX_SNAPSHOT_VOLUME, description, min.toShortString());
            return -1;
        }
        try {
            StructureTemplate template = new StructureTemplate();
            // empty ignore-list => every block in the box is captured, air included
            template.fillFromWorld(level, min, new Vec3i(
                    max.getX() - min.getX() + 1,
                    max.getY() - min.getY() + 1,
                    max.getZ() - min.getZ() + 1), false, List.of());
            Path dir = dirOf(level.getServer());
            Files.createDirectories(dir);
            int seq = nextSeq(dir);
            NbtIo.writeCompressed(template.save(new CompoundTag()), dir.resolve(nbtName(seq)));
            Meta meta = new Meta(seq, min.getX(), min.getY(), min.getZ(),
                    max.getX(), max.getY(), max.getZ(), description, Instant.now().toString(), session);
            Files.writeString(dir.resolve(metaName(seq)), GSON.toJson(toJson(meta)) + System.lineSeparator());
            prune(dir);
            AiBuildMod.LOGGER.info("[aibuild] snapshot build-{} captured: {} blocks ({}), {}{}",
                    seq, volume, min.toShortString() + " ~ " + max.toShortString(), description,
                    session != null ? " [session " + session + "]" : "");
            return seq;
        } catch (Exception e) {
            AiBuildMod.LOGGER.error("[aibuild] snapshot capture failed ({} — {})", description, min.toShortString(), e);
            return -1;
        }
    }

    /** Newest snapshot, or null when none exists. Throws on corrupt data. */
    public static Loaded latest(ServerLevel level) throws IOException {
        int seq = latestSeq(dirOf(level.getServer()));
        return seq < 0 ? null : load(level, seq);
    }

    /** Loads one snapshot's metadata + template. Throws on corrupt/missing data. */
    public static Loaded load(ServerLevel level, int seq) throws IOException {
        Path dir = dirOf(level.getServer());
        Meta meta = readMeta(dir, seq);
        CompoundTag tag = NbtIo.readCompressed(dir.resolve(nbtName(seq)), NbtAccounter.unlimitedHeap());
        StructureTemplate template = new StructureTemplate();
        template.load(level.registryAccess().lookupOrThrow(Registries.BLOCK), tag);
        return new Loaded(meta, template);
    }

    /** All snapshot metadatas, newest first; entries with corrupt/missing json are skipped (logged). */
    public static List<Meta> list(ServerLevel level) {
        Path dir = dirOf(level.getServer());
        List<Integer> seqs = seqs(dir);
        List<Meta> out = new ArrayList<>(seqs.size());
        for (int i = seqs.size() - 1; i >= 0; i--) {
            try {
                out.add(readMeta(dir, seqs.get(i)));
            } catch (Exception e) {
                AiBuildMod.LOGGER.warn("[aibuild] skipping unreadable snapshot meta build-{}", seqs.get(i), e);
            }
        }
        return out;
    }

    /** Deletes the given snapshot's files (consumed by a successful undo). Missing files are ignored. */
    public static void delete(MinecraftServer server, int seq) {
        Path dir = dirOf(server);
        try {
            Files.deleteIfExists(dir.resolve(nbtName(seq)));
            Files.deleteIfExists(dir.resolve(metaName(seq)));
        } catch (IOException e) {
            AiBuildMod.LOGGER.warn("[aibuild] failed to delete snapshot build-{}", seq, e);
        }
    }

    /** Number of stored snapshots (for diagnostics). */
    public static int count(MinecraftServer server) {
        return seqs(dirOf(server)).size();
    }

    // ------------------------------------------------------------------ internals

    private static String nbtName(int seq) {
        return "build-" + seq + ".nbt";
    }

    private static String metaName(int seq) {
        return "build-" + seq + ".json";
    }

    private static List<Integer> seqs(Path dir) {
        List<Integer> out = new ArrayList<>();
        if (!Files.isDirectory(dir)) {
            return out;
        }
        try (var stream = Files.list(dir)) {
            for (Path p : stream.toList()) {
                Matcher m = NBT_NAME.matcher(p.getFileName().toString());
                if (m.matches()) {
                    out.add(Integer.parseInt(m.group(1)));
                }
            }
        } catch (IOException e) {
            AiBuildMod.LOGGER.warn("[aibuild] failed to list snapshots in {}", dir, e);
        }
        out.sort(Comparator.naturalOrder());
        return out;
    }

    private static int nextSeq(Path dir) {
        List<Integer> seqs = seqs(dir);
        return seqs.isEmpty() ? 1 : seqs.get(seqs.size() - 1) + 1;
    }

    private static int latestSeq(Path dir) {
        List<Integer> seqs = seqs(dir);
        return seqs.isEmpty() ? -1 : seqs.get(seqs.size() - 1);
    }

    private static void prune(Path dir) {
        List<Integer> seqs = seqs(dir);
        for (int i = 0; i < seqs.size() - KEEP; i++) {
            int seq = seqs.get(i);
            try {
                Files.deleteIfExists(dir.resolve(nbtName(seq)));
                Files.deleteIfExists(dir.resolve(metaName(seq)));
                AiBuildMod.LOGGER.info("[aibuild] pruned old snapshot build-{}", seq);
            } catch (IOException e) {
                AiBuildMod.LOGGER.warn("[aibuild] failed to prune snapshot build-{}", seq, e);
            }
        }
    }

    private static Meta readMeta(Path dir, int seq) throws IOException {
        JsonObject o = JsonParser.parseString(Files.readString(dir.resolve(metaName(seq)))).getAsJsonObject();
        var min = o.getAsJsonArray("min");
        var max = o.getAsJsonArray("max");
        return new Meta(
                o.get("seq").getAsInt(),
                min.get(0).getAsInt(), min.get(1).getAsInt(), min.get(2).getAsInt(),
                max.get(0).getAsInt(), max.get(1).getAsInt(), max.get(2).getAsInt(),
                o.has("description") ? o.get("description").getAsString() : "",
                o.has("time") ? o.get("time").getAsString() : "",
                o.has("session") && !o.get("session").isJsonNull() ? o.get("session").getAsString() : null);
    }

    private static JsonObject toJson(Meta m) {
        JsonObject o = new JsonObject();
        o.addProperty("seq", m.seq());
        var min = new com.google.gson.JsonArray();
        min.add(m.minX());
        min.add(m.minY());
        min.add(m.minZ());
        o.add("min", min);
        var max = new com.google.gson.JsonArray();
        max.add(m.maxX());
        max.add(m.maxY());
        max.add(m.maxZ());
        o.add("max", max);
        o.addProperty("description", m.description());
        o.addProperty("time", m.timestamp());
        o.addProperty("volume", m.volume());
        if (m.session() != null) {
            o.addProperty("session", m.session());
        }
        return o;
    }
}
