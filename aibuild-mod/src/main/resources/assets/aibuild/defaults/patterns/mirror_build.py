#!/usr/bin/env python3
"""mirror_build.py — complete a symmetric build from its half (对称镜像补全).

Takes a JSON block list describing ONE half of a symmetric structure (plus
optionally the on-axis blocks) and emits the full list: every block mirrored
across the given axis plane. Blocks on the plane are kept once (first
occurrence wins, duplicates dropped). Directional block states are remapped
on the mirrored side: facing east<->west (axis=x) / north<->south (axis=z),
stair shape left<->right.

Usage:
  python mirror_build.py --params '{"input":"half.json","axis":"x","axis_coord":100}' --out full.json
  axis_coord may be a half-integer (e.g. 99.5) for a plane BETWEEN block rows.
"""
import argparse, json, sys

FACING_MIRROR = {
    "x": {"east": "west", "west": "east"},
    "z": {"north": "south", "south": "north"},
}
SHAPE_MIRROR = {
    "outer_left": "outer_right", "outer_right": "outer_left",
    "inner_left": "inner_right", "inner_right": "inner_left",
}

def mirror_block_state(block, axis):
    """Remap directional states for the mirrored side. Id/state string in,
    mirrored string out."""
    if "[" not in block:
        return block
    base, props = block.split("[", 1)
    props = props.rstrip("]")
    out = []
    for kv in props.split(","):
        k, _, v = kv.partition("=")
        if k == "facing":
            v = FACING_MIRROR.get(axis, {}).get(v, v)
        elif k == "shape":
            v = SHAPE_MIRROR.get(v, v)
        out.append("%s=%s" % (k, v))
    return base + "[" + ",".join(out) + "]"

def mirror_coord(c, axis_coord):
    """Mirror a block coordinate across the plane; plane may sit at .5."""
    return int(round(2.0 * float(axis_coord) - c))

def mirror_blocks(blocks, axis, axis_coord):
    """blocks: iterable of {x,y,z,block}. Returns the completed full list
    (originals + mirrored, on-axis kept once, order stable)."""
    result, seen = [], set()
    for b in blocks:
        key = (b["x"], b["y"], b["z"])
        if key not in seen:
            seen.add(key)
            result.append({"x": b["x"], "y": b["y"], "z": b["z"], "block": b["block"]})
    for b in blocks:
        if axis == "x":
            mx, my, mz = mirror_coord(b["x"], axis_coord), b["y"], b["z"]
        else:
            mx, my, mz = b["x"], b["y"], mirror_coord(b["z"], axis_coord)
        key = (mx, my, mz)
        if key in seen:
            continue  # on the mirror plane (or already produced): keep once
        seen.add(key)
        result.append({"x": mx, "y": my, "z": mz, "block": mirror_block_state(b["block"], axis)})
    return result

def load_blocks(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data["blocks"]
    return data

def build(p):
    blocks = load_blocks(p["input"])
    return mirror_blocks(blocks, p["axis"], float(p["axis_coord"]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    p = {"input": "half.json", "axis": "x", "axis_coord": 0}
    p.update(json.loads(a.params) if a.params.strip() else {})
    out = json.dumps({"blocks": build(p)}, ensure_ascii=False)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print("wrote %d blocks to %s" % (len(json.loads(out)["blocks"]), a.out), file=sys.stderr)
    else:
        print(out)

if __name__ == "__main__":
    main()
