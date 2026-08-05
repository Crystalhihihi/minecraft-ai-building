#!/usr/bin/env python3
"""timber_structure.py — exposed timber frame (木构梁架) generator, A3.

Five kinds (梁的句法):
- truss_simple:     tie beam (梁端收分: tapered stair ends) + rafter stairs
                    rising 45° to a ridge log; purlins run `spacing` blocks
                    toward the next truss (暴露屋架节奏, stats-calibrated).
- truss_kingpost:   truss_simple + vertical king post(s) under the ridge,
                    with bolster pads (梁柱交接垫块) flanking the post base.
- truss_hammerbeam: simplified hammer-beam — no full tie beam; short hammer
                    beams project from both wall heads, posts rise on them,
                    rafters spring from the post tops.
- corbel:           托臂 — stacked courses of upside-down stairs projecting
                    1..n from the wall face (each course one block deeper).
- brace:            45° knee brace (斜撑) — post stub, beam stub, and a
                    diagonal of stairs connecting them; both diagonal ends
                    land on orthogonal structure (see support_check's
                    diagonal-strut rule).

Calibration: purlin/truss spacing 2-5, default 4 (GrabCraft stats:
柱距 2格 35% / 3格 15% / 4格 35%, scratch/phase9/gc_probe/stats_details.md).

Conventions: origin = [x,y,z] of the truss's left wall-head (tie-beam west
end) at wall-TOP layer, or the corbel/brace attach column base. Canonical
frame: span along +x, run/outward along +z (south); rotated to `facing`.
ALL direction states (log axis / stair facing+half) are script-derived —
never hand-edit them in the output (禁止手改方向状态).

Usage:
  python timber_structure.py --params '{"origin":[100,80,100],"kind":"truss_kingpost","span":7}' [--out t.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import Builder, FACING_ROT, die, require_suffix, stair, write_out

KINDS = ("truss_simple", "truss_kingpost", "truss_hammerbeam", "corbel", "brace")

DEFAULTS = {
    "origin": [0, 64, 0],   # [x,y,z] truss: left wall-head at wall top; corbel/brace: attach column base
    "kind": "truss_simple",
    "facing": "south",      # truss: gable-end direction (span rotates with it); corbel/brace: outward from wall
    "span": 7,              # truss: tie-beam length 3-15; corbel/brace: projection/reach 2-4
    "spacing": 4,           # trusses only: purlin length toward the next truss, 2-5 (stats: 2/3/4 mainstream)
    "material": "minecraft:spruce_log"  # any *_log; stairs are derived (stripped_*_log -> *_stairs)
}


def stair_id(log_id):
    """minecraft:stripped_spruce_log -> minecraft:spruce_stairs."""
    base = log_id.replace("stripped_", "")
    return base[:-4] + "_stairs"  # require_suffix already guaranteed _log


def build(p):
    kind, s, sp, mat = p["kind"], int(p["span"]), int(p["spacing"]), p["material"]
    st = stair_id(mat)
    rot, fmap = FACING_ROT[p["facing"]]
    b = Builder(rot=rot, fmap=fmap)

    if kind in ("corbel", "brace"):
        n = s  # projection / reach
        if kind == "corbel":
            # course c at y=c projects 1..c+1; each new outer block leans on
            # the previous course / its own course neighbor (托臂逐层外挑)
            for c in range(n):
                for k in range(1, c + 2):
                    b.put(0, c, k, stair(st, "south", half="top"))
        else:  # brace: post stub + beam stub + 45° stair diagonal
            for y in range(n + 2):
                b.put(0, y, 0, mat + "[axis=y]")
            for k in range(n + 2):
                b.put(0, n + 2, k, mat + "[axis=z]")
            for k in range(1, n + 1):
                b.put(0, k, k, stair(st, "south"))
        return b.emit([int(v) for v in p["origin"]])

    # ---- trusses -----------------------------------------------------------
    rise = (s + 1) // 2
    rx = (s - 1) // 2            # ridge column (left cell of the top pair when even)
    ry = rise                    # ridge layer

    if kind == "truss_hammerbeam":
        b.put(0, 0, 0, stair(st, "west"))            # 梁端收分 tapered ends
        b.put(1, 0, 0, mat + "[axis=x]")
        b.put(s - 2, 0, 0, mat + "[axis=x]")
        b.put(s - 1, 0, 0, stair(st, "east"))
        b.put(1, 1, 0, mat + "[axis=y]")             # hammer posts
        b.put(s - 2, 1, 0, mat + "[axis=y]")
        for x in (1, s - 2):                         # 梁柱交接垫块 bolsters
            b.put(x, 1, -1, mat + "[axis=z]")
            b.put(x, 1, 1, mat + "[axis=z]")
        ry = rise - 1
        for j in range(1, rise):                     # rafters spring from post tops
            xl, xr, y = 1 + j, s - 2 - j, 1 + j
            if xl > xr:
                ry = y - 1
                break
            if xl == xr:
                b.put(xl, y, 0, mat + "[axis=z]")    # ridge log
                rx, ry = xl, y
            else:
                b.put(xl, y, 0, stair(st, "east"))
                b.put(xr, y, 0, stair(st, "west"))
        for z in range(1, sp + 1):                   # purlins (暴露节奏)
            for x, y in ((1, 0), (s - 2, 0), (rx, ry)):
                b.put(x, y, z, mat + "[axis=z]")
        return b.emit([int(v) for v in p["origin"]])

    # tie beam with tapered ends (梁端收分)
    for x in range(s):
        if x == 0:
            b.put(x, 0, 0, stair(st, "west"))
        elif x == s - 1:
            b.put(x, 0, 0, stair(st, "east"))
        else:
            b.put(x, 0, 0, mat + "[axis=x]")
    for i in range(rise):                            # rafters, 45° to the ridge
        xl, xr, y = i, s - 1 - i, 1 + i
        if xl == xr:
            b.put(xl, y, 0, mat + "[axis=z]")        # ridge log
        else:
            b.put(xl, y, 0, stair(st, "east"))       # facing = uphill, at the ridge
            b.put(xr, y, 0, stair(st, "west"))
    if kind == "truss_kingpost":
        xs = [rx] if s % 2 else [rx, rx + 1]
        for x in xs:                                 # king post(s) tie beam -> ridge
            for y in range(1, ry):
                b.put(x, y, 0, mat + "[axis=y]")
            b.put(x, 1, -1, mat + "[axis=z]")        # 梁柱交接垫块 bolsters
            b.put(x, 1, 1, mat + "[axis=z]")
    for z in range(1, sp + 1):                       # purlins (暴露节奏)
        for x, y in ((0, 0), (s - 1, 0), (rx, ry)):
            b.put(x, y, z, mat + "[axis=z]")
    return b.emit([int(v) for v in p["origin"]])


def validate(p):
    if p["kind"] not in KINDS:
        die("kind must be one of %s" % (KINDS,), {"kind": list(KINDS)})
    if p["facing"] not in FACING_ROT:
        die("facing must be one of north/south/east/west", {"facing": list(FACING_ROT)})
    try:
        s, sp = int(p["span"]), int(p["spacing"])
    except (TypeError, ValueError):
        die("span/spacing must be ints", {"span": "3-15 (truss) | 2-4 (corbel/brace)", "spacing": "2-5"})
    if p["kind"].startswith("truss"):
        if not 3 <= s <= 15:
            die("span out of range for trusses", {"span": "3-15"})
        if not 2 <= sp <= 5:
            die("spacing out of range (柱距统计: 2格35%/3格15%/4格35%)", {"spacing": "2-5"})
    elif not 2 <= s <= 4:
        die("span out of range for corbel/brace", {"span": "2-4"})
    require_suffix(p, "material", "_log",
                   ["minecraft:spruce_log", "minecraft:dark_oak_log", "minecraft:stripped_oak_log"])
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,80,100]"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}", help="JSON object of parameters")
    ap.add_argument("--out", default="", help="output file (default: stdout)")
    a = ap.parse_args()
    p = dict(DEFAULTS)
    try:
        p.update(json.loads(a.params) if a.params.strip() else {})
    except json.JSONDecodeError as e:
        die("--params is not valid JSON: %s" % e,
            {"example": '{"origin":[100,80,100],"kind":"truss_kingpost","span":7}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
