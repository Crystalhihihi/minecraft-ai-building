#!/usr/bin/env python3
"""hip_roof.py — parametric hip roof (四坡顶) generator.

All four sides slope up to a ridge (rectangular footprint) or a point (square).
Stairs only + ridge slabs. Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python hip_roof.py --params '{"origin":[100,80,100],"width":9,"depth":7}' [--out roof.json]
"""
import argparse, json, math, sys

DEFAULTS = {
    "origin": [0, 64, 0],
    "width": 9,
    "depth": 7,
    "height": 0,                   # 0 = auto 45deg from the shorter span
    "overhang": 1,
    "material": "minecraft:deepslate_tile_stairs",
    "ridge_material": "minecraft:deepslate_tile_slab",
    "ridge_support": "minecraft:deepslate_tiles"  # solid beam under the ridge slab (E8 实测:侧放支撑楼梯留半格缝)
}

def stair(base, facing, shape=None):
    s = "%s[facing=%s,half=bottom" % (base, facing)
    if shape:
        s += ",shape=" + shape
    return s + "]"

# Corner shape intents for a hip ring (derived from vanilla stair bending:
# front stair perpendicular -> outer corner; left/right by counter-clockwise).
# The mod may re-derive `shape` at placement time — these are intents; what
# matters here is that facing/half are geometrically correct.
CORNER_SHAPE = {
    "nw": "outer_left",   # x0,z0 row facing south
    "ne": "outer_right",  # x1,z0 row facing south
    "sw": "outer_right",  # x0,z1 row facing north
    "se": "outer_left",   # x1,z1 row facing north
}

def top_slab(base):
    return "%s[type=top]" % base if base.endswith("_slab") else base

def build(p):
    ox, oy, oz = p["origin"]
    w, d = int(p["width"]), int(p["depth"])
    oh = max(0, int(p["overhang"]))
    tw, td = w + 2 * oh, d + 2 * oh
    max_inset = min(tw, td) // 2
    # height beyond max_inset (= the 45-degree rise) is impossible with
    # stairs: clamp. round() so consecutive layers never share an inset.
    height = int(p["height"]) or max(1, max_inset)
    height = max(1, min(height, max_inset))
    mat, ridge = p["material"], p["ridge_material"]
    beam = p.get("ridge_support", "minecraft:deepslate_tiles")
    blocks = []

    def ridge_cap(x, y, z, facing):
        # SOLID beam under the ridge top slab — a sideways support stair
        # leaves a half-gap on its open side (E8 实测 "还是悬空").
        # skipped when the cap sits on the wall top (y==oy, wall supports it)
        if y > oy:
            blocks.append({"x": ox + x, "y": y - 1, "z": oz + z, "block": beam})
        blocks.append({"x": ox + x, "y": y, "z": oz + z, "block": top_slab(ridge)})

    top = None  # (y, x0, x1, z0, z1) of the last emitted ring
    for i in range(height):
        inset = round(i * max_inset / height)
        y = oy + i
        x0, x1 = -oh + inset, tw - 1 - oh - inset
        z0, z1 = -oh + inset, td - 1 - oh - inset
        if x0 > x1 or z0 > z1:
            break
        top = (y, x0, x1, z0, z1)
        if x0 == x1 and z0 == z1:
            ridge_cap(x0, y, z0, "east")
        elif z0 == z1:
            for x in range(x0, x1 + 1):  # collapsed to the ridge line
                ridge_cap(x, y, z0, "east")
        elif x0 == x1:
            for z in range(z0, z1 + 1):
                ridge_cap(x0, y, z, "south")
        else:
            for x in range(x0, x1 + 1):
                # north row (facing south): corners get outer-curve intent
                if x == x0:
                    blocks.append({"x": ox + x, "y": y, "z": oz + z0, "block": stair(mat, "south", CORNER_SHAPE["nw"])})
                elif x == x1:
                    blocks.append({"x": ox + x, "y": y, "z": oz + z0, "block": stair(mat, "south", CORNER_SHAPE["ne"])})
                else:
                    blocks.append({"x": ox + x, "y": y, "z": oz + z0, "block": stair(mat, "south")})
                # south row (facing north)
                if x == x0:
                    blocks.append({"x": ox + x, "y": y, "z": oz + z1, "block": stair(mat, "north", CORNER_SHAPE["sw"])})
                elif x == x1:
                    blocks.append({"x": ox + x, "y": y, "z": oz + z1, "block": stair(mat, "north", CORNER_SHAPE["se"])})
                else:
                    blocks.append({"x": ox + x, "y": y, "z": oz + z1, "block": stair(mat, "north")})
            for z in range(z0 + 1, z1):
                blocks.append({"x": ox + x0, "y": y, "z": oz + z, "block": stair(mat, "east")})
                blocks.append({"x": ox + x1, "y": y, "z": oz + z, "block": stair(mat, "west")})
    # steeper-than-45 roof (height < max_inset): cap the open top ring's
    # interior with a flat slab lid so the roof is always closed.
    if top is not None:
        y, x0, x1, z0, z1 = top
        if x1 - x0 >= 2 and z1 - z0 >= 2:
            for x in range(x0 + 1, x1):
                for z in range(z0 + 1, z1):
                    ridge_cap(x, y, z, "east")
    return blocks

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
        print("wrote %d blocks to %s" % (len(json.loads(out)["blocks"]), a.out), file=sys.stderr)
    else:
        print(out)

if __name__ == "__main__":
    main()
