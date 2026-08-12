#!/usr/bin/env python3
"""conifer_spire.py — 针叶塔形树(云杉/雪松/松)生成器.

与 giant_tree(阔叶云片)不同几何: 通直细干 + 逐层环裙边(半径随高度递减,
外环垂唇下垂, metaball 密度场成面 — 阶段2 kernel 迁移, 旧盘链近似废弃),
三形态:
- spire 云杉锥: 从 0.25h 起逐层环(真云杉=枝轮非满盘), 半径线性收成尖塔,
  裙边下垂 1 格, 层间竖向融合
- cedar 雪松: 3-5 块厚平板层, 层间露空气(分层塔)
- pine 松: 0.55h 以下光干, 顶部 2-4 个扁伞团(意大利伞松)

参考: 真实针叶形态 + MC 社区杉树惯例(裙边=叶层外圈下垂 1 格)。
Fully deterministic; stdlib only; tree_common kernel(Field 密度场).
Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python conifer_spire.py --params '{"origin":[0,64,0],"height":30,"base_radius":5,"form":"spire","species":"spruce","seed":7}' [--out t.json]
"""
import argparse, json, math, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out
from tree_common import SPECIES, rhu, vline, Voxel, Field

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
    ftx, ftz = rhu(tx), rhu(tz)

    # ---- 叶: metaball 场源(阶段2 kernel 迁移) — 旧版逐格直写 leaves 的
    # 盘链近似废弃; 真云杉=逐层环(枝轮, 半径随高递减)+裙边下垂, 环源同场
    # 成面天然连续(层间竖向融合, 层内环面+噪声撕裂缘)
    fld = Field(p["seed"])

    def skirt(y, r, droop=True, solid_disc=True):
        """一层裙边的场源: 外环(+垂唇 y-1 = 裙边下垂), solid_disc 补内环;
        层心小源防穿。环源成面后 = 连续环面带撕裂缘(非满盘非球串)。"""
        r = r * rng.uniform(0.9, 1.1)
        src = min(2.0, max(1.2, r * 0.4))
        step = src * 1.5
        n = max(6, int(2 * math.pi * r / step))
        for k in range(n):
            az = 2 * math.pi * k / n
            ring = (ftx + rhu(math.cos(az) * r), ftz + rhu(math.sin(az) * r))
            fld.add(ring[0], y, ring[1], src, 0.6)
            if droop:                                # 垂唇(裙边下垂 1 格)
                fld.add(ring[0], y - 1, ring[1], src * 0.9, 0.7)
        if solid_disc and r > 2.2:                   # 满盘层补内环(雪松平板)
            ri = r * 0.5
            for k in range(max(4, int(2 * math.pi * ri / step))):
                az = 2 * math.pi * k / max(4, int(2 * math.pi * ri / step))
                fld.add(ftx + rhu(math.cos(az) * ri), y,
                        ftz + rhu(math.sin(az) * ri), src, 0.6)
        fld.add(ftx, y, ftz, max(0.9, r * 0.35), 0.6)

    form = p["form"]
    if form == "spire":
        y0 = max(3, int(h * 0.25))
        dy = 2 if h <= 30 else 3
        for y in range(y0, h):
            if (y - y0) % dy:
                continue
            frac = (y - y0) / max(1, h - y0)
            skirt(y, rb * (1 - frac * 0.85) + 0.5, solid_disc=False)  # 逐层环
        fld.add(ftx, h - 1, ftz, 1.6, 0.8)          # 尖顶
    elif form == "cedar":
        n_plates = max(3, min(5, h // 8))
        for k in range(n_plates):
            y = int(h * (0.35 + 0.6 * k / max(1, n_plates - 1)))
            r = rb * (1 - 0.7 * k / max(1, n_plates - 1)) + 0.5
            for yy in (y, y + 1):
                skirt(yy, r, droop=(yy == y))
        fld.add(ftx, h - 1, ftz, 1.5, 0.8)
    else:  # pine
        n_puffs = rng.randint(2, 4)
        for k in range(n_puffs):
            az = 2 * math.pi * k / n_puffs + rng.uniform(-0.4, 0.4)
            px = tx + math.cos(az) * rb * 0.4
            pz = tz + math.sin(az) * rb * 0.4
            py = h - rng.randint(1, max(2, h // 6))
            fld.add(rhu(px), py, rhu(pz), rb * rng.uniform(0.45, 0.6), 0.65)
        fld.add(ftx, h - 1, ftz, rb * 0.5, 0.65)
    # 成面: carve(旧镂空率)→ 噪声振幅(边缘撕裂度); T 略高=针叶透光感
    t.leaves |= fld.rasterize(t.wood, T=0.55, amp=0.3 + p["carve"],
                              noise_L=max(2.5, rb / 2.0), shell=2)

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
