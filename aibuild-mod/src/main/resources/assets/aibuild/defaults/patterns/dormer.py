#!/usr/bin/env python3
"""dormer.py — parametric dormer (老虎窗) generator: gabled / shed / hipped.

A dormer is a small roofed window box that protrudes from a main roof slope.
This script emits the dormer BODY (front window wall + sill + mini roof +
cheeks) plus explicit minecraft:air cells that CARVE the window tunnel into
the main slope behind the wall — the opening must cut INTO the slope, not
sit on it. Output: {"blocks":[{x,y,z,block}...]} (set_blocks_from_file
compatible; air cells carve via place_air).

ALL direction states are DERIVED by the script from origin+params (canonical
frame: front faces south, u -> +x = viewer's right, v -> into the roof = -z;
then rotated to `facing`). Never hand-edit facing/half/shape in the output;
change params and re-run (禁止手改方向状态).

Usage:
  python dormer.py --params '{"origin":[100,80,100],"facing":"south","width":3,"variant":"gabled"}' [--out dormer.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import (Builder, FACING_ROT, die, require_suffix, stair,
                         slab, write_out)

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] bottom-LEFT cell of the window wall (seen from outside), y = wall base layer
    "facing": "south",             # direction the dormer faces (out of the roof, downhill)
    "width": 3,                    # window wall width, 2-4
    "variant": "gabled",           # gabled (狗屋双坡) | shed (单坡) | hipped (四坡)
    "depth": 2,                    # mini-roof depth into the slope, 1-4
    "wall_material": "minecraft:spruce_planks",
    "roof_material": "minecraft:spruce_stairs",
    "ridge_material": "minecraft:spruce_slab",
    "sill_material": "minecraft:spruce_stairs",
    "window_material": "minecraft:glass_pane",
    "cheeks": True                 # fill the side wedges down to the wall base (embeds into the slope)
}

VARIANTS = ("gabled", "shed", "hipped")
FACINGS = ("north", "south", "east", "west")

def window_cells(w):
    return {2: [0, 1], 3: [1], 4: [1, 2]}[w]

def build(p):
    w, depth = int(p["width"]), int(p["depth"])
    variant = p["variant"]
    wall, roofm = p["wall_material"], p["roof_material"]
    ridge, sill, win = p["ridge_material"], p["sill_material"], p["window_material"]
    cheeks = bool(p["cheeks"])
    rot, fmap = FACING_ROT[p["facing"]]
    b = Builder(rot=rot, fmap=fmap)
    wc = window_cells(w)

    # ---- front window wall (v=0), 2 high: sill row / window row ----------
    for u in range(w):
        if u in wc:
            b.put(u, 0, 0, stair(sill, "south", half="top"))  # sill ledge, face out
            b.put(u, 1, 0, win)                               # the window itself
        else:
            b.put(u, 0, 0, wall)
            b.put(u, 1, 0, wall)

    if variant == "gabled":
        # ridge runs along v; slopes step in along u; 45-degree: h = ceil(w/2)
        h = (w + 1) // 2
        for i in range(h):
            y = 2 + i
            ulo, uhi = i, w - 1 - i
            for v in range(-1, depth + 1):
                if ulo == uhi:                    # odd-width apex line
                    if v >= 0:
                        b.put(ulo, y, v, slab(ridge, "bottom"))
                    continue
                b.put(ulo, y, v, stair(roofm, "east"))
                b.put(uhi, y, v, stair(roofm, "west"))
                for u in range(ulo + 1, uhi):
                    if v == 0:
                        b.put(u, y, v, wall)      # gable triangle face
                    elif v > 0 and w % 2 == 1 and i == h - 2:
                        b.put(u, y, v, wall)      # support under the apex slab
        if cheeks:
            for v in range(1, depth + 1):
                for y in (0, 1):
                    b.put(0, y, v, wall)
                    b.put(w - 1, y, v, wall)

    elif variant == "shed":
        # header row closes the front, then a single slope rises into the roof
        for u in range(w):
            b.put(u, 2, 0, wall)
        for v in range(-1, depth):
            y = 2 + (v + 1)
            for u in range(w):
                b.put(u, y, v, stair(roofm, "north"))
        if cheeks:                                # stair-stepped side wedges
            for v in range(1, depth):
                for y in range(0, 3 + v):
                    b.put(0, y, v, wall)
                    b.put(w - 1, y, v, wall)

    else:  # hipped
        # eave ring at y=2 (overhangs all four sides), solid deck under cap
        for v in range(-1, depth + 1):
            for u in range(-1, w + 1):
                edge = u in (-1, w) or v in (-1, depth)
                if not edge:
                    b.put(u, 2, v, wall)          # deck fill (supports cap)
                    continue
                if v == -1:
                    b.put(u, 2, v, stair(roofm, "north"))
                elif v == depth:
                    b.put(u, 2, v, stair(roofm, "south"))
                elif u == -1:
                    b.put(u, 2, v, stair(roofm, "east"))
                else:
                    b.put(u, 2, v, stair(roofm, "west"))
        for v in range(0, depth):
            for u in range(0, w):
                b.put(u, 3, v, slab(ridge, "bottom"))  # shallow pyramid cap
        if cheeks:
            for v in range(1, depth):
                for y in (0, 1):
                    b.put(0, y, v, wall)
                    b.put(w - 1, y, v, wall)

    # ---- carve the window tunnel INTO the slope (the point of a dormer) ---
    # through the body and one cell past its back edge, so the window opens
    # into the attic, not onto roof skin left behind. Never carves the roof
    # skin itself (y=1 is always below the mini roof).
    for u in wc:
        for v in range(1, depth + 2):
            b.carve(u, 1, v, force=True)
    return b.emit(p["origin"])

def validate(p):
    if p["facing"] not in FACINGS:
        die("facing must be one of %s" % (FACINGS,), {"facing": list(FACINGS)})
    if p["variant"] not in VARIANTS:
        die("variant must be one of %s" % (VARIANTS,), {"variant": list(VARIANTS)})
    try:
        w, depth = int(p["width"]), int(p["depth"])
    except (TypeError, ValueError):
        die("width/depth must be ints", {"width": "2-4", "depth": "1-4"})
    if not 2 <= w <= 4:
        die("width %s out of range" % w, {"width": [2, 3, 4]})
    if not 1 <= depth <= 4:
        die("depth %s out of range" % depth, {"depth": "1-4"})
    require_suffix(p, "roof_material", "_stairs",
                   ["minecraft:spruce_stairs", "minecraft:dark_oak_stairs",
                    "minecraft:deepslate_tile_stairs"])
    require_suffix(p, "sill_material", "_stairs",
                   ["minecraft:spruce_stairs", "minecraft:dark_oak_stairs"])
    require_suffix(p, "ridge_material", "_slab",
                   ["minecraft:spruce_slab", "minecraft:dark_oak_slab",
                    "minecraft:deepslate_tile_slab"])
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,80,100]"})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}", help="JSON object of parameters")
    ap.add_argument("--out", default="", help="output file (default: stdout)")
    a = ap.parse_args()
    p = dict(DEFAULTS)
    try:
        p.update(json.loads(a.params) if a.params.strip() else {})
    except json.JSONDecodeError as e:
        die("--params is not valid JSON: %s" % e, {"example": '{"facing":"south","width":3,"variant":"gabled"}'})
    validate(p)
    write_out(build(p), a.out)

if __name__ == "__main__":
    main()
