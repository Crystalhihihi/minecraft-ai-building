#!/usr/bin/env python3
"""accent_detailing.py — accent scattering (点缀学) generator, D1.

Thin generator: scatters small accent GROUPS on the OUTER face of an existing
wall (it never emits the wall itself). L4a/L4b split is hard-wired:

- L4a: `palette` = per-style whitelist (medieval/japanese/elven/industrial/
  interior) — the ONLY place piece kinds are chosen. No global all-style
  accent list. `interior` is the indoor palette (室内点缀): wall-banner
  挂画/挂毯 (1.21 实测 painting/item_frame 是实体, setblock 放不了 — 挂画用
  wall_banner 替代), wall_torch 壁灯, candle 蜡烛台, bookshelf 书架墙,
  顶角线 crown molding (倒放楼梯贴顶角), potted plant 盆栽; it pairs with
  the interior surfaces interior_wall / ceiling_corner / tabletop (桌面 30%
  概率放小件 — each tabletop group slot emits only on a 30% roll).
- L4b: the scatter algorithm below only decides DISTRIBUTION: accents attach
  to structural seams (corner columns / wall interior seams / under-eave row /
  column base), come in groups of 2-3 cells (never isolated singles), and the
  group count scales with the facade width.

Coordinate frame (same as wall_weathering): origin = bottom-LEFT cell of the
facade seen from outside, y = base layer; facing = outward normal; u runs to
the outside viewer's right. All accent cells sit one cell OFF the face
(u -> wall cell, +facing -> accent cell); attachment states (vine face, banner
facing, lantern hanging) are derived from `facing` — never
hand-edit the output (禁止手改方向状态).

Usage:
  python accent_detailing.py --params '{"origin":[100,64,100],"facing":"south","width":9,"height":6,"surface":["corner","eave","column_base"],"palette":"medieval"}' [--out accents.json]
"""
import argparse, json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, stair, write_out

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
RIGHT = {"north": "east", "east": "south", "south": "west", "west": "north"}
SURFACES = ("wall", "corner", "eave", "column_base",
            "interior_wall", "ceiling_corner", "tabletop")

# kind -> structural seams it may attach to (位置语法:碎件必依附结构缝)
KIND_SURFACES = {
    "vine": ("corner", "wall"),
    "banner": ("wall", "interior_wall"),
    "bars": ("corner", "wall"),
    "lantern_hang": ("eave",),
    "lantern_stand": ("column_base",),
    "button": ("wall",),
    "candle": ("column_base", "tabletop"),
    "stone_lantern": ("column_base",),
    "moss": ("column_base",),
    "gold": ("corner",),
    "sea_lamp": ("eave", "corner"),
    "pipes": ("corner",),
    # ---- interior palette kinds (室内点缀) --------------------------------
    "wall_sconce": ("interior_wall",),      # 壁灯:墙面火把排
    "bookshelf_wall": ("interior_wall",),   # 书架墙:贴墙落地竖列
    "crown_molding": ("ceiling_corner",),   # 顶角线:倒放楼梯贴顶角
    "potted_plant": ("tabletop", "column_base"),  # 盆栽:桌面/落地
}

# L4a 风格化白名单 — each entry: (kind, block-arg or None). 禁止全局通用清单.
PALETTES = {
    "medieval": [("vine", None), ("banner", "minecraft:red_wall_banner"),
                 ("bars", None), ("lantern_hang", None), ("lantern_stand", None)],
    "japanese": [("stone_lantern", None), ("moss", None), ("lantern_hang", None)],
    "elven": [("sea_lamp", None), ("gold", None), ("vine", None)],
    "industrial": [("bars", None), ("button", "minecraft:stone_button"),
                   ("pipes", None)],
    # 室内点缀:挂画=wall_banner 挂毯(1.21 painting/item_frame 是实体,不能
    # setblock — blocks.md:153);surface 配 interior_wall/ceiling_corner/tabletop
    "interior": [("banner", "minecraft:light_gray_wall_banner"),
                 ("wall_sconce", None), ("bookshelf_wall", None),
                 ("crown_molding", "minecraft:oak_stairs"),
                 ("candle", None), ("potted_plant", "minecraft:potted_fern")],
}

DEFAULTS = {
    "origin": [0, 64, 0],      # [x,y,z] 立面外视左下角格;y=基座层(贴地)
    "facing": "south",         # 立面外法线;附着状态由此推导
    "width": 9,                # 3-64, 沿墙宽
    "height": 6,               # 3-64, 层高
    "surface": ["wall", "corner", "eave", "column_base"],  # 允许的结构缝(可多选)
    "density": 0,              # 0-24;0=auto(约 width/3 组,随面宽)
    "palette": "medieval",     # L4a 风格白名单
    "seed": 7
}


def place(rng, kind, arg, u, v, F, cells, width, height):
    """Emit one accent GROUP (2-3 cells, never an isolated single). cells maps
    (u, v) -> block; every cell is one block off the wall face."""
    def free(uu, vv):
        return 0 <= uu < width and 0 <= vv < height and (uu, vv) not in cells

    def row(n, block):                       # horizontal group at (u, v)
        pts = [(u + i, v) for i in range(n)]
        if not all(free(*q) for q in pts):
            return False
        for q in pts:
            cells[q] = block
        return True

    if kind == "vine":                       # short grouped strip hanging down
        pts = [(u, v - i) for i in range(rng.randint(2, 3))]
        if not all(free(*q) for q in pts):
            return False
        for q in pts:
            cells[q] = "minecraft:vine[%s=true]" % F
        return True
    if kind == "banner":
        pts = [(u, v), (u, v - 1)]
        if not all(free(*q) for q in pts):
            return False
        for q in pts:
            cells[q] = "%s[facing=%s]" % (arg, F)
        return True
    if kind == "bars":
        return row(rng.randint(2, 3), "minecraft:iron_bars")
    if kind == "lantern_hang":
        return row(rng.randint(2, 3), "minecraft:lantern[hanging=true]")
    if kind == "lantern_stand":
        return row(2, "minecraft:lantern[hanging=false]")
    if kind == "button":
        return row(rng.randint(2, 3), "%s[face=wall,facing=%s]" % (arg, F))
    if kind == "candle":
        return row(2, "minecraft:candle[candles=%d,lit=true]" % rng.randint(2, 3))
    if kind == "stone_lantern":              # 石灯笼:石墙座+灯笼叠, 2 blocks
        pts = [(u, 0), (u, 1)]
        if not all(free(*q) for q in pts):
            return False
        cells[pts[0]] = "minecraft:stone_brick_wall"
        cells[pts[1]] = "minecraft:lantern[hanging=false]"
        return True
    if kind == "moss":
        return row(rng.randint(2, 3), "minecraft:moss_carpet")
    if kind == "gold":                       # corner studs, stacked (grounded)
        pts = [(u, 0), (u, 1)]
        if not all(free(*q) for q in pts):
            return False
        for q in pts:
            cells[q] = "minecraft:gold_block"
        return True
    if kind == "sea_lamp":                   # 海晶灯壁灯(凸出墙面半格观感)
        return row(2, "minecraft:sea_lantern")
    if kind == "pipes":                      # 管道:铁栏立管从柱脚爬 2-3 格
        pts = [(u, i) for i in range(rng.randint(2, 3))]
        if not all(free(*q) for q in pts):
            return False
        for q in pts:
            cells[q] = "minecraft:iron_bars"
        return True
    # ---- interior palette kinds (室内点缀;不影响老 palette 的 rng 流) ------
    if kind == "wall_sconce":                # 壁灯:贴墙火把横排 2-3
        return row(rng.randint(2, 3), "minecraft:wall_torch[facing=%s]" % F)
    if kind == "bookshelf_wall":             # 书架墙:落地竖列 2-3 层
        pts = [(u, i) for i in range(rng.randint(2, 3))]
        if not all(free(*q) for q in pts):
            return False
        for q in pts:
            cells[q] = "minecraft:bookshelf"
        return True
    if kind == "crown_molding":              # 顶角线:倒放楼梯横排(背贴墙)
        return row(rng.randint(2, 3), stair(arg, F, half="top"))
    if kind == "potted_plant":               # 盆栽:成组 2-3(桌面/落地)
        return row(rng.randint(2, 3), arg)
    return False


def build(p):
    F = p["facing"]
    width, height = int(p["width"]), int(p["height"])
    ox, oy, oz = [int(v) for v in p["origin"]]
    fx, fz = DIRS[F]
    ux, uz = DIRS[OPP[RIGHT[F]]]
    rng = random.Random(int(p["seed"]))
    requested = set(p["surface"])
    entries = [(k, a) for k, a in PALETTES[p["palette"]]
               if set(KIND_SURFACES[k]) & requested]
    n_groups = int(p["density"]) or max(2, round(width / 3))

    cells = {}
    for _ in range(n_groups):
        for _attempt in range(12):
            kind, arg = entries[rng.randrange(len(entries))]
            surf = rng.choice([s for s in KIND_SURFACES[kind] if s in requested])
            if surf == "corner":
                u, v = rng.choice((0, width - 1)), rng.randint(1, max(1, height - 2))
            elif surf == "wall":
                u = rng.randint(1, width - 2) if width > 2 else 0
                v = rng.randint(1, max(1, height - 2))
            elif surf == "eave":
                u, v = rng.randint(0, width - 1), height - 1
            elif surf == "interior_wall":
                u = rng.randint(1, width - 2) if width > 2 else 0
                v = rng.randint(1, max(1, height - 2))
            elif surf == "ceiling_corner":
                u, v = rng.randint(0, width - 1), height - 1
            elif surf == "tabletop":         # 桌面 30% 概率放小件:整组放或整组空
                if rng.random() >= 0.3:
                    break                    # 本次不放,该组留空(不补抽)
                u, v = rng.randint(0, width - 1), 1
            else:                            # column_base (柱脚优先转角柱)
                u = rng.choice((0, width - 1)) if rng.random() < 0.5 \
                    else rng.randint(0, width - 1)
                v = 0
            if place(rng, kind, arg, u, v, F, cells, width, height):
                break

    return [{"x": ox + ux * u + fx, "y": oy + v, "z": oz + uz * u + fz,
             "block": cells[(u, v)]}
            for (u, v) in sorted(cells)]


def validate(p):
    if p["facing"] not in DIRS:
        die("facing must be one of north/south/east/west", {"facing": list(DIRS)})
    if p["palette"] not in PALETTES:
        die("palette must be one of %s (L4a 风格白名单,无全局通用清单)"
            % (tuple(PALETTES),), {"palette": list(PALETTES)})
    try:
        width, height = int(p["width"]), int(p["height"])
    except (TypeError, ValueError):
        die("width/height must be ints", {"width": "3-64", "height": "3-64"})
    if not 3 <= width <= 64 or not 3 <= height <= 64:
        die("width/height out of range", {"width": "3-64", "height": "3-64"})
    if not isinstance(p["surface"], list) or not p["surface"] \
            or any(s not in SURFACES for s in p["surface"]):
        die("surface must be a non-empty list of structural seams",
            {"surface": list(SURFACES)})
    if not 0 <= int(p["density"]) <= 24:
        die("density out of range", {"density": "0-24 (0=auto 随面宽)"})
    if not [s for k, _ in PALETTES[p["palette"]]
            for s in KIND_SURFACES[k] if s in p["surface"]]:
        die("palette %s has no piece that can attach to surface %s"
            % (p["palette"], p["surface"]),
            {"KIND_SURFACES": {k: v for k, v in KIND_SURFACES.items()
                               if k in dict(PALETTES[p["palette"]])}})
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,64,100]"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}", help="JSON object of parameters")
    ap.add_argument("--out", default="", help="output file (default: stdout)")
    a = ap.parse_args()
    p = dict(DEFAULTS)
    try:
        p.update(json.loads(a.params) if a.params.strip() else {})
    except json.JSONDecodeError as e:
        die("--params is not valid JSON: %s" % e,
            {"example": '{"origin":[100,64,100],"facing":"south","width":9,"height":6,"palette":"medieval"}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
