#!/usr/bin/env python3
"""quadruped_statue.py — parametric quadruped statue (四足雕像).

Born to fix the "abstract cow" failure: proportions are locked to readable
ratios — distinct legs, a torso box, a raised neck, a head with snout, ears
and a tail. The body is axis-symmetric, so the script builds ONE side and
completes it through the same logic as mirror_build.py (imported).
Accent material marks hooves, snout, ears and tail tip.
Output: {"blocks":[...]}.

Usage:
  python quadruped_statue.py --params '{"origin":[100,64,100],"length":10,"facing":"x+"}' [--out s.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mirror_build  # same directory: shared mirror logic

DEFAULTS = {
    "origin": [0, 64, 0],   # [x,y,z] min corner of the statue bounding box at hoof-bottom level
    "length": 8,            # nose-to-tail torso length, 5-16
    "material": "minecraft:stone",
    "accent": "minecraft:andesite",
    "facing": "x+"          # head direction: x+ / x- / z+ / z-
}

def build(p):
    L = max(5, min(16, int(p["length"])))
    mat, acc = p["material"], p["accent"]
    leg_h = max(2, round(L * 0.35))
    body_h = max(2, round(L * 0.30))
    body_w = max(2, round(L * 0.30))
    body_len = L
    head_s = max(2, round(body_w * 0.9))
    neck_h = max(1, round(L * 0.15))
    # mirror plane across the body width (integer for odd widths, .5 for even)
    plane = (body_w - 1) / 2.0
    zc = int(plane)             # center row of the near half (axis row if odd)
    half = []                   # near half only: z <= plane

    def put(x, y, z, b):
        if z <= plane + 1e-9:
            half.append({"x": x, "y": y, "z": z, "block": b})

    # legs: near-side pair only; mirror creates the far pair
    for x in (1, body_len - 2):
        for y in range(leg_h):
            put(x, y, 0, acc if y == 0 else mat)
    # torso box (near half incl. center row)
    for x in range(body_len):
        for y in range(leg_h, leg_h + body_h):
            for z in range(0, zc + 1):
                put(x, y, z, mat)
    # neck: rising column at the front (high x), on the center row(s)
    nx = body_len - 1
    nz0 = (body_w - head_s) // 2
    for y in range(leg_h + body_h, leg_h + body_h + neck_h):
        put(nx, y, zc, mat)
    # head: box on top of neck, sticking one block forward (snout direction +x)
    hy = leg_h + body_h + neck_h
    for x in range(nx, nx + head_s):
        for y in range(hy, hy + head_s):
            for z in range(nz0, nz0 + head_s):
                put(x, y, z, mat)
    # snout: one block forward on the center row, accent
    put(nx + head_s, hy, zc, acc)
    # ear: one accent block on head top rear (near side); mirror makes the pair
    put(nx, hy + head_s, nz0, acc)
    # tail: two blocks sloping down at the rear on the center row, accent tip
    put(-1, leg_h + body_h - 1, zc, mat)
    put(-2, leg_h + body_h - 2, zc, acc)

    # complete the symmetric body through the shared mirror logic
    local = mirror_build.mirror_blocks(half, "z", plane)

    # normalize to min corner (0,0,0)
    minx = min(b["x"] for b in local)
    minz = min(b["z"] for b in local)
    local = [{"x": b["x"] - minx, "y": b["y"], "z": b["z"] - minz, "block": b["block"]} for b in local]
    W = max(b["x"] for b in local) + 1
    D = max(b["z"] for b in local) + 1

    ox, oy, oz = p["origin"]
    facing = p["facing"]
    blocks = []
    for b in local:
        x, y, z = b["x"], b["y"], b["z"]
        if facing == "x-":
            x, z = W - 1 - x, D - 1 - z
        elif facing == "z+":
            x, z = z, x
        elif facing == "z-":
            x, z = D - 1 - z, W - 1 - x
        blocks.append({"x": ox + x, "y": oy + y, "z": oz + z, "block": b["block"]})
    return blocks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    p = dict(DEFAULTS)
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
