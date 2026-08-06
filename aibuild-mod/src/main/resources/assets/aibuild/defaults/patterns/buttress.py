#!/usr/bin/env python3
"""buttress.py — buttress (扶壁) against a wall, two variants.

- stepped (default): a 1-wide stepped pier sticking out from a wall face,
  deepest at the bottom, tapering to 1 at the top (classic 3-2-1 profile).
- flying: flying buttress (飞扶壁) for gothic churches — a freestanding pier
  2-3 cells off the wall, with a sloped arch arm springing from the pier top
  up to the wall attachment point, plus an optional pinnacle on the pier.

Output: {"blocks":[...]}.

Usage:
  python buttress.py --params '{"origin":[100,64,100],"side":"south","height":10}' [--out b.json]
  python buttress.py --params '{"variant":"flying","origin":[100,64,100],"side":"south","wall_height":12,"pier_dist":3,"pier_height":8,"pinnacle":true}' [--out fb.json]
"""
import argparse, json, math, sys

DEFAULTS = {
    "variant": "stepped",   # "stepped" (default, original behaviour) | "flying"
    "origin": [0, 64, 0],   # [x,y,z] the wall-face block column the buttress leans on, at ground level
    "side": "south",        # which way the buttress sticks OUT: north/south/east/west
    "material": "minecraft:stone_bricks",
    # stepped
    "height": 10,           # total height in blocks
    "depth": 3,             # projection at the base (2-4)
    # flying
    "wall_height": 12,      # y-offset of the arch attachment point on the wall (arm tip at origin y + wall_height - 1)
    "pier_dist": 3,         # pier distance from the wall face (2-3 classic, clamped 2-4)
    "pier_height": 8,       # pier column height; must be < wall_height (clamped)
    "pinnacle": True        # small spire (post+post+stair tip) above the pier top
}

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


def rhu(v):
    """Round half up (deterministic)."""
    return int(math.floor(v + 0.5))


def vline(a, b):
    """Face-connected voxel cells from int cell a to b (3D Bresenham +
    L-corner inserts, so consecutive cells never touch only by an edge).
    Same idiom as giant_tree.vline."""
    (ax, ay, az), (bx, by, bz) = a, b
    n = max(abs(bx - ax), abs(by - ay), abs(bz - az))
    cells, (px, py, pz) = [(ax, ay, az)], (ax, ay, az)
    for i in range(1, n + 1):
        t = i / n
        cx, cy, cz = rhu(ax + (bx - ax) * t), rhu(ay + (by - ay) * t), rhu(az + (bz - az) * t)
        if (cx, cy, cz) == (px, py, pz):
            continue
        if cx != px and (cy != py or cz != pz):
            cells.append((cx, py, pz))          # x-first corner
        if cz != pz and cy != py:
            cells.append((cx, py, cz))          # then z
        cells.append((cx, cy, cz))
        px, py, pz = cx, cy, cz
    return cells


def build_stepped(p):
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


def _post_of(mat):
    """Pinnacle post derived from material (roof_ornament idiom): stone
    families taper with walls, wood with fences; fallback = material."""
    if "_bricks" in mat:
        return mat.replace("_bricks", "_brick_wall")
    if mat.endswith("_planks"):
        return mat[:-len("_planks")] + "_fence"
    return mat


def _stair_of(mat):
    """Stair block for the pinnacle tip; fallback = material."""
    if "_bricks" in mat:
        return mat.replace("_bricks", "_brick_stairs")
    if mat.endswith("_planks"):
        return mat[:-len("_planks")] + "_stairs"
    return mat


def build_flying(p):
    ox, oy, oz = p["origin"]
    dx, dz = DIRS[p["side"]]
    mat = p["material"]
    wall_h = max(4, int(p["wall_height"]))
    dist = max(2, min(4, int(p["pier_dist"])))
    pier_h = max(2, min(int(p["pier_height"]), wall_h - 1))
    blocks, seen = [], set()

    def put(x, y, z, block):
        if (x, y, z) not in seen:
            seen.add((x, y, z))
            blocks.append({"x": x, "y": y, "z": z, "block": block})

    px, pz = ox + dx * dist, oz + dz * dist
    # pier: 1x1 column from ground up
    for y in range(pier_h):
        put(px, oy + y, pz, mat)
    # arch arm: pier top -> wall attachment one cell off the wall face
    # (vline keeps the slope face-connected; the tip touches the wall sideways)
    a = (px, oy + pier_h - 1, pz)
    b = (ox + dx, oy + wall_h - 1, oz + dz)
    for x, y, z in vline(a, b):
        put(x, y, z, mat)
    # optional pinnacle above the pier top: post + post + stair tip (gothic finial)
    if p["pinnacle"]:
        post, tip = _post_of(mat), _stair_of(mat)
        put(px, oy + pier_h, pz, post)
        put(px, oy + pier_h + 1, pz, post)
        if tip.endswith("_stairs"):
            tip = "%s[facing=%s]" % (tip, p["side"])
        put(px, oy + pier_h + 2, pz, tip)
    return blocks


def build(p):
    if p["variant"] == "flying":
        return build_flying(p)
    return build_stepped(p)


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
