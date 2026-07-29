package com.aibuild.bridge;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.List;
import java.util.Map;
import java.util.zip.GZIPInputStream;

/**
 * Read-only Sponge Schematic (.schem) v2/v3 parser on top of {@link NbtReader}.
 *
 * v2 layout: root compound holds Version=2, Width/Height/Length (shorts), Offset (int[3],
 * optional), Palette (compound: block-state string -> int index), BlockData (byte array of
 * varint-encoded palette indices). v3 layout: root compound holds Version=3, Width/Height/Length,
 * Offset, and a Blocks sub-compound with Palette/Data/BlockEntities.
 *
 * Palette indices are stored in x + z*Width + y*Width*Length order (x fastest, y slowest).
 * Block entities are counted but not decoded.
 */
final class SchematicParser {

    /** Refuse absurd dimensions from corrupt files (64M blocks max). */
    private static final long MAX_VOLUME = 64L * 1024 * 1024;

    private SchematicParser() {
    }

    record Schematic(int version, int dataVersion, int width, int height, int length,
                     int[] offset, String[] paletteByIndex, int[] indices, int blockEntityCount) {

        int indexAt(int x, int y, int z) {
            return indices[x + z * width + y * width * length];
        }
    }

    static Schematic parse(byte[] fileBytes) throws IOException {
        Map<String, Object> root = readNbt(fileBytes);
        int version = asInt(root.get("Version"), -1);
        Map<String, Object> blocks;
        String dataKey;
        if (version == 2) {
            blocks = root;
            dataKey = "BlockData";
        } else if (version == 3) {
            blocks = asCompound(root.get("Blocks"), "Blocks");
            dataKey = "Data";
        } else {
            throw new IOException("unsupported schematic Version " + version + " (only v2 and v3)");
        }
        int width = dimension(root.get("Width"), "Width");
        int height = dimension(root.get("Height"), "Height");
        int length = dimension(root.get("Length"), "Length");
        long volume = (long) width * height * length;
        if (volume > MAX_VOLUME) {
            throw new IOException("schematic too large: " + width + "x" + height + "x" + length);
        }
        int[] offset = root.get("Offset") instanceof int[] o && o.length == 3 ? o : new int[3];
        String[] palette = invertPalette(asCompound(blocks.get("Palette"), "Palette"));
        if (!(blocks.get(dataKey) instanceof byte[] data)) {
            throw new IOException(dataKey + " byte array missing or wrong type");
        }
        int[] indices = decodeVarInts(data, (int) volume);
        int blockEntities = blocks.get("BlockEntities") instanceof List<?> list ? list.size() : 0;
        return new Schematic(version, asInt(root.get("DataVersion"), 0),
                width, height, length, offset, palette, indices, blockEntities);
    }

    private static Map<String, Object> readNbt(byte[] fileBytes) throws IOException {
        boolean gzipped = fileBytes.length >= 2
                && (fileBytes[0] & 0xFF) == 0x1F && (fileBytes[1] & 0xFF) == 0x8B;
        InputStream in = new ByteArrayInputStream(fileBytes);
        if (gzipped) {
            in = new GZIPInputStream(in);
        }
        return NbtReader.readRoot(in);
    }

    /** Invert the palette compound to index -> block-state string; adds a "minecraft:" prefix if missing. */
    private static String[] invertPalette(Map<String, Object> paletteCompound) throws IOException {
        if (paletteCompound.isEmpty()) {
            throw new IOException("Palette is empty");
        }
        int max = -1;
        for (Map.Entry<String, Object> e : paletteCompound.entrySet()) {
            int idx = asInt(e.getValue(), -1);
            if (idx < 0) {
                throw new IOException("palette entry \"" + e.getKey() + "\" has no integer index");
            }
            max = Math.max(max, idx);
        }
        String[] byIndex = new String[max + 1];
        for (Map.Entry<String, Object> e : paletteCompound.entrySet()) {
            String name = e.getKey();
            byIndex[asInt(e.getValue(), -1)] = name.contains(":") ? name : "minecraft:" + name;
        }
        return byIndex;
    }

    /** LEB128 varints (7 bits per byte, high bit = continuation), non-negative. Extra bytes are ignored. */
    static int[] decodeVarInts(byte[] data, int expected) throws IOException {
        int[] out = new int[expected];
        int pos = 0;
        int count = 0;
        while (pos < data.length && count < expected) {
            int value = 0;
            int shift = 0;
            while (true) {
                if (pos >= data.length) {
                    throw new IOException("truncated varint in block data");
                }
                int b = data[pos++] & 0xFF;
                value |= (b & 0x7F) << shift;
                if ((b & 0x80) == 0) {
                    break;
                }
                shift += 7;
                if (shift > 28) {
                    throw new IOException("varint longer than 5 bytes in block data");
                }
            }
            out[count++] = value;
        }
        if (count < expected) {
            throw new IOException("block data holds " + count + " indices, expected " + expected);
        }
        return out;
    }

    private static int dimension(Object value, String name) throws IOException {
        int d = asInt(value, 0);
        if (d <= 0) {
            throw new IOException(name + " missing or not a positive number");
        }
        return d;
    }

    private static int asInt(Object value, int fallback) {
        if (value instanceof Integer i) {
            return i;
        }
        if (value instanceof Short s) {
            return s;
        }
        if (value instanceof Byte b) {
            return b;
        }
        return fallback;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asCompound(Object value, String name) throws IOException {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        throw new IOException(name + " compound missing or wrong type");
    }
}
