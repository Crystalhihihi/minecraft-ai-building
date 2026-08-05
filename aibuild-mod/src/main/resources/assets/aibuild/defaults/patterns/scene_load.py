#!/usr/bin/env python3
"""scene_load.py — 从 scene 计划重建聚落方块 (multi-paradigm settlement loader).

Consumes a scene plan (settlement.py, see 调研/scene-format.md) and emits the
actual blocks:

- PATTERN entries (roads / paths / plaza / altar) -> run their generator.
- STYLE entries (building cards with no generator, e.g. medieval_house) ->
  emit a deterministic PLACEHOLDER building (box + gable roof) so the
  settlement has full geometry for preview, AND list them in `pending` with
  the real card reference for the LLM builder to replace.

Optional post-processing (borrowed from emreulsy procedural village gen):
- terrain adaptation: if a heightmap file is given, each piece's origin y is
  lifted onto the surface (max height over its footprint, +1), so buildings
  sit on terrain instead of floating / being buried.
- flatten: after placing, emit a cobblestone foundation pad under any piece
  whose footprint spans uneven terrain (fill from terrain to its base y).
- collision detection: if enabled, pieces overlapping already-placed blocks
  are skipped and recorded in `pending` (collision report).

Deterministic: same scene + same heightmap -> same blocks.

Output: {"blocks":[...], "pending":[...]} (set_blocks compatible).

Usage:
  python scene_load.py --params '{"scene":"town.json","terrain":"hmap.json"}' --out town_blocks.json
"""
import argparse, json, os, sys, subprocess
from pathlib import Path

PY_DIR = Path(__file__).resolve().parent


def load_heightmap(path):
    """Read a heightmap file. Formats:
      {"heights": [[h00,h01,...],[...]], "base_y":N, "origin":[x0,z0]}  2D grid
      {"cells": {"x,z": h, ...}, "base_y":N}                              sparse dict
    Returns (fn(x,z)->h_or_None, base_y). fn returns None outside known cells.
    """
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    base_y = d.get("base_y", 0)
    cells = {}
    if "heights" in d:
        rows = d["heights"]
        x0, z0 = d.get("origin", [0, 0])
        for zi, row in enumerate(rows):
            for xi, h in enumerate(row):
                if h is not None:
                    cells[(x0 + xi, z0 + zi)] = int(h)
    elif "cells" in d:
        for k, v in d["cells"].items():
            try:
                x, z = (int(t) for t in k.split(","))
            except ValueError:
                continue
            cells[(x, z)] = int(v)
    def hmap(x, z):
        return cells.get((x, z))
    return hmap, base_y


def _footprint(params):
    """Best-effort footprint (w,d) from a piece's params; default 5x5.
    FIX 2026-08-03: road_segment is direction-aware — for `direction="x"` the
    length runs along x (width), for `direction="z"` it runs along z. Earlier
    code ignored `direction` and always took (width, length), so a horizontal
    road's footprint sampled the wrong strip on a heightmap (only its start
    corner). Now the axis matches the generator's actual footprint."""
    direction = params.get("direction")
    if direction == "x":
        # length along x, width along z
        w = params.get("length") or params.get("width") or 5
        d = params.get("width") or params.get("depth") or 5
    elif direction == "z":
        # length along z, width along x
        w = params.get("width") or params.get("depth") or 5
        d = params.get("length") or params.get("width") or 5
    else:
        w = params.get("w") or params.get("width") or params.get("length") or 5
        d = params.get("d") or params.get("depth") or params.get("length") or 5
    return int(w), int(d)


def adapt_origin(params, hmap, base_y, lift=1):
    """If a heightmap is present, lift the piece's origin.y onto the terrain.
    Uses the MAX surface height over the footprint (find dry high ground so the
    piece never floats over a dip). Returns (new_params, terrain_found)."""
    if hmap is None:
        return params, False
    ox, oy, oz = params["origin"]
    w, d = _footprint(params)
    hs = []
    for dx in range(w):
        for dz in range(d):
            h = hmap(ox + dx, oz + dz)
            if h is not None:
                hs.append(h)
    if not hs:
        return params, False
    surface = max(hs)
    target = surface + lift
    newp = dict(params)
    newp["origin"] = [ox, target, oz]
    return newp, (target != oy)


def foundation_pad(origin, hmap, base_y, params, pad_material):
    """Emit a cobblestone/dirt pad filling from terrain surface up to the piece
    base y, under the piece footprint — so a piece on uneven ground isn't
    floating. Returns list of blocks (empty if terrain not used or even)."""
    if hmap is None:
        return []
    ox, oy, oz = origin
    w, d = _footprint(params)
    blocks = []
    for dx in range(w):
        for dz in range(d):
            h = hmap(ox + dx, oz + dz)
            if h is None:
                continue
            for y in range(h + 1, oy):   # fill from surface up to piece base
                blocks.append({"x": ox + dx, "y": y, "z": oz + dz,
                               "block": pad_material})
    return blocks


def collision_report(blocks):
    """Detect overlapping coordinates in a block list. Returns list of dupes."""
    seen = {}
    dupes = []
    for b in blocks:
        key = (b["x"], b["y"], b["z"])
        if key in seen:
            dupes.append({"x": b["x"], "y": b["y"], "z": b["z"],
                          "a": seen[key], "b": b["block"]})
        else:
            seen[key] = b["block"]
    return dupes

def run_generator(script, params, out_dir):
    tmp = os.path.join(out_dir, "_scene_tmp_%d.json" % os.getpid())
    cmd = [sys.executable, str(PY_DIR / script), "--params",
           json.dumps(params), "--out", tmp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        _try_remove(tmp)
        raise RuntimeError("%s failed: %s" % (script, r.stderr.strip()[-400:]))
    with open(tmp, encoding="utf-8") as f:
        blocks = json.load(f)["blocks"]
    _try_remove(tmp)
    return blocks


def _try_remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _placeholder_building(params):
    """Deterministic box + gable roof so a style lot gets full geometry.
    Size from params w/d/h (default 5x5x4); rotates so the gable front faces
    `facing` (roof ridge runs perpendicular to facing)."""
    ox, oy, oz = params["origin"]
    facing = params.get("facing", "south")
    w = max(3, min(15, int(params.get("w", 5))))
    d = max(3, min(15, int(params.get("d", 5))))
    h = max(2, min(8, int(params.get("h", 4))))
    blocks = []
    wall = "minecraft:oak_planks"
    roof = "minecraft:spruce_stairs"
    slab = "minecraft:spruce_slab"
    base = "minecraft:cobblestone"
    beam = "minecraft:oak_planks"
    # rotate canonical (x along width, z along depth, front at z=d) so the
    # front faces `facing`; remap the roof stair facings accordingly
    ROT = {
        "south": (lambda x, z: (x, z),  {"south": "south", "north": "north"}),
        "north": (lambda x, z: (-x, -z), {"south": "north", "north": "south"}),
        "east":  (lambda x, z: (z, -x),  {"south": "east", "north": "west"}),
        "west":  (lambda x, z: (-z, x),  {"south": "west", "north": "east"}),
    }
    rot, fmap = ROT.get(facing, ROT["south"])

    def emit(x, y, z, block):
        wx, wz = rot(x, z)
        blocks.append({"x": ox + wx, "y": oy + y, "z": oz + wz, "block": block})

    # base + walls (canonical coords, rotated on emit)
    for x in range(w):
        for z in range(d):
            emit(x, 0, z, base)
    # front wall is z=d-1 (facing side); cut a 1x2 door at x=w//2 so the
    # placeholder is enterable (E7: "能进" before "好看")
    door_x = w // 2
    for y in range(1, h):
        for x in range(w):
            emit(x, y, 0, wall)
            if not (x == door_x and y in (1, 2)):  # skip the door opening
                emit(x, y, d - 1, wall)
        for z in range(1, d - 1):
            emit(0, y, z, wall)
            emit(w - 1, y, z, wall)
    # gable roof: rows rise toward the ridge (along z), front faces `facing`
    ridge = h
    half = d // 2
    for i in range(half + 1):
        y = ridge + i
        zn, zs = i, d - 1 - i
        if zn > zs:
            break
        for x in range(w):
            if zn == zs:
                emit(x, y - 1, zn, beam)   # solid beam, never floating slab
                emit(x, y, zn, slab + "[type=top]")
            else:
                emit(x, y, zn, roof + "[facing=%s,half=bottom]" % fmap["south"])
                emit(x, y, zs, roof + "[facing=%s,half=bottom]" % fmap["north"])
    return blocks


def build(p):
    with open(p["scene"], encoding="utf-8") as f:
        scene = json.load(f)
    # optional terrain adaptation
    hmap = None
    if p.get("terrain"):
        hmap, base_y = load_heightmap(p["terrain"])
    else:
        base_y = 0
    pad_mat = p.get("pad_material", "minecraft:cobblestone")
    do_collision = bool(p.get("collision", False))
    blocks = []
    placed_occupied = set()   # (x,y,z) already placed (for collision)
    pending = []
    out_path = p.get("out", "_scene_blocks.json")
    out_dir = os.path.dirname(out_path) or "."

    def emit(b):
        """Add a block, skipping duplicates at the same coordinate (last-free
        dedupe: a road crossing lays the same cell twice — keep the first)."""
        key = (b["x"], b["y"], b["z"])
        if key in placed_occupied:
            return False
        blocks.append(b)
        placed_occupied.add(key)
        return True

    def place_piece(item, params_override=None):
        """Run a pattern generator for a piece (with terrain-adapted origin),
        return the blocks; None if it collides (collision mode)."""
        script = item["card"] + ".py"
        params = dict(item["params"])
        if params_override:
            params.update(params_override)
        adapted, _used = adapt_origin(params, hmap, base_y)
        if hmap is not None and _used:
            # also fill the pad under the piece so it sits on terrain
            pad = foundation_pad(adapted["origin"], hmap, base_y, params, pad_mat)
            for b in pad:
                emit(b)
        try:
            bl = run_generator(script, adapted, out_dir)
        except RuntimeError as e:
            pending.append({"card": item["card"], "params": adapted,
                            "reason": "generator_error", "detail": str(e)})
            return None
        if do_collision:
            hit = [b for b in bl if (b["x"], b["y"], b["z"]) in placed_occupied]
            if hit:
                pending.append({"card": item["card"], "params": adapted,
                                "reason": "collision",
                                "detail": "overlaps %d placed block(s)" % len(hit)})
                return None
        for b in bl:
            emit(b)
        return bl

    # pattern entries: roads + paths + center
    items = (scene.get("roads") or []) + (scene.get("paths") or [])
    if scene.get("center"):
        items = items + [scene["center"]]
    for item in items:
        if not item or item.get("kind") != "pattern":
            continue
        place_piece(item)

    # lots: pattern (tree/pond) -> generator; style (building) -> placeholder
    for lot in scene.get("lots") or []:
        kind = lot.get("kind", "style")
        if kind == "pattern":
            place_piece(lot)
        else:
            params = dict(lot["params"])
            adapted, _used = adapt_origin(params, hmap, base_y)
            if hmap is not None and _used:
                pad = foundation_pad(adapted["origin"], hmap, base_y, params, pad_mat)
                for b in pad:
                    emit(b)
            bl = _placeholder_building(adapted)
            if do_collision:
                hit = [b for b in bl if (b["x"], b["y"], b["z"]) in placed_occupied]
                if hit:
                    pending.append({"card": lot["card"], "kind": "style",
                                    "params": adapted, "reason": "collision",
                                    "detail": "overlaps %d placed block(s)" % len(hit)})
                    continue
            for b in bl:
                emit(b)
            pending.append({"card": lot["card"], "kind": "style",
                            "params": adapted, "reason": "style_card_placeholder"})

    report = {"scene_id": scene.get("scene_id"), "blocks": blocks,
              "pending": pending, "collisions": collision_report(blocks)}
    if hmap is not None:
        report["terrain_adapted"] = True
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    p = {"scene": "settlement.json", "out": "scene_blocks.json",
         "terrain": None, "collision": False,
         "pad_material": "minecraft:cobblestone"}
    p.update(json.loads(a.params) if a.params.strip() else {})
    if a.out:
        p["out"] = a.out
    out = build(p)
    blocks = out.pop("blocks")
    payload = dict(out)
    payload["blocks"] = blocks
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print("wrote %d blocks, %d pending to %s"
              % (len(blocks), len(payload["pending"]), a.out), file=sys.stderr)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

