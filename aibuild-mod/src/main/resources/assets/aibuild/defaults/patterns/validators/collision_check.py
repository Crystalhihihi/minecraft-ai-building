#!/usr/bin/env python3
"""collision_check.py — deterministic overlap validator (patterns/validators/).

Reads TWO JSON block lists (e.g. walls.json and furniture.json) and lists
every coordinate present in BOTH — the intersection must be empty before
placing the second list.

Prints a JSON report to stdout. Exit code: 0 = no overlap, 1 = collisions.

Usage:
  python validators/collision_check.py --params '{"a":"walls.json","b":"furniture.json"}'
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import mirror_build  # patterns/ : for load_blocks

def check(p):
    a_blocks = mirror_build.load_blocks(p["a"])
    b_blocks = mirror_build.load_blocks(p["b"])
    a_at = {(b["x"], b["y"], b["z"]): b["block"] for b in a_blocks}
    collisions = []
    for b in b_blocks:
        key = (b["x"], b["y"], b["z"])
        if key in a_at:
            collisions.append({"x": key[0], "y": key[1], "z": key[2],
                               "a_block": a_at[key], "b_block": b["block"]})
    return {"collision_free": not collisions,
            "a_blocks": len(a_blocks), "b_blocks": len(b_blocks),
            "collision_count": len(collisions), "collisions": collisions}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    a = ap.parse_args()
    p = {"a": "a.json", "b": "b.json"}
    p.update(json.loads(a.params) if a.params.strip() else {})
    report = check(p)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    sys.exit(0 if report["collision_free"] else 1)

if __name__ == "__main__":
    main()
