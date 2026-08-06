#!/usr/bin/env python3
"""connector.py — 体块连接件生成器 (bridge / corridor between two masses).

R10 体块编排层的交接件: cluster 簇群排好体块后, 本卡负责把它们连起来。
两种形态:
  open     露天桥: 地板 + 两侧栏杆(fence)
  covered  有顶连廊: 地板 + 栏杆 + 每 3 格立柱 + y+3 平板顶
  enclosed 封闭走廊: 地板 + 墙(每 3 格玻璃窗) + y+3 平板顶

接口约定(和 plan_shape 配合):
  frm/to = 两个体块墙面上的门洞格(取走面层空气格 y; 地板铺在 y-1)。
  两格 y 必须相同(标高不同先各自解决竖向, 本卡不做坡道)。
  路径: 同轴直连; 不同轴走 L 弯(bend=xz 先横后纵 / zx 先纵后横, 缺省 xz)。
  width=1 小径 / 2 标准走廊(垂直向 +1 格, 弯角补 2x2 平台)。

门洞清单写到 <out>.doors.json 并打印 stderr: 起墙时这些格留空(2 高)。
支撑: support_ground_y 给定时, 地板中线每 4 格一根立柱直达该标高。

Usage:
  python connector.py --params '{"frm":[100,65,100],"to":[110,65,100],"kind":"covered","width":2}' --out conn.json
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out  # noqa: E402

DEFAULTS = {
    "frm": [0, 65, 0],             # 门洞格 A (走面层空气格)
    "to": [10, 65, 0],             # 门洞格 B
    "kind": "covered",             # open | covered | enclosed
    "width": 2,                    # 1 小径 | 2 走廊
    "bend": "xz",                  # L 弯顺序: xz | zx
    "floor": "minecraft:spruce_planks",
    "railing": "minecraft:spruce_fence",
    "post": "minecraft:oak_log",
    "wall": "minecraft:spruce_planks",
    "window": "minecraft:glass_pane",
    "roof": "minecraft:spruce_slab",
    "support_ground_y": 0,         # >0 时立柱从地板下直达该标高; 0=不支撑
}

KINDS = ("open", "covered", "enclosed")


def _axis_path(frm, to, bend):
    """Manhattan 路径(含两端门洞格): 先沿 bend 第一轴后第二轴。"""
    x0, y0, z0 = frm
    x1, y1, z1 = to
    pts = []
    if bend == "xz":
        xs = range(x0, x1 + (1 if x1 >= x0 else -1), 1 if x1 >= x0 else -1)
        pts += [(x, z0) for x in xs]
        step = 1 if z1 >= z0 else -1
        pts += [(x1, z) for z in range(z0 + step, z1 + step, step)]
    else:
        zs = range(z0, z1 + (1 if z1 >= z0 else -1), 1 if z1 >= z0 else -1)
        pts += [(x0, z) for z in zs]
        step = 1 if x1 >= x0 else -1
        pts += [(x, z1) for x in range(x0 + step, x1 + step, step)]
    return pts


def _widen(pts, bend, width):
    """width=2: 第一段路径向垂直方向 +1 扩格, 弯角自然成 2x2。"""
    if width == 1:
        return list(pts), []
    wide = []
    corner = []
    for i, (x, z) in enumerate(pts):
        wide.append((x, z))
        nxt = pts[i + 1] if i + 1 < len(pts) else None
        prv = pts[i - 1] if i > 0 else None
        # 沿 x 走的段向 +z 扩, 沿 z 走的段向 +x 扩; 端点单格也扩
        dx = abs(nxt[0] - x) if nxt else (abs(prv[0] - x) if prv else 0)
        if dx == 1:
            wide.append((x, z + 1))
        else:
            wide.append((x + 1, z))
    # 弯角补全 2x2: 找方向变化点
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        if (a[0] != b[0]) != (b[0] != c[0]):
            corner += [(b[0], b[1]), (b[0] + 1, b[1]), (b[0], b[1] + 1), (b[0] + 1, b[1] + 1)]
    seen = set()
    out = []
    for cell in wide + corner:
        if cell not in seen:
            seen.add(cell)
            out.append(cell)
    return out, corner


def build(p):
    frm = [int(v) for v in p["frm"]]
    to = [int(v) for v in p["to"]]
    y = frm[1]
    w = int(p["width"])
    kind = p["kind"]

    path = _axis_path(frm, to, p["bend"])
    walk, _ = _widen(path, p["bend"], w)
    walk_set = set(walk)

    # 门洞格: 路径首尾 + 其宽度伴格(伴格 = 端点的非路径邻居; deterministic)
    door_cells = []
    for e, pn in ((path[0], path[1] if len(path) > 1 else None),
                  (path[-1], path[-2] if len(path) > 1 else None)):
        door_cells.append(e)
        if w == 2:
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c = (e[0] + dx, e[1] + dz)
                if c in walk_set and c != pn:
                    door_cells.append(c)
                    break
    door_set = set(door_cells)
    doors = []
    for dx, dz in door_cells:
        doors.append([dx, y, dz])
        doors.append([dx, y + 1, dz])

    # 栏杆格: 中段(= 路径去掉门洞格)的 4 邻不在路径内的位置
    # (门洞格不产栏杆 — 桥头两侧留空进出, 端点外侧更不能有)
    rail_cells = set()
    for (x, z) in sorted(walk_set):
        if (x, z) in door_set:
            continue
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n not in walk_set:
                rail_cells.add(n)

    blocks = []
    floor, rail = p["floor"], p["railing"]
    # 地板(walk + 栏杆格下面也要地板)
    for (x, z) in sorted(walk_set | rail_cells):
        blocks.append({"x": x, "y": y - 1, "z": z, "block": floor})
    if kind == "open":
        for (x, z) in sorted(rail_cells):
            blocks.append({"x": x, "y": y, "z": z, "block": rail})
    else:
        # 立柱/墙节奏: 沿路径每 3 格一根(对 covered)或连续墙带窗(enclosed)
        for i, (x, z) in enumerate(sorted(rail_cells)):
            if kind == "covered":
                if i % 3 == 0:
                    for dy in (0, 1, 2):
                        blocks.append({"x": x, "y": y + dy, "z": z, "block": p["post"]})
                else:
                    blocks.append({"x": x, "y": y, "z": z, "block": rail})
            else:  # enclosed
                for dy in (0, 1, 2):
                    mat = p["window"] if (dy == 1 and i % 3 == 1) else p["wall"]
                    blocks.append({"x": x, "y": y + dy, "z": z, "block": mat})
        # 顶: walk + 栏杆全覆盖
        for (x, z) in sorted(walk_set | rail_cells):
            blocks.append({"x": x, "y": y + 3, "z": z, "block": p["roof"]})

    # 支撑柱(可选): walk 中线每 4 格
    gy = int(p["support_ground_y"])
    if gy > 0:
        for i, (x, z) in enumerate(path):
            if i % 4 == 1:
                for sy in range(gy, y - 1):
                    blocks.append({"x": x, "y": sy, "z": z, "block": p["post"]})
    return blocks, doors


def validate(p):
    frm, to = p["frm"], p["to"]
    if len(frm) != 3 or len(to) != 3:
        die("frm/to must be [x,y,z]", {"frm": "[100,65,100]", "to": "[110,65,100]"})
    if int(frm[1]) != int(to[1]):
        die("frm/to 的 y 必须相同(本卡不做坡道; 标高不同先各自解决竖向)",
            {"frm_y": str(frm[1]), "to_y": str(to[1])})
    if p["kind"] not in KINDS:
        die("kind must be one of %s" % (KINDS,), {"kind": list(KINDS)})
    if int(p["width"]) not in (1, 2):
        die("width must be 1 or 2", {"width": "1-2"})
    if p["bend"] not in ("xz", "zx"):
        die("bend must be xz|zx", {"bend": ["xz", "zx"]})
    if frm[0] == to[0] and frm[2] == to[2]:
        die("frm/to 同格——没有可连的距离", {})
    for k in ("floor", "railing", "post", "wall", "window", "roof"):
        if not str(p[k]).startswith("minecraft:"):
            die("%s must be a minecraft block id" % k, {k: "minecraft:..."})


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
            {"example": '{"frm":[100,65,100],"to":[110,65,100],"kind":"covered"}'})
    validate(p)
    blocks, doors = build(p)
    write_out(blocks, a.out)
    sidecar = (a.out + ".doors.json") if a.out else ""
    payload = json.dumps({"doors": doors}, ensure_ascii=False)
    if sidecar:
        with open(sidecar, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
    print("doors(起墙留空, 2 高): %s%s" % (payload, " -> " + sidecar if sidecar else ""),
          file=sys.stderr)


if __name__ == "__main__":
    main()
