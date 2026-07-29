#!/usr/bin/env python3
"""window_trim.py — window surround / trim frame (窗套) around an opening.

A decorative ring around a window opening: side jambs + header + sill rows.
projection=0 puts the trim in the wall plane (replaces wall blocks flanking
the opening); projection=1 hangs it one block OUT of the wall face. The four
ring corners use corner_material (角件) when set. Output: {"blocks":[...]}.

Usage:
  python window_trim.py --params '{"origin":[100,70,100],"width":2,"height":3,"facing":"south","projection":1}' [--out t.json]
"""
import argparse, json, sys

DEFAULTS = {
    "origin": [0, 64, 0],               # [x,y,z] bottom-LEFT cell of the window OPENING, seen from outside
    "width": 2,                         # opening width
    "height": 3,                        # opening height
    "facing": "south",                  # outward direction of the wall face
    "projection": 1,                    # 0 = in the wall plane, 1 = one block out of the face
    "material": "minecraft:dark_oak_planks",
    "corner_material": "",              # e.g. "minecraft:smooth_stone": the 4 ring corners (角件)
    "sill_material": ""                 # e.g. "minecraft:stone_brick_slab": bottom row becomes slabs
}

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}

def build(p):
    ox, oy, oz = p["origin"]
    w, h = int(p["width"]), int(p["height"])
    facing = p["facing"]
    dx, dz = DIRS[facing]
    ux, uz = (1, 0) if facing in ("south", "north") else (0, 1)  # along-wall axis
    proj = max(0, min(1, int(p["projection"])))
    mat, corner, sill = p["material"], p["corner_material"], p["sill_material"]
    blocks = []

    def emit(u, v, block):
        blocks.append({
            "x": ox + ux * u + dx * proj,
            "y": oy + v,
            "z": oz + uz * u + dz * proj,
            "block": block})

    def ring_block(u, v):
        is_corner = (u in (-1, w)) and (v in (-1, h))
        if is_corner and corner:
            return corner
        if v == -1 and sill:
            s = sill
            return s + "[type=bottom]" if s.endswith("_slab") else s
        return mat

    # ring spans u in [-1, w], v in [-1, h]: jambs at u=-1 and u=w,
    # header at v=h, sill at v=-1
    for v in range(-1, h + 1):
        for u in (-1, w):
            emit(u, v, ring_block(u, v))
    for u in range(0, w):
        emit(u, h, ring_block(u, h))     # header row
        emit(u, -1, ring_block(u, -1))   # sill row
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
