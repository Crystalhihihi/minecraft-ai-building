#!/usr/bin/env python3
"""xieshan_roof.py — 歇山顶 (Chinese hip-and-gable roof) generator.

Chinese gable-and-hip roof: a hip (四坡) lower section whose four corners
recede inward, then an upper gable (双坡) section whose two end faces become
VERTICAL gable walls (山花). Ridge runs along x. Output is a
set_blocks_from_file-compatible JSON: {"blocks":[{x,y,z,block}...]}.

All stair/slab facing + corner shapes are DERIVED by the script — never
hand-edit facing/half/shape in the output (禁止手改方向状态).

Usage:
  python xieshan_roof.py --params '{"origin":[100,80,100],"width":9,"depth":13}' [--out roof.json]
"""
import argparse, json, math, sys

DEFAULTS = {
    "origin": [0, 64, 0],           # [x,y,z] NW corner of the wall footprint; y = roof base layer
    "width": 9,                     # wall footprint along x (ridge direction)
    "depth": 13,                    # wall footprint along z (slope direction)
    "height": 0,                    # 0 = auto (45-degree from z span)
    "hip_height": 2,                # layers of the lower 4-slope receding section
    "overhang": 1,                  # eaves past the wall line
    "material": "minecraft:deepslate_tile_stairs",
    "ridge_material": "minecraft:deepslate_tile_slab",
    "ridge_support": "minecraft:deepslate_tiles",   # solid beam under ridge slab (E8 实测)
    # FIX 2026-08-03: default was "" (open gables) but the card JSON default
    # is deepslate_tiles — running per the card's example left the gable ends
    # wide open. Align code default with the card so "run the example" is sane.
    "end_fill": "minecraft:deepslate_tiles"  # gable wall (山花) fill material; "" = open
}

CORNER_SHAPE = {
    "nw": "outer_left",   # x=xn, z=zn row facing south
    "ne": "outer_right",  # x=xs, z=zn row facing south
    "sw": "outer_right",  # x=xn, z=zs row facing north
    "se": "outer_left",   # x=xs, z=zs row facing north
}

def stair(base, facing, shape=None):
    s = "%s[facing=%s,half=bottom" % (base, facing)
    if shape:
        s += ",shape=" + shape
    return s + "]"

def top_slab(base):
    return "%s[type=top]" % base if base.endswith("_slab") else base

def build(p):
    ox, oy, oz = p["origin"]
    w, d = int(p["width"]), int(p["depth"])
    oh = max(0, int(p["overhang"]))
    total_w, total_d = w + 2 * oh, d + 2 * oh
    half = total_d / 2.0
    auto_h = max(1, math.ceil(half))
    # FIX 2026-08-03: was `max(1, min(height, auto_h))` which clamped any
    # explicit larger height back to auto — so "explicit height = shallower"
    # (per the card notes) silently did nothing. Now height may be larger than
    # auto for a shallower pitch (inset per layer shrinks); a height smaller
    # than auto is still geometrically impossible with stairs, so keep the
    # lower bound at auto (steepest allowed = 45deg).
    height = int(p["height"]) or auto_h
    height = max(auto_h, height)
    hip_h = max(0, int(p.get("hip_height", 2)))
    hip_h = min(hip_h, height - 1) if height > 1 else 0
    mat, ridge, fill = p["material"], p["ridge_material"], p["end_fill"]
    beam = p.get("ridge_support", "minecraft:deepslate_tiles")
    blocks = []

    def emit(x, y, z, block):
        blocks.append({"x": ox + x, "y": y, "z": oz + z, "block": block})

    top = None
    for i in range(height):
        inset_z = round(i * half / height)
        y = oy + i
        zn = -oh + inset_z
        zs = total_d - 1 - oh - inset_z
        if zn > zs:
            break
        # x extent stays at FULL wall width: the slope recedes only along z.
        xn, xs = -oh, total_w - 1 - oh
        top = (y, zn, zs, xn, xs)
        if zn == zs:
            # ridge line: solid beam + slab
            for x in range(xn, xs + 1):
                if y > oy:
                    emit(x, y - 1, zn, beam)
                emit(x, y, zn, top_slab(ridge))
        else:
            # N/S slope rows across the full x width, corners get hip shape
            for x in range(xn, xs + 1):
                if x == xn:
                    emit(x, y, zn, stair(mat, "south", CORNER_SHAPE["nw"]))
                    emit(x, y, zs, stair(mat, "north", CORNER_SHAPE["sw"]))
                elif x == xs:
                    emit(x, y, zn, stair(mat, "south", CORNER_SHAPE["ne"]))
                    emit(x, y, zs, stair(mat, "north", CORNER_SHAPE["se"]))
                else:
                    emit(x, y, zn, stair(mat, "south"))
                    emit(x, y, zs, stair(mat, "north"))
            if zs - zn >= 2:
                if i < hip_h:
                    # lower hip section: the x-end is a SLOPE (receding corners)
                    for z in range(zn + 1, zs):
                        emit(xn, y, z, stair(mat, "east"))
                        emit(xs, y, z, stair(mat, "west"))
                elif fill:
                    # upper gable section: the x-end is a VERTICAL gable wall (山花)
                    for z in range(zn + 1, zs):
                        emit(xn, y, z, fill)
                        emit(xs, y, z, fill)
    # close any still-open top interior with a flat slab lid (roof must be sealed)
    if top is not None:
        y, zn, zs, xn, xs = top
        if zs - zn >= 2:
            for x in range(xn, xs + 1):
                for z in range(zn + 1, zs):
                    emit(x, y, z, top_slab(ridge))
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
