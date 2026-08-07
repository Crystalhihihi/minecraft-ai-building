#!/usr/bin/env python3
"""conifer_spire.py — 针叶塔形树(云杉/雪松/松)生成器.

与 giant_tree(阔叶云片)不同几何: 通直细干 + 逐层裙边(半径随高度递减,
边缘下垂+撕裂), 三形态:
- spire 云杉锥: 从 0.25h 起每层环盘, 半径线性收成尖塔, 裙边下垂 1 格
- cedar 雪松: 3-5 块厚平板层, 层间露空气(分层塔)
- pine 松: 0.55h 以下光干, 顶部 2-4 个扁伞团(意大利伞松)

参考: 真实针叶形态 + MC 社区杉树惯例(裙边=叶层外圈下垂 1 格)。
Fully deterministic; stdlib only; tree_common kernel.
Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python conifer_spire.py --params '{"origin":[0,64,0],"height":30,"base_radius":5,"form":"spire","species":"spruce","seed":7}' [--out t.json]
"""
import argparse, json, math, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out
from tree_common import SPECIES, h3, rhu, vline, Voxel

DEFAULTS = {
    "origin": [0, 64, 0],
    "height": 25,               # 8-80
    "base_radius": 4,           # 2-12, 叶锥底半径(裙边最宽处)
    "form": "spire",            # spire | cedar | pine
    "species": "spruce",
    "trunk": 1,                 # 1=1x1 | 2=2x2(大树)
    "seed": 0,
    "carve": 0.15,              # 0-0.4, 叶层镂空率
}
FORMS = ("spire", "cedar", "pine")


def build(p):
    h, rb = p["height"], p["base_radius"]
    rng = random.Random(p["seed"])
    t = Voxel(p["species"], p["seed"], p["origin"])
    c = (p["trunk"] - 1) / 2.0
    # ---- 通直干(微抖; trunk=2 → 0.5h 以上收 1x1; vline 桥防对角断开)
    jx = jz = 0.0
    prev = None
    for y in range(h):
        jx += rng.uniform(-0.04, 0.04)
        jz += rng.uniform(-0.04, 0.04)
        size = p["trunk"] if (p["trunk"] == 1 or y < h * 0.5) else 1
        t.bole_section(c + jx, c + jz, y, size)
        if prev is not None:
            pcx, pcy, pcz = prev
            for cc in vline((pcx, pcy, pcz), (rhu(c + jx), y, rhu(c + jz))):
                t.put_wood(*cc, "%s[axis=y]" % t.log)
        prev = (rhu(c + jx), y, rhu(c + jz))
    tx, tz = c + jx, c + jz

    def skirt(y, r, droop=True, solid_disc=True):
        """一层裙边环盘: 半径 r(带 ±10% 层抖动+±1 格边撕裂), 外圈下垂 1 格。"""
        r = r * rng.uniform(0.9, 1.1)
        ri = max(1, int(round(r)))
        for dx in range(-ri, ri + 1):
            for dz in range(-ri, ri + 1):
                d = math.sqrt(dx * dx + dz * dz)
                rag = (h3(dx, y, dz, p["seed"]) - 0.5) * 1.6   # 边撕裂 ±0.8
                if d > r + rag or (not solid_disc and d < r - 1.2 + rag):
                    continue
                if h3(dx, y + 99, dz, p["seed"]) < p["carve"]:
                    continue
                cell = (rhu(tx) + dx, y, rhu(tz) + dz)
                if cell not in t.wood:
                    t.leaves.add(cell)
                if droop and d > r - 1.3 + rag:               # 裙边: 外圈下垂 1 格
                    cell2 = (cell[0], y - 1, cell[2])
                    if cell2 not in t.wood and y - 1 > 0:
                        t.leaves.add(cell2)

    form = p["form"]
    if form == "spire":
        y0 = max(3, int(h * 0.25))
        dy = 2 if h <= 30 else 3
        for y in range(y0, h):
            if (y - y0) % dy:
                continue
            frac = (y - y0) / max(1, h - y0)
            skirt(y, rb * (1 - frac * 0.85) + 0.5)
        t.tuft(rhu(tx), h - 1, rhu(tz), 1.6, p["carve"] * 0.5)   # 尖顶
    elif form == "cedar":
        n_plates = max(3, min(5, h // 8))
        for k in range(n_plates):
            y = int(h * (0.35 + 0.6 * k / max(1, n_plates - 1)))
            r = rb * (1 - 0.7 * k / max(1, n_plates - 1)) + 0.5
            for yy in (y, y + 1):
                skirt(yy, r, droop=(yy == y))
        t.tuft(rhu(tx), h - 1, rhu(tz), 1.5, p["carve"] * 0.5)
    else:  # pine
        n_puffs = rng.randint(2, 4)
        for k in range(n_puffs):
            az = 2 * math.pi * k / n_puffs + rng.uniform(-0.4, 0.4)
            px = tx + math.cos(az) * rb * 0.4
            pz = tz + math.sin(az) * rb * 0.4
            py = h - rng.randint(1, max(2, h // 6))
            t.tuft(rhu(px), py, rhu(pz), rb * rng.uniform(0.45, 0.6), p["carve"])
        t.tuft(rhu(tx), h - 1, rhu(tz), rb * 0.5, p["carve"])

    t.prune(p["trunk"])
    return t.emit()


def validate(p):
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,64,100]"})
    p["origin"] = [int(v) for v in p["origin"]]
    for key, lo, hi in (("height", 8, 80), ("base_radius", 2, 12), ("trunk", 1, 2)):
        try:
            p[key] = int(p[key])
        except (TypeError, ValueError):
            die("%s must be an int %d-%d" % (key, lo, hi), {key: [lo, hi]})
        if not lo <= p[key] <= hi:
            die("%s must be %d-%d" % (key, lo, hi), {key: [lo, hi]})
    if p["form"] not in FORMS:
        die("form must be one of %s" % (FORMS,), {"form": list(FORMS)})
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
            {"example": '{"origin":[100,64,100],"height":30,"base_radius":5,"form":"spire","seed":7}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
