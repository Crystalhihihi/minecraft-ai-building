#!/usr/bin/env python3
"""weeping_tree.py — 垂柳(垂坠树)生成器.

与 giant_tree 不同几何: 粗壮短干(0.35-0.45h) + 3-5 主枝陡峭上扬外展 +
**垂坠叶帘**(重力垂链: 主枝外侧段+帘环锚点向下, 顶粗渐细+尾部渐断,
相邻垂链顶部场融合成帘幕 — 阶段2 metaball 场成面) + 冠顶簇团(读得出
是树, 不是一团线)。垂坠是重力向下生长, 与一切上扬逻辑相反 — 单独成
生成器(拆分决议)。

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
from tree_common import SPECIES, h3, rhu, vline, Voxel, Field, shell_surface, pick_even

DEFAULTS = {
    "origin": [0, 64, 0],
    "height": 18,               # 8-30
    "crown_radius": 7,          # 4-12
    "species": "oak",
    "trunk": 2,                 # 2=2x2 | 3=3x3(大树)
    "seed": 0,
    "carve": 0.15,              # 0-0.4, 帘透缝率
    "decor": "",                # 装饰钩子(逗号组合): lights=外壳面光点(shroomlight)
                                #   berries=发光浆果垂链(cave_vines[berries=true]) all=全上
}


def build(p):
    h, r = p["height"], p["crown_radius"]
    rng = random.Random(p["seed"])
    t = Voxel(p["species"], p["seed"], p["origin"])
    c = (p["trunk"] - 1) / 2.0
    top_y = int(h * rng.uniform(0.35, 0.45))
    for y in range(top_y):
        t.bole_section(c, c, y, p["trunk"])
    fld = Field(p["seed"])          # 叶全部走 metaball 场源(阶段2)

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
        fld.add(chain[-1][0], chain[-1][1], chain[-1][2], r * 0.3, 0.8,
                len(limb_chains) - 1)                # 梢簇随主枝 gid(R1)
    # 冠顶中心团(读得出是树) — 独立 gid
    fld.add(rhu(c), top_y + int(r * 0.5), rhu(c), max(2.0, r * 0.45), 0.8,
            len(limb_chains))

    # ---- 垂坠叶帘(真垂坠修形, 阶段2): 主枝外侧 50% 的节点 + 帘环为锚,
    # 重力垂链 = 沿随机游走链逐格布场源, 顶粗(1.5)渐细(0.7), 尾部概率
    # 渐断; 相邻垂链顶部同场融合成帘幕, 尾段各自散开成条 — 不是疙瘩串。
    # 阶段6 R1: 锚点 gid=所在主枝(帘环锚按方位归最近主枝), 帘间留缝
    limb_az = [math.atan2(ch[-1][2] - c, ch[-1][0] - c) for ch in limb_chains] or [0.0]

    def gid_of(x, z):
        a = math.atan2(z - c, x - c)
        return min(range(len(limb_az)), key=lambda gi:
                   abs((a - limb_az[gi] + math.pi) % (2 * math.pi) - math.pi))

    anchors = []
    for gi, chain in enumerate(limb_chains):
        anchors.extend((cc, gi) for cc in chain[len(chain) // 2::2])  # 隔一取一
    ring_y = top_y + int(r * 0.4)
    n_ring = max(6, int(2 * math.pi * r * 0.8 / 2.5))  # 帘环间距 2.5
    for k in range(n_ring):
        az = 2 * math.pi * k / n_ring
        rx, rz = rhu(c + math.cos(az) * r * 0.8), rhu(c + math.sin(az) * r * 0.8)
        anchors.append(((rx, ring_y, rz), gid_of(rx, rz)))
    for (ax, ay, az), gi in anchors:
        if h3(ax, ay, az, p["seed"]) < p["carve"]:
            continue                                     # 透缝
        length = int(h * rng.uniform(0.35, 0.6))
        sx = sy = sz = 0.0
        for k in range(length):
            y = ay - k
            if y <= 1:
                break
            sx += rng.uniform(-0.25, 0.25)
            sz += rng.uniform(-0.25, 0.25)
            cell = (rhu(ax + sx), y, rhu(az + sz))
            if cell in t.wood:
                continue
            tail = k / max(1, length)
            if tail > 0.6 and h3(cell[0], cell[1], cell[2],
                                 p["seed"] ^ 31) < (tail - 0.6) * 1.5:
                continue                                 # 尾部渐断
            fld.add(cell[0], y, cell[2], 1.05 * (1.0 - 0.48 * tail), 0.9, gi)
    # 成面: 垂链是 1-3 格细条, 噪声收小(amp 0.2)防断链; T 低=帘更垂实;
    # R3 咬缺 0.08
    t.leaves |= fld.rasterize(t.wood, T=0.5, amp=0.2,
                              noise_L=max(2.5, r / 2.0), shell=2, bite=0.08)
    _decorate(t, p, rng, top_y)
    t.prune(p["trunk"])
    return t.emit()


def _decorate(t, p, rng, top_y):
    """decor 后处理(成面之后, prune 之前): lights=外壳面光点(shroomlight
    替换外壳面叶格, 8 扇区均布 + 1/3 给冠底/帘缘下侧, 全部 ≥1 空气面 —
    壳感知洪泛走 tree_common.shell_surface); berries=发光浆果垂链(逐列
    最低叶下方挂 cave_vines 身 + cave_vines_plant 梢, 长 1-4 渐断,
    链间隔≥2 不糊帘; 挂点正上方必是叶)。glow_berries 是物品不是方块。"""
    modes = set(m.strip() for m in str(p.get("decor") or "").lower().split(",")
                if m.strip())
    modes.discard("none")
    if "all" in modes:
        modes = {"lights", "berries"}
    if not modes or not t.leaves:
        return
    r = p["crown_radius"]
    outer_shell, col_bottom = shell_surface(sorted(t.leaves), t.wood)
    c = (p["trunk"] - 1) / 2.0
    if "lights" in modes:
        quota = max(2, r // 2)
        n_bottom = max(1, quota // 3)
        face = [cc for cc in outer_shell if cc[1] >= top_y]
        bot = [cc for cc in outer_shell if cc[1] < top_y]
        for cc in pick_even(face, quota - n_bottom, c, c, rng) + \
                pick_even(bot, n_bottom, c, c, rng):
            t.leaves.discard(cc)
            t.decor[cc] = "minecraft:shroomlight"
    if "berries" in modes:
        used = set()
        for (x, y, z) in sorted(col_bottom.values()):
            if (x, y, z) not in t.leaves:
                continue                                # 被 lights 占了(挂点须是叶)
            if any(abs(x - ux) < 2 and abs(z - uz) < 2 for ux, uz in used):
                continue                                # 链间隔≥2(别糊帘)
            if h3(x, y, z, t.seed ^ 71) >= 0.45:
                continue                                # 密度节制(帘缘为主)
            used.add((x, z))
            L = 1 + int(h3(x, y, z, t.seed ^ 73) * 4)   # 长 1-4
            cells = []
            for i in range(1, L + 1):
                c2 = (x, y - i, z)
                if c2 in t.wood or c2 in t.leaves or c2 in t.decor:
                    break                               # 渐断(碰块即收)
                cells.append(c2)
            for j, c2 in enumerate(cells):
                t.decor[c2] = ("minecraft:cave_vines_plant[berries=true]"
                               if j == 0 else            # 顶段挂叶底
                               "minecraft:cave_vines[berries=true]")


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
    bad = [m for m in str(p.get("decor") or "").lower().split(",")
           if m.strip() and m.strip() not in ("lights", "berries", "all", "none")]
    if bad:
        die("decor 未知项 %s (lights|berries|all, 逗号组合)" % bad,
            {"decor": "lights,berries"})


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
