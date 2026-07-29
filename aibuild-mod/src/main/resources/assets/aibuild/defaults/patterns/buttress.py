#!/usr/bin/env python3
"""buttress.py — stepped buttress (扶壁) against a wall.

A 1-wide stepped pier sticking out from a wall face: deepest at the bottom,
tapering to 1 at the top (classic 3-2-1 profile). Output: {"blocks":[...]}.

Usage:
  python buttress.py --params '{"origin":[100,64,100],"side":"south","height":10}' [--out b.json]
"""
import argparse, json, sys

DEFAULTS = {
    "origin": [0, 64, 0],   # [x,y,z] the wall-face block column the buttress leans on, at ground level
    "side": "south",        # which way the buttress sticks OUT: north/south/east/west
    "height": 10,           # total height in blocks
    "depth": 3,             # projection at the base (2-4)
    "material": "minecraft:stone_bricks"
}

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}

def build(p):
    ox, oy, oz = p["origin"]
    h = max(2, int(p["height"]))
    depth = max(2, min(4, int(p["depth"])))
    dx, dz = DIRS[p["side"]]
    mat = p["material"]
    blocks = []
    for y in range(h):
        proj = max(1, depth - int(y * depth / h))  # 3-2-1 taper
        for k in range(1, proj + 1):
            blocks.append({"x": ox + dx * k, "y": oy + y, "z": oz + dz * k, "block": mat})
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
