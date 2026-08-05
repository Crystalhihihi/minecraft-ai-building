#!/usr/bin/env python3
"""support_check.py — deterministic floating-block validator (patterns/validators/).

Reads a JSON block list and flags blocks that would visually FLOAT:
- any solid-ish block with no support directly below (y-1), and
- top slabs (`[type=top]`) specifically — they render hanging when the cell
  below is air.

Support sources: other entries in the same list, an optional base/ground
file, and entries at the list's minimum y (assumed ground contact).
Whitelist (never need support): leaves, vines, lichen, chains, lanterns,
hanging roots, flowers/grass/saplings, water/lava, fire, cobweb, and items
designed to hang or float.

Prints a JSON report to stdout. Exit code: 0 = all supported, 1 = floaters.

Usage:
  python validators/support_check.py --params '{"blocks":"furniture.json","base":"walls.json"}'
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import mirror_build  # patterns/ : for load_blocks

# 不需要支撑的白名单(名称子串匹配;"air"单独精确匹配,否则 stairs 全被误豁免)
WHITELIST = (
    "_leaves", "vine", "lichen", "vein", "hanging_roots", "roots",
    "spore_blossom", "chain", "lantern", "end_rod", "torch", "candle",
    "flower", "tulip", "orchid", "daisy", "allium", "poppy", "dandelion",
    "grass", "fern", "sapling", "bush", "fungus", "sprouts", "cobweb",
    "water", "lava", "fire", "kelp", "seagrass", "snow", "moss_carpet",
    "carpet", "mushroom", "azalea", "glow_berries", "ladder", "rail",
    "sign", "banner", "button", "lever", "pressure_plate", "tripwire",
)

STATE_RE = re.compile(r"^([a-z0-9_:.]+)(?:\[(.*)\])?$")


def parse(spec):
    m = STATE_RE.match(spec)
    if not m:
        return spec, {}
    name = m.group(1)
    props = {}
    if m.group(2):
        for kv in m.group(2).split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                props[k.strip()] = v.strip()
    return name, props


def whitelisted(name):
    n = name.lower()
    if n in ("air", "minecraft:air", "cave_air", "void_air",
             "minecraft:cave_air", "minecraft:void_air"):
        return True
    return any(w in n for w in WHITELIST)


FACING_DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


def check(p):
    blocks = mirror_build.load_blocks(p["blocks"])
    base = mirror_build.load_blocks(p["base"]) if p.get("base") else []
    solid = {(b["x"], b["y"], b["z"]) for b in blocks}
    solid |= {(b["x"], b["y"], b["z"]) for b in base}
    min_y = min(b["y"] for b in blocks) if blocks else 0

    def supported(pos, name, props):
        x, y, z = pos
        if y == min_y:
            return True
        if (x, y - 1, z) in solid:
            return True
        # hanging from above (upside-down pieces, chandeliers)
        if (x, y + 1, z) in solid:
            return True
        # attached on any horizontal side — reads as connected, not floating
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y, z + dz) in solid:
                return True
        if "_stairs" in name:
            f = props.get("facing")
            if f in FACING_DIRS:
                dx, dz = FACING_DIRS[f]
                # stair slopes rest on the step below-downhill (y-1, -facing)
                if (x - dx, y - 1, z - dz) in solid:
                    return True
        # 45-degree knee brace (斜撑): a stair/log sitting on a diagonal
        # strut is legal when BOTH diagonal ends are connected — one
        # neighbour up-hill (y+1) and one down-hill (y-1) along the same
        # horizontal axis. Without this a mid-strut block with air below
        # and no same-y neighbour is misjudged as floating.
        if "_stairs" in name or "_log" in name:
            for dx, dz in ((1, 0), (0, 1)):
                if (x + dx, y + 1, z + dz) in solid and (x - dx, y - 1, z - dz) in solid:
                    return True
        return False

    floaters = []
    for b in blocks:
        name, props = parse(b["block"])
        if whitelisted(name):
            continue
        pos = (b["x"], b["y"], b["z"])
        below = (b["x"], b["y"] - 1, b["z"])
        if "_slab" in name and props.get("type") == "top":
            if below not in solid:
                floaters.append({"x": b["x"], "y": b["y"], "z": b["z"],
                                 "block": b["block"], "reason": "floating_top_slab"})
        elif not supported(pos, name, props):
            floaters.append({"x": b["x"], "y": b["y"], "z": b["z"],
                             "block": b["block"], "reason": "no_support"})
    return {"all_supported": not floaters,
            "checked": len(blocks), "base_blocks": len(base),
            "floater_count": len(floaters), "floaters": floaters[:100]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    a = ap.parse_args()
    p = {"blocks": "blocks.json"}
    p.update(json.loads(a.params) if a.params.strip() else {})
    report = check(p)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    sys.exit(0 if report["all_supported"] else 1)


if __name__ == "__main__":
    main()
