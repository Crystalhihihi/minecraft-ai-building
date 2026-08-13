#!/usr/bin/env python3
"""banyan_tree.py — 榕树(气生根成柱多柱林)生成器.

与 giant_tree 不同几何(阶段4, docs/plans/2026-08-08-tree-overhaul.md):
中央短干(收分)+近平展主枝; 枝干外侧段垂下**气生根** — 垂链微摆下落,
触地者末段增粗成柱(柱脚小根盘), 未触地者中途渐断成帘; 3-7 柱共享一冠
(冠幅>柱距, 柱间冠底可读 = "多柱林")。冠 = metaball 密度场壳体
(tree_common.Field)。取代 giant_tree 的 banyan_court 近似卡(卡面已注路由)。
Fully deterministic; stdlib only; tree_common kernel.
Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python banyan_tree.py --params '{"origin":[0,64,0],"height":30,"crown_radius":12,"trunk":3,"seed":7}' [--out t.json]
"""
import argparse, json, math, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out
from tree_common import SPECIES, h3, rhu, vline, Voxel, Field

DEFAULTS = {
    "origin": [0, 64, 0],
    "height": 30,               # 15-60, 总高
    "crown_radius": 12,         # 6-25, 冠幅半径(>柱距, 柱间冠底可读)
    "trunk": 3,                 # 2-4, 中央干 ts×ts
    "species": "oak",
    "pillars": 0,               # 成柱气生根数 3-7; 0 = seed 自动
    "seed": 0,                  # int; same seed = same tree
}


def build(p):
    h, r = p["height"], p["crown_radius"]
    rng = random.Random(p["seed"])
    t = Voxel(p["species"], p["seed"], p["origin"])
    ts = p["trunk"]
    c = (ts - 1) / 2.0
    top_y = int(h * 0.5)                        # 榕树干短, 冠占上半
    for y in range(top_y):
        size = ts if y < top_y * 0.5 else max(1, ts - 1)   # 简化收分
        t.bole_section(c, c, y, size)
    fld = Field(p["seed"])

    # ---- 主枝: 5-7 条起角 0.4-0.7 渐走平展, 长 0.7-0.9r, 记链(气生根锚点)
    n_limbs = rng.randint(5, 7)
    az0 = rng.uniform(0, 2 * math.pi)
    limb_chains = []
    for k in range(n_limbs):
        az = az0 + k * (2 * math.pi / n_limbs) + rng.uniform(-0.25, 0.25)
        el = rng.uniform(0.4, 0.7)
        steps = max(4, int(r * rng.uniform(0.7, 0.9)))
        pos = (c, top_y, c)
        chain = []
        for s in range(steps):
            pos = (pos[0] + math.cos(az) * math.cos(el),
                   pos[1] + math.sin(el),
                   pos[2] + math.sin(az) * math.cos(el))
            el = max(0.08, el - rng.uniform(0.02, 0.06))  # 越走越平(榕枝横伸)
            az += rng.uniform(-0.04, 0.04)
            cell = (rhu(pos[0]), rhu(pos[1]), rhu(pos[2]))
            chain.append(cell)
            t.put_wood(*cell, "%s[axis=%s]" % (
                t.log, "x" if abs(math.cos(az)) >= abs(math.sin(az)) else "z"))
        limb_chains.append(chain)
        # 主枝链 vline 连通(防对角断开被 prune 剪)
        for j in range(1, len(chain)):
            for cc in vline(chain[j - 1], chain[j]):
                if cc not in t.wood:
                    t.put_wood(*cc, "%s[axis=y]" % t.log)

    # ---- 气生根: 锚点=主枝外侧 40-90% 节点(隔一取一); 前 n_pil 根强制
    # 触地成柱(底 4 格 2 宽+柱脚小根盘+入土), 其余过 55% 行程后概率渐断成帘
    anchors = []
    for chain in limb_chains:
        anchors.extend(chain[int(len(chain) * 0.4):int(len(chain) * 0.9) + 1:2])
    rng.shuffle(anchors)
    n_pil = max(3, min(7, p["pillars"] or rng.randint(3, 7)))
    for i, (ax, ay, azc) in enumerate(anchors):
        grounded = i < n_pil
        sx = sz = 0.0
        cells = []
        for k in range(ay + 1):
            y = ay - 1 - k
            if y < 0:
                break
            if not grounded and k > ay * 0.55 and \
                    h3(ax + k, ay, azc, p["seed"] ^ 91) < 0.25:
                break                               # 帘状垂根: 中途渐断
            sx += rng.uniform(-0.15, 0.15)          # 微摆(垂根近直)
            sz += rng.uniform(-0.15, 0.15)
            cells.append((rhu(ax + sx), y, rhu(azc + sz)))
            if y <= 0 and grounded:
                break                               # 触地
        prev = (ax, ay, azc)
        for cell in cells:
            for cc in vline(prev, cell):            # 垂链连通(锚在枝上)
                if cc not in t.wood:
                    t.put_wood(*cc, "%s[axis=y]" % t.log)
            prev = cell
        if grounded and cells:
            gx, _, gz = cells[-1]
            for (cx, cy, cz) in cells[-4:]:         # 末段 2 宽成柱
                t.put_wood(cx + 1, cy, cz, "%s[axis=y]" % t.log)
            t.put_wood(gx, -1, gz, "%s[axis=y]" % t.log)     # 入土
            for ox, oz in ((1, 0), (-1, 0), (0, 1), (0, -1)):  # 柱脚小根盘
                t.put_wood(gx + ox, 0, gz + oz, "%s[axis=y]" % t.log)

    # ---- 共享整冠(metaball 壳体): 主枝外侧 30% 起布源(双层+纵向抖动 —
    # 单层盘源成面是平板, 榕冠要有厚度), 冠心+顶穹团; flat 0.65 横展,
    # 冠幅>柱距(柱在 0.4-0.9r, 冠到 1.1r)
    base_r = max(1.8, r * 0.2)
    for gi, chain in enumerate(limb_chains):
        L = len(chain)
        gap = max(1.6, base_r * 1.4)
        n = max(2, int(L * 0.7 / gap))
        for k in range(n):
            frac = 0.3 + 0.7 * (k + rng.uniform(-0.3, 0.3)) / n
            frac = min(1.0, max(0.3, frac))
            x, y, z = chain[min(L - 1, int(frac * (L - 1)))]
            tr = base_r * rng.uniform(0.8, 1.2)
            fld.add(x, y, z, tr, 0.65, gi)
            fld.add(x, y + 2, z, tr * 0.8, 0.7, gi)  # 上层源(冠体厚度)
        x, y, z = chain[-1]                          # 梢端团
        fld.add(x, y, z, base_r * rng.uniform(1.1, 1.4), 0.65, gi)
    # 冠心团 + 顶穹团(治平顶/漏干) — 独立 gid(R1)
    n_limbs = len(limb_chains)
    fld.add(rhu(c), top_y + int(r * 0.35), rhu(c), min(r * 0.4, 7.0), 0.7, n_limbs)
    fld.add(rhu(c), h - 1, rhu(c), max(2.0, base_r * 1.2), 0.8, n_limbs + 1)
    t.leaves |= fld.rasterize(t.wood, T=0.5, amp=0.4,
                              noise_L=max(3, rhu(r / 3.0)),
                              shell=2 if r <= 10 else 3, bite=0.1, drape=0.3)
    t.prune(ts)
    return t.emit()


def validate(p):
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,64,100]"})
    p["origin"] = [int(v) for v in p["origin"]]
    for key, lo, hi in (("height", 15, 60), ("crown_radius", 6, 25),
                        ("trunk", 2, 4), ("pillars", 0, 7)):
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
    except (TypeError, ValueError):
        die("seed must be an int", {"seed": 0})


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
            {"example": '{"origin":[100,64,100],"height":30,"crown_radius":12,"seed":7}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
