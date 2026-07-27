package com.aibuild.mod.selection;

import com.aibuild.mod.AiBuildMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;

/**
 * Mod items. Registration on 1.21.11 (mojmap) requires a {@link ResourceKey} —
 * {@link Items#registerItem(ResourceKey, java.util.function.Function, Item.Properties)}
 * wires the key into the properties itself.
 *
 * The wand uses the vanilla stick model (assets/aibuild/items/selection_wand.json)
 * and stacks to 1.
 */
public final class ModItems {
    public static final ResourceKey<Item> SELECTION_WAND_KEY = ResourceKey.create(
            Registries.ITEM, Identifier.fromNamespaceAndPath(AiBuildMod.MOD_ID, "selection_wand"));
    public static final Item SELECTION_WAND = Items.registerItem(
            SELECTION_WAND_KEY, Item::new, new Item.Properties().stacksTo(1));

    private ModItems() {
    }

    /** Forces class loading / static registration. Call from the mod initializer. */
    public static void register() {
        AiBuildMod.LOGGER.info("[aibuild] registered item {}", SELECTION_WAND_KEY.identifier());
    }
}
