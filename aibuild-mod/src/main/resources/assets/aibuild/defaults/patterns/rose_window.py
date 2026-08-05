#!/usr/bin/env python3
"""rose_window.py — 哥特玫瑰窗 (rose window) generator.

径向对称组合光栅化 (Grafix Arts / UCLA 画法): 外圈石框环 + N 根辐条 +
中心毂 + 玻璃填充, 全部圆/盘来自 patterns/ellipse.py (圆算法单一来源,
禁止各写一份). 窗体嵌进墙面: 窗面在墙外皮层(v=0, 替换墙块), 并向墙内
carve `depth` 格 minecraft:air 窗洞 (air 开凿学 dormer — 没有 place_air
能力时先手工挖掉对应墙块再放置).

Canonical frame: 窗面朝 south, u -> +x (面外看向右), v -> -z (进墙);
再按 facing 旋转. 无楼梯/半砖方向状态, 全确定性.

Usage:
  python rose_window.py --params '{"origin":[100,80,100],"facing":"south","radius":5}' [--out rose.json]
"""
import argparse, json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import Builder, FACING_ROT, die, write_out
from ellipse import circle_ring, disc

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] 窗心格(墙外皮层), y = 窗心层
    "facing": "south",             # 墙外法线: 窗朝向
    "radius": 5,                   # 外圈半径(格), 3-12
    "spokes": 8,                   # 辐条数, 4-16
    "frame_material": "minecraft:stone_bricks",
    "glass_material": "minecraft:red_stained_glass",
    "depth": 1,                    # 向墙内开凿的窗洞深度, 1-3
}

FACINGS = ("north", "south", "east", "west")

def ring_cells(r):
    """外圈环 + 对角孤立格的径向补厚 (中点环在八分圆交界有 8 连通跳格,
    孤立格外侧是空气、内侧超出玻璃盘, 会被 support_check 判悬空)."""
    cells = set(circle_ring(r))
    for dx, dy in list(cells):
        if not any((dx + a, dy + b) in cells
                   for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            if abs(dx) >= abs(dy) and dx != 0:
                cells.add((dx - (1 if dx > 0 else -1), dy))
            else:
                cells.add((dx, dy - (1 if dy > 0 else -1)))
    return cells

def build(p):
    r = int(p["radius"])
    spokes = int(p["spokes"])
    depth = int(p["depth"])
    frame, glass = p["frame_material"], p["glass_material"]
    rot, fmap = FACING_ROT[p["facing"]]
    b = Builder(rot=rot, fmap=fmap)

    frame_cells = ring_cells(r)              # 外圈石框(含补厚)
    frame_cells |= set(disc(1, 1))             # 中心毂(十字 5 格)
    for k in range(spokes):                    # N 重径向对称辐条
        a = 2 * math.pi * k / spokes
        for d in range(2, r):
            frame_cells.add((round(d * math.cos(a)), round(d * math.sin(a))))
    for du, dy in sorted(frame_cells):
        b.put(du, dy, 0, frame)
    for du, dy in disc(r - 1, r - 1):          # 玻璃填充(辐条/毂优先)
        if (du, dy) not in frame_cells:
            b.put(du, dy, 0, glass)
    for v in range(1, depth + 1):              # 窗洞开凿进墙(让位于窗体)
        for du, dy in disc(r, r):
            b.carve(du, dy, v)
    return b.emit(p["origin"])

def validate(p):
    if p["facing"] not in FACINGS:
        die("facing must be one of %s" % (FACINGS,), {"facing": list(FACINGS)})
    try:
        r, s, d = int(p["radius"]), int(p["spokes"]), int(p["depth"])
    except (TypeError, ValueError):
        die("radius/spokes/depth must be ints", {"radius": "3-12", "spokes": "4-16", "depth": "1-3"})
    if not 3 <= r <= 12:
        die("radius %s out of range" % r, {"radius": "3-12"})
    if not 4 <= s <= 16:
        die("spokes %s out of range" % s, {"spokes": "4-16"})
    if not 1 <= d <= 3:
        die("depth %s out of range" % d, {"depth": "1-3"})
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
            {"example": '{"origin":[100,80,100],"facing":"south","radius":5}'})
    validate(p)
    write_out(build(p), a.out)

if __name__ == "__main__":
    main()
