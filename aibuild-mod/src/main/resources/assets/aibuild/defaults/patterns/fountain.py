#!/usr/bin/env python3
"""fountain.py — parametric fountain (喷泉) generator.

Classic community recipe distilled into parameters:
- ground basin: full floor disc at y, water one layer deep at y+1, a full
  rim ring at water level (y+1) and a lip on top (y+2): upside-down stairs
  facing outward (flat walkable edge, the classic) or a flat slab ring;
- center pillar (wall/fence column is the classic; full blocks work too)
  rising from the basin floor — it replaces the center water cell, so it
  always stands on the floor;
- upper tiers (tiers=2..3): smaller basins stacked on the pillar, each =
  floor disc + upside-down-stair lip + 1-deep water, radius shrinking by
  `shrink` per tier, spacing = tier_height+2 layers between basin floors;
- one water source on the pillar top; in-game it cascades tier by tier
  into the ground basin.

Shapes: circle (midpoint-style disc test) or square. ALL stair facing/half/
corner states are derived by the script (backs outward, half=top; corners
auto-resolved by roof_common.Builder) — never hand-edit (禁止手改方向状态).

Output: {"blocks":[{x,y,z,block}...]} compatible with set_blocks_from_file.

Usage:
  python fountain.py --params '{"origin":[100,64,100],"radius":5,"tiers":2}' [--out f.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import Builder, die, slab, stair, write_out

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] CENTER cell of the basin; y = basin floor layer
    "shape": "circle",             # circle | square
    "radius": 5,                   # outer rim radius (circle) / half-size (square), 3-8
    "tiers": 1,                    # basin count, 1-3
    "tier_height": 3,              # pillar layers visible above each basin's water, 2-5
    "shrink": 0.5,                 # radius multiplier per upper tier, 0.3-0.7
    "rim_material": "minecraft:stone_bricks",
    "floor_material": "minecraft:stone_bricks",
    "trim": "stairs",              # stairs (lip) | slab (flat cap) | none
    "trim_material": "minecraft:stone_brick_stairs",
    "pillar_material": "minecraft:stone_brick_wall",   # wall/fence column = the classic
    "water": True
}

SHAPES = ("circle", "square")
TRIMS = ("stairs", "slab", "none")


def disc(r, shape):
    """Cell offsets of the filled disc/square of radius r, plus its rim subset."""
    cells, rim = [], set()
    R = r + 0.5 if shape == "circle" else r
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            inside = (dx * dx + dz * dz <= R * R) if shape == "circle" \
                else max(abs(dx), abs(dz)) <= r
            if inside:
                cells.append((dx, dz))
    cellset = set(cells)
    for dx, dz in cells:
        if any((dx + a, dz + b) not in cellset
               for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            rim.add((dx, dz))
    return cells, rim


def outward(dx, dz):
    """Cardinal direction away from the center (for lip stairs)."""
    if abs(dx) >= abs(dz):
        return "east" if dx > 0 else "west"
    return "south" if dz > 0 else "north"


def basin(b, y, r, shape, floor_mat, lip_mat, water, pillar_mat, pillar_top):
    """One basin: floor disc at y, water + stair lip at y+1, pillar through
    the center up to pillar_top (inclusive)."""
    cells, rim = disc(r, shape)
    for dx, dz in cells:
        b.put(dx, y, dz, floor_mat)
    for dx, dz in cells:
        if (dx, dz) == (0, 0):
            continue                      # pillar cell
        if water and (dx, dz) not in rim:
            b.put(dx, y + 1, dz, "minecraft:water")
    for dx, dz in rim:
        b.put(dx, y + 1, dz, stair(lip_mat, outward(dx, dz), half="top"))
    for yy in range(y + 1, pillar_top + 1):
        b.put(0, yy, 0, pillar_mat)
    return y + 2                          # layer above water/lip


def build(p):
    shape = p["shape"]
    radius, tiers = int(p["radius"]), int(p["tiers"])
    tier_h = int(p["tier_height"])
    shrink = float(p["shrink"])
    water = bool(p["water"])
    b = Builder()                              # local frame: basin floor at y=0

    # ---- ground basin: floor at y0, full rim ring at y0+1, water y0+1 ----
    cells, rim = disc(radius, shape)
    for dx, dz in cells:
        b.put(dx, 0, dz, p["floor_material"])
    for dx, dz in rim:
        b.put(dx, 1, dz, p["rim_material"])
        trim = p["trim"]
        if trim == "stairs":
            b.put(dx, 2, dz, stair(p["trim_material"], outward(dx, dz), half="top"))
        elif trim == "slab":
            base = p["trim_material"].replace("_stairs", "_slab")
            if not base.endswith("_slab"):
                base = "minecraft:stone_brick_slab"
            b.put(dx, 2, dz, slab(base, "bottom"))
    if tiers == 1:
        pillar_top = 1 + tier_h
    else:
        pillar_top = (tiers - 1) * (tier_h + 2) + 1
    for dx, dz in cells:
        if (dx, dz) != (0, 0) and water and (dx, dz) not in rim:
            b.put(dx, 1, dz, "minecraft:water")
    # pillar base segment: basin floor -> first upper floor (or top if 1 tier)
    seg_top = pillar_top if tiers == 1 else tier_h + 1
    for yy in range(1, seg_top + 1):
        b.put(0, yy, 0, p["pillar_material"])

    # ---- upper tiers on the pillar ----
    for i in range(1, tiers):
        ri = max(1, round(radius * (shrink ** i)))
        fi = i * (tier_h + 2)                   # this tier's floor layer
        basin(b, fi, ri, shape, p["floor_material"], p["trim_material"],
              water, p["pillar_material"], pillar_top)

    if water:
        b.put(0, pillar_top + 1, 0, "minecraft:water")   # source on top -> cascade
    return b.emit(p["origin"])


def validate(p):
    try:
        radius, tiers, tier_h = int(p["radius"]), int(p["tiers"]), int(p["tier_height"])
        shrink = float(p["shrink"])
    except (TypeError, ValueError):
        die("radius/tiers/tier_height must be ints, shrink a float",
            {"radius": "3-8", "tiers": "1-3", "tier_height": "2-5", "shrink": "0.3-0.7"})
    if not 3 <= radius <= 8:
        die("radius out of range", {"radius": "3-8"})
    if not 1 <= tiers <= 3:
        die("tiers out of range", {"tiers": "1-3"})
    if not 2 <= tier_h <= 5:
        die("tier_height out of range", {"tier_height": "2-5"})
    if not 0.3 <= shrink <= 0.7:
        die("shrink out of range", {"shrink": "0.3-0.7"})
    if p["shape"] not in SHAPES:
        die("shape must be one of %s" % (SHAPES,), {"shape": list(SHAPES)})
    if p["trim"] not in TRIMS:
        die("trim must be one of %s" % (TRIMS,), {"trim": list(TRIMS)})
    if p["trim"] == "stairs" and not str(p["trim_material"]).endswith("_stairs"):
        die("trim_material must be a *_stairs id when trim=stairs",
            {"trim_material": ["minecraft:stone_brick_stairs", "minecraft:quartz_stairs",
                               "minecraft:sandstone_stairs"]})
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
            {"example": '{"origin":[100,64,100],"radius":5,"tiers":2}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
