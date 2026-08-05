#!/usr/bin/env python3
"""plan_shape.py — 平面形状生成器 (building footprint planner).

治"只会矩形平面": emits the WALL OUTLINE (单层周界格) of each storey as one
marker layer; the build AI raises the real walls from these cells. Shapes:
rect / L / T / U (主体+翼楼矩形拼合; wing size preset + side/position derived
from `seed`) / rect_bump (矩形带凹凸 — notches bitten from the edges until the
measured concavity reaches the calibrated tier).

凹凸率校准 (scratch/phase9/gc_probe/stats_details.md 二b, 299 medieval plans;
口径与 layer_analyze.py 完全一致: 洪泛填室内空洞后, 单调链凸包 + Pick 定理
格数, concavity = (凸包格数 - 轮廓格数) / 凸包格数): small builds (footprint
<= 238 cells, the stats median) P25~P75 = 0.10~0.28, large builds 0.17~0.43.
rect_bump draws its target uniformly from the matching tier.

Canonical frame: front = south (+z), origin = bounding-box north-west corner
cell (0,0), y = first-storey wall base. Upper storeys repeat the same
footprint at +4 y per storey (3 墙 + 1 楼板). Rotated to `facing` on emit
(朝向脚本推导, 禁止手改). Output: {"blocks":[{x,y,z,block}...]}.

NOTE: outline layers above the first floor have air below by design — this is
a PLAN artifact, not a structure; support_check is not applicable.

Usage:
  python plan_shape.py --params '{"origin":[100,64,100],"shape":"L","width":11,"depth":9,"wing":"medium","seed":5}' [--out plan.json]
"""
import argparse, json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out, FACING_ROT

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] 包围盒西北角格(canonical 0,0); y = 一层墙基层
    "facing": "south",             # 正面朝向(翼楼/凹凸随正面一起旋转)
    "width": 9,                    # 正面宽(x), 5-31
    "depth": 7,                    # 进深(z), 5-31
    "shape": "rect",               # rect | L | T | U | rect_bump
    "wing": "medium",              # 翼楼尺寸档: small 0.25 / medium 0.35 / large 0.45 (L/T/U 用)
    "storeys": 2,                  # 层数 1-4; 每层一条周界, 层距 +4
    "material": "minecraft:stone_bricks",  # 轮廓标记材(无方向整方块; 起墙时按风格卡替换)
    "seed": 7
}

SHAPES = ("rect", "L", "T", "U", "rect_bump")
WING_RATIO = {"small": 0.25, "medium": 0.35, "large": 0.45}
STOREY_GAP = 4


def _hull(points):
    """Monotonic-chain convex hull of (x,z) cell centres."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _fill_holes(cells):
    """洪泛填室内空洞 (layer_analyze.py 二b 同款口径)."""
    xs = [c[0] for c in cells]
    zs = [c[1] for c in cells]
    x0, x1, z0, z1 = min(xs) - 1, max(xs) + 1, min(zs) - 1, max(zs) + 1
    outside = set()
    stack = [(x, z) for x in range(x0, x1 + 1) for z in (z0, z1)
             if (x in (x0, x1) or z in (z0, z1)) and (x, z) not in cells]
    outside.update(stack)
    while stack:
        cx, cz = stack.pop()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (cx + dx, cz + dz)
            if x0 <= n[0] <= x1 and z0 <= n[1] <= z1 \
                    and n not in cells and n not in outside:
                outside.add(n)
                stack.append(n)
    return cells | {(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)
                    if (x, z) not in outside}


def concavity(cells):
    """(凸包格数 - 轮廓格数) / 凸包格数 — layer_analyze.py 二b 原口径
    (填洞 + 单调链凸包 + Pick 定理格数)."""
    import math
    filled = _fill_holes(cells)
    hull = _hull(list(filled))
    if len(hull) < 3:
        return 0.0
    area = abs(sum(hull[i][0] * hull[(i + 1) % len(hull)][1]
                   - hull[(i + 1) % len(hull)][0] * hull[i][1]
                   for i in range(len(hull)))) / 2
    b = sum(math.gcd(abs(hull[(i + 1) % len(hull)][0] - hull[i][0]),
                     abs(hull[(i + 1) % len(hull)][1] - hull[i][1]))
            for i in range(len(hull)))
    hull_cells = area + b / 2 + 1
    return max(0.0, (hull_cells - len(filled)) / hull_cells)


def footprint(p):
    W, D = int(p["width"]), int(p["depth"])
    rng = random.Random(int(p["seed"]))
    shape = p["shape"]
    cells = {(x, z) for x in range(W) for z in range(D)}          # 主体满矩形
    if shape in ("L", "T", "U"):
        r = WING_RATIO[p["wing"]]
        dm = max(2, round(D * 0.6))                               # 主体(前)进深
        cells = {(x, z) for x in range(W) for z in range(D - dm, D)}
        if shape == "L":
            ww = max(2, min(W - 2, round(W * r)))
            xs = range(0, ww) if rng.random() < 0.5 else range(W - ww, W)
            cells |= {(x, z) for x in xs for z in range(0, D - dm)}
        elif shape == "T":
            ww = max(2, min(W - 2, round(W * r)))
            x0 = (W - ww) // 2
            cells |= {(x, z) for x in range(x0, x0 + ww) for z in range(0, D - dm)}
        else:  # U: 后栋(z 北侧) + 双侧翼楼通长, 内院向正面(south)开口
            ww = max(2, min((W - 3) // 2, round(W * r)))
            db = max(2, min(D - 3, round(D * r)))
            cells = {(x, z) for x in range(W) for z in range(0, db)}
            cells |= {(x, z) for x in list(range(0, ww)) + list(range(W - ww, W))
                      for z in range(0, D)}
    elif shape == "rect_bump":
        area = W * D
        lo, hi = (0.10, 0.28) if area <= 238 else (0.17, 0.43)   # stats 分档
        target = rng.uniform(lo, hi)
        # 咬边避开角格 => 凸包恒等于原矩形(Pick 口径), 凹凸率 = 咬除格数/area,
        # 按目标面积构造咬合: need = round(target * area)
        need = round(target * area)
        removed = 0
        for _ in range(80):
            if removed >= need:
                break
            edge = rng.choice(("n", "s", "e", "w"))
            span, across = (W, D) if edge in ("n", "s") else (D, W)
            dmax = 2 if area <= 238 else 3
            if min(5, span - 2) < 2 or min(dmax, across - 4) < 1:
                continue
            wn = rng.randint(2, min(5, span - 2))
            dn = rng.randint(1, min(dmax, across - 4))
            remaining = need - removed                            # 收口: 末口不超目标
            while wn * dn > remaining and dn > 1:
                dn -= 1
            while wn * dn > remaining and wn > 1:
                wn -= 1
            p0 = rng.randint(1, span - wn - 1)                  # 1 格角部留白
            if edge in ("n", "s"):
                rows = range(0, dn) if edge == "n" else range(D - dn, D)
                bite = {(x, z) for x in range(p0, p0 + wn) for z in rows}
            else:
                cols = range(0, dn) if edge == "w" else range(W - dn, W)
                bite = {(x, z) for z in range(p0, p0 + wn) for x in cols}
            if bite and bite <= cells:                        # 不加深/拓宽已有凹口
                cells -= bite
                removed += len(bite)
    return cells


def build(p):
    ox, oy, oz = [int(v) for v in p["origin"]]
    rot, _ = FACING_ROT[p["facing"]]
    cells = footprint(p)
    outline = sorted(c for c in cells
                     if any((c[0] + dx, c[1] + dz) not in cells
                            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))))
    blocks = []
    for s in range(int(p["storeys"])):
        for x, z in outline:
            wx, wz = rot(x, z)
            blocks.append({"x": ox + wx, "y": oy + s * STOREY_GAP,
                           "z": oz + wz, "block": p["material"]})
    return blocks


def validate(p):
    if p["facing"] not in FACING_ROT:
        die("facing must be one of north/south/east/west", {"facing": list(FACING_ROT)})
    if p["shape"] not in SHAPES:
        die("shape must be one of %s" % (SHAPES,), {"shape": list(SHAPES)})
    if p["wing"] not in WING_RATIO:
        die("wing must be one of %s" % (tuple(WING_RATIO),), {"wing": list(WING_RATIO)})
    try:
        w, d, st = int(p["width"]), int(p["depth"]), int(p["storeys"])
    except (TypeError, ValueError):
        die("width/depth/storeys must be ints", {"width": "5-31", "depth": "5-31", "storeys": "1-4"})
    if not 5 <= w <= 31 or not 5 <= d <= 31:
        die("width/depth out of range", {"width": "5-31", "depth": "5-31"})
    if not 1 <= st <= 4:
        die("storeys out of range", {"storeys": "1-4"})
    if not str(p["material"]).startswith("minecraft:") or "[" in str(p["material"]):
        die("material must be a plain full-block id (no block states)",
            {"material": "minecraft:stone_bricks"})
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
            {"example": '{"origin":[100,64,100],"shape":"L","width":11,"depth":9}'})
    try:
        p["seed"] = int(p["seed"])
    except (TypeError, ValueError):
        die("seed must be an int", {"seed": 7})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
