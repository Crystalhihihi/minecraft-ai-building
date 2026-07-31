package com.aibuild.mod.bridge;

import com.aibuild.mod.agent.AgentSessionManager;
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
 * Site-selection analysis for the analyze_site tool. Splits the region into
 * 16x16 candidate tiles and computes, per tile: ground height mean/stddev
 * (same sampling logic as {@link TerrainSummary}), a cut/fill estimate (the
 * number of blocks to dig/fill to level the tile to its rounded mean height),
 * water share, tree count, and the intersection with the occupied map
 * (confirmed bounds of ALL sessions, any status). A tile CONFLICTS with an
 * occupied bounds when their 2D footprints overlap AND the occupied y-range
 * intersects [ground-5, ground+40] (the plausible build zone of the tile).
 *
 * Output (plain text, like get_terrain_summary): the region's occupied-area
 * list, then the top-5 conflict-free candidates ranked by flatness, then the
 * conflicted tiles for reference. Runs on the server main thread (may
 * synchronously load chunks inside the sampled area).
 */
public final class SiteAnalyzer {
    public static final int MAX_RADIUS = 96;
    private static final int TILE = 16;
    private static final int TOP_CANDIDATES = 5;
    private static final int MAX_CONFLICTED_LISTED = 8;
    /** 冲突判定的建筑 y 区间: 候选地面向下 5(地基/地下室) 、向上 40(塔楼/屋顶)。 */
    private static final int BUILD_BELOW = 5;
    private static final int BUILD_ABOVE = 40;
    /** 水面占比超过一半的候选不参与排名(纯水域),但仍计入切填方统计输出。 */
    private static final int MAX_WATER_PCT_RANKED = 50;

    private SiteAnalyzer() {
    }

    private record Candidate(int cx, int cz, double mean, double stddev, long cutFill, int waterPct, int trees,
                             List<Integer> conflicts) {
    }

    public static String generate(ServerLevel level, int centerX, int centerZ, int radius,
                                  List<AgentSessionManager.OccupiedSite> occupied) {
        int x0 = centerX - radius;
        int z0 = centerZ - radius;
        int tilesSide = (2 * radius) / TILE;

        StringBuilder sb = new StringBuilder();
        sb.append(String.format(Locale.ROOT,
                "site analysis center=(%d,%d) radius=%d tile=%dx%d%n", centerX, centerZ, radius, TILE, TILE));
        if (tilesSide == 0) {
            sb.append("area too small for 16x16 candidates (radius < 8)\n");
            appendOccupied(sb, occupied, x0, z0, x0 + 2 * radius - 1, z0 + 2 * radius - 1);
            return sb.toString();
        }
        int n = tilesSide * TILE; // sampled columns per side
        int[][] ground = new int[n][n]; // [row=z][col=x], top solid y (no leaves)
        boolean[][] water = new boolean[n][n];
        boolean[][] tree = new boolean[n][n];
        int lastCx = Integer.MIN_VALUE;
        int lastCz = Integer.MIN_VALUE;
        for (int r = 0; r < n; r++) {
            int z = z0 + r;
            for (int c = 0; c < n; c++) {
                int x = x0 + c;
                int cx = x >> 4;
                int cz = z >> 4;
                if (cx != lastCx || cz != lastCz) {
                    // getHeight 对未生成区块直接返回 minY(-64)而不会触发生成
                    // (与 TerrainSummary 相同的取样在野地里会得到假的 "-65 平地") —
                    // 先按 FULL 状态加载/生成该区块,再读高度图。
                    level.getChunk(cx, cz);
                    lastCx = cx;
                    lastCz = cz;
                }
                ground[r][c] = level.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x, z) - 1;
                int surfaceY = level.getHeight(Heightmap.Types.WORLD_SURFACE, x, z);
                BlockPos surfPos = new BlockPos(x, surfaceY - 1, z);
                if (!level.getFluidState(surfPos).isEmpty()) {
                    water[r][c] = true;
                } else {
                    BlockState surf = level.getBlockState(surfPos);
                    if (surf.is(BlockTags.LEAVES) || surf.is(BlockTags.LOGS)) {
                        tree[r][c] = true;
                    }
                }
            }
        }
        sb.append(String.format(Locale.ROOT, "sampled area x[%d..%d] z[%d..%d] (%dx%d tiles)%n",
                x0, x0 + n - 1, z0, z0 + n - 1, tilesSide, tilesSide));
        appendOccupied(sb, occupied, x0, z0, x0 + n - 1, z0 + n - 1);

        List<Candidate> ranked = new ArrayList<>();
        List<Candidate> conflicted = new ArrayList<>();
        int waterlogged = 0;
        for (int tr = 0; tr < tilesSide; tr++) {
            for (int tc = 0; tc < tilesSide; tc++) {
                double mean = 0;
                int waterCells = 0;
                int treeCells = 0;
                for (int r = tr * TILE; r < tr * TILE + TILE; r++) {
                    for (int c = tc * TILE; c < tc * TILE + TILE; c++) {
                        mean += ground[r][c];
                        if (water[r][c]) {
                            waterCells++;
                        }
                        if (tree[r][c]) {
                            treeCells++;
                        }
                    }
                }
                mean /= TILE * TILE;
                int target = (int) Math.round(mean); // 整平目标高度
                double variance = 0;
                long cutFill = 0;
                for (int r = tr * TILE; r < tr * TILE + TILE; r++) {
                    for (int c = tc * TILE; c < tc * TILE + TILE; c++) {
                        double d = ground[r][c] - mean;
                        variance += d * d;
                        cutFill += Math.abs(ground[r][c] - target);
                    }
                }
                variance /= TILE * TILE;

                int tileMinX = x0 + tc * TILE;
                int tileMinZ = z0 + tr * TILE;
                List<Integer> conflicts = new ArrayList<>();
                for (AgentSessionManager.OccupiedSite site : occupied) {
                    SiteGate.Bounds b = site.bounds();
                    boolean overlap2d = b.minX() <= tileMinX + TILE - 1 && b.maxX() >= tileMinX
                            && b.minZ() <= tileMinZ + TILE - 1 && b.maxZ() >= tileMinZ;
                    boolean overlapY = b.minY() <= target + BUILD_ABOVE && b.maxY() >= target - BUILD_BELOW;
                    if (overlap2d && overlapY) {
                        conflicts.add(site.sessionNo());
                    }
                }
                Candidate cand = new Candidate(tileMinX + TILE / 2, tileMinZ + TILE / 2, mean, Math.sqrt(variance),
                        cutFill, waterCells * 100 / (TILE * TILE), treeCells, conflicts);
                if (!conflicts.isEmpty()) {
                    conflicted.add(cand);
                } else if (cand.waterPct() > MAX_WATER_PCT_RANKED) {
                    waterlogged++;
                } else {
                    ranked.add(cand);
                }
            }
        }
        ranked.sort(Comparator.comparingDouble(Candidate::stddev)
                .thenComparingLong(Candidate::cutFill)
                .thenComparingInt(Candidate::waterPct));

        sb.append("candidates (16x16 tiles, conflict-free, flattest first; cut+fill = blocks to level to mean):\n");
        if (ranked.isEmpty()) {
            sb.append("  none (all tiles conflict with occupied bounds or are water)\n");
        } else {
            int rank = 1;
            for (Candidate cand : ranked) {
                if (rank > TOP_CANDIDATES) {
                    break;
                }
                sb.append(String.format(Locale.ROOT,
                        "  %d. center=(%d,%d) ground=%.1f stddev=%.2f cut+fill=%d water=%d%% trees=%d%n",
                        rank++, cand.cx(), cand.cz(), cand.mean(), cand.stddev(), cand.cutFill(),
                        cand.waterPct(), cand.trees()));
            }
        }
        if (waterlogged > 0) {
            sb.append(String.format(Locale.ROOT, "(%d tile(s) skipped: mostly water)%n", waterlogged));
        }
        if (!conflicted.isEmpty()) {
            sb.append("conflicted tiles (overlap occupied bounds, excluded from ranking):\n");
            conflicted.sort(Comparator.comparingInt(c -> c.conflicts().get(0)));
            int shown = 0;
            for (Candidate cand : conflicted) {
                if (++shown > MAX_CONFLICTED_LISTED) {
                    sb.append(String.format(Locale.ROOT, "  ... and %d more%n", conflicted.size() - MAX_CONFLICTED_LISTED));
                    break;
                }
                StringBuilder who = new StringBuilder();
                for (int i = 0; i < cand.conflicts().size(); i++) {
                    if (i > 0) {
                        who.append(", ");
                    }
                    who.append('#').append(cand.conflicts().get(i));
                }
                sb.append(String.format(Locale.ROOT,
                        "  tile center=(%d,%d) ground=%.1f conflicts with session %s (build zone y %d..%d)%n",
                        cand.cx(), cand.cz(), cand.mean(), who,
                        (int) Math.round(cand.mean()) - BUILD_BELOW, (int) Math.round(cand.mean()) + BUILD_ABOVE));
            }
        }
        return sb.toString();
    }

    /** 区域内(2D footprint 相交)的已占用 bounds 列表 — 选址时先知道哪里已经盖过。 */
    private static void appendOccupied(StringBuilder sb, List<AgentSessionManager.OccupiedSite> occupied,
                                       int minX, int minZ, int maxX, int maxZ) {
        List<AgentSessionManager.OccupiedSite> hits = new ArrayList<>();
        for (AgentSessionManager.OccupiedSite site : occupied) {
            SiteGate.Bounds b = site.bounds();
            if (b.minX() <= maxX && b.maxX() >= minX && b.minZ() <= maxZ && b.maxZ() >= minZ) {
                hits.add(site);
            }
        }
        if (hits.isEmpty()) {
            sb.append("occupied areas in region: none\n");
            return;
        }
        sb.append("occupied areas in region (confirmed bounds of past/current sessions, y range in brackets):\n");
        for (AgentSessionManager.OccupiedSite site : hits) {
            SiteGate.Bounds b = site.bounds();
            sb.append(String.format(Locale.ROOT, "  session #%d bounds [%d %d %d ~ %d %d %d] y %d..%d%n",
                    site.sessionNo(), b.minX(), b.minY(), b.minZ(), b.maxX(), b.maxY(), b.maxZ(), b.minY(), b.maxY()));
        }
    }
}
