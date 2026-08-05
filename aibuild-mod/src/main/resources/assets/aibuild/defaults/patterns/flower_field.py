#!/usr/bin/env python3
"""flower_field.py — parametric flower field / flower bed (花海/花境).

Color schemes (community bedding techniques, parameterized):
- single:  one flower, solid drifts;
- stripes: bands of `band_width` rows along z cycling the palette (条带);
- gradient: palette sweeps across the width (渐变);
- meadow:  deterministic hash scatter from the palette (混色撒点).

Every cell gets a ground block at y (grass; path cells get path_material),
flowers sit at y+1 with probability `density` (deterministic per-column
hash — reproducible, no two runs differ). Cells within `edge_fade` of the
border get density x0.25 so the field thins out instead of ending with a
hard edge (边缘收束). `path` cuts dirt-path lanes through the field
(小径穿插): cross = one lane each way through the middle, grid = lanes
every 4 cells. Tall flowers (sunflower/lilac/rose_bush/peony) emit their
two-half blocks automatically.

Upgrade (all default to the legacy behavior, old callers unchanged):
- undergrowth: 地被三层法 — each non-path column is hashed into one of
  four layers: flower / grass tuft (草丛, some tall_grass) / fern (蕨) /
  empty (空), instead of the flat density coin-flip;
- companion: "花:草:蕨:空" ratio string (e.g. "6:3:1:0") setting the layer
  shares when undergrowth is on (density still scales the whole cover);
- scatter: 散置 density (0-0.5) of stones (cobblestone) and deadwood
  (fallen logs, axis by hash) on columns that stayed empty.

Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python flower_field.py --params '{"origin":[100,64,100],"width":16,"depth":12,"scheme":"stripes"}' [--out f.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] min corner; y = GROUND layer (flowers at y+1)
    "width": 12,                   # along x, 4-32
    "depth": 12,                   # along z, 4-32
    "scheme": "meadow",            # single | stripes | gradient | meadow
    "flowers": ["minecraft:poppy", "minecraft:dandelion",
                "minecraft:cornflower", "minecraft:azure_bluet"],
    "density": 0.6,                # 0.1-1.0
    "band_width": 2,               # stripe thickness in rows, 1-4
    "path": "none",                # none | cross | grid
    "edge_fade": 1,                # 0-3: border band where density drops to x0.25
    "ground_material": "minecraft:grass_block",
    "path_material": "minecraft:dirt_path",
    "gap_fill": "grass",           # grass (short_grass on empty cells) | none
    "undergrowth": False,          # 地被三层法: flower / grass tuft / fern / empty layers
    "companion": "6:3:1:0",        # 花:草:蕨:空 ratio (only with undergrowth=true)
    "scatter": 0.0                 # 0-0.5: stones/deadwood on columns that stayed empty
}

SCHEMES = ("single", "stripes", "gradient", "meadow")
PATHS = ("none", "cross", "grid")
FLOWERS = {
    "minecraft:dandelion", "minecraft:poppy", "minecraft:blue_orchid",
    "minecraft:allium", "minecraft:azure_bluet", "minecraft:red_tulip",
    "minecraft:orange_tulip", "minecraft:white_tulip", "minecraft:pink_tulip",
    "minecraft:oxeye_daisy", "minecraft:cornflower",
    "minecraft:lily_of_the_valley", "minecraft:sunflower", "minecraft:lilac",
    "minecraft:rose_bush", "minecraft:peony",
}
TALL = ("sunflower", "lilac", "rose_bush", "peony")


def h2(x, z):
    """Deterministic per-column hash -> [0,1)."""
    n = (x * 73428767) ^ (z * 91227153) ^ 0x5bd1e995
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65536.0


def is_path(x, z, w, d, mode):
    if mode == "cross":
        return x == w // 2 or z == d // 2
    if mode == "grid":
        return x % 4 == 0 or z % 4 == 0
    return False


def pick(p, x, z, w):
    palette, n = p["flowers"], len(p["flowers"])
    scheme = p["scheme"]
    if scheme == "single":
        return palette[0]
    if scheme == "stripes":
        return palette[(z // max(1, int(p["band_width"]))) % n]
    if scheme == "gradient":
        return palette[min(n - 1, int(x * n / w))]
    return palette[int(h2(x * 3 + 11, z * 5 + 7) * n) % n]   # meadow


def parse_companion(s):
    """'花:草:蕨:空' ratio string -> 4 cumulative normalized thresholds."""
    parts = str(s).split(":")
    if len(parts) != 4:
        raise ValueError
    v = [int(x) for x in parts]
    if any(x < 0 for x in v) or sum(v) <= 0:
        raise ValueError
    total = float(sum(v))
    acc, out = 0.0, []
    for x in v:
        acc += x / total
        out.append(acc)
    return out                                # (F, F+G, F+G+E, 1.0)


def build(p):
    ox, oy, oz = p["origin"]
    w, d = int(p["width"]), int(p["depth"])
    density, fade = float(p["density"]), int(p["edge_fade"])
    ug = p["undergrowth"]
    comp = parse_companion(p["companion"]) if ug else None
    scatter = float(p["scatter"])
    blocks = []
    for z in range(d):
        for x in range(w):
            path = is_path(x, z, w, d, p["path"])
            blocks.append({"x": ox + x, "y": oy, "z": oz + z,
                           "block": p["path_material"] if path else p["ground_material"]})
            if path:
                continue
            edge = min(x, z, w - 1 - x, d - 1 - z)
            eff = density * (0.25 if edge < fade else 1.0)
            r = h2(ox + x, oz + z)
            placed = False
            if ug:
                # 地被三层法: one hash splits the column into the 4 layers
                m = density * (0.25 if edge < fade else 1.0)
                f, g, e = comp[0] * m, comp[1] * m, comp[2] * m
                if r < f:
                    placed = put_flower(blocks, p, ox + x, oy, oz + z, x, z, w)
                elif r < g:
                    if h2(ox + x * 7 + 3, oz + z * 7 + 1) < 0.2:
                        blocks.append({"x": ox + x, "y": oy + 1, "z": oz + z,
                                       "block": "minecraft:tall_grass[half=lower]"})
                        blocks.append({"x": ox + x, "y": oy + 2, "z": oz + z,
                                       "block": "minecraft:tall_grass[half=upper]"})
                    else:
                        blocks.append({"x": ox + x, "y": oy + 1, "z": oz + z,
                                       "block": "minecraft:short_grass"})
                    placed = True
                elif r < e:
                    blocks.append({"x": ox + x, "y": oy + 1, "z": oz + z,
                                   "block": "minecraft:fern"})
                    placed = True
            else:
                if r < eff:
                    placed = put_flower(blocks, p, ox + x, oy, oz + z, x, z, w)
                elif p["gap_fill"] == "grass" and r < eff + 0.5 * density:
                    blocks.append({"x": ox + x, "y": oy + 1, "z": oz + z,
                                   "block": "minecraft:short_grass"})
                    placed = True
            if not placed and scatter > 0.0:
                s = h2(ox + x * 13 + 5, oz + z * 11 + 3)
                if s < scatter:
                    if h2(ox + x * 3 + 1, oz + z * 3 + 9) < 0.5:
                        blocks.append({"x": ox + x, "y": oy + 1, "z": oz + z,
                                       "block": "minecraft:cobblestone"})
                    else:
                        axis = "x" if h2(ox + x, oz + z * 17 + 7) < 0.5 else "z"
                        blocks.append({"x": ox + x, "y": oy + 1, "z": oz + z,
                                       "block": "minecraft:oak_log[axis=%s]" % axis})
    return blocks


def put_flower(blocks, p, wx, wy, wz, x, z, w):
    flower = pick(p, x, z, w)
    if any(t in flower for t in TALL):
        blocks.append({"x": wx, "y": wy + 1, "z": wz,
                       "block": flower + "[half=lower]"})
        blocks.append({"x": wx, "y": wy + 2, "z": wz,
                       "block": flower + "[half=upper]"})
    else:
        blocks.append({"x": wx, "y": wy + 1, "z": wz, "block": flower})
    return True


def validate(p):
    try:
        w, d = int(p["width"]), int(p["depth"])
        density = float(p["density"])
    except (TypeError, ValueError):
        die("width/depth must be ints, density a float",
            {"width": "4-32", "depth": "4-32", "density": "0.1-1.0"})
    if not (4 <= w <= 32 and 4 <= d <= 32):
        die("width/depth out of range", {"width": "4-32", "depth": "4-32"})
    if not 0.1 <= density <= 1.0:
        die("density out of range", {"density": "0.1-1.0"})
    if p["scheme"] not in SCHEMES:
        die("scheme must be one of %s" % (SCHEMES,), {"scheme": list(SCHEMES)})
    if p["path"] not in PATHS:
        die("path must be one of %s" % (PATHS,), {"path": list(PATHS)})
    if p["gap_fill"] not in ("grass", "none"):
        die("gap_fill must be grass|none", {"gap_fill": ["grass", "none"]})
    if not isinstance(p["undergrowth"], bool):
        die("undergrowth must be true|false", {"undergrowth": [True, False]})
    try:
        parse_companion(p["companion"])
    except (TypeError, ValueError):
        die("companion must be '花:草:蕨:空' non-negative int ratios",
            {"companion": "6:3:1:0"})
    try:
        scatter = float(p["scatter"])
    except (TypeError, ValueError):
        die("scatter must be a float 0-0.5", {"scatter": "0-0.5"})
    if not 0.0 <= scatter <= 0.5:
        die("scatter out of range", {"scatter": "0-0.5"})
    if not isinstance(p["flowers"], list) or not p["flowers"]:
        die("flowers must be a non-empty list", {"flowers": ["minecraft:poppy"]})
    bad = [f for f in p["flowers"] if f not in FLOWERS]
    if bad:
        die("unknown flower ids: %s" % bad, {"flowers": sorted(FLOWERS)})
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
            {"example": '{"origin":[100,64,100],"width":16,"depth":12,"scheme":"stripes"}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
