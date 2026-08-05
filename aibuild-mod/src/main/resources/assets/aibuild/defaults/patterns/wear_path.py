#!/usr/bin/env python3
"""wear_path.py — 踩出来的路 (worn desire-path) generator.

Two endpoints, one living path: the straight line is broken by 1-2 seeded
perpendicular bends (直角折线=死气, 带弯=活), rasterized with Bresenham so
diagonals read naturally. 主材 dirt_path; `wear` levels:
- light: pure dirt_path spine;
- heavy: 中段 (t 0.25~0.75) 35% 掺 podzol/coarse_dirt (踩秃了).
edge_fade 收边: ring-1 neighbours get coarse_dirt/gravel (heavy 更密),
ring-2 gets sparse coarse_dirt — 渐稀收边, 不是硬切边. All randomness from
`seed` (确定性). Flat ground assumed: y = from[1] everywhere; 起伏地形先
terraform_pad. Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python wear_path.py --params '{"from":[100,64,100],"to":[116,64,109],"width":1,"wear":"heavy","seed":5}' [--out path.json]
"""
import argparse, json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out

DEFAULTS = {
    "from": [0, 64, 0],            # [x,y,z] 起点格; y = 路面层(平地假设)
    "to": [12, 64, 3],             # [x,y,z] 终点格
    "width": 1,                    # 1-2
    "wear": "light",               # light | heavy
    "seed": 7
}

WEARS = ("light", "heavy")


def _line(p0, p1):
    """Bresenham 栅格化 (含端点)."""
    x0, z0 = p0
    x1, z1 = p1
    dx, dz = abs(x1 - x0), abs(z1 - z0)
    sx = 1 if x0 < x1 else -1
    sz = 1 if z0 < z1 else -1
    err = dx - dz
    cells = []
    while True:
        cells.append((x0, z0))
        if (x0, z0) == (x1, z1):
            return cells
        e2 = 2 * err
        if e2 > -dz:
            err -= dz
            x0 += sx
        if e2 < dx:
            err += dx
            z0 += sz


def build(p):
    fx, fy, fz = [int(v) for v in p["from"]]
    tx, _, tz = [int(v) for v in p["to"]]
    width = int(p["width"])
    heavy = p["wear"] == "heavy"
    rng = random.Random(int(p["seed"]))
    dx, dz = tx - fx, tz - fz
    cheb = max(abs(dx), abs(dz))

    # 1-2 个弯: 中点垂直偏移, 符号非零 => 永不退化成直线/直角折线
    ts = [0.5] if cheb < 12 else [1.0 / 3, 2.0 / 3]
    way = [(fx, fz)]
    for t in ts:
        bx, bz = fx + t * dx, fz + t * dz
        mag = rng.randint(1, min(4, max(1, cheb // 4))) * rng.choice((-1, 1))
        way.append((round(bx - dz * mag / cheb), round(bz + dx * mag / cheb)))
    way.append((tx, tz))

    spine = []
    for a, b in zip(way, way[1:]):
        for c in _line(a, b):
            if not spine or spine[-1] != c:
                spine.append(c)

    # width=2: 沿主走向的法向加一条并行列 (侧向由 seed 定)
    side = None
    if width == 2:
        off = (0, rng.choice((-1, 1))) if abs(dx) >= abs(dz) \
            else (rng.choice((-1, 1)), 0)
        side = {(x + off[0], z + off[1]) for x, z in spine}
    path = set(spine) | (side or set())

    blocks = {}
    n = len(spine)
    for i, (x, z) in enumerate(spine):
        t = i / max(1, n - 1)
        block = "minecraft:dirt_path"
        if heavy and 0.25 <= t <= 0.75:
            r = rng.random()
            if r < 0.35:
                block = "minecraft:podzol" if r < 0.17 else "minecraft:coarse_dirt"
        blocks[(x, z)] = block
    if side is not None:           # 并行列同材质 (取各自最近 spine 段)
        off_cells = {}
        for (x, z) in side:
            if (x, z) not in blocks:
                # 最近的 spine 格材质
                near = min(spine, key=lambda c: abs(c[0] - x) + abs(c[1] - z))
                off_cells[(x, z)] = blocks[near]
        blocks.update({k: v for k, v in off_cells.items() if k not in blocks})

    # edge_fade: 贴边 1 圈 coarse_dirt/gravel, 第 2 圈稀疏 coarse_dirt
    p1 = 0.6 if heavy else 0.45
    ring1 = set()
    for x, z in path:
        for ddx, ddz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            c = (x + ddx, z + ddz)
            if c not in path:
                ring1.add(c)
    for c in sorted(ring1):
        r = rng.random()
        if r < p1:
            blocks[c] = "minecraft:coarse_dirt"
        elif r < p1 + 0.15:
            blocks[c] = "minecraft:gravel"
    ring2 = set()
    for x, z in ring1:
        for ddx, ddz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            c = (x + ddx, z + ddz)
            if c not in path and c not in ring1:
                ring2.add(c)
    for c in sorted(ring2):
        if rng.random() < 0.15:
            blocks.setdefault(c, "minecraft:coarse_dirt")

    return [{"x": x, "y": fy, "z": z, "block": b}
            for (x, z), b in sorted(blocks.items())]


def validate(p):
    try:
        f = [int(v) for v in p["from"]]
        t = [int(v) for v in p["to"]]
    except (TypeError, ValueError):
        die("from/to must be [x,y,z] ints", {"from": "[100,64,100]", "to": "[116,64,109]"})
    if len(f) != 3 or len(t) != 3:
        die("from/to must be [x,y,z]", {"from": "[100,64,100]", "to": "[116,64,109]"})
    cheb = max(abs(t[0] - f[0]), abs(t[2] - f[2]))
    if not 3 <= cheb <= 64:
        die("path length (Chebyshev) out of range", {"from,to": "3-64 cells apart"})
    try:
        w = int(p["width"])
    except (TypeError, ValueError):
        die("width must be an int", {"width": "1-2"})
    if w not in (1, 2):
        die("width out of range", {"width": "1-2"})
    if p["wear"] not in WEARS:
        die("wear must be one of %s" % (WEARS,), {"wear": list(WEARS)})
    try:
        int(p["seed"])
    except (TypeError, ValueError):
        die("seed must be an int", {"seed": 7})


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
            {"example": '{"from":[100,64,100],"to":[116,64,109],"wear":"heavy"}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
