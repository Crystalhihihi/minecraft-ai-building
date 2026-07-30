package com.aibuild.mod;

import com.aibuild.mod.agent.AgentCommands;
import com.aibuild.mod.agent.AgentSessionManager;
import com.aibuild.mod.bridge.BridgeHttpServer;
import com.aibuild.mod.config.AgentConfig;
import com.aibuild.mod.job.JobManager;
import com.aibuild.mod.selection.ModItems;
import com.aibuild.mod.selection.SelectionEvents;
import com.aibuild.mod.selection.SelectionManager;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.loader.api.FabricLoader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AiBuildMod implements ModInitializer {
    public static final String MOD_ID = "aibuild";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    @Override
    public void onInitialize() {
        AgentConfig config = AgentConfig.load(FabricLoader.getInstance().getGameDir());
        JobManager jobManager = new JobManager(config);
        AgentSessionManager sessionManager = new AgentSessionManager(config, jobManager);
        BridgeHttpServer bridge = new BridgeHttpServer(jobManager, sessionManager);
        sessionManager.attachBridge(bridge);
        SelectionManager selectionManager = new SelectionManager();

        ModItems.register();
        SelectionEvents.register(selectionManager);

        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) ->
                new AgentCommands(sessionManager, selectionManager, jobManager).register(dispatcher));

        ServerTickEvents.END_SERVER_TICK.register(server -> jobManager.tick(server));
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) ->
                sessionManager.onPlayerJoin(handler.getPlayer()));

        ServerLifecycleEvents.SERVER_STARTED.register(server -> {
            selectionManager.onServerStarted(server);
            try {
                bridge.start(server, FabricLoader.getInstance().getGameDir());
                sessionManager.onServerStarted(server);
            } catch (Exception e) {
                LOGGER.error("[aibuild] failed to start bridge http server", e);
            }
        });
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
            sessionManager.onServerStopping();
            selectionManager.onServerStopping();
            bridge.stop();
        });
    }
}
