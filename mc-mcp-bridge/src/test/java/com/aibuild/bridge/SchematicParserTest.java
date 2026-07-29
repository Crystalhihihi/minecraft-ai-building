package com.aibuild.bridge;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** SchematicParser: v2/v3 layouts, varint codec, coordinate order, palette handling, bad input. */
class SchematicParserTest {

    private static Map<String, Integer> palette(Object... pairs) {
        Map<String, Integer> palette = new LinkedHashMap<>();
        for (int i = 0; i < pairs.length; i += 2) {
            palette.put((String) pairs[i], (Integer) pairs[i + 1]);
        }
        return palette;
    }

    @Test
    void parsesV2LayoutAndCoordinateOrder() throws Exception {
        // 3x2x2: distinctive index 2 at (x=1, y=1, z=0) -> flat index 1 + 0*3 + 1*3*2 = 7
        int[] indices = new int[12];
        indices[7] = 2;
        indices[0] = 1;
        byte[] schem = SchemFixtures.schematic(2, 3, 2, 2, new int[]{10, 60, -5},
                palette("minecraft:air", 0, "minecraft:stone", 1, "minecraft:oak_stairs[facing=north]", 2),
                indices, 0);
        SchematicParser.Schematic parsed = SchematicParser.parse(schem);
        assertEquals(2, parsed.version());
        assertEquals(3700, parsed.dataVersion());
        assertEquals(3, parsed.width());
        assertEquals(2, parsed.height());
        assertEquals(2, parsed.length());
        assertArrayEquals(new int[]{10, 60, -5}, parsed.offset());
        assertEquals(1, parsed.indexAt(0, 0, 0));
        assertEquals(2, parsed.indexAt(1, 1, 0), "flat order must be x + z*Width + y*Width*Length");
        assertEquals(0, parsed.indexAt(2, 1, 1));
        assertEquals("minecraft:oak_stairs[facing=north]", parsed.paletteByIndex()[2]);
        assertEquals(0, parsed.blockEntityCount());
    }

    @Test
    void parsesV3LayoutFromBlocksSubCompound() throws Exception {
        int[] indices = new int[12];
        indices[7] = 2;
        byte[] schem = SchemFixtures.schematic(3, 3, 2, 2, new int[]{0, 64, 0},
                palette("minecraft:air", 0, "minecraft:stone", 1, "minecraft:glass", 2),
                indices, 2);
        SchematicParser.Schematic parsed = SchematicParser.parse(schem);
        assertEquals(3, parsed.version());
        assertEquals(3, parsed.width());
        assertEquals(2, parsed.indexAt(1, 1, 0));
        assertEquals("minecraft:glass", parsed.paletteByIndex()[2]);
        assertEquals(2, parsed.blockEntityCount(), "block entities are counted, not decoded");
    }

    @Test
    void varIntCodecRoundTripsMultiByteValues() throws Exception {
        int[] values = {0, 1, 127, 128, 300, 16384, 2_097_151};
        assertArrayEquals(values, SchematicParser.decodeVarInts(SchemFixtures.varInts(values),
                values.length));
    }

    @Test
    void varIntDecoderRejectsTruncatedData() {
        byte[] truncated = {(byte) 0x80}; // continuation bit set, then EOF
        IOException e = assertThrows(IOException.class,
                () -> SchematicParser.decodeVarInts(truncated, 1));
        assertTrue(e.getMessage().contains("truncated"), e.getMessage());
    }

    @Test
    void varIntDecoderRejectsTooFewIndices() {
        IOException e = assertThrows(IOException.class,
                () -> SchematicParser.decodeVarInts(SchemFixtures.varInts(new int[]{1, 2}), 3));
        assertTrue(e.getMessage().contains("expected 3"), e.getMessage());
    }

    @Test
    void paletteKeysGetMinecraftPrefixWhenMissing() throws Exception {
        byte[] schem = SchemFixtures.schematic(2, 1, 1, 1, null,
                palette("stone", 0), new int[]{0}, 0);
        SchematicParser.Schematic parsed = SchematicParser.parse(schem);
        assertEquals("minecraft:stone", parsed.paletteByIndex()[0]);
    }

    @Test
    void missingOffsetDefaultsToZero() throws Exception {
        byte[] schem = SchemFixtures.schematic(2, 1, 1, 1, null,
                palette("minecraft:stone", 0), new int[]{0}, 0);
        assertArrayEquals(new int[]{0, 0, 0}, SchematicParser.parse(schem).offset());
    }

    @Test
    void unsupportedVersionRejected() throws Exception {
        byte[] schem = SchemFixtures.schematic(5, 1, 1, 1, null,
                palette("minecraft:stone", 0), new int[]{0}, 0);
        IOException e = assertThrows(IOException.class, () -> SchematicParser.parse(schem));
        assertTrue(e.getMessage().contains("Version 5"), e.getMessage());
    }

    @Test
    void garbageBytesRejected() {
        assertThrows(IOException.class, () -> SchematicParser.parse(new byte[]{1, 2, 3, 4}));
        assertThrows(IOException.class, () -> SchematicParser.parse(new byte[0]));
    }
}
