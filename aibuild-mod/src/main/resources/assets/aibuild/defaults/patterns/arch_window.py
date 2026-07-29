#!/usr/bin/env python3
"""arch_window.py — arched window unit (拱窗) for a flat wall plane.

Two sizes: 1x2 (arrow slit) and 2x3 (proper arch). Glass panes fill the
opening; the top row is upside-down stairs for the arch head; optional sill.
Output: {"blocks":[...]} in the wall plane (facing = outward direction).

Usage:
  python arch_window.py --params '{"origin":[100,70,100],"size":"2x3","facing":"south"}' [--out w.json]
"""
import argparse, json, sys

DEFAULTS = {
    "origin": [0, 64, 0],               # [x,y,z] bottom-LEFT cell of the opening (seen from outside)
    "size": "1x2",                      # "1x2" or "2x3"
    "facing": "south",                  # outward direction of the wall face
    "glass": "minecraft:glass_pane",
    "frame_material": "minecraft:stone_brick_stairs",  # arch head (upside-down stairs)
    "sill_material": ""                 # e.g. "minecraft:stone_brick_slab": slab row under the window
}

def arch_stair(base, facing):
    return "%s[facing=%s,half=top]" % (base, facing)

def build(p):
    ox, oy, oz = p["origin"]
    w, h = (1, 2) if p["size"] == "1x2" else (2, 3)
    facing = p["facing"]
    horiz = facing in ("south", "north")   # opening runs along x; else along z
    blocks = []

    def cell(i, dy):
        return (ox + i, oy + dy, oz) if horiz else (ox, oy + dy, oz + i)

    for i in range(w):
        for dy in range(h):
            x, y, z = cell(i, dy)
            if dy == h - 1:
                blocks.append({"x": x, "y": y, "z": z, "block": arch_stair(p["frame_material"], facing)})
            else:
                blocks.append({"x": x, "y": y, "z": z, "block": p["glass"]})
    if p["sill_material"]:
        sill = p["sill_material"]
        if sill.endswith("_slab"):
            sill += "[type=bottom]"
        for i in range(w):
            x, y, z = cell(i, -1)
            blocks.append({"x": x, "y": y, "z": z, "block": sill})
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
