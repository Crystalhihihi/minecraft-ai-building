#!/usr/bin/env python3
"""giant_tree.py — space-colonization giant tree (巨树) generator. EXPERIMENTAL.

Algorithm (Runions et al. 2007, voxel adaptation): scatter N attraction
points inside an ellipsoid crown envelope (seeded RNG), then grow the
skeleton from the trunk base — each iteration, every node that is the
nearest neighbour of >=1 living points sprouts one child of length 1.0
toward their mean direction (plus an upward tropism below the crown);
points within kill distance are consumed. A leader hack keeps the bole
rising until the crown envelope is reached, so the trunk stays straight.
Branch calibre follows the pipe model via descendant-tip counts:
thick limb (2-wide log beam) -> log -> fence twig, and the lower bole is a
solid 2x2/3x3 trunk column up to the first fork. Tips (and unreached crown
points near the skeleton) grow carved ellipsoid leaf blobs; a full-tree
flood fill from the trunk base prunes anything not face-connected
(断枝/浮叶剪掉), so the output is always one rooted piece. Buttress roots
= 4-6 stepped fins around the base. Fully deterministic: same params +
same seed = same tree; origin only translates. Stdlib only.

Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python giant_tree.py --params '{"origin":[100,64,100],"height":22,"canopy_radius":8,"trunk":3,"seed":7}' [--out t.json]
"""
import argparse, json, math, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out

DEFAULTS = {
    "origin": [0, 64, 0],       # [x,y,z] trunk base min corner, y = ground layer
    "height": 18,               # 10-30, total tree height in blocks
    "canopy_radius": 6,         # 3-14, crown envelope horizontal radius
    "trunk": 2,                 # 2 = 2x2 bole | 3 = 3x3 bole
    "species": "oak",           # oak | dark_oak
    "seed": 0,                  # int; same seed = same tree
    "buttress": True,           # 板根: 4-6 stepped root fins around the base
    "leaf_density": 0.6,        # 0.1-1.0; scales tip blob size + carving
}
SPECIES = {"oak": ("minecraft:oak_log", "minecraft:oak_leaves", "minecraft:oak_fence"),
           "dark_oak": ("minecraft:dark_oak_log", "minecraft:dark_oak_leaves",
                        "minecraft:dark_oak_fence")}
DIRS8 = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
STEP, INFLUENCE, KILL = 1.0, 4.0, 1.6     # colonization radii (blocks)
THICK_TIPS, LOG_TIPS = 8, 3               # descendant-tip calibre thresholds
MAX_NODES, MAX_ITERS = 6000, 300


def h3(x, y, z, seed):
    """Deterministic per-cell hash -> [0,1), local coords + seed."""
    n = (x * 73428767) ^ (y * 91227153) ^ (z * 58362839) ^ \
        ((seed * 2654435761) & 0xFFFFFFFF) ^ 0x27d4eb2d
    n = (n ^ (n >> 15)) * 2246822519 & 0xFFFFFFFF
    return ((n ^ (n >> 13)) & 0xFFFF) / 65536.0


def rhu(v):
    """Round half up (banker's-rounding free, deterministic)."""
    return int(math.floor(v + 0.5))


def vline(a, b):
    """Face-connected voxel cells from int cell a to b (3D Bresenham +
    L-corner inserts, so consecutive cells never touch only by an edge)."""
    (ax, ay, az), (bx, by, bz) = a, b
    n = max(abs(bx - ax), abs(by - ay), abs(bz - az))
    cells, (px, py, pz) = [(ax, ay, az)], (ax, ay, az)
    for i in range(1, n + 1):
        t = i / n
        cx, cy, cz = rhu(ax + (bx - ax) * t), rhu(ay + (by - ay) * t), rhu(az + (bz - az) * t)
        if (cx, cy, cz) == (px, py, pz):
            continue
        if cx != px and (cy != py or cz != pz):
            cells.append((cx, py, pz))          # x-first corner
        if cz != pz and cy != py:
            cells.append((cx, py, cz))          # then z
        cells.append((cx, cy, cz))
        px, py, pz = cx, cy, cz
    return cells


class Tree:
    def __init__(self, p):
        self.p = p
        self.ox, self.oy, self.oz = (int(v) for v in p["origin"])
        self.ts = p["trunk"]
        self.c = (self.ts - 1) / 2.0                    # trunk centre (local)
        self.log, self.leaf, self.fence = SPECIES[p["species"]]
        self.rng = random.Random(p["seed"])
        self.seed = int(p["seed"])
        self.wood, self.leaves = {}, set()
        h, r = p["height"], p["canopy_radius"]
        self.ry = max(2, min(rhu(r * 0.6), (h - 3) // 2))
        self.yc = h - self.ry                           # crown centre y
        self.nodes = [(self.c, 0.0, self.c)]            # float skeleton
        self.parent = [-1]
        self.children = [[]]
        self.points, self.alive = self._scatter(h, r)

    # ------------------------------------------------------- colonization --
    def _scatter(self, h, r):
        """N attraction points, uniform inside the crown ellipsoid (seeded)."""
        vol = 4.0 / 3.0 * math.pi * r * r * self.ry
        n = max(60, min(900, int(vol / 7)))
        pts, alive = [], []
        while len(pts) < n:
            x = self.rng.uniform(-r, r)
            y = self.rng.uniform(-self.ry, self.ry)
            z = self.rng.uniform(-r, r)
            if (x / r) ** 2 + (y / self.ry) ** 2 + (z / r) ** 2 > 1.0:
                continue
            pts.append((self.c + x, self.yc + y, self.c + z))
            alive.append(True)
        return pts, alive

    def grow(self):
        di2, dk2 = INFLUENCE * INFLUENCE, KILL * KILL
        crown_bot, crown_top = self.yc - self.ry, self.yc + self.ry
        for _ in range(MAX_ITERS):
            if len(self.nodes) >= MAX_NODES:
                break
            buckets = {}
            for i, (x, y, z) in enumerate(self.nodes):
                key = (int(x // INFLUENCE), int(y // INFLUENCE), int(z // INFLUENCE))
                buckets.setdefault(key, []).append(i)
            influ, pending = {}, 0
            for pi, (x, y, z) in enumerate(self.points):
                if not self.alive[pi]:
                    continue
                best = None
                gx, gy, gz = int(x // INFLUENCE), int(y // INFLUENCE), int(z // INFLUENCE)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for dz in (-1, 0, 1):
                            for ni in buckets.get((gx + dx, gy + dy, gz + dz), ()):
                                nx, ny, nz = self.nodes[ni]
                                d2 = (nx - x) ** 2 + (ny - y) ** 2 + (nz - z) ** 2
                                if d2 <= di2 and (best is None or d2 < best[0]):
                                    best = (d2, ni)
                if best is None:
                    pending += 1                        # out of reach, for now
                elif best[0] <= dk2:
                    self.alive[pi] = False              # consumed
                else:
                    influ.setdefault(best[1], []).append(pi)
                    pending += 1
            for ni, pids in influ.items():
                x, y, z = self.nodes[ni]
                dx = dy = dz = 0.0
                for pi in pids:
                    vx, vy, vz = (self.points[pi][0] - x, self.points[pi][1] - y,
                                  self.points[pi][2] - z)
                    ln = math.sqrt(vx * vx + vy * vy + vz * vz) or 1.0
                    dx, dy, dz = dx + vx / ln, dy + vy / ln, dz + vz / ln
                if y < crown_bot:
                    dy += 0.15                          # upward tropism below crown
                ln = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
                self._add(ni, (x + dx / ln * STEP, y + dy / ln * STEP,
                               z + dz / ln * STEP))
            if influ:
                continue
            if pending == 0:
                break                                   # every point consumed
            lead = max(range(len(self.nodes)),          # leader hack: rise straight
                       key=lambda i: (self.nodes[i][1], -i))
            if self.nodes[lead][1] >= crown_top:
                break                                   # crown top reached, give up
            lx, ly, lz = self.nodes[lead]
            jx, jz = self.rng.uniform(-0.12, 0.12), self.rng.uniform(-0.12, 0.12)
            ln = math.sqrt(jx * jx + 1.0 + jz * jz)
            self._add(lead, (lx + jx / ln * STEP, ly + STEP / ln, lz + jz / ln * STEP))

    def _add(self, parent, pos):
        self.nodes.append(pos)
        self.parent.append(parent)
        self.children.append([])
        self.children[parent].append(len(self.nodes) - 1)

    # --------------------------------------------------------- rasterize --
    def calibre(self):
        """descendant-tip counts -> per-segment width class; first fork y."""
        desc = [0] * len(self.nodes)
        for i in reversed(range(len(self.nodes))):
            desc[i] = sum(desc[c] for c in self.children[i]) or 1
        forks = [i for i, c in enumerate(self.children) if len(c) >= 2]
        clear_h = min((rhu(self.nodes[i][1]) for i in forks), default=self.p["height"] - 2)
        clear_h = max(3, min(self.p["height"] - 2, clear_h))
        return desc, clear_h

    def put_wood(self, x, y, z, spec):
        self.wood[(x, y, z)] = spec

    def rasterize(self):
        desc, clear_h = self.desc, self.clear_h
        for y in range(clear_h + 1):                    # solid bole
            for x in range(self.ts):
                for z in range(self.ts):
                    self.put_wood(x, y, z, "%s[axis=y]" % self.log)
        for i in range(1, len(self.nodes)):
            pa = self.parent[i]
            a = tuple(rhu(v) for v in self.nodes[pa])
            b = tuple(rhu(v) for v in self.nodes[i])
            dx, dy, dz = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            axis = "x" if abs(dx) >= abs(dy) and abs(dx) >= abs(dz) else \
                   ("y" if abs(dy) >= abs(dz) else "z")
            below = rhu(self.nodes[i][1]) <= clear_h and rhu(self.nodes[pa][1]) <= clear_h
            thick = not below and desc[i] >= THICK_TIPS
            spec = self.fence if (not below and desc[i] < LOG_TIPS) else \
                "%s[axis=%s]" % (self.log, axis)
            for cell in vline(a, b):
                self.put_wood(*cell, spec)
                if thick:                               # 2-wide beam, widen sideways
                    bud = (cell[0], cell[1], cell[2] + 1) if axis == "x" else \
                          (cell[0] + 1, cell[1], cell[2])
                    self.put_wood(*bud, "%s[axis=%s]" % (self.log, axis))

    def buttress(self):
        """板根: 4-6 stepped fins; column heights fall off outward."""
        n = 4 + self.rng.randrange(3)
        start = self.rng.randrange(8)
        dirs, seen = [], set()
        for k in range(n):
            d = DIRS8[(start + rhu(k * 8.0 / n)) % 8]
            if d not in seen:
                seen.add(d)
                dirs.append(d)
        length, c = self.ts + 1, self.c
        for ddx, ddz in dirs:
            px = max(0, min(self.ts - 1, rhu(c + ddx * c)))
            pz = max(0, min(self.ts - 1, rhu(c + ddz * c)))
            axis = "x" if abs(ddx) >= abs(ddz) else "z"
            for k in range(1, length + 1):
                hgt = max(1, length - k + 1)            # 3,2,1 (ts=2) / 4,3,2,1 (ts=3)
                cols = [(px + k * ddx, pz + k * ddz)]
                if ddx and ddz:                         # diagonal fin: L-corner column
                    cols.append((px + k * ddx, pz + (k - 1) * ddz))
                for cx, cz in cols:
                    for y in range(hgt):
                        self.put_wood(cx, y, cz, "%s[axis=%s]" % (
                            self.log, axis if y == hgt - 1 else "y"))

    def blob(self, cx, cy, cz, r, carve):
        """Carved ellipsoid leaf blob (garden_tree recipe, seeded hash)."""
        ry = max(1, r - 1)
        for dy in range(-ry, ry + 1):
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    v = (dx / r) ** 2 + (dy / ry) ** 2 + (dz / r) ** 2
                    if v > 1.0:
                        continue
                    if v > 0.55 and h3(cx + dx, cy + dy, cz + dz, self.seed) < carve:
                        continue                        # 镂空 breathing pocket
                    if (cx + dx, cy + dy, cz + dz) not in self.wood:
                        self.leaves.add((cx + dx, cy + dy, cz + dz))

    def foliage(self):
        ld = self.p["leaf_density"]
        r = 2 if ld < 0.35 else (3 if ld < 0.75 else 4)
        if r > 2 and self.p["canopy_radius"] * self.ry >= 70:
            r -= 1              # huge crown: slim blobs to stay within block budget
        carve = 0.30 - 0.18 * ld
        for i, ch in enumerate(self.children):
            if not ch:                                  # terminal twig tip
                self.blob(*[rhu(v) for v in self.nodes[i]], r, carve)
        reach2 = (INFLUENCE + 1.5) ** 2                 # unreached points near wood
        for pi, pt in enumerate(self.points):
            if not self.alive[pi]:
                continue
            near = min(((n[0] - pt[0]) ** 2 + (n[1] - pt[1]) ** 2 +
                        (n[2] - pt[2]) ** 2 for n in self.nodes), default=1e9)
            if near <= reach2:
                self.blob(rhu(pt[0]), rhu(pt[1]), rhu(pt[2]), max(1, r - 1), carve)

    def prune(self):
        """Flood fill from the bole base over wood+leaves; drop the rest."""
        adj = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
        seen = set()
        stack = [(x, 0, z) for x in range(self.ts) for z in range(self.ts)]
        allc = set(self.wood) | self.leaves
        while stack:
            cell = stack.pop()
            if cell in seen or cell not in allc:
                continue
            seen.add(cell)
            x, y, z = cell
            stack.extend((x + dx, y + dy, z + dz) for dx, dy, dz in adj)
        self.wood = {k: v for k, v in self.wood.items() if k in seen}
        self.leaves &= seen
        self.dropped = len(allc) - len(seen)

    def emit(self):
        out = [{"x": self.ox + x, "y": self.oy + y, "z": self.oz + z, "block": b}
               for (x, y, z), b in sorted(self.wood.items())]
        # persistent=true: bare leaves decay away from logs (实机实测) — always pin.
        out += [{"x": self.ox + x, "y": self.oy + y, "z": self.oz + z,
                 "block": self.leaf + "[persistent=true]"}
                for (x, y, z) in sorted(self.leaves) if (x, y, z) not in self.wood]
        return out


def build(p):
    t = Tree(p)
    t.grow()
    t.desc, t.clear_h = t.calibre()
    t.rasterize()
    if p["buttress"]:
        t.buttress()
    t.foliage()
    t.prune()
    return t.emit()


def validate(p):
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,64,100]"})
    try:
        p["origin"] = [int(v) for v in p["origin"]]
    except (TypeError, ValueError):
        die("origin must be [x,y,z] ints", {"origin": "[100,64,100]"})
    for key, lo, hi in (("height", 10, 30), ("canopy_radius", 3, 14)):
        try:
            p[key] = int(p[key])
        except (TypeError, ValueError):
            die("%s must be an int %d-%d" % (key, lo, hi), {key: [lo, hi]})
        if not lo <= p[key] <= hi:
            die("%s must be %d-%d" % (key, lo, hi), {key: [lo, hi]})
    try:
        p["trunk"] = int(p["trunk"])
    except (TypeError, ValueError):
        die("trunk must be 2|3", {"trunk": [2, 3]})
    if p["trunk"] not in (2, 3):
        die("trunk must be 2|3 (2x2|3x3)", {"trunk": [2, 3]})
    if p["species"] not in SPECIES:
        die("species must be one of %s" % (tuple(SPECIES),), {"species": list(SPECIES)})
    try:
        p["seed"] = int(p["seed"])
    except (TypeError, ValueError):
        die("seed must be an int", {"seed": 0})
    if not isinstance(p["buttress"], bool):
        die("buttress must be true|false", {"buttress": [True, False]})
    try:
        p["leaf_density"] = float(p["leaf_density"])
    except (TypeError, ValueError):
        die("leaf_density must be 0.1-1.0", {"leaf_density": 0.6})
    if not 0.1 <= p["leaf_density"] <= 1.0:
        die("leaf_density must be 0.1-1.0", {"leaf_density": 0.6})


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
            {"example": '{"origin":[100,64,100],"height":22,"canopy_radius":8,"seed":7}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
