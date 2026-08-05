#!/usr/bin/env python3
"""clutter_pile.py — 杂物堆生成器 (yard clutter piles), 治"无菌感".

四种随手堆 (kind):
- hay      干草堆: hay_block 错落簇 3-5 底 + 1-2 压顶, 轴向 seeded 随机
           (大多是立轴, 个别倒放 = 随手扔的);
- wood     柴木堆: 横放原木两层交叉码 (axis 逐层交替), 旁边再滚一根散的;
- firewood 劈柴垛: 单轴整齐码三排 (底满/中满/顶收), 一头被抽走一根;
- crates   箱桶堆: chest + barrel 组合, chest 朝向由脚本按堆心外推
           (禁止手填 facing).

判别原则: 小而像随手堆的 — 簇形由 seed 随机游走长出, 不做对称雕塑.
所有叠放格正下方必有方块 (support 安全). origin = 堆占地最小角格
(规范化后), y = 地面层. Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python clutter_pile.py --params '{"origin":[100,64,100],"kind":"hay","size":"small","seed":3}' [--out pile.json]
"""
import argparse, json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] 堆占地最小角格; y = 地面层
    "kind": "hay",                 # hay | wood | crates | firewood
    "size": "small",               # small | medium
    "seed": 3
}

KINDS = ("hay", "wood", "crates", "firewood")
SIZES = ("small", "medium")


def _walk_cluster(rng, n):
    """随机游走长出的不规则簇 (反对称雕塑)."""
    cells = [(0, 0)]
    while len(cells) < n:
        x, z = rng.choice(cells)
        dx, dz = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
        if (x + dx, z + dz) not in cells:
            cells.append((x + dx, z + dz))
    return cells


def _outward_facing(x, z, cells):
    """chest 朝向: 背离堆心 (脚本推导, 禁止手填)."""
    cx = sum(c[0] for c in cells) / len(cells)
    cz = sum(c[1] for c in cells) / len(cells)
    dx, dz = x - cx, z - cz
    if abs(dx) >= abs(dz):
        return "east" if dx > 0 else "west"
    return "south" if dz > 0 else "north"


def build(p):
    ox, oy, oz = [int(v) for v in p["origin"]]
    rng = random.Random(int(p["seed"]))
    small = p["size"] == "small"
    kind = p["kind"]
    blocks = {}                                # (x,y,z) -> spec, 后写覆盖

    if kind == "hay":
        base = _walk_cluster(rng, 3 if small else 5)
        for x, z in base:                      # 立轴为主, 个别倒放
            r = rng.random()
            axis = "y" if r < 0.6 else ("x" if r < 0.8 else "z")
            blocks[(x, 0, z)] = "minecraft:hay_block[axis=%s]" % axis
        for x, z in rng.sample(base, 1 if small else 2):
            blocks[(x, 1, z)] = "minecraft:hay_block[axis=y]"
    elif kind == "wood":
        a = rng.choice(("x", "z"))             # 主轴: 原木横放方向(脚本推导)
        b = "z" if a == "x" else "x"
        n = 3 if small else 4
        row = [(i, 0) if a == "x" else (0, i) for i in range(n)]
        for x, z in row:
            blocks[(x, 0, z)] = "minecraft:oak_log[axis=%s]" % a
        for x, z in rng.sample(row, n - 1):    # 上层交叉码
            blocks[(x, 1, z)] = "minecraft:oak_log[axis=%s]" % b
        lx, lz = row[rng.randrange(n)]         # 滚落一旁的一根
        blocks[(lx + (1 if a == "z" else 0), 0, lz + (1 if a == "x" else 0))] = \
            "minecraft:oak_log[axis=%s]" % b
    elif kind == "firewood":
        a = rng.choice(("x", "z"))
        n = 3 if small else 5

        def cell(i):
            return (i, 0) if a == "x" else (0, i)
        for i in range(n):                     # 底排 + 中排 (整齐码放)
            x, z = cell(i)
            blocks[(x, 0, z)] = "minecraft:spruce_log[axis=%s]" % a
            blocks[(x, 1, z)] = "minecraft:spruce_log[axis=%s]" % a
        for i in range(1, n - 1):              # 顶排收分
            x, z = cell(i)
            blocks[(x, 2, z)] = "minecraft:spruce_log[axis=%s]" % a
        x, z = cell(rng.choice((0, n - 1)))    # 一头被抽走一根
        del blocks[(x, 1, z)]
    else:                                      # crates
        base = [(0, 0), (1, 0), (0, 1)] if small \
            else [(0, 0), (1, 0), (2, 0), (0, 1)]
        chests = [base[0]] if small else rng.sample(base, 2)
        for x, z in base:
            if (x, z) in chests:
                f = _outward_facing(x, z, base)
                blocks[(x, 0, z)] = "minecraft:chest[facing=%s]" % f
            else:
                blocks[(x, 0, z)] = "minecraft:barrel"
        if not small:                          # 顶上再摞一个桶
            x, z = rng.choice([c for c in base if c not in chests] or [base[-1]])
            blocks[(x, 1, z)] = "minecraft:barrel"

    # 规范化到最小角格 (origin = min corner)
    mx = min(k[0] for k in blocks)
    mz = min(k[2] for k in blocks)
    return [{"x": ox + x - mx, "y": oy + y, "z": oz + z - mz, "block": spec}
            for (x, y, z), spec in sorted(blocks.items())]


def validate(p):
    if p["kind"] not in KINDS:
        die("kind must be one of %s" % (KINDS,), {"kind": list(KINDS)})
    if p["size"] not in SIZES:
        die("size must be one of %s" % (SIZES,), {"size": list(SIZES)})
    try:
        int(p["seed"])
    except (TypeError, ValueError):
        die("seed must be an int", {"seed": 3})
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,64,100]"})


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
            {"example": '{"origin":[100,64,100],"kind":"crates","size":"medium","seed":11}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
