#!/usr/bin/env python3
"""slab_check.py — deterministic slab-type validator (patterns/validators/).

Flags slab-type mistakes that produce visible seams/gaps (E7 lesson:
"roof slabs placed as top-half leave holes"):
1. TYPE SEAM: two vertically adjacent... no — two side-adjacent slabs at the
   same y sharing a face but having different `type` (top vs bottom). In a
   continuous surface they must share one type; a seam is almost always an
   error.
2. DOUBLE SLAB HOLE: a `type=top` slab with air directly below AND no slab
   in the cell below — the classic floating-hole look. (Overlaps
   support_check's floating rule, kept here because it is the #1 roof bug.)

Prints a JSON report. Exit 0 = clean, 1 = violations found.

Usage:
  python validators/slab_check.py --params '{"blocks":"blocks.json"}'
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import mirror_build  # patterns/ : for load_blocks

STATE_RE = re.compile(r"^([a-z0-9_:.]+)(?:\[(.*)\])?$")


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
    slabs = {}
    solid = set()
    for b in blocks:
        name, props = parse(b["block"])
        pos = (b["x"], b["y"], b["z"])
        solid.add(pos)
        if "_slab" in name:
            slabs[pos] = props.get("type", "bottom")
    issues = []
    for (x, y, z), t in slabs.items():
        for dx, dz, tag in ((1, 0, "east"), (0, 1, "south")):
            nb = (x + dx, y, z + dz)
            if nb in slabs and slabs[nb] != t and t != "double" and slabs[nb] != "double":
                issues.append({"at": [x, y, z], "neighbor": list(nb),
                               "types": [t, slabs[nb]], "reason": "type_seam"})
        if t == "top" and (x, y - 1, z) not in solid:
            issues.append({"at": [x, y, z], "reason": "double_slab_hole"})
    # de-dup seams (each pair reported once by construction)
    return {"ok": not issues, "checked_slabs": len(slabs),
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
