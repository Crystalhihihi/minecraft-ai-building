#!/usr/bin/env python3
"""roof_plan.py — 组合平面屋顶生成器 (L/T/U 等多矩形平面的一体化屋顶).

治" L 形房子盖两个平行双坡"的实测翻车: 平面是组合的, 屋顶就必须分翼
垂直相交。本卡读取 plan_shape 同款平面(直接调 footprint 复算, 同 seed
同平面), 按"等 x 集合的连续 z 行"拆成矩形翼条, 每翼调 gable_roof
(脊沿长轴 — 主翼/翼楼自动垂直), 冲突格主翼优先(从属屋面并入主坡),
并在内转角铺 45° 谷沟(倒放楼梯, half=top)。

v1 范围: 平面必须能拆成 <=3 个等高条带矩形(L/T/U 均可; rect/rect_bump/
O/cluster 请直接用各屋顶卡或逐体块调用本卡)。各翼坡高各自按 45° 自动,
翼楼脊低于主脊是正常形态。

Usage:
  python roof_plan.py --params '{"origin":[100,80,100],"shape":"L","width":13,"depth":11,"seed":5}' [--out roof.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out  # noqa: E402
import plan_shape  # noqa: E402
import gable_roof  # noqa: E402

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] 平面包围盒西北角, y = 屋顶基层(墙顶上一层)
    "shape": "L",                  # L | T | U (rect 请直接用 gable_roof 等)
    "width": 13, "depth": 11,
    "wing": "medium",              # 与 plan_shape 同名参数同义
    "overhang": 1,                 # 檐口出挑 0-2
    "material": "minecraft:spruce_stairs",
    "ridge_material": "minecraft:spruce_slab",
    "ridge_support": "minecraft:spruce_planks",
    "valley_material": "",         # 缺省 = material
    "seed": 7,                     # 必须与墙体的 plan_shape 同 seed 才同一平面
}


def _strips(cells):
    """按"等 x 集合的连续 z 行"拆条带。返回 [(x0,x1,z0,z1)...]。"""
    rows = {}
    for (x, z) in cells:
        rows.setdefault(z, set()).add(x)
    strips = []
    for z in sorted(rows):
        xs = frozenset(rows[z])
        if strips and strips[-1][2] == xs and strips[-1][1] == z - 1:
            strips[-1][1] = z
        else:
            strips.append([z, z, xs])
    rects = []
    for z0, z1, xs in strips:
        if len(xs) != max(xs) - min(xs) + 1:
            die("平面条带 x 不连续(锯齿/洞), roof_plan v1 不支持", {})
        rects.append((min(xs), max(xs), z0, z1))
    return rects


def build(p):
    ox, oy, oz = [int(v) for v in p["origin"]]
    pp = dict(plan_shape.DEFAULTS)
    pp.update({"shape": p["shape"], "width": p["width"], "depth": p["depth"],
               "wing": p["wing"], "seed": p["seed"], "origin": [0, 0, 0]})
    cells, _ = plan_shape.footprint(pp)
    rects = _strips(cells)
    if not 1 <= len(rects) <= 3:
        die("拆出 %d 个条带, v1 只支持 <=3(L/T/U)" % len(rects), {})
    # 主翼 = 面积最大者; 其余为从属翼
    areas = [(x1 - x0 + 1) * (z1 - z0 + 1) for (x0, x1, z0, z1) in rects]
    main_i = max(range(len(rects)), key=lambda i: areas[i])

    mat = p["material"]
    valley_mat = p["valley_material"] or mat
    order = sorted(range(len(rects)), key=lambda i: i != main_i)  # 主翼先
    blocks = []
    taken = set()
    for i in order:
        x0, x1, z0, z1 = rects[i]
        w, d = x1 - x0 + 1, z1 - z0 + 1
        if i == main_i:
            axis = "x" if w >= d else "z"
        else:
            main_w = rects[main_i][1] - rects[main_i][0] + 1
            main_d = rects[main_i][3] - rects[main_i][2] + 1
            main_axis = "x" if main_w >= main_d else "z"
            axis = "z" if main_axis == "x" else "x"
        gp = {"origin": [ox + x0, oy, oz + z0], "width": w, "depth": d,
              "axis": axis, "overhang": p["overhang"], "height": 0,
              "material": mat, "ridge_material": p["ridge_material"],
              "ridge_support": p["ridge_support"], "end_fill": ""}
        for b in gable_roof.build(gp):
            key = (b["x"], b["y"], b["z"])
            if key not in taken:
                taken.add(key)
                blocks.append(b)

    # ---- 谷沟: 主翼与每个从属翼的内转角斜沟
    main = rects[main_i]
    for i, r in enumerate(rects):
        if i == main_i:
            continue
        x0, x1, z0, z1 = r
        # 从属翼与主翼的共边: 找出两者相邻的边
        # 内转角 = 从属翼矩形超出主翼边界的那个角(L 形有且仅有一个)
        corners = []
        if z1 + 1 == main[2]:        # 翼在主翼北(-z)
            if x0 > main[0]:
                corners.append((x0, main[2], 1, 1))    # 内凹角在翼西根
            if x1 < main[1]:
                corners.append((x1, main[2], -1, 1))   # 内凹角在翼东根
        elif main[3] + 1 == z0:      # 翼在主翼南(+z)
            if x0 > main[0]:
                corners.append((x0, main[3], 1, -1))
            if x1 < main[1]:
                corners.append((x1, main[3], -1, -1))
        if x1 + 1 == main[0]:        # 翼在主翼西(-x)
            if z0 > main[2]:
                corners.append((main[0], z0, 1, 1))
            if z1 < main[3]:
                corners.append((main[0], z1, 1, -1))
        elif main[1] + 1 == x0:      # 翼在主翼东(+x)
            if z0 > main[2]:
                corners.append((main[1], z0, -1, 1))
            if z1 < main[3]:
                corners.append((main[1], z1, -1, -1))
        for (cx, cz, dx, dz) in corners:
            y = oy
            x, z = cx, cz
            for _ in range(40):      # 沿 45° 斜向上爬, 直到主脊为止
                cand = None
                for probe_y in range(y + 3, oy - 1, -1):
                    if (x, probe_y, z) in taken:
                        cand = (x, probe_y, z)
                        break
                if cand is None:
                    break
                hit = next(b for b in blocks
                           if (b["x"], b["y"], b["z"]) == cand)
                if "slab" in hit["block"]:
                    break            # 主脊到了: 谷沟止于脊下, 不翻越
                # 谷沟替换该格屋面(不是架在上面): 倒放楼梯形成沟槽
                blocks.remove(hit)
                taken.discard(cand)
                facing = "south" if dz > 0 else "north"
                if abs(dx) > 0 and abs(dz) > 0:
                    facing = "east" if dx > 0 else "west"
                blocks.append({"x": x, "y": cand[1], "z": z,
                               "block": "%s[facing=%s,half=top]" % (valley_mat, facing)})
                taken.add(cand)
                x += dx
                z += dz
                y += 1
    return blocks


def validate(p):
    if p["shape"] not in ("L", "T", "U"):
        die("shape must be L|T|U(rect 直接用 gable_roof)", {"shape": ["L", "T", "U"]})
    if p["wing"] not in plan_shape.WING_RATIO:
        die("wing must be small|medium|large", {"wing": list(plan_shape.WING_RATIO)})
    for k in ("width", "depth"):
        if not 5 <= int(p[k]) <= 31:
            die("%s out of range" % k, {k: "5-31"})
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
            {"example": '{"origin":[100,80,100],"shape":"L","width":13,"depth":11,"seed":5}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
