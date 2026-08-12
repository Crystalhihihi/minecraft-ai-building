#!/usr/bin/env python3
"""tree_common.py — 树类生成器共享 kernel (patterns/).

供 conifer_spire / palm_umbrella / weeping_tree 及后续树类生成器使用。
giant_tree.py v4 里有一份等价的内嵌拷贝(已验证冻结, 未回拆统一 —
新增树请一律用本模块, 别再复制)。

内容: 确定性 hash / rhu / vline 面连通体素线 / vnoise3 seeded value noise /
Field metaball 密度场等值面 kernel(簇心场源+噪声阈值+剥壳, 阶段1起叶图元
正主) / Voxel 容器(木 dict+叶 set, 截面圆台+半砖台阶, flood-fill 连通剪枝,
emit persistent 叶) / SPECIES 材质表(与 giant_tree 同步, 9 种)。
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


def vnoise3(x, y, z, L, seed):
    """Seeded value noise: h3 格点哈希 + 三线性(smoothstep 权)插值 ->
    [0,1), 低频连续(波长=L 格), 供密度场阈值扰动; 全确定性。"""
    fx, fy, fz = x / L, y / L, z / L
    ix, iy, iz = math.floor(fx), math.floor(fy), math.floor(fz)
    tx, ty, tz = fx - ix, fy - iy, fz - iz
    tx, ty, tz = (t * t * (3.0 - 2.0 * t) for t in (tx, ty, tz))

    def c(dx, dy, dz):
        return h3(ix + dx, iy + dy, iz + dz, seed)

    c00 = c(0, 0, 0) + (c(1, 0, 0) - c(0, 0, 0)) * tx
    c10 = c(0, 1, 0) + (c(1, 1, 0) - c(0, 1, 0)) * tx
    c01 = c(0, 0, 1) + (c(1, 0, 1) - c(0, 0, 1)) * tx
    c11 = c(0, 1, 1) + (c(1, 1, 1) - c(0, 1, 1)) * tx
    return (c00 + (c10 - c00) * ty) + ((c01 + (c11 - c01) * ty) -
                                       (c00 + (c10 - c00) * ty)) * tz


class Field:
    """metaball 密度场等值面成面 kernel(治"树叶全是一个个球",
    阶段1 giant_tree 验证后下沉共享): 簇心场源(各向异性 flat=y 向压扁)
    叠加 F(p)=Σ max(0,1-d²)² — K 倍半径截断, 逐源 splat; 低频 seeded
    value noise 扰动阈值 T 取实心, 再从外表面逐层向内剥 shell 层体素作叶
    (壳厚均匀不受场梯度影响 → 不穿孔; 冠内留空可藏灯)。
    全确定性: 噪声 seeded(salt 按调用方区分), F 求和顺序=add 顺序(固定)。
    用法: f = Field(seed); f.add(cx, cy, cz, r, flat) ...;
          leaves = f.rasterize(wood, T=..., amp=..., noise_L=..., shell=...)
    参数默认 = giant_tree 阶段1 调参; 各树型按冠厚/尺度覆盖。"""

    def __init__(self, seed, K=2.2):
        self.seed = int(seed)
        self.K = float(K)                       # 场源影响半径倍率(截断)
        self.sources = []                       # (cx, cy, cz, r, flat) 收集序

    def add(self, cx, cy, cz, r, flat=0.8):
        """收一个场源(簇心+半径+各向异性); 成面在 rasterize 统一做。"""
        self.sources.append((int(cx), int(cy), int(cz),
                             float(r), float(flat)))

    def rasterize(self, wood, T=0.5, amp=0.4, noise_L=6, salt=424242, shell=2):
        """成面 → 叶格集(不含 wood):
        实心 = {F >= T_eff}, T_eff = T*(1+amp*(2*noise-1)); 带外快通道
        (f>=t_hi 必实 / f<t_lo 必空, 省噪声求值); 再剥壳 shell 层。"""
        F = {}
        fget = F.get
        for (cx, cy, cz, tr, flat) in self.sources:
            R = tr * self.K
            Ry = max(1.0, R * flat)
            Rx = int(math.ceil(R))
            inv = 1.0 / (R * R)
            for dx in range(-Rx, Rx + 1):
                x = cx + dx
                q0 = dx * dx * inv
                for dz in range(-Rx, Rx + 1):
                    q = q0 + dz * dz * inv
                    if q >= 1.0:
                        continue
                    z = cz + dz
                    wq = 1.0 - q
                    dym = int(Ry * math.sqrt(wq))   # 椭球列(免角部浪费)
                    for dy in range(-dym, dym + 1):
                        t = dy / Ry
                        w = wq - t * t
                        cell = (x, cy + dy, z)
                        F[cell] = fget(cell, 0.0) + w * w
        if not F:
            return set()
        t_lo, t_hi = T * (1.0 - amp), T * (1.0 + amp)
        nseed = self.seed ^ salt
        solid = set()
        for (x, y, z), f in F.items():
            if f < t_lo or (x, y, z) in wood:
                continue
            if f >= t_hi or f >= T * (1.0 + amp * (
                    2.0 * vnoise3(x, y, z, noise_L, nseed) - 1.0)):
                solid.add((x, y, z))
        leaves = set()
        adj = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
        for _ in range(max(1, int(shell))):
            boundary = set()
            for c in solid:
                x, y, z = c
                for dx, dy, dz in adj:
                    if (x + dx, y + dy, z + dz) not in solid:
                        boundary.add(c)
                        break
            if not boundary:
                break
            leaves |= boundary
            solid -= boundary
        return leaves


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
