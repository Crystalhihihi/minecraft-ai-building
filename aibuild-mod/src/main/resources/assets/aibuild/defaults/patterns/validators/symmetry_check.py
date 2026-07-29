#!/usr/bin/env python3
"""symmetry_check.py — deterministic symmetry validator (patterns/validators/).

Reads a JSON block list and checks it is symmetric across the given axis
plane. Every block must have a counterpart at the mirrored position, and the
counterpart's block string must equal the state-remapped mirror (facing and
stair-shape are remapped like mirror_build.py does).

Prints a JSON report to stdout. Exit code: 0 = symmetric, 1 = diffs found.

Usage:
  python validators/symmetry_check.py --params '{"input":"build.json","axis":"x","axis_coord":104.5}'
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import mirror_build  # patterns/ : shared mirror logic

def check(p):
    blocks = mirror_build.load_blocks(p["input"])
    axis, ac = p["axis"], float(p["axis_coord"])
    at = {}
    for b in blocks:
        at[(b["x"], b["y"], b["z"])] = b["block"]
    diffs = []
    for b in blocks:
        if axis == "x":
            mpos = (mirror_build.mirror_coord(b["x"], ac), b["y"], b["z"])
        else:
            mpos = (b["x"], b["y"], mirror_build.mirror_coord(b["z"], ac))
        if mpos == (b["x"], b["y"], b["z"]):
            continue  # on the mirror plane
        expected = mirror_build.mirror_block_state(b["block"], axis)
        actual = at.get(mpos)
        pos = {"x": b["x"], "y": b["y"], "z": b["z"]}
        m = {"x": mpos[0], "y": mpos[1], "z": mpos[2]}
        if actual is None:
            diffs.append({"type": "missing_mirror", "pos": pos, "mirror_pos": m, "block": b["block"]})
        elif actual != expected:
            diffs.append({"type": "mismatch", "pos": pos, "mirror_pos": m,
                          "block": b["block"], "expected_at_mirror": expected, "actual_at_mirror": actual})
    return {"symmetric": not diffs, "checked_blocks": len(blocks), "diff_count": len(diffs), "diffs": diffs}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    a = ap.parse_args()
    p = {"input": "build.json", "axis": "x", "axis_coord": 0}
    p.update(json.loads(a.params) if a.params.strip() else {})
    report = check(p)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    sys.exit(0 if report["symmetric"] else 1)

if __name__ == "__main__":
    main()
