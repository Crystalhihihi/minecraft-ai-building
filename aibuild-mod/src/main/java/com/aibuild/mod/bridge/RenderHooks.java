package com.aibuild.mod.bridge;

import net.minecraft.core.BlockPos;

import java.util.concurrent.CompletableFuture;

/**
 * Indirection between the (common) bridge HTTP server and the client-only GL
 * region renderer. The common source set must not reference client classes
 * (they do not exist on a dedicated server), so the client source set
 * registers its renderer here during client init and the render_region
 * endpoint looks it up at request time.
 */
public final class RenderHooks {

    /**
     * Renders a region of the client world to PNG bytes. Implementations run
     * on the client (render) thread and complete asynchronously; the returned
     * future may complete exceptionally when the region is not available on
     * the client (e.g. chunks not loaded) — callers are expected to fall back
     * to the server-side top-down renderer.
     */
    @FunctionalInterface
    public interface GlRegionRenderer {
        CompletableFuture<byte[]> renderPng(BlockPos min, BlockPos max, float azimuth, float elevation,
                                            boolean orthographic);
    }

    private static volatile GlRegionRenderer glRenderer;

    private RenderHooks() {
    }

    /** Called once from client init; null on a dedicated server. */
    public static void setGlRenderer(GlRegionRenderer renderer) {
        glRenderer = renderer;
    }

    public static GlRegionRenderer glRenderer() {
        return glRenderer;
    }
}
