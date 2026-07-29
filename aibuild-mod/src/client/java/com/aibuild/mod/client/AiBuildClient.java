package com.aibuild.mod.client;

import net.fabricmc.api.ClientModInitializer;

public class AiBuildClient implements ClientModInitializer {
    @Override
    public void onInitializeClient() {
        // GL region renderer backing render_region (mode=gl); registers itself
        // into RenderHooks so the common bridge server can find it.
        ClientRegionRenderer.init();
    }
}
