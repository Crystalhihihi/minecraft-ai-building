package com.aibuild.mod.bridge;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.MapColor;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;

/**
 * V1 fallback renderer: a top-down raster of the region, in the style of the
 * vanilla map item ({@code FilledMapItem#updateColors}). For each (x,z) column
 * the topmost non-air block inside the region's Y range determines the color
 * ({@link BlockState#getMapColor}); the brightness shade is derived from the
 * height difference against the north (-z) neighbor column, like vanilla maps
 * do (higher = HIGH, lower = LOW, level = NORMAL).
 *
 * Runs entirely server-side (no GL), so it works on dedicated servers and as
 * the fallback when the GL pipeline is unavailable or fails. Row 0 of the
 * image is -z (north up), column 0 is -x (west left). Empty columns are
 * transparent. Small images are upscaled (nearest neighbor) so the longest
 * side reaches {@value #MIN_OUTPUT_SIDE}px for legibility.
 *
 * Verified against 1.21.11 (mojmap): {@code BlockState#getMapColor(BlockGetter,
 * BlockPos)} and {@code MapColor#calculateARGBColor(MapColor.Brightness)}.
 */
public final class TopDownRenderer {
    private static final int MIN_OUTPUT_SIDE = 256;

    private TopDownRenderer() {
    }

    public static byte[] renderPng(ServerLevel level, BlockPos min, BlockPos max) throws IOException {
        int sx = max.getX() - min.getX() + 1;
        int sz = max.getZ() - min.getZ() + 1;

        // Top non-air y per column (Integer.MIN_VALUE = empty column).
        int[] topY = new int[sx * sz];
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
        for (int z = 0; z < sz; z++) {
            for (int x = 0; x < sx; x++) {
                int found = Integer.MIN_VALUE;
                for (int y = max.getY(); y >= min.getY(); y--) {
                    pos.set(min.getX() + x, y, min.getZ() + z);
                    if (!level.getBlockState(pos).isAir()) {
                        found = y;
                        break;
                    }
                }
                topY[z * sx + x] = found;
            }
        }

        BufferedImage image = new BufferedImage(sx, sz, BufferedImage.TYPE_INT_ARGB);
        for (int z = 0; z < sz; z++) {
            for (int x = 0; x < sx; x++) {
                int y = topY[z * sx + x];
                if (y == Integer.MIN_VALUE) {
                    continue; // transparent
                }
                int northY = z > 0 ? topY[(z - 1) * sx + x] : y;
                MapColor.Brightness brightness = y > northY
                        ? MapColor.Brightness.HIGH
                        : (y < northY ? MapColor.Brightness.LOW : MapColor.Brightness.NORMAL);
                pos.set(min.getX() + x, y, min.getZ() + z);
                BlockState state = level.getBlockState(pos);
                MapColor mapColor = state.getMapColor(level, pos);
                if (mapColor == MapColor.NONE) {
                    continue;
                }
                image.setRGB(x, z, mapColor.calculateARGBColor(brightness));
            }
        }

        BufferedImage output = upscale(image, sx, sz);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ImageIO.write(output, "png", out);
        return out.toByteArray();
    }

    /** Nearest-neighbor integer upscale so the longest side reaches MIN_OUTPUT_SIDE. */
    private static BufferedImage upscale(BufferedImage image, int sx, int sz) {
        int scale = Math.max(1, (int) Math.ceil((double) MIN_OUTPUT_SIDE / Math.max(sx, sz)));
        if (scale <= 1) {
            return image;
        }
        BufferedImage scaled = new BufferedImage(sx * scale, sz * scale, BufferedImage.TYPE_INT_ARGB);
        for (int z = 0; z < sz * scale; z++) {
            for (int x = 0; x < sx * scale; x++) {
                scaled.setRGB(x, z, image.getRGB(x / scale, z / scale));
            }
        }
        return scaled;
    }
}
