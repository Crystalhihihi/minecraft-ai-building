#!/usr/bin/env python3
"""garden_tree.py — handcrafted landscape tree (景观树) generator.

Born to replace the "vanilla sapling look": every species follows the
hand-building recipes from custom-tree tutorials, fully deterministic
(no worldgen randomness — same params, same tree):
- visible branch structure: branches climb OUTWARD as face-connected
  staircases (never diagonal floaters), each tipped with a leaf blob;
- canopies are ellipsoid blobs with hashed surface carving (airy edges,
  not solid balls) — sized per species and per `size` (3 体量);
- species silhouettes: oak = branched round crown (large gets a 2x2 trunk
  + buttress roots); birch = tall slim trunk + elongated canopy; cherry =
  low fork, two slanted stems + wide flat pink canopy; spruce = conical
  tapering tiers with cut corners.

Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python garden_tree.py --params '{"origin":[100,64,100],"species":"cherry","size":"large"}' [--out t.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] trunk base cell (min corner of the trunk) at ground y
    "species": "oak",              # oak | birch | cherry | spruce
    "size": "medium"               # small | medium | large
}

SPECIES = ("oak", "birch", "cherry", "spruce")
SIZES = ("small", "medium", "large")
LOG = {"oak": "minecraft:oak_log", "birch": "minecraft:birch_log",
       "cherry": "minecraft:cherry_log", "spruce": "minecraft:spruce_log"}
LEAVES = {"oak": "minecraft:oak_leaves", "birch": "minecraft:birch_leaves",
          "cherry": "minecraft:cherry_leaves", "spruce": "minecraft:spruce_leaves"}
# trunk height per species/size
HEIGHT = {"oak": (4, 6, 8), "birch": (5, 7, 9), "cherry": (4, 5, 7), "spruce": (6, 8, 11)}
CROWN_R = {"oak": (2, 3, 4), "birch": (2, 2, 3), "cherry": (3, 3, 4), "spruce": (2, 3, 4)}
BRANCHES = {"oak": (3, 4, 5), "birch": (0, 0, 0), "cherry": (0, 0, 0), "spruce": (0, 0, 0)}
DIRS8 = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def h3(x, y, z):
    """Deterministic per-cell hash -> [0,1)."""
    n = (x * 73428767) ^ (y * 91227153) ^ (z * 58362839) ^ 0x27d4eb2d
    n = (n ^ (n >> 15)) * 2246822519 & 0xFFFFFFFF
    return ((n ^ (n >> 13)) & 0xFFFF) / 65536.0


class Tree:
    def __init__(self, p):
        self.p = p
        self.ox, self.oy, self.oz = p["origin"]
        self.sp, self.sz = p["species"], SIZES.index(p["size"])
        self.log, self.leaf = LOG[p["species"]], LEAVES[p["species"]]
        self.logs, self.leaves = {}, set()

    def put_log(self, x, y, z, axis="y"):
        self.logs[(x, y, z)] = "%s[axis=%s]" % (self.log, axis)

    def blob(self, cx, cy, cz, rx, ry, carve=0.12):
        """Ellipsoid leaf blob with hashed surface carving."""
        for dy in range(-ry, ry + 1):
            for dx in range(-rx, rx + 1):
                for dz in range(-rx, rx + 1):
                    v = (dx / (rx + 0.0)) ** 2 + (dy / (ry + 0.0)) ** 2 + (dz / (rx + 0.0)) ** 2
                    if v > 1.0:
                        continue
                    wx, wy, wz = self.ox + cx + dx, self.oy + cy + dy, self.oz + cz + dz
                    if v > 0.5 and h3(wx, wy, wz) < carve:
                        continue          # air pocket on the surface
                    if (cx + dx, cy + dy, cz + dz) not in self.logs:
                        self.leaves.add((cx + dx, cy + dy, cz + dz))

    def branch(self, bx, by, bz, d, reach, tip_r):
        """Face-connected ascending staircase outward; blob at the tip.
        Diagonal steps get an L-corner connector so no log ever floats."""
        ddx, ddz = d
        axis = "x" if abs(ddx) >= abs(ddz) else "z"
        tx = ty = tz = None
        for s in range(1, reach + 1):
            cx, cz = bx + s * ddx, bz + s * ddz
            yb = by + s - 1
            if ddx != 0 and ddz != 0:
                self.put_log(cx, yb, bz + (s - 1) * ddz, "x")   # L-corner
            self.put_log(cx, yb, cz, axis)
            self.put_log(cx, yb + 1, cz, axis)
            tx, ty, tz = cx, yb + 1, cz
        self.blob(tx, ty + 1, tz, tip_r, max(1, tip_r - 1))

    def trunk(self, h, thick=False):
        rng = ((0, 0), (1, 0), (0, 1), (1, 1)) if thick else ((0, 0),)
        for y in range(h):
            for tx, tz in rng:
                self.put_log(tx, y, tz)
        return rng

    def emit(self):
        out = [{"x": self.ox + x, "y": self.oy + y, "z": self.oz + z, "block": b}
               for (x, y, z), b in sorted(self.logs.items())]
        out += [{"x": self.ox + x, "y": self.oy + y, "z": self.oz + z, "block": self.leaf}
                for (x, y, z) in sorted(self.leaves) if (x, y, z) not in self.logs]
        return out


def build(p):
    t = Tree(p)
    h = HEIGHT[t.sp][t.sz]
    cr = CROWN_R[t.sp][t.sz]
    seed = int(h3(t.ox, t.oy, t.oz) * 8)

    if t.sp == "oak":
        thick = p["size"] == "large"
        t.trunk(h, thick)
        if thick:                                     # buttress roots
            for dx, dz, ax in ((1, 0, "x"), (-1, 0, "x"), (0, 1, "z"), (0, -1, "z")):
                t.put_log(dx, 0, dz, ax)
        n = BRANCHES["oak"][t.sz]
        for i in range(n):
            d = DIRS8[(seed + i * 3) % 8]
            hb = h - 2 + (i % 2)
            reach = 1 + (i % 2)
            t.branch(0, hb, 0, d, reach, max(2, cr - 1))
        t.blob(0, h + 1, 0, cr, max(2, cr - 1))       # main crown
    elif t.sp == "birch":
        t.trunk(h)
        t.blob(0, h, 0, cr, cr)                       # elongated canopy
        if t.sz >= 1:
            for i in range(2):                        # small side tufts
                d = DIRS8[(seed + i * 4) % 8]
                t.blob(d[0] * (cr - 1), h - 2 - i, d[1] * (cr - 1), 1, 1)
        t.blob(0, h + cr, 0, 1, 1)                    # tip tuft
    elif t.sp == "cherry":
        t.trunk(h - 1)                            # trunk top = fork level h-2
        d = DIRS8[seed % 8]                           # fork: two opposite slanted stems
        t.branch(0, h - 2, 0, d, 2, 2)
        t.branch(0, h - 2, 0, (-d[0], -d[1]), 2, 2)
        t.blob(0, h + 1, 0, cr, 2, carve=0.15)        # wide flat airy canopy
    else:  # spruce
        t.trunk(h)
        for y in range(2, h + 1):
            r = max(0, round(cr * (h - y) / max(1, h - 2)))
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if (dx, dz) == (0, 0):
                        continue
                    if abs(dx) == r and abs(dz) == r and r > 1:
                        continue                      # cut corners
                    if h3(t.ox + dx, t.oy + y, t.oz + dz) < 0.10:
                        continue
                    t.leaves.add((dx, y, dz))
        t.leaves.add((0, h, 0))                       # tip
        t.leaves.add((0, h + 1, 0))
    return t.emit()


def validate(p):
    if p["species"] not in SPECIES:
        die("species must be one of %s" % (SPECIES,), {"species": list(SPECIES)})
    if p["size"] not in SIZES:
        die("size must be one of %s" % (SIZES,), {"size": list(SIZES)})
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,64,100]"})


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
            {"example": '{"origin":[100,64,100],"species":"cherry","size":"large"}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
