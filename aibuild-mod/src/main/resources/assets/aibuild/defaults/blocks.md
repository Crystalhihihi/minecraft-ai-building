# blocks.md — Common Building Block Quick Reference (MC 1.21)

All ids are namespaced (`minecraft:` prefix required). Grouped by family.
If a block you need is not here, call `search_blocks` — do not guess ids.
Stairs/slabs/walls/fences exist for almost every full block: append
`_stairs` / `_slab` / `_wall` / `_fence` to the base name (exceptions noted).

## 主结构 / Structural basics

- minecraft:stone
- minecraft:cobblestone
- minecraft:mossy_cobblestone
- minecraft:stone_bricks
- minecraft:mossy_stone_bricks
- minecraft:cracked_stone_bricks
- minecraft:chiseled_stone_bricks
- minecraft:smooth_stone
- minecraft:smooth_stone_slab
- minecraft:bricks
- minecraft:mud_bricks
- minecraft:packed_mud
- minecraft:granite / polished_granite
- minecraft:diorite / polished_diorite
- minecraft:andesite / polished_andesite
- minecraft:calcite
- minecraft:tuff / polished_tuff / tuff_bricks / chiseled_tuff_bricks
- minecraft:dirt / coarse_dirt / rooted_dirt
- minecraft:grass_block
- minecraft:dirt_path
- minecraft:gravel
- minecraft:sand / sandstone / smooth_sandstone / chiseled_sandstone
- minecraft:red_sand / red_sandstone / smooth_red_sandstone
- minecraft:terracotta
- minecraft:white_terracotta / light_gray_terracotta / gray_terracotta / brown_terracotta
- minecraft:white_concrete / light_gray_concrete / gray_concrete / black_concrete
- (concrete comes in all 16 colors: orange/magenta/light_blue/yellow/lime/pink/cyan/purple/blue/brown/green/red + the above)

## 木 / Wood ( planks / log / stripped_log / wood / stairs / slab / fence / fence_gate / door / trapdoor / button / pressure_plate / sign )

- minecraft:oak_planks / oak_log / stripped_oak_log
- minecraft:spruce_planks / spruce_log / stripped_spruce_log
- minecraft:birch_planks / birch_log / stripped_birch_log
- minecraft:jungle_planks / jungle_log / stripped_jungle_log
- minecraft:acacia_planks / acacia_log / stripped_acacia_log
- minecraft:dark_oak_planks / dark_oak_log / stripped_dark_oak_log
- minecraft:mangrove_planks / mangrove_log / stripped_mangrove_log
- minecraft:cherry_planks / cherry_log / stripped_cherry_log
- minecraft:pale_oak_planks / pale_oak_log / stripped_pale_oak_log
- minecraft:crimson_planks / warped_planks (nether stems, fireproof)
- minecraft:bamboo_planks / bamboo_mosaic
- Fences: oak_fence / spruce_fence / birch_fence / dark_oak_fence ... (per wood type)
- Doors: oak_door / spruce_door / birch_door / dark_oak_door / iron_door
- Trapdoors: oak_trapdoor / spruce_trapdoor / dark_oak_trapdoor / iron_trapdoor

## 石 / Stone variants & decoration

- minecraft:stone_brick_stairs / stone_brick_slab / stone_brick_wall
- minecraft:cobblestone_stairs / cobblestone_slab / cobblestone_wall
- minecraft:mossy_cobblestone_stairs / mossy_cobblestone_slab / mossy_cobblestone_wall
- minecraft:mossy_stone_brick_stairs / mossy_stone_brick_slab / mossy_stone_brick_wall
- minecraft:brick_stairs / brick_slab / brick_wall
- minecraft:sandstone_stairs / sandstone_slab / sandstone_wall
- minecraft:granite_stairs / granite_slab / granite_wall
- minecraft:diorite_stairs / diorite_slab / diorite_wall
- minecraft:andesite_stairs / andesite_slab / andesite_wall
- minecraft:polished_granite / polished_diorite / polished_andesite (+ _stairs/_slab each)
- minecraft:quartz_block / smooth_quartz / quartz_bricks / quartz_pillar / chiseled_quartz_block
- minecraft:purpur_block / purpur_pillar
- minecraft:prismarine / prismarine_bricks / dark_prismarine
- minecraft:end_stone_bricks
- minecraft:blackstone / polished_blackstone / polished_blackstone_bricks / cracked_polished_blackstone_bricks
- minecraft:basalt / polished_basalt / smooth_basalt
- minecraft:obsidian / crying_obsidian
- minecraft:bedrock (unbreakable — do not use for normal builds)

## 深板岩 / Deepslate family (dark, reads as slate/shadow)

- minecraft:deepslate
- minecraft:cobbled_deepslate (+ _stairs/_slab/_wall)
- minecraft:polished_deepslate (+ _stairs/_slab/_wall)
- minecraft:deepslate_bricks / cracked_deepslate_bricks (+ _stairs/_slab/_wall)
- minecraft:deepslate_tiles / cracked_deepslate_tiles (+ _stairs/_slab/_wall)
- minecraft:chiseled_deepslate
- minecraft:tuff (+ _stairs/_slab/_wall), tuff_bricks (+ _stairs/_slab/_wall)

## 屋顶 / Roofing (the usual stair+slab pairs)

- minecraft:spruce_stairs / spruce_slab (warm brown, default cottage roof)
- minecraft:dark_oak_stairs / dark_oak_slab (near-black spires)
- minecraft:deepslate_tile_stairs / deepslate_tile_slab (slate grey, castle)
- minecraft:deepslate_brick_stairs / deepslate_brick_slab
- minecraft:stone_brick_stairs / stone_brick_slab
- minecraft:brick_stairs / brick_slab (red clay tile look)
- minecraft:mud_brick_stairs / mud_brick_slab
- minecraft:terracotta + colored terracottas (mediterranean tiles)
- minecraft:copper_roof? — NO, does not exist; copper blocks: copper_block / exposed_copper / weathered_copper / oxidized_copper (+ cut_copper _stairs/_slab; oxidized = green patina roofs)

## 窗 / Windows & light passers

- minecraft:glass
- minecraft:glass_pane
- minecraft:tinted_glass (blocks light, dark look)
- Stained glass: white/orange/magenta/light_blue/yellow/lime/pink/gray/light_gray/cyan/purple/blue/brown/green/red/black_stained_glass (+ _pane each)
- minecraft:iron_bars
- Shutters/frames: spruce_trapdoor / dark_oak_trapdoor, any fence, walls

## 照明 / Lighting

- minecraft:torch
- minecraft:wall_torch (attach to wall faces, [facing=...])
- minecraft:lantern (sits or hangs)
- minecraft:soul_lantern (dim blue)
- minecraft:glowstone
- minecraft:sea_lantern
- minecraft:shroomlight
- minecraft:jack_o_lantern
- minecraft:campfire / soul_campfire (smoke + glow)
- minecraft:candle (+ colored candles)
- minecraft:end_rod (modern/vertical light bar)
- minecraft:froglight variants: ochre_froglight / verdant_froglight / pearlescent_froglight

## 地面点缀 / Ground detail & vegetation

- minecraft:dirt_path (worn footpaths — use generously)
- minecraft:farmland
- minecraft:podzol / mycelium
- minecraft:short_grass / tall_grass
- minecraft:fern / large_fern
- Flowers: dandelion / poppy / blue_orchid / allium / azure_bluet / red_tulip / orange_tulip / white_tulip / pink_tulip / oxeye_daisy / cornflower / lily_of_the_valley / sunflower / lilac / rose_bush / peony
- minecraft:oak_leaves / spruce_leaves / birch_leaves / azalea_leaves (hedges)
- minecraft:oak_sapling / spruce_sapling / birch_sapling
- minecraft:azalea / flowering_azalea
- minecraft:moss_block / moss_carpet
- minecraft:vine
- minecraft:lily_pad
- minecraft:sugar_cane
- minecraft:hay_block (farms)
- minecraft:pumpkin / carved_pumpkin / melon
- minecraft:sweet_berry_bush
- Leaf litter/petals (1.21.4+): minecraft:leaf_litter / minecraft:wildflowers / minecraft:pink_petals

## 功能道具 / Props & furniture-ish

- minecraft:barrel (dock/storage clutter)
- minecraft:chest / trapped_chest
- minecraft:crafting_table / furnace / smoker / blast_furnace
- minecraft:anvil / grindstone / stonecutter / smithing_table / fletching_table / cartography_table / loom
- minecraft:composter / cauldron
- minecraft:bookshelf / chiseled_bookshelf / lectern
- minecraft:ladder / scaffolding / chain
- minecraft:bell
- minecraft:flower_pot
- minecraft:item_frame / glow_item_frame / painting (entities — place with caution)
- minecraft:armor_stand (entity)
- minecraft:banner? — use wool colors + loom patterns; ids: white_banner ... red_banner
- minecraft:note_block / jukebox
- minecraft:rail / powered_rail / detector_rail / activator_rail / minecart

## 水景 / Water features

- minecraft:water (place with care — flows)
- minecraft:ice / packed_ice / blue_ice
- minecraft:snow_block / snow (layer) / powder_snow
- minecraft:seagrass / tall_seagrass / kelp
- minecraft:clay / mud

## 禁用/慎用 / Handle with care

- minecraft:air — only via fill/set_blocks with place_air, for carving
- TNT, lava, fire — never unless the task says so
- Command/structure blocks — banned for builds
- Anything not in this file AND not in the style card: justify in plan.md or pick something listed
