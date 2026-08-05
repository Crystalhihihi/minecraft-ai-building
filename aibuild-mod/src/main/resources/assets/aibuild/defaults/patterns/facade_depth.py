#!/usr/bin/env python3
"""facade_depth.py — parametric facade depth (立面纵深) generator.

Emits the Z-axis relief around an EXISTING rectangular wall box — geometry
only, never the wall body (材质掺比 is wall_weathering's job):

三段式 (calibrated from GrabCraft layer stats, scratch/phase9/gc_probe/
stats_details.md):
1. 基座放脚 (wall-ground junction): a footing ring protruding 1 past the
   wall line for base_height-1 solid layers, then a收分 top course of
   upside-down stairs whose BACKS FACE INWARD (-> outer corners). An
   optional apron (散水) slab ring one cell further out edges the site.
2. 墙身: string-course ledge rings every string_course_every layers
   (upside-down stairs, backs outward -> inner corners) and optional
   recess panels (壁龛): 1-deep air cells carved into the principal facade
   with a sill ledge stair below each panel.
3. 檐口封檐 (wall-roof junction): cornice overhang ring — 98.9% of samples
   overhang exactly 1, so the default is 1; 2 is the rare deep-eave variant
   (stepped: inner half=top + outer half=bottom) — plus a fascia slab row
   sealing the eave edge.

交接专章: 屋顶-烟囱泛水圈 = chimney.py's ledge_ring (call chimney.py, do
NOT rebuild it here); 建筑-场地挡土墙/踏步 = terraform_pad/terrace_farm —
this card stops at the apron.

L3 params are PRE-BAKED into named profiles; callers pass a profile name or
override single keys explicitly (any key left null inherits the profile).

Conventions: origin = [x,y,z] of the wall footprint's north-west corner,
y = ground layer; facing = principal facade (recess panels go there).
Canonical frame: facade = south, u -> +x; rotated to `facing` on emit.
ALL direction states are script-derived — never hand-edit facing/half/shape
in the output (禁止手改方向状态).

Usage:
  python facade_depth.py --params '{"origin":[100,64,100],"facing":"south","width":9,"depth":7,"height":6,"profile":"medieval_townhouse"}' [--out depth.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import Builder, FACING_ROT, die, require_suffix, slab, stair, write_out

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}

# relief_budget defaults calibrated from stats_details.md: 凹凸率中位 0.23
# (小房 0.18 / 大房 0.28); 出挑默认 1 (98.9% 样本); recess_panels default
# derived from relief_budget at build time.
PROFILES = {
    "medieval_townhouse": {  # 中世纪联排:石脚 2 层 + 楼层线脚
        "base_height": 2, "cornice_overhang": 1, "string_course_every": 4,
        "recess_panels": None, "relief_budget": 0.23, "apron": True,
        "base_material": "minecraft:stone_bricks",
        "trim_stairs": "minecraft:stone_brick_stairs",
        "fascia_slab": "minecraft:stone_brick_slab",
        "apron_slab": "minecraft:cobblestone_slab",
    },
    "modern_flat": {         # 现代平檐:薄脚、无线脚、净檐口
        "base_height": 1, "cornice_overhang": 1, "string_course_every": 0,
        "recess_panels": None, "relief_budget": 0.10, "apron": False,
        "base_material": "minecraft:smooth_stone",
        "trim_stairs": "minecraft:sandstone_stairs",
        "fascia_slab": "minecraft:smooth_stone_slab",
        "apron_slab": "minecraft:smooth_stone_slab",
    },
    "sakura_shinkabe": {     # 真壁日式:石基 1 层 + 木檐口
        "base_height": 1, "cornice_overhang": 1, "string_course_every": 0,
        "recess_panels": None, "relief_budget": 0.18, "apron": True,
        "base_material": "minecraft:cobblestone",
        "trim_stairs": "minecraft:spruce_stairs",
        "fascia_slab": "minecraft:spruce_slab",
        "apron_slab": "minecraft:cobblestone_slab",
    },
    "east_asian_formal": {   # 中式殿堂:台基 2 层 + 深檐 2(出挑 2 属 ~1% 变体)
        "base_height": 2, "cornice_overhang": 2, "string_course_every": 0,
        "recess_panels": None, "relief_budget": 0.20, "apron": True,
        "base_material": "minecraft:stone_bricks",
        "trim_stairs": "minecraft:stone_brick_stairs",
        "fascia_slab": "minecraft:stone_brick_slab",
        "apron_slab": "minecraft:stone_brick_slab",
    },
}

OVERRIDABLES = ("base_height", "cornice_overhang", "string_course_every",
                "recess_panels", "relief_budget", "apron", "base_material",
                "trim_stairs", "fascia_slab", "apron_slab")

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] wall footprint north-west corner; y = ground layer
    "facing": "south",             # principal facade (recess panels go on this face)
    "width": 9,                    # wall footprint along x, 3-31
    "depth": 7,                    # wall footprint along z, 3-31
    "height": 6,                   # wall height, 4-32; cornice sits on the top layer
    "profile": "medieval_townhouse",
    # null = inherit from profile; set explicitly to override a single value
    "base_height": None, "cornice_overhang": None, "string_course_every": None,
    "recess_panels": None, "relief_budget": None, "apron": None,
    "base_material": None, "trim_stairs": None, "fascia_slab": None,
    "apron_slab": None,
}


def ring_cells(w, d, o):
    """Perimeter cells of the footprint expanded by o (o>=1: outside the
    walls), tagged with the outward direction of each edge."""
    cells = []
    for x in range(-o, w + o):
        cells.append((x, -o, "north"))
        cells.append((x, d - 1 + o, "south"))
    for z in range(-o + 1, d - 1 + o):
        cells.append((-o, z, "west"))
        cells.append((w - 1 + o, z, "east"))
    return cells


def panel_columns(w, n):
    """Start columns of n 2-wide recess panels, even spread over u=1..w-2."""
    if n == 1:
        return [max(1, (w - 2) // 2)]
    return [1 + round(i * (w - 4) / (n - 1)) for i in range(n)]


def build(p):
    w, d, h = int(p["width"]), int(p["depth"]), int(p["height"])
    base_h, oh, every = int(p["base_height"]), int(p["cornice_overhang"]), int(p["string_course_every"])
    panels = p["recess_panels"]
    if panels is None:  # derive from relief budget: 凹凸率 -> 壁龛数量
        panels = int(round(float(p["relief_budget"]) * (w - 1) * 2 / 3))
    panels = min(panels, (w - 1) // 3) if h >= base_h + 4 else 0
    trim, fascia = p["trim_stairs"], p["fascia_slab"]
    rot, fmap = FACING_ROT[p["facing"]]
    b = Builder(rot=rot, fmap=fmap)

    # ---- 1. 基座放脚 (wall-ground junction) -------------------------------
    if base_h > 0:
        for y in range(0, base_h - 1):                 # solid footing ring
            for x, z, _ in ring_cells(w, d, 1):
                b.put(x, y, z, p["base_material"])
        for x, z, out in ring_cells(w, d, 1):          # 收分: backs inward
            b.put(x, base_h - 1, z, stair(trim, OPP[out], half="top"))
        if p["apron"]:
            for x, z, _ in ring_cells(w, d, 2):        # 散水 one cell further
                b.put(x, 0, z, slab(p["apron_slab"], "bottom"))
    elif p["apron"]:
        for x, z, _ in ring_cells(w, d, 1):
            b.put(x, 0, z, slab(p["apron_slab"], "bottom"))

    # ---- 2. 墙身: string courses + recess panels --------------------------
    if every > 0:
        y = base_h + every
        while y < h - 1:                               # cornice owns the top
            for x, z, out in ring_cells(w, d, 1):      # ledge: backs outward
                b.put(x, y, z, stair(trim, out, half="top"))
            y += every
    if panels > 0:
        y0, y1 = base_h + 1, h - 3
        for u0 in panel_columns(w, panels):
            for u in (u0, u0 + 1):
                for y in range(y0, y1 + 1):            # carve 1 deep (facade = canonical south)
                    b.carve(u, y, d - 1)
                b.put(u, y0 - 1, d, stair(trim, "south", half="bottom"))  # sill ledge

    # ---- 3. 檐口封檐 (wall-roof junction) ---------------------------------
    if oh >= 1:
        for x, z, out in ring_cells(w, d, 1):          # cornice: backs outward
            b.put(x, h - 1, z, stair(trim, out, half="top"))
        if oh == 2:                                    # deep eave: stepped outer row
            for x, z, out in ring_cells(w, d, 2):
                b.put(x, h - 1, z, stair(trim, out, half="bottom"))
        for x, z, _ in ring_cells(w, d, oh):           # 封檐板 sealing the eave edge
            b.put(x, h, z, slab(fascia, "bottom"))
    return b.emit([int(v) for v in p["origin"]])


def validate(p):
    if p["profile"] not in PROFILES:
        die("profile must be one of %s" % (tuple(PROFILES),), {"profile": list(PROFILES)})
    for k in OVERRIDABLES:                             # null -> inherit profile
        if p[k] is None:
            p[k] = PROFILES[p["profile"]][k]
    if p["facing"] not in FACING_ROT:
        die("facing must be one of north/south/east/west", {"facing": list(FACING_ROT)})
    try:
        w, d, h = int(p["width"]), int(p["depth"]), int(p["height"])
        base_h, oh, every = int(p["base_height"]), int(p["cornice_overhang"]), int(p["string_course_every"])
        relief = float(p["relief_budget"])
    except (TypeError, ValueError):
        die("width/depth/height/base_height/cornice_overhang/string_course_every must be ints, relief_budget a number",
            {"width": "3-31", "depth": "3-31", "height": "4-32", "base_height": "0-4",
             "cornice_overhang": "0-2", "string_course_every": "0-8", "relief_budget": "0-0.5"})
    if not (3 <= w <= 31 and 3 <= d <= 31):
        die("width/depth out of range", {"width": "3-31", "depth": "3-31"})
    if not 4 <= h <= 32:
        die("height out of range", {"height": "4-32"})
    if not 0 <= base_h <= min(4, h - 3):
        die("base_height out of range", {"base_height": "0-%d" % min(4, h - 3)})
    if not 0 <= oh <= 2:
        die("cornice_overhang out of range (98.9% of samples are 1; 2 is the rare deep eave)",
            {"cornice_overhang": "0-2"})
    if not 0 <= every <= 8:
        die("string_course_every out of range", {"string_course_every": "0-8 (0=off)"})
    if not 0 <= relief <= 0.5:
        die("relief_budget out of range (凹凸率中位 0.23, 大房上限 0.43)", {"relief_budget": "0-0.5"})
    if p["recess_panels"] is not None:
        n = int(p["recess_panels"])
        if not 0 <= n <= (w - 1) // 3:
            die("recess_panels must fit the facade (2 wide + 1 gap each)",
                {"recess_panels": "0-%d for width %d" % ((w - 1) // 3, w)})
        if n > 0 and h < base_h + 4:
            die("recess_panels need height >= base_height + 4", {"height": ">= %d" % (base_h + 4)})
    require_suffix(p, "trim_stairs", "_stairs",
                   ["minecraft:stone_brick_stairs", "minecraft:spruce_stairs"])
    require_suffix(p, "fascia_slab", "_slab", ["minecraft:stone_brick_slab", "minecraft:spruce_slab"])
    require_suffix(p, "apron_slab", "_slab", ["minecraft:cobblestone_slab", "minecraft:smooth_stone_slab"])
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
            {"example": '{"origin":[100,64,100],"facing":"south","width":9,"depth":7,"height":6,"profile":"medieval_townhouse"}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
