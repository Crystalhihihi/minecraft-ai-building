package com.aibuild.mod.bridge;

import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.minecraft.commands.arguments.blocks.BlockStateParser;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.List;

/**
 * Parses block specs like {@code "minecraft:stone_bricks"} and
 * {@code "minecraft:oak_stairs[facing=north,half=bottom]"} using the vanilla
 * block state parser (mojmap). Runs on the server main thread.
 */
public final class BlockSpecParser {
    private BlockSpecParser() {
    }

    public static final class InvalidBlockException extends Exception {
        private final List<String> suggestions;

        InvalidBlockException(String spec, List<String> suggestions) {
            super("invalid block: " + spec);
            this.suggestions = suggestions;
        }

        public List<String> suggestions() {
            return suggestions;
        }
    }

    public static BlockState parse(MinecraftServer server, String spec) throws InvalidBlockException {
        try {
            return BlockStateParser.parseForBlock(server.registryAccess().lookupOrThrow(Registries.BLOCK), spec, false).blockState();
        } catch (CommandSyntaxException e) {
            throw new InvalidBlockException(spec, suggestions(spec));
        }
    }

    /** Substring fuzzy match over the block registry, capped at 8 entries. */
    public static List<String> suggestions(String spec) {
        String id = spec;
        int bracket = id.indexOf('[');
        if (bracket >= 0) {
            id = id.substring(0, bracket);
        }
        String path = id.contains(":") ? id.substring(id.indexOf(':') + 1) : id;
        // progressively trim the typo tail until something matches
        for (int len = path.length(); len >= Math.min(3, path.length()); len--) {
            List<String> out = substringMatches(path.substring(0, len), 8);
            if (!out.isEmpty()) {
                return out;
            }
        }
        return List.of();
    }

    /**
     * Plain substring fuzzy match over the block registry for the
     * {@code search_blocks} endpoint: strips an optional namespace and any
     * {@code [state]} suffix, then matches against registry key paths,
     * capped at {@code limit} entries (registry order).
     */
    public static List<String> search(String query, int limit) {
        String needle = query == null ? "" : query.trim().toLowerCase(java.util.Locale.ROOT);
        int bracket = needle.indexOf('[');
        if (bracket >= 0) {
            needle = needle.substring(0, bracket);
        }
        if (needle.contains(":")) {
            needle = needle.substring(needle.indexOf(':') + 1);
        }
        return substringMatches(needle, limit);
    }

    private static List<String> substringMatches(String needle, int limit) {
        List<String> out = new ArrayList<>(Math.min(limit, 16));
        for (Identifier key : BuiltInRegistries.BLOCK.keySet()) {
            if (needle.isEmpty() || key.getPath().contains(needle)) {
                out.add(key.toString());
                if (out.size() >= limit) {
                    break;
                }
            }
        }
        return out;
    }
}
