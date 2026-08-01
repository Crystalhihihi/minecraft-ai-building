#!/usr/bin/env python3
"""helm_roof.py — parametric helm roof (盔顶) generator for square towers.

A helm (Rhenish helm) is a square roof with FOUR gable ends. Recipe per the
wiki, ground-truthed against the stair rules:
- every stair faces only TWO directions (north rows face south, south rows
  face north — four-direction helms are "very fiddly" and read badly);
- each layer is a filled square, inset 1 on all sides per layer, so every
  face of the pyramid shows a triangle = four gables;
- the middle row(s) of each layer are SLABS (type=top) — the wiki's "slabs
  are usually needed under the main roof blocks" seam fix; they stack on the
  layer below, so no floating-slab holes;
- odd widths come to a point (single seam row + apex); even widths get a
  2-row seam (wiki: works better odd; even allowed here).

Output: {"blocks":[{x,y,z,block}...]}. ALL direction/shape states derived;
never hand-edit (禁止手改方向状态).

Usage:
  python helm_roof.py --params '{"origin":[100,80,100],"width":7}' [--out roof.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import Builder, die, require_suffix, stair, slab, write_out

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] NW corner of the TOWER footprint; y = first layer above the walls
    "width": 7,                    # square tower width, 3-21; odd comes to a point (recommended)
    "overhang": 1,                 # eaves past the wall line (0-2)
    "material": "minecraft:dark_oak_stairs",
    "ridge_material": "minecraft:dark_oak_slab",
    "spire_material": "",          # e.g. "minecraft:spruce_fence"; "" = no spire
    "spire_height": 0              # 0-2 fence layers on the apex (odd widths only)
}

def build(p):
    ox, oy, oz = p["origin"]
    w = int(p["width"])
    oh = max(0, int(p["overhang"]))
    mat, ridgem = p["material"], p["ridge_material"]
    s0 = w + 2 * oh
    b = Builder()

    apex = None                    # (x, y, z) of the top cell, for the spire
    i = 0
    while s0 - 2 * i >= 1:
        lo, hi = i, s0 - 1 - i
        y = oy + i
        span = hi - lo + 1
        midlo = (lo + hi) // 2
        midhi = midlo if span % 2 == 1 else midlo + 1  # even span: 2-row seam
        for z in range(lo, hi + 1):
            for x in range(lo, hi + 1):
                if midlo <= z <= midhi:
                    # base-course seam = double slab (full block, sits on the
                    # wall line — a lone top slab there fails the hole check)
                    b.put(x, y, z, slab(ridgem, "double" if i == 0 else "top"))
                elif z < midlo:
                    b.put(x, y, z, stair(mat, "south"))
                else:
                    b.put(x, y, z, stair(mat, "north"))
        apex = (midlo, y, midlo)
        i += 1

    if p["spire_material"] and int(p["spire_height"]) > 0:
        ax, ay, az = apex
        for k in range(1, int(p["spire_height"]) + 1):
            b.put(ax, ay + k, az, p["spire_material"])
    return b.emit([ox - oh, 0, oz - oh])  # local (0,0) = the -oh eave corner; y absolute

def validate(p):
    try:
        w = int(p["width"])
        oh = int(p["overhang"])
    except (TypeError, ValueError):
        die("width/overhang must be ints", {"width": "3-21", "overhang": "0-2"})
    if not 3 <= w <= 21:
        die("width %s out of range" % w,
            {"width": "3-21", "recommended": "odd: 5, 7, 9, 11 (comes to a point)"})
    if not 0 <= oh <= 2:
        die("overhang out of range", {"overhang": [0, 1, 2]})
    if p["spire_material"] and int(p["spire_height"]) > 0:
        if (w + 2 * oh) % 2 == 0:
            die("spire needs a single apex cell = odd total width",
                {"legal_width_for_spire": "odd width with this overhang, e.g. 5/7/9",
                     "alternative": "spire_height 0"})
        if not 0 < int(p["spire_height"]) <= 2:
            die("spire_height out of range", {"spire_height": [0, 1, 2]})
        if "fence" not in str(p["spire_material"]) and "wall" not in str(p["spire_material"]):
            die("spire_material should be a fence/wall id",
                {"spire_material": ["minecraft:spruce_fence", "minecraft:dark_oak_fence",
                                    "minecraft:cobblestone_wall"]})
    require_suffix(p, "material", "_stairs",
                   ["minecraft:dark_oak_stairs", "minecraft:spruce_stairs",
                    "minecraft:deepslate_tile_stairs"])
    require_suffix(p, "ridge_material", "_slab",
                   ["minecraft:dark_oak_slab", "minecraft:spruce_slab",
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
        die("--params is not valid JSON: %s" % e,
            {"example": '{"origin":[100,80,100],"width":7,"material":"minecraft:dark_oak_stairs"}'})
    validate(p)
    write_out(build(p), a.out)

if __name__ == "__main__":
    main()
