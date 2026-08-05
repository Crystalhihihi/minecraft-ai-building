#!/usr/bin/env python3
"""round_plan.py — 圆环墙/收分圆顶 (tapered round tower wall) generator.

Emits a circular-plan wall as stacked single-cell rings that shrink by
`taper` per layer (0 = straight cylinder, 1 = classic tower, 2+ = steeper
cone). Every ring is a connected circle (patterns/ellipse.py circle_ring —
shared rasterization, 禁止各写一份). Optional flat cap (`cap`) seals the top
with a filled disc; without it the top ring stays open (for a crenellation /
roof / turret stack on top).

Deterministic, all geometry derived from origin+params (禁止手改方向状态).
Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python round_plan.py --params '{"origin":[100,80,100],"radius":4,"height":6,"taper":1}' [--out tower.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import write_out
from ellipse import circle_ring, disc

DEFAULTS = {
    "origin": [0, 64, 0],        # [x,y,z] centre cell of the base ring at ground y
    "radius": 4,                 # base ring radius, 2-15
    "height": 6,                 # wall layers, 2-16
    "taper": 1,                  # radius shrink per layer, 0-3
    "material": "minecraft:smooth_quartz",
    "cap_material": "minecraft:smooth_quartz",  # top cap disc ("" = leave open)
    "cap": True,                 # seal the top with a filled disc
    "solid": True,               # fill the interior disc each layer (support)
}

def build(p):
    ox, oy, oz = p["origin"]
    radius = max(2, min(15, int(p["radius"])))
    height = max(2, min(16, int(p["height"])))
    taper = max(0, min(3, int(p["taper"])))
    mat = p["material"]
    solid = p.get("solid", True)
    blocks = []
    base = radius
    for y in range(height):
        r = max(1, base - taper * y)
        # a tapered ring's new diagonal cells would float over the layer below
        # (the ring offsets are not nested); a solid interior disc guarantees
        # support. Hollow straight cylinders use taper=0 + solid=false.
        cells = disc(r, r) if solid else circle_ring(r)
        for dx, dz in cells:
            blocks.append({"x": ox + dx, "y": oy + y, "z": oz + dz, "block": mat})
    if p.get("cap", True) and p.get("cap_material") and not solid:
        top_r = max(1, base - taper * (height - 1))
        for dx, dz in disc(top_r, top_r):
            if not any(b["x"] == ox + dx and b["y"] == oy + height - 1
                       and b["z"] == oz + dz for b in blocks):
                blocks.append({"x": ox + dx, "y": oy + height - 1,
                               "z": oz + dz, "block": p["cap_material"]})
    return blocks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    p = dict(DEFAULTS)
    p.update(json.loads(a.params) if a.params.strip() else {})
    write_out(build(p), a.out)

if __name__ == "__main__":
    main()
