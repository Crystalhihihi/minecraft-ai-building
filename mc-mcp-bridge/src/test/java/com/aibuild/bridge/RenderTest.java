package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Base64;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** render_region: PNG bytes from the mod become MCP image content (base64 round-trip). */
class RenderTest {

    private MockBackend backend;
    private TestRig rig;

    @BeforeEach
    void setUp() throws Exception {
        backend = new MockBackend();
        rig = new TestRig(backend.baseUrl());
    }

    @AfterEach
    void tearDown() {
        backend.close();
    }

    @Test
    void pngResponseBecomesImageContent() throws Exception {
        byte[] png = TestImages.png64();
        backend.on("/tools/render_region", MockBackend.Canned.png(png));
        JsonNode resp = rig.call(TestRig.toolsCall(1, "render_region",
                "{\"min\":[0,0,0],\"max\":[9,9,9]}"));
        JsonNode result = resp.get("result");
        assertFalse(result.get("isError").asBoolean());
        JsonNode content = result.get("content").get(0);
        assertEquals("image", content.get("type").asText());
        assertEquals("image/png", content.get("mimeType").asText());
        byte[] decoded = Base64.getDecoder().decode(content.get("data").asText());
        assertArrayEquals(png, decoded, "base64 must decode back to the exact PNG bytes");
    }

    @Test
    void renderHttpErrorIsTextErrorNotImage() throws Exception {
        backend.on("/tools/render_region", MockBackend.Canned.json(500, "{\"error\":\"render pipeline broken\"}"));
        JsonNode resp = rig.call(TestRig.toolsCall(1, "render_region",
                "{\"min\":[0,0,0],\"max\":[9,9,9]}"));
        JsonNode result = resp.get("result");
        assertTrue(result.get("isError").asBoolean());
        assertEquals("text", result.get("content").get(0).get("type").asText());
        assertTrue(result.get("content").get(0).get("text").asText().contains("render pipeline broken"));
    }
}
