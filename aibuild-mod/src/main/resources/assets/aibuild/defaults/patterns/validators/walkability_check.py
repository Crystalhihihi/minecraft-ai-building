#!/usr/bin/env python3
"""walkability_check.py — deterministic "can a 2-tall agent walk in?" validator
(patterns/validators/). Ported from the E7 walkability experiment
(docs/plans/2026-07-31-e7-inside-out.md): style cards can place furniture, but
only a flood-fill from the door proves the building is actually ENTERABLE.

Reads a JSON block list (floor + walls + furniture in ONE file — air cells are
implicit) plus a door coordinate and optional required points, then BFS-walks
a 2-block-tall agent from the door:

- standable(x,y,z) = passable(y) and passable(y+1) and support(y-1)
  (standing ON a stair/slab at y also counts)
- passable = air, decor whitelist (torches/plants/carpets/signs...), doors,
  trapdoors, stairs, slabs; glass is a WALL for walking purposes
- support = not passable, or stair/slab
- moves: 4-neighbours, dy in {0,±1} (±2 only while on stairs/slabs);
  stepping up needs head clearance at y+2

`door` need not be exact: the nearest standable cell within radius 4 is used
as the BFS start. Each `require` point is "reachable" if its nearest
standable cell (radius 4) is in the walked set — i.e. the agent can stand in
front of every required piece / at every required spot.

Prints a JSON report to stdout. Exit code: 0 = all required points reachable,
1 = some required point unreachable (or no standable cell near the door).

Usage:
  python validators/walkability_check.py --params '{"blocks":"room.json","door":[103,65,108],"require":[[103,65,103]]}'
"""
import argparse, json, sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import mirror_build  # patterns/ : for load_blocks

# 可通行白名单(精确匹配;名称已去掉 minecraft: 前缀和 [state] 后缀)
PASS_EXACT = {
    "air", "cave_air", "void_air", "lantern", "soul_lantern", "chain",
    "torch", "wall_torch", "soul_torch", "soul_wall_torch", "redstone_torch",
    "redstone_wall_torch", "lever", "tripwire", "tripwire_hook", "string",
    "short_grass", "tall_grass", "fern", "large_fern", "dead_bush", "snow",
    "poppy", "dandelion", "blue_orchid", "allium", "cornflower",
    "lily_of_the_valley", "wither_rose", "sunflower", "lilac", "peony",
    "rose_bush", "sweet_berry_bush", "ladder", "vine", "rail", "powered_rail",
    "detector_rail", "activator_rail", "redstone_wire", "repeater",
    "comparator",
}

PASS_SUFFIX = (
    "_carpet", "_sign", "_wall_sign", "_hanging_sign",
    "_wall_hanging_sign", "_button", "_pressure_plate",
    "_flower_pot", "_sapling", "_door", "_trapdoor", "_pane",
    "_bed", "_banner",
)

# windows are walls for walking purposes (checked BEFORE the _pane suffix)
GLASS_EXACT = {"glass", "glass_pane", "tinted_glass"}


def base_name(block):
    """'minecraft:spruce_stairs[facing=north,...]' -> 'spruce_stairs'."""
    name = block.split("[", 1)[0]
    return name.split(":", 1)[1] if ":" in name else name


def is_stair_or_slab(name):
    return name.endswith("_stairs") or name.endswith("_slab")


def passable(block):
    name = base_name(block)
    if name in GLASS_EXACT:
        return False
    if name in PASS_EXACT or is_stair_or_slab(name):
        return True
    return any(name.endswith(suf) for suf in PASS_SUFFIX)


def support(block):
    name = base_name(block)
    return (not passable(block)) or is_stair_or_slab(name)


def check(p):
    blocks = mirror_build.load_blocks(p["blocks"])
    grid = {}
    for b in blocks:  # last write wins (dedup like set_blocks)
        grid[(b["x"], b["y"], b["z"])] = b["block"]
    if not blocks:
        return {"ok": False, "error": "empty block list",
                "reachable_cells": 0, "requires": []}
    # bounding box of the built region (+1 margin) — BFS must consider air
    # cells (door openings, empty rooms) which are NOT in `grid`; the bounds
    # keep the walk bounded to the built area instead of spreading forever.
    xs = [b["x"] for b in blocks]; ys = [b["y"] for b in blocks]
    zs = [b["z"] for b in blocks]
    min_x, max_x = min(xs) - 1, max(xs) + 1
    min_y, max_y = min(ys) - 1, max(ys) + 1
    min_z, max_z = min(zs) - 1, max(zs) + 1

    def in_bounds(c):
        x, y, z = c
        return (min_x <= x <= max_x and min_y <= y <= max_y
                and min_z <= z <= max_z)

    def cell(c):
        return grid.get(c, "minecraft:air")

    def standable(c):
        x, y, z = c
        return (passable(cell((x, y, z))) and passable(cell((x, y + 1, z)))
                and (support(cell((x, y - 1, z)))
                     or is_stair_or_slab(base_name(cell((x, y, z))))))

    def neighbors(c):
        x, y, z = c
        on_partial = (is_stair_or_slab(base_name(cell((x, y, z))))
                      or is_stair_or_slab(base_name(cell((x, y - 1, z)))))
        out = []
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1, 2, -2):
                if abs(dy) == 2 and not on_partial:
                    continue
                q = (x + dx, y + dy, z + dz)
                if not in_bounds(q):
                    continue
                if dy > 0 and not passable(cell((x, y + 2, z))):
                    continue  # head clearance when stepping up
                if standable(q):
                    out.append(q)
        return out

    def nearest_standable(c, radius=4):
        x, y, z = c
        best, best_d = None, 1e9
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    q = (x + dx, y + dy, z + dz)
                    if not in_bounds(q):
                        continue
                    if standable(q):
                        d = abs(dx) + abs(dy) + abs(dz)
                        if d < best_d:
                            best, best_d = q, d
        return best

    door = tuple(int(v) for v in p["door"])
    start = nearest_standable(door)
    if start is None:
        return {"ok": False, "error": "no standable cell near door",
                "door": list(door), "reachable_cells": 0, "requires": []}

    seen = {start}
    dq = deque([start])
    while dq:
        c = dq.popleft()
        for q in neighbors(c):
            if q not in seen:
                seen.add(q)
                dq.append(q)

    requires = []
    for r in p.get("require", []):
        pt = tuple(int(v) for v in r)
        st = nearest_standable(pt)
        requires.append({"point": list(pt),
                         "reachable": (st in seen) if st else False,
                         "standable_near": st is not None})
    ok = all(r["reachable"] for r in requires) if requires else True
    return {"ok": ok, "door": list(door), "start": list(start),
            "reachable_cells": len(seen), "requires": requires}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    a = ap.parse_args()
    p = {"blocks": "blocks.json", "door": [0, 65, 0], "require": []}
    p.update(json.loads(a.params) if a.params.strip() else {})
    report = check(p)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    sys.exit(0 if report.get("ok") else 1)


if __name__ == "__main__":
    main()
