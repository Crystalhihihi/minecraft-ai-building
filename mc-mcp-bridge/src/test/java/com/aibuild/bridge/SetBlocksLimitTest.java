package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** set_blocks: the bridge itself rejects batches over 4096 entries without any HTTP call. */
class SetBlocksLimitTest {

    private MockBackend backend;
    private TestRig rig;

    @BeforeEach
    void setUp() throws Exception {
        backend = new MockBackend();
        backend.on("/tools/set_blocks", MockBackend.Canned.json("{\"job_id\":\"job-9\"}"));
        rig = new TestRig(backend.baseUrl());
    }

    @AfterEach
    void tearDown() {
        backend.close();
    }

    private static String argsWithBlocks(int count) {
        ObjectNode args = TestRig.MAPPER.createObjectNode();
        ArrayNode blocks = args.putArray("blocks");
        for (int i = 0; i < count; i++) {
            ObjectNode b = blocks.addObject();
            b.put("x", i % 64);
            b.put("y", 64);
            b.put("z", i / 64);
            b.put("block", "minecraft:stone");
        }
        return args.toString();
    }

    @Test
    void over4096RejectedLocallyWithoutHttp() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks", argsWithBlocks(4097)));
        JsonNode result = resp.get("result");
        assertTrue(result.get("isError").asBoolean());
        String text = result.get("content").get(0).get("text").asText();
        assertTrue(text.contains("4096"), text);
        assertTrue(text.contains("4097"), text);
        assertEquals(0, backend.requests().size(), "no HTTP request may be sent");
    }

    @Test
    void exactly4096IsSent() throws Exception {
        JsonNode resp = rig.call(TestRig.toolsCall(1, "set_blocks", argsWithBlocks(4096)));
        assertFalse(resp.get("result").get("isError").asBoolean());
        assertEquals(1, backend.requestsTo("/tools/set_blocks").size());
        JsonNode body = TestRig.MAPPER.readTree(backend.requests().get(0).body());
        assertEquals(4096, body.get("blocks").size());
    }
}
