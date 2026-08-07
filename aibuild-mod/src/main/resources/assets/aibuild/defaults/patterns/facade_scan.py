#!/usr/bin/env python3
"""facade_scan.py — 立面感知器 (patterns/). 治"强行让 AI 修饰, AI 不会修"。

分工(项目最高指令: 程序算空间事实, AI 只做审美决策):
输入建筑外壳 blocks json, 对每个朝外立面(±x/±z)输出:
- face 面积/bbox/门窗洞(位置+宽高)
- flat_spans: 无洞无凸起的连续平整区段(面积>=min_span)
- anchors: 按规则排好序的候选装饰锚点(带类型+坐标+一句理由):
    corner_pilaster 面角通高壁柱位 / base_footing 基座放脚行 /
    string_course 层间线脚行 / eave_cornice 檐口线脚行 /
    window_trim 洞口周边(大洞优先, 最多 6 个/面) /
    accent_cluster 大平区段中心(2-3 成组点缀位)
- budget: 该面建议装饰处数(面积/40, 钳 2-4) — 超过就是堆饰

AI 用法: 读报告 → 按风格和预算从 anchors 里挑(可全跳过的面留给次立面)
→ 对照 decoration_menu.md 选生成器/配方 → 放置。
不报"哪里平"就别修饰; 报告里没锚点的面不是敌人, 是留白。

Prints JSON report to stdout (或 --out)。Exit 0 always(这是感知不是判决)。
Usage:
  python patterns/facade_scan.py --params '{"blocks":"walls.json","min_span":12}' [--out scan.json]
"""
import argparse, json, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mirror_build  # for load_blocks

DIRS = (("x", -1), ("x", 1), ("z", -1), ("z", 1))
SIDE_NAME = {("z", 1): "南", ("z", -1): "北", ("x", 1): "东", ("x", -1): "西"}


def clusters(cells):
    """4-连通聚类((u,y) 平面格) -> [set,...]"""
    cells = set(cells)
    out = []
    while cells:
        stack = [cells.pop()]
        comp = set()
        while stack:
            c = stack.pop()
            comp.add(c)
            u, y = c
            for n in ((u + 1, y), (u - 1, y), (u, y + 1), (u, y - 1)):
                if n in cells:
                    cells.remove(n)
                    stack.append(n)
        out.append(comp)
    return out


def scan(p):
    blocks = mirror_build.load_blocks(p["blocks"])
    min_span = int(p.get("min_span", 12))
    solid = {(b["x"], b["y"], b["z"]) for b in blocks
             if not b["block"].startswith("minecraft:air")}

    faces = defaultdict(set)          # (axis, plane, sign) -> {(u,y)}
    relief = defaultdict(set)         # 同 key -> 面外一格有实体(凸起/凹进)的 (u,y)
    for (x, y, z) in solid:
        for axis, sign in DIRS:
            nb = (x + sign if axis == "x" else x, y,
                  z + sign if axis == "z" else z)
            if nb in solid:
                continue
            key = (axis, x if axis == "x" else z, sign)
            u = z if axis == "x" else x
            faces[key].add((u, y))
            outer = (x + 2 * sign if axis == "x" else x, y,
                     z + 2 * sign if axis == "z" else z)
            if outer in solid:        # 1 格外有实体 = 该格前有凹进腔, 不算平
                relief[key].add((u, y))

    report = []
    for (axis, plane, sign), cells in sorted(faces.items(),
                                             key=lambda kv: -len(kv[1])):
        if len(cells) < 20:
            continue
        us = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        u0, u1, y0, y1 = min(us), max(us), min(ys), max(ys)

        # 门窗洞: bbox 内非面格, 正后方(墙内一格)是实体 或 上下皆实体 → 洞
        holes = set()
        for u in range(u0, u1 + 1):
            for y in range(y0, y1 + 1):
                if (u, y) in cells:
                    continue
                wall = (plane, y, u) if axis == "x" else (u, y, plane)
                above = (wall[0], y + 1, wall[2])
                below = (wall[0], y - 1, wall[2])
                inner = (plane - sign, y, u) if axis == "x" else (u, y, plane - sign)
                if above in solid and below in solid or inner in solid:
                    holes.add((u, y))
        openings = []
        for comp in clusters(holes):
            cu = [c[0] for c in comp]
            cy = [c[1] for c in comp]
            openings.append({"u": [min(cu), max(cu)], "y": [min(cy), max(cy)],
                             "w": max(cu) - min(cu) + 1, "h": max(cy) - min(cy) + 1,
                             "area": len(comp)})
        openings.sort(key=lambda o: -o["area"])

        # 平整区段: 面格中无凸起且不在洞周边 1 格内的连续团
        near_hole = set()
        for (u, y) in holes:
            for du in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    near_hole.add((u + du, y + dy))
        flat_cells = {c for c in cells if c not in relief[(axis, plane, sign)]
                      and c not in near_hole}
        spans = []
        for comp in clusters(flat_cells):
            if len(comp) < min_span:
                continue
            cu = [c[0] for c in comp]
            cy = [c[1] for c in comp]
            spans.append({"u": [min(cu), max(cu)], "y": [min(cy), max(cy)],
                          "area": len(comp),
                          "center": [sum(cu) // len(cu), sum(cy) // len(cy)]})
        spans.sort(key=lambda s: -s["area"])

        height = y1 - y0 + 1
        anchors = []
        for u in (u0, u1):
            anchors.append({"type": "corner_pilaster", "u": u, "y": [y0, y1],
                            "note": "面角, 通高壁柱/转角柱位"})
        if height >= 4:
            anchors.append({"type": "base_footing", "u": [u0, u1], "y": y0,
                            "note": "基座放脚行(墙根凸 1 格或逐格收分)"})
        if height >= 7:
            anchors.append({"type": "string_course", "u": [u0, u1],
                            "y": y0 + height // 2,
                            "note": "层间线脚行(凸半格/一格通长线)"})
        anchors.append({"type": "eave_cornice", "u": [u0, u1], "y": y1,
                        "note": "檐口线(檐下收口/牛腿/封檐位)"})
        for o in openings[:6]:
            anchors.append({"type": "window_trim", "opening": o,
                            "note": "洞口周边(窗套/窗台/百叶; 正立面优先, 隔窗做, 别每窗都做)"})
        for s in spans:
            if s["area"] >= max(24, min_span * 2):
                anchors.append({"type": "accent_cluster", "pos": s["center"],
                                "note": "大平区段中心, 2-3 成组点缀(藤蔓/灯笼/旗/壁龛)"})

        report.append({
            "face": "%s=%d(%s)" % (axis, plane, SIDE_NAME[(axis, sign)]),
            "area": len(cells), "bbox_u": [u0, u1], "bbox_y": [y0, y1],
            "openings": openings, "flat_spans": spans,
            "budget": max(2, min(4, len(cells) // 40)),
            "anchors": anchors})
    return {"faces": report, "min_span": min_span,
            "usage": "anchors 是候选不是任务; 每面按 budget 挑, 次立面可整面留白"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    p = json.loads(a.params) if a.params.strip() else {}
    if "blocks" not in p:
        print(json.dumps({"error": "missing 'blocks' (walls/shell blocks json path)"},
                         ensure_ascii=False))
        sys.exit(2)
    report = scan(p)
    if a.out:
        Path(a.out).write_text(json.dumps(report, ensure_ascii=False, indent=1),
                               encoding="utf-8")
        print("wrote %s" % a.out)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
