package com.aibuild.mod;

import com.aibuild.mod.agent.AgentCommands;
import com.aibuild.mod.agent.AgentRunner;
import com.aibuild.mod.bridge.BridgeHttpServer;
import com.aibuild.mod.bridge.PlayerInbox;
import com.aibuild.mod.config.AgentConfig;
import com.aibuild.mod.job.JobManager;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.loader.api.FabricLoader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AiBuildMod implements ModInitializer {
    public static final String MOD_ID = "aibuild";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    @Override
    public void onInitialize() {
        JobManager jobManager = new JobManager();
        PlayerInbox inbox = new PlayerInbox();
        BridgeHttpServer bridge = new BridgeHttpServer(jobManager, inbox);
        AgentConfig config = AgentConfig.load(FabricLoader.getInstance().getGameDir());
        AgentRunner agentRunner = new AgentRunner(config, inbox, bridge);

        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) ->
                new AgentCommands(agentRunner).register(dispatcher));

        ServerTickEvents.END_SERVER_TICK.register(server -> jobManager.tick(server));

        ServerLifecycleEvents.SERVER_STARTED.register(server -> {
            try {
                bridge.start(server, FabricLoader.getInstance().getGameDir());
                agentRunner.onServerStarted(server);
            } catch (Exception e) {
                LOGGER.error("[aibuild] failed to start bridge http server", e);
            }
        });
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
            agentRunner.onServerStopping();
            bridge.stop();
        });
    }
}
