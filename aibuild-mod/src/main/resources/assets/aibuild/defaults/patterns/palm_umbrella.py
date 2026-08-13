#!/usr/bin/env python3
"""palm_umbrella.py — 棕榈/平顶伞盖树生成器.

与 giant_tree(阔叶云片)不同几何(阶段2: 叶全部 metaball 场源成面):
- palm 棕榈: 微弯 1x1 细干, 顶生 7-9 条羽状叶(抛物线先扬后垂, 无木纯叶,
  脊源+交错侧源场成面 → 叶条有体积, carve→沿条透缝), 冠下 2-3 椰团(fence 块)
- flat_top 平顶金合欢: 干 0.75h 处 2-4 短枝上扬(60% 概率基部分叉双干),
  顶部单块平顶微穹叶盘(盘面方格场源+噪声撕裂缘)

参考: 热带棕榈/稀树草原金合欢形态, MC 社区惯例。
Fully deterministic; stdlib only; tree_common kernel.
Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python palm_umbrella.py --params '{"origin":[0,64,0],"height":14,"crown_radius":5,"form":"palm","species":"jungle","seed":7}' [--out t.json]
"""
import argparse, json, math, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out
from tree_common import SPECIES, h3, rhu, vline, Voxel, Field

DEFAULTS = {
    "origin": [0, 64, 0],
    "height": 14,               # 8-30
    "crown_radius": 5,          # 3-10
    "form": "palm",             # palm | flat_top
    "species": "jungle",
    "seed": 0,
    "carve": 0.12,              # 0-0.4
}
FORMS = ("palm", "flat_top")


def build(p):
    h, r = p["height"], p["crown_radius"]
    rng = random.Random(p["seed"])
    t = Voxel(p["species"], p["seed"], p["origin"])
    form = p["form"]

    if form == "palm":
        # ---- 微弯干(单侧漂移; vline 桥防对角断开被剪)
        az = rng.uniform(0, 2 * math.pi)
        bx, bz = math.cos(az) * 0.14, math.sin(az) * 0.14
        x = z = 0.0
        prev = None
        for y in range(h):
            cell = (rhu(x), y, rhu(z))
            for cc in (vline(prev, cell) if prev else [cell]):
                t.put_wood(*cc, "%s[axis=y]" % t.log)
            prev = cell
            bend = 1.0 if y > 2 else 0.0
            x += bx * bend + rng.uniform(-0.03, 0.03)
            z += bz * bend + rng.uniform(-0.03, 0.03)
        top = (rhu(x), h, rhu(z))
        for cc in vline(prev, top):
            t.put_wood(*cc, "%s[axis=y]" % t.log)
        # ---- 羽状叶: 7-9 条抛物线叶(先扬后垂; 阶段2: 叶链改场源成面,
        # 叶条有体积不再是 1 格线; carve→沿条透缝)。K 小=条带细(1.8),
        # 羽条间距拉开才读得出"羽"而不是一坨
        fld = Field(p["seed"], K=2.0)
        n = rng.randint(7, 9)
        az0 = rng.uniform(0, 2 * math.pi)
        for k in range(n):
            faz = az0 + k * (2 * math.pi / n) + rng.uniform(-0.15, 0.15)
            fx, fz = top[0], top[2]
            L = r + rng.randint(-1, 1)
            first = None
            prev_sp = None
            for s in range(L):
                # 抛物线: 前 40% 微扬, 之后垂落
                frac = s / max(1, L - 1)
                fy = top[1] + 1 + (1 if frac < 0.3 else int(-(frac - 0.3) * L * 0.5))
                fx = top[0] + rhu(math.cos(faz) * (s + 1) * 0.9)
                fz = top[2] + rhu(math.sin(faz) * (s + 1) * 0.9)
                if first is None:
                    first = (fx, fy, fz)
                    # 连通桥: 干顶 → 羽叶首格(防整条羽叶对角断开被剪)
                    for cc in vline(top, first):
                        if cc not in t.wood:
                            t.leaves.add(cc)
                # 脊源沿 vline 面连通格逐格布(对角步进不断管 → prune 安全;
                # 脊源不吃 carve, 透缝只由侧源/噪声扛); gid=羽条分组(R1)
                cur_sp = (fx, fy, fz)
                for cc in (vline(prev_sp, cur_sp)[1:] if prev_sp else [cur_sp]):
                    fld.add(cc[0], cc[1], cc[2], 0.85, 0.7, k)
                prev_sp = cur_sp
                # 中缝交错侧叶(羽状)
                side = 1 if s % 2 == 0 else -1
                sx = fx + rhu(math.cos(faz + math.pi / 2) * side)
                sz = fz + rhu(math.sin(faz + math.pi / 2) * side)
                if h3(sx, fy, sz, p["seed"] ^ 7) >= p["carve"]:
                    fld.add(sx, fy, sz, 0.6, 0.7, k)
        t.leaves |= fld.rasterize(t.wood, T=0.55, amp=0.3 + p["carve"],
                                  noise_L=max(2.5, r / 2.0), shell=2, bite=0.08)
        # ---- 椰团
        for _ in range(rng.randint(2, 3)):
            cx = top[0] + rng.randint(-1, 1)
            cz = top[2] + rng.randint(-1, 1)
            t.put_wood(cx, top[1] - 1, cz, t.fence)
    else:
        # ---- flat_top: 60% 基部分叉双干
        forks = [(0.0, 0.0, 0.0, 0.0)]
        if rng.random() < 0.6:
            forks = [(0.35, 0.0, 0.0, 0.35), (-0.35, 0.35, 0.0, 0.0)]
        tips = []
        for (bx, bz, dx, dz) in forks:
            x, z = 0.0, 0.0
            top_y = int(h * 0.75)
            prev = None
            for y in range(top_y):
                cell = (rhu(x), y, rhu(z))
                for cc in (vline(prev, cell) if prev else [cell]):
                    t.put_wood(*cc, "%s[axis=y]" % t.log)
                prev = cell
                x += (dx + rng.uniform(-0.03, 0.03)) * (y / top_y)
                z += (dz + rng.uniform(-0.03, 0.03)) * (y / top_y)
            tips.append((rhu(x), top_y, rhu(z)))
        # ---- 短枝上扬(vline 桥) + 平顶叶盘(桥接到干尖)
        tips2 = []
        for (tx0, ty0, tz0) in tips:
            n_br = rng.randint(2, 4)
            for k in range(n_br):
                az = 2 * math.pi * k / n_br + rng.uniform(-0.3, 0.3)
                steps = rng.randint(2, 3)
                px, py, pz = tx0, ty0, tz0
                for s in range(steps):
                    nx = px + rhu(math.cos(az) * 0.9)
                    nz = pz + rhu(math.sin(az) * 0.9)
                    for cc in vline((px, py, pz), (nx, py + 1, nz)):
                        t.put_wood(*cc, "%s[axis=y]" % t.log)
                    px, py, pz = nx, py + 1, nz
                tips2.append((px, py, pz))
        cy = int(h * 0.75) + rng.randint(2, 3)
        ccx = rhu(sum(tx for tx, _, _ in tips) / len(tips))
        ccz = rhu(sum(tz for _, _, tz in tips) / len(tips))
        for (tx0, ty0, tz0) in tips2:                    # 连通桥: 枝尖 → 盘心
            for cc in vline((tx0, ty0, tz0), (ccx, cy, ccz)):
                if cc not in t.wood:
                    t.leaves.add(cc)
        # ---- 平顶叶盘: 盘面方格场源(阶段2 场成面, 微穹保留; 旧逐格直写废弃)
        fld = Field(p["seed"])
        for gx in range(-r, r + 1, 2):
            for gz in range(-r, r + 1, 2):
                d = math.sqrt(gx * gx + gz * gz)
                if d > r:
                    continue
                fld.add(ccx + gx, cy, ccz + gz, 1.5, 0.45)
                if d < r * 0.28:                        # 微穹(缓起, 不是台阶)
                    fld.add(ccx + gx, cy + 1, ccz + gz, 1.0, 0.5)
        fld.add(ccx, cy + 1, ccz, max(1.5, r * 0.3), 0.6)
        t.leaves |= fld.rasterize(t.wood, T=0.55, amp=0.3 + p["carve"],
                                  noise_L=max(2.5, r / 2.0), shell=2, bite=0.08)

    t.prune(1)
    return t.emit()


def validate(p):
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,64,100]"})
    p["origin"] = [int(v) for v in p["origin"]]
    for key, lo, hi in (("height", 8, 30), ("crown_radius", 3, 10)):
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
        die("seed must be int, carve must be float", {"carve": 0.12})
    if not 0.0 <= p["carve"] <= 0.4:
        die("carve must be 0-0.4", {"carve": 0.12})


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
            {"example": '{"origin":[100,64,100],"height":14,"crown_radius":5,"form":"palm","seed":7}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
