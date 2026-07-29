package com.aibuild.bridge;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Standalone mock of the aibuild mod HTTP backend (all endpoints from
 * docs/specs/bridge-http-api.md with canned responses). For manual smoke tests
 * of the real bridge against a real agent CLI.
 *
 * Usage: java -cp <classes> com.aibuild.bridge.MockMcBackend --port <int> [--token <string>]
 */
public final class MockMcBackend {

    private MockMcBackend() {
    }

    public static void main(String[] args) throws IOException {
        int port = 0;
        String token = null;
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--port" -> port = Integer.parseInt(args[++i]);
                case "--token" -> token = args[++i];
                default -> {
                    System.err.println("usage: MockMcBackend --port <int> [--token <string>]");
                    System.exit(2);
                    return;
                }
            }
        }
        final String expectedToken = token;
        AtomicInteger jobCounter = new AtomicInteger(0);
        // job_id -> entry count, so job_status can report real placed/failed numbers
        java.util.Map<String, Integer> jobs = new java.util.concurrent.ConcurrentHashMap<>();

        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        server.createContext("/", exchange -> {
            try {
                if (expectedToken != null && !expectedToken.equals(
                        exchange.getRequestHeaders().getFirst("X-Aibuild-Token"))) {
                    respond(exchange, 403, "application/json", "{\"error\":\"forbidden\"}");
                    return;
                }
                String path = exchange.getRequestURI().getPath();
                String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
                System.out.println("[mock-backend] " + exchange.getRequestMethod() + " "
                        + exchange.getRequestURI() + " " + body);
                switch (path) {
                    case "/tools/fill", "/tools/set_block" ->
                            respond(exchange, 200, "application/json",
                                    "{\"job_id\":\"mock-" + jobCounter.incrementAndGet() + "\"}");
                    case "/tools/set_blocks" -> {
                        // crude entry count: number of "\"block\"" keys
                        int entries = body.split("\"block\"", -1).length - 1;
                        if (entries > 4096) {
                            respond(exchange, 400, "application/json",
                                    "{\"error\":\"too many entries: " + entries + " (max 4096)\"}");
                        } else {
                            String id = "mock-" + jobCounter.incrementAndGet();
                            jobs.put(id, entries);
                            respond(exchange, 200, "application/json", "{\"job_id\":\"" + id + "\"}");
                        }
                    }
                    case "/tools/job_status" -> {
                        String id = queryParam(exchange.getRequestURI().getRawQuery(), "id");
                        int total = jobs.getOrDefault(id, 100);
                        respond(exchange, 200, "application/json",
                                "{\"job_id\":\"" + id + "\",\"state\":\"done\",\"total\":" + total
                                        + ",\"placed\":" + total + ",\"failed\":0,\"errors\":[]}");
                    }
                    case "/tools/search_blocks" ->
                            respond(exchange, 200, "application/json",
                                    "{\"matches\":[\"minecraft:white_stained_glass\","
                                            + "\"minecraft:black_stained_glass\","
                                            + "\"minecraft:glass\"]}");
                    case "/tools/get_block" ->
                            respond(exchange, 200, "application/json",
                                    "{\"block\":\"minecraft:oak_stairs\",\"properties\":"
                                            + "{\"facing\":\"north\",\"half\":\"bottom\"}}");
                    case "/tools/get_region_summary" ->
                            respond(exchange, 200, "application/json",
                                    "{\"text\":\"方块统计: minecraft:stone x512, minecraft:air x1024\\n"
                                            + "第64层 ASCII 平面图:\\n#####\\n#####\\n#####\"}");
                    case "/tools/get_terrain_summary" ->
                            respond(exchange, 200, "application/json",
                                    "{\"text\":\"高度图(中心 0,0 半径 64): 平均高度 64, 坡度平缓, 无水体\\n"
                                            + "  6 6 6 7 7\\n  6 6 6 7 7\\n平坦度: 适合建造\"}");
                    case "/tools/render_region" ->
                            respond(exchange, 200, "image/png", TestImages.png64());
                    case "/tools/propose_site" ->
                            respond(exchange, 200, "application/json",
                                    "{\"status\":\"pending_confirmation\",\"message\":\"等待玩家确认\"}");
                    default ->
                            respond(exchange, 404, "application/json",
                                    "{\"error\":\"unknown endpoint: " + path + "\"}");
                }
            } catch (Exception e) {
                respond(exchange, 500, "application/json",
                        "{\"error\":\"mock backend failure: " + e.getMessage() + "\"}");
            } finally {
                exchange.close();
            }
        });
        server.start();
        System.out.println("[mock-backend] listening on http://127.0.0.1:"
                + server.getAddress().getPort() + (expectedToken != null ? " (token required)" : ""));
    }

    private static void respond(HttpExchange exchange, int status, String contentType, String body)
            throws IOException {
        respond(exchange, status, contentType, body.getBytes(StandardCharsets.UTF_8));
    }

    private static void respond(HttpExchange exchange, int status, String contentType, byte[] body)
            throws IOException {
        exchange.getResponseHeaders().set("Content-Type", contentType);
        exchange.sendResponseHeaders(status, body.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(body);
        }
    }

    private static String queryParam(String rawQuery, String key) {
        if (rawQuery == null) {
            return "";
        }
        for (String pair : rawQuery.split("&")) {
            int eq = pair.indexOf('=');
            if (eq > 0 && pair.substring(0, eq).equals(key)) {
                return java.net.URLDecoder.decode(pair.substring(eq + 1), StandardCharsets.UTF_8);
            }
        }
        return "";
    }
}
