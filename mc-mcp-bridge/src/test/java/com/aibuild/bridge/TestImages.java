package com.aibuild.bridge;

import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.UncheckedIOException;

import javax.imageio.ImageIO;

/** Generates real PNG bytes for render tests / the mock backend. */
final class TestImages {

    private TestImages() {
    }

    /** A 64x64 PNG with a deterministic pattern (red/blue diagonal). */
    static byte[] png64() {
        BufferedImage image = new BufferedImage(64, 64, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = image.createGraphics();
        try {
            for (int y = 0; y < 64; y++) {
                for (int x = 0; x < 64; x++) {
                    image.setRGB(x, y, (x - y + 64) % 8 < 4 ? 0xCC0000 : 0x0000CC);
                }
            }
        } finally {
            g.dispose();
        }
        try {
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            ImageIO.write(image, "png", baos);
            return baos.toByteArray();
        } catch (java.io.IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
