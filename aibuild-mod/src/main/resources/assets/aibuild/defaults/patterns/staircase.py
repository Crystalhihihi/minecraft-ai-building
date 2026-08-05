#!/usr/bin/env python3
"""staircase.py — parametric indoor staircase (室内楼梯) generator.

Motivation: hand-placed interior stairs are the #1 orientation failure in
real builds (屋子里的楼梯最容易放歪). All block states are DERIVED from
origin/facing/shape — never hand-edit facing/half in the output JSON;
change params and re-run (朝向状态由脚本推导, see stair_orientations.md).

Geometry contract (口径):
- origin = 底层第一级踏步所在格; origin.y = 底层地板行走面高度 (its stair
  block sits on the floor block at origin.y-1). Rise = 1 block per step,
  steps = floors; last step at origin.y+floors-1, so its tread surface is
  flush with the upper floor slab at origin.y+floors (顶端接楼板面; the
  floor plate itself belongs to the room, not this card).
- facing = 上行方向 (uphill = the stair's high/back side — the iron rule).
- shape straight: one flight of `floors` steps along facing.
- shape l: flight1 of ceil(floors/2) steps along facing, then a W×W solid
  landing (整砖, no slab seams), then flight2 turns 90° to facing's LEFT
  and continues the remaining steps. Fixed left turn — pick origin/facing
  accordingly.
- shape u: flight1 of ceil(floors/2) steps, then a 1-deep × 2W-wide solid
  landing, then flight2 folds back 180° (facing reversed) alongside
  flight1.
- width = steps side by side (1-2), spread to facing's RIGHT.
- railing none/fence/wall: posts at step level on the flight's outer
  edge(s) (same y as the step, attached to it). Landing edges take no
  railing (interior landings sit against walls).
- underside=true fills every step column solid down to origin.y (梯腹填实);
  false leaves the space under the flights open (storage nook) — the
  LANDING column is always filled solid (platform must not float).

Output: {"blocks":[{x,y,z,block}]} compatible with set_blocks_from_file.
Usage:
  python staircase.py --params '{"origin":[100,64,100],"facing":"north","shape":"l","width":2,"floors":4}' [--out stairs.json]
Bare `python staircase.py` prints a demo straight flight to stdout.
"""
import argparse, json, sys

DEFAULTS = {
    "origin": [0, 64, 0],            # [x,y,z] 底层第一级踏步格; y = 底层地板行走面
    "facing": "north",               # 上行方向 (stair facing = uphill)
    "shape": "straight",             # straight | l | u
    "width": 1,                      # 1-2, spread to facing's right
    "floors": 4,                     # 爬升总高(格) = 层净高+1; 层高3 -> 4, 层高4 -> 5
    "material": "minecraft:oak_stairs",
    "railing": "none",               # none | fence | wall
    "railing_material": "",          # "" = derive from material (wood->同种 fence; stone->同种 wall)
    "underside": True,               # 梯腹填实; false = 留空做储物 (landing column stays solid)
}

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
SIDE = {"north": "east", "east": "south", "south": "west", "west": "north"}  # right hand
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
WOODS = {"oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove",
         "cherry", "pale_oak", "crimson", "warped", "bamboo"}
# stairs base -> solid full block, where plain strip of "_stairs" is wrong
SOLID_SPECIAL = {
    "stone_brick": "stone_bricks", "mossy_stone_brick": "mossy_stone_bricks",
    "brick": "bricks", "mud_brick": "mud_bricks",
    "deepslate_brick": "deepslate_bricks", "deepslate_tile": "deepslate_tiles",
    "cracked_deepslate_brick": "cracked_deepslate_bricks",
    "cracked_deepslate_tile": "cracked_deepslate_tiles",
    "tuff_brick": "tuff_bricks", "nether_brick": "nether_bricks",
    "red_nether_brick": "red_nether_bricks",
    "polished_blackstone_brick": "polished_blackstone_bricks",
    "end_stone_brick": "end_stone_bricks", "prismarine_brick": "prismarine_bricks",
    "quartz": "quartz_block", "smooth_quartz": "smooth_quartz",
    "purpur": "purpur_block", "cut_sandstone": "cut_sandstone",
    "cut_red_sandstone": "cut_red_sandstone",
}
NO_WALL = {"quartz", "smooth_quartz", "purpur", "cut_sandstone",
           "cut_red_sandstone", "nether_brick", "red_nether_brick",
           "end_stone_brick", "prismarine", "prismarine_brick", "dark_prismarine"}


def die(msg, legal):
    print(json.dumps({"error": msg, "legal": legal}, ensure_ascii=False), file=sys.stderr)
    sys.exit(2)


def base_of(mat):
    return mat.split(":", 1)[1][:-len("_stairs")]


def solid_of(base):
    if base in WOODS:
        return "minecraft:%s_planks" % base
    return "minecraft:" + SOLID_SPECIAL.get(base, base)


def fence_of(base):
    return "minecraft:%s_fence" % base if base in WOODS else "minecraft:iron_bars"


def wall_of(base):
    if base in WOODS or base in NO_WALL:
        return "minecraft:cobblestone_wall"
    return "minecraft:%s_wall" % base


def check_params(p):
    o = p.get("origin")
    if not (isinstance(o, list) and len(o) == 3 and all(isinstance(v, int) for v in o)):
        die("origin must be [x,y,z] ints", {"origin": "[100,64,100]"})
    if p.get("facing") not in DIRS:
        die("facing must be one of north/south/east/west", {"facing": list(DIRS)})
    shape = str(p.get("shape", "")).lower()
    if shape not in ("straight", "l", "u"):
        die("shape must be straight/l/u", {"shape": ["straight", "l", "u"]})
    p["shape"] = shape
    try:
        p["width"] = int(p["width"]); p["floors"] = int(p["floors"])
    except (TypeError, ValueError):
        die("width/floors must be ints", {"width": "1-2", "floors": "2-8"})
    if not 1 <= p["width"] <= 2:
        die("width out of range", {"width": "1-2"})
    if not 2 <= p["floors"] <= 8:
        die("floors out of range (爬升总高 2-8 格)", {"floors": "2-8"})
    mat = str(p.get("material", ""))
    if not (mat.startswith("minecraft:") and mat.endswith("_stairs")):
        die("material must be a minecraft:*_stairs id",
            {"material": ["minecraft:oak_stairs", "minecraft:stone_brick_stairs"]})
    if p.get("railing") not in ("none", "fence", "wall"):
        die("railing must be none/fence/wall", {"railing": ["none", "fence", "wall"]})
    p["underside"] = bool(p.get("underside"))


def build(p):
    check_params(p)
    ox, oy, oz = p["origin"]
    F, W, H = p["facing"], p["width"], p["floors"]
    S = SIDE[F]
    fx, fz = DIRS[F]
    sx, sz = DIRS[S]
    base = base_of(p["material"])
    solid = solid_of(base)
    rail = p.get("railing_material") or (
        fence_of(base) if p["railing"] == "fence" else wall_of(base))
    cells = {}

    def put(k, w, y, block):  # k along facing, w along right-hand side
        cells[(ox + k * fx + w * sx, y, oz + k * fz + w * sz)] = block

    def stair(k, w, y, face):
        put(k, w, y, "%s[facing=%s,half=bottom]" % (p["material"], face))

    def column(k, w, y_from):  # solid fill from y_from down to oy (接地)
        for y in range(y_from, oy - 1, -1):
            put(k, w, y, solid)

    # flight 1: shared by all shapes — steps k=0..H1-1 along facing
    H1 = (H + 1) // 2
    H2 = H - H1
    for k in range(H1):
        for w in range(W):
            stair(k, w, oy + k, F)
            if p["underside"]:
                column(k, w, oy + k - 1)
        if p["railing"] != "none":
            put(k, -1, oy + k, rail)
            put(k, W, oy + k, rail)

    if p["shape"] == "straight":
        for k in range(H1, H):
            for w in range(W):
                stair(k, w, oy + k, F)
                if p["underside"]:
                    column(k, w, oy + k - 1)
            if p["railing"] != "none":
                put(k, -1, oy + k, rail)
                put(k, W, oy + k, rail)

    elif p["shape"] == "l":
        # landing: W x W solid at y=oy+H1-1 (surface = oy+H1), k=H1..H1+W-1
        for k in range(H1, H1 + W):
            for w in range(W):
                put(k, w, oy + H1 - 1, solid)
                column(k, w, oy + H1 - 2)      # landing column always solid
        # flight 2: turn LEFT (uphill = -S); step j at k=H1..H1+W-1 (width
        # along facing), side offset -1-j, y=oy+H1+j, facing = opposite(S)
        f2 = OPP[S]
        for j in range(H2):
            for w2 in range(W):
                kk, ww = H1 + w2, -1 - j
                stair(kk, ww, oy + H1 + j, f2)
                if p["underside"]:
                    column(kk, ww, oy + H1 + j - 1)
            if p["railing"] != "none":
                put(H1 - 1, -1 - j, oy + H1 + j, rail)
                put(H1 + W, -1 - j, oy + H1 + j, rail)

    else:  # u — 折返: landing 1 deep x 2W wide, flight 2 back along -facing
        for w in range(2 * W):
            put(H1, w, oy + H1 - 1, solid)
            column(H1, w, oy + H1 - 2)
        f2 = OPP[F]
        for j in range(H2):
            for w in range(W, 2 * W):
                stair(H1 - 1 - j, w, oy + H1 + j, f2)
                if p["underside"]:
                    column(H1 - 1 - j, w, oy + H1 + j - 1)
            if p["railing"] != "none":
                put(H1 - 1 - j, 2 * W, oy + H1 + j, rail)

    return [{"x": x, "y": y, "z": z, "block": b}
            for (x, y, z), b in sorted(cells.items())]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}", help="JSON object of parameters")
    ap.add_argument("--out", default="", help="output file (default: stdout)")
    a = ap.parse_args()
    p = dict(DEFAULTS)
    try:
        p.update(json.loads(a.params) if a.params.strip() else {})
    except json.JSONDecodeError as e:
        die("--params is not valid JSON: %s" % e,
            {"example": '{"origin":[100,64,100],"facing":"north","shape":"l"}'})
    blocks = build(p)
    out = json.dumps({"blocks": blocks}, ensure_ascii=False)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print("wrote %d blocks to %s" % (len(blocks), a.out), file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
