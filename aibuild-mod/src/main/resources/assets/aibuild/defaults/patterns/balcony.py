#!/usr/bin/env python3
"""balcony.py — parametric balcony (阳台) generator.

Two variants (both classic MC build-circle recipes):
  cantilever — 悬空挑板式: deck slab cantilevered out of the facade, held by
    upside-down stair corbels under the wall line (support=brackets), fence
    columns down from the front corners (support=columns), or neither
    (support=none, modern look). Railing wraps the three free edges.
  recessed   — 凹进式 (loggia): the balcony is carved INTO the facade; the
    generator emits the recess shell (back/side walls, floor, lintel,
    threshold) plus explicit air cells that carve the recess out of an
    existing wall, and a railing at the front lip.

Conventions (ALL direction states derived from origin+facing — never
hand-edit 禁止手改方向状态; see stair_orientations.md):
- origin = bottom-LEFT cell of the wall face (seen from outside), y = the
  balcony FLOOR layer; facing = the outward direction the balcony looks to.
- canonical frame: u along the wall to the viewer's right, w outward (=
  facing), v up; the facade plane is w=-1 (cantilever) / w=0 lip (recessed).
- corbels are half=top stairs, flat top up against the deck underside,
  facing outward. (trapdoor 栏杆选项已下线 — 活板门全线禁用 2026-08-07)
- wall_stub (default true) emits the facade patch the balcony hangs on so
  the piece is self-supporting and shows where it attaches; overlap with
  the real wall is intentional (same material).

Output: {"blocks":[{x,y,z,block}]} (set_blocks_from_file compatible; air
cells carve via place_air).

Usage:
  python balcony.py --params '{"variant":"cantilever","origin":[100,64,100],"facing":"south","width":4,"depth":2}' [--out bal.json]
  python balcony.py --params '{"variant":"recessed","origin":[100,64,120],"facing":"east","width":3,"depth":1,"railing":"pane","railing_material":"minecraft:glass_pane"}'
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
RIGHT = {"north": "east", "east": "south", "south": "west", "west": "north"}
VARIANTS = ("cantilever", "recessed")
RAIL_KINDS = ("none", "fence", "wall", "pane")
SUPPORTS = ("brackets", "columns", "none")

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] bottom-LEFT cell of the wall face (outside view); y = balcony floor layer
    "facing": "south",             # outward direction
    "variant": "cantilever",       # cantilever | recessed
    "width": 4,                    # along the wall, 2-8
    "depth": 2,                    # cantilever: 1-3 out from the wall; recessed: 1-2 into it
    "floor_material": "minecraft:spruce_planks",
    "wall_material": "minecraft:stone_bricks",
    "wall_stub": True,             # emit the facade patch the balcony hangs on
    "stub_height": 3,              # cantilever stub layers ABOVE the deck (1-6)
    "railing": "fence",            # none | fence | wall | pane(trapdoor 已下线, 活板门全线禁用)
    "railing_material": "minecraft:spruce_fence",
    "post_material": "minecraft:spruce_fence",  # pane corner/end posts
    "post_spacing": 3,             # pane: post every N cells
    "support": "brackets",         # cantilever: brackets | columns | none
    "corbel_material": "minecraft:spruce_stairs",   # upside-down stair corbels
    "column_material": "minecraft:spruce_fence",
    "column_drop": 3,              # columns: layers down from the deck front corners
    "door": True,                  # access opening (cantilever: carved in the stub; recessed: carved in the back wall)
    "door_offset": -1,             # u of the doorway cell; -1 = center
    "headroom": 2                  # recessed: opening height 2-3
}


def stair(mat, facing, half="bottom"):
    return "%s[facing=%s,half=%s]" % (mat, facing, half)


def build(p):
    F = p["facing"]
    variant = p["variant"]
    width, depth = int(p["width"]), int(p["depth"])
    ox, oy, oz = [int(v) for v in p["origin"]]
    fx, fz = DIRS[F]
    ux, uz = DIRS[OPP[RIGHT[F]]]           # u axis: along the wall, viewer's right
    cells, air = {}, set()

    def P(u, w, v, block):
        cells[(u, w, v)] = block

    def carve(u, w, v):
        """Force-carve: wins over own body (doorway must punch the stub)."""
        cells.pop((u, w, v), None)
        air.add((u, w, v))

    def railing_cell(u, w, outward_dir, i, n):
        """One railing cell at v=1+ per kind; i = index along the edge."""
        kind = p["railing"]
        mat = p["railing_material"]
        if kind == "pane":
            is_post = (i % max(2, int(p["post_spacing"])) == 0) or (i == n - 1)
            return p["post_material"] if is_post else mat
        return mat  # fence / wall

    door_u = int(p["door_offset"])
    if door_u < 0:
        door_u = width // 2
    door_u = max(0, min(width - 1, door_u))

    if variant == "cantilever":
        stub_h = int(p["stub_height"])
        if p["wall_stub"]:                            # facade patch behind
            for u in range(width):
                for v in range(-1, stub_h + 1):
                    P(u, -1, v, p["wall_material"])
        for u in range(width):                        # the deck
            for w in range(depth):
                P(u, w, 0, p["floor_material"])
        support = p["support"]
        if support == "brackets":
            for u in range(width):                    # corbels under the wall line
                P(u, 0, -1, stair(p["corbel_material"], F, half="top"))
            if depth >= 2:                            # + a row under the front lip
                for u in range(width):
                    P(u, depth - 1, -1, stair(p["corbel_material"], F, half="top"))
        elif support == "columns":
            us = [0, width - 1] if width < 5 else [0, width // 2, width - 1]
            for u in us:
                for v in range(1, int(p["column_drop"]) + 1):
                    P(u, depth - 1, -v, p["column_material"])
        if p["railing"] != "none":                    # wrap the three free edges
            for u in range(width):                    # front edge
                P(u, depth - 1, 1, railing_cell(u, depth - 1, F, u, width))
            for w in range(depth - 1):                # side edges (corners already done)
                P(0, w, 1, railing_cell(0, w, RIGHT[F], w, depth))
                P(width - 1, w, 1, railing_cell(width - 1, w, OPP[RIGHT[F]], w, depth))
        if p["door"]:                                 # punch the doorway through the facade
            for v in (0, 1):
                carve(door_u, -1, v)

    else:  # recessed — emit the recess shell + carve the volume
        head = int(p["headroom"])
        floor, wall = p["floor_material"], p["wall_material"]
        for u in range(-1, width + 1):                # back wall
            for v in range(-1, head + 2):
                P(u, -depth, v, wall)
        for w in range(-depth, 1):                    # side walls (jambs)
            for v in range(-1, head + 2):
                P(-1, w, v, wall)
                P(width, w, v, wall)
        for u in range(width):
            for w in range(-depth, 1):
                P(u, w, -1, wall)                     # foundation row under the floor
                P(u, w, 0, floor)                     # the recess floor
                P(u, w, head + 1, wall)               # lintel / ceiling
        if p["railing"] != "none":                    # railing at the front lip
            for u in range(width):
                P(u, 0, 1, railing_cell(u, 0, F, u, width))
        # carve the recess + opening out of whatever facade is already there
        for u in range(width):
            for v in range(1, head + 1):
                for w in range(-depth, 0):
                    carve(u, w, v)                    # recess interior
                if p["railing"] == "none" or v > 1:
                    carve(u, 0, v)                    # front opening (above the lip)
        if p["door"]:                                 # access through the back wall
            for v in (0, 1):
                carve(door_u, -depth, v)

    out = []
    for (u, w, v) in sorted(air):
        if (u, w, v) in cells:
            continue                                  # own body wins
        out.append({"x": ox + ux * u + fx * w, "y": oy + v,
                    "z": oz + uz * u + fz * w, "block": "minecraft:air"})
    for (u, w, v), block in sorted(cells.items()):
        out.append({"x": ox + ux * u + fx * w, "y": oy + v,
                    "z": oz + uz * u + fz * w, "block": block})
    return out


def validate(p):
    if p["facing"] not in DIRS:
        die("facing must be one of north/south/east/west", {"facing": list(DIRS)})
    variant = p["variant"]
    if variant not in VARIANTS:
        die("variant must be one of %s" % (VARIANTS,), {"variant": list(VARIANTS)})
    try:
        width, depth = int(p["width"]), int(p["depth"])
    except (TypeError, ValueError):
        die("width/depth must be ints", {"width": "2-8", "depth": "1-3"})
    if not 2 <= width <= 8:
        die("width out of range", {"width": "2-8"})
    lo, hi = (1, 3) if variant == "cantilever" else (1, 2)
    if not lo <= depth <= hi:
        die("depth out of range for %s" % variant,
            {"depth": "%d-%d" % (lo, hi)})
    if p["railing"] not in RAIL_KINDS:
        die("railing must be one of %s" % (RAIL_KINDS,), {"railing": list(RAIL_KINDS)})
    rk, mat = p["railing"], str(p["railing_material"])
    need = {"fence": "_fence", "wall": "_wall"}
    if rk in need and not mat.endswith(need[rk]):
        die("railing=%s needs a *%s railing_material" % (rk, need[rk]),
            {"railing_material": ["minecraft:spruce_fence", "minecraft:cobblestone_wall"]})
    if rk == "pane" and not (mat.endswith("_pane") or mat == "minecraft:iron_bars"):
        die("railing=pane needs a *_pane id or minecraft:iron_bars",
            {"railing_material": ["minecraft:glass_pane", "minecraft:iron_bars"]})
    if variant == "cantilever":
        if p["support"] not in SUPPORTS:
            die("support must be one of %s" % (SUPPORTS,), {"support": list(SUPPORTS)})
        if not str(p["corbel_material"]).endswith("_stairs"):
            die("corbel_material must be a *_stairs id",
                {"corbel_material": ["minecraft:spruce_stairs", "minecraft:stone_brick_stairs"]})
    else:
        if not 2 <= int(p["headroom"]) <= 3:
            die("headroom out of range", {"headroom": "2-3"})
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
            {"example": '{"variant":"cantilever","origin":[100,64,100],"facing":"south","width":4,"depth":2}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
