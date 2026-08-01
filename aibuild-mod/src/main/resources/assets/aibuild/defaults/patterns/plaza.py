#!/usr/bin/env python3
"""plaza.py — parametric plaza / town square (广场).

Paving patterns (community square recipes, parameterized):
- concentric: Chebyshev rings around the center cycling the palette (同心环带);
- radial:     8 spokes (axes + diagonals) in accent over ring-parity base (放射);
- checker:    alternating two-tone (棋盘);
- border:     plain field, the accent does only the rim (镶边).

A `border_width` accent rim always frames the square. The center gets a
reserved accent disc (`centerpiece` = fountain/statue: build those with
their own generators on this exact spot; flagpole: built inline — fence
mast + two-tone concrete flag flying +x). Around the rim runs a rhythm of
benches (stair seats facing outward — the sitter faces the center) and
lamp posts (3 fences + lantern); positions mirror around each side's
midpoint so the square stays symmetric, lamps win over benches at shared
spots, corners always get lamps, and cells on the center axes are kept
clear of benches as walkways.

Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python plaza.py --params '{"origin":[100,64,100],"width":15,"depth":15,"pattern":"concentric"}' [--out p.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] min corner; y = floor layer
    "width": 15,                   # along x, 7-41; odd centers best
    "depth": 15,                   # along z, 7-41
    "pattern": "concentric",       # concentric | radial | checker | border
    "materials": ["minecraft:stone_bricks", "minecraft:polished_andesite",
                  "minecraft:polished_diorite"],   # [main, secondary, accent]
    "border_width": 1,             # accent rim thickness, 0-3
    "centerpiece": "none",         # none | fountain | statue | flagpole
    "benches": True,
    "bench_spacing": 4,            # bench rhythm along the rim, 3-8
    "bench_material": "minecraft:oak_stairs",
    "lamps": True,
    "lamp_spacing": 6,             # lamp rhythm, 3-10
    "lamp_material": "minecraft:oak_fence"
}

PATTERNS = ("concentric", "radial", "checker", "border")
CENTERPIECES = ("none", "fountain", "statue", "flagpole")
FLAG = ("minecraft:red_concrete", "minecraft:white_concrete")


def rhythm(inner, spacing):
    """Index set in [0, inner) mirrored around the side midpoint."""
    half = (inner - 1) / 2.0
    return {t for t in range(inner)
            if min(abs((t - half) % spacing),
                   spacing - abs((t - half) % spacing)) < 1e-9}


def build(p):
    ox, oy, oz = p["origin"]
    w, d = int(p["width"]), int(p["depth"])
    mats = p["materials"]
    main, secondary, accent = mats[0], mats[1 % len(mats)], mats[-1]
    bw = int(p["border_width"])
    cx, cz = (w - 1) / 2.0, (d - 1) / 2.0
    icx, icz = w // 2, d // 2
    cells = {}

    def put(x, y, z, block):
        cells[(x, y, z)] = block

    # ---- paving ----
    for z in range(d):
        for x in range(w):
            dx, dz = x - cx, z - cz
            edge = min(x, z, w - 1 - x, d - 1 - z)
            if edge < bw:
                mat = accent
            elif p["pattern"] == "checker":
                mat = main if (x + z) % 2 == 0 else secondary
            elif p["pattern"] == "border":
                mat = main
            else:
                r = int(round(max(abs(dx), abs(dz))))
                if p["pattern"] == "concentric":
                    mat = mats[r % len(mats)]
                else:  # radial
                    spoke = dx == 0 or dz == 0 or abs(abs(dx) - abs(dz)) < 0.5
                    mat = accent if spoke else (main if r % 2 == 0 else secondary)
            put(ox + x, oy, oz + z, mat)

    # ---- centerpiece: reserved accent disc (+ inline flagpole) ----
    if p["centerpiece"] != "none":
        for z in range(d):
            for x in range(w):
                if (x - cx) ** 2 + (z - cz) ** 2 <= 2.5 ** 2:
                    put(ox + x, oy, oz + z, accent)
    if p["centerpiece"] == "flagpole":
        for i in range(1, 7):
            put(ox + icx, oy + i, oz + icz, p["lamp_material"])
        for x in range(icx + 1, icx + 4):
            put(ox + x, oy + 6, oz + icz, FLAG[0])
            put(ox + x, oy + 5, oz + icz, FLAG[1])

    # ---- rim rhythm: lamps + benches on the ring just inside the border ----
    def lamp(x, z):
        for i in range(1, 4):
            put(ox + x, oy + i, oz + z, p["lamp_material"])
        put(ox + x, oy + 4, oz + z, "minecraft:lantern")

    # sides: (along-length, coord-of-(t), facing-away-from-center)
    sides = [
        (w, lambda t: (bw + t, bw), "north"),
        (w, lambda t: (bw + t, d - 1 - bw), "south"),
        (d, lambda t: (bw, bw + t), "west"),
        (d, lambda t: (w - 1 - bw, bw + t), "east"),
    ]
    for side_len, place, facing in sides:
        inner = side_len - 2 * bw
        if inner < 3:
            continue
        lamp_ts = rhythm(inner, int(p["lamp_spacing"])) if p["lamps"] else set()
        lamp_ts |= {0, inner - 1}                     # corners always lit
        bench_ts = rhythm(inner, int(p["bench_spacing"])) if p["benches"] else set()
        for t in sorted(lamp_ts):
            x, z = place(t)
            lamp(x, z)
        for t in sorted(bench_ts - lamp_ts):
            x, z = place(t)
            axis = abs(x - cx) if side_len == w else abs(z - cz)
            if axis <= 1:                             # keep walkways clear
                continue
            put(ox + x, oy + 1, oz + z,
                "%s[facing=%s,half=bottom]" % (p["bench_material"], facing))
    return [{"x": x, "y": y, "z": z, "block": b}
            for (x, y, z), b in sorted(cells.items())]


def validate(p):
    try:
        w, d = int(p["width"]), int(p["depth"])
        bw = int(p["border_width"])
    except (TypeError, ValueError):
        die("width/depth/border_width must be ints",
            {"width": "7-41", "depth": "7-41", "border_width": "0-3"})
    if not (7 <= w <= 41 and 7 <= d <= 41):
        die("width/depth out of range", {"width": "7-41", "depth": "7-41"})
    if not 0 <= bw <= 3:
        die("border_width out of range", {"border_width": "0-3"})
    if p["pattern"] not in PATTERNS:
        die("pattern must be one of %s" % (PATTERNS,), {"pattern": list(PATTERNS)})
    if p["centerpiece"] not in CENTERPIECES:
        die("centerpiece must be one of %s" % (CENTERPIECES,),
            {"centerpiece": list(CENTERPIECES)})
    if not isinstance(p["materials"], list) or len(p["materials"]) < 2:
        die("materials needs [main, secondary, accent]",
            {"materials": ["minecraft:stone_bricks", "minecraft:polished_andesite",
                           "minecraft:polished_diorite"]})
    if not str(p["bench_material"]).endswith("_stairs"):
        die("bench_material must be a *_stairs id",
            {"bench_material": ["minecraft:oak_stairs", "minecraft:spruce_stairs",
                                "minecraft:stone_brick_stairs"]})
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
            {"example": '{"origin":[100,64,100],"width":15,"depth":15,"pattern":"concentric"}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
