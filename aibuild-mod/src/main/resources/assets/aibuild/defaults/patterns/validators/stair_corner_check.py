#!/usr/bin/env python3
"""stair_corner_check.py — frame-corner shape validator (patterns/validators/).

Rule (from the hand-built ground truth, patterns/stair_orientations.md):
in a closed frame of stairs at the same y, corner stairs MUST have a corner
shape (inner_left/inner_right/outer_left/outer_right) — butting two straight
runs leaves gaps or bulges.

Detection: a stair with stair neighbors at the same y on two PERPENDICULAR
sides (e.g. north+east) is a corner candidate; shape must not be "straight".
Reports the candidate's facing + neighbors so the fix is mechanical.
Roof-slope rows are exempted automatically (their neighbors are collinear).

Prints a JSON report. Exit 0 = clean, 1 = violations.

Usage:
  python validators/stair_corner_check.py --params '{"blocks":"blocks.json"}'
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import mirror_build  # patterns/ : for load_blocks

STATE_RE = re.compile(r"^([a-z0-9_:.]+)(?:\[(.*)\])?$")
# neighbor offsets at same y: direction -> (dx, dz)
DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
PERPENDICULAR = [("north", "east"), ("east", "south"), ("south", "west"),
                 ("west", "north")]
CORNER_SHAPES = {"inner_left", "inner_right", "outer_left", "outer_right"}


def parse(spec):
    m = STATE_RE.match(spec)
    if not m:
        return spec, {}
    props = {}
    if m.group(2):
        for kv in m.group(2).split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                props[k.strip()] = v.strip()
    return m.group(1), props


def check(p):
    blocks = mirror_build.load_blocks(p["blocks"])
    stairs = {}
    for b in blocks:
        name, props = parse(b["block"])
        if "_stairs" in name:
            stairs[(b["x"], b["y"], b["z"])] = props
    issues = []
    for (x, y, z), props in stairs.items():
        present = {d for d, (dx, dz) in DIRS.items()
                   if (x + dx, y, z + dz) in stairs}
        # corner candidate = exactly 2 neighbor directions, perpendicular
        # (3+ directions = junction/middle of a 2-deep frame, not a corner)
        if len(present) != 2:
            continue
        # straight-run member exemption: a stair whose facing has a
        # same-facing neighbor along its own axis belongs to a straight run
        # that merely TOUCHES a perpendicular structure (roof row meeting a
        # ridge cap, solid stair masses) — MC auto-connect handles these.
        # The failure mode we catch is the butt-end of two runs meeting at
        # 90° with no run continuing through the corner.
        facing = props.get("facing", "")
        axis_dirs = (("north", "south") if facing in ("north", "south")
                     else ("east", "west"))
        if any(d in present and stairs[(x + DIRS[d][0], y, z + DIRS[d][1])].get("facing") == facing
               for d in axis_dirs):
            continue
        for d1, d2 in PERPENDICULAR:
            if d1 in present and d2 in present:
                # only an EXPLICIT straight at a corner is an error;
                # a missing shape property auto-derives in-game (vanilla
                # updateShape) and is fine — v1's real failure mode was
                # facing/half, never shape.
                if props.get("shape") == "straight":
                    issues.append({
                        "at": [x, y, z],
                        "facing": props.get("facing"),
                        "neighbors": sorted(present),
                        "reason": "corner_needs_shape",
                        "hint": "backs outward -> inner corner; backs inward -> outer corner",
                    })
                break
    return {"ok": not issues, "checked_stairs": len(stairs),
            "issue_count": len(issues), "issues": issues[:100]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    a = ap.parse_args()
    p = {"blocks": "blocks.json"}
    p.update(json.loads(a.params) if a.params.strip() else {})
    report = check(p)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
