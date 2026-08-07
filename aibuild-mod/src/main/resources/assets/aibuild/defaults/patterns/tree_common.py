#!/usr/bin/env python3
"""tree_common.py — 树类生成器共享 kernel (patterns/).

供 conifer_spire / palm_umbrella / weeping_tree 及后续树类生成器使用。
giant_tree.py v4 里有一份等价的内嵌拷贝(已验证冻结, 未回拆统一 —
新增树请一律用本模块, 别再复制)。

内容: 确定性 hash / rhu / vline 面连通体素线 / Voxel 容器(木 dict+叶 set,
截面圆台+半砖台阶, flood-fill 连通剪枝, emit persistent 叶) / _tuft 镂空叶簇 /
SPECIES 材质表(与 giant_tree 同步, 9 种)。
"""
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out  # noqa: F401  (re-export)

SPECIES = {"oak": ("minecraft:oak_log", "minecraft:oak_leaves", "minecraft:oak_fence",
                   "minecraft:oak_slab"),
           "dark_oak": ("minecraft:dark_oak_log", "minecraft:dark_oak_leaves",
                        "minecraft:dark_oak_fence", "minecraft:dark_oak_slab"),
           "birch": ("minecraft:birch_log", "minecraft:birch_leaves",
                     "minecraft:birch_fence", "minecraft:birch_slab"),
           "spruce": ("minecraft:spruce_log", "minecraft:spruce_leaves",
                      "minecraft:spruce_fence", "minecraft:spruce_slab"),
           "jungle": ("minecraft:jungle_log", "minecraft:jungle_leaves",
                      "minecraft:jungle_fence", "minecraft:jungle_slab"),
           "acacia": ("minecraft:acacia_log", "minecraft:acacia_leaves",
                      "minecraft:acacia_fence", "minecraft:acacia_slab"),
           "cherry": ("minecraft:cherry_log", "minecraft:cherry_leaves",
                      "minecraft:cherry_fence", "minecraft:cherry_slab"),
           "mangrove": ("minecraft:mangrove_log", "minecraft:mangrove_leaves",
                        "minecraft:mangrove_fence", "minecraft:mangrove_slab"),
           "pale_oak": ("minecraft:pale_oak_log", "minecraft:pale_oak_leaves",
                        "minecraft:pale_oak_fence", "minecraft:pale_oak_slab")}


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
            cells.append((cx, py, pz))
        if cz != pz and cy != py:
            cells.append((cx, py, cz))
        cells.append((cx, cy, cz))
        px, py, pz = cx, cy, cz
    return cells


class Voxel:
    """木 dict + 叶 set 容器: 截面/剪枝/emit 一套。"""

    def __init__(self, species, seed, origin):
        self.log, self.leaf, self.fence, self.slab = SPECIES[species]
        self.seed = int(seed)
        self.ox, self.oy, self.oz = (int(v) for v in origin)
        self.wood, self.leaves = {}, set()

    def put_wood(self, x, y, z, spec):
        self.wood[(x, y, z)] = spec

    def bole_section(self, cx, cz, y, size):
        half = (size - 1) / 2.0
        cells = set()
        for ix in range(size):
            for iz in range(size):
                x, z = rhu(cx - half) + ix, rhu(cz - half) + iz
                self.put_wood(x, y, z, "%s[axis=y]" % self.log)
                cells.add((x, z))
        return cells

    def tuft(self, cx, cy, cz, r, carve):
        """镂空小椭球叶簇(seeded hash, 与 giant_tree v4 同款)。"""
        ry = max(1, int(round(r * 0.8)))
        ri = max(1, int(round(r)))
        for dy in range(-ry, ry + 1):
            for dx in range(-ri, ri + 1):
                for dz in range(-ri, ri + 1):
                    v = (dx / r) ** 2 + (dy / max(0.6, r * 0.8)) ** 2 + (dz / r) ** 2
                    if v > 1.0:
                        continue
                    if v > 0.5 and h3(cx + dx, cy + dy, cz + dz, self.seed) < carve:
                        continue
                    cell = (cx + dx, cy + dy, cz + dz)
                    if cell not in self.wood:
                        self.leaves.add(cell)

    def prune(self, ground_width):
        """Flood fill from base (ground_width×ground_width at y=0); drop rest."""
        adj = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
        seen = set()
        stack = [(x, 0, z) for x in range(ground_width) for z in range(ground_width)]
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

    def emit(self):
        out = [{"x": self.ox + x, "y": self.oy + y, "z": self.oz + z, "block": b}
               for (x, y, z), b in sorted(self.wood.items())]
        out += [{"x": self.ox + x, "y": self.oy + y, "z": self.oz + z,
                 "block": self.leaf + "[persistent=true]"}
                for (x, y, z) in sorted(self.leaves) if (x, y, z) not in self.wood]
        return out
