package com.aibuild.bridge;

import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Minimal read-only NBT parser (tag ids 0-12), just enough for Sponge .schem files.
 * No external dependencies. Values map to plain Java objects:
 * Byte, Short, Integer, Long, Float, Double, byte[], String,
 * List&lt;Object&gt; (list), Map&lt;String,Object&gt; (compound), int[], long[].
 * Corrupt input surfaces as IOException (EOFException included).
 */
final class NbtReader {

    /** Refuse single payloads larger than this to keep corrupt length prefixes from OOMing the JVM. */
    private static final int MAX_PAYLOAD_SIZE = 1 << 28;

    private NbtReader() {
    }

    /** Read the root tag; it must be a compound. The root name is ignored. */
    static Map<String, Object> readRoot(InputStream in) throws IOException {
        DataInputStream data = in instanceof DataInputStream d ? d : new DataInputStream(in);
        int type = data.readByte();
        if (type != 10) {
            throw new IOException("NBT root must be a compound (tag 10), got tag " + type);
        }
        data.readUTF(); // root name, ignored
        return readCompoundPayload(data);
    }

    private static Map<String, Object> readCompoundPayload(DataInputStream data) throws IOException {
        Map<String, Object> map = new LinkedHashMap<>();
        while (true) {
            int type = data.readByte(); // EOFException -> corrupt/truncated file
            if (type == 0) {
                return map;
            }
            String name = data.readUTF();
            map.put(name, readPayload(data, type));
        }
    }

    private static Object readPayload(DataInputStream data, int type) throws IOException {
        return switch (type) {
            case 1 -> data.readByte();
            case 2 -> data.readShort();
            case 3 -> data.readInt();
            case 4 -> data.readLong();
            case 5 -> data.readFloat();
            case 6 -> data.readDouble();
            case 7 -> {
                int n = size(data.readInt(), "byte array");
                byte[] value = new byte[n];
                data.readFully(value);
                yield value;
            }
            case 8 -> data.readUTF();
            case 9 -> {
                int elementType = data.readByte();
                int n = size(data.readInt(), "list");
                if (elementType == 0 && n > 0) {
                    throw new IOException("NBT list with TAG_End element type but length " + n);
                }
                List<Object> list = new ArrayList<>(Math.min(n, 1 << 16));
                for (int i = 0; i < n; i++) {
                    list.add(readPayload(data, elementType));
                }
                yield list;
            }
            case 10 -> readCompoundPayload(data);
            case 11 -> {
                int n = size(data.readInt(), "int array");
                int[] value = new int[n];
                for (int i = 0; i < n; i++) {
                    value[i] = data.readInt();
                }
                yield value;
            }
            case 12 -> {
                int n = size(data.readInt(), "long array");
                long[] value = new long[n];
                for (int i = 0; i < n; i++) {
                    value[i] = data.readLong();
                }
                yield value;
            }
            default -> throw new IOException("unknown NBT tag id: " + type);
        };
    }

    private static int size(int n, String what) throws IOException {
        if (n < 0 || n > MAX_PAYLOAD_SIZE) {
            throw new IOException("unreasonable NBT " + what + " size: " + n);
        }
        return n;
    }
}
