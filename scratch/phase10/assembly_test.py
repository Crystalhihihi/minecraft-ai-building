#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""assembly_test.py — R10 体块拼装端到端离线验证。

plan_shape(cluster 2 体块) → 起墙/铺地/平顶 → connector(covered 连廊) →
按 doors 清单掏门 → collision_check + walkability_check(主门进, 要求到达附属体块内部)。
全绿 = 拼装链路闭环。跑法: cd scratch/phase10 && python assembly_test.py
"""
import json, sys
from pathlib import Path

PAT = Path(r"D:\minecraft-ai-building\aibuild-mod\src\main\resources\assets\aibuild\defaults\patterns")
sys.path.insert(0, str(PAT))
sys.path.insert(0, str(PAT / "validators"))

import plan_shape, connector, walkability_check, collision_check  # noqa: E402

WALL = "minecraft:oak_planks"
FLOOR = "minecraft:stone_bricks"
ROOF = "minecraft:oak_slab"
OUT = Path(__file__).parent

OX, GY, OZ = 0, 64, 0   # 测试原点, 地面 63


def mass_shell(cells, base_y):
    """一个体块的地板+3 高墙+平顶。返回 blocks。"""
    blocks = []
    outline = {c for c in cells if any((c[0]+dx, c[1]+dz) not in cells
                                       for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    for x, z in cells:
        blocks.append({"x": x, "y": base_y, "z": z, "block": FLOOR})          # 地板
        blocks.append({"x": x, "y": base_y + 4, "z": z, "block": ROOF})       # 平顶
    for x, z in outline:
        for dy in (1, 2, 3):
            blocks.append({"x": x, "y": base_y + dy, "z": z, "block": WALL})  # 墙
    return blocks


def main():
    # 1) 平面: cluster 2 体块
    p = dict(plan_shape.DEFAULTS)
    p.update({"origin": [OX, GY, OZ], "shape": "cluster", "width": 9, "depth": 7,
              "masses": 2, "storeys": 1, "seed": 5})
    cells, masses = plan_shape.footprint(p)
    assert len(masses) == 2, "cluster 应出 2 体块"
    main_mass, annex = masses[0], masses[1]

    # 2) 门洞: 两体块最接近的对面墙中点(同 y=GY+1 走面层)
    def nearest_wall_cell(mass, other):
        best = None
        for c in mass:
            oc = min(other, key=lambda o: abs(o[0]-c[0]) + abs(o[1]-c[1]))
            d = abs(oc[0]-c[0]) + abs(oc[1]-c[1])
            if best is None or d < best[0]:
                best = (d, c)
        return best[1]
    door_a = nearest_wall_cell(main_mass, annex)
    door_b = nearest_wall_cell(annex, main_mass)
    walk_y = GY + 1

    # 3) 连廊
    cp = dict(connector.DEFAULTS)
    cp.update({"frm": [door_a[0], walk_y, door_a[1]],
               "to": [door_b[0], walk_y, door_b[1]],
               "kind": "covered", "width": 1, "support_ground_y": 0})
    connector.validate(cp)
    conn_blocks, doors = connector.build(cp)
    door_set = {(d[0], d[2]) for d in doors}

    # 4) 体块壳 + 掏门(门洞格不起墙; 门下地板由连廊铺, 体块地板让位)
    walls, slabs = [], []
    for m in (main_mass, annex):
        for b in mass_shell(m, GY):
            if b["block"] == WALL and (b["x"], b["z"]) in door_set and b["y"] in (walk_y, walk_y + 1):
                continue  # 掏门
            if b["block"] == FLOOR and (b["x"], b["z"]) in door_set:
                continue  # 门下地板让给连廊
            (walls if b["block"] == WALL else slabs).append(b)

    # 主入口: 主体南面墙掏 1x2
    sx = sorted(main_mass, key=lambda c: (c[1], c[0]))[0]
    entrance = (sx[0], sx[1])
    walls = [b for b in walls if not (b["block"] == WALL and (b["x"], b["z"]) == entrance
                                      and b["y"] in (walk_y, walk_y + 1))]

    # 5) 写出并验收
    def dump(name, blocks):
        f = OUT / name
        f.write_text(json.dumps({"blocks": blocks}, ensure_ascii=False), encoding="utf-8")
        return str(f)

    walls_f = dump("assembly_walls.json", walls)
    conn_f = dump("assembly_conn.json", conn_blocks)
    merged = walls + slabs + conn_blocks
    merged_f = dump("assembly_merged.json", merged)

    fails = []
    r = collision_check.check({"a": walls_f, "b": conn_f})
    if not r["collision_free"]:
        fails.append("collision: %d 处" % len(r["collisions"]))

    # 主门在主体外墙: walkability 从外面走进来, 要求到达附属体块内部中心
    ac = sorted(annex)[len(annex) // 2]
    req = [[ac[0], walk_y, ac[1]]]
    outside = [entrance[0], walk_y, entrance[1] + 2]
    w = walkability_check.check({"blocks": merged_f, "door": outside, "require": req})
    reachable = all(q.get("reachable") for q in w.get("requires", [])) and w.get("ok")
    if not reachable:
        fails.append("walkability: %s" % json.dumps(w, ensure_ascii=False)[:300])

    print("体块数 2, 门洞 %d 格, 墙 %d 块, 连廊 %d 块" % (len(door_set), len(walls), len(conn_blocks)))
    if fails:
        for f in fails:
            print("FAIL", f)
        sys.exit(1)
    print("端到端全绿: collision_free + 主门→附属体块可达")
    print("merged:", merged_f)


if __name__ == "__main__":
    main()
