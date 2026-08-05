#!/usr/bin/env python3
"""wall_weathering.py — parametric wall texturing/weathering (墙壁肌理) generator.

Emits one facade rectangle (1 block thick) that is NEVER a flat single-
material slab — the four build-circle techniques, all parameterized:

1. 材质掺比 (material mixing): a palette of [block, weight] entries — a
   primary material plus 2-3 accents blended in by weighted random
   (e.g. stone_bricks + cracked/mossy_stone_bricks). Ratios come from
   GrabCraft sample stats + community gradient recipes (see
   wall_weathering.md); deterministic via `seed`.
2. 深浅分层 (vertical banding): base_height bottom rows use base_palette
   (heavier/darker: cobble + mossy cobble), the body uses palette; with
   gradient=true the accent share ramps up toward the base (weathering
   creeps from the ground).
3. 壁柱/线脚分格 (pilasters + string courses): pilaster_every N columns of
   pilaster_material full height; course_rows = horizontal beam rows
   (course_material; *_log axis derived from the wall direction — 禁止手填).
4. 藤蔓做旧 (aging): vine_pct probability per column of a vine strip
   hanging down the front face (vine face state derived from `facing`).
5. 修补痕迹 (patch): patch_pct > 0 replaces 1-2 small rectangles wholesale
   with patch_material (木补砖墙类; "" = auto: 预设基座主材 — 同风格族异材).
   Default 0 = off, and the patch pass then draws ZERO rng — old callers'
   output is byte-identical (向后兼容).

Conventions: origin = bottom-LEFT cell of the facade (seen from outside),
y = base layer; facing = the outward normal. u runs along the wall to the
outside viewer's right. Output: {"blocks":[{x,y,z,block}]} compatible with
set_blocks_from_file.

Usage:
  python wall_weathering.py --params '{"origin":[100,64,100],"facing":"south","width":9,"height":6,"preset":"stone_brick_aged"}' [--out wall.json]
  python wall_weathering.py --params '{"origin":[100,64,120],"facing":"east","width":11,"height":7,"preset":"plaster_timber","pilaster_every":3,"course_rows":[0,3]}'
"""
import argparse, json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
RIGHT = {"north": "east", "east": "south", "south": "west", "west": "north"}

# Ratios: GrabCraft 1668-sample palette stats (scratch/phase9/gc_probe/
# stats_palettes.md: stone_bricks/cobblestone dominant in stone/medieval/
# military builds) + BlockBlend community gradient recipes — see
# wall_weathering.md for the full derivation.
PRESETS = {
    "stone_brick_aged": {   # castle/keep body, aged (BlockBlend ruins band 3->1 flip)
        "palette": [["minecraft:stone_bricks", 60],
                    ["minecraft:cracked_stone_bricks", 15],
                    ["minecraft:mossy_stone_bricks", 15],
                    ["minecraft:cobblestone", 10]],
        "base_palette": [["minecraft:cobblestone", 40],
                         ["minecraft:mossy_cobblestone", 30],
                         ["minecraft:stone", 20],
                         ["minecraft:stone_bricks", 10]],
    },
    "cobble_rustic": {      # medieval cottage/farm wall (GrabCraft medieval top-8)
        "palette": [["minecraft:cobblestone", 55],
                    ["minecraft:mossy_cobblestone", 20],
                    ["minecraft:stone", 15],
                    ["minecraft:andesite", 10]],
        "base_palette": [["minecraft:cobblestone", 45],
                         ["minecraft:mossy_cobblestone", 30],
                         ["minecraft:stone", 15],
                         ["minecraft:gravel", 10]],
    },
    "deepslate_dark": {     # slate-dark fortress/gothic
        "palette": [["minecraft:deepslate_bricks", 55],
                    ["minecraft:cracked_deepslate_bricks", 20],
                    ["minecraft:cobbled_deepslate", 15],
                    ["minecraft:deepslate_tiles", 10]],
        "base_palette": [["minecraft:cobbled_deepslate", 50],
                         ["minecraft:deepslate", 30],
                         ["minecraft:blackstone", 20]],
    },
    "brick_townhouse": {    # red-brick town house
        "palette": [["minecraft:bricks", 75],
                    ["minecraft:stone_bricks", 15],
                    ["minecraft:mud_bricks", 10]],
        "base_palette": [["minecraft:stone_bricks", 60],
                         ["minecraft:bricks", 25],
                         ["minecraft:mossy_stone_bricks", 15]],
    },
    "plaster_timber": {     # half-timbered plaster infill (pair with pilasters)
        "palette": [["minecraft:white_terracotta", 75],
                    ["minecraft:light_gray_terracotta", 20],
                    ["minecraft:smooth_stone", 5]],
        "base_palette": [["minecraft:stone_bricks", 60],
                         ["minecraft:cobblestone", 25],
                         ["minecraft:mossy_cobblestone", 15]],
    },
}

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] bottom-LEFT cell of the facade (outside view); y = base layer
    "facing": "south",             # outward normal
    "width": 9,                    # 3-64
    "height": 6,                   # 3-64
    "preset": "stone_brick_aged",  # named palette set; explicit palette/base_palette override it
    "palette": None,               # [[block, weight], ...] body mix; first entry = primary
    "base_height": 1,              # bottom rows using base_palette, 0-4
    "base_palette": None,          # [[block, weight], ...] heavy/dark base band
    "gradient": True,              # accent share ramps up toward the base
    "pilaster_every": 0,           # 0=off; N = pilaster column every N cells (u=0 always when on)
    "pilaster_material": "minecraft:spruce_log",
    "pilaster_ends": True,         # also force a pilaster at the last column
    "course_rows": [],             # y-offsets of string-course rows (beam rows)
    "course_material": "minecraft:spruce_log",  # *_log -> axis derived from wall direction
    "vine_pct": 10,                # 0-50, per-column chance of a hanging vine strip
    "patch_pct": 0,                # 0-30, % of facade area patched with a different material (0=off)
    "patch_material": "",          # "" = auto: preset base_palette primary (同族异材)
    "seed": 7
}


def parse_palette(raw, key):
    if not isinstance(raw, list) or not raw:
        die("%s must be a non-empty list of [block, weight]" % key,
            {key: [["minecraft:stone_bricks", 60], ["minecraft:mossy_stone_bricks", 20]]})
    out = []
    for entry in raw:
        if (not isinstance(entry, list)) or len(entry) != 2 \
                or not isinstance(entry[0], str) or not str(entry[0]).startswith("minecraft:"):
            die("bad %s entry %r" % (key, entry),
                {key: [["minecraft:stone_bricks", 60], ["minecraft:mossy_stone_bricks", 20]]})
        try:
            w = float(entry[1])
        except (TypeError, ValueError):
            die("bad weight in %s entry %r" % (key, entry), {key: "weights must be numbers > 0"})
        if w <= 0:
            die("weights must be > 0 in %s" % key, {key: "weights must be numbers > 0"})
        out.append((entry[0], w))
    return out


def pick(rng, palette, accent_factor):
    """Weighted pick; entry 0 is the primary, accents scale by accent_factor."""
    weights = [palette[0][1]] + [w * accent_factor for _, w in palette[1:]]
    total = sum(weights)
    r = rng.random() * total
    for (block, _), w in zip(palette, weights):
        r -= w
        if r <= 0:
            return block
    return palette[0][0]


def build(p):
    F = p["facing"]
    width, height = int(p["width"]), int(p["height"])
    ox, oy, oz = [int(v) for v in p["origin"]]
    fx, fz = DIRS[F]
    ux, uz = DIRS[OPP[RIGHT[F]]]               # along the wall, viewer's right
    rng = random.Random(int(p["seed"]))

    preset = PRESETS[p["preset"]]
    palette = parse_palette(p["palette"], "palette") if p["palette"] \
        else [(b, float(w)) for b, w in preset["palette"]]
    base_palette = parse_palette(p["base_palette"], "base_palette") if p["base_palette"] \
        else [(b, float(w)) for b, w in preset["base_palette"]]
    base_h = int(p["base_height"])
    gradient = bool(p["gradient"])
    every = int(p["pilaster_every"])
    course_rows = {int(y) for y in p["course_rows"]}
    course_mat = str(p["course_material"])
    if course_mat.endswith("_log"):            # beam axis derived from wall direction
        axis = "x" if (ux, uz) in ((1, 0), (-1, 0)) else "z"
        course_mat = "%s[axis=%s]" % (course_mat, axis)
    vine_pct = float(p["vine_pct"])

    cells = {}
    for u in range(width):
        is_pilaster = every > 0 and (
            u % every == 0 or (p["pilaster_ends"] and u == width - 1))
        for v in range(height):
            if is_pilaster:
                cells[(u, v)] = p["pilaster_material"]
            elif v in course_rows:
                cells[(u, v)] = course_mat
            else:
                pal = base_palette if v < base_h else palette
                factor = (1.0 - v / max(1, height - 1)) if gradient else 1.0
                cells[(u, v)] = pick(rng, pal, factor)

    # repair patches: 1-2 small rectangles wholly swapped to a repair material
    # (修补痕迹). Runs only when patch_pct > 0 — zero rng draws when off, so
    # legacy callers keep byte-identical output.
    patch_pct = float(p["patch_pct"])
    if patch_pct > 0:
        pmat = str(p["patch_material"]) or base_palette[0][0]
        n_patch = 1 if rng.random() < 0.5 else 2
        target_each = max(2, width * height * patch_pct / 100.0 / n_patch)
        for _ in range(n_patch):
            pw = max(1, min(4, round(target_each ** 0.5 * 1.3)))
            ph = max(1, min(3, round(target_each / pw)))
            pw, ph = min(pw, width), min(ph, height)
            u0 = rng.randint(0, width - pw)
            v0 = rng.randint(0, height - ph)
            for u in range(u0, u0 + pw):
                for v in range(v0, v0 + ph):
                    cells[(u, v)] = pmat

    # aging: vine strips hanging down the front face (whitelisted for support)
    for u in range(width):
        if rng.random() * 100 >= vine_pct:
            continue
        top = rng.randrange(max(1, height // 2), height)
        run = rng.randrange(1, 4)
        for v in range(top, max(0, top - run), -1):
            cells[(u, v, "vine")] = "minecraft:vine[%s=true]" % F

    out = []
    for key in sorted(cells, key=str):
        block = cells[key]
        u, v = key[0], key[1]
        w = 1 if len(key) == 3 else 0          # vines sit one cell off the face
        out.append({"x": ox + ux * u + fx * w, "y": oy + v,
                    "z": oz + uz * u + fz * w, "block": block})
    return out


def validate(p):
    if p["facing"] not in DIRS:
        die("facing must be one of north/south/east/west", {"facing": list(DIRS)})
    if p["preset"] not in PRESETS and not p["palette"]:
        die("preset must be one of %s (or pass an explicit palette)" % (tuple(PRESETS),),
            {"preset": list(PRESETS)})
    try:
        width, height = int(p["width"]), int(p["height"])
    except (TypeError, ValueError):
        die("width/height must be ints", {"width": "3-64", "height": "3-64"})
    if not 3 <= width <= 64 or not 3 <= height <= 64:
        die("width/height out of range", {"width": "3-64", "height": "3-64"})
    base_h = int(p["base_height"])
    if not 0 <= base_h <= min(4, height - 2):
        die("base_height out of range", {"base_height": "0-%d" % min(4, height - 2)})
    if not 0 <= int(p["pilaster_every"]) <= 8:
        die("pilaster_every out of range", {"pilaster_every": "0-8 (0=off)"})
    for y in p["course_rows"]:
        if not 0 <= int(y) <= height - 1:
            die("course_rows entries must be y-offsets inside the wall",
                {"course_rows": "ints in 0..%d" % (height - 1)})
    if not 0 <= float(p["vine_pct"]) <= 50:
        die("vine_pct out of range", {"vine_pct": "0-50"})
    if not 0 <= float(p["patch_pct"]) <= 30:
        die("patch_pct out of range", {"patch_pct": "0-30 (0=off)"})
    pm = str(p["patch_material"])
    if pm and not pm.startswith("minecraft:"):
        die("patch_material must be a minecraft: block id", {"patch_material": "minecraft:oak_planks"})
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,64,100]"})


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
            {"example": '{"origin":[100,64,100],"facing":"south","width":9,"height":6,"preset":"stone_brick_aged"}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
