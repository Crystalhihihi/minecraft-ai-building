#!/usr/bin/env python3
"""dougong.py — 斗拱 (Chinese bracket cluster under the eaves) generator.

Emits a row of stacked, outward-projecting bracket clusters (斗拱) along a
wall, one cluster per column bay, each a tapering staircase of corbels: a
bucket seat (斗) at the column head, then N corbel layers projecting outward
one cell per layer, each corbel capped with an upside-down stair (拱) facing
back into the wall. Optionally capped by a spanning beam (枋) along the row.

The clusters hang in front of a wall face. Every layer is contiguous from the
wall to its outer edge, so the outermost cell is always carried by the cell
beside it (never floating) — see support_check semantics. All direction
states are DERIVED from origin+facing (禁止手改方向状态).

Canonical frame (face-able piece): front = south, u -> +x (along wall, to
the viewer's right), w -> +z (outward = facing), v -> +y (up). The facade
plane is w = -1; clusters project outward from w = 0.

Output: {"blocks":[{x,y,z,block}]} (set_blocks_from_file compatible).

Usage:
  python dougong.py --params '{"origin":[100,80,100],"facing":"south","count":3,"spacing":3,"depth":2}' [--out dougong.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import Builder, FACING_ROT, stair, die, write_out

DEFAULTS = {
    "origin": [0, 64, 0],            # [x,y,z] bottom-LEFT cell of the wall face (outside view); y = column-head layer
    "facing": "south",               # outward direction the brackets project to
    "count": 3,                      # number of clusters in the row, 1-12
    "spacing": 3,                    # cells between cluster centers, 2-5
    "depth": 2,                      # corbel layers per cluster (projection depth), 1-3
    "seat_material": "minecraft:dark_oak_planks",  # 斗 seat / inner core
    "corbel_material": "minecraft:dark_oak_stairs",  # 拱 upside-down stair cap
    "beam_material": "minecraft:dark_oak_log",      # 枋 spanning beam over the row
    "wall_stub": True,               # emit the wall patch behind the row (self-supporting)
    "wall_material": "minecraft:spruce_log",
}

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}

def build(p):
    ox, oy, oz = p["origin"]
    facing = p["facing"]
    count = max(1, min(12, int(p["count"])))
    spacing = max(2, min(5, int(p["spacing"])))
    depth = max(1, min(3, int(p["depth"])))
    seat, corbel, beam = p["seat_material"], p["corbel_material"], p["beam_material"]
    rot, fmap = FACING_ROT[facing]
    b = Builder(rot=rot, fmap=fmap)

    # canonical: u along wall (+x), w outward (+z), v up (+y); wall at w = -1
    for k in range(count):
        u0 = k * spacing
        if p.get("wall_stub", True):
            for v in range(0, depth + 1):
                b.put(u0, v, -1, p["wall_material"])
        # bucket seat (斗) at the column head
        b.put(u0, 0, 0, seat)
        # corbel layers: inner core contiguous from wall, outer cell capped stair
        for v in range(1, depth + 1):
            for w in range(0, v):
                b.put(u0, v, w, seat)
            b.put(u0, v, v, stair(corbel, OPP[facing], half="top"))
        # spanning beam (枋) across the row at the top
        b.put(u0, depth + 1, 0, beam)
    return b.emit(origin=p["origin"])

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
