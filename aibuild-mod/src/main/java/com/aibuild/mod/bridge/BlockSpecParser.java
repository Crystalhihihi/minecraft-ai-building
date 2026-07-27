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
            List<String> out = substringMatches(path.substring(0, len));
            if (!out.isEmpty()) {
                return out;
            }
        }
        return List.of();
    }

    private static List<String> substringMatches(String needle) {
        List<String> out = new ArrayList<>(8);
        for (Identifier key : BuiltInRegistries.BLOCK.keySet()) {
            if (needle.isEmpty() || key.getPath().contains(needle)) {
                out.add(key.toString());
                if (out.size() >= 8) {
                    break;
                }
            }
        }
        return out;
    }
}
