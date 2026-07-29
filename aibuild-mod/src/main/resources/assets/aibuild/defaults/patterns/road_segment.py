#!/usr/bin/env python3
"""road_segment.py — straight road segment with camber, ditches and material gradient.

Cross-section (width 3-7, symmetric):
  center column(s): full block at y+camber  (crown / 路拱)
  mid columns:      full block at y, top slab on top when camber=1 (half-height step)
  edge columns:     full block at y
  ditch (optional): 1-wide, 1-deep trench at y-1 on both sides
Surface materials graduate center -> edge and vary per column via a
deterministic coordinate hash (no two stretches identical, always reproducible).
Output: {"blocks":[...]}.

Usage:
  python road_segment.py --params '{"origin":[100,64,100],"direction":"x","length":20}' [--out r.json]
"""
import argparse, json, sys

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] start corner: min x AND min z end of the road centerline at ground level
    "direction": "x",              # "x" (runs east) or "z" (runs south)
    "length": 16,
    "width": 3,                    # 3-7, odd numbers read best
    "camber": 1,                   # 0 = flat, 1 = crowned center (路拱, half-block steps)
    "ditch": 1,                    # 1 = dig 1-deep side ditches (边沟)
    "surface_materials": ["minecraft:gravel", "minecraft:dirt_path", "minecraft:coarse_dirt"],
    "center_material": "minecraft:dirt_path",
    "edge_material": "minecraft:stone",
    "ditch_material": "minecraft:gravel",
    "fill_material": "minecraft:dirt"
}

def h2(x, z):
    """Deterministic per-column hash -> [0,1)."""
    n = (x * 73428767) ^ (z * 91227153) ^ 0x5bd1e995
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65536.0

def build(p):
    ox, oy, oz = p["origin"]
    length, width = int(p["length"]), max(3, int(p["width"]))
    camber, ditch = int(p["camber"]), int(p["ditch"])
    mats = p["surface_materials"]
    half = width // 2
    blocks = []

    for t in range(length):
        for o in range(-half, half + 1):
            ao = abs(o)
            x, z = (ox + t, oz + o) if p["direction"] == "x" else (ox + o, oz + t)
            r = h2(x, z)
            # cross-section height profile
            if camber and width >= 3:
                if ao <= half - 2 or (half == 1 and ao == 0):
                    surf, top = oy + 1, None          # crown: raised full block
                elif ao == half - (0 if width % 2 == 0 else 1) and ao == half:
                    surf, top = oy, None
                else:
                    surf, top = oy, oy + 1            # mid: block + top slab (half step)
            else:
                surf, top = oy, None
            # material gradient center -> edge, with per-column noise
            if ao == 0:
                block = p["center_material"]
            elif ao == half:
                block = p["edge_material"] if r < 0.7 else mats[int(r * len(mats)) % len(mats)]
            else:
                block = mats[int(r * len(mats)) % len(mats)]
            blocks.append({"x": x, "y": surf, "z": z, "block": block})
            blocks.append({"x": x, "y": surf - 1, "z": z, "block": p["fill_material"]})
            if top is not None and camber and ao != 0 and ao < half:
                slab = p["edge_material"]
                if not slab.endswith("_slab"):
                    slab = "minecraft:stone_slab"
                blocks.append({"x": x, "y": top, "z": z, "block": slab + "[type=top]"})
        if ditch:
            for o in (-half - 1, half + 1):
                x, z = (ox + t, oz + o) if p["direction"] == "x" else (ox + o, oz + t)
                if h2(x, z) < 0.85:  # ditch has occasional natural gaps
                    blocks.append({"x": x, "y": oy - 1, "z": z, "block": p["ditch_material"]})
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
