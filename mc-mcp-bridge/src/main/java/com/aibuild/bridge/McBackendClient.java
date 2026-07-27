package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

/**
 * HTTP client for the aibuild mod backend, per docs/specs/bridge-http-api.md.
 * Every request carries the X-Aibuild-Token header.
 */
public final class McBackendClient {

    /** Result of an HTTP call: status code, Content-Type header (may be null), raw body. */
    public record Response(int status, String contentType, byte[] body) {
        public boolean isSuccess() {
            return status >= 200 && status < 300;
        }
    }

    private final BridgeConfig config;
    private final HttpClient client;
    private final ObjectMapper mapper = new ObjectMapper();

    public McBackendClient(BridgeConfig config) {
        this.config = config;
        this.client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofMillis(config.httpTimeoutMs()))
                .build();
    }

    public String baseUrl() {
        return config.baseUrl();
    }

    public Response postJson(String path, JsonNode body) throws IOException, InterruptedException {
        byte[] bytes = mapper.writeValueAsBytes(body);
        HttpRequest request = baseRequest(URI.create(config.baseUrl() + path))
                .POST(HttpRequest.BodyPublishers.ofByteArray(bytes))
                .header("Content-Type", "application/json")
                .build();
        return send(request);
    }

    public Response get(String pathWithQuery) throws IOException, InterruptedException {
        HttpRequest request = baseRequest(URI.create(config.baseUrl() + pathWithQuery))
                .GET()
                .build();
        return send(request);
    }

    private HttpRequest.Builder baseRequest(URI uri) {
        return HttpRequest.newBuilder(uri)
                .timeout(Duration.ofMillis(config.httpTimeoutMs()))
                .header("X-Aibuild-Token", config.token())
                .header("Accept-Charset", StandardCharsets.UTF_8.name());
    }

    private Response send(HttpRequest request) throws IOException, InterruptedException {
        HttpResponse<byte[]> response = client.send(request, HttpResponse.BodyHandlers.ofByteArray());
        String contentType = response.headers().firstValue("Content-Type").orElse(null);
        return new Response(response.statusCode(), contentType, response.body());
    }
}
