#!/usr/bin/env python3
"""pilaster.py — rhythmic pilasters (壁柱) along a wall face.

1-wide piers projecting 1-2 blocks out of a flat wall face at a fixed
spacing; both wall ends always get one. Optional base/capital segmentation
(材料分段): first block(s) base_material, top block capital_material, shaft
= material. projection=2 steps: lower third projects 2, upper part 1.
Output: {"blocks":[...]}.

Usage:
  python pilaster.py --params '{"origin":[100,64,100],"side":"south","wall_length":15,"spacing":4,"height":12}' [--out p.json]
"""
import argparse, json, sys

DEFAULTS = {
    "origin": [0, 64, 0],   # [x,y,z] one END of the wall face at ground level (the wall runs along the perpendicular axis)
    "side": "south",        # outward direction the pilasters project: north/south (wall runs x) / east/west (wall runs z)
    "wall_length": 15,
    "spacing": 4,           # blocks between pilaster columns (3-6 reads best)
    "projection": 1,        # 1 or 2 blocks out of the wall face
    "height": 12,
    "material": "minecraft:stone_bricks",
    "base_material": "",    # e.g. "minecraft:cobblestone": bottom block of each pilaster
    "capital_material": ""  # e.g. "minecraft:stripped_spruce_log": top block of each pilaster
}

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}

def build(p):
    ox, oy, oz = p["origin"]
    side = p["side"]
    dx, dz = DIRS[side]
    ux, uz = (1, 0) if side in ("south", "north") else (0, 1)  # wall run axis
    length = max(3, int(p["wall_length"]))
    spacing = max(2, int(p["spacing"]))
    proj = max(1, min(2, int(p["projection"])))
    h = max(2, int(p["height"]))
    mat, base, cap = p["material"], p["base_material"], p["capital_material"]
    # pilaster center positions: both ends + every `spacing` steps
    positions = {0, length - 1}
    t = spacing
    while t < length - 1:
        positions.add(t)
        t += spacing
    blocks = []
    for u in sorted(positions):
        for y in range(h):
            if proj == 2:
                depth = 2 if y < max(1, h // 3) else 1  # stepped: deep base, shallow shaft
            else:
                depth = 1
            block = mat
            if y == 0 and base:
                block = base
            elif y == h - 1 and cap:
                block = cap
            for k in range(1, depth + 1):
                blocks.append({"x": ox + ux * u + dx * k, "y": oy + y, "z": oz + uz * u + dz * k,
                               "block": block})
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
