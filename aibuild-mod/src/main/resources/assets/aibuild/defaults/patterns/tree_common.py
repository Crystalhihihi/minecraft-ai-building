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
                        "minecraft:pale_oak_fence", "minecraft:pale_oak_slab"),
           "frost": ("minecraft:birch_log", "minecraft:ice",
                     "minecraft:birch_fence", "minecraft:birch_slab")}


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
    叠加 F(p)=Σ max(0,1-d²)² — K 倍半径截断, 逐源 splat; 再从外表面逐层
    向内剥 shell 层体素作叶(壳厚均匀不受场梯度影响 → 不穿孔; 冠内留空)。

    阶段6 叶层质感(docs/research/2026-08-13-foliage-texture.md §3):
    - gid 枝级分场(R1): 组内 sum、组间各自取等值面后并集(组间鞍部永不被
      填 → 枝间沟壑保得住), 统一剥壳一次(内腔特性不变); 默认 gid=0 全树
      一组(旧行为)。调用约定: 每 gid ≥2 源或源 r≥1.6(单源小团自成球)。
    - 三octave 噪声阈值(R2): n=0.55·vnoise3(λ=noise_L 剪影) + 0.30·
      vnoise3(λ=4.0 簇级) + 0.15·vnoise3(λ=1.7 叶碎), T_eff=T(1±amp·(2n-1));
      快通道保留(只边界带求 3 次噪声)。
    - R3 壳面咬缺(bite>0): 剥壳后 26 邻表决 — 外向空气面>0 且 26 邻叶
      ≤10 的壳格按 h3 门控删除(光斑/碎轮廓; 与外向飞叶=双向毛边)。
    - R4 垂叶绦(drape>0): 逐列最低叶按概率向下垂 1-3 格叶柱(遇块即止)。
    全确定性: 噪声/门控全部 seeded(salt 派生三料), 求和顺序=add 顺序。
    用法: f = Field(seed); f.add(cx, cy, cz, r, flat, gid) ...;
          leaves = f.rasterize(wood, T=..., amp=..., noise_L=..., shell=...)
    参数默认 = giant_tree 阶段1 调参; 各树型按冠厚/尺度覆盖。"""

    def __init__(self, seed, K=2.2):
        self.seed = int(seed)
        self.K = float(K)                       # 场源影响半径倍率(截断)
        self.sources = []                       # (cx, cy, cz, r, flat, gid) 收集序

    def add(self, cx, cy, cz, r, flat=0.8, gid=0):
        """收一个场源(簇心+半径+各向异性+枝级分组); 成面在 rasterize 统一做。"""
        self.sources.append((int(cx), int(cy), int(cz),
                             float(r), float(flat), int(gid)))

    def rasterize(self, wood, T=0.5, amp=0.4, noise_L=6, salt=424242, shell=2,
                  bite=0.0, drape=0.0):
        """成面 → 叶格集(不含 wood)。分组 splat→逐组阈值取实心→并集→
        统一剥壳 shell 层→咬缺→垂叶绦。"""
        groups = {}
        for s in self.sources:
            groups.setdefault(s[5], []).append(s)   # dict 保首见序(确定性)
        # 三八度噪声盐(同 salt 派生, 互不相关)
        s1 = self.seed ^ salt
        s2 = self.seed ^ (salt ^ 0x51E15E)
        s3 = self.seed ^ (salt ^ 0xB17E)
        L1 = max(1.5, float(noise_L))
        t_lo, t_hi = T * (1.0 - amp), T * (1.0 + amp)
        solid = set()
        for gid in groups:
            F = {}
            fget = F.get
            for (cx, cy, cz, tr, flat, _g) in groups[gid]:
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
            for (x, y, z), f in F.items():
                if f < t_lo or (x, y, z) in wood:
                    continue
                if f >= t_hi:
                    solid.add((x, y, z))
                    continue
                n = 0.55 * vnoise3(x, y, z, L1, s1) + \
                    0.30 * vnoise3(x, y, z, 4.0, s2) + \
                    0.15 * vnoise3(x, y, z, 1.7, s3)
                if f >= T * (1.0 + amp * (2.0 * n - 1.0)):
                    solid.add((x, y, z))
        # 统一剥壳(并集后剥, 内腔保留)
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
        # R3 壳面咬缺: 外向空气面>0 且 26 邻叶≤10 的壳格按概率删除
        if bite > 0.0 and leaves:
            bseed = self.seed ^ (salt ^ 0xB17E5)
            for c in list(leaves):
                x, y, z = c
                if all((x + dx, y + dy, z + dz) in leaves or
                       (x + dx, y + dy, z + dz) in wood for dx, dy, dz in adj):
                    continue                            # 不碰内侧面
                n26 = 0
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for dz in (-1, 0, 1):
                            if (dx or dy or dz) and \
                                    (x + dx, y + dy, z + dz) in leaves:
                                n26 += 1
                if n26 > 10:
                    continue                            # 保厚区(防断连/穿孔)
                if h3(x, y, z, bseed) < bite:
                    leaves.discard(c)
        # R4 垂叶绦: 逐列最低叶按概率向下垂 1-3 格叶柱(遇块即止, 材质=叶)
        if drape > 0.0 and leaves:
            colb = {}
            for c in leaves:
                k = (c[0], c[2])
                if k not in colb or c[1] < colb[k][1]:
                    colb[k] = c
            dseed = self.seed ^ (salt ^ 0xD9A9E)
            for (x, y, z) in sorted(colb.values()):
                if h3(x, y, z, dseed) >= drape:
                    continue
                L = 1 + int(h3(x, y, z, dseed ^ 7) * 3)
                for i in range(1, L + 1):
                    c2 = (x, y - i, z)
                    if c2 in leaves or c2 in wood:
                        break
                    leaves.add(c2)
        return leaves


# 双色混叶(R4): 主叶近色配对, h3 门控 0.2 换次叶(persistent 照设;
# azalea/flowering_azalea_leaves 带 persistent 属性, 已核)
LEAF_ALT = {"minecraft:oak_leaves": "minecraft:birch_leaves",
            "minecraft:birch_leaves": "minecraft:oak_leaves",
            "minecraft:dark_oak_leaves": "minecraft:spruce_leaves",
            "minecraft:spruce_leaves": "minecraft:dark_oak_leaves",
            "minecraft:jungle_leaves": "minecraft:oak_leaves",
            "minecraft:acacia_leaves": "minecraft:oak_leaves",
            "minecraft:cherry_leaves": "minecraft:flowering_azalea_leaves",
            "minecraft:mangrove_leaves": "minecraft:jungle_leaves",
            "minecraft:pale_oak_leaves": "minecraft:birch_leaves",
            # 冰叶混比(幻想 frost 试点): 主 ice 70%, 次 packed_ice 20%, blue_ice 10%
            "minecraft:ice": "minecraft:packed_ice"}


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
        self.decor = {}                             # 装饰块(灯/浆果等, 可选)

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
        alt = LEAF_ALT.get(self.leaf)               # 双色混叶(R4, 0.2 换次叶)
        for (x, y, z) in sorted(self.leaves):
            if (x, y, z) in self.wood:
                continue
            b = self.leaf
            if alt and h3(x, y, z, self.seed ^ 0x2C0107) < 0.2:
                b = alt
            if self.leaf == "minecraft:ice" and \
                    h3(x, y, z, self.seed ^ 0x81CE) < 0.10:
                b = "minecraft:blue_ice"            # 冰叶混比 70/20/10
            # ice 等非叶方块无 persistent 属性 — 按块名后缀判定(实机非法属性会炸)
            suffix = "[persistent=true]" if b.endswith("_leaves") else ""
            out.append({"x": self.ox + x, "y": self.oy + y, "z": self.oz + z,
                        "block": b + suffix})
        out += [{"x": self.ox + x, "y": self.oy + y, "z": self.oz + z, "block": b}
                for (x, y, z), b in sorted(self.decor.items())
                if (x, y, z) not in self.wood]
        return out


def shell_surface(leaves, wood):
    """外壳面/冠底判定(壳体树冠装饰用, 阶段6 自 giant_tree 下沉共用):
    外部空气洪泛(叶 bbox 外扩 1 格, 从边界 BFS, 不经过叶/木) →
    (outer_shell, col_bottom):
    - outer_shell: 邻接外部空气的叶格(=外壳面; 内壳面贴冠内空腔, 不算)
    - col_bottom: {(x,z): 该列最低叶格}(冠底外壳 — 垂挂/下缘装饰锚点)
    确定性: 输出顺序=leaves 传入顺序(建议 sorted); BFS 集合与序无关。"""
    adj6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    ll = list(leaves)
    xs = [c[0] for c in ll]
    ys = [c[1] for c in ll]
    zs = [c[2] for c in ll]
    x0, x1 = min(xs) - 1, max(xs) + 1
    y0, y1 = min(ys) - 1, max(ys) + 1
    z0, z1 = min(zs) - 1, max(zs) + 1
    outside = set()
    stack = []
    for x in range(x0, x1 + 1):
        for y in (y0, y1):
            for z in range(z0, z1 + 1):
                stack.append((x, y, z))
    for x in (x0, x1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                stack.append((x, y, z))
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in (z0, z1):
                stack.append((x, y, z))
    while stack:
        c = stack.pop()
        if c in outside or c in leaves or c in wood:
            continue
        outside.add(c)
        x, y, z = c
        for dx, dy, dz in adj6:
            n2 = (x + dx, y + dy, z + dz)
            if x0 <= n2[0] <= x1 and y0 <= n2[1] <= y1 and z0 <= n2[2] <= z1:
                stack.append(n2)
    outer_shell = [c for c in ll if any(
        (c[0] + dx, c[1] + dy, c[2] + dz) in outside for dx, dy, dz in adj6)]
    col_bottom = {}
    for c in ll:
        k = (c[0], c[2])
        if k not in col_bottom or c[1] < col_bottom[k][1]:
            col_bottom[k] = c
    return outer_shell, col_bottom


def pick_even(cands, m, cx, cz, rng):
    """8 扇区均布选取(以 (cx,cz) 为心, 扇区内 rng.shuffle, 扇区间轮转) —
    展示树装饰点均匀分布用。rng 调用方种子流(调用顺序即确定性)。"""
    bins = {}
    for (x, y, z) in cands:
        sec = int((math.atan2(z - cz, x - cx) + math.pi) / (math.pi / 4)) % 8
        bins.setdefault(sec, []).append((x, y, z))
    pools = list(bins.values())
    for pl in pools:
        rng.shuffle(pl)
    out = []
    while len(out) < m and any(pools):
        for pl in pools:
            if pl and len(out) < m:
                out.append(pl.pop())
    return out
