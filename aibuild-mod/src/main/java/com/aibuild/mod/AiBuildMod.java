package com.aibuild.mod;

import com.aibuild.mod.agent.AgentCommands;
import com.aibuild.mod.agent.AgentRunner;
import com.aibuild.mod.bridge.BridgeHttpServer;
import com.aibuild.mod.bridge.PlayerInbox;
import com.aibuild.mod.bridge.SiteGate;
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
        PlayerInbox inbox = new PlayerInbox();
        SiteGate gate = new SiteGate();
        SelectionManager selectionManager = new SelectionManager();
        BridgeHttpServer bridge = new BridgeHttpServer(jobManager, inbox, gate);
        AgentRunner agentRunner = new AgentRunner(config, inbox, bridge, gate, jobManager);

        ModItems.register();
        SelectionEvents.register(selectionManager);

        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) ->
                new AgentCommands(agentRunner, selectionManager, gate, jobManager).register(dispatcher));

        ServerTickEvents.END_SERVER_TICK.register(server -> jobManager.tick(server));
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) ->
                agentRunner.onPlayerJoin(handler.getPlayer()));

        ServerLifecycleEvents.SERVER_STARTED.register(server -> {
            selectionManager.onServerStarted(server);
            try {
                bridge.start(server, FabricLoader.getInstance().getGameDir());
                agentRunner.onServerStarted(server);
            } catch (Exception e) {
                LOGGER.error("[aibuild] failed to start bridge http server", e);
            }
        });
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
            agentRunner.onServerStopping();
            selectionManager.onServerStopping();
            bridge.stop();
        });
    }
}
