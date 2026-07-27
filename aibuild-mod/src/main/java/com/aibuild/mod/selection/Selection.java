package com.aibuild.mod.selection;

import com.aibuild.mod.bridge.SiteGate;
import net.minecraft.core.BlockPos;

/**
 * One player's wand selection: corner 1 (left-click) and corner 2 (right-click),
 * either of which may be unset. Setting a corner replaces that corner.
 */
public record Selection(BlockPos corner1, BlockPos corner2) {
    public static final Selection EMPTY = new Selection(null, null);

    public boolean isComplete() {
        return corner1 != null && corner2 != null;
    }

    public Selection withCorner1(BlockPos pos) {
        return new Selection(pos, corner2);
    }

    public Selection withCorner2(BlockPos pos) {
        return new Selection(pos, corner1);
    }

    /** Normalized bounds; only call when {@link #isComplete()}. */
    public SiteGate.Bounds toBounds() {
        return SiteGate.Bounds.of(corner1, corner2);
    }

    public String describe() {
        if (corner1 == null && corner2 == null) {
            return "(empty)";
        }
        String s = "corner1=" + posText(corner1) + " corner2=" + posText(corner2);
        if (isComplete()) {
            s += " → " + toBounds().describe();
        }
        return s;
    }

    private static String posText(BlockPos p) {
        return p == null ? "(unset)" : "(" + p.getX() + " " + p.getY() + " " + p.getZ() + ")";
    }
}
