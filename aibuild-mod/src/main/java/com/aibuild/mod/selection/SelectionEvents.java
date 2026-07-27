package com.aibuild.mod.selection;

import net.fabricmc.fabric.api.event.player.AttackBlockCallback;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionResult;

/**
 * Wand interactions: left-click a block sets corner 1, right-click sets
 * corner 2. Handled on the server only; returning SUCCESS consumes the
 * interaction so the click neither breaks the block nor triggers its use
 * action (chests, doors, ...).
 */
public final class SelectionEvents {
    private SelectionEvents() {
    }

    public static void register(SelectionManager selections) {
        AttackBlockCallback.EVENT.register((player, level, hand, pos, direction) -> {
            if (level.isClientSide() || !player.getItemInHand(hand).is(ModItems.SELECTION_WAND)) {
                return InteractionResult.PASS;
            }
            if (player instanceof ServerPlayer serverPlayer) {
                selections.setFirst(serverPlayer, pos);
            }
            return InteractionResult.SUCCESS;
        });

        UseBlockCallback.EVENT.register((player, level, hand, hitResult) -> {
            if (level.isClientSide() || !player.getItemInHand(hand).is(ModItems.SELECTION_WAND)) {
                return InteractionResult.PASS;
            }
            if (player instanceof ServerPlayer serverPlayer) {
                selections.setSecond(serverPlayer, hitResult.getBlockPos());
            }
            return InteractionResult.SUCCESS;
        });
    }
}
