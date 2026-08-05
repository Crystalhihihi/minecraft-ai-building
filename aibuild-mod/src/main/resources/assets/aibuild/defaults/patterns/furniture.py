#!/usr/bin/env python3
"""furniture.py — furniture atlas generator (家具图鉴, 20 classic pieces).

Pick a `piece`, give `origin` (bottom-front-left cell, y = floor layer the
piece stands on) and `facing` (the direction the piece's FRONT faces —
where the user stands and looks at it; for seats: the way the sitter
faces). ALL block states (stair facing/half, sign rotation, bed/door part,
barrel/smoker/campfire facing, trapdoor half/open ...) are DERIVED from
those two params — never hand-edit direction states in the output JSON;
change params and re-run (朝向状态由脚本推导,禁止手填, see
stair_orientations.md).

Output: {"blocks":[{x,y,z,block}]} compatible with set_blocks_from_file.

Usage:
  python furniture.py --params '{"piece":"bed","origin":[100,64,100],"facing":"east"}' [--out bed.json]
  python furniture.py --params '{"piece":"sofa","origin":[100,64,110],"facing":"south","length":4}'

Pieces (in priority order):
  bed table chair stool sofa bookshelf cabinet kitchen_counter desk
  lamp_post flower_pot bench dresser fireplace piano
  wardrobe fridge bunk_bed            (absorbed from 家具造法图鉴)
  bathtub bathroom_sink               (卫浴线, absorbed from 图片造法提炼)

Conventions (all classic MC build-circle recipes, no inventions):
  seat stairs face OPPOSITE of `facing` (stair facing = high/back side,
  the sitter looks down the steps); sofa arms are end stairs with their
  backs OUTWARD (tall side at the outer edge); counter/desk fronts use
  half=top stairs whose flat back face points AT `facing`; sign armrests
  stand on the ground beside the seat with their broad side out; closed
  trapdoors read as cupboard doors / drawer fronts / table leaves (图鉴
  §2.0); a bottom slab directly above a bed block reads as a headboard.
"""
import argparse, json, sys

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
RIGHT = {"north": "east", "east": "south", "south": "west", "west": "north"}
SIGN_ROT = {"south": 0, "west": 4, "north": 8, "east": 12}
BED_COLORS = ("white", "orange", "magenta", "light_blue", "yellow", "lime",
              "pink", "gray", "light_gray", "cyan", "purple", "blue",
              "brown", "green", "red", "black")


def die(msg, legal):
    print(json.dumps({"error": msg, "legal": legal}, ensure_ascii=False),
          file=sys.stderr)
    sys.exit(2)


def clamp(v, lo, hi):
    return max(lo, min(hi, int(v)))


def stair(mat, facing, half="bottom"):
    return "%s[facing=%s,half=%s]" % (mat, facing, half)


def _wood_derive(mat, suffix, fallback):
    # "minecraft:spruce_stairs" -> "minecraft:spruce_trapdoor" etc.
    base = mat.split(":", 1)[-1].rsplit("_", 1)[0]
    return "minecraft:%s_%s" % (base, suffix) if base else fallback


# ---------------------------------------------------------------- pieces
def piece_bed(P, p, F):
    # REAL bed block, two cells: foot at origin, head one cell forward.
    # facing = foot->head direction (the way the sleeper's head points).
    # Default detail (图鉴 §2.1): a bottom slab right above the head block
    # reads as a headboard — same footprint column, so callers are safe.
    color = p.get("color", "red")
    if color not in BED_COLORS:
        raise ValueError("bed color must be one of %s" % (BED_COLORS,))
    bed = "minecraft:%s_bed" % color
    out = [P(0, 0, 0, "%s[part=foot,facing=%s]" % (bed, F)),
           P(0, 1, 0, "%s[part=head,facing=%s]" % (bed, F))]
    if p.get("headboard", True):
        hb = p.get("headboard_material", "minecraft:oak_slab")
        out.append(P(0, 1, 1, "%s[type=bottom]" % hb))
    if p.get("posts", False):           # four-poster frame (帷幔床, 图鉴 §2.1)
        post = p.get("post_material", "minecraft:oak_fence")
        for (u, w) in ((-1, -1), (1, -1), (-1, 2), (1, 2)):
            out += [P(u, w, v, post) for v in range(3)]
    return out


def piece_table(P, p, F):
    # fence leg(s) + top. width along the right axis.
    # top: "plate" = pressure plate (classic side table) |
    #      "cloth" = carpet tablecloth (图鉴 §2.2 桌布).
    wood = p.get("wood", "oak")
    width = clamp(p.get("width", 1), 1, 4)
    top = p.get("top", "plate")
    if top == "cloth":
        top_block = "minecraft:%s" % p.get("cloth_material",
                                           "minecraft:white_carpet")
    elif top == "plate":
        top_block = "minecraft:%s_pressure_plate" % wood
    else:
        raise ValueError("table top must be 'plate' or 'cloth'")
    out = []
    for u in range(width):
        out.append(P(u, 0, 0, "minecraft:%s_fence" % wood))
        out.append(P(u, 0, 1, top_block))
    return out


def _sign_arms(P, F, u_left, u_right, y, sign_mat):
    left_dir = OPP[RIGHT[F]]
    right_dir = RIGHT[F]
    return [P(u_left, 0, y, "%s[rotation=%d]" % (sign_mat, SIGN_ROT[left_dir])),
            P(u_right, 0, y, "%s[rotation=%d]" % (sign_mat, SIGN_ROT[right_dir]))]


def piece_chair(P, p, F):
    # one stair (back at the rear) + armrests.
    # arm: "sign" (classic) | "trapdoor" (closed side trapdoors, 图鉴 §2.4)
    #      | "none" (bare side chair).
    mat = p.get("material", "minecraft:oak_stairs")
    arm = p.get("arm", "sign")
    out = [P(0, 0, 0, stair(mat, OPP[F]))]
    if arm == "sign":
        sign = p.get("sign_material", "minecraft:oak_sign")
        out += _sign_arms(P, F, -1, 1, 0, sign)
    elif arm == "trapdoor":
        td = p.get("trapdoor_material",
                   _wood_derive(mat, "trapdoor", "minecraft:oak_trapdoor"))
        left_dir, right_dir = OPP[RIGHT[F]], RIGHT[F]
        out.append(P(-1, 0, 0,
                     "%s[facing=%s,half=top,open=false]" % (td, right_dir)))
        out.append(P(1, 0, 0,
                     "%s[facing=%s,half=top,open=false]" % (td, left_dir)))
    elif arm != "none":
        raise ValueError("chair arm must be 'sign', 'trapdoor' or 'none'")
    return out


def piece_stool(P, p, F):
    # style: "stair" = bare stair (backless low seat / ottoman) |
    #        "bar" = fence post + top slab (高脚凳/吧台凳, 图鉴 §2.4).
    style = p.get("style", "stair")
    if style == "bar":
        post = p.get("post_material", "minecraft:spruce_fence")
        top = p.get("top_material", "minecraft:spruce_slab")
        return [P(0, 0, 0, post), P(0, 0, 1, "%s[type=top]" % top)]
    if style != "stair":
        raise ValueError("stool style must be 'stair' or 'bar'")
    mat = p.get("material", "minecraft:spruce_stairs")
    return [P(0, 0, 0, stair(mat, OPP[F]))]


def piece_sofa(P, p, F):
    # row of seat stairs (backs at rear) + end stairs as arms, backs OUTWARD.
    # Opt-in detail (图鉴 §2.4):
    #   cushion=<color>  — wool cushion cap on each seat stair (same column)
    #   back=true        — open trapdoor back panels one cell BEHIND the seat
    #                      row (adds 1 cell of depth; not for wall-flush use)
    mat = p.get("material", "minecraft:spruce_stairs")
    length = clamp(p.get("length", 3), 2, 6)
    out = [P(u, 0, 0, stair(mat, OPP[F])) for u in range(length)]
    out.append(P(-1, 0, 0, stair(mat, OPP[RIGHT[F]])))   # left arm, tall side out
    out.append(P(length, 0, 0, stair(mat, RIGHT[F])))    # right arm, tall side out
    cushion = p.get("cushion", "")
    if cushion:
        for u in range(length):
            out.append(P(u, 0, 1, "minecraft:%s_wool" % cushion))
    if p.get("back", False):
        td = p.get("trapdoor_material",
                   _wood_derive(mat, "trapdoor", "minecraft:spruce_trapdoor"))
        for u in range(length):
            out.append(P(u, 1, 0,
                         "%s[facing=%s,half=top,open=true]" % (td, OPP[F])))
    return out


def piece_bookshelf(P, p, F):
    # plain bookshelf wall; texture is rotation-blind (facing unused).
    # trim=true caps the wall with a slab strip (same columns, 图鉴 §2.6
    # 层板) — reads as a finished top edge instead of raw shelf tops.
    width = clamp(p.get("width", 2), 1, 4)
    height = clamp(p.get("height", 2), 1, 4)
    out = [P(u, 0, v, "minecraft:bookshelf")
           for u in range(width) for v in range(height)]
    if p.get("trim", False):
        slab = p.get("trim_material", "minecraft:oak_slab")
        out += [P(u, 0, height, "%s[type=bottom]" % slab)
                for u in range(width)]
    return out


def piece_cabinet(P, p, F):
    # style "barrel" (default): barrels with lids facing out = cupboard doors.
    # style "shelf" (图鉴 §2.5): bookshelf body + closed trapdoor lid on top
    # (same columns, +1 layer) — reads as a display cabinet with a cover.
    # style "banner" (图片提炼 e850): barrel grid + a wall banner hung in the
    # FRONT row cell of each barrel = modern banner cupboard doors (adds 1
    # cell of depth; banners read as light door panels).
    width = clamp(p.get("width", 2), 1, 4)
    height = clamp(p.get("height", 2), 1, 4)
    style = p.get("style", "barrel")
    if style == "barrel":
        return [P(u, 0, v, "minecraft:barrel[facing=%s]" % F)
                for u in range(width) for v in range(height)]
    if style == "shelf":
        td = p.get("trapdoor_material", "minecraft:oak_trapdoor")
        out = [P(u, 0, v, "minecraft:bookshelf")
               for u in range(width) for v in range(height)]
        out += [P(u, 0, height,
                  "%s[facing=%s,half=bottom,open=false]" % (td, F))
                for u in range(width)]
        return out
    if style == "banner":
        banner = p.get("banner_material", "minecraft:white_wall_banner")
        out = [P(u, 0, v, "minecraft:barrel[facing=%s]" % F)
               for u in range(width) for v in range(height)]
        out += [P(u, -1, v, "%s[facing=%s]" % (banner, F))
                for u in range(width) for v in range(height)]
        return out
    raise ValueError("cabinet style must be 'barrel', 'shelf' or 'banner'")


def piece_kitchen_counter(P, p, F):
    # cauldron sink + upside-down stair counter run + smoker oven.
    # faucet=true adds a lever tap in the wall cell BEHIND the sink
    # (图鉴 §2.7) — only for wall-flush placement.
    # curtain=true (图片提炼 e850) hangs a striped banner 挡布 in the front
    # cell of the sink + counter run (adds 1 cell of depth; not the smoker).
    mat = p.get("material", "minecraft:spruce_stairs")
    length = clamp(p.get("length", 3), 2, 6)
    out = [P(0, 0, 0, "minecraft:cauldron")]
    for u in range(1, length - 1):
        out.append(P(u, 0, 0, stair(mat, F, "top")))
    out.append(P(length - 1, 0, 0, "minecraft:smoker[facing=%s]" % F))
    if p.get("faucet", False):
        out.append(P(0, -1, 1,
                     "minecraft:lever[face=wall,facing=%s]" % OPP[F]))
    if p.get("curtain", False):
        banner = p.get("curtain_material", "minecraft:light_blue_wall_banner")
        out += [P(u, -1, 0, "%s[facing=%s]" % (banner, F))
                for u in range(length - 1)]
    return out


def piece_desk(P, p, F):
    # style "slab" (default): upside-down stair writing desk + lectern.
    # style "study" (图鉴 §2.3 builditapp 工作桌): barrel drawer pedestals
    # + stair desktop + bookshelf side rack + lectern + potted tulip.
    mat = p.get("material", "minecraft:spruce_stairs")
    width = clamp(p.get("width", 3), 2, 4)
    style = p.get("style", "slab")
    if style == "slab":
        out = [P(u, 0, 0, stair(mat, F, "top")) for u in range(width)]
        out.append(P(width // 2, 0, 1,
                     "minecraft:lectern[facing=%s,has_book=true]" % F))
        return out
    if style == "study":
        out = [P(0, 0, 0, "minecraft:barrel[facing=%s]" % F),
               P(width - 1, 0, 0, "minecraft:barrel[facing=%s]" % F)]
        out += [P(u, 0, 1, stair(mat, F, "top")) for u in range(width)]
        out.append(P(width - 1, 0, 2, "minecraft:bookshelf"))
        out.append(P(0, 0, 2, "minecraft:lectern[facing=%s,has_book=true]" % F))
        out.append(P(width // 2, 0, 2, "minecraft:potted_red_tulip"))
        return out
    raise ValueError("desk style must be 'slab' or 'study'")


def piece_lamp_post(P, p, F):
    # style "fence" (default): fence-post floor lamp with a lantern on top.
    # style "end_rod" (图鉴 §2.8 现代落地灯): stacked end rods, glowing tip.
    style = p.get("style", "fence")
    height = clamp(p.get("height", 2), 1, 4)
    if style == "fence":
        mat = p.get("material", "minecraft:spruce_fence")
        light = p.get("light_material", "minecraft:lantern")
        out = [P(0, 0, v, mat) for v in range(height)]
        out.append(P(0, 0, height, light))
        return out
    if style == "end_rod":
        return [P(0, 0, v, "minecraft:end_rod[facing=up]")
                for v in range(height)]
    raise ValueError("lamp_post style must be 'fence' or 'end_rod'")


def piece_flower_pot(P, p, F):
    # potted plant (flower_pot + plant = the potted_* block family);
    # pedestal=true puts it on a fence-post plant stand.
    plant = p.get("plant", "red_tulip")
    pot = plant if plant.startswith("minecraft:potted_") \
        else "minecraft:potted_%s" % plant
    if p.get("pedestal", False):
        return [P(0, 0, 0, p.get("material", "minecraft:spruce_fence")),
                P(0, 0, 1, pot)]
    return [P(0, 0, 0, pot)]


def piece_bench(P, p, F):
    # backless slab seat + standing-sign armrests (park bench).
    mat = p.get("material", "minecraft:spruce_slab")
    sign = p.get("sign_material", "minecraft:spruce_sign")
    length = clamp(p.get("length", 2), 2, 4)
    slab = mat if "[" in mat else mat + "[type=bottom]"
    out = [P(u, 0, 0, slab) for u in range(length)]
    return out + _sign_arms(P, F, -1, length, 0, sign)


def piece_dresser(P, p, F):
    # tall chest of drawers: barrel drawer-fronts + slab top surface.
    width = clamp(p.get("width", 2), 1, 3)
    height = clamp(p.get("height", 3), 2, 4)
    top = p.get("top_material", "minecraft:spruce_slab")
    out = [P(u, 0, v, "minecraft:barrel[facing=%s]" % F)
           for u in range(width) for v in range(height)]
    out += [P(u, 0, height, "%s[type=bottom]" % top) for u in range(width)]
    return out


def piece_fireplace(P, p, F):
    # campfire firebox + upside-down stair lintel (arch over the fire)
    # + brick breast and a 1-wide chimney column.
    mat = p.get("material", "minecraft:stone_bricks")
    lintel = p.get("lintel_material", "minecraft:stone_brick_stairs")
    fire = p.get("fire", "minecraft:campfire")
    chimney = clamp(p.get("chimney", 2), 0, 8)
    out = [P(0, 0, 0, mat),
           P(1, 0, 0, "%s[facing=%s]" % (fire, F)),
           P(2, 0, 0, mat),
           P(0, 0, 1, mat),
           P(1, 0, 1, stair(lintel, F, "top")),
           P(2, 0, 1, mat),
           P(0, 0, 2, mat), P(1, 0, 2, mat), P(2, 0, 2, mat)]
    out += [P(1, 0, 3 + v, mat) for v in range(chimney)]
    return out


def piece_piano(P, p, F):
    # upright piano: dark body, white keys strip facing the player,
    # stair lid sloping toward the player (music-stand top).
    body = p.get("material", "minecraft:dark_oak_planks")
    keys = p.get("keys_material", "minecraft:white_concrete")
    lid = p.get("lid_material", "")
    if not lid:
        lid = body.replace("_planks", "_stairs") if body.endswith("_planks") \
            else "minecraft:dark_oak_stairs"
    out = [P(u, 0, 0, body) for u in range(3)]
    out += [P(0, 0, 1, body), P(1, 0, 1, keys), P(2, 0, 1, body)]
    out += [P(u, 0, 2, stair(lid, OPP[F])) for u in range(3)]
    return out


# ------------------------------------------------- new pieces (家具造法图鉴)
def piece_wardrobe(P, p, F):
    # 衣橱 (图鉴 §2.5): 2-wide solid body + double doors in the front row
    # with handles toward the middle + stair cornice on top.
    body = p.get("material", "minecraft:dark_oak_planks")
    door = p.get("door_material", "minecraft:oak_door")
    out = [P(u, 0, v, body) for u in range(2) for v in range(2)]
    for u, hinge in ((0, "right"), (1, "left")):      # handles meet mid
        out.append(P(u, -1, 0, "%s[facing=%s,half=lower,hinge=%s]"
                     % (door, F, hinge)))
        out.append(P(u, -1, 1, "%s[facing=%s,half=upper,hinge=%s]"
                     % (door, F, hinge)))
    cornice = p.get("cornice_material",
                    _wood_derive(body, "stairs", "minecraft:dark_oak_stairs"))
    out += [P(u, 0, 2, stair(cornice, F, "top")) for u in range(2)]
    return out


def piece_fridge(P, p, F):
    # 冰箱 (图鉴 §2.7 最简带储物版): 2-high iron body + iron door in the
    # front cell (opens for access) + button handle on the upper door cell.
    body = p.get("material", "minecraft:iron_block")
    out = [P(0, 0, 0, body), P(0, 0, 1, body),
           P(0, -1, 0, "minecraft:iron_door[facing=%s,half=lower]" % F),
           P(0, -1, 1, "minecraft:iron_door[facing=%s,half=upper]" % F),
           P(0, -2, 1, "minecraft:stone_button[face=wall,facing=%s]" % F)]
    return out


def piece_bunk_bed(P, p, F):
    # 双层床 (图鉴 §2.1): real bed at floor level, fence posts rising at the
    # head & foot columns, second real bed on top. facing = foot->head.
    # style "storage" (图片提炼 62f6, opt-in): + vertical open trapdoor
    # guard rail along the top bunk's right edge, ladder at the foot front,
    # and a barrel storage column behind the head (adds depth to w=2).
    color = p.get("color", "red")
    if color not in BED_COLORS:
        raise ValueError("bed color must be one of %s" % (BED_COLORS,))
    post = p.get("post_material", "minecraft:oak_fence")
    bed = "minecraft:%s_bed" % color
    out = [P(0, 0, 0, "%s[part=foot,facing=%s]" % (bed, F)),
           P(0, 1, 0, "%s[part=head,facing=%s]" % (bed, F))]
    out += [P(0, w, v, post) for w in (0, 1) for v in (1, 2)]
    out += [P(0, 0, 3, "%s[part=foot,facing=%s]" % (bed, F)),
            P(0, 1, 3, "%s[part=head,facing=%s]" % (bed, F))]
    style = p.get("style", "classic")
    if style == "storage":
        td = p.get("rail_material", "minecraft:spruce_trapdoor")
        for w in (0, 1):          # guard rail: vertical trapdoors, hinge to bed
            out.append(P(1, w, 4, "%s[facing=%s,half=bottom,open=true]"
                         % (td, OPP[RIGHT[F]])))
        for v in (1, 2, 3):       # ladder up the foot front
            out.append(P(0, -1, v, "minecraft:ladder[facing=%s]" % F))
        out += [P(u, 2, v, "minecraft:barrel[facing=%s]" % F)
                for u in (0, 1) for v in (0, 1, 2)]
        return out
    if style != "classic":
        raise ValueError("bunk_bed style must be 'classic' or 'storage'")
    return out


# ------------------------------------------------- bathroom pieces (图片造法提炼)
def piece_bathtub(P, p, F):
    # 浴缸 (图片提炼 8cc4 + b8f3 手法): 2-wide basin ringed by half=top
    # stairs facing OUTWARD with waterlogged=true — the water lives in the
    # stair/slab state, no raw water blocks (no fluid spill, nothing for
    # support_check to misjudge). faucet=true (default) puts a
    # tripwire_hook tap on the wall cell BEHIND the back rim (贴墙摆放).
    mat = p.get("material", "minecraft:spruce_stairs")
    length = clamp(p.get("length", 3), 2, 4)
    out = []
    for w in range(length):
        for u in range(2):
            if w == 0:
                f = OPP[F]                      # front rim
            elif w == length - 1:
                f = F                           # back rim
            else:
                f = OPP[RIGHT[F]] if u == 0 else RIGHT[F]   # side rims
            out.append(P(u, w, 0,
                         "%s[facing=%s,half=top,waterlogged=true]" % (mat, f)))
    if p.get("faucet", True):
        out.append(P(0, length, 1, "minecraft:tripwire_hook[facing=%s]"
                     % OPP[F]))
    return out


def piece_bathroom_sink(P, p, F):
    # 浴室水槽 (图片提炼 b8f3 洗手池造法, 8f12 的 minecart 台盆是实体无法
    # setblock, 按文档降级为 waterlogged 楼梯盆): white vanity body +
    # half=top waterlogged stair basin + tripwire_hook faucet on the wall
    # cell behind (same convention as kitchen_counter's lever).
    # Opt-in wall dressing (need a wall behind, w=-1): mirror=true hangs
    # white_wall_banner mirrors above the faucet; towel=true hangs a
    # light_blue_wall_banner 毛巾 beside it.
    width = clamp(p.get("width", 2), 2, 3)
    body = p.get("material", "minecraft:white_concrete")
    basin = p.get("basin_material", "minecraft:quartz_stairs")
    out = [P(u, 0, 0, body) for u in range(width)]
    out += [P(u, 0, 1, "%s[facing=%s,half=top,waterlogged=true]" % (basin, F))
            for u in range(width)]
    if p.get("faucet", True):
        out.append(P(0, -1, 2, "minecraft:tripwire_hook[facing=%s]" % OPP[F]))
    if p.get("soap", True):                     # 海泡菜皂盒 on the basin rim
        out.append(P(width - 1, 0, 2,
                     "minecraft:sea_pickle[pickles=2,waterlogged=false]"))
    if p.get("mirror", False):
        for u in range(width):
            out.append(P(u, -1, 3,
                         "minecraft:white_wall_banner[facing=%s]" % OPP[F]))
    if p.get("towel", False):
        out.append(P(width - 1, -1, 2,
                     "minecraft:light_blue_wall_banner[facing=%s]" % OPP[F]))
    return out


PIECES = {
    "bed": piece_bed,
    "table": piece_table,
    "chair": piece_chair,
    "stool": piece_stool,
    "sofa": piece_sofa,
    "bookshelf": piece_bookshelf,
    "cabinet": piece_cabinet,
    "kitchen_counter": piece_kitchen_counter,
    "desk": piece_desk,
    "lamp_post": piece_lamp_post,
    "flower_pot": piece_flower_pot,
    "bench": piece_bench,
    "dresser": piece_dresser,
    "fireplace": piece_fireplace,
    "piano": piece_piano,
    "wardrobe": piece_wardrobe,
    "fridge": piece_fridge,
    "bunk_bed": piece_bunk_bed,
    "bathtub": piece_bathtub,
    "bathroom_sink": piece_bathroom_sink,
}

DEFAULTS = {"origin": [0, 64, 0], "facing": "south", "piece": "bed"}


def build(p):
    piece = p.get("piece", "bed")
    if piece not in PIECES:
        raise ValueError("unknown piece %r; valid: %s"
                         % (piece, ", ".join(PIECES)))
    F = p.get("facing", "south")
    if F not in DIRS:
        raise ValueError("facing must be one of north/south/east/west")
    ox, oy, oz = p.get("origin", [0, 64, 0])
    fx, fz = DIRS[F]                      # forward (into the piece)
    rx, rz = DIRS[RIGHT[F]]               # right, seen from the front

    def P(u, w, v, block):
        return {"x": ox + rx * u + fx * w,
                "y": oy + v,
                "z": oz + rz * u + fz * w,
                "block": block}

    return PIECES[piece](P, p, F)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    p = dict(DEFAULTS)
    p.update(json.loads(a.params) if a.params.strip() else {})
    try:
        blocks = build(p)
    except ValueError as e:
        die(str(e), {"piece": sorted(PIECES), "facing": sorted(DIRS)})
    out = json.dumps({"blocks": blocks}, ensure_ascii=False)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print("wrote %d blocks to %s"
              % (len(json.loads(out)["blocks"]), a.out), file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
