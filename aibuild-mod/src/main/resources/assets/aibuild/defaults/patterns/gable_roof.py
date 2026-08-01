#!/usr/bin/env python3
"""gable_roof.py — parametric gable roof (人字顶) generator, V2.

Outputs a set_blocks_from_file-compatible JSON: {"blocks":[{x,y,z,block}...]}.
V2: every stair carries a geometrically DERIVED block state — each slope
row's facing points uphill toward the ridge (north slope rows face south,
south slope rows face north), half=bottom everywhere, ridge sealed with a
slab row, eaves on one slope share one facing. Do NOT hand-edit facings in
the output: the script derives them; fix params instead.
Stairs only (roof skin) + ridge slab; optional solid gable-end triangle fill.
A gable roof has no hip corners by geometry — for corner curve intents see
hip_roof.py.

Usage:
  python gable_roof.py --params '{"origin":[100,80,100],"width":7,"depth":9}' [--out roof.json]
All params optional; bare `python gable_roof.py` prints a demo roof to stdout.
"""
import argparse, json, math, re, sys

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] north-west corner of the WALL footprint; roof base layer y
    "width": 7,                    # wall footprint along x
    "depth": 9,                    # wall footprint along z
    "height": 0,                   # roof rise in layers; 0 = auto 45deg from span+overhang
    "overhang": 1,                 # eaves sticking out past the walls (0-2)
    "axis": "x",                   # ridge axis: "x" (ridge along x) or "z"
    "material": "minecraft:spruce_stairs",
    "ridge_material": "minecraft:spruce_slab",
    "end_fill": ""                 # e.g. "minecraft:oak_planks": solid gable-end triangles inside wall footprint
}

def stair(base, facing):
    return "%s[facing=%s,half=bottom]" % (base, facing)

def top_slab(base):
    return "%s[type=top]" % base if base.endswith("_slab") else base

def build(p):
    ox, oy, oz = p["origin"]
    oh = max(0, int(p["overhang"]))
    # normalize so the ridge runs along local x; swap for axis=z at the end
    w, d = int(p["width"]), int(p["depth"])
    if p.get("axis", "x") == "z":
        w, d = d, w
    total = d + 2 * oh
    half = total / 2.0
    # height beyond auto (= the 45-degree rise) is geometrically impossible
    # with stairs: clamp. round() (not int()) so consecutive layers never
    # share an inset (duplicate eave rows).
    auto_h = max(1, math.ceil(half))
    height = int(p["height"]) or auto_h
    height = max(1, min(height, auto_h))
    mat, ridge, fill = p["material"], p["ridge_material"], p["end_fill"]
    blocks = []

    # axis=z transposes local coords (local x -> world z); facing strings must
    # rotate with them: local +z -> world +x, local +x -> world +z.
    FACING_ROT = {"south": "east", "east": "south", "north": "west", "west": "north"}

    def emit(x, y, z, block):
        if p.get("axis", "x") == "z":
            x, z = z, x  # transpose back: local x -> world z
            block = re.sub(r"facing=(north|south|east|west)",
                           lambda m: "facing=" + FACING_ROT[m.group(1)], block)
        blocks.append({"x": ox + x, "y": y, "z": oz + z, "block": block})

    top_y, top_zn, top_zs = oy, None, None
    for i in range(height):
        inset = round(i * half / height)
        y = oy + i
        zn = -oh + inset                 # north eave row (ascends +z, faces south)
        zs = d - 1 + oh - inset          # south eave row (ascends -z, faces north)
        if zn > zs:
            break
        top_y, top_zn, top_zs = y, zn, zs
        for x in range(-oh, w + oh):
            if zn == zs:
                # ridge: hidden support stair under the top slab (no more
                # floating top slab / see-through gap, E7 漏空 fix).
                # skip when the ridge sits on the wall top (y==oy): the wall
                # itself is the support then.
                if y > oy:
                    emit(x, y - 1, zn, stair(mat, "east"))
                emit(x, y, zn, top_slab(ridge))
            else:
                emit(x, y, zn, stair(mat, "south"))
                emit(x, y, zs, stair(mat, "north"))
        if fill:
            g = max(0, inset - oh)
            for x in (0, w - 1):         # gable-end walls at the two wall faces
                for z in range(g, d - g):
                    if z not in (zn, zs):
                        emit(x, y, z, fill)
    # steeper-than-45 roof (height < auto): cap the still-open middle rows
    # with a flat ridge slab strip so the roof is always closed.
    if top_zn is not None and top_zn < top_zs:
        for x in range(-oh, w + oh):
            for z in range(top_zn, top_zs + 1):
                if top_y > oy:
                    emit(x, top_y - 1, z, stair(mat, "east"))
                emit(x, top_y, z, top_slab(ridge))
    return blocks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}", help="JSON object of parameters")
    ap.add_argument("--out", default="", help="output file (default: stdout)")
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
