package com.aibuild.bridge;

/** Command line configuration for the bridge. */
public record BridgeConfig(String baseUrl, String token, int httpTimeoutMs) {

    public static final int DEFAULT_HTTP_TIMEOUT_MS = 30_000;

    public static BridgeConfig parse(String[] args) {
        Integer port = null;
        String token = null;
        String baseUrl = null;
        int timeout = DEFAULT_HTTP_TIMEOUT_MS;
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--port" -> port = parseInt(requireValue(args, ++i, "--port"), "--port");
                case "--token" -> token = requireValue(args, ++i, "--token");
                case "--base-url" -> baseUrl = requireValue(args, ++i, "--base-url");
                case "--http-timeout-ms" -> timeout = parseInt(requireValue(args, ++i, "--http-timeout-ms"), "--http-timeout-ms");
                default -> throw new IllegalArgumentException("unknown argument: " + args[i]);
            }
        }
        if (baseUrl == null && port == null) {
            throw new IllegalArgumentException("--port is required");
        }
        if (token == null || token.isEmpty()) {
            throw new IllegalArgumentException("--token is required");
        }
        if (timeout <= 0) {
            throw new IllegalArgumentException("--http-timeout-ms must be positive");
        }
        if (baseUrl == null) {
            baseUrl = "http://127.0.0.1:" + port;
        }
        if (baseUrl.endsWith("/")) {
            baseUrl = baseUrl.substring(0, baseUrl.length() - 1);
        }
        return new BridgeConfig(baseUrl, token, timeout);
    }

    private static String requireValue(String[] args, int i, String flag) {
        if (i >= args.length) {
            throw new IllegalArgumentException(flag + " requires a value");
        }
        return args[i];
    }

    private static int parseInt(String value, String flag) {
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException(flag + " must be an integer, got: " + value);
        }
    }
}
