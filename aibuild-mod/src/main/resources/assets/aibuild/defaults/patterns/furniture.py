#!/usr/bin/env python3
"""furniture.py — furniture atlas generator (家具图鉴, 15 classic pieces).

Pick a `piece`, give `origin` (bottom-front-left cell, y = floor layer the
piece stands on) and `facing` (the direction the piece's FRONT faces —
where the user stands and looks at it; for seats: the way the sitter
faces). ALL block states (stair facing/half, sign rotation, bed part,
barrel/smoker/campfire facing ...) are DERIVED from those two params —
never hand-edit direction states in the output JSON; change params and
re-run (朝向状态由脚本推导,禁止手填, see stair_orientations.md).

Output: {"blocks":[{x,y,z,block}]} compatible with set_blocks_from_file.

Usage:
  python furniture.py --params '{"piece":"bed","origin":[100,64,100],"facing":"east"}' [--out bed.json]
  python furniture.py --params '{"piece":"sofa","origin":[100,64,110],"facing":"south","length":4}'

Pieces (in priority order):
  bed table chair stool sofa bookshelf cabinet kitchen_counter desk
  lamp_post flower_pot bench dresser fireplace piano

Conventions (all classic MC build-circle recipes, no inventions):
  seat stairs face OPPOSITE of `facing` (stair facing = high/back side,
  the sitter looks down the steps); sofa arms are end stairs with their
  backs OUTWARD (tall side at the outer edge); counter/desk fronts use
  half=top stairs whose flat back face points AT `facing`; sign armrests
  stand on the ground beside the seat with their broad side out.
"""
import argparse, json, sys

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
RIGHT = {"north": "east", "east": "south", "south": "west", "west": "north"}
SIGN_ROT = {"south": 0, "west": 4, "north": 8, "east": 12}
BED_COLORS = ("white", "orange", "magenta", "light_blue", "yellow", "lime",
              "pink", "gray", "light_gray", "cyan", "purple", "blue",
              "brown", "green", "red", "black")


def clamp(v, lo, hi):
    return max(lo, min(hi, int(v)))


def stair(mat, facing, half="bottom"):
    return "%s[facing=%s,half=%s]" % (mat, facing, half)


# ---------------------------------------------------------------- pieces
def piece_bed(P, p, F):
    # REAL bed block, two cells: foot at origin, head one cell forward.
    # facing = foot->head direction (the way the sleeper's head points).
    color = p.get("color", "red")
    if color not in BED_COLORS:
        raise ValueError("bed color must be one of %s" % (BED_COLORS,))
    bed = "minecraft:%s_bed" % color
    return [P(0, 0, 0, "%s[part=foot,facing=%s]" % (bed, F)),
            P(0, 1, 0, "%s[part=head,facing=%s]" % (bed, F))]


def piece_table(P, p, F):
    # fence leg(s) + pressure-plate top. width along the right axis.
    wood = p.get("wood", "oak")
    width = clamp(p.get("width", 1), 1, 4)
    out = []
    for u in range(width):
        out.append(P(u, 0, 0, "minecraft:%s_fence" % wood))
        out.append(P(u, 0, 1, "minecraft:%s_pressure_plate" % wood))
    return out


def _sign_arms(P, F, u_left, u_right, y, sign_mat):
    left_dir = OPP[RIGHT[F]]
    right_dir = RIGHT[F]
    return [P(u_left, 0, y, "%s[rotation=%d]" % (sign_mat, SIGN_ROT[left_dir])),
            P(u_right, 0, y, "%s[rotation=%d]" % (sign_mat, SIGN_ROT[right_dir]))]


def piece_chair(P, p, F):
    # one stair (back at the rear) + two standing signs as armrests.
    mat = p.get("material", "minecraft:oak_stairs")
    sign = p.get("sign_material", "minecraft:oak_sign")
    return [P(0, 0, 0, stair(mat, OPP[F]))] + _sign_arms(P, F, -1, 1, 0, sign)


def piece_stool(P, p, F):
    # a bare stair — backless low seat / ottoman (no armrests).
    mat = p.get("material", "minecraft:spruce_stairs")
    return [P(0, 0, 0, stair(mat, OPP[F]))]


def piece_sofa(P, p, F):
    # row of seat stairs (backs at rear) + end stairs as arms, backs OUTWARD.
    mat = p.get("material", "minecraft:spruce_stairs")
    length = clamp(p.get("length", 3), 2, 6)
    out = [P(u, 0, 0, stair(mat, OPP[F])) for u in range(length)]
    out.append(P(-1, 0, 0, stair(mat, OPP[RIGHT[F]])))   # left arm, tall side out
    out.append(P(length, 0, 0, stair(mat, RIGHT[F])))    # right arm, tall side out
    return out


def piece_bookshelf(P, p, F):
    # plain bookshelf wall; texture is rotation-blind (facing unused).
    width = clamp(p.get("width", 2), 1, 4)
    height = clamp(p.get("height", 2), 1, 4)
    return [P(u, 0, v, "minecraft:bookshelf")
            for u in range(width) for v in range(height)]


def piece_cabinet(P, p, F):
    # barrels with lids facing out = cupboard doors. width x height grid.
    width = clamp(p.get("width", 2), 1, 4)
    height = clamp(p.get("height", 2), 1, 4)
    return [P(u, 0, v, "minecraft:barrel[facing=%s]" % F)
            for u in range(width) for v in range(height)]


def piece_kitchen_counter(P, p, F):
    # cauldron sink + upside-down stair counter run + smoker oven.
    mat = p.get("material", "minecraft:spruce_stairs")
    length = clamp(p.get("length", 3), 2, 6)
    out = [P(0, 0, 0, "minecraft:cauldron")]
    for u in range(1, length - 1):
        out.append(P(u, 0, 0, stair(mat, F, "top")))
    out.append(P(length - 1, 0, 0, "minecraft:smoker[facing=%s]" % F))
    return out


def piece_desk(P, p, F):
    # upside-down stair writing desk + lectern with an open book.
    mat = p.get("material", "minecraft:spruce_stairs")
    width = clamp(p.get("width", 3), 2, 4)
    out = [P(u, 0, 0, stair(mat, F, "top")) for u in range(width)]
    out.append(P(width // 2, 0, 1,
                 "minecraft:lectern[facing=%s,has_book=true]" % F))
    return out


def piece_lamp_post(P, p, F):
    # fence-post floor lamp with a lantern on top.
    mat = p.get("material", "minecraft:spruce_fence")
    light = p.get("light_material", "minecraft:lantern")
    height = clamp(p.get("height", 2), 1, 4)
    out = [P(0, 0, v, mat) for v in range(height)]
    out.append(P(0, 0, height, light))
    return out


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
    out = json.dumps({"blocks": build(p)}, ensure_ascii=False)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print("wrote %d blocks to %s"
              % (len(json.loads(out)["blocks"]), a.out), file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
