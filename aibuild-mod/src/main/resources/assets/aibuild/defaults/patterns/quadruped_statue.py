#!/usr/bin/env python3
"""quadruped_statue.py — parametric quadruped statue (四足雕像).

Born to fix the "abstract cow" failure: proportions are locked to readable
ratios — distinct legs, a torso box, a raised neck, a head with snout, ears
and a tail. Size scales from `length`; accent material marks hooves, snout,
ears and tail tip. Output: {"blocks":[...]}.

Usage:
  python quadruped_statue.py --params '{"origin":[100,64,100],"length":10,"facing":"x+"}' [--out s.json]
"""
import argparse, json, sys

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
    local = []  # (x,y,z,block) local coords: x = nose->tail axis, head at HIGH x

    def put(x, y, z, b):
        local.append((x, y, z, b))

    # legs: inset 1 from body corners; hooves in accent
    lx = [1, body_len - 2]
    lz = [0, body_w - 1]
    for x in lx:
        for z in lz:
            for y in range(leg_h):
                put(x, y, z, acc if y == 0 else mat)
    # torso box
    for x in range(body_len):
        for y in range(leg_h, leg_h + body_h):
            for z in range(body_w):
                put(x, y, z, mat)
    # neck: rising column at the front (high x)
    nx = body_len - 1
    nz0 = (body_w - head_s) // 2
    for y in range(leg_h + body_h, leg_h + body_h + neck_h):
        for z in range(nz0 + 1, nz0 + head_s - 1):
            put(nx, y, z, mat)
    # head: box on top of neck, sticking one block forward (snout direction +x)
    hy = leg_h + body_h + neck_h
    for x in range(nx, nx + head_s):
        for y in range(hy, hy + head_s):
            for z in range(nz0, nz0 + head_s):
                put(x, y, z, mat)
    # snout: one block forward, accent
    put(nx + head_s, hy, nz0 + head_s // 2, acc)
    # ears: two accent blocks on head top rear
    put(nx, hy + head_s, nz0, acc)
    put(nx, hy + head_s, nz0 + head_s - 1, acc)
    # tail: two blocks sloping down at the rear, accent tip
    put(-1, leg_h + body_h - 1, body_w // 2, mat)
    put(-2, leg_h + body_h - 2, body_w // 2, acc)

    # normalize to min corner (0,0,0)
    minx = min(b[0] for b in local)
    minz = min(b[2] for b in local)
    local = [(x - minx, y, z - minz, b) for x, y, z, b in local]
    W = max(b[0] for b in local) + 1
    D = max(b[2] for b in local) + 1

    ox, oy, oz = p["origin"]
    facing = p["facing"]
    blocks = []
    for x, y, z, b in local:
        if facing == "x-":
            x, z = W - 1 - x, D - 1 - z
        elif facing == "z+":
            x, z = z, x
        elif facing == "z-":
            x, z = D - 1 - z, W - 1 - x
        blocks.append({"x": ox + x, "y": oy + y, "z": oz + z, "block": b})
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
