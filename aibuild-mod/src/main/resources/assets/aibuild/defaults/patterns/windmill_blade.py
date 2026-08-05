#!/usr/bin/env python3
"""windmill_blade.py — 风车叶片 (windmill blades) generator: 4 叶 X 形/+ 形.

Classic Dutch-mill rotor in a vertical plane perpendicular to `facing`:
a centre hub (十字 5 格, ellipse.py disc — 圆算法单一来源) + axle cells
into the tower, and 4 spars at 90° intervals. Rotation angle is script
-derived from `variant` (x = 45° 起始, plus = 0° 起始, 禁止手改); each spar
is a 4-connected rasterized line ( Manhattan 补格, 斜叶无对角悬空), with an
optional one-cell-wide sail panel (蒙布半砖面, type=bottom slab) on the
trailing edge from 1/3 length outward.

Deterministic; vanilla 1.21 ids. Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python windmill_blade.py --params '{"origin":[100,80,100],"facing":"south","length":8}' [--out rotor.json]
"""
import argparse, json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import Builder, FACING_ROT, die, write_out
from ellipse import disc

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] 轮毂中心格, y = 轮毂层
    "facing": "south",             # 轴法线: 转子面朝的方向
    "length": 8,                   # 叶尖半径(格, 轮毂外沿到叶尖), 4-12
    "variant": "x",                # x = X 形(45° 起始) | plus = + 形
    "sail": True,                  # 蒙布半砖面; false = 裸骨架
    "frame_material": "minecraft:dark_oak_fence",
    "sail_material": "minecraft:smooth_quartz_slab",
}

FACINGS = ("north", "south", "east", "west")
VARIANTS = ("x", "plus")

def spar_line(du, dy):
    """4-connected raster cells from (0,0) to (du,dy), (0,0) excluded."""
    steps = max(abs(du), abs(dy))
    pts, prev = [], (0, 0)
    for s in range(1, steps + 1):
        u, y = round(du * s / steps), round(dy * s / steps)
        if u != prev[0] and y != prev[1]:
            pts.append((u, prev[1]))        # Manhattan 补格: 杜绝纯对角悬空
        pts.append((u, y))
        prev = (u, y)
    return pts

def build(p):
    L = int(p["length"])
    sail = bool(p.get("sail", True))
    frame = p["frame_material"]
    sailm = p["sail_material"]
    if sail and sailm.endswith("_slab"):
        sailm = sailm + "[type=bottom]"      # 蒙布半砖面: 下半砖, 拼缝同向
    rot, fmap = FACING_ROT[p["facing"]]
    b = Builder(rot=rot, fmap=fmap)

    for du, dy in disc(1, 1):                # 轮毂: 十字 5 格
        b.put(du, dy, 0, frame)
    b.put(0, 0, 1, frame)                    # 轴: 伸进塔身 2 格
    b.put(0, 0, 2, frame)

    base = 45.0 if p["variant"] == "x" else 0.0
    for i in range(4):
        a = math.radians(base + 90.0 * i)
        ca, sa = math.cos(a), math.sin(a)
        tip = (round(L * ca), round(L * sa))
        for d, (u, y) in enumerate(spar_line(*tip), start=1):
            b.put(u, y, 0, frame)
            if sail and d >= max(2, L // 3):
                # 后缘蒙布: 取切向的主导轴分量, 保证与骨架格面相邻(不悬空)
                tu, ty = -sa, ca
                if abs(tu) >= abs(ty):
                    off = (1 if tu > 0 else -1, 0)
                else:
                    off = (0, 1 if ty > 0 else -1)
                if not b.has(u + off[0], y + off[1], 0):
                    b.put(u + off[0], y + off[1], 0, sailm)
    return b.emit(p["origin"])

def validate(p):
    if p["facing"] not in FACINGS:
        die("facing must be one of %s" % (FACINGS,), {"facing": list(FACINGS)})
    if p["variant"] not in VARIANTS:
        die("variant must be one of %s" % (VARIANTS,), {"variant": list(VARIANTS)})
    try:
        L = int(p["length"])
    except (TypeError, ValueError):
        die("length must be an int", {"length": "4-12"})
    if not 4 <= L <= 12:
        die("length %s out of range" % L, {"length": "4-12"})
    if p.get("sail", True) and not str(p["sail_material"]).endswith("_slab"):
        die("sail_material must be a *_slab id",
            {"sail_material": ["minecraft:smooth_quartz_slab", "minecraft:spruce_slab"]})
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
            {"example": '{"origin":[100,80,100],"facing":"south","length":8,"variant":"x"}'})
    validate(p)
    write_out(build(p), a.out)

if __name__ == "__main__":
    main()
