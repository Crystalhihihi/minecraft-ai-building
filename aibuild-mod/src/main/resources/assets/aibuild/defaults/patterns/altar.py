#!/usr/bin/env python3
"""altar.py — 大祭坛/中心地标 (central altar / landmark) generator.

A ceremonial stepped dais (centerpiece for plazas, park centers, settlement
focal points). Layered square platforms (tiers) rising to a shrine column,
entered by a stair on the `facing` side. Deterministic; all geometry
script-derived (the stair's facing is derived from `facing`).

Layout (canonical, facing=south): a square `size`x`size` base platform, then
`tiers` progressively smaller square platforms stacked; the top carries the
`top` feature. A stair descends the `facing` edge.

Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python altar.py --params '{"origin":[100,64,100],"size":9,"tiers":3,"facing":"south"}' [--out altar.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import write_out, stair

DEFAULTS = {
    "origin": [0, 64, 0],            # [x,y,z] centre cell of the base platform at ground y
    "size": 9,                       # base platform width (odd recommended), 5-15
    "tiers": 3,                      # number of stacked platform layers, 2-5
    "facing": "south",               # stair direction (the stair faces OUT this way)
    "material": "minecraft:stone_bricks",
    "trim_material": "minecraft:chiseled_stone_bricks",  # top platform / edge band
    "accent": "minecraft:gold_block",  # shrine cap accent (sparing)
    "top": "flame",                  # none | flame | column | crystal
    "stair_material": "minecraft:stone_brick_stairs",
}

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
RIGHT = {"north": "east", "east": "south", "south": "west", "west": "north"}


def build(p):
    ox, oy, oz = p["origin"]
    size = max(5, min(15, int(p["size"])))
    if size % 2 == 0:
        size += 1  # keep odd -> clean centre + stair alignment
    tiers = max(2, min(5, int(p["tiers"])))
    mat, trim = p["material"], p["trim_material"]
    blocks = []

    def emit(x, y, z, block):
        blocks.append({"x": ox + x, "y": oy + y, "z": oz + z, "block": block})

    step = 2  # each tier shrinks by 2 (one block per side)
    y = 0
    for t in range(tiers):
        w = size - t * step
        if w < 3:
            break
        # platform slab (fill the top surface, solid for support)
        for dx in range(-(w // 2), w // 2 + 1):
            for dz in range(-(w // 2), w // 2 + 1):
                emit(dx, y, dz, trim if t == tiers - 1 else mat)
        # base layer solid under the platform for support (y-1)
        for dx in range(-(w // 2), w // 2 + 1):
            for dz in range(-(w // 2), w // 2 + 1):
                if y > 0:
                    emit(dx, y - 1, dz, mat)
        # facing stair descends this tier edge — its facing is the OUTWARD
        # direction (it steps down toward `facing`), derived by the script.
        # (FIX 2026-08-03: was a bare stair with no facing, which the mod's
        # BlockSpecParser resolves to default facing=north — wrong for 3 of 4
        # orientations. Now facing=facing.)
        fdx, fdz = DIRS[p["facing"]]
        f = (w // 2) + 1  # one block beyond platform edge
        emit(fdx * f, y, fdz * f, stair(p["stair_material"], p["facing"]))
        # right-side trim band on facing edge top (nice edge)
        rdx, rdz = DIRS[RIGHT[p["facing"]]]
        for k in range(-(w // 2), w // 2 + 1):
            emit(fdx * k + rdx * (w // 2), y, fdz * k + rdz * (w // 2), mat)
        y += 1

    # shrine column on the top platform
    cy = y
    col_h = 3
    for k in range(col_h):
        emit(0, cy + k, 0, mat)
    # top feature
    cap_y = cy + col_h
    top = p.get("top", "flame")
    if top == "flame":
        emit(0, cap_y, 0, "minecraft:campfire")
        emit(0, cap_y + 1, 0, p["accent"])   # accent on top of campfire (supported)
    elif top == "column":
        for k in range(2):
            emit(0, cap_y + k, 0, "minecraft:polished_blackstone")
        emit(0, cap_y + 2, 0, p["accent"])
    elif top == "crystal":
        emit(0, cap_y, 0, "minecraft:amethyst_block")
        emit(0, cap_y + 1, 0, "minecraft:amethyst_block")
        emit(0, cap_y + 2, 0, p["accent"])

    return blocks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    p = dict(DEFAULTS)
    p.update(json.loads(a.params) if a.params.strip() else {})
    write_out(build(p), a.out)

if __name__ == "__main__":
    main()
