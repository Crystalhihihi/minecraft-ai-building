package com.aibuild.mod.client;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Holder;
import net.minecraft.world.level.BlockAndTintGetter;
import net.minecraft.world.level.ColorResolver;
import net.minecraft.world.level.LightLayer;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.lighting.LevelLightEngine;
import net.minecraft.world.level.material.FluidState;
import org.jetbrains.annotations.Nullable;

import java.util.Arrays;

/**
 * Immutable snapshot of a world region (plus a 1-block halo, needed for
 * ambient occlusion, face culling and biome-tint sampling at the region
 * borders) used as the {@link BlockAndTintGetter} for off-thread mesh baking.
 * The GL renderer captures it on the client thread and the background bake
 * reads ONLY this copy — never the live world — so chunk updates/packet
 * arrivals during the bake cannot race it (unlike worldmesher, which
 * tolerates those races).
 *
 * Captured per position: BlockState, sky/block light (0-15), biome holder
 * (for {@link #getBlockTint} — grass/foliage/water colors). Also the 12
 * {@link #getShade} values (6 directions x shaded/unshaded) sampled from the
 * real level, and the level's Y bounds. Verified against 1.21.11: the block
 * render path ({@code ModelBlockRenderer}, {@code LiquidBlockRenderer}) only
 * calls getBlockState/getShade/getBrightness(via the static
 * {@code LevelRenderer.getLightColor} helper)/getBlockTint — never
 * {@link #getLightEngine} directly, which therefore returns null.
 */
final class SnapshotRegion implements BlockAndTintGetter {
    private final int minX, minY, minZ;   // halo-inclusive origin
    private final int sx, sy, sz;         // halo-inclusive size
    private final int levelMinY, levelHeight;
    private final BlockState[] states;
    private final byte[] skyLight;
    private final byte[] blockLight;
    private final Holder<Biome>[] biomes;
    private final float[][] shades; // [direction.ordinal()][shaded ? 1 : 0]
    private Holder<Biome> fallbackBiome;

    @SuppressWarnings("unchecked")
    private SnapshotRegion(int minX, int minY, int minZ, int sx, int sy, int sz, int levelMinY, int levelHeight,
                           int volume) {
        this.minX = minX;
        this.minY = minY;
        this.minZ = minZ;
        this.sx = sx;
        this.sy = sy;
        this.sz = sz;
        this.levelMinY = levelMinY;
        this.levelHeight = levelHeight;
        this.states = new BlockState[volume];
        this.skyLight = new byte[volume];
        this.blockLight = new byte[volume];
        this.biomes = new Holder[volume];
        this.shades = new float[6][2];
        Arrays.fill(states, Blocks.AIR.defaultBlockState());
    }

    /** Dimensions + level constants for an incremental capture. */
    static SnapshotRegion create(net.minecraft.client.multiplayer.ClientLevel level, BlockPos min, BlockPos max) {
        int levelMinY = level.getMinY();
        int levelMaxYInclusive = level.getMaxY() - 1;
        int hx0 = min.getX() - 1;
        int hy0 = Math.max(levelMinY, min.getY() - 1);
        int hz0 = min.getZ() - 1;
        int hx1 = max.getX() + 1;
        int hy1 = Math.min(levelMaxYInclusive, max.getY() + 1);
        int hz1 = max.getZ() + 1;
        int sx = hx1 - hx0 + 1;
        int sy = hy1 - hy0 + 1;
        int sz = hz1 - hz0 + 1;
        SnapshotRegion region = new SnapshotRegion(hx0, hy0, hz0, sx, sy, sz, levelMinY, level.getHeight(),
                sx * sy * sz);
        for (Direction direction : Direction.values()) {
            region.shades[direction.ordinal()][1] = level.getShade(direction, true);
            region.shades[direction.ordinal()][0] = level.getShade(direction, false);
        }
        region.fallbackBiome = level.getBiome(min);
        return region;
    }

    int size() {
        return states.length;
    }

    /**
     * Fills flat indices [startInclusive, endExclusive) — the capture is
     * sliced across client ticks so each tick only pays a few ms. MUST run on
     * the client thread. Biomes are sampled once per 4x4x4 quart cell (their
     * native resolution since 1.18) via a single-entry cache keyed by quart
     * coordinates.
     */
    void captureSlice(net.minecraft.client.multiplayer.ClientLevel level, int startInclusive, int endExclusive) {
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
        Holder<Biome> cachedBiome = null;
        int cachedQx = Integer.MIN_VALUE, cachedQy = 0, cachedQz = 0;
        for (int i = startInclusive; i < endExclusive; i++) {
            int x = i % sx;
            int z = (i / sx) % sz;
            int y = i / (sx * sz);
            pos.set(minX + x, minY + y, minZ + z);
            states[i] = level.getBlockState(pos);
            skyLight[i] = (byte) level.getBrightness(LightLayer.SKY, pos);
            blockLight[i] = (byte) level.getBrightness(LightLayer.BLOCK, pos);
            int qx = pos.getX() >> 2;
            int qy = pos.getY() >> 2;
            int qz = pos.getZ() >> 2;
            if (qx != cachedQx || qy != cachedQy || qz != cachedQz) {
                cachedQx = qx;
                cachedQy = qy;
                cachedQz = qz;
                cachedBiome = level.getBiome(pos);
            }
            biomes[i] = cachedBiome;
        }
    }

    private int index(int x, int y, int z) {
        return (y * sz + z) * sx + x;
    }

    /** Clamped index for any world position; returns -1 when outside the halo on Y beyond world bounds. */
    private int clampedIndex(BlockPos pos) {
        int x = pos.getX() - minX;
        int y = pos.getY() - minY;
        int z = pos.getZ() - minZ;
        if (y < 0 || y >= sy) {
            return -1;
        }
        x = Math.min(Math.max(x, 0), sx - 1);
        z = Math.min(Math.max(z, 0), sz - 1);
        return index(x, y, z);
    }

    @Override
    public BlockState getBlockState(BlockPos pos) {
        int i = clampedIndex(pos);
        return i >= 0 ? states[i] : Blocks.AIR.defaultBlockState();
    }

    @Override
    public FluidState getFluidState(BlockPos pos) {
        return getBlockState(pos).getFluidState();
    }

    @Override
    public @Nullable BlockEntity getBlockEntity(BlockPos pos) {
        return null; // block-entity rendering is not part of the mesh bake
    }

    @Override
    public int getBrightness(LightLayer layer, BlockPos pos) {
        int i = clampedIndex(pos);
        if (i < 0) {
            return layer == LightLayer.SKY ? 15 : 0;
        }
        return layer == LightLayer.SKY ? skyLight[i] : blockLight[i];
    }

    @Override
    public int getRawBrightness(BlockPos pos, int skyDecrease) {
        int i = clampedIndex(pos);
        if (i < 0) {
            return 15 - skyDecrease;
        }
        return Math.max(skyLight[i] - skyDecrease, blockLight[i]);
    }

    @Override
    public boolean canSeeSky(BlockPos pos) {
        int i = clampedIndex(pos);
        return i < 0 || skyLight[i] >= 15;
    }

    @Override
    public float getShade(Direction direction, boolean shaded) {
        return shades[direction.ordinal()][shaded ? 1 : 0];
    }

    @Override
    public LevelLightEngine getLightEngine() {
        // Never called by the block render path (see class javadoc); light is
        // served via the overridden getBrightness/getRawBrightness.
        return null;
    }

    @Override
    public int getBlockTint(BlockPos pos, ColorResolver resolver) {
        int i = clampedIndex(pos);
        Holder<Biome> biome = i >= 0 ? biomes[i] : fallbackBiome;
        return resolver.getColor(biome.value(), pos.getX(), pos.getZ());
    }

    @Override
    public int getMinY() {
        return levelMinY;
    }

    @Override
    public int getHeight() {
        return levelHeight;
    }
}
