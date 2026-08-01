#!/usr/bin/env python3
"""chimney.py — parametric chimney (烟囱) generator.

Stone-brick / brick shaft (1x1, 1x2 or 2x2) with:
- a FLASHING ledge ring where it pierces the roof (检修台/泛水): upside-down
  stairs one cell out all around, facing outward — backs outward -> inner
  corners per the stair rules; the half-top tread is a standable service
  ledge for roof repairs;
- a rim course on top (same ring recipe) and a cap: campfire (smoke, the
  classic) or a closed trapdoor lid.

The shaft is solid full blocks stacked from the base, so every block has
support; the campfire is whitelisted (contains "fire").

Output: {"blocks":[{x,y,z,block}...]}. ALL direction states derived; never
hand-edit (禁止手改方向状态).

Usage:
  python chimney.py --params '{"origin":[100,64,100],"width":2,"depth":2,"height":6}' [--out chimney.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import Builder, die, stair, write_out

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] bottom-front-left cell of the shaft; y = shaft base layer
    "width": 2,                    # shaft footprint along x: 1-2
    "depth": 2,                    # shaft footprint along z: 1-2
    "height": 6,                   # shaft height in layers, 1-24
    "material": "minecraft:stone_bricks",
    "cap": "campfire",             # campfire | trapdoor | none
    "facing": "south",             # fireplace/front direction (campfire faces this way)
    "ledge_layer": -1,             # flashing/检修台 ring at this y-offset from origin; -1 = auto (height-3)
    "rim": True,                   # rim course on top of the shaft
    "trim_material": "minecraft:stone_brick_stairs",  # stairs for ledge + rim rings
    "trapdoor_material": "minecraft:spruce_trapdoor"
}

CAPS = ("campfire", "trapdoor", "none")
FACINGS = ("north", "south", "east", "west")

def ledge_ring(b, w, d, y, mat):
    """Upside-down stair ring one cell out, facing outward (backs outward ->
    inner corners, resolved automatically)."""
    for x in range(-1, w + 1):
        b.put(x, y, -1, stair(mat, "north", half="top"))
        b.put(x, y, d, stair(mat, "south", half="top"))
    for z in range(0, d):
        b.put(-1, y, z, stair(mat, "west", half="top"))
        b.put(w, y, z, stair(mat, "east", half="top"))

def build(p):
    ox, oy, oz = p["origin"]
    w, d, h = int(p["width"]), int(p["depth"]), int(p["height"])
    mat, trim = p["material"], p["trim_material"]
    ledge = int(p["ledge_layer"])
    if ledge < 0:
        ledge = max(1, h - 3)
    b = Builder()

    for y in range(h):                             # solid shaft
        for x in range(w):
            for z in range(d):
                b.put(x, y, z, mat)

    ledge_ring(b, w, d, ledge, trim)               # 检修台/泛水 ring at roofline
    if p["rim"]:
        ledge_ring(b, w, d, h, trim)               # rim course on top

    cap = p["cap"]
    for x in range(w):
        for z in range(d):
            if cap == "campfire":
                b.put(x, h, z, "minecraft:campfire[facing=%s,lit=true]" % p["facing"])
            elif cap == "trapdoor":
                b.put(x, h, z, "%s[facing=north,half=bottom,open=false]" % p["trapdoor_material"])
    return b.emit([ox, oy, oz])

def validate(p):
    try:
        w, d, h = int(p["width"]), int(p["depth"]), int(p["height"])
        ledge = int(p["ledge_layer"])
    except (TypeError, ValueError):
        die("width/depth/height/ledge_layer must be ints",
            {"width": "1-2", "depth": "1-2", "height": "1-24", "ledge_layer": "-1=auto or 0..height-1"})
    if not (1 <= w <= 2 and 1 <= d <= 2):
        die("shaft footprint must be 1x1, 1x2 or 2x2", {"width": [1, 2], "depth": [1, 2]})
    if not 1 <= h <= 24:
        die("height out of range", {"height": "1-24"})
    if not -1 <= ledge <= h - 1:
        die("ledge_layer must sit on the shaft", {"ledge_layer": "-1 (auto) or 0..%d" % (h - 1)})
    if p["cap"] not in CAPS:
        die("cap must be one of %s" % (CAPS,), {"cap": list(CAPS)})
    if p["facing"] not in FACINGS:
        die("facing must be one of %s" % (FACINGS,), {"facing": list(FACINGS)})
    if not str(p["trim_material"]).endswith("_stairs"):
        die("trim_material must be a *_stairs id",
            {"trim_material": ["minecraft:stone_brick_stairs", "minecraft:brick_stairs"]})
    if p["cap"] == "trapdoor" and "trapdoor" not in str(p["trapdoor_material"]):
        die("trapdoor_material must be a *_trapdoor id",
            {"trapdoor_material": ["minecraft:spruce_trapdoor", "minecraft:dark_oak_trapdoor",
                                   "minecraft:iron_trapdoor"]})
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
            {"example": '{"origin":[100,64,100],"width":2,"depth":2,"height":6,"cap":"campfire"}'})
    validate(p)
    write_out(build(p), a.out)

if __name__ == "__main__":
    main()
