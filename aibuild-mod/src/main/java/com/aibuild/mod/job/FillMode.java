package com.aibuild.mod.job;

import java.util.Locale;

public enum FillMode {
    REPLACE,
    KEEP,
    OUTLINE,
    HOLLOW;

    public static FillMode parse(String raw) {
        return switch (raw.toLowerCase(Locale.ROOT)) {
            case "replace" -> REPLACE;
            case "keep" -> KEEP;
            case "outline" -> OUTLINE;
            case "hollow" -> HOLLOW;
            default -> throw new IllegalArgumentException("invalid mode: " + raw + " (expected replace|keep|outline|hollow)");
        };
    }
}
