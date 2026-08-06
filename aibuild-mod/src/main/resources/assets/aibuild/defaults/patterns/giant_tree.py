#!/usr/bin/env python3
"""giant_tree.py — space-colonization giant tree (巨树) generator. EXPERIMENTAL.

v2 (2026-08-06, R8 对照精灵树参考图调优):
- 主枝样条: 3-5 条显性主枝从冠底发出, "先平展再上扬"(仰角逐步抬升),
  细枝在主枝周围局部空间殖民 — 治 v1 "灌木化"(大枝只在冠缘剧烈分叉)
- 云片分层冠: 吸引点撒在每根主枝末端的扁椭球层盘 + 顶部盘(canopy_layers
  控层数), 不再是单个椭球 — 治"叶团葡萄串"的远因
- 干形: form=straight/curved/leaning(弯干=平滑蛇形漂移, 斜干=恒定偏向),
  主干沿骨架走不再强制垂直; taper 收分(3x3→2x2 / 2x2→1x1 上部 40%)
- 叶团沿枝成簇: 末端 + 末端的父节点都长叶团(链条簇), 不再是孤立球

v1 算法核心(Runions et al. 2007 空间殖民, 体素化)不变: 吸引点消耗/管模型
枝径(desc-tip 计数)/板根阶梯鳍/镂空叶团/整树 flood-fill 剪不连通。
Fully deterministic: same params + same seed = same tree; origin only translates.
Stdlib only. Output: {"blocks":[{x,y,z,block}...]}.

Usage:
  python giant_tree.py --params '{"origin":[100,64,100],"height":22,"canopy_radius":8,"trunk":3,"seed":7,"form":"curved"}' [--out t.json]
"""
import argparse, json, math, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out

DEFAULTS = {
    "origin": [0, 64, 0],       # [x,y,z] trunk base min corner, y = ground layer
    "height": 18,               # 10-60, total tree height in blocks
    "canopy_radius": 6,         # 3-20, crown envelope horizontal radius
    "trunk": 2,                 # 2 = 2x2 bole | 3 = 3x3 bole
    "species": "oak",           # oak | dark_oak
    "seed": 0,                  # int; same seed = same tree
    "buttress": True,           # 板根: 4-6 stepped root fins around the base
    "leaf_density": 0.6,        # 0.1-1.0; scales tip blob size + carving
    "form": "straight",         # straight | curved | leaning | spiral (干形)
    "preset": "",               # 形态卡 id(PRESETS 之一); 给了就按卡填形态参数
    "no_foliage": False,        # True = 纯骨架(枯立木); 正常树别动
    "limbs": 0,                 # 主枝数 3-6; 0 = seed 自动
    "canopy_layers": 2,         # 冠层盘数档 1-4 (1=旧椭球感, 2-4=云片分层)
    "taper": True,              # 干柱收分: 上部 40% 缩一档
}
SPECIES = {"oak": ("minecraft:oak_log", "minecraft:oak_leaves", "minecraft:oak_fence"),
           "dark_oak": ("minecraft:dark_oak_log", "minecraft:dark_oak_leaves",
                        "minecraft:dark_oak_fence")}
FORMS = ("straight", "curved", "leaning", "spiral")
# 形态卡预设(scratch/giant_tree/tree_forms.json 调研固化, docs/research/tree-forms.md
# 有每卡的形态依据与来源 URL)。preset 只填形态参数; height/canopy_radius/seed
# 由调用方按体量档给, 显式参数永远覆盖预设。
PRESETS = {
    "ancient_oak":       {"form": "straight", "limbs": 5, "canopy_layers": 2, "leaf_density": 0.75},
    "sky_pillar":        {"form": "straight", "limbs": 5, "canopy_layers": 4, "leaf_density": 0.5},
    "gnarled_twist":     {"form": "curved",   "limbs": 4, "canopy_layers": 3, "leaf_density": 0.35},
    "leaning_river":     {"form": "leaning",  "limbs": 5, "canopy_layers": 1, "leaf_density": 0.6},
    "banyan_court":      {"form": "straight", "limbs": 6, "canopy_layers": 2, "leaf_density": 0.8},
    "umbrella_acacia":   {"form": "straight", "limbs": 4, "canopy_layers": 2, "leaf_density": 0.5},
    "weeping_willow":    {"form": "straight", "limbs": 5, "canopy_layers": 1, "leaf_density": 0.4},
    "cloud_disc":        {"form": "curved",   "limbs": 5, "canopy_layers": 4, "leaf_density": 0.5},
    "spirit_candelabra": {"form": "spiral",   "limbs": 4, "canopy_layers": 3, "leaf_density": 0.45},
    "world_tree":        {"form": "straight", "limbs": 6, "canopy_layers": 3, "leaf_density": 0.6,
                          "trunk": 3},
    "dead_snag":         {"form": "curved",   "limbs": 5, "canopy_layers": 1, "leaf_density": 0.1,
                          "no_foliage": True},
}
DIRS8 = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
STEP, INFLUENCE, KILL = 1.0, 4.0, 1.6     # colonization radii (blocks)
THICK_TIPS, LOG_TIPS = 8, 3               # descendant-tip calibre thresholds
MAX_NODES, MAX_ITERS = 12000, 500


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
        self.trunk_ids = [0]                            # 主干链(phase 1 记录)
        self.limb_ends = []                             # 主枝末端节点 id
        # 干形曲线参数(seed 推导)
        self.lean_az = self.rng.uniform(0, 2 * math.pi)
        self.curve_freq = self.rng.uniform(0.25, 0.4)
        self.curve_phase = self.rng.uniform(0, 2 * math.pi)
        self.points, self.alive = [], []

    # ------------------------------------------------------- trunk forms --
    def _trunk_bias(self, y):
        """干形水平偏向: straight=微抖; leaning=恒定偏向; curved=蛇形;
        spiral=螺旋(Ori 精灵树同款扭转干, xz 同频相差 π/2)。"""
        f = self.p["form"]
        if f == "leaning":
            bx, bz = math.cos(self.lean_az) * 0.22, math.sin(self.lean_az) * 0.22
            return bx + self.rng.uniform(-0.06, 0.06), bz + self.rng.uniform(-0.06, 0.06)
        if f == "curved":
            a = 0.28 if y > 2 else 0.0                  # 基部 2 格保持垂直(接板根)
            return (a * math.sin(y * self.curve_freq + self.curve_phase),
                    a * math.cos(y * self.curve_freq * 0.7 + self.curve_phase))
        if f == "spiral":
            a = 0.34 if y > 2 else 0.0
            return (a * math.sin(y * self.curve_freq + self.curve_phase),
                    a * math.cos(y * self.curve_freq + self.curve_phase))
        return self.rng.uniform(-0.12, 0.12), self.rng.uniform(-0.12, 0.12)

    def grow(self):
        crown_bot = self.yc - self.ry
        # ---- phase 1: 主干(leader 直到冠底), 应用干形偏向
        while True:
            lead = self.trunk_ids[-1]
            lx, ly, lz = self.nodes[lead]
            if ly >= crown_bot or len(self.nodes) >= MAX_NODES:
                break
            bx, bz = self._trunk_bias(ly)
            ln = math.sqrt(bx * bx + 1.0 + bz * bz)
            self._add(lead, (lx + bx / ln * STEP, ly + STEP / ln, lz + bz / ln * STEP))
            self.trunk_ids.append(len(self.nodes) - 1)
        # ---- phase 2: 显性主枝(先平展再上扬样条)
        n_limbs = int(self.p["limbs"]) or self.rng.randint(3, 5)
        n_limbs = max(3, min(6, n_limbs))
        r = self.p["canopy_radius"]
        az0 = self.rng.uniform(0, 2 * math.pi)
        h = self.p["height"]
        for i in range(n_limbs):
            # 起叉高度: 0.35-0.55 树高(形态规律: 低位起叉才有巨木感),
            # 映射到主干链上最近的节点
            h_start = h * (0.35 + 0.2 * (i / max(1, n_limbs - 1)) + self.rng.uniform(-0.03, 0.03))
            start_id = min(self.trunk_ids,
                           key=lambda nid: abs(self.nodes[nid][1] - h_start))
            az = az0 + i * (2 * math.pi / n_limbs) + self.rng.uniform(-0.2, 0.2)
            el = self.rng.uniform(0.1, 0.2)             # 近平展起角
            tilt = self.rng.uniform(0.05, 0.09)         # 上扬段每步仰角抬升
            el_cap = self.rng.uniform(0.85, 1.15)
            steps = max(3, int(r * self.rng.uniform(0.75, 0.95)))
            flat = int(steps * self.rng.uniform(0.4, 0.6))  # 先平展行程
            pos = self.nodes[start_id]
            cur = start_id
            for s in range(steps):
                dx = math.cos(az) * math.cos(el)
                dy = math.sin(el)
                dz = math.sin(az) * math.cos(el)
                pos = (pos[0] + dx * STEP, pos[1] + dy * STEP, pos[2] + dz * STEP)
                self._add(cur, pos)
                cur = len(self.nodes) - 1
                if s >= flat:                           # 平展段保持低仰角
                    el = min(el_cap, el + tilt)
                az += self.rng.uniform(-0.05, 0.05)
            # 层盘中心推到枝端外侧: 主枝平展段要留白可读, 叶盘长在枝端之外
            self.limb_ends.append((cur, (dx, dy, dz), steps))
        # ---- phase 3: 吸引点(云片层盘: 每主枝末端一盘 + 顶部盘)
        self.points, self.alive = self._scatter()
        # ---- phase 4: 空间殖民(细枝填充层盘)
        self._colonize()

    def _scatter(self):
        """层盘撒点: 每主枝末端扁椭球盘(中心推到枝端外侧 0.3 行程,
        主枝平展段留白可读); canopy_layers>=2 加顶部盘, >=3 每主枝中段加盘。
        点数按总体积/7, 钳 60..1400。"""
        r = self.p["canopy_radius"]
        layers = int(self.p["canopy_layers"])
        rl = max(2.0, r * 0.4)
        hl = max(1.5, self.ry * 0.3)
        discs = []
        for li, ldir, steps in self.limb_ends:
            x, y, z = self.nodes[li]
            push = 0.3 * steps
            cx, cy, cz = x + ldir[0] * push, y + ldir[1] * push, z + ldir[2] * push
            discs.append((cx, cy, cz, rl, hl))
            if layers >= 3:
                mid = self.parent[li]
                for _ in range(3):
                    if mid in self.trunk_ids or mid <= 0:
                        break
                    mid = self.parent[mid]
                mx, my, mz = self.nodes[mid]
                discs.append((mx + ldir[0] * 1.5, my, mz + ldir[2] * 1.5, rl * 0.7, hl))
        if layers >= 2:
            discs.append((self.c, self.yc + self.ry * 0.4, self.c, r * 0.55, hl))
        if layers == 1 and self.limb_ends:
            discs = discs[:len(self.limb_ends)]
        vol = sum(4.0 / 3.0 * math.pi * dr * dr * dh for _, _, _, dr, dh in discs)
        n = max(60, min(1400, int(vol / 7)))
        per = max(1, n // max(1, len(discs)))
        pts, alive = [], []
        for (cx, cy, cz, dr, dh) in discs:
            cnt = 0
            while cnt < per:
                x = self.rng.uniform(-dr, dr)
                y = self.rng.uniform(-dh, dh)
                z = self.rng.uniform(-dr, dr)
                if (x / dr) ** 2 + (y / dh) ** 2 + (z / dr) ** 2 > 1.0:
                    continue
                pts.append((cx + x, cy + y, cz + z))
                alive.append(True)
                cnt += 1
        return pts, alive

    def _colonize(self):
        di2, dk2 = INFLUENCE * INFLUENCE, KILL * KILL
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
                    pending += 1
                elif best[0] <= dk2:
                    self.alive[pi] = False
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
                ln = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
                self._add(ni, (x + dx / ln * STEP, y + dy / ln * STEP,
                               z + dz / ln * STEP))
            if not influ and pending == 0:
                break

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

    def _bole_section(self, cx, cz, y, size):
        """以 (cx,cz) 浮点为中心的 size×size 水平截面(收分用)。"""
        half = (size - 1) / 2.0
        for ix in range(size):
            for iz in range(size):
                self.put_wood(rhu(cx - half) + ix, y, rhu(cz - half) + iz,
                              "%s[axis=y]" % self.log)

    def rasterize(self):
        desc, clear_h = self.desc, self.clear_h
        # 主干: 沿骨架链逐格截面(可弯/斜); 收分按主干链的尾部 35%
        # (与起叉点无关 — 起叉低不等于干变细)
        trunk_set = set(self.trunk_ids)
        span = max(1, len(self.trunk_ids))
        for idx, nid in enumerate(self.trunk_ids):
            x, y, z = self.nodes[nid]
            size = self.ts if (not self.p["taper"] or idx < span * 0.65) \
                else max(1, self.ts - 1)
            self._bole_section(x, z, rhu(y), size)
        for i in range(1, len(self.nodes)):
            if i in trunk_set:
                continue                                # 主干已画
            pa = self.parent[i]
            a = tuple(rhu(v) for v in self.nodes[pa])
            b = tuple(rhu(v) for v in self.nodes[i])
            dx, dy, dz = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            axis = "x" if abs(dx) >= abs(dy) and abs(dx) >= abs(dz) else \
                   ("y" if abs(dy) >= abs(dz) else "z")
            in_trunk_zone = rhu(self.nodes[i][1]) <= clear_h and rhu(self.nodes[pa][1]) <= clear_h \
                and pa in trunk_set
            thick = desc[i] >= THICK_TIPS
            spec = self.fence if (not in_trunk_zone and desc[i] < LOG_TIPS) else \
                "%s[axis=%s]" % (self.log, axis)
            for cell in vline(a, b):
                if in_trunk_zone:
                    continue                            # 主干区内由截面画过
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
        base = self.nodes[min(1, len(self.nodes) - 1)]
        bcx, bcz = base[0], base[2]
        for ddx, ddz in dirs:
            px = rhu(bcx + ddx * c)
            pz = rhu(bcz + ddz * c)
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
            if not ch and i not in self.trunk_ids:      # terminal twig tip
                self.blob(*[rhu(v) for v in self.nodes[i]], r, carve)
                pa = self.parent[i]                     # 父节点小团补链(更稀更薄,
                if pa > 0 and pa not in self.trunk_ids:  # 防葡萄串也防糊死)
                    self.blob(*[rhu(v) for v in self.nodes[pa]],
                              max(1, r - 2), min(0.5, carve + 0.1))
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
    if not p.get("no_foliage"):
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
    for key, lo, hi in (("height", 10, 60), ("canopy_radius", 3, 20)):
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
    if p["form"] not in FORMS:
        die("form must be one of %s" % (FORMS,), {"form": list(FORMS)})
    try:
        p["limbs"] = int(p["limbs"])
    except (TypeError, ValueError):
        die("limbs must be 0-6 (0=auto)", {"limbs": 0})
    if not 0 <= p["limbs"] <= 6:
        die("limbs must be 0-6 (0=auto)", {"limbs": 0})
    try:
        p["canopy_layers"] = int(p["canopy_layers"])
    except (TypeError, ValueError):
        die("canopy_layers must be 1-4", {"canopy_layers": 2})
    if not 1 <= p["canopy_layers"] <= 4:
        die("canopy_layers must be 1-4", {"canopy_layers": 2})
    if not isinstance(p["taper"], bool):
        die("taper must be true|false", {"taper": True})
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
        user = json.loads(a.params) if a.params.strip() else {}
    except json.JSONDecodeError as e:
        die("--params is not valid JSON: %s" % e,
            {"example": '{"origin":[100,64,100],"height":22,"canopy_radius":8,"seed":7}'})
    preset = user.get("preset")
    if preset:
        if preset not in PRESETS:
            die("unknown preset '%s'" % preset, {"presets": sorted(PRESETS)})
        p.update(PRESETS[preset])                       # 预设先填
        user = {k: v for k, v in user.items() if k != "preset"}
        p.update(user)                                  # 显式参数覆盖预设
    else:
        p.update(user)
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
