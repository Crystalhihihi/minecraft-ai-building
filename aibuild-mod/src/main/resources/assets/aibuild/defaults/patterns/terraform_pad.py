#!/usr/bin/env python3
"""terraform_pad.py — building pad (建筑台地) with smoothstep transition band.

Raises (or lowers) a flat pad at target height and blends it into the
surrounding ground over a transition band (<= 16 blocks) using a smoothstep
falloff, plus +-1 block deterministic noise inside the band so the slope
never looks ruler-straight. Every surface column gets 3 blocks of fill below.
Output: {"blocks":[...]}.

NOTE: the script cannot read the world. Pass `ground` = the typical surface
height around the pad, read from terrain.json / get_terrain_summary.

Usage:
  python terraform_pad.py --params '{"origin":[96,70,96],"width":12,"depth":10,"ground":64}' [--out pad.json]
"""
import argparse, json, sys

DEFAULTS = {
    "origin": [0, 68, 0],          # [x,y,z] min corner of the FLAT pad; y = pad surface height
    "width": 10,
    "depth": 10,
    "ground": 64,                  # typical surrounding surface height (from terrain.json!)
    "transition": 8,               # blend band width in blocks, clamped to 1-16
    "top_material": "minecraft:grass_block",
    "slope_material": "minecraft:dirt",   # surface of the transition band
    "fill_material": "minecraft:dirt",
    "stone_material": "minecraft:stone"   # shows through on steeper noise dips
}

def h2(x, z):
    n = (x * 73428767) ^ (z * 91227153) ^ 0x27d4eb2d
    n = (n ^ (n >> 15)) * 2246822519 & 0xFFFFFFFF
    return ((n ^ (n >> 13)) & 0xFFFF) / 65536.0

def smoothstep(s):
    s = max(0.0, min(1.0, s))
    return s * s * (3.0 - 2.0 * s)

def build(p):
    ox, oy, oz = p["origin"]
    w, d = int(p["width"]), int(p["depth"])
    ground = int(p["ground"])
    trans = max(1, min(16, int(p["transition"])))
    blocks = []
    for x in range(-trans, w + trans):
        for z in range(-trans, d + trans):
            # distance from the pad rectangle (0 = inside)
            dx = max(0, -x, x - (w - 1))
            dz = max(0, -z, z - (d - 1))
            dist = max(dx, dz)
            if dist == 0:
                h = oy
                surf = p["top_material"]
            else:
                t = dist / trans                      # 0 at pad edge -> 1 at band edge
                h = round(ground + (oy - ground) * smoothstep(1.0 - t))
                if 0 < t < 1:                         # noise only inside the band
                    h += int(h2(ox + x, oz + z) * 3) - 1
                if h < ground - 2:
                    continue                          # far below grade: leave terrain alone
                if h >= oy - 1:
                    surf = p["top_material"]
                elif h2(ox + x + 31, oz + z - 17) < 0.25:
                    surf = p["stone_material"]
                else:
                    surf = p["slope_material"]
            wx, wz = ox + x, oz + z
            blocks.append({"x": wx, "y": h, "z": wz, "block": surf})
            for k in range(1, 4):
                blocks.append({"x": wx, "y": h - k, "z": wz, "block": p["fill_material"]})
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
