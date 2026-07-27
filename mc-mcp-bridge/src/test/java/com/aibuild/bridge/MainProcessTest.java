package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** End-to-end smoke: the real Main process speaks protocol on stdout only. */
class MainProcessTest {

    private MockBackend backend;
    private Process process;

    @BeforeEach
    void setUp() throws Exception {
        backend = new MockBackend();
        backend.on("/tools/get_block", MockBackend.Canned.json("{\"block\":\"minecraft:stone\"}"));
    }

    @AfterEach
    void tearDown() {
        if (process != null) {
            process.destroyForcibly();
        }
        backend.close();
    }

    @Test
    void mainServesProtocolOverStdio() throws Exception {
        String javaBin = System.getProperty("java.home") + (System.getProperty("os.name").toLowerCase().contains("win")
                ? "\\bin\\java.exe" : "/bin/java");
        process = new ProcessBuilder(javaBin, "-cp", System.getProperty("java.class.path"),
                Main.class.getName(), "--port", String.valueOf(backend.port()), "--token", TestRig.TOKEN)
                .start();

        BufferedWriter stdin = new BufferedWriter(
                new OutputStreamWriter(process.getOutputStream(), StandardCharsets.UTF_8));
        BufferedReader stdout = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8));

        stdin.write("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\","
                + "\"params\":{\"protocolVersion\":\"2025-03-26\"}}");
        stdin.newLine();
        stdin.write(TestRig.toolsCall("s", "get_block", "{\"x\":1,\"y\":64,\"z\":1}"));
        stdin.newLine();
        stdin.flush();

        JsonNode init = TestRig.MAPPER.readTree(readLineWithTimeout(stdout));
        assertEquals("2025-03-26", init.get("result").get("protocolVersion").asText());

        JsonNode call = TestRig.MAPPER.readTree(readLineWithTimeout(stdout));
        assertEquals("s", call.get("id").asText());
        assertFalse(call.get("result").get("isError").asBoolean());
        assertEquals("{\"block\":\"minecraft:stone\"}",
                call.get("result").get("content").get(0).get("text").asText());

        stdin.close(); // EOF on stdin -> bridge should exit on its own
        boolean exited = process.waitFor(15, java.util.concurrent.TimeUnit.SECONDS);
        assertTrue(exited, "bridge must exit on stdin EOF");
        assertEquals(0, process.exitValue());
    }

    private static String readLineWithTimeout(BufferedReader reader) throws Exception {
        long deadline = System.nanoTime() + Duration.ofSeconds(15).toNanos();
        while (System.nanoTime() < deadline) {
            if (reader.ready()) {
                String line = reader.readLine();
                if (line != null) {
                    return line;
                }
            }
            Thread.sleep(20);
        }
        throw new AssertionError("timed out waiting for a protocol line on stdout");
    }
}
