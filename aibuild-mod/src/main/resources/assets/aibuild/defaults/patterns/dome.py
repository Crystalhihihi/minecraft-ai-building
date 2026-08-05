#!/usr/bin/env python3
"""dome.py — 穹顶 (dome) generator: hemisphere / paraboloid / onion profiles.

Layer-sliced dome (Minecraft Wiki "Curved roofs" 逐层切片法): every layer is
a circle whose radius r(y) the profile function shrinks with height; each
ring comes from patterns/ellipse.py circle_ring/disc (共用圆栅格化, 禁止各
写一份). hollow=true emits only the shell rings (内壁空); hollow=false fills
each layer's disc. The top layer is ALWAYS a solid disc (顶部收口实芯).
Optional rim ring (檐口环) at radius+1 on the base layer.

Deterministic; all geometry derived from origin+params. Vanilla 1.21 ids.
Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python dome.py --params '{"origin":[100,80,100],"radius":6,"profile":"hemisphere"}' [--out dome.json]
"""
import argparse, json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out
from ellipse import circle_ring, disc

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] 底圆心格; y = 底圈层
    "radius": 6,                   # 底半径(格), 2-15
    "profile": "hemisphere",       # hemisphere | paraboloid | onion
    "material": "minecraft:smooth_quartz",
    "hollow": True,                # true=壳体(每层只留环); false=实心盘
    "rim": True,                   # 底层檐口环(radius+1 一圈)
}

PROFILES = ("hemisphere", "paraboloid", "onion")

def layer_radii(profile, R):
    """Radius per layer, bottom -> top. All >= 1, first == R."""
    radii = []
    if profile == "hemisphere":
        h = R
        fn = lambda y: round(math.sqrt(max(0, R * R - y * y)))
    elif profile == "paraboloid":
        # 缓凸浅穹顶 (segmented 思路): 高度压扁到 ~0.7R, 接墙更缓
        h = max(2, round(R * 0.7))
        fn = lambda y: round(R * math.sqrt(max(0.0, 1.0 - y / h)))
    else:  # onion 洋葱头: 中部鼓出 ~1.35R 再收尖, 总高 ~1.5R
        h = max(3, round(R * 1.5))
        def fn(y):
            t = y / h
            return round(R * math.sqrt(max(0.0, 1.0 - t * t))
                         * (1.0 + 0.45 * math.sin(math.pi * t)))
    for y in range(0, h + 1):
        r = int(fn(y))
        if y == 0:
            r = R
        if r < 1:
            break
        radii.append(max(1, r))
    return radii

def shell_cells(r):
    """Ring + 对角孤立格的径向补厚 (中点环在八分圆交界有 8 连通跳格,
    同层无 4 邻会被 support_check 判悬空; 向圆心补一格同材质即可)."""
    cells = set(circle_ring(r))
    for dx, dz in list(cells):
        if not any((dx + a, dz + b) in cells
                   for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            if abs(dx) >= abs(dz) and dx != 0:
                cells.add((dx - (1 if dx > 0 else -1), dz))
            else:
                cells.add((dx, dz - (1 if dz > 0 else -1)))
    return sorted(cells)

def build(p):
    ox, oy, oz = p["origin"]
    R = int(p["radius"])
    mat = p["material"]
    hollow = bool(p.get("hollow", True))
    radii = layer_radii(p["profile"], R)
    blocks = []
    last = len(radii) - 1
    for y, r in enumerate(radii):
        # 顶部收口实芯: 最上层永远用实心盘封死; 壳体其余层只留环
        cells = disc(r, r) if (not hollow or y == last) else shell_cells(r)
        for dx, dz in cells:
            blocks.append({"x": ox + dx, "y": oy + y, "z": oz + dz, "block": mat})
    if p.get("rim", True):
        for dx, dz in shell_cells(R + 1):
            blocks.append({"x": ox + dx, "y": oy, "z": oz + dz, "block": mat})
    return blocks

def validate(p):
    if p["profile"] not in PROFILES:
        die("profile must be one of %s" % (PROFILES,), {"profile": list(PROFILES)})
    try:
        r = int(p["radius"])
    except (TypeError, ValueError):
        die("radius must be an int", {"radius": "2-15"})
    if not 2 <= r <= 15:
        die("radius %s out of range" % r, {"radius": "2-15"})
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,80,100]"})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    p = dict(DEFAULTS)
    try:
        p.update(json.loads(a.params) if a.params.strip() else {})
    except json.JSONDecodeError as e:
        die("--params is not valid JSON: %s" % e,
            {"example": '{"origin":[100,80,100],"radius":6,"profile":"onion"}'})
    validate(p)
    write_out(build(p), a.out)

if __name__ == "__main__":
    main()
