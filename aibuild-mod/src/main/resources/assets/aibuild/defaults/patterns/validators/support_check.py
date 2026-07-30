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

# 不需要支撑的白名单(名称子串匹配)
WHITELIST = (
    "air", "_leaves", "vine", "lichen", "vein", "hanging_roots", "roots",
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
    return any(w in n for w in WHITELIST)


def check(p):
    blocks = mirror_build.load_blocks(p["blocks"])
    base = mirror_build.load_blocks(p["base"]) if p.get("base") else []
    solid = {(b["x"], b["y"], b["z"]) for b in blocks}
    solid |= {(b["x"], b["y"], b["z"]) for b in base}
    min_y = min(b["y"] for b in blocks) if blocks else 0

    floaters = []
    for b in blocks:
        name, props = parse(b["block"])
        if whitelisted(name):
            continue
        below = (b["x"], b["y"] - 1, b["z"])
        supported = below in solid or b["y"] == min_y
        if "_slab" in name and props.get("type") == "top":
            if not supported:
                floaters.append({"x": b["x"], "y": b["y"], "z": b["z"],
                                 "block": b["block"], "reason": "floating_top_slab"})
        elif not supported:
            floaters.append({"x": b["x"], "y": b["y"], "z": b["z"],
                             "block": b["block"], "reason": "no_block_below"})
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
