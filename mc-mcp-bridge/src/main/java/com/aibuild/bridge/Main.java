package com.aibuild.bridge;

import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;

/**
 * Entry point. Usage:
 *   java -jar mc-mcp-bridge-all.jar --port <int> --token <string> [--base-url <url>] [--http-timeout-ms <n>]
 *
 * stdout is reserved for protocol messages; everything else goes to stderr.
 */
public final class Main {

    public static void main(String[] args) {
        BridgeConfig config;
        try {
            config = BridgeConfig.parse(args);
        } catch (IllegalArgumentException e) {
            System.err.println("[mc-mcp-bridge] " + e.getMessage());
            System.err.println("usage: java -jar mc-mcp-bridge-all.jar --port <int> --token <string>"
                    + " [--base-url <url>] [--http-timeout-ms <n>]");
            System.exit(2);
            return;
        }

        PrintWriter err = new PrintWriter(System.err, true, StandardCharsets.UTF_8);
        err.println("[mc-mcp-bridge] ready, backend=" + config.baseUrl()
                + " http-timeout=" + config.httpTimeoutMs() + "ms");

        McBackendClient backend = new McBackendClient(config);
        McpServer server = new McpServer(new ToolDispatcher(backend), err);
        try {
            server.serve(System.in, System.out);
        } catch (Exception e) {
            err.println("[mc-mcp-bridge] fatal: " + e);
            System.exit(1);
            return;
        }
        err.println("[mc-mcp-bridge] stdin closed, exiting");
    }
}
