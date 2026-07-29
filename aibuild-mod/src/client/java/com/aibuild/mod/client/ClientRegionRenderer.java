package com.aibuild.mod.client;

import com.aibuild.mod.AiBuildMod;
import com.aibuild.mod.bridge.RenderHooks;
import com.mojang.blaze3d.buffers.GpuBuffer;
import com.mojang.blaze3d.buffers.GpuBufferSlice;
import com.mojang.blaze3d.buffers.Std140Builder;
import com.mojang.blaze3d.pipeline.RenderPipeline;
import com.mojang.blaze3d.pipeline.TextureTarget;
import com.mojang.blaze3d.systems.CommandEncoder;
import com.mojang.blaze3d.systems.RenderPass;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.textures.FilterMode;
import com.mojang.blaze3d.vertex.BufferBuilder;
import com.mojang.blaze3d.vertex.ByteBufferBuilder;
import com.mojang.blaze3d.vertex.MeshData;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexFormat;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.DynamicUniforms;
import net.minecraft.client.renderer.GlobalSettingsUniform;
import net.minecraft.client.renderer.ItemBlockRenderTypes;
import net.minecraft.client.renderer.PerspectiveProjectionMatrixBuffer;
import net.minecraft.client.renderer.block.BlockRenderDispatcher;
import net.minecraft.client.renderer.block.model.BlockModelPart;
import net.minecraft.client.renderer.chunk.ChunkSectionLayer;
import net.minecraft.client.renderer.texture.AbstractTexture;
import net.minecraft.client.renderer.texture.TextureAtlas;
import net.minecraft.client.server.IntegratedServer;
import net.minecraft.core.BlockPos;
import net.minecraft.network.protocol.game.ClientboundLevelChunkWithLightPacket;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.RandomSource;
import net.minecraft.util.Util;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.material.FluidState;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import org.lwjgl.system.MemoryStack;

import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.OptionalDouble;
import java.util.OptionalInt;
import java.util.concurrent.CompletableFuture;

/**
 * Client-side GL region renderer backing render_region (mode=gl). Ported to
 * the 1.21.11 rendering API following the Isometric Renders pattern
 * (https://github.com/gliscowo/isometric-renders, MIT — bake the region into
 * vertex buffers, draw offscreen with a custom projection, read pixels back).
 * worldmesher is not used: its latest build (0.4.7+1.21.4) predates the 1.21.5
 * render-pipeline rewrite, so the bake is done directly against the vanilla
 * calls worldmesher wraps ({@code BlockRenderDispatcher#renderBatched}, same
 * idiom as {@code SectionCompiler}).
 *
 * Threading model (same shape as vanilla chunk meshing — compile off-thread,
 * upload on the render thread — so an AI render request does not stall the
 * game; phase timings are logged per render):
 * 1. [client/render thread, END_CLIENT_TICK] wait until every chunk of the
 *    region is loaded (missing chunks are re-pushed by the integrated server;
 *    give up after {@value #MAX_WAIT_TICKS} ticks), then capture a
 *    {@link SnapshotRegion} (block states + light + biomes + shades) — the
 *    only phase that touches the live world; the capture is sliced across
 *    ticks ({@value #CAPTURE_POSITIONS_PER_TICK} positions per tick, a few ms)
 *    so even a 64^3 region never blocks a frame
 * 2. [background worker, {@code Util.backgroundExecutor()}] bake every non-air
 *    block/liquid of the snapshot into per-{@link ChunkSectionLayer}
 *    {@link BufferBuilder}s (pure CPU, off-heap buffers, same as
 *    {@code SectionCompiler} workers); hands the built {@link MeshData}s back
 *    via {@code Minecraft#execute}
 * 3. [client/render thread] upload meshes to GPU buffers and draw them into
 *    an offscreen {@link TextureTarget} through the vanilla terrain pipelines
 *    ({@code ChunkSectionLayer#pipeline()}), exactly like
 *    {@code ChunkSectionsToRender#renderGroup}: Sampler0 = block atlas,
 *    Sampler2 = lightmap, a "ChunkSection" UBO carrying the (rotation-only)
 *    view matrix + region origin, and a swapped-in Globals UBO with the
 *    virtual camera position. Camera: look-at around the region center from
 *    azimuth/elevation at distance 1.5x region diagonal, perspective (default)
 *    or orthographic projection. All encoder operations (buffer uploads,
 *    uniform ring writes) happen BEFORE {@code createRenderPass} — they are
 *    illegal while a pass records
 * 4. read pixels back with {@code Screenshot.takeScreenshot} (async GPU copy;
 *    the consumer fires on a later frame on this thread and completes the
 *    request's future — joining here would deadlock) and encode PNG.
 *
 * Notes verified against 1.21.11:
 * - {@code ItemBlockRenderTypes#getRenderType} returns the moving-block
 *   rendertypes (entity vertex format) — NOT usable for static region baking;
 *   the terrain pipelines via {@code ItemBlockRenderTypes#getChunkRenderType}
 *   are the correct target (BLOCK vertex format).
 * - terrain.vsh computes pos = Position + (ChunkPosition - CameraBlockPos)
 *   + CameraOffset, so the Globals UBO's camera must be the virtual camera;
 *   it is swapped in before the draw and restored afterwards.
 * - Vertex buffers are created with {@code GpuDevice#createBuffer} directly:
 *   {@code VertexFormat#uploadImmediateVertexBuffer} returns a shared
 *   per-format slot (later uploads invalidate earlier ones, closing it
 *   poisons subsequent renders).
 *
 * Limitations: block entities without a baked model (chests, signs...) are not
 * rendered; translucent geometry is not depth-sorted per view; fog/sky values
 * come from the player's current environment.
 */
public final class ClientRegionRenderer {
    private static final int IMAGE_SIZE = 768;
    private static final float FOV_Y = (float) Math.toRadians(50.0);
    private static final int MAX_WAIT_TICKS = 40; // ~2 s for chunks+light to arrive
    private static final int BUFFER_INITIAL_SIZE = 1 << 20;
    /**
     * Snapshot positions copied per client tick (~6 ms at the measured
     * ~0.4 µs/position): bounds the per-frame cost of the capture phase; a
     * full 64^3 halo region takes ~17 ticks (~0.3 s) of added latency.
     */
    private static final int CAPTURE_POSITIONS_PER_TICK = 16384;
    /** Vanilla draw order: opaque layers first, translucent last (blend correctness). */
    private static final List<ChunkSectionLayer> DRAW_ORDER =
            List.of(ChunkSectionLayer.SOLID, ChunkSectionLayer.CUTOUT, ChunkSectionLayer.TRIPWIRE,
                    ChunkSectionLayer.TRANSLUCENT);

    private record Pending(BlockPos min, BlockPos max, float azimuth, float elevation, boolean orthographic,
                           CompletableFuture<byte[]> future, int ticksLeft) {
    }

    /** One baked layer: the mesh plus the builder that owns its off-heap memory (freed in that order). */
    private record LayerMesh(ChunkSectionLayer layer, MeshData mesh, ByteBufferBuilder byteBuffer) {
    }

    private record BakedRegion(List<LayerMesh> layers, int nonAirBlocks) {
        void close() {
            for (LayerMesh layer : layers) {
                layer.mesh().close();
            }
            for (LayerMesh layer : layers) {
                layer.byteBuffer().close();
            }
        }
    }

    private static final Deque<Pending> PENDING = new ArrayDeque<>();
    private static TextureTarget target;
    // Incremental snapshot capture state for the current PENDING head.
    private static SnapshotRegion activeSnapshot;
    private static int captureOffset;
    private static long captureNanos;

    private ClientRegionRenderer() {
    }

    public static void init() {
        RenderHooks.setGlRenderer(ClientRegionRenderer::requestRender);
        ClientTickEvents.END_CLIENT_TICK.register(ClientRegionRenderer::tick);
    }

    private static CompletableFuture<byte[]> requestRender(BlockPos min, BlockPos max, float azimuth,
                                                           float elevation, boolean orthographic) {
        CompletableFuture<byte[]> future = new CompletableFuture<>();
        PENDING.addLast(new Pending(min, max, azimuth, elevation, orthographic, future, MAX_WAIT_TICKS));
        return future;
    }

    private static void tick(Minecraft mc) {
        Pending pending = PENDING.peekFirst();
        if (pending == null) {
            return;
        }
        ClientLevel level = mc.level;
        if (level == null) {
            fail(new IllegalStateException("no client level (not in a world)"));
            return;
        }
        if (!allChunksLoaded(level, pending.min(), pending.max())) {
            if (pending.ticksLeft() <= 0) {
                fail(new IllegalStateException("region chunks not loaded on the client"));
                return;
            }
            if (pending.ticksLeft() == MAX_WAIT_TICKS || pending.ticksLeft() == MAX_WAIT_TICKS / 2) {
                pushChunks(mc, pending.min(), pending.max());
            }
            PENDING.pollFirst();
            PENDING.addLast(new Pending(pending.min(), pending.max(), pending.azimuth(), pending.elevation(),
                    pending.orthographic(), pending.future(), pending.ticksLeft() - 1));
            return;
        }
        // Chunks ready: capture the snapshot incrementally, one slice per
        // tick, then hand the bake to the background pool.
        try {
            if (activeSnapshot == null) {
                activeSnapshot = SnapshotRegion.create(level, pending.min(), pending.max());
                captureOffset = 0;
                captureNanos = 0;
            }
            long sliceStart = System.nanoTime();
            int end = Math.min(activeSnapshot.size(), captureOffset + CAPTURE_POSITIONS_PER_TICK);
            activeSnapshot.captureSlice(level, captureOffset, end);
            captureNanos += System.nanoTime() - sliceStart;
            captureOffset = end;
            if (captureOffset < activeSnapshot.size()) {
                return; // continue next tick
            }
        } catch (Throwable t) {
            activeSnapshot = null;
            failCapture(t);
            return;
        }
        SnapshotRegion snapshot = activeSnapshot;
        long snapshotNanos = captureNanos;
        activeSnapshot = null;
        PENDING.pollFirst();
        dispatch(mc, pending, snapshot, snapshotNanos);
    }

    private static void failCapture(Throwable t) {
        Pending pending = PENDING.pollFirst();
        if (pending != null) {
            pending.future().completeExceptionally(t);
        }
    }

    private static void fail(Exception e) {
        activeSnapshot = null; // drop any half-captured snapshot of the failed head
        Pending pending = PENDING.pollFirst();
        if (pending != null) {
            pending.future().completeExceptionally(e);
        }
    }

    private static boolean allChunksLoaded(ClientLevel level, BlockPos min, BlockPos max) {
        for (int cx = min.getX() >> 4; cx <= max.getX() >> 4; cx++) {
            for (int cz = min.getZ() >> 4; cz <= max.getZ() >> 4; cz++) {
                ChunkAccess chunk = level.getChunk(cx, cz, ChunkStatus.FULL, false);
                if (chunk == null) {
                    return false;
                }
            }
        }
        return true;
    }

    /** Asks the integrated server to (re)send the region's chunks to all local players. */
    private static void pushChunks(Minecraft mc, BlockPos min, BlockPos max) {
        IntegratedServer server = mc.getSingleplayerServer();
        if (server == null) {
            return;
        }
        server.execute(() -> {
            ServerLevel serverLevel = server.overworld();
            List<ServerPlayer> players = server.getPlayerList().getPlayers();
            if (players.isEmpty()) {
                return;
            }
            for (int cx = min.getX() >> 4; cx <= max.getX() >> 4; cx++) {
                for (int cz = min.getZ() >> 4; cz <= max.getZ() >> 4; cz++) {
                    LevelChunk chunk = serverLevel.getChunk(cx, cz);
                    ClientboundLevelChunkWithLightPacket packet =
                            new ClientboundLevelChunkWithLightPacket(chunk, serverLevel.getLightEngine(), null, null);
                    for (ServerPlayer player : players) {
                        player.connection.send(packet);
                    }
                }
            }
        });
    }

    // ------------------------------------------------------------------ stage 1→2: snapshot + background bake

    /**
     * [render thread] Hands the bake of a completed snapshot to the
     * background pool. The heavy part (meshing tens of thousands of blocks)
     * runs off-thread; the render thread only did the (sliced) snapshot copy
     * and, later, the GPU upload+draw.
     */
    private static void dispatch(Minecraft mc, Pending req, SnapshotRegion snapshot, long snapshotNanos) {
        BlockRenderDispatcher dispatcher = mc.getBlockRenderer();
        Util.backgroundExecutor().execute(() -> {
            BakedRegion baked = null;
            try {
                long bakeStart = System.nanoTime();
                baked = bake(snapshot, dispatcher, req.min(), req.max());
                long bakeNanos = System.nanoTime() - bakeStart;
                AiBuildMod.LOGGER.info(
                        "[aibuild] render_region snapshot={}ms bake={}ms ({} non-air blocks, {}x{}x{})",
                        snapshotNanos / 1_000_000, bakeNanos / 1_000_000, baked.nonAirBlocks(),
                        req.max().getX() - req.min().getX() + 1, req.max().getY() - req.min().getY() + 1,
                        req.max().getZ() - req.min().getZ() + 1);
                BakedRegion done = baked;
                mc.execute(() -> {
                    try {
                        drawAndReadback(mc, req, done);
                    } catch (Throwable t) {
                        done.close();
                        req.future().completeExceptionally(t);
                    }
                });
            } catch (Throwable t) {
                if (baked != null) {
                    baked.close();
                }
                req.future().completeExceptionally(t);
            }
        });
    }

    /**
     * [background worker] Bakes the snapshot into per-layer meshes (BLOCK
     * vertex format, vertices relative to the region's min corner). Pure CPU
     * work on off-heap buffers — identical to what SectionCompiler workers do.
     */
    private static BakedRegion bake(SnapshotRegion region, BlockRenderDispatcher dispatcher, BlockPos min,
                                    BlockPos max) {
        Map<ChunkSectionLayer, BufferBuilder> builders = new EnumMap<>(ChunkSectionLayer.class);
        Map<ChunkSectionLayer, ByteBufferBuilder> byteBuffers = new EnumMap<>(ChunkSectionLayer.class);
        PoseStack pose = new PoseStack();
        RandomSource random = RandomSource.create();
        List<BlockModelPart> parts = new ArrayList<>();
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
        int nonAir = 0;
        List<LayerMesh> layers = new ArrayList<>();
        try {
            for (int y = min.getY(); y <= max.getY(); y++) {
                for (int z = min.getZ(); z <= max.getZ(); z++) {
                    for (int x = min.getX(); x <= max.getX(); x++) {
                        pos.set(x, y, z);
                        BlockState state = region.getBlockState(pos);
                        if (state.isAir()) {
                            continue;
                        }
                        nonAir++;
                        FluidState fluid = state.getFluidState();
                        if (!fluid.isEmpty()) {
                            dispatcher.renderLiquid(pos, region,
                                    builderFor(builders, byteBuffers, ItemBlockRenderTypes.getRenderLayer(fluid)),
                                    state, fluid);
                        }
                        parts.clear();
                        random.setSeed(state.getSeed(pos));
                        dispatcher.getBlockModel(state).collectParts(random, parts);
                        if (parts.isEmpty()) {
                            continue;
                        }
                        pose.pushPose();
                        pose.translate(x - min.getX(), y - min.getY(), z - min.getZ());
                        dispatcher.renderBatched(state, pos, region, pose,
                                builderFor(builders, byteBuffers, ItemBlockRenderTypes.getChunkRenderType(state)),
                                true, parts);
                        pose.popPose();
                    }
                }
            }
            for (ChunkSectionLayer layer : DRAW_ORDER) {
                BufferBuilder builder = builders.get(layer);
                if (builder == null) {
                    continue;
                }
                MeshData mesh = builder.build();
                if (mesh != null) {
                    layers.add(new LayerMesh(layer, mesh, byteBuffers.get(layer)));
                }
            }
            BakedRegion baked = new BakedRegion(layers, nonAir);
            // Layers not represented above (empty meshes) still own buffers.
            for (Map.Entry<ChunkSectionLayer, ByteBufferBuilder> entry : byteBuffers.entrySet()) {
                boolean held = false;
                for (LayerMesh layer : layers) {
                    if (layer.byteBuffer() == entry.getValue()) {
                        held = true;
                        break;
                    }
                }
                if (!held) {
                    entry.getValue().close();
                }
            }
            return baked;
        } catch (Throwable t) {
            for (LayerMesh layer : layers) {
                layer.mesh().close();
            }
            for (ByteBufferBuilder byteBuffer : byteBuffers.values()) {
                byteBuffer.close();
            }
            throw t;
        }
    }

    // ------------------------------------------------------------------ stage 3→4: upload, draw, readback

    /** [render thread] Uploads the baked meshes, draws offscreen, starts the async pixel readback. */
    private static void drawAndReadback(Minecraft mc, Pending req, BakedRegion baked) throws Exception {
        long start = System.nanoTime();
        BlockPos min = req.min();
        BlockPos max = req.max();
        try {
            // Camera: look-at around the region center, distance = 1.5x diagonal.
            double sx = max.getX() - min.getX() + 1;
            double sy = max.getY() - min.getY() + 1;
            double sz = max.getZ() - min.getZ() + 1;
            double diagonal = Math.sqrt(sx * sx + sy * sy + sz * sz);
            double distance = diagonal * 1.5;
            Vector3f center = new Vector3f((float) (sx / 2), (float) (sy / 2), (float) (sz / 2));
            double az = Math.toRadians(req.azimuth());
            double el = Math.toRadians(req.elevation());
            Vector3f eyeRel = new Vector3f(
                    (float) (center.x + distance * Math.cos(el) * Math.sin(az)),
                    (float) (center.y + distance * Math.sin(el)),
                    (float) (center.z + distance * Math.cos(el) * Math.cos(az)));
            Matrix4f view = new Matrix4f().setLookAt(eyeRel, center, new Vector3f(0, 1, 0));
            view.setTranslation(0, 0, 0); // rotation only; the shader applies translation via Globals
            float near = (float) Math.max(0.05, distance - diagonal);
            float far = (float) (distance + diagonal);
            Matrix4f projection = req.orthographic()
                    ? new Matrix4f().setOrtho((float) (-diagonal * 0.6), (float) (diagonal * 0.6),
                            (float) (-diagonal * 0.6), (float) (diagonal * 0.6), near, far)
                    : new Matrix4f().setPerspective(FOV_Y, 1.0f, near, far);

            if (target == null) {
                target = new TextureTarget("aibuild-region", IMAGE_SIZE, IMAGE_SIZE, true);
            }
            CommandEncoder encoder = RenderSystem.getDevice().createCommandEncoder();
            encoder.clearColorAndDepthTextures(target.getColorTexture(), 0, target.getDepthTexture(), 1.0);

            AbstractTexture atlas = mc.getTextureManager().getTexture(TextureAtlas.LOCATION_BLOCKS);
            RenderSystem.backupProjectionMatrix();
            GpuBuffer savedGlobals = RenderSystem.getGlobalSettingsUniform();
            try (PerspectiveProjectionMatrixBuffer projBuffer =
                         new PerspectiveProjectionMatrixBuffer("aibuild-region");
                 GpuBuffer globals = createGlobalsBuffer(min, eyeRel)) {
                RenderSystem.setProjectionMatrix(projBuffer.getBuffer(projection),
                        req.orthographic() ? com.mojang.blaze3d.ProjectionType.ORTHOGRAPHIC
                                : com.mojang.blaze3d.ProjectionType.PERSPECTIVE);
                RenderSystem.setGlobalSettingsUniform(globals);

                // Upload everything BEFORE opening the render pass: buffer
                // uploads and uniform ring writes are command-encoder
                // operations, which are illegal while a pass is recording.
                record LayerDraw(RenderPipeline pipeline, GpuBuffer vertexBuffer, int indexCount,
                                 GpuBufferSlice chunkSection) {
                }
                List<LayerDraw> draws = new ArrayList<>();
                int maxIndexCount = 0;
                for (LayerMesh layerMesh : baked.layers()) {
                    MeshData mesh = layerMesh.mesh();
                    RenderPipeline pipeline = layerMesh.layer().pipeline();
                    int indexCount = mesh.drawState().indexCount();
                    maxIndexCount = Math.max(maxIndexCount, indexCount);
                    // Own GpuBuffer per layer (shared immediate slot unsafe —
                    // see class javadoc).
                    GpuBuffer vertexBuffer = RenderSystem.getDevice().createBuffer(
                            () -> "aibuild region mesh", GpuBuffer.USAGE_VERTEX, mesh.vertexBuffer());
                    GpuBufferSlice[] chunkSection = RenderSystem.getDynamicUniforms().writeChunkSections(
                            new DynamicUniforms.ChunkSectionInfo(view, min.getX(), min.getY(), min.getZ(),
                                    1.0f, atlas.getTexture().getWidth(0), atlas.getTexture().getHeight(0)));
                    draws.add(new LayerDraw(pipeline, vertexBuffer, indexCount, chunkSection[0]));
                }
                // One sequential (quads) index buffer sized for the largest
                // layer — growing it later would invalidate earlier handles.
                RenderSystem.AutoStorageIndexBuffer sequential =
                        RenderSystem.getSequentialBuffer(VertexFormat.Mode.QUADS);
                GpuBuffer indexBuffer = draws.isEmpty() ? null : sequential.getBuffer(maxIndexCount);

                try (RenderPass pass = encoder.createRenderPass(() -> "aibuild region render",
                        target.getColorTextureView(), OptionalInt.empty(),
                        target.getDepthTextureView(), OptionalDouble.empty())) {
                    RenderSystem.bindDefaultUniforms(pass);
                    pass.bindTexture("Sampler2", mc.gameRenderer.lightTexture().getTextureView(),
                            RenderSystem.getSamplerCache().getClampToEdge(FilterMode.LINEAR));
                    for (LayerDraw draw : draws) {
                        pass.setPipeline(draw.pipeline());
                        pass.bindTexture("Sampler0", atlas.getTextureView(), atlas.getSampler());
                        pass.setUniform("ChunkSection", draw.chunkSection());
                        pass.setVertexBuffer(0, draw.vertexBuffer());
                        pass.setIndexBuffer(indexBuffer, sequential.type());
                        pass.drawIndexed(0, 0, draw.indexCount(), 1);
                    }
                } finally {
                    for (LayerDraw draw : draws) {
                        draw.vertexBuffer().close();
                    }
                }
            } finally {
                RenderSystem.setGlobalSettingsUniform(savedGlobals);
                RenderSystem.restoreProjectionMatrix();
            }
        } finally {
            baked.close();
        }
        AiBuildMod.LOGGER.info("[aibuild] render_region draw+upload={}ms (render thread)",
                (System.nanoTime() - start) / 1_000_000);

        // Read pixels back (async GPU copy; the consumer fires on a later
        // frame on this thread and completes the request's future).
        CompletableFuture<byte[]> future = req.future();
        Screenshot.takeScreenshot(target, 1, image -> {
            try {
                Path tmp = Files.createTempFile("aibuild-render", ".png");
                try {
                    image.writeToFile(tmp);
                    future.complete(Files.readAllBytes(tmp));
                } finally {
                    Files.deleteIfExists(tmp);
                }
                image.close();
            } catch (Exception e) {
                future.completeExceptionally(e);
            }
        });
    }

    private static BufferBuilder builderFor(Map<ChunkSectionLayer, BufferBuilder> builders,
                                            Map<ChunkSectionLayer, ByteBufferBuilder> byteBuffers,
                                            ChunkSectionLayer layer) {
        return builders.computeIfAbsent(layer, l -> {
            ByteBufferBuilder byteBuffer = new ByteBufferBuilder(BUFFER_INITIAL_SIZE);
            byteBuffers.put(l, byteBuffer);
            return new BufferBuilder(byteBuffer, l.pipeline().getVertexFormatMode(),
                    l.pipeline().getVertexFormat());
        });
    }

    /**
     * Builds a Globals UBO (layout: assets/minecraft/shaders/include/globals.glsl)
     * whose camera is the virtual render camera, in the terrain shader's
     * convention: pos = Position + (ChunkPosition - CameraBlockPos) + CameraOffset,
     * i.e. CameraBlockPos = floor(eye) and CameraOffset = floor(eye) - eye.
     */
    private static GpuBuffer createGlobalsBuffer(BlockPos regionMin, Vector3f eyeRel) {
        float eyeX = regionMin.getX() + eyeRel.x;
        float eyeY = regionMin.getY() + eyeRel.y;
        float eyeZ = regionMin.getZ() + eyeRel.z;
        int camBlockX = (int) Math.floor(eyeX);
        int camBlockY = (int) Math.floor(eyeY);
        int camBlockZ = (int) Math.floor(eyeZ);
        ByteBuffer data;
        try (MemoryStack stack = MemoryStack.stackPush()) {
            data = Std140Builder.onStack(stack, GlobalSettingsUniform.UBO_SIZE)
                    .putIVec3(camBlockX, camBlockY, camBlockZ)
                    .putVec3(camBlockX - eyeX, camBlockY - eyeY, camBlockZ - eyeZ)
                    .putVec2(IMAGE_SIZE, IMAGE_SIZE)
                    .putFloat(1.0f) // GlintAlpha
                    .putFloat(0.0f) // GameTime
                    .putInt(0)      // MenuBlurRadius
                    .putInt(0)      // UseRgss
                    .get();
            return RenderSystem.getDevice().createBuffer(() -> "aibuild region globals",
                    GpuBuffer.USAGE_UNIFORM, data);
        }
    }
}
