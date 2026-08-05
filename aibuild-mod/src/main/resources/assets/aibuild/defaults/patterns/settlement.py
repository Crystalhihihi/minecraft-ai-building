#!/usr/bin/env python3
"""settlement.py — 聚落布局生成器 (multi-paradigm settlement layout planner).

Produces a SCENE PLAN (JSON, not blocks) for a settlement or park: a set of
building lots + road/path network + optional center node (plaza / altar).
The scene is consumed by scene_load.py to emit geometry (roads, plaza, altar)
and to list style lots for the LLM builder. Deterministic from seed.

Layout modes (`mode`):
  grid    — orthogonal road grid, rectangular lots (urban/classical).
  radial  — concentric ring roads + radiating spokes around a center (medieval
            town / fortress city); lots between rings.
  organic — winding paths (jittered grid), irregular lots (countryside).
  park    — green space with tiers of paths around a central altar; lots are
            planted features (trees/ponds) + a big altar node.

Center nodes (`centerpiece`): none | plaza | altar (big ceremonial dais).
Output scene schema: 调研/scene-format.md.

Usage:
  python settlement.py --params '{"rows":3,"cols":3,"cell":8,"mode":"grid"}' --out town.json
  python settlement.py --params '{"rows":3,"cols":3,"mode":"radial"}' --out city.json
  python settlement.py --params '{"mode":"park","size":16}' --out park.json
"""
import argparse, json, math, sys

DEFAULTS = {
    "scene_id": "settlement",
    "origin": [0, 64, 0],
    "mode": "grid",             # grid | radial | organic | park
    "rows": 3, "cols": 3,       # grid: lots per side
    "cell": 8,                  # grid: lot width
    "road_width": 2,            # road/path width
    "rings": 3,                 # radial/park: number of rings
    "size": 16,                 # park: outer extent (radius)
    "lots": [],
    "default_card": "medieval_house",
    "centerpiece": "plaza",     # none | plaza | altar
    "center_card": "plaza",     # pattern card for plaza center
    "altar_params": {},         # extra params for altar center
    "seed": 0,
}

DIRS8 = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def _grid(p):
    rows = max(1, int(p["rows"])); cols = max(1, int(p["cols"]))
    cell = max(3, int(p["cell"])); rw = max(1, int(p["road_width"]))
    ox, oy, oz = p["origin"]
    step = cell + rw
    lots, roads = [], []
    for i in range(rows + 1):
        z = oz + i * step - rw // 2
        roads.append({"card": "road_segment", "kind": "pattern",
                      "params": {"origin": [ox, oy, z], "direction": "x",
                                 "length": cols * step + rw, "width": rw}})
    for j in range(cols + 1):
        x = ox + j * step - rw // 2
        roads.append({"card": "road_segment", "kind": "pattern",
                      "params": {"origin": [x, oy, oz], "direction": "z",
                                 "length": rows * step + rw, "width": rw}})
    auto = not p["lots"]
    for i in range(rows):
        for j in range(cols):
            cx = ox + j * step + cell // 2; cz = oz + i * step + cell // 2
            if auto:
                card, facing = p["default_card"], "south"
            else:
                e = p["lots"][i * cols + j] if i * cols + j < len(p["lots"]) else [p["default_card"], "south"]
                card, facing = e[0], (e[1] if len(e) > 1 else "south")
            lots.append({"card": card, "kind": "style",
                         "params": {"origin": [cx, oy, cz], "facing": facing}})
    center = _center(p, ox, oy, oz, (cols // 2) * step + cell // 2,
                     (rows // 2) * step + cell // 2, cell + rw)
    return roads, lots, center


def _radial(p):
    rings = max(2, min(6, int(p["rings"]))); rw = max(1, int(p["road_width"]))
    ox, oy, oz = p["origin"]
    ring_gap = max(6, int(p["cell"]) + 2)   # spacing between ring roads
    lots, roads = [], []
    # 4 orthogonal spokes (real road_segment, center <-> outermost ring)
    outer_r = rings * ring_gap
    spokes = [
        # east: from center toward +x
        {"dir": "x", "ox": 0, "oz": 0},
        # west: from center-outer_r toward +x (reaches center)
        {"dir": "x", "ox": -outer_r, "oz": 0},
        # south: from center toward +z
        {"dir": "z", "ox": 0, "oz": 0},
        # north: from center-outer_r toward +z (reaches center)
        {"dir": "z", "ox": 0, "oz": -outer_r},
    ]
    for sp in spokes:
        roads.append({"card": "road_segment", "kind": "pattern",
                      "params": {"origin": [ox + sp["ox"], oy, oz + sp["oz"]],
                                 "direction": sp["dir"],
                                 "length": outer_r + 1, "width": rw}})
    for k in range(1, rings + 1):
        r = k * ring_gap
        # FIX 2026-08-03: plaza.py clamps width/depth to max 41; with large
        # rings (default rings=3, cell=8 -> r=30, width=61) the plaza would
        # `die()` and the whole ring be dropped. Clamp the plaza ring to 41 so
        # the radial layout is always valid (the ring still circles the centre).
        w = min(2 * r + 1, 41)
        roads.append({"card": "plaza", "kind": "pattern",
                      "params": {"origin": [ox, oy, oz], "width": w,
                                 "depth": w, "pattern": "concentric",
                                 "materials": ["minecraft:gravel", "minecraft:coarse_dirt"],
                                 "centerpiece": "none", "benches": False, "lamps": False}})
    # lots between rings, on diagonal directions (avoid the 4 spoke roads)
    auto = not p["lots"]
    lot_idx = 0
    DIAG = [1, 3, 5, 7]  # DIRS8 diagonal indices: NE,NW,SW,SE
    for k in range(1, rings):
        r_in = k * ring_gap; r_out = (k + 1) * ring_gap
        mid = (r_in + r_out) // 2
        for s in DIAG:
            dx, dz = DIRS8[s]
            cx = ox + dx * mid; cz = oz + dz * mid
            if auto:
                card, facing = p["default_card"], "south"
            else:
                e = p["lots"][lot_idx] if lot_idx < len(p["lots"]) else [p["default_card"], "south"]
                card, facing = e[0], (e[1] if len(e) > 1 else "south")
            lot_idx += 1
            lots.append({"card": card, "kind": "style",
                         "params": {"origin": [cx, oy, cz], "facing": facing}})
    center = _center(p, ox, oy, oz, 0, 0, 2 * ring_gap - 2)
    return roads, lots, center


def _organic(p):
    rows = max(1, int(p["rows"])); cols = max(1, int(p["cols"]))
    cell = max(3, int(p["cell"])); rw = max(1, int(p["road_width"]))
    ox, oy, oz = p["origin"]; seed = int(p["seed"])
    step = cell + rw
    rng = __import__("random").Random(seed)
    lots, roads = [], []
    # jittered winding path grid (simple: jitter the road lines)
    for i in range(rows + 1):
        z = oz + i * step - rw // 2 + (rng.randint(-2, 2) if 0 < i < rows else 0)
        roads.append({"card": "road_segment", "kind": "pattern",
                      "params": {"origin": [ox, oy, z], "direction": "x",
                                 "length": cols * step + rw, "width": rw}})
    for j in range(cols + 1):
        x = ox + j * step - rw // 2 + (rng.randint(-2, 2) if 0 < j < cols else 0)
        roads.append({"card": "road_segment", "kind": "pattern",
                      "params": {"origin": [x, oy, oz], "direction": "z",
                                 "length": rows * step + rw, "width": rw}})
    auto = not p["lots"]
    for i in range(rows):
        for j in range(cols):
            jx = rng.randint(-1, 1) if 0 < i < rows else 0
            jz = rng.randint(-1, 1) if 0 < j < cols else 0
            cx = ox + j * step + cell // 2 + jz
            cz = oz + i * step + cell // 2 + jx
            if auto:
                card, facing = p["default_card"], "south"
            else:
                e = p["lots"][i * cols + j] if i * cols + j < len(p["lots"]) else [p["default_card"], "south"]
                card, facing = e[0], (e[1] if len(e) > 1 else "south")
            lots.append({"card": card, "kind": "style",
                         "params": {"origin": [cx, oy, cz], "facing": facing}})
    center = _center(p, ox, oy, oz, (cols // 2) * step + cell // 2,
                     (rows // 2) * step + cell // 2, cell + rw)
    return roads, lots, center


def _park(p):
    size = max(10, min(32, int(p["size"]))); rw = max(1, int(p["road_width"]))
    ox, oy, oz = p["origin"]; seed = int(p["seed"])
    rings = max(2, min(4, int(p.get("rings", 3))))
    lots, paths = [], []
    # circular paths (plaza rings) + planted features on rings
    for k in range(1, rings):
        r = size * k // rings
        paths.append({"card": "plaza", "kind": "pattern",
                      "params": {"origin": [ox, oy, oz], "width": 2 * r + 1,
                                 "depth": 2 * r + 1, "pattern": "concentric",
                                 "materials": ["minecraft:dirt_path", "minecraft:gravel"],
                                 "centerpiece": "none", "benches": True, "lamps": False}})
    rng = __import__("random").Random(seed)
    # planted trees/flowers on the middle ring, between paths
    mid_r = size * 2 // rings // 2
    n_plants = max(4, rings * 4)
    for i in range(n_plants):
        a = 2 * math.pi * i / n_plants + rng.uniform(0, 0.4)
        r = mid_r + rng.randint(-2, 2)
        cx = ox + int(round(math.cos(a) * r)); cz = oz + int(round(math.sin(a) * r))
        if i % 3 == 0:
            lots.append({"card": "garden_tree", "kind": "pattern",
                         "params": {"origin": [cx, oy, cz],
                                    "species": rng.choice(["oak", "cherry", "spruce"]),
                                    "size": "large"}})
        else:
            lots.append({"card": "flower_field", "kind": "pattern",
                         "params": {"origin": [cx - 4, oy, cz - 3], "width": 9,
                                    "depth": 7, "scheme": "meadow"}})
    # park buildings (style) on the outermost ring, facing center
    build_card = p.get("park_building", p["default_card"])
    n_build = max(4, rings * 2)
    outer_r = size - max(3, size // 5)
    for i in range(n_build):
        a = 2 * math.pi * i / n_build + rng.uniform(0, 0.3)
        cx = ox + int(round(math.cos(a) * outer_r))
        cz = oz + int(round(math.sin(a) * outer_r))
        # facing toward center
        facing = "north" if cz < oz else "south" if cz > oz else ("west" if cx < ox else "east")
        lots.append({"card": build_card, "kind": "style",
                     "params": {"origin": [cx, oy, cz], "facing": facing}})
    center = _center(p, ox, oy, oz, 0, 0, size // 2, default_altar=True)
    return paths, lots, center


def _center(p, ox, oy, oz, cx, cz, csize, default_altar=False):
    cp = p.get("centerpiece", "plaza")
    if cp == "none":
        return None
    if cp == "altar" or default_altar:
        ap = {"origin": [ox + cx, oy, oz + cz]}
        ap.update(p.get("altar_params", {}))
        return {"card": "altar", "kind": "pattern", "params": ap, "centerpiece": "altar"}
    # plaza (possibly with fountain centerpiece)
    return {"card": p.get("center_card", "plaza"), "kind": "pattern",
            "params": {"origin": [ox + cx, oy, oz + cz], "width": csize,
                       "depth": csize},
            "centerpiece": cp}


def build(p):
    ox, oy, oz = p["origin"]
    mode = p.get("mode", "grid")
    if mode == "radial":
        roads, lots, center = _radial(p)
    elif mode == "organic":
        roads, lots, center = _organic(p)
    elif mode == "park":
        roads, lots, center = _park(p)
    else:
        roads, lots, center = _grid(p)
    return {"scene_id": p["scene_id"],
            "meta": {"mode": mode, "seed": int(p.get("seed", 0)),
                     "generator": "settlement",
                     "origin": [ox, oy, oz], "params": dict(p)},
            "origin": [ox, oy, oz], "center": center,
            "roads": roads, "lots": lots}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    p = dict(DEFAULTS)
    p.update(json.loads(a.params) if a.params.strip() else {})
    out = json.dumps(build(p), ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print("wrote scene %s" % a.out, file=sys.stderr)
    else:
        print(out)

if __name__ == "__main__":
    main()
