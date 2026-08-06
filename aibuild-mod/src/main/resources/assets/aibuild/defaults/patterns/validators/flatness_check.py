#!/usr/bin/env python3
"""flatness_check.py — 立面"光秃"检测器 (patterns/validators/).

用户实测定性: "细节修饰完全没有, 墙面凹凸变形等人类细节加工完全没有"。
手册写了 facade_depth/accent_detailing 但没有牙齿 — 本卡就是牙齿:
对每个朝外的立面(水平法线 ±x/±z), 凡面积 >= min_area 且**平面外无任何
凸出/凹进**者判 FAIL(光秃墙)。凸出判定: 立面外法线侧一格, 在立面 bounding
box 范围内存在任何实体块(线脚/壁柱/窗台/装饰都算)。

输入 blocks json(建造计划或读回的实际方块均可; 只含本建筑, 别带地形)。
Prints a JSON report. Exit 0 = 无光秃墙, 1 = 有。

Usage:
  python validators/flatness_check.py --params '{"blocks":"walls.json","min_area":40}'
"""
import argparse, json, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import mirror_build  # patterns/ : for load_blocks


def check(p):
    blocks = mirror_build.load_blocks(p["blocks"])
    min_area = int(p.get("min_area", 40))
    solid = {(b["x"], b["y"], b["z"]) for b in blocks
             if not b["block"].startswith("minecraft:air")}

    # 外侧面格: 实体块 + 某水平侧相邻为空气 => 立面格;
    # 相邻为"1 格深凸出物"(该邻居的外侧又是空气)也算立面格(计入面积,
    # 否则一条壁柱会把墙面切成碎片逃逸检查) — 同时它本身就是 relief。
    faces = defaultdict(set)   # (axis, plane, sign) -> {(u, y)}
    relief_marks = defaultdict(set)  # 同 key -> 有凸出物的 (u,y)
    for (x, y, z) in solid:
        for axis, sign, ux, uy, uz in (
                ("x", -1, x - 1, y, z), ("x", +1, x + 1, y, z),
                ("z", -1, x, y, z - 1), ("z", +1, x, y, z + 1)):
            nb = (ux, uy, uz)
            if nb in solid:
                # 邻居是 1 深凸出物?
                outer = (ux + (sign if axis == "x" else 0), uy,
                         uz + (sign if axis == "z" else 0))
                if outer not in solid:
                    key = (axis, x if axis == "x" else z, sign)
                    u = z if axis == "x" else x
                    faces[key].add((u, y))
                    relief_marks[key].add((u, y))
                continue
            key = (axis, x if axis == "x" else z, sign)
            u = z if axis == "x" else x
            faces[key].add((u, y))

    report_faces = []
    flat = 0
    for (axis, plane, sign), cells in sorted(faces.items(), key=lambda kv: -len(kv[1])):
        area = len(cells)
        if area < min_area:
            continue
        us = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        u0, u1, y0, y1 = min(us), max(us), min(ys), max(ys)
        # 外法线一格内有无任何凸出物(在立面 bbox 内), 或已被凸出物覆盖
        has_relief = bool(relief_marks.get((axis, plane, sign)))
        if not has_relief:
            for u in range(u0, u1 + 1):
                for y in range(y0, y1 + 1):
                    if axis == "x":
                        probe = (plane + sign, y, u)
                    else:
                        probe = (u, y, plane + sign)
                    if probe in solid:
                        has_relief = True
                        break
                if has_relief:
                    break
        report_faces.append({"face": "%s=%d%s" % (axis, plane, "外" if sign > 0 else "内"),
                             "area": area, "relief": has_relief})
        if not has_relief:
            flat += 1
    return {"flat_free": flat == 0,
            "flat_faces": flat,
            "checked_faces": len(report_faces),
            "min_area": min_area,
            "faces": report_faces}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    a = ap.parse_args()
    p = json.loads(a.params) if a.params.strip() else {}
    if "blocks" not in p:
        print(json.dumps({"error": "missing 'blocks' (blocks json path)"}, ensure_ascii=False))
        sys.exit(2)
    report = check(p)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    sys.exit(0 if report["flat_free"] else 1)


if __name__ == "__main__":
    main()
