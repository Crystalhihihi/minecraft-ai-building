#!/usr/bin/env python3
"""giant_tree.py — 巨树(景观大树/巨树/地标树)生成器. EXPERIMENTAL.

v3 (2026-08-07, 治实测"断头/粗细突变/高度虚标/平板木"):
- 顶梢干(leader)一路穿到树梢(进入顶盘): v2 主干止于冠底, 顶盘离任何节点
  超过殖民影响半径永久锁死 → 要 40 给 28 的"断头"。现在干即树脊
- 盘壳叶: 叶=每盘镂空壳层(v∈[0.68,1]) + 盘内贴木簇, 取代 v2 末梢绒球
  (葡萄串远因); 云片层盘有了实心轮廓。小盘降内界+减镂空补实(治虫蛀冠)
- 盘内辐枝扇(取代空间殖民): 每盘锚枝到盘心 + 5-7 辐条打到壳缘 — 殖民
  吸引点均布盘内会淤成 1-2 格厚平板木(叶壳盖不住), 辐扇=云片树真实内构;
  全确定性, 无死锁, 地标级从 ~40s 降到秒级
- 沿主枝盘链+核心盘: 盘不再只在枝端(主枝后半程布盘 + 分叉区核心盘),
  治"冠边 puff 串+冠心裸木"
- 渐进收分+半砖过渡: 干柱沿顶梢从 ts×ts 逐档缩到 1x1(前 25% 足尺),
  每档缩径层在旧截面外环铺 bottom 半砖 — 0.5 格台阶取代 1 格突变
- 截面连通兜底: 弯/斜/螺旋干截面中心漂移可能前后层 xz 各偏 1 格(对角=
  不连通, flood-fill 会剪掉整段顶梢), 每层铺 vline 层内桥
- 上限提升: height 10-150 / canopy_radius 3-50 / trunk 2-5(地标级直出,
  不再 60 截断); 板根/枝粗阈值随体量缩放

v2 (2026-08-06, R8): 显性主枝样条(低位起叉先平展再上扬)/云片层盘/干形四式
(直弯斜螺旋)/板根阶梯鳍/整树 flood-fill 剪不连通。
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
    "height": 18,               # 10-150, total tree height in blocks
    "canopy_radius": 6,         # 3-50, crown envelope horizontal radius
    "trunk": 2,                 # 2..5 = ts×ts bole at base (渐进收分到 1x1 顶梢)
    "species": "oak",           # oak | dark_oak
    "seed": 0,                  # int; same seed = same tree
    "buttress": True,           # 板根: 4-6 stepped root fins around the base
    "leaf_density": 0.6,        # 0.1-1.0; scales shell carving (越大叶越密)
    "form": "straight",         # straight | curved | leaning | spiral (干形)
    "preset": "",               # 形态卡 id(PRESETS 之一); 给了就按卡填形态参数
    "no_foliage": False,        # True = 纯骨架(枯立木); 正常树别动
    "limbs": 0,                 # 主枝数 3-6; 0 = seed 自动
    "canopy_layers": 2,         # 冠层盘数档 1-4 (1=旧椭球感, 2-4=云片分层)
    "taper": True,              # 干柱渐进收分(到 1x1 顶梢, 缩径层半砖过渡)
}
SPECIES = {"oak": ("minecraft:oak_log", "minecraft:oak_leaves", "minecraft:oak_fence",
                   "minecraft:oak_slab"),
           "dark_oak": ("minecraft:dark_oak_log", "minecraft:dark_oak_leaves",
                        "minecraft:dark_oak_fence", "minecraft:dark_oak_slab")}
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
                          "trunk": 4},
    "dead_snag":         {"form": "curved",   "limbs": 5, "canopy_layers": 1, "leaf_density": 0.1,
                          "no_foliage": True},
}
DIRS8 = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
STEP = 1.0                                # 骨架步进(格)
LOG_TIPS = 3                              # fence 梢阈值(不随体量变)
MAX_NODES = 60000                         # 骨架节点安全上限
SHELL_IN = 0.68                           # 盘壳内界(v>=SHELL_IN 为壳层)
HUG = 2.4                                 # 盘内贴木生叶半径


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
        self.log, self.leaf, self.fence, self.slab = SPECIES[p["species"]]
        self.rng = random.Random(p["seed"])
        self.seed = int(p["seed"])
        self.wood, self.leaves = {}, set()
        h, r = p["height"], p["canopy_radius"]
        self.ry = max(2, min(rhu(r * 0.6), (h - 3) // 2))
        self.hl = max(1.5, self.ry * 0.3)               # 层盘半高
        self.yc = h - self.ry                           # crown centre y
        self.nodes = [(self.c, 0.0, self.c)]            # float skeleton
        self.parent = [-1]
        self.children = [[]]
        self.trunk_ids = [0]                            # 顶梢干链(phase 1 记录)
        self.limb_ends = []                             # 主枝末端节点 id
        self.discs = []                                 # 层盘 (cx,cy,cz,dr,dh)
        # 干形曲线参数(seed 推导)
        self.lean_az = self.rng.uniform(0, 2 * math.pi)
        self.curve_freq = self.rng.uniform(0.10, 0.18)   # 低频慢扭(高频=碎锯齿)
        self.curve_phase = self.rng.uniform(0, 2 * math.pi)

    # ------------------------------------------------------- trunk forms --
    def _trunk_offset(self, y):
        """干形水平偏移曲线 o(y)(解析式, 有界): spiral=绕轴螺旋半径 R;
        curved=有界蛇形振幅 A; 其余=0。基部 2 格归零(接板根), 振幅 6 格渐入
        (防 y=3 处相位突变跳干)。"""
        if y <= 2:
            return 0.0, 0.0
        f = self.p["form"]
        yy = y - 2.0
        ramp = min(1.0, yy / 6.0)
        if f == "spiral":
            R = min(2.5, 0.6 * self.ts + 0.7)
            w = self.curve_freq * 1.6
            return (ramp * R * math.sin(yy * w + self.curve_phase),
                    ramp * R * math.cos(yy * w + self.curve_phase))
        if f == "curved":
            A = min(2.0, 0.5 * self.ts + 0.5)
            return (ramp * A * math.sin(yy * self.curve_freq + self.curve_phase),
                    ramp * A * math.sin(yy * self.curve_freq * 0.7 + self.curve_phase * 1.3))
        return 0.0, 0.0

    def _trunk_bias(self, y):
        """每步水平偏向 = 偏移曲线差分(关键: 偏移有界, 干绕轴而不 wander —
        旧版直接积分 sin 偏向, 螺旋干中段漂出冠幅读成悬空裸枝)。"""
        f = self.p["form"]
        if f == "leaning":
            bx, bz = math.cos(self.lean_az) * 0.22, math.sin(self.lean_az) * 0.22
            return bx + self.rng.uniform(-0.06, 0.06), bz + self.rng.uniform(-0.06, 0.06)
        if f in ("curved", "spiral"):
            ox1, oz1 = self._trunk_offset(y + 1.0)
            ox0, oz0 = self._trunk_offset(y)
            return (ox1 - ox0 + self.rng.uniform(-0.05, 0.05),
                    oz1 - oz0 + self.rng.uniform(-0.05, 0.05))
        return self.rng.uniform(-0.12, 0.12), self.rng.uniform(-0.12, 0.12)

    def grow(self):
        h = self.p["height"]
        # ---- phase 1: 顶梢干(leader 一路到树梢, 穿进顶盘) — 干即树脊,
        # 治 v2 "主干止于冠底, 顶盘锁死不长"的断头
        leader_top = h - max(1, rhu(self.hl * 0.5))
        while True:
            lead = self.trunk_ids[-1]
            lx, ly, lz = self.nodes[lead]
            if ly >= leader_top or len(self.nodes) >= MAX_NODES:
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
        for i in range(n_limbs):
            # 起叉高度: 0.35-0.55 树高(形态规律: 低位起叉才有巨木感),
            # 映射到顶梢干链上最近的节点
            h_start = h * (0.35 + 0.2 * (i / max(1, n_limbs - 1)) + self.rng.uniform(-0.03, 0.03))
            start_id = min(self.trunk_ids,
                           key=lambda nid: abs(self.nodes[nid][1] - h_start))
            az = az0 + i * (2 * math.pi / n_limbs) + self.rng.uniform(-0.2, 0.2)
            el = self.rng.uniform(0.25, 0.45)           # 起角抬高(低角=蜘蛛腿)
            tilt = self.rng.uniform(0.04, 0.08)         # 上扬段每步仰角抬升
            el_cap = self.rng.uniform(0.8, 1.05)
            steps = max(3, int(r * self.rng.uniform(0.5, 0.7)))   # 枝长收敛在冠幅内
            flat = int(steps * self.rng.uniform(0.25, 0.4))       # 短平展段
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
        # ---- phase 3: 层盘 + 盘内辐枝扇(确定性轮辐: 盘心锚枝 + 5-7 辐条打到
        # 壳缘。v3 曾用空间殖民填盘, 吸引点均布盘内 → 细枝淤成 1-2 格厚平板木,
        # 叶壳盖不住; 大盘还殖民死锁。轮辐=真实云片树的内构)
        self.discs = self._make_discs()
        self.pre_fan = len(self.nodes)              # 主干+主枝阶段节点界
        self.spoke_thick = set()                    # 大盘辐条根(2 宽)
        self._disc_fans()

    def _make_discs(self):
        """层盘: 沿每根主枝后半程布盘链(盘心在枝节点上, 间距随 canopy_layers
        收密 — 云片沿枝连续成层, 治"末端单盘+中段裸枝"), 枝端盘外推 0.3 行程
        让平展段留白可读; layers>=2 加顶部盘(盘顶≈树梢, 盘心跟随顶梢干尖 —
        弯干/螺旋干顶盘不跑偏)。"""
        r = self.p["canopy_radius"]
        layers = int(self.p["canopy_layers"])
        rl = max(2.0, r * 0.4)
        spacing = max(2, int(rl * (1.8 - 0.2 * layers)))   # layers1≈3.2rl稀..4≈2rl密
        trunk_set = set(self.trunk_ids)
        discs = []
        for li, ldir, steps in self.limb_ends:
            chain = []                                   # 主枝链 base→tip
            cur = li
            while cur not in trunk_set and cur > 0:
                chain.append(cur)
                cur = self.parent[cur]
            chain.reverse()
            for ci in range(int(len(chain) * 0.45), len(chain), spacing):
                x, y, z = self.nodes[chain[ci]]
                discs.append((x, y, z, rl * 0.75, self.hl))
            x, y, z = self.nodes[li]                     # 枝端盘(略大, 外推)
            push = 0.3 * steps
            discs.append((x + ldir[0] * push, y + ldir[1] * push, z + ldir[2] * push,
                          rl, self.hl))
        if layers >= 2:
            tx, _, tz = self.nodes[self.trunk_ids[-1]]   # 顶梢干尖水平位
            discs.append((tx, self.p["height"] - self.hl, tz, r * 0.55, self.hl))
        # 核心盘: 主枝分叉区(yc 高度, 跟随该处干位) — 治小树/疏树冠心裸木感
        mid_id = min(self.trunk_ids, key=lambda nid: abs(self.nodes[nid][1] - self.yc))
        mx, _, mz = self.nodes[mid_id]
        discs.append((mx, self.yc, mz, max(2.5, r * 0.5), self.hl))
        return discs

    def _disc_fans(self):
        """每盘一轮辐扇: 最近节点链接到盘心(锚枝), 再从盘心辐射 n_spokes 条
        辐枝到壳缘附近。辐枝仰角被盘扁度钳制(不捅出盘顶), 方位角均分+抖动。
        大盘(dr>=10)辐枝前 40% 记 spoke_thick 画 2 宽(云片下的粗枝脚)。"""
        rng = self.rng
        bare = bool(self.p.get("no_foliage"))
        for (cx, cy, cz, dr, dh) in self.discs:
            best = min(range(len(self.nodes)),
                       key=lambda i: ((self.nodes[i][0] - cx) ** 2 +
                                      (self.nodes[i][1] - cy) ** 2 +
                                      (self.nodes[i][2] - cz) ** 2))
            while len(self.nodes) < MAX_NODES:        # 锚枝接到盘心
                x, y, z = self.nodes[best]
                vx, vy, vz = cx - x, cy - y, cz - z
                d = math.sqrt(vx * vx + vy * vy + vz * vz)
                if d <= 0.5:
                    break
                self._add(best, (x + vx / d * STEP, y + vy / d * STEP,
                                 z + vz / d * STEP))
                best = len(self.nodes) - 1
            center_id = best
            n_spokes = 5 + rng.randrange(3) + (3 if bare else 0)
            el_max = min(0.55, math.atan2(dh * 0.9, dr * 0.8 + 0.001))
            az0 = rng.uniform(0, 2 * math.pi)
            for k in range(n_spokes):
                az = az0 + k * (2 * math.pi / n_spokes) + rng.uniform(-0.25, 0.25)
                el = rng.uniform(-0.3, 0.6) if bare else rng.uniform(0.1, el_max)
                steps = max(2, int(dr * rng.uniform(0.7, 0.9)))
                cur = center_id
                pos = self.nodes[cur]
                for s in range(steps):
                    dx = math.cos(az) * math.cos(el)
                    dy = math.sin(el)
                    dz = math.sin(az) * math.cos(el)
                    pos = (pos[0] + dx * STEP, pos[1] + dy * STEP, pos[2] + dz * STEP)
                    self._add(cur, pos)
                    cur = len(self.nodes) - 1
                    if dr >= 10.0 and s < steps * 0.4:
                        self.spoke_thick.add(cur)
                    az += rng.uniform(-0.06, 0.06)
                    el += rng.uniform(-0.03, 0.04)

    def _add(self, parent, pos):
        self.nodes.append(pos)
        self.parent.append(parent)
        self.children.append([])
        self.children[parent].append(len(self.nodes) - 1)

    # --------------------------------------------------------- rasterize --
    def calibre(self):
        """descendant-tip counts -> per-segment width class; first fork y.
        粗枝阈值随总体量缩放(大树枝尖计数膨胀, 固定 8 会满树 2 宽梁)。"""
        desc = [0] * len(self.nodes)
        for i in reversed(range(len(self.nodes))):
            desc[i] = sum(desc[c] for c in self.children[i]) or 1
        self.thick_tips = max(8, desc[0] // 150)
        forks = [i for i, c in enumerate(self.children) if len(c) >= 2]
        clear_h = min((rhu(self.nodes[i][1]) for i in forks), default=self.p["height"] - 2)
        clear_h = max(3, min(self.p["height"] - 2, clear_h))
        return desc, clear_h

    def put_wood(self, x, y, z, spec):
        self.wood[(x, y, z)] = spec

    def _bole_section(self, cx, cz, y, size):
        """以 (cx,cz) 浮点为中心的 size×size 水平截面(收分用)。返回 (x,z) 集合。"""
        half = (size - 1) / 2.0
        cells = set()
        for ix in range(size):
            for iz in range(size):
                x, z = rhu(cx - half) + ix, rhu(cz - half) + iz
                self.put_wood(x, y, z, "%s[axis=y]" % self.log)
                cells.add((x, z))
        return cells

    def rasterize(self):
        desc, clear_h = self.desc, self.clear_h
        # 顶梢干: 沿骨架链逐格截面(可弯/斜); 渐进收分 — 前 25% 足尺,
        # 之后线性缩到 1x1 顶梢; 每档缩径层在旧截面外环铺 bottom 半砖,
        # 0.5 格台阶过渡取代 1 格突变(实测"粗细突变"反馈)
        trunk_set = set(self.trunk_ids)
        span = max(1, len(self.trunk_ids))
        prev_cells, prev_size = None, None
        prev_pos, prev_yy = None, None
        for idx, nid in enumerate(self.trunk_ids):
            x, y, z = self.nodes[nid]
            yy = rhu(y)
            frac = idx / span
            if not self.p["taper"] or frac < 0.25:
                size = self.ts
            else:
                size = max(1, int(round(self.ts - (self.ts - 1) * (frac - 0.25) / 0.75)))
            if prev_pos is not None and yy > prev_yy:
                # 连通兜底: 弯/斜/螺旋干的截面中心漂移可能前后层xz各偏1格
                # (对角接触=不连通, 实测把整段顶梢+顶盘剪没)。每层先用 vline
                # 在层内铺一条面连通桥到上一截面中心, 跳层则补中间层
                px, pz = rhu(prev_pos[0]), rhu(prev_pos[2])
                for fy in range(prev_yy + 1, yy):       # 跳层保险(正常不会发生)
                    self._bole_section(px, pz, fy, size)
                for cell in vline((px, yy, pz), (rhu(x), yy, rhu(z))):
                    self.put_wood(*cell, "%s[axis=y]" % self.log)
            cells = self._bole_section(x, z, yy, size)
            if (prev_cells is not None and size < prev_size and prev_yy is not None
                    and yy > prev_yy):
                for (lx, lz) in prev_cells - cells:
                    self.put_wood(lx, yy, lz, "%s[type=bottom]" % self.slab)
            prev_cells, prev_size = cells, size
            prev_pos, prev_yy = (x, y, z), yy
        for i in range(1, len(self.nodes)):
            if i in trunk_set:
                continue                                # 顶梢干已画
            pa = self.parent[i]
            a = tuple(rhu(v) for v in self.nodes[pa])
            b = tuple(rhu(v) for v in self.nodes[i])
            dx, dy, dz = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            axis = "x" if abs(dx) >= abs(dy) and abs(dx) >= abs(dz) else \
                   ("y" if abs(dy) >= abs(dz) else "z")
            in_trunk_zone = rhu(self.nodes[i][1]) <= clear_h and rhu(self.nodes[pa][1]) <= clear_h \
                and pa in trunk_set
            thick = (i < self.pre_fan and desc[i] >= self.thick_tips) or \
                i in self.spoke_thick
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
        """板根: 4-6 stepped fins; 长度/高度随干径缩放(大树大根)。"""
        n = 4 + self.rng.randrange(3)
        start = self.rng.randrange(8)
        dirs, seen = [], set()
        for k in range(n):
            d = DIRS8[(start + rhu(k * 8.0 / n)) % 8]
            if d not in seen:
                seen.add(d)
                dirs.append(d)
        length, c = self.ts + 2, self.c
        base = self.nodes[min(1, len(self.nodes) - 1)]
        bcx, bcz = base[0], base[2]
        for ddx, ddz in dirs:
            px = rhu(bcx + ddx * c)
            pz = rhu(bcz + ddz * c)
            axis = "x" if abs(ddx) >= abs(ddz) else "z"
            for k in range(1, length + 1):
                hgt = max(1, self.ts + 1 - k)           # ts=2: 3,2,1,1 | ts=5: 6..1
                cols = [(px + k * ddx, pz + k * ddz)]
                if ddx and ddz:                         # diagonal fin: L-corner column
                    cols.append((px + k * ddx, pz + (k - 1) * ddz))
                for cx, cz in cols:
                    for y in range(hgt):
                        self.put_wood(cx, y, cz, "%s[axis=%s]" % (
                            self.log, axis if y == hgt - 1 else "y"))

    # ----------------------------------------------------------- foliage --
    def foliage(self):
        """盘壳叶: 每盘 v∈[SHELL_IN,1] 镂空壳层(剪影主体) + 盘内贴木簇
        (HUG 内, 更稀) — 取代 v2 末梢绒球(葡萄串)。carve 由 leaf_density 控。"""
        ld = self.p["leaf_density"]
        carve = 0.32 - 0.20 * ld                        # ld=0.6 → 0.20
        hug2 = HUG * HUG
        wb = {}
        for (x, y, z) in self.wood:
            wb.setdefault((x // 3, y // 3, z // 3), []).append((x, y, z))

        def near_wood(x, y, z):
            gx, gy, gz = x // 3, y // 3, z // 3
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        for (wx, wy, wz) in wb.get((gx + dx, gy + dy, gz + dz), ()):
                            if ((wx - x) ** 2 + (wy - y) ** 2 + (wz - z) ** 2) <= hug2:
                                return True
            return False

        for (cx, cy, cz, dr, dh) in self.discs:
            R, H = math.ceil(dr), math.ceil(dh)
            # 小盘壳薄, 降内界+减镂空补实(治小树"虫蛀冠"); 大盘保持透气
            shell_in = SHELL_IN if dr >= 6.0 else 0.45
            cscale = min(1.0, dr / 5.0)
            for dx in range(-R, R + 1):
                for dz in range(-R, R + 1):
                    for dy in range(-H, H + 1):
                        v = (dx / dr) ** 2 + (dy / dh) ** 2 + (dz / dr) ** 2
                        if v > 1.0:
                            continue
                        x, y, z = rhu(cx) + dx, rhu(cy) + dy, rhu(cz) + dz
                        shell = v >= shell_in
                        if not shell and not near_wood(x, y, z):
                            continue                  # 盘心深处不长(省块+镂空)
                        c = (carve if shell else carve * 0.4) * cscale
                        if h3(x, y, z, self.seed) < c:
                            continue                  # 镂空 breathing pocket
                        if (x, y, z) not in self.wood:
                            self.leaves.add((x, y, z))

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
    for key, lo, hi in (("height", 10, 150), ("canopy_radius", 3, 50)):
        try:
            p[key] = int(p[key])
        except (TypeError, ValueError):
            die("%s must be an int %d-%d" % (key, lo, hi), {key: [lo, hi]})
        if not lo <= p[key] <= hi:
            die("%s must be %d-%d" % (key, lo, hi), {key: [lo, hi]})
    try:
        p["trunk"] = int(p["trunk"])
    except (TypeError, ValueError):
        die("trunk must be 2-5", {"trunk": [2, 5]})
    if not 2 <= p["trunk"] <= 5:
        die("trunk must be 2-5 (ts×ts 基部干柱, 渐进收分到 1x1 顶梢)", {"trunk": [2, 5]})
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
