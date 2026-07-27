package com.aibuild.bridge;

import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Function;

/**
 * Minimal mock of the aibuild mod HTTP backend for unit tests.
 * Binds 127.0.0.1 on a random port, records every request, replies per registered path.
 */
final class MockBackend implements AutoCloseable {

    record Request(String method, String path, String query, String token, String contentType, byte[] body) {
        String pathWithQuery() {
            return query == null ? path : path + "?" + query;
        }
    }

    record Canned(int status, String contentType, byte[] body) {
        static Canned json(String body) {
            return json(200, body);
        }

        static Canned json(int status, String body) {
            return new Canned(status, "application/json", body.getBytes(StandardCharsets.UTF_8));
        }

        static Canned png(byte[] bytes) {
            return new Canned(200, "image/png", bytes);
        }
    }

    private final HttpServer server;
    private final List<Request> requests = Collections.synchronizedList(new ArrayList<>());
    private final Map<String, Function<Request, Canned>> handlers = new ConcurrentHashMap<>();

    MockBackend() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            byte[] body = exchange.getRequestBody().readAllBytes();
            Request request = new Request(
                    exchange.getRequestMethod(),
                    exchange.getRequestURI().getPath(),
                    exchange.getRequestURI().getRawQuery(),
                    exchange.getRequestHeaders().getFirst("X-Aibuild-Token"),
                    exchange.getRequestHeaders().getFirst("Content-Type"),
                    body);
            requests.add(request);
            Function<Request, Canned> handler = handlers.get(request.path());
            Canned canned = handler != null
                    ? handler.apply(request)
                    : Canned.json(404, "{\"error\":\"no mock handler for " + request.path() + "\"}");
            exchange.getResponseHeaders().set("Content-Type", canned.contentType());
            exchange.sendResponseHeaders(canned.status(), canned.body().length);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(canned.body());
            }
        });
        server.start();
    }

    int port() {
        return server.getAddress().getPort();
    }

    String baseUrl() {
        return "http://127.0.0.1:" + port();
    }

    void on(String path, Function<Request, Canned> handler) {
        handlers.put(path, handler);
    }

    void on(String path, Canned canned) {
        handlers.put(path, request -> canned);
    }

    List<Request> requests() {
        return requests;
    }

    List<Request> requestsTo(String path) {
        synchronized (requests) {
            return requests.stream().filter(r -> r.path().equals(path)).toList();
        }
    }

    @Override
    public void close() {
        server.stop(0);
    }
}
