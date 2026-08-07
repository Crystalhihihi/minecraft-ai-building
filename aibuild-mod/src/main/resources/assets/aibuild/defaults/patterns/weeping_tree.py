#!/usr/bin/env python3
"""weeping_tree.py — 垂柳(垂坠树)生成器.

与 giant_tree 不同几何: 粗壮短干(0.35-0.45h) + 3-5 主枝陡峭上扬外展 +
**垂坠叶帘**(从主枝外侧段和帘环垂下的叶链, 长 0.35-0.6h, 带摆动与透缝,
末端渐稀) + 冠顶簇团(读得出是树, 不是一团线)。
垂坠是重力向下生长, 与一切上扬逻辑相反 — 单独成生成器(拆分决议)。

参考: GrabCraft willow 蓝图 + 真实垂柳形态(帘从枝外沿垂下, 帘内有透缝)。
Fully deterministic; stdlib only; tree_common kernel.
Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python weeping_tree.py --params '{"origin":[0,64,0],"height":18,"crown_radius":7,"species":"oak","seed":7}' [--out t.json]
"""
import argparse, json, math, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out
from tree_common import SPECIES, h3, rhu, vline, Voxel

DEFAULTS = {
    "origin": [0, 64, 0],
    "height": 18,               # 8-30
    "crown_radius": 7,          # 4-12
    "species": "oak",
    "trunk": 2,                 # 2=2x2 | 3=3x3(大树)
    "seed": 0,
    "carve": 0.15,              # 0-0.4, 帘透缝率
}


def build(p):
    h, r = p["height"], p["crown_radius"]
    rng = random.Random(p["seed"])
    t = Voxel(p["species"], p["seed"], p["origin"])
    c = (p["trunk"] - 1) / 2.0
    top_y = int(h * rng.uniform(0.35, 0.45))
    for y in range(top_y):
        t.bole_section(c, c, y, p["trunk"])

    # ---- 主枝: 3-5 条陡峭上扬外展, 记录链(垂帘锚点)
    n_limbs = rng.randint(3, 5)
    az0 = rng.uniform(0, 2 * math.pi)
    limb_chains = []
    for k in range(n_limbs):
        az = az0 + k * (2 * math.pi / n_limbs) + rng.uniform(-0.25, 0.25)
        el = rng.uniform(0.5, 0.8)
        steps = max(3, int(r * rng.uniform(0.5, 0.7)))
        pos = (c, top_y, c)
        chain = []
        for s in range(steps):
            pos = (pos[0] + math.cos(az) * math.cos(el), pos[1] + math.sin(el),
                   pos[2] + math.sin(az) * math.cos(el))
            el = min(1.2, el + rng.uniform(0.02, 0.06))
            az += rng.uniform(-0.05, 0.05)
            cell = (rhu(pos[0]), rhu(pos[1]), rhu(pos[2]))
            chain.append(cell)
            t.put_wood(*cell, "%s[axis=%s]" % (
                t.log, "x" if abs(math.cos(az)) >= abs(math.sin(az)) else "z"))
        limb_chains.append(chain)
        t.tuft(chain[-1][0], chain[-1][1], chain[-1][2], r * 0.3, p["carve"] * 0.6)
    # 冠顶中心团(读得出是树)
    t.tuft(rhu(c), top_y + int(r * 0.5), rhu(c), max(2.0, r * 0.45), p["carve"] * 0.6)

    # ---- 垂坠叶帘: 主枝外侧 50% 的节点 + 帘环, 向下垂链
    anchors = []
    for chain in limb_chains:
        anchors.extend(chain[len(chain) // 2:])
    ring_y = top_y + int(r * 0.4)
    n_ring = max(6, int(2 * math.pi * r * 0.8 / 2))
    for k in range(n_ring):
        az = 2 * math.pi * k / n_ring
        anchors.append((rhu(c + math.cos(az) * r * 0.8), ring_y,
                        rhu(c + math.sin(az) * r * 0.8)))
    for (ax, ay, az) in anchors:
        if h3(ax, ay, az, p["seed"]) < p["carve"]:
            continue                                     # 透缝
        length = int(h * rng.uniform(0.35, 0.6))
        sx = sy = sz = 0.0
        for k in range(length):
            y = ay - k
            if y <= 1:
                break
            fade = 1.0 - 0.6 * k / max(1, length)        # 末端渐稀
            sx += rng.uniform(-0.3, 0.3)
            sz += rng.uniform(-0.3, 0.3)
            cell = (rhu(ax + sx), y, rhu(az + sz))
            if cell in t.wood:
                continue
            if h3(cell[0], cell[1], cell[2], p["seed"] ^ 31) > fade * 0.25:
                t.leaves.add(cell)
            if k < 3 and h3(cell[0], y, cell[2], p["seed"] ^ 77) < 0.5:
                t.leaves.add((cell[0] + (1 if cell[0] % 2 == 0 else -1), y, cell[2]))
    t.prune(p["trunk"])
    return t.emit()


def validate(p):
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,64,100]"})
    p["origin"] = [int(v) for v in p["origin"]]
    for key, lo, hi in (("height", 8, 30), ("crown_radius", 4, 12), ("trunk", 2, 3)):
        try:
            p[key] = int(p[key])
        except (TypeError, ValueError):
            die("%s must be an int %d-%d" % (key, lo, hi), {key: [lo, hi]})
        if not lo <= p[key] <= hi:
            die("%s must be %d-%d" % (key, lo, hi), {key: [lo, hi]})
    if p["species"] not in SPECIES:
        die("species must be one of %s" % (tuple(SPECIES),), {"species": list(SPECIES)})
    try:
        p["seed"] = int(p["seed"])
        p["carve"] = float(p["carve"])
    except (TypeError, ValueError):
        die("seed must be int, carve must be float", {"carve": 0.15})
    if not 0.0 <= p["carve"] <= 0.4:
        die("carve must be 0-0.4", {"carve": 0.15})


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
            {"example": '{"origin":[100,64,100],"height":18,"crown_radius":7,"seed":7}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
