package com.aibuild.bridge;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.zip.GZIPOutputStream;

/**
 * Builds real gzip-NBT Sponge .schem v2/v3 byte streams in code, for parser/placer tests
 * and for manual smoke fixtures (no community schematic files - see Phase 5.5 plan).
 *
 * Usage: java ... SchemFixtures &lt;out.schem&gt; - writes a small v2 stone-brick shell.
 */
final class SchemFixtures {

    private SchemFixtures() {
    }

    public static void main(String[] args) throws IOException {
        if (args.length != 1) {
            System.err.println("usage: SchemFixtures <out.schem>");
            System.exit(2);
        }
        Map<String, Integer> palette = new LinkedHashMap<>();
        palette.put("minecraft:air", 0);
        palette.put("minecraft:stone_bricks", 1);
        int w = 4;
        int h = 3;
        int l = 4;
        int[] indices = new int[w * h * l];
        for (int y = 0; y < h; y++) {
            for (int z = 0; z < l; z++) {
                for (int x = 0; x < w; x++) {
                    boolean wall = y == 0 || y == h - 1 || x == 0 || x == w - 1 || z == 0 || z == l - 1;
                    indices[x + z * w + y * w * l] = wall ? 1 : 0;
                }
            }
        }
        byte[] schem = schematic(2, w, h, l, new int[]{0, 64, 0}, palette, indices, 0);
        Files.write(Path.of(args[0]), schem);
        System.out.println("wrote " + args[0] + " (" + schem.length + " bytes, v2, 44 stone_bricks + 4 air)");
    }

    /**
     * Serialize a schematic to gzip NBT. {@code indices} are palette indices in
     * x + z*width + y*width*length order; they are varint-encoded into BlockData (v2) / Data (v3).
     * {@code offset} may be null (tag omitted). Each block entity is written as a stub
     * compound with Id/Pos.
     */
    static byte[] schematic(int version, int width, int height, int length, int[] offset,
                            Map<String, Integer> palette, int[] indices, int blockEntities)
            throws IOException {
        ByteArrayOutputStream raw = new ByteArrayOutputStream();
        DataOutputStream out = new DataOutputStream(raw);
        out.writeByte(10);           // root compound
        out.writeUTF("Schematic");   // root name
        writeInt(out, "Version", version);
        writeInt(out, "DataVersion", 3700);
        writeShort(out, "Width", width);
        writeShort(out, "Height", height);
        writeShort(out, "Length", length);
        if (offset != null) {
            writeIntArray(out, "Offset", offset);
        }
        if (version == 3) {
            out.writeByte(10);       // Blocks compound
            out.writeUTF("Blocks");
        }
        writePalette(out, palette);
        writeByteArray(out, version == 3 ? "Data" : "BlockData", varInts(indices));
        writeBlockEntities(out, blockEntities);
        if (version == 3) {
            out.writeByte(0);        // end Blocks
        }
        out.writeByte(0);            // end root
        out.flush();

        ByteArrayOutputStream gzipped = new ByteArrayOutputStream();
        try (GZIPOutputStream gz = new GZIPOutputStream(gzipped)) {
            gz.write(raw.toByteArray());
        }
        return gzipped.toByteArray();
    }

    /** LEB128 varints: 7 bits per byte, high bit = continuation. Inverse of SchematicParser#decodeVarInts. */
    static byte[] varInts(int[] values) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        for (int value : values) {
            int v = value;
            while ((v & ~0x7F) != 0) {
                out.write((v & 0x7F) | 0x80);
                v >>>= 7;
            }
            out.write(v);
        }
        return out.toByteArray();
    }

    private static void writePalette(DataOutputStream out, Map<String, Integer> palette)
            throws IOException {
        out.writeByte(10);
        out.writeUTF("Palette");
        for (Map.Entry<String, Integer> entry : palette.entrySet()) {
            writeInt(out, entry.getKey(), entry.getValue());
        }
        out.writeByte(0);
    }

    private static void writeBlockEntities(DataOutputStream out, int count) throws IOException {
        out.writeByte(9);            // list
        out.writeUTF("BlockEntities");
        out.writeByte(10);           // of compounds
        out.writeInt(count);
        for (int i = 0; i < count; i++) {
            writeString(out, "Id", "minecraft:chest");
            writeIntArray(out, "Pos", new int[]{0, 0, 0});
            out.writeByte(0);
        }
    }

    private static void writeInt(DataOutputStream out, String name, int value) throws IOException {
        out.writeByte(3);
        out.writeUTF(name);
        out.writeInt(value);
    }

    private static void writeShort(DataOutputStream out, String name, int value) throws IOException {
        out.writeByte(2);
        out.writeUTF(name);
        out.writeShort(value);
    }

    private static void writeString(DataOutputStream out, String name, String value)
            throws IOException {
        out.writeByte(8);
        out.writeUTF(name);
        out.writeUTF(value);
    }

    private static void writeByteArray(DataOutputStream out, String name, byte[] value)
            throws IOException {
        out.writeByte(7);
        out.writeUTF(name);
        out.writeInt(value.length);
        out.write(value);
    }

    private static void writeIntArray(DataOutputStream out, String name, int[] value)
            throws IOException {
        out.writeByte(11);
        out.writeUTF(name);
        out.writeInt(value.length);
        for (int v : value) {
            out.writeInt(v);
        }
    }
}
