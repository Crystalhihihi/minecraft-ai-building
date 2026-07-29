package com.aibuild.mod.bridge;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Generates the get_region_summary text: non-air block counts (top N) plus a
 * per-layer ASCII plan of the region. Runs on the server main thread (may
 * synchronously load chunks inside the region).
 *
 * The whole region is read once into a {@link Block} array (volume is capped
 * at {@link SiteGate#MAX_VOLUME} = 64^3 by the endpoint, so ~2 MB of
 * references) and both the statistics and the layer plans are derived from
 * that snapshot.
 *
 * Output budget (~200 lines, to stay cheap on tokens):
 * - header + stats: ~20 lines (top 12 block types + "others")
 * - layer plans: at most {@value #MAX_LAYERS} sampled Y layers (evenly spaced,
 *   always including top and bottom), each downsampled to at most
 *   {@value #MAX_PLAN_ROWS} rows x {@value #MAX_PLAN_COLS} columns; each cell
 *   shows the dominant non-air block inside it, using the legend chars.
 */
public final class RegionSummary {
    private static final int MAX_TOP_BLOCKS = 12;
    private static final int MAX_LAYERS = 8;
    private static final int MAX_PLAN_ROWS = 20;
    private static final int MAX_PLAN_COLS = 60;
    /** Legend chars in frequency order (most frequent block gets the first). */
    private static final String LEGEND_CHARS = "#=.oO%@*;:~^$&?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    private static final char OTHER_CHAR = '+';
    private static final char AIR_CHAR = ' ';

    private RegionSummary() {
    }

    public static String generate(ServerLevel level, BlockPos min, BlockPos max) {
        int sx = max.getX() - min.getX() + 1;
        int sy = max.getY() - min.getY() + 1;
        int sz = max.getZ() - min.getZ() + 1;

        // Snapshot the whole region once.
        Block[] blocks = new Block[sx * sy * sz];
        Map<Block, Integer> counts = new HashMap<>();
        int nonAir = 0;
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
        for (int y = 0; y < sy; y++) {
            for (int z = 0; z < sz; z++) {
                for (int x = 0; x < sx; x++) {
                    pos.set(min.getX() + x, min.getY() + y, min.getZ() + z);
                    BlockState state = level.getBlockState(pos);
                    Block block = state.getBlock();
                    blocks[(y * sz + z) * sx + x] = block;
                    if (!state.isAir()) {
                        counts.merge(block, 1, Integer::sum);
                        nonAir++;
                    } else {
                        blocks[(y * sz + z) * sx + x] = Blocks.AIR; // collapse cave/void air
                    }
                }
            }
        }

        // Frequency-sorted block list (ties broken by id for stable output).
        List<Map.Entry<Block, Integer>> sorted = new ArrayList<>(counts.entrySet());
        sorted.sort(Comparator.<Map.Entry<Block, Integer>>comparingInt(e -> -e.getValue())
                .thenComparing(e -> blockId(e.getKey())));

        // Legend: top blocks get distinct chars, everything else is OTHER_CHAR.
        Map<Block, Character> legend = new LinkedHashMap<>();
        for (int i = 0; i < sorted.size() && i < LEGEND_CHARS.length(); i++) {
            legend.put(sorted.get(i).getKey(), LEGEND_CHARS.charAt(i));
        }

        StringBuilder out = new StringBuilder();
        out.append("Region [").append(min.toShortString()).append("] .. [").append(max.toShortString()).append("]")
                .append(" size ").append(sx).append('x').append(sy).append('x').append(sz)
                .append(" (volume ").append((long) sx * sy * sz).append(')').append('\n');
        out.append("Non-air blocks: ").append(nonAir).append("; air: ")
                .append((long) sx * sy * sz - nonAir).append('\n');
        out.append("Block counts (top ").append(Math.min(MAX_TOP_BLOCKS, sorted.size())).append(" of ")
                .append(sorted.size()).append(" types):\n");
        long others = 0;
        for (int i = 0; i < sorted.size(); i++) {
            if (i < MAX_TOP_BLOCKS) {
                out.append("  ").append(blockId(sorted.get(i).getKey())).append(' ').append(sorted.get(i).getValue())
                        .append('\n');
            } else {
                others += sorted.get(i).getValue();
            }
        }
        if (others > 0) {
            out.append("  (others: ").append(sorted.size() - MAX_TOP_BLOCKS).append(" types) ").append(others)
                    .append('\n');
        }

        // Sampled layers: evenly spaced, always including min and max Y.
        List<Integer> layers = sampledLayers(sy);
        int zStride = Math.max(1, (int) Math.ceil((double) sz / MAX_PLAN_ROWS));
        int xStride = Math.max(1, (int) Math.ceil((double) sx / MAX_PLAN_COLS));
        int rows = (sz + zStride - 1) / zStride;
        int cols = (sx + xStride - 1) / xStride;

        out.append("Layer plans: ").append(layers.size()).append(" sampled layer(s)");
        if (zStride > 1 || xStride > 1) {
            out.append(", downsampled ").append(xStride).append('x').append(zStride).append(" blocks/cell");
        }
        out.append("; row 0 = north (-z), col 0 = west (-x); '").append(AIR_CHAR == ' ' ? " " : AIR_CHAR)
                .append("' = air, '").append(OTHER_CHAR).append("' = other blocks\n");
        out.append("Legend:");
        for (Map.Entry<Block, Character> e : legend.entrySet()) {
            out.append(' ').append(e.getValue()).append('=').append(shortId(e.getKey()));
        }
        out.append('\n');

        for (int layerY : layers) {
            out.append("y=").append(min.getY() + layerY).append(":\n");
            for (int r = 0; r < rows; r++) {
                StringBuilder row = new StringBuilder(cols);
                for (int c = 0; c < cols; c++) {
                    row.append(cellChar(blocks, sx, sz, layerY, c * xStride, r * zStride, xStride, zStride, legend));
                }
                // Trim trailing air to keep lines short; keep at least one char.
                int end = row.length();
                while (end > 1 && row.charAt(end - 1) == AIR_CHAR) {
                    end--;
                }
                out.append(row, 0, end).append('\n');
            }
        }
        return out.toString();
    }

    /** Evenly spaced layer offsets in [0, sy), at most MAX_LAYERS, always including 0 and sy-1. */
    private static List<Integer> sampledLayers(int sy) {
        List<Integer> layers = new ArrayList<>();
        if (sy <= MAX_LAYERS) {
            for (int y = 0; y < sy; y++) {
                layers.add(y);
            }
            return layers;
        }
        for (int k = 0; k < MAX_LAYERS; k++) {
            int y = (int) Math.round(k * (sy - 1) / (double) (MAX_LAYERS - 1));
            if (layers.isEmpty() || layers.get(layers.size() - 1) != y) {
                layers.add(y);
            }
        }
        return layers;
    }

    /** Dominant non-air block char inside one downsampled cell of a layer. */
    private static char cellChar(Block[] blocks, int sx, int sz, int layerY, int x0, int z0, int xStride, int zStride,
                                 Map<Block, Character> legend) {
        Map<Block, Integer> cellCounts = new HashMap<>();
        int bestCount = 0;
        Block best = null;
        for (int dz = 0; dz < zStride && z0 + dz < sz; dz++) {
            for (int dx = 0; dx < xStride && x0 + dx < sx; dx++) {
                Block block = blocks[(layerY * sz + z0 + dz) * sx + x0 + dx];
                if (block == Blocks.AIR) {
                    continue;
                }
                int n = cellCounts.merge(block, 1, Integer::sum);
                if (n > bestCount) {
                    bestCount = n;
                    best = block;
                }
            }
        }
        if (best == null) {
            return AIR_CHAR;
        }
        Character ch = legend.get(best);
        return ch != null ? ch : OTHER_CHAR;
    }

    private static String blockId(Block block) {
        return BuiltInRegistries.BLOCK.getKey(block).toString();
    }

    private static String shortId(Block block) {
        String id = blockId(block);
        return id.startsWith("minecraft:") ? id.substring("minecraft:".length()) : id;
    }
}
