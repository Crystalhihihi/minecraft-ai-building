package com.aibuild.mod.bridge;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/**
 * Generates the compact terrain summary for get_terrain_summary and for the
 * terrain.json written before every agent spawn. Runs on the server main
 * thread (may synchronously load chunks inside the sampled area).
 *
 * Output (~80 lines): an ASCII heightmap (one char per cell: 0-9 = ground
 * height relative to the sampled min/max, {@code ~} water, {@code T} tree,
 * {@code #} at/above build height), height/water/flatness stats, and up to 3
 * suggested flat candidate areas with center coordinates.
 */
public final class TerrainSummary {
    public static final int MAX_RADIUS = 128;
    private static final int MAX_GRID = 64;
    private static final int CANDIDATE_TILE_BLOCKS = 16;

    private TerrainSummary() {
    }

    public static String generate(ServerLevel level, int centerX, int centerZ, int radius) {
        int step = Math.max(1, (int) Math.ceil(2.0 * radius / MAX_GRID));
        int n = (2 * radius) / step + 1; // cells per side
        int x0 = centerX - radius;
        int z0 = centerZ - radius;

        int[][] ground = new int[n][n]; // [row=z][col=x], top solid y (no leaves)
        boolean[][] water = new boolean[n][n];
        boolean[][] tree = new boolean[n][n];
        boolean[][] overTop = new boolean[n][n];
        int minY = Integer.MAX_VALUE;
        int maxY = Integer.MIN_VALUE;
        int waterCells = 0;
        int treeCells = 0;
        int lastCx = Integer.MIN_VALUE;
        int lastCz = Integer.MIN_VALUE;

        for (int r = 0; r < n; r++) {
            int z = z0 + r * step;
            for (int c = 0; c < n; c++) {
                int x = x0 + c * step;
                int cx = x >> 4;
                int cz = z >> 4;
                if (cx != lastCx || cz != lastCz) {
                    // getHeight 对未生成区块直接返回 minY(-64)而不会触发生成
                    // (野地里会得到假的 "-65 平地",2026-08-06 实测证实) —
                    // 先按 FULL 状态加载/生成该区块,再读高度图。同 SiteAnalyzer。
                    level.getChunk(cx, cz);
                    lastCx = cx;
                    lastCz = cz;
                }
                int gy = level.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x, z) - 1;
                ground[r][c] = gy;
                minY = Math.min(minY, gy);
                maxY = Math.max(maxY, gy);
                int surfaceY = level.getHeight(Heightmap.Types.WORLD_SURFACE, x, z);
                BlockPos surfPos = new BlockPos(x, surfaceY - 1, z);
                if (!level.getFluidState(surfPos).isEmpty()) {
                    water[r][c] = true;
                    waterCells++;
                } else {
                    BlockState surf = level.getBlockState(surfPos);
                    if (surf.is(BlockTags.LEAVES) || surf.is(BlockTags.LOGS)) {
                        tree[r][c] = true;
                        treeCells++;
                    }
                }
                if (gy >= level.getMaxY()) {
                    overTop[r][c] = true;
                }
            }
        }

        // height stats
        int cells = n * n;
        double mean = 0;
        for (int[] row : ground) {
            for (int y : row) {
                mean += y;
            }
        }
        mean /= cells;
        double variance = 0;
        for (int[] row : ground) {
            for (int y : row) {
                double d = y - mean;
                variance += d * d;
            }
        }
        variance /= cells;
        double stddev = Math.sqrt(variance);

        StringBuilder sb = new StringBuilder();
        sb.append(String.format(Locale.ROOT,
                "terrain summary center=(%d,%d) radius=%d step=%d ground-y range [%d..%d]%n",
                centerX, centerZ, radius, step, minY, maxY));
        sb.append(String.format(Locale.ROOT,
                "height mean=%.1f stddev=%.2f (%s); water %.0f%%; trees %.0f%%%n",
                mean, stddev, flatnessWord(stddev), waterCells * 100.0 / cells, treeCells * 100.0 / cells));
        sb.append("legend: 0-9 = ground height (0=min, 9=max of this map), ~ = water, T = tree, # = at/above build height\n");
        sb.append(String.format(Locale.ROOT,
                "map: row 0 = z=%d (north), col 0 = x=%d (west); 1 cell = %d block(s); axes +x east, +z south%n",
                z0, x0, step));

        int range = maxY - minY;
        for (int r = 0; r < n; r++) {
            for (int c = 0; c < n; c++) {
                if (water[r][c]) {
                    sb.append('~');
                } else if (overTop[r][c]) {
                    sb.append('#');
                } else if (tree[r][c]) {
                    sb.append('T');
                } else if (range == 0) {
                    sb.append('5'); // perfectly flat map: mid-band everywhere
                } else {
                    sb.append((char) ('0' + (ground[r][c] - minY) * 9 / range));
                }
            }
            sb.append('\n');
        }

        // flat candidates: 16-block tiles, ranked by internal height stddev
        int tile = Math.max(1, CANDIDATE_TILE_BLOCKS / step);
        record Candidate(int cx, int cz, int size, double stddev) {
        }
        List<Candidate> candidates = new ArrayList<>();
        for (int r0 = 0; r0 + tile <= n; r0 += tile) {
            for (int c0 = 0; c0 + tile <= n; c0 += tile) {
                double m = 0;
                int count = 0;
                int tileWater = 0;
                for (int r = r0; r < r0 + tile; r++) {
                    for (int c = c0; c < c0 + tile; c++) {
                        m += ground[r][c];
                        count++;
                        if (water[r][c]) {
                            tileWater++;
                        }
                    }
                }
                if (tileWater * 10 > count) {
                    continue; // mostly water — not a build candidate
                }
                m /= count;
                double v = 0;
                for (int r = r0; r < r0 + tile; r++) {
                    for (int c = c0; c < c0 + tile; c++) {
                        double d = ground[r][c] - m;
                        v += d * d;
                    }
                }
                v /= count;
                candidates.add(new Candidate(
                        x0 + (c0 + tile / 2) * step, z0 + (r0 + tile / 2) * step,
                        tile * step, Math.sqrt(v)));
            }
        }
        candidates.sort(Comparator.comparingDouble(Candidate::stddev));
        sb.append("flat candidates (16-block tiles, least height variation first):\n");
        if (candidates.isEmpty()) {
            sb.append("  none (area too small or mostly water)\n");
        } else {
            int rank = 1;
            for (Candidate cand : candidates) {
                if (rank > 3) {
                    break;
                }
                sb.append(String.format(Locale.ROOT, "  %d. center=(%d,%d) size=%dx%d stddev=%.2f%n",
                        rank++, cand.cx(), cand.cz(), cand.size(), cand.size(), cand.stddev()));
            }
        }
        return sb.toString();
    }

    private static String flatnessWord(double stddev) {
        if (stddev < 1.0) {
            return "flat";
        }
        if (stddev < 3.0) {
            return "gentle";
        }
        if (stddev < 6.0) {
            return "hilly";
        }
        return "mountainous";
    }
}
