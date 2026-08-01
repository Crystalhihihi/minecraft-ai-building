#!/usr/bin/env python3
"""terrace_farm.py — parametric hillside terrace farm (梯田).

Community hillside-farm recipe, parameterized:
- `levels` terraces climb toward +z, each one block higher than the last
  (高差 1) and `terrace_depth` blocks wide (2-4 farmland rows);
- a 1-high retaining wall (挡土墙) at each step, capped with a ridge
  (田埂压边: cobblestone_wall or dirt_path);
- the BACK row of every terrace is a water channel (水渠); on each wall one
  cell is a spill (水口) — a source on the wall top plus a falling cell
  into the channel below, so water reads as cascading level to level
  (层间下灌); spill x alternates left/right per level (zigzag);
- the remaining rows are farmland with a mature crop on top; crop type
  cycles per level through the `crops` palette;
- every surface column is filled down to origin y with fill_material, so
  the terraces stand as a solid earthwork — no floating dirt.

Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python terrace_farm.py --params '{"origin":[100,64,100],"width":10,"levels":4}' [--out t.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] min corner of the LOWEST terrace surface; climbs toward +z
    "width": 8,                    # along x, 3-24
    "levels": 3,                   # terrace count, 1-8
    "terrace_depth": 3,            # rows per terrace incl. the channel row, 2-4
    "crops": ["minecraft:wheat", "minecraft:carrots", "minecraft:potatoes"],
    "wall_material": "minecraft:cobblestone",
    "ridge": "cobblestone_wall",   # 田埂压边: cobblestone_wall | dirt_path | none
    "fill_material": "minecraft:dirt",
    "water_channel": True,
    "spill": True                  # 层间下灌水口
}

CROPS = {
    "minecraft:wheat": 7, "minecraft:carrots": 7,
    "minecraft:potatoes": 7, "minecraft:beetroots": 3,
}
RIDGES = ("cobblestone_wall", "dirt_path", "none")


def build(p):
    ox, oy, oz = p["origin"]
    w, levels, d = int(p["width"]), int(p["levels"]), int(p["terrace_depth"])
    step = d + 1                        # terrace rows + wall column
    cells = {}                          # (x,y,z) -> block, deduped

    def put(x, y, z, block):
        cells[(x, y, z)] = block

    def fill_under(x, y, z):
        for yy in range(oy, y):
            cells.setdefault((x, yy, z), p["fill_material"])

    for k in range(levels):
        y = oy + k
        z0 = k * step
        crop = p["crops"][k % len(p["crops"])]
        age = CROPS[crop]
        for z in range(z0, z0 + d):
            is_channel = (z == z0 + d - 1) and p["water_channel"]
            for x in range(w):
                if is_channel:
                    put(ox + x, y, oz + z, "minecraft:water")
                else:
                    put(ox + x, y, oz + z, "minecraft:farmland")
                    put(ox + x, y + 1, oz + z, "%s[age=%d]" % (crop, age))
                fill_under(ox + x, y, oz + z)
        if k == 0:
            continue
        # retaining wall between level k-1 and k
        zw = oz + k * step - 1
        xs = 1 if k % 2 == 1 else w - 2   # spill x, zigzag
        for x in range(w):
            put(ox + x, y, zw, p["wall_material"])
            fill_under(ox + x, y, zw)
            if p["ridge"] != "none" and not (p["spill"] and x == xs):
                put(ox + x, y + 1, zw, "minecraft:" + p["ridge"])
        if p["spill"]:
            put(ox + xs, y + 1, zw, "minecraft:water")        # source on the wall top
            put(ox + xs, y, zw - 1, "minecraft:water")        # falls into the channel below
    return [{"x": x, "y": y, "z": z, "block": b}
            for (x, y, z), b in sorted(cells.items())]


def validate(p):
    try:
        w, levels, d = int(p["width"]), int(p["levels"]), int(p["terrace_depth"])
    except (TypeError, ValueError):
        die("width/levels/terrace_depth must be ints",
            {"width": "3-24", "levels": "1-8", "terrace_depth": "2-4"})
    if not 3 <= w <= 24:
        die("width out of range", {"width": "3-24"})
    if not 1 <= levels <= 8:
        die("levels out of range", {"levels": "1-8"})
    if not 2 <= d <= 4:
        die("terrace_depth out of range (灌溉半径 4,过宽中间会干)",
            {"terrace_depth": "2-4"})
    if p["ridge"] not in RIDGES:
        die("ridge must be one of %s" % (RIDGES,), {"ridge": list(RIDGES)})
    if not isinstance(p["crops"], list) or not p["crops"]:
        die("crops must be a non-empty list", {"crops": ["minecraft:wheat"]})
    bad = [c for c in p["crops"] if c not in CROPS]
    if bad:
        die("unknown crop ids: %s" % bad, {"crops": sorted(CROPS)})
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
            {"example": '{"origin":[100,64,100],"width":10,"levels":4}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
