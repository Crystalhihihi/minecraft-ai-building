package com.aibuild.mod.job;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;

/**
 * One pending block placement.
 *
 * @param keepOnly when true, only replace air (vanilla /fill keep semantics)
 */
public record Placement(BlockPos pos, BlockState state, boolean keepOnly) {
}
