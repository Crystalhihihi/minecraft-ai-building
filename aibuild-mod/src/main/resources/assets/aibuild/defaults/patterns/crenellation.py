#!/usr/bin/env python3
"""crenellation.py — battlement ring (垛口) along a wall-top rectangle.

Merlons placed along the perimeter of the given rectangle with a fixed
spacing rhythm; corners are always merlons. Output: {"blocks":[...]}.

Usage:
  python crenellation.py --params '{"origin":[100,86,100],"width":7,"depth":7}' [--out c.json]
"""
import argparse, json, sys

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] north-west corner of the WALL footprint, y = first layer above wall top
    "width": 7,
    "depth": 7,
    "material": "minecraft:stone_brick_wall",
    "spacing": 2,                  # every Nth perimeter step is a merlon (2 = merlon, gap, merlon, gap)
    "height": 1                    # merlon height in blocks
}

def build(p):
    ox, oy, oz = p["origin"]
    w, d = int(p["width"]), int(p["depth"])
    spacing = max(1, int(p["spacing"]))
    h = max(1, int(p["height"]))
    mat = p["material"]
    # perimeter walk order: north edge (x 0..w-1 at z=0), east edge, south edge, west edge
    ring = []
    for x in range(w):
        ring.append((x, 0))
    for z in range(1, d):
        ring.append((w - 1, z))
    if d > 1:
        for x in range(w - 2, -1, -1):
            ring.append((x, d - 1))
    if w > 1:
        for z in range(d - 2, 0, -1):
            ring.append((0, z))
    blocks = []
    for i, (x, z) in enumerate(ring):
        corner = (x in (0, w - 1)) and (z in (0, d - 1))
        if corner or i % spacing == 0:
            for dy in range(h):
                blocks.append({"x": ox + x, "y": oy + dy, "z": oz + z, "block": mat})
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
