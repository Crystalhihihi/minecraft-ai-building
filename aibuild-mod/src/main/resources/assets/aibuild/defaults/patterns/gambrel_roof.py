#!/usr/bin/env python3
"""gambrel_roof.py — parametric gambrel roof (折线屋顶) generator.

Two pitches per slope, steep lower / shallow upper (wiki: "steep lower down,
and shallow or flat higher up" — the barn/Dutch-Colonial profile). At MC
scale a real curve reads as noise (Curved roofs: radius < ~6 m just looks
like mixed pitches), so the gambrel is built from straight segments:
- steep segment: stacked stair pairs (bottom + upside-down, 2 y per 1 inset,
  ~63 degrees, the stair_orientations.md stacked-trim trick);
- shallow segment: stair + top-slab pairs (1 y per 2 columns, ~27 degrees);
  every top slab is carried by a support stair directly below (validators
  flag floating top slabs — stairs are exempt, slabs are not).

Output: {"blocks":[{x,y,z,block}...]}. ALL direction states derived from
origin+params; never hand-edit (禁止手改方向状态).

Usage:
  python gambrel_roof.py --params '{"origin":[100,80,100],"width":9,"depth":11}' [--out roof.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import Builder, die, require_suffix, stair, slab, write_out

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] NW corner of the WALL footprint; y = roof base layer
    "width": 9,                    # wall footprint along x
    "depth": 11,                   # wall footprint along z (the slope span)
    "lower_rise": 2,               # steep lower segment: stacked-pair layers (2 y each)
    "upper_rise": 2,               # shallow upper segment: stair+slab layers (1 y per 2 columns)
    "overhang": 1,                 # eaves past the wall line (0-2)
    "axis": "x",                   # ridge axis: "x" or "z"
    "material": "minecraft:spruce_stairs",
    "ridge_material": "minecraft:spruce_slab",
    "ridge": True,                 # cap the meeting line with a ridge slab row
    "end_fill": ""                 # e.g. "minecraft:oak_planks": solid gambrel-end walls inside the footprint
}

def build(p):
    ox, oy, oz = p["origin"]
    w, d = int(p["width"]), int(p["depth"])
    oh = max(0, int(p["overhang"]))
    h1, h2 = int(p["lower_rise"]), int(p["upper_rise"])
    mat, ridgem, fill = p["material"], p["ridge_material"], p["end_fill"]
    axis = p.get("axis", "x")
    if axis == "z":
        w, d = d, w
    T = d + 2 * oh
    S = T // 2                       # slope columns per side
    rem = S - (h1 + 2 * h2)
    b = Builder()

    def emit(x, y, z, block):
        if axis == "z":
            x, z = z, x
        b.put(x, y, z, block)

    def has(x, y, z):
        if axis == "z":
            x, z = z, x
        return b.has(x, y, z)

    ytop = oy + 2 * h1 + h2 + (1 if rem == 1 else 0)  # top walking surface level

    def slope_row(rel, y, kind):
        """One profile column at relative distance rel from each eave.
        kind: 'stair' | 'pair' (stacked steep pair) | 'slab' (shallow tread).
        Spans the full ridge-parallel length; mirrored on both slopes."""
        for x in range(-oh, w + oh):
            zn = -oh + rel                # north slope column (ascends +z)
            zs = T - 1 - oh - rel         # south slope column (ascends -z)
            if kind == "pair":
                emit(x, y, zn, stair(mat, "south"))
                emit(x, y + 1, zn, stair(mat, "south", half="top"))
                emit(x, y, zs, stair(mat, "north"))
                emit(x, y + 1, zs, stair(mat, "north", half="top"))
            elif kind == "stair":
                emit(x, y, zn, stair(mat, "south"))
                emit(x, y, zs, stair(mat, "north"))
            else:  # slab tread + support stair below
                emit(x, y, zn, slab(mat.replace("_stairs", "_slab"), "top"))
                emit(x, y - 1, zn, stair(mat, "south"))
                emit(x, y, zs, slab(mat.replace("_stairs", "_slab"), "top"))
                emit(x, y - 1, zs, stair(mat, "north"))

    # ---- profile: steep stacked pairs, then shallow stair+slab pairs ------
    for k in range(h1):
        slope_row(k, oy + 2 * k, "pair")
    r = h1
    for j in range(h2):
        y = oy + 2 * h1 + j
        if r + 1 <= S - 1:
            slope_row(r, y, "stair")
            slope_row(r + 1, y, "slab")
            r += 2
        else:                             # odd leftover: single stair column
            slope_row(r, y, "stair")
            r += 1
    if rem == 1:                          # undershoot by one: curb single step
        slope_row(r, oy + 2 * h1 + h2, "stair")

    # ---- closure at the meeting line --------------------------------------
    if T % 2 == 1:
        zmid = -oh + S                    # shared middle ridge column
        for x in range(-oh, w + oh):
            emit(x, ytop - 2, zmid, stair(mat, "south"))       # hidden support
            emit(x, ytop - 1, zmid, slab(ridgem, "top"))       # flush seam
            if p["ridge"]:
                emit(x, ytop, zmid, slab(ridgem, "bottom"))
    elif p["ridge"]:
        for x in range(-oh, w + oh):      # two knife-edge columns get caps
            emit(x, ytop, -oh + S - 1, slab(ridgem, "bottom"))
            emit(x, ytop, T - oh - S, slab(ridgem, "bottom"))

    # ---- optional gambrel-end walls (inside the wall footprint) -----------
    if fill:
        for y in range(oy, ytop):
            for x in (0, w - 1):
                for z in range(0, d):
                    if not has(x, y, z):
                        emit(x, y, z, fill)
    return b.emit([ox, 0, oz])  # y already absolute (computed from oy)

def legal_pairs(S):
    """(lower_rise, upper_rise) combos that close the span: h1+2*h2 in {S-1, S}."""
    out = []
    for a in range(1, S):
        for bb in range(1, S):
            if a + 2 * bb in (S - 1, S):
                out.append([a, bb])
    return out

def validate(p):
    try:
        w, d = int(p["width"]), int(p["depth"])
        h1, h2 = int(p["lower_rise"]), int(p["upper_rise"])
        oh = int(p["overhang"])
    except (TypeError, ValueError):
        die("width/depth/lower_rise/upper_rise/overhang must be ints",
            {"width": "3-31", "depth": "3-31", "lower_rise": ">=1", "upper_rise": ">=1", "overhang": "0-2"})
    if not 3 <= w <= 31 or not 3 <= d <= 31:
        die("width/depth out of range", {"width": "3-31", "depth": "3-31"})
    if not 0 <= oh <= 2:
        die("overhang out of range", {"overhang": [0, 1, 2]})
    if p.get("axis", "x") not in ("x", "z"):
        die("axis must be x or z", {"axis": ["x", "z"]})
    span = d + 2 * oh if p.get("axis", "x") == "x" else w + 2 * oh
    S = span // 2
    pairs = legal_pairs(S)
    if h1 < 1 or h2 < 1 or h1 + 2 * h2 > S or S - (h1 + 2 * h2) > 1:
        die("lower_rise=%d, upper_rise=%d does not close the span "
            "(need lower_rise+2*upper_rise in {%d, %d}; a gambrel needs both "
            "pitches)" % (h1, h2, S - 1, S),
            {"legal_[lower_rise,upper_rise]_for_this_span": pairs})
    require_suffix(p, "material", "_stairs",
                   ["minecraft:spruce_stairs", "minecraft:dark_oak_stairs",
                    "minecraft:deepslate_tile_stairs"])
    require_suffix(p, "ridge_material", "_slab",
                   ["minecraft:spruce_slab", "minecraft:dark_oak_slab",
                    "minecraft:deepslate_tile_slab"])
    if not str(p["material"]).replace("_stairs", "_slab").endswith("_slab"):
        die("cannot derive slab id from material", {"material": "minecraft:spruce_stairs"})
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
            {"example": '{"origin":[100,80,100],"width":9,"depth":11,"lower_rise":2,"upper_rise":2}'})
    validate(p)
    write_out(build(p), a.out)

if __name__ == "__main__":
    main()
