#!/usr/bin/env python3
"""giant_tree.py — 巨树(景观大树/巨树/地标树)生成器. EXPERIMENTAL.

v9 (2026-08-12 深夜, 治实机"六形一味/怪树"):
- 叶形=骨架拓扑+包络分形: layers 云片(主枝起叉聚成离散层档, flat 0.5,
  层间留缝) / umbrella 伞形(高位单点近水平共点射出, flat 0.4, 梢簇下垂
  成伞沿) / mist 雾团(侧枝加密, 0.17r 小簇全链高方差叠放) / blob 不变;
  层盘/辐扇体系废除, 全叶形由真分枝骨架扛
- aesthetic 美学约束(可选, 访谈二选一): 树冠 8 扇区 x 2 层簇覆盖强制,
  空洞扇区自动补短枝+端簇(心形/双塔=扇区空洞, 实测); 0=自由野生
- 新 preset: mist_crown; umbrella_acacia 改 umbrella 冠(ASPECT 0.4-0.9)

v8 (2026-08-12 深夜, 治实机"没有分枝/叶团硬凑/宽幅全靠叶"):
- 二级/三级分枝(_sub_branches, 全树通用): 主枝外侧段长 2-4 侧枝(夹角
  0.3-0.6, 0.35-0.55×母枝长), 侧枝梢再分 1-2 小枝; terminals=全枝梢表
- 幻想宽幅 foliage 重写: 辐条/壳层全废, 叶簇只坐枝梢+冠心团+顶穹团
  (分层=主枝起叉高度差天然形成); 主枝长 0.7-0.9r(宽幅靠真枝不靠叶团)
- 垂藤修正: 短 2-5+横向摆动(冰锥翻车); 灯笼锚点无辐条时回落枝梢

v7 (2026-08-12, 幻想地标系 — 用户参考图 bilibili 展示树蒸馏):
- fantasy 档(卡级开关): ASPECT 0.7-1.3 矮胖撑伞 / 冠底 0.3h / tuft 大簇
  (0.3r 封顶 6, 簇距 x2.6, 簇更透) / 辐条减半(团块独立成花椰菜) / 弯幅
  x2 / 基座巨化(flare 0.15h, 爬根 x2.5 拱高成门洞) / 粗干 size>=6 双材质纵纹
- 幻想卡 4 张: fantasy_sakura(樱花地标)/fantasy_world(世界树, trunk 10+
  flare)/fantasy_oak(湖心孤树)/fantasy_spirit(螺旋苍白); 真实系 15 卡不动
- decor 装饰钩子(任何树可用, 逗号组合): lights=冠内 shroomlight 光点 /
  lanterns=辐条外段 chain+lantern / vines=冠底垂藤叶链(渐断) / all
- 体量警告: fantasy 地标 40 高 ~2 万块 / 70 高 ~5 万(卡面须注明 footprint)

v6 (2026-08-12, 治"棒棒糖/抽象根/壳糊球"):
- 贴地爬根 roots=crawl(默认): 干基样条先拱出再逐级下扎入土, 长短混编方位
  抖动, 粗干近段双宽; flare=钟形基座(干基膨大 ~1.7ts)+短根; buttress=
  旧板根鳍保留; buttress=False 兼容旧卡=none
- blob 去壳: 壳层只剩 v∈[0.85,1] 薄皮填簇缝(旧 v∈[0.5,1] 实心壳抹掉枝纹
  是"什么冠都成一个球"的根源); 主体=辐条链上 tuft 簇(簇随枝走)
- 辐条二级锚点: ~45% 从主枝末端发出(干→主枝→辐条层级可读), 条长沿方向
  步进求交椭球壳(偏心锚点径长各异)
- tuft 参数化: 压扁度 layers 0.65(云片)/blob 0.9(球团), tuft_scale 0.6-1.6
  簇径倍率(蓬松大肉 vs 碎叶透光)
- 干径/冠幅护栏: trunk >= canopy_radius/4 否则 die(老树干径≈冠幅 1/4-1/6)

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
    "trunk": 2,                 # 2..12 = ts×ts bole at base (圆台收分+削角成圆; 粗高 ts≈h/15, 细高 ts≈h/25; 10+ 供刻纹路)
    "species": "oak",           # oak | dark_oak
    "seed": 0,                  # int; same seed = same tree
    "buttress": True,           # 兼容旧参数: False 等价 roots=none
    "roots": "crawl",           # 根式: crawl=贴地爬根(默认) | flare=钟形基座+短根 |
                                #       buttress=旧板根鳍 | none=无根
    "tuft_scale": 1.0,          # 0.6-1.6 叶簇径倍率(大=蓬松大肉, 小=碎叶透光)
    "leaf_density": 0.6,        # 0.1-1.0; scales shell carving (越大叶越密)
    "form": "straight",         # straight | curved | leaning | spiral (干形)
    "crown": "layers",          # 叶形函数: layers=云片分层 | blob=圆整球形(近似球, 用户参考图款)
    "preset": "",               # 形态卡 id(PRESETS 之一); 给了就按卡填形态参数
    "no_foliage": False,        # True = 纯骨架(枯立木); 正常树别动
    "fantasy": 0,               # 1=幻想地标档: 矮胖撑伞比例+花椰菜大叶团+弯幅
                                #   x2+冠底下压 0.25h+基座巨化+粗干双材质纵纹
    "aesthetic": 0,             # 1=美学约束: 树冠 8 扇区 x 2 层覆盖强制
                                #   (空洞自动补枝补簇); 0=自由生成(野生感)
    "decor": "",                # 装饰钩子(逗号组合): lights=冠内光点(shroomlight)
                                #   lanterns=枝下灯笼串 vines=冠底垂藤 all=全上
    "limbs": 0,                 # 主枝数 3-6; 0 = seed 自动
    "canopy_layers": 2,         # 冠层盘数档 1-4 (1=旧椭球感, 2-4=云片分层)
    "taper": True,              # 干柱渐进收分(到 1x1 顶梢, 缩径层半砖过渡)
}
SPECIES = {"oak": ("minecraft:oak_log", "minecraft:oak_leaves", "minecraft:oak_fence",
                   "minecraft:oak_slab", "minecraft:stripped_oak_log"),
           "dark_oak": ("minecraft:dark_oak_log", "minecraft:dark_oak_leaves",
                        "minecraft:dark_oak_fence", "minecraft:dark_oak_slab", "minecraft:stripped_dark_oak_log"),
           "birch": ("minecraft:birch_log", "minecraft:birch_leaves",
                     "minecraft:birch_fence", "minecraft:birch_slab", "minecraft:stripped_birch_log"),
           "spruce": ("minecraft:spruce_log", "minecraft:spruce_leaves",
                      "minecraft:spruce_fence", "minecraft:spruce_slab", "minecraft:stripped_spruce_log"),
           "jungle": ("minecraft:jungle_log", "minecraft:jungle_leaves",
                      "minecraft:jungle_fence", "minecraft:jungle_slab", "minecraft:stripped_jungle_log"),
           "acacia": ("minecraft:acacia_log", "minecraft:acacia_leaves",
                      "minecraft:acacia_fence", "minecraft:acacia_slab", "minecraft:stripped_acacia_log"),
           "cherry": ("minecraft:cherry_log", "minecraft:cherry_leaves",
                      "minecraft:cherry_fence", "minecraft:cherry_slab", "minecraft:stripped_cherry_log"),
           "mangrove": ("minecraft:mangrove_log", "minecraft:mangrove_leaves",
                        "minecraft:mangrove_fence", "minecraft:mangrove_slab", "minecraft:stripped_mangrove_log"),
           "pale_oak": ("minecraft:pale_oak_log", "minecraft:pale_oak_leaves",
                        "minecraft:pale_oak_fence", "minecraft:pale_oak_slab", "minecraft:stripped_pale_oak_log")}
FORMS = ("straight", "curved", "leaning", "spiral")
# 形态卡预设(scratch/giant_tree/tree_forms.json 调研固化, docs/research/tree-forms.md
# 有每卡的形态依据与来源 URL)。preset 只填形态参数; height/canopy_radius/seed
# 由调用方按体量档给, 显式参数永远覆盖预设。
PRESETS = {
    "ancient_oak":       {"form": "straight", "limbs": 5, "canopy_layers": 2, "leaf_density": 0.75,
                          "crown": "blob"},
    "sky_pillar":        {"form": "straight", "limbs": 5, "canopy_layers": 4, "leaf_density": 0.5},
    "gnarled_twist":     {"form": "curved",   "limbs": 4, "canopy_layers": 3, "leaf_density": 0.35},
    "leaning_river":     {"form": "leaning",  "limbs": 5, "canopy_layers": 1, "leaf_density": 0.6},
    "banyan_court":      {"form": "straight", "limbs": 6, "canopy_layers": 2, "leaf_density": 0.8,
                          "crown": "blob"},
    "umbrella_acacia":   {"form": "straight", "limbs": 5, "canopy_layers": 2, "leaf_density": 0.5,
                          "crown": "umbrella"},
    "mist_crown":        {"form": "curved",   "limbs": 5, "canopy_layers": 3, "leaf_density": 0.7,
                          "crown": "mist"},
    "weeping_willow":    {"form": "straight", "limbs": 5, "canopy_layers": 1, "leaf_density": 0.4},
    "cloud_disc":        {"form": "curved",   "limbs": 5, "canopy_layers": 4, "leaf_density": 0.5},
    "spirit_candelabra": {"form": "spiral",   "limbs": 4, "canopy_layers": 3, "leaf_density": 0.45},
    "world_tree":        {"form": "straight", "limbs": 6, "canopy_layers": 3, "leaf_density": 0.6,
                          "trunk": 5},
    "dead_snag":         {"form": "curved",   "limbs": 5, "canopy_layers": 1, "leaf_density": 0.1,
                          "no_foliage": True},
    # 材质系新卡(同骨架换树皮树叶, 零成本扩多样性 — 2026-08-07 species 扩充)
    "cherry_blossom":    {"form": "curved",   "limbs": 4, "canopy_layers": 2, "leaf_density": 0.7,
                          "species": "cherry", "crown": "blob"},
    "birch_grove":       {"form": "straight", "limbs": 4, "canopy_layers": 2, "leaf_density": 0.55,
                          "species": "birch"},
    "mangrove_swamp":    {"form": "straight", "limbs": 5, "canopy_layers": 2, "leaf_density": 0.6,
                          "species": "mangrove", "crown": "blob"},
    "pale_oak_garden":   {"form": "straight", "limbs": 5, "canopy_layers": 3, "leaf_density": 0.5,
                          "species": "pale_oak"},
    "fluffy_crown":      {"form": "straight", "limbs": 5, "canopy_layers": 3, "leaf_density": 0.8,
                          "crown": "blob"},
    # 幻想地标系(2026-08-12 用户参考图 bilibili 展示树蒸馏): 矮胖撑伞比例
    # (ASPECT 0.7-1.3, 冠幅可大于身高)+大叶团+弯幅x2+冠底下压+基座巨化+
    # 粗干双材质纵纹。真实系卡一行不动。decor 另传。
    "fantasy_sakura":    {"form": "curved",   "limbs": 5, "canopy_layers": 3, "leaf_density": 0.8,
                          "species": "cherry", "crown": "blob", "fantasy": 1, "tuft_scale": 1.15},
    "fantasy_world":     {"form": "straight", "limbs": 6, "canopy_layers": 3, "leaf_density": 0.85,
                          "crown": "blob", "fantasy": 1, "trunk": 10, "roots": "flare"},
    "fantasy_oak":       {"form": "curved",   "limbs": 5, "canopy_layers": 3, "leaf_density": 0.75,
                          "crown": "blob", "fantasy": 1, "roots": "flare"},
    "fantasy_spirit":    {"form": "spiral",   "limbs": 4, "canopy_layers": 3, "leaf_density": 0.6,
                          "species": "pale_oak", "crown": "layers", "fantasy": 1},
}
DIRS8 = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
STEP = 1.0                                # 骨架步进(格)
LOG_TIPS = 3                              # fence 梢阈值(不随体量变)
MAX_NODES = 60000                         # 骨架节点安全上限


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
        self.log, self.leaf, self.fence, self.slab, self.stripped = SPECIES[p["species"]]
        self.rng = random.Random(p["seed"])
        self.seed = int(p["seed"])
        self.wood, self.leaves = {}, set()
        h, r = p["height"], p["canopy_radius"]
        self.ry = max(2, min(rhu(r * 0.6), (h - 3) // 2))
        if p["fantasy"]:
            # 幻想档: 宽幅矮冠(ry<=0.45r) + 冠底≈0.3h(人站伞下但干可读)
            self.ry = max(2, min(self.ry, rhu(r * 0.45), (h * 5) // 16))
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
            if self.p["fantasy"]:
                R = min(3.5, R * 1.5)                 # 幻想档扭得更狠
            w = self.curve_freq * 1.6
            return (ramp * R * math.sin(yy * w + self.curve_phase),
                    ramp * R * math.cos(yy * w + self.curve_phase))
        if f == "curved":
            A = min(6.0, max(2.5, self.p["height"] * 0.05))   # 弯幅随树高(实测: 固定小幅=看不见弯)
            if self.p["fantasy"]:
                A = min(10.0, max(4.0, self.p["height"] * 0.1))   # 幻想档弯幅x2
            return (ramp * A * math.sin(yy * self.curve_freq + self.curve_phase),
                    ramp * A * math.sin(yy * self.curve_freq * 0.7 + self.curve_phase * 1.3))
        return 0.0, 0.0

    def _trunk_bias(self, x, y, z):
        """每步水平偏向 = 偏移曲线差分(偏移有界, 干绕轴而不 wander —
        旧版直接积分 sin 偏向, 螺旋干中段漂出冠幅读成悬空裸枝)。
        leaning=生长点吸引(ez-tree force 机制: 远处一点持续拉弯, 强度随
        高度增 — 粗处抗弯细处弯, "被风推着弯"的迎客松式风骨)。"""
        f = self.p["form"]
        if f == "leaning":
            h = max(1.0, self.p["height"])
            ax, az = math.cos(self.lean_az) * 3 * h, math.sin(self.lean_az) * 3 * h
            dx, dz = ax - x, az - z
            dist = max(1.0, math.sqrt(dx * dx + dz * dz))
            strength = 0.05 + 0.40 * (y / h)             # 基部近直, 梢部大弯
            bx, bz = dx / dist * strength, dz / dist * strength
            return bx + self.rng.uniform(-0.04, 0.04), bz + self.rng.uniform(-0.04, 0.04)
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
            bx, bz = self._trunk_bias(lx, ly, lz)
            ln = math.sqrt(bx * bx + 1.0 + bz * bz)
            self._add(lead, (lx + bx / ln * STEP, ly + STEP / ln, lz + bz / ln * STEP))
            self.trunk_ids.append(len(self.nodes) - 1)
        # ---- phase 2: 显性主枝(先平展再上扬样条; 拓扑随叶形分形 —
        # 实测"六形一味": 云片=起叉高度聚成离散层档, 伞形=高位单点近水平
        # 共点射出, 雾团=侧枝加密; 一套主枝撒所有叶形=全塌成小团)
        n_limbs = int(self.p["limbs"]) or self.rng.randint(3, 5)
        n_limbs = max(3, min(6, n_limbs))
        crown_mode = self.p["crown"]
        tiers = int(self.p["canopy_layers"]) if crown_mode == "layers" else 1
        r = self.p["canopy_radius"]
        az0 = self.rng.uniform(0, 2 * math.pi)
        for i in range(n_limbs):
            # 起叉高度: 0.35-0.55 树高(形态规律: 低位起叉才有巨木感),
            # 映射到顶梢干链上最近的节点
            if crown_mode == "umbrella":
                # 伞形: 全部主枝从 0.7-0.8h 同一节点共点射出
                h_start = h * (0.75 + self.rng.uniform(-0.02, 0.02))
            elif crown_mode == "layers" and tiers >= 2:
                # 云片: 起叉高度聚成 tiers 个离散层档(0.5h→0.8h), 层间留缝
                tier_i = i % tiers
                h_start = h * (0.5 + 0.3 * (tier_i / max(1, tiers - 1)) +
                               self.rng.uniform(-0.02, 0.02))
            else:
                h_start = h * (0.35 + 0.2 * (i / max(1, n_limbs - 1)) + self.rng.uniform(-0.03, 0.03))
            start_id = min(self.trunk_ids,
                           key=lambda nid: abs(self.nodes[nid][1] - h_start))
            if self.p["form"] == "leaning":
                # 偏锋主枝 = 顺风扇(lean_az ±1.2 rad 内展开), 背风面无枝 —
                # 探头剪影(F04: 倾斜侧枝长背侧裸);整环分布+冠心偏移=逆风裸枝翻车
                az = self.lean_az + ((i + self.rng.uniform(-0.3, 0.3)) /
                                     max(1, n_limbs - 1) - 0.5) * 2.4
            else:
                az = az0 + i * (2 * math.pi / n_limbs) + self.rng.uniform(-0.2, 0.2)
            if crown_mode == "umbrella":
                el = self.rng.uniform(0.05, 0.18)       # 近水平射出(伞面)
                tilt = self.rng.uniform(0.02, 0.04)
                el_cap = self.rng.uniform(0.3, 0.45)    # 顶多微扬(伞沿不下扣)
            else:
                el = self.rng.uniform(0.25, 0.45)       # 起角抬高(低角=蜘蛛腿)
                tilt = self.rng.uniform(0.04, 0.08)     # 上扬段每步仰角抬升
                el_cap = self.rng.uniform(0.8, 1.05)
            # 枝长收敛在冠幅内; 幻想宽幅档主枝更长(宽幅>高度的前提是真枝伸出去,
            # 不是叶团甩出去 — 实测"宽幅全靠叶团硬凑"翻车)
            lo, hi2 = (0.7, 0.9) if self.p["fantasy"] else (0.5, 0.7)
            steps = max(3, int(r * self.rng.uniform(lo, hi2)))
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
        # ---- phase 2.5: 二级/三级分枝(全树通用 — 实测"树没有分枝, 全是一条")
        self._sub_branches()
        # ---- phase 3: 树冠内容
        self.pre_fan = len(self.nodes)              # 主干+主枝阶段节点界
        self.spoke_thick = set()                    # 大盘辐条根(2 宽)
        self.spoke_chains = []                      # 每条辐条的节点链(叶簇用)
        self.discs = []
        if crown_mode == "blob" and not self.p["fantasy"]:
            # blob: 球面辐条(球形是枝条长出来的, 不是叶壳)
            self._blob_spokes()
        # layers/umbrella/mist/幻想宽幅: 无盘无辐条 — 真分枝骨架扛全部叶形

    def _sub_branches(self):
        """二级/三级分枝(phase 2.5, 全树通用): 每根主枝外侧 40-90% 段长 2-4
        根侧枝(与母枝走向夹角 0.3-0.6 rad, 长 0.35-0.55×母枝), 每根侧枝梢
        再分 1-2 根小枝(3-6 格)。产出 self.terminals=全部枝梢节点(叶簇锚点
        — 叶必须坐在枝梢上, 不是沿链撒点硬凑)。侧枝抬高 desc 计数, 主枝
        自动加粗(calibre), 分层由主枝起叉高度差天然形成。"""
        rng = self.rng
        trunk_set = set(self.trunk_ids)
        self.terminals = []
        self.sub_chains = []                            # 侧枝链(mist 雾团用)

        def rot(v, ang):
            """向量 v 绕随机垂直轴转 ang 弧度(确定性 rng)。"""
            ux, uy, uz = rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)
            un = math.sqrt(ux * ux + uy * uy + uz * uz) or 1.0
            ux, uy, uz = ux / un, uy / un, uz / un
            # perp = normalize(cross(v, u))
            px = v[1] * uz - v[2] * uy
            py = v[2] * ux - v[0] * uz
            pz = v[0] * uy - v[1] * ux
            pn = math.sqrt(px * px + py * py + pz * pz)
            if pn < 1e-6:
                return v
            px, py, pz = px / pn, py / pn, pz / pn
            c, s = math.cos(ang), math.sin(ang)
            return (v[0] * c + px * s, v[1] * c + py * s, v[2] * c + pz * s)

        for li, ldir, steps in list(self.limb_ends):
            chain = []
            cur = li
            while cur not in trunk_set and cur > 0:
                chain.append(cur)
                cur = self.parent[cur]
            chain.reverse()
            if len(chain) < 4:
                self.terminals.append(li)
                continue
            n_sub = rng.randint(2, 3 if steps < 14 else 4)
            if self.p["crown"] == "mist":
                n_sub = rng.randint(3, 5)               # 雾团: 侧枝加密(小枝扛簇)
            for si in range(n_sub):
                t = 0.4 + 0.5 * (si / max(1, n_sub - 1)) + rng.uniform(-0.06, 0.06)
                anchor = chain[min(len(chain) - 1, max(0, int(t * (len(chain) - 1))))]
                pa = self.parent[anchor]
                ax, ay, az = self.nodes[anchor]
                bx, by, bz = self.nodes[pa]
                vn = math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2) or 1.0
                v = ((ax - bx) / vn, (ay - by) / vn, (az - bz) / vn)
                d = rot(v, rng.uniform(0.3, 0.6))
                d = (d[0], max(d[1], -0.15), d[2])       # 侧枝不许下垂(下垂=裸枝)
                L = max(3, int(steps * rng.uniform(0.35, 0.55)))
                cur, pos = anchor, self.nodes[anchor]
                sub_chain = [cur]
                for s in range(L):
                    pos = (pos[0] + d[0] * STEP, pos[1] + d[1] * STEP, pos[2] + d[2] * STEP)
                    self._add(cur, pos)
                    cur = len(self.nodes) - 1
                    sub_chain.append(cur)
                    d = rot(d, rng.uniform(-0.06, 0.10))
                    d = (d[0], max(d[1], -0.15), d[2])
                self.terminals.append(cur)
                self.sub_chains.append(sub_chain)
                for _ in range(rng.randint(1, 2)):
                    td = rot(d, rng.uniform(0.3, 0.7))
                    L2 = rng.randint(3, 6)
                    tcur, tpos = cur, pos
                    for s in range(L2):
                        tpos = (tpos[0] + td[0] * STEP, tpos[1] + td[1] * STEP,
                                tpos[2] + td[2] * STEP)
                        self._add(tcur, tpos)
                        tcur = len(self.nodes) - 1
                        td = rot(td, rng.uniform(-0.08, 0.08))
                    self.terminals.append(tcur)
            self.terminals.append(li)               # 主枝梢也是簇点

    def _blob_spokes(self):
        """crown=blob 的骨架: 球面辐条(球形是枝条长出来的, 不是叶壳)。
        二级锚点: ~45% 辐条从主枝末端发出(干→主枝→辐条的层级可读, 球底
        看得见粗枝分叉托冠), 其余从冠心(yc 处干节点)发出; 条长沿方向打到
        球壳 v≈0.85(从锚点步进求交, 不从球心算 — 偏心锚点径长各异)。"""
        rng = self.rng
        mid = min(self.trunk_ids, key=lambda i: abs(self.nodes[i][1] - self.yc))
        r, ry = self.p["canopy_radius"], self.ry
        mx, my, mz = self.nodes[mid][0], self.yc, self.nodes[mid][2]
        anchors = [mid] + [li for li, _d, _s in self.limb_ends]
        # 幻想档辐条减半: 团块要能各自独立(花椰菜), 条太密簇全粘连成盘
        n = max(8, int(r * (0.55 if self.p["fantasy"] else 1.2)))
        az0 = rng.uniform(0, 2 * math.pi)

        def v_of(x, y, z):
            return ((x - mx) / r) ** 2 + ((y - my) / ry) ** 2 + ((z - mz) / r) ** 2

        for k in range(n):
            az = az0 + k * (2 * math.pi / n) + rng.uniform(-0.25, 0.25)
            el = rng.uniform(-0.35, 1.1)
            ex, ey, ez = math.cos(az) * math.cos(el), math.sin(el), math.sin(az) * math.cos(el)
            # 二级锚点: 部分辐条挂在主枝末端, 方向大体沿用但起点偏心
            cur = mid
            if self.limb_ends and rng.random() < 0.45:
                li, ldir, _s = self.limb_ends[rng.randrange(len(self.limb_ends))]
                cur = li
                # 从枝端出发的辐条偏向该枝原方位(枝的延续, 不乱穿)
                laz = math.atan2(ldir[2], ldir[0]) + rng.uniform(-0.9, 0.9)
                lel = rng.uniform(-0.2, 0.9)
                ex, ey, ez = math.cos(laz) * math.cos(lel), math.sin(lel), \
                             math.sin(laz) * math.cos(lel)
            pos0 = self.nodes[cur]
            # 步进求交: 沿方向打到椭球壳 v≈0.85
            t_hit, t = 2.0, 0.0
            while t < r * 1.6:
                t += 0.5
                if v_of(pos0[0] + ex * t, pos0[1] + ey * t, pos0[2] + ez * t) >= 0.85:
                    t_hit = t
                    break
            else:
                t_hit = r * 0.9
            steps = max(2, int(t_hit * rng.uniform(0.75, 0.9)))
            pos = pos0
            chain = [cur]
            for s in range(steps):
                pos = (pos[0] + ex, pos[1] + ey, pos[2] + ez)
                self._add(cur, pos)
                cur = len(self.nodes) - 1
                chain.append(cur)
                if t_hit >= 10.0 and s < steps * 0.4:
                    self.spoke_thick.add(cur)
                az += rng.uniform(-0.04, 0.04)
                el += rng.uniform(-0.03, 0.03)
                ex, ey, ez = math.cos(az) * math.cos(el), math.sin(el), math.sin(az) * math.cos(el)
            self.spoke_chains.append(chain)

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
            for ci in range(int(len(chain) * 0.25), len(chain), spacing):
                x, y, z = self.nodes[chain[ci]]
                discs.append((x, y, z, rl * 0.75, self.hl))
            x, y, z = self.nodes[li]                     # 枝端盘(略大, 外推埋尖)
            push = 0.4 * steps
            ex, ey, ez = (x + ldir[0] * push, y + ldir[1] * push, z + ldir[2] * push)
            discs.append((ex, ey, ez, rl, self.hl))
            if self.rng.random() < 0.35:                 # 卫星小团(破轮廓重复感)
                sat_az = self.rng.uniform(0, 2 * math.pi)
                discs.append((ex + math.cos(sat_az) * rl * 0.9,
                              ey + self.rng.uniform(-1.0, 1.5),
                              ez + math.sin(sat_az) * rl * 0.9,
                              rl * self.rng.uniform(0.35, 0.5), self.hl))
        if layers >= 2:
            tx, _, tz = self.nodes[self.trunk_ids[-1]]   # 顶梢干尖水平位
            discs.append((tx, self.p["height"] - self.hl, tz, r * 0.55, self.hl))
            # 冠区干身盘链: 沿顶梢干 0.6/0.72/0.84 树高各一盘 — 实测裸干段
            # (主枝盘顶到核心盘底之间 15-20 格无叶, 读成悬空光杆);叶裹上段干
            h = self.p["height"]
            for frac in (0.6, 0.72, 0.84):
                ty = h * frac
                if ty >= h - self.hl * 2:
                    continue                             # 顶盘覆盖区不重复
                nid = min(self.trunk_ids, key=lambda i: abs(self.nodes[i][1] - ty))
                x, _, z = self.nodes[nid]
                discs.append((x, ty, z, r * 0.42, self.hl))
        # 核心盘: 主枝分叉区(yc 高度, 跟随该处干位) — 治小树/疏树冠心裸木感
        mid_id = min(self.trunk_ids, key=lambda nid: abs(self.nodes[nid][1] - self.yc))
        mx, _, mz = self.nodes[mid_id]
        discs.append((mx, self.yc, mz, max(2.5, r * 0.5), self.hl))
        # 逐盘剪影抖动(治"每棵树都一样": 同 preset 同 seed 也不该盘盘同形);
        # leaning 冠心偏向(F04 卡旧账: 冠心偏向倾斜方向 0.35 冠幅, 探头剪影)
        if self.p["form"] == "leaning":
            off = r * 0.35
            lox, loz = math.cos(self.lean_az) * off, math.sin(self.lean_az) * off
        else:
            lox = loz = 0.0
        return [(cx + lox + self.rng.uniform(-1.0, 1.0), cy + self.rng.uniform(-0.5, 0.5),
                 cz + loz + self.rng.uniform(-1.0, 1.0),
                 dr * self.rng.uniform(0.8, 1.25), dh * self.rng.uniform(0.75, 1.4))
                for (cx, cy, cz, dr, dh) in discs]

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
            bridge = [best]
            while len(self.nodes) < MAX_NODES:        # 锚枝接到盘心
                x, y, z = self.nodes[best]
                vx, vy, vz = cx - x, cy - y, cz - z
                d = math.sqrt(vx * vx + vy * vy + vz * vz)
                if d <= 0.5:
                    break
                self._add(best, (x + vx / d * STEP, y + vy / d * STEP,
                                 z + vz / d * STEP))
                best = len(self.nodes) - 1
                bridge.append(best)
            if len(bridge) >= 3:
                # 桥本身也入叶簇链(实测: 冠心偏移/枝端外推把盘顶离锚点,
                # 长桥无簇=一条裸梁)
                self.spoke_chains.append(bridge)
            center_id = best
            n_spokes = 5 + rng.randrange(3) + (3 if bare else 0)
            el_max = min(0.55, math.atan2(dh * 0.9, dr * 0.8 + 0.001))
            az0 = rng.uniform(0, 2 * math.pi)
            for k in range(n_spokes):
                az = az0 + k * (2 * math.pi / n_spokes) + rng.uniform(-0.25, 0.25)
                el = rng.uniform(-0.3, 0.6) if bare else rng.uniform(0.1, el_max)
                steps = max(2, int(dr * rng.uniform(0.6, 0.8)))   # 辐条止于壳内(不捅出叶壳)
                cur = center_id
                pos = self.nodes[cur]
                chain = [cur]
                for s in range(steps):
                    dx = math.cos(az) * math.cos(el)
                    dy = math.sin(el)
                    dz = math.sin(az) * math.cos(el)
                    pos = (pos[0] + dx * STEP, pos[1] + dy * STEP, pos[2] + dz * STEP)
                    self._add(cur, pos)
                    cur = len(self.nodes) - 1
                    chain.append(cur)
                    if dr >= 10.0 and s < steps * 0.4:
                        self.spoke_thick.add(cur)
                    az += rng.uniform(-0.06, 0.06)
                    el = min(el_max, max(0.05,          # 钳在盘内: 下垂辐条出盘=裸枝
                             el + rng.uniform(-0.03, 0.04)))
                self.spoke_chains.append(chain)

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

    def _trunk_size(self, frac):
        """干柱截面边长(沿顶梢位置 frac∈[0,1]): 基部板根/基座区(frac0)足尺,
        之上全程线性收分到 tip=round(ts*0.4) — 连续圆台, 收分要看得见
        (实测反馈"压根没有减小直径": 旧 tip=ts-2 太保守)。缩径层铺半砖。"""
        tip = max(1, int(round(self.ts * 0.4)))
        span = max(1, len(self.trunk_ids))
        frac0 = min(0.12, (self.ts + 2.0) / span)        # 基座足尺区(接板根)
        if not self.p["taper"] or frac <= frac0:
            return self.ts
        return max(tip, int(round(self.ts - (self.ts - tip) * (frac - frac0) / (1 - frac0))))

    def _bole_section(self, cx, cz, y, size):
        """以 (cx,cz) 浮点为中心的 size×size 水平截面, size>=3 削角成圆
        (近似圆截面 — 实测反馈"所有树干都是正方形"; 3x3→十字5, 4x4→12,
        5x5→21, >=8 削两层角成八边形感)。返回 (x,z) 集合。"""
        half = (size - 1) / 2.0
        corner_depth = 0 if size < 3 else (1 if size < 8 else 2)
        cells = set()
        for ix in range(size):
            for iz in range(size):
                if corner_depth and \
                        (ix < corner_depth or ix >= size - corner_depth) and \
                        (iz < corner_depth or iz >= size - corner_depth):
                    continue                            # 削角成圆
                x, z = rhu(cx - half) + ix, rhu(cz - half) + iz
                # 幻想档粗干双材质纵纹: 同列位置逐层一致=纵向条纹
                # (展示树树皮观感核心 — 单材质粗干是"水泥柱"翻车根源)
                bark = self.log
                if self.p["fantasy"] and size >= 6 and (ix + iz) % 3 == 0:
                    bark = self.stripped
                self.put_wood(x, y, z, "%s[axis=y]" % bark)
                cells.add((x, z))
        return cells

    def rasterize(self):
        desc, clear_h = self.desc, self.clear_h
        # 顶梢干: 沿骨架链逐格截面(可弯/斜); 全程圆台收分(_trunk_size:
        # 基座足尺区以上线性缩到 tip); 每档缩径层在旧截面外环铺 bottom 半砖,
        # 0.5 格台阶过渡取代 1 格突变(实测"粗细突变"反馈)
        trunk_set = set(self.trunk_ids)
        span = max(1, len(self.trunk_ids))
        prev_cells, prev_size = None, None
        prev_pos, prev_yy = None, None
        for idx, nid in enumerate(self.trunk_ids):
            x, y, z = self.nodes[nid]
            yy = rhu(y)
            frac = idx / span
            size = self._trunk_size(frac)
            if self.p["roots"] == "flare" and self.p["buttress"]:
                # 钟形基座: 干基 ts+2 层内线性膨大到 ~1.7ts(温带老树立干感),
                # 削角成圆由 _bole_section 负责
                flare_h = self.ts + 2
                if self.p["fantasy"]:
                    flare_h = max(flare_h, int(self.p["height"] * 0.15))  # 基座巨化
                if yy < flare_h:
                    size = min(self.ts + 4, size + int(round(
                        (1 - yy / flare_h) * self.ts * 0.7)))
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

    def _twist_ridge(self):
        """盘旋棱脊(spiral 干专属): 沿干身绕轴每格一条棱线, pitch=ts*3+8 层
        一圈, 从截面表面贴出外缘(vline 保底连通)。中心线螺旋半径必须小
        (大了干漂),"盘旋"靠棱脊读 — 树皮扭转条纹是 MC 经典手法(端面纹理)。
        粗干(ts>=4)双棱对生。"""
        span = max(1, len(self.trunk_ids))
        pitch = self.ts * 3 + 8
        for idx, nid in enumerate(self.trunk_ids):
            frac = idx / span
            if frac > 0.7:
                break                                        # 冠区不刻(叶裹)
            x, y, z = self.nodes[nid]
            yy = rhu(y)
            half = self._trunk_size(frac) / 2.0              # 棱贴当层截面外缘
            phases = (0.0,) if self.ts < 4 else (0.0, math.pi)
            for ph in phases:
                ang = yy * (2 * math.pi / pitch) + self.curve_phase + ph
                dx, dz = math.cos(ang), math.sin(ang)
                axis = "x" if abs(dx) >= abs(dz) else "z"
                sx, sz = rhu(x + dx * half), rhu(z + dz * half)
                rx, rz = rhu(x + dx * (half + 0.5)), rhu(z + dz * (half + 0.5))
                for cell in vline((sx, yy, sz), (rx, yy, rz)):
                    self.put_wood(*cell, "%s[axis=%s]" % (self.log, axis))

    def _crawl_roots(self, flare=False):
        """贴地爬根(默认根式): 每条根 = 干基表面出发的样条 — 先高位拱出
        (hump), 再逐级下扎, 末端钻进地表 1-2 格(半埋); 长度/方向不均布
        (修长根+短根混编, 方位抖动), 近干段随体量加宽。flare=钟形基座款:
        根更短更矮(基座膨大由 rasterize 干基加粗负责)。治旧板根鳍
        "4-6 条等长直鳍绕圈"的符号感 — 真根是爬出来的不是贴上去的。"""
        rng = self.rng
        ts_eff = min(self.ts, 8)
        n = min(10, 5 + ts_eff // 2 + rng.randrange(3))
        az0 = rng.uniform(0, 2 * math.pi)
        bcx, bcz = self.c, self.c                      # 干基中心(local)
        half = (self.ts - 1) / 2.0
        for k in range(n):
            az = az0 + k * (2 * math.pi / n) + rng.uniform(-0.35, 0.35)
            dx, dz = math.cos(az), math.sin(az)
            L = ts_eff + 2 + rng.randrange(4)          # 基础长
            if self.p["fantasy"]:
                L = int(L * 2.5)                       # 幻想档根巨化(根拱下能钻人)
            if rng.random() < 0.4:                     # 长短混编(破均布感)
                L = max(2, int(L * 0.6))
            if flare:
                L = max(2, int(L * 0.6))
            if self.p["form"] == "leaning":
                # 根部抓地补偿(风骨): 倾斜反方向的根加长锚定, 顺风向缩短
                dot = dx * math.cos(self.lean_az) + dz * math.sin(self.lean_az)
                L = max(2, int(round(L * (1.0 - 0.5 * dot))))
            # y 轮廓: 出干处拱高 hump(随干径), 每 2 步降 1 格直到入土
            hump = max(1, min(3, ts_eff // 2))
            if self.p["fantasy"]:
                hump = max(2, min(5, ts_eff // 2 + 1))  # 幻想档拱高(根下成门洞)
            if flare:
                hump = 1
            px, pz = bcx + dx * half, bcz + dz * half  # 干基表面起点
            prev_top = None
            wide = ts_eff >= 4                          # 粗干近段双宽
            for t in range(L):
                cx, cz = rhu(px + dx * t), rhu(pz + dz * t)
                # 幻想档降速减半(每 3 步降 1 格): 长根才能爬得远
                sink = 3 if self.p["fantasy"] else 2
                y_top = hump - max(0, (t - 1) // sink)    # 第 0/1 步保持拱高
                axis = "x" if abs(dx) >= abs(dz) else "z"
                if y_top >= 0:
                    for y in range(y_top + 1):         # 地表实心柱
                        self.put_wood(cx, y, cz, "%s[axis=%s]" % (
                            self.log, axis if y == y_top else "y"))
                else:                                   # 入土段(半埋收梢)
                    self.put_wood(cx, -1, cz, "%s[axis=y]" % self.log)
                    if t + 1 < L:                       # 再送一格入土尾
                        self.put_wood(rhu(px + dx * (t + 1)), -1,
                                      rhu(pz + dz * (t + 1)),
                                      "%s[axis=y]" % self.log)
                    break
                if prev_top is not None:                # 连通兜底
                    for cell in vline(prev_top, (cx, y_top, cz)):
                        self.put_wood(*cell, "%s[axis=%s]" % (self.log, axis))
                if wide and t < L * 0.4:                # 近干段侧向加宽
                    bx, bz = (-dz, dx) if abs(dx) >= abs(dz) else (dz, -dx)
                    self.put_wood(rhu(cx + bx), y_top, rhu(cz + bz),
                                  "%s[axis=%s]" % (self.log, axis))
                prev_top = (cx, y_top, cz)

    def buttress(self):
        """板根: 4-6 stepped fins; 长度/高度随干径缩放(封顶 8, 巨干靠粗不靠长)。"""
        n = 4 + self.rng.randrange(3)
        start = self.rng.randrange(8)
        dirs, seen = [], set()
        for k in range(n):
            d = DIRS8[(start + rhu(k * 8.0 / n)) % 8]
            if d not in seen:
                seen.add(d)
                dirs.append(d)
        ts_eff = min(self.ts, 8)
        length, c = ts_eff + 2, self.c
        base = self.nodes[min(1, len(self.nodes) - 1)]
        bcx, bcz = base[0], base[2]
        for ddx, ddz in dirs:
            px = rhu(bcx + ddx * c)
            pz = rhu(bcz + ddz * c)
            axis = "x" if abs(ddx) >= abs(ddz) else "z"
            fin_len = length
            if self.p["form"] == "leaning":
                # 根部抓地补偿(风骨): 倾斜反方向的板根加长锚定, 顺风向缩短
                dot = ddx * math.cos(self.lean_az) + ddz * math.sin(self.lean_az)
                fin_len = max(1, int(round(length * (1.0 - 0.75 * dot))))
            for k in range(1, fin_len + 1):
                hgt = max(1, ts_eff + 1 - k)        # 递减鳍高(封顶 9)
                cols = [(px + k * ddx, pz + k * ddz)]
                if ddx and ddz:                         # diagonal fin: L-corner column
                    cols.append((px + k * ddx, pz + (k - 1) * ddz))
                for cx, cz in cols:
                    for y in range(hgt):
                        self.put_wood(cx, y, cz, "%s[axis=%s]" % (
                            self.log, axis if y == hgt - 1 else "y"))

    # ----------------------------------------------------------- foliage --
    def _tuft(self, cx, cy, cz, r, carve, flat=0.8):
        """单个叶簇: 带镂空的小椭球(carve 用 seeded hash, 确定性);
        flat=y 向压扁度(layers 云片 0.5 扁, blob 球团 0.9 近圆)。
        簇心记 tuft_centers(美学约束扇区覆盖统计用)。"""
        if hasattr(self, "tuft_centers"):
            self.tuft_centers.append((cx, cy, cz))
        ry = max(1, int(round(r * flat)))
        ri = max(1, int(round(r)))
        for dy in range(-ry, ry + 1):
            for dx in range(-ri, ri + 1):
                for dz in range(-ri, ri + 1):
                    v = (dx / r) ** 2 + (dy / max(0.6, r * flat)) ** 2 + (dz / r) ** 2
                    if v > 1.0:
                        continue
                    if v > 0.5 and h3(cx + dx, cy + dy, cz + dz, self.seed) < carve:
                        continue                    # 镂空
                    cell = (cx + dx, cy + dy, cz + dz)
                    if cell not in self.wood:
                        self.leaves.add(cell)

    def foliage(self):
        """叶形四式(crown 参数, 骨架拓扑已在 grow 分形):
        - layers 云片层盘: 主枝起叉高度聚成离散层档, 簇沿枝外侧段成盘
          (flat 0.5), 层间留缝;
        - umbrella 伞形平顶: 高位共点近水平枝, 整枝盘面簇(flat 0.4),
          枝梢簇下垂 1-2 格成伞沿;
        - mist 蓬松雾团: 侧枝加密, 小簇(0.13r)沿全部枝链高方差叠放,
          无层无壳;
        - blob 圆整球形: 球面辐条+薄壳(v6, 真实系) / 幻想宽幅=枝梢簇并集。
        共享: 顶穹团(治平顶/秃顶) + 边界 2 轮飞叶。leaf_density 控簇距/镂空。"""
        rng = self.rng
        ld = self.p["leaf_density"]
        if bool(self.p.get("no_foliage")):
            return
        r = self.p["canopy_radius"]
        crown_mode = self.p["crown"]
        base_r = max(1.6, r * 0.22 * self.p["tuft_scale"])
        carve = 0.26 - 0.16 * ld
        flat = {"blob": 0.9, "layers": 0.5, "umbrella": 0.4,
                "mist": 0.75}.get(crown_mode, 0.65)
        if crown_mode == "mist":
            base_r = max(1.5, r * 0.17 * self.p["tuft_scale"])
        trunk_set = set(self.trunk_ids)
        tip = self.nodes[self.trunk_ids[-1]]
        h = self.p["height"]
        self.tuft_centers = []                          # 美学约束扇区统计用

        gap = base_r * (1.9 - 0.8 * ld) + 0.4   # 簇距随簇径缩放(小树也连续成冠)
        # 幻想档大叶团: 簇径上限按冠幅放开(0.3r, 封顶 7), 簇距拉稀 —
        # 少量大团+团间沟壑留白 = 展示树"花椰菜"剪影(参考图核心观感)
        tcap, ecap = 4.5, 5.0
        if self.p["fantasy"]:
            tcap = min(6.0, max(4.5, r * 0.3))
            ecap = tcap + 0.5
            gap *= 1.6                      # 簇距(幻想主靠枝梢簇, 沿链簇是配角)

        def tufts_along(chain, start_frac):
            L = len(chain)
            if L < 2:
                return
            n = max(2, int((L * (1 - start_frac)) / gap + 0.5))   # 每链至少 2 簇
            for k in range(n):
                frac = start_frac + (1 - start_frac) * (k + rng.uniform(-0.35, 0.35)) / n
                frac = min(1.0, max(start_frac, frac))
                nid = chain[int(frac * (L - 1))]
                x, y, z = self.nodes[nid]
                tr = min(base_r * rng.uniform(0.7, 1.3), tcap)   # 大冠封顶防块数爆炸
                self._tuft(round(x), round(y), round(z), tr, carve, flat)
            x, y, z = self.nodes[chain[-1]]      # 梢端大团(云片焦点, 半径封顶)
            self._tuft(round(x), round(y), round(z),
                       min(base_r * rng.uniform(1.0, 1.3), ecap), carve, flat)

        limb_chains = []
        for li, _ldir, _steps in self.limb_ends:
            chain = []
            cur = li
            while cur not in trunk_set and cur > 0:
                chain.append(cur)
                cur = self.parent[cur]
            chain.reverse()
            limb_chains.append(chain)

        if crown_mode == "blob" and self.p["fantasy"]:
            # 幻想宽幅: 叶簇只坐枝梢(terminals=主枝/侧枝/小枝梢) —
            # 实测"发胖叶团是硬凑的, 不长在枝上, 还镂空": 无壳无辐条,
            # 簇径大但 carve 正常, 分层=主枝起叉高度差天然形成
            for tid in self.terminals:
                x, y, z = self.nodes[tid]
                tr = min(base_r * rng.uniform(0.9, 1.4), tcap)
                self._tuft(round(x), round(y), round(z), tr, carve, flat)
            # 冠心团: 枝梢簇全在外圈, 冠中心上空会漏干(实测"心形缺口")
            mid = min(self.trunk_ids, key=lambda i: abs(self.nodes[i][1] - self.yc))
            mx, my, mz = self.nodes[mid]
            self._tuft(round(mx), round(my + self.ry * 0.7), round(mz),
                       min(base_r * 1.3, ecap), carve, flat)
            for chain in limb_chains:               # 主枝中段稀疏补簇(遮骨干)
                tufts_along(chain, 0.6)
        elif crown_mode == "blob":
            for chain in self.spoke_chains:         # 球面辐条: 外侧 35% 起簇
                tufts_along(chain, 0.35)            # (球形=枝条长成, 簇随枝走)
            for chain in limb_chains:               # 主枝下部也别裸(球底收口)
                tufts_along(chain, 0.45)
            self._foliage_blob(r, carve * 1.2)      # 壳层封口(更透: 簇团已扛纹理)
        elif crown_mode == "umbrella":
            # 伞形平顶: 整枝盘面(近水平枝从 25% 起簇), 梢簇下垂成伞沿,
            # 冠心一张顶盘收口
            for chain in limb_chains:
                tufts_along(chain, 0.25)
            for tid in self.terminals:
                x, y, z = self.nodes[tid]
                tr = min(base_r * rng.uniform(0.8, 1.2), tcap)
                self._tuft(round(x), round(y) - rng.randint(1, 2), round(z),
                           tr, carve, flat)
            mid = min(self.trunk_ids, key=lambda i: abs(self.nodes[i][1] - self.yc))
            mx, my, mz = self.nodes[mid]
            self._tuft(round(mx), round(my + self.ry * 0.4), round(mz),
                       min(base_r * 1.4, ecap), carve, flat)
        elif crown_mode == "mist":
            # 蓬松雾团: 全部枝链(主枝+侧枝)小簇高方差叠放 — 要"雾"不要"稀"
            # (实测 0.3 起簇+标准簇距=半枯), 起簇更早簇距更密
            gap *= 0.5
            for chain in limb_chains:
                tufts_along(chain, 0.1)
            for chain in getattr(self, "sub_chains", []):
                tufts_along(chain, 0.1)
            for tid in self.terminals:
                x, y, z = self.nodes[tid]
                self._tuft(round(x), round(y), round(z),
                           base_r * rng.uniform(0.7, 1.3), carve, flat)
        else:
            # layers 云片层盘: 簇沿主枝+侧枝外侧段成盘(flat 0.5 压扁),
            # 层档=骨架起叉高度, 层间缝=层档间距; 侧枝梢补同层小盘
            # (实测只在主枝撒簇=秃枝小树, 侧枝链必须入盘)
            for chain in limb_chains:
                tufts_along(chain, 0.35)
            for chain in getattr(self, "sub_chains", []):
                tufts_along(chain, 0.3)
            for tid in self.terminals:
                x, y, z = self.nodes[tid]
                tr = min(base_r * rng.uniform(0.7, 1.1), tcap)
                self._tuft(round(x), round(y), round(z), tr, carve, flat)
        # 顶穹团: 树尖上方一个半球团(治平顶/秃顶 — 树冠顶部必须是穹面不是平台)
        self._tuft(rhu(tip[0]), int(h) - 1, rhu(tip[2]),
                   min(max(2.0, base_r * 1.2), ecap), carve * 0.6, flat)
        # 边界飞叶: 叶格邻空处按概率向外补 1 格(连 2 轮 → 1-2 格毛边)
        for fuzz_round, prob in ((0.10, 12345), (0.045, 54321)):
            edge = []
            for (x, y, z) in self.leaves:
                for dx, dy, dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                    c = (x + dx, y + dy, z + dz)
                    if c not in self.leaves and c not in self.wood and \
                            h3(c[0], c[1], c[2], self.seed ^ prob) < fuzz_round:
                        edge.append(c)
            for c in edge:
                self.leaves.add(c)

    def _foliage_blob(self, r, carve):
        """crown=blob 圆整球形冠的壳层: 只铺 v∈[0.85,1] 的薄皮(带镂空,
        外缘更稀) — 主体由辐条链上的 tuft 簇扛(簇随枝走), 壳层只填簇间
        缝隙让剪影读成球, 不再整球糊实(旧 v∈[0.5,1] 实心壳抹掉一切枝纹
        = "棒棒糖"翻车的根源)。"""
        mid = min(self.trunk_ids, key=lambda i: abs(self.nodes[i][1] - self.yc))
        mx, _, mz = self.nodes[mid]
        dr, dh = r * 0.8, max(2.0, self.ry * 0.8)
        cy = self.yc + self.ry * 0.1
        # 幻想档: 壳只留 v∈[0.92,1] 极薄皮+更透 — 壳糊平=花椰菜变蘑菇盘
        # (实测: 大簇+满壳=团块全粘连, 沟壑消失, 干被吞)
        v_lo = 0.92 if self.p["fantasy"] else 0.85
        if self.p["fantasy"]:
            carve = min(0.55, carve * 1.6)
        R, H = math.ceil(dr), math.ceil(dh)
        for dx in range(-R, R + 1):
            for dz in range(-R, R + 1):
                for dy in range(-H, H + 1):
                    v = (dx / dr) ** 2 + (dy / dh) ** 2 + (dz / dr) ** 2
                    if not v_lo <= v <= 1.0:
                        continue                    # 只要薄皮
                    cell = (rhu(mx) + dx, rhu(cy) + dy, rhu(mz) + dz)
                    c = carve * (0.6 + 0.5 * v)     # 外缘更透(毛糙球面)
                    if h3(cell[0], cell[1], cell[2], self.seed) < c:
                        continue
                    if cell not in self.wood:
                        self.leaves.add(cell)

    # ------------------------------------------------------------ decor --
    def _decorate(self):
        """装饰后处理(foliage 之后, prune 之前): 展示树的"戏"层。
        lights=冠内光点(叶团深处的叶换 shroomlight, 透光); lanterns=辐条
        外段挂 chain+lantern 灯笼串; vines=冠底垂藤(叶链下垂 3-8 渐断)。
        装饰块记 self.decor_blocks, emit 单独输出(叶不覆盖)。"""
        modes = set(m.strip() for m in str(self.p["decor"]).lower().split(",") if m.strip())
        if not modes or "none" in modes or not self.leaves:
            return
        if "all" in modes:
            modes = {"lights", "lanterns", "vines"}
        rng = self.rng
        r = self.p["canopy_radius"]
        self.decor_blocks = {}
        leaves_list = sorted(self.leaves)
        adj6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
        if "lights" in modes:
            # 埋在叶团里(>=4 面被叶包围)才透光自然, 数量随冠幅
            cands = [c for c in leaves_list if sum(
                (c[0] + dx, c[1] + dy, c[2] + dz) in self.leaves
                for dx, dy, dz in adj6) >= 4]
            rng.shuffle(cands)
            for c in cands[:max(2, r // 2)]:
                self.leaves.discard(c)
                self.decor_blocks[c] = "minecraft:shroomlight"
        if "lanterns" in modes:
            # 辐条/主枝外段节点下方: 2-4 格链 + 挂灯; 无辐条(幻想宽幅)用枝梢
            spots = []
            for chain in self.spoke_chains:
                if len(chain) >= 3:
                    spots.append(self.nodes[chain[int(len(chain) * 0.8)]])
            if not spots:
                spots = [self.nodes[t] for t in getattr(self, "terminals", [])]
            rng.shuffle(spots)
            for (x, y, z) in spots[:2 + r // 6]:
                bx, by, bz = rhu(x), rhu(y), rhu(z)
                L = rng.randint(2, 4)
                for i in range(1, L + 1):
                    c = (bx, by - i, bz)
                    if c in self.wood:
                        break
                    self.leaves.discard(c)
                    self.decor_blocks[c] = "minecraft:chain"
                c = (bx, by - L - 1, bz)
                if c not in self.wood:
                    self.leaves.discard(c)
                    self.decor_blocks[c] = "minecraft:lantern[hanging=true]"
        if "vines" in modes:
            # 冠底外缘(下方无叶的叶格)垂叶链: 短(2-5)+带横向摆动 —
            # 实测"垂藤像冰锥": 长直杆是翻车剪影, 藤要歪歪斜斜
            bottom = [c for c in leaves_list if c[1] < self.yc and
                      (c[0], c[1] - 1, c[2]) not in self.leaves]
            rng.shuffle(bottom)
            for (x, y, z) in bottom[:r]:
                vx, vz = x, z
                for i in range(1, rng.randint(2, 5)):
                    vx += rng.choice((0, 0, 1, -1))
                    vz += rng.choice((0, 0, 1, -1))
                    c = (vx, y - i, vz)
                    if c in self.wood or c in self.decor_blocks:
                        break
                    if rng.random() < 0.85:
                        self.leaves.add(c)      # 入 leaves, emit 带 persistent
                    else:
                        break

    # ------------------------------------------------------- aesthetic --
    def _aesthetic_fix(self):
        """美学约束(aesthetic=1, foliage 之后): 树冠包络 8 扇区 x 上下 2 层
        的簇覆盖检查 — 空洞扇区在最近骨架节点徒手补一条短枝(vline 木)+
        端簇。心形/双塔/大缺口翻车全部是扇区空洞(实测), 这条直接掐死;
        自由生成(aesthetic=0)不做任何修补, 野生感保留。"""
        if not getattr(self, "tuft_centers", None):
            return
        r = self.p["canopy_radius"]
        mid = min(self.trunk_ids, key=lambda i: abs(self.nodes[i][1] - self.yc))
        mx, my, mz = self.nodes[mid][0], self.yc, self.nodes[mid][2]
        bins = {}
        for (x, y, z) in self.tuft_centers:
            sec = int((math.atan2(z - mz, x - mx) + math.pi) / (math.pi / 4)) % 8
            bins[(sec, 0 if y < my else 1)] = bins.get(
                (int((math.atan2(z - mz, x - mx) + math.pi) / (math.pi / 4)) % 8,
                 0 if y < my else 1), 0) + 1
        base_r = max(1.6, r * 0.22 * self.p["tuft_scale"])
        tcap = min(6.0, max(4.5, r * 0.3)) if self.p["fantasy"] else 4.5
        carve = 0.26 - 0.16 * self.p["leaf_density"]
        flat = {"blob": 0.9, "layers": 0.5, "umbrella": 0.4,
                "mist": 0.75}.get(self.p["crown"], 0.65)
        for sec in range(8):
            for tier in (0, 1):
                if bins.get((sec, tier), 0) >= 1:
                    continue
                ang = (sec + 0.5) * (math.pi / 4) - math.pi
                tx = mx + math.cos(ang) * r * 0.6
                ty = my + (self.ry * 0.4 if tier else -self.ry * 0.4)
                tz = mz + math.sin(ang) * r * 0.6
                best = min(range(len(self.nodes)),
                           key=lambda i: (self.nodes[i][0] - tx) ** 2 +
                                         (self.nodes[i][1] - ty) ** 2 +
                                         (self.nodes[i][2] - tz) ** 2)
                bx, by, bz = self.nodes[best]
                dx, dy, dz = tx - bx, ty - by, tz - bz
                axis = "x" if abs(dx) >= abs(dy) and abs(dx) >= abs(dz) else \
                       ("y" if abs(dy) >= abs(dz) else "z")
                cells = vline((rhu(bx), rhu(by), rhu(bz)),
                              (rhu(tx), rhu(ty), rhu(tz)))
                for c in cells[1:]:
                    self.put_wood(*c, "%s[axis=%s]" % (self.log, axis))
                self._tuft(rhu(tx), rhu(ty), rhu(tz),
                           min(base_r * 1.2, tcap), carve, flat)

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
        deco = getattr(self, "decor_blocks", {})
        # persistent=true: bare leaves decay away from logs (实机实测) — always pin.
        out += [{"x": self.ox + x, "y": self.oy + y, "z": self.oz + z,
                 "block": self.leaf + "[persistent=true]"}
                for (x, y, z) in sorted(self.leaves)
                if (x, y, z) not in self.wood and (x, y, z) not in deco]
        out += [{"x": self.ox + x, "y": self.oy + y, "z": self.oz + z, "block": b}
                for (x, y, z), b in sorted(deco.items()) if (x, y, z) not in self.wood]
        return out


def build(p):
    t = Tree(p)
    t.grow()
    t.desc, t.clear_h = t.calibre()
    t.rasterize()
    roots_mode = p["roots"] if p["buttress"] else "none"   # buttress=False 兼容旧卡
    if roots_mode == "buttress":
        t.buttress()
    elif roots_mode in ("crawl", "flare"):
        t._crawl_roots(flare=(roots_mode == "flare"))
    if p["form"] == "spiral":
        t._twist_ridge()
    if not p.get("no_foliage"):
        t.foliage()
    if p.get("aesthetic") and not p.get("no_foliage"):
        t._aesthetic_fix()
    if p.get("decor") and not p.get("no_foliage"):
        t._decorate()
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
        die("trunk must be 2-12", {"trunk": [2, 12]})
    if not 2 <= p["trunk"] <= 12:
        die("trunk must be 2-12 (ts×ts 基部干柱; 粗高 ts≈h/15, 细高 ts≈h/25, 10+ 刻纹路)", {"trunk": [2, 12]})
    if p["crown"] not in ("layers", "blob", "umbrella", "mist"):
        die("crown must be layers|blob|umbrella|mist",
            {"crown": ["layers", "blob", "umbrella", "mist"]})
    try:
        p["aesthetic"] = int(p["aesthetic"])
    except (TypeError, ValueError):
        die("aesthetic must be 0|1", {"aesthetic": 0})
    if p["aesthetic"] not in (0, 1):
        die("aesthetic must be 0|1", {"aesthetic": 0})
    if p["roots"] not in ("crawl", "flare", "buttress", "none"):
        die("roots must be crawl|flare|buttress|none",
            {"roots": ["crawl", "flare", "buttress", "none"]})
    try:
        p["tuft_scale"] = float(p["tuft_scale"])
    except (TypeError, ValueError):
        die("tuft_scale must be 0.6-1.6", {"tuft_scale": 1.0})
    if not 0.6 <= p["tuft_scale"] <= 1.6:
        die("tuft_scale must be 0.6-1.6 (叶簇径倍率)", {"tuft_scale": 1.0})
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
        p["fantasy"] = int(p["fantasy"])
    except (TypeError, ValueError):
        die("fantasy must be 0|1", {"fantasy": 0})
    if p["fantasy"] not in (0, 1):
        die("fantasy must be 0|1", {"fantasy": 0})
    bad = [m for m in str(p["decor"]).lower().split(",")
           if m.strip() and m.strip() not in ("lights", "lanterns", "vines", "all", "none")]
    if bad:
        die("decor 未知项 %s (lights|lanterns|vines|all, 逗号组合)" % bad,
            {"decor": "lights,lanterns,vines"})
    try:
        p["leaf_density"] = float(p["leaf_density"])
    except (TypeError, ValueError):
        die("leaf_density must be 0.1-1.0", {"leaf_density": 0.6})
    if not 0.1 <= p["leaf_density"] <= 1.0:
        die("leaf_density must be 0.1-1.0", {"leaf_density": 0.6})


# 高宽比护栏(height/canopy_diameter): 比例即形态语言, 越界直接拒生成 —
# 实测翻车: 55 高 52 冠幅的"煎饼树"、115 高筷子干。preset 各有合法域。
ASPECT = {
    "ancient_oak": (0.9, 2.2), "sky_pillar": (2.2, 5.0),
    "gnarled_twist": (1.0, 3.0), "leaning_river": (1.1, 2.8),
    "banyan_court": (0.7, 1.8), "umbrella_acacia": (0.4, 0.9),
    "mist_crown": (0.9, 2.2),
    "weeping_willow": (0.9, 2.2), "cloud_disc": (1.2, 3.5),
    "spirit_candelabra": (1.6, 4.5), "world_tree": (1.6, 4.5),
    "dead_snag": (1.2, 4.0),
    "cherry_blossom": (0.8, 2.2), "birch_grove": (1.6, 4.0),
    "mangrove_swamp": (0.8, 2.0), "pale_oak_garden": (1.2, 3.0),
    "fluffy_crown": (1.05, 1.35),   # 蓬松档: 冠幅直径 ≈ 0.75-0.95 × 高度(用户点单)
    # 幻想地标系: 矮胖撑伞(冠幅直径可 = 0.75-1.4 × 身高)
    "fantasy_sakura": (0.7, 1.2), "fantasy_world": (0.7, 1.3),
    "fantasy_oak": (0.7, 1.2), "fantasy_spirit": (0.9, 1.6),
}


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
    lo, hi = ASPECT.get(preset or "", (0.8, 4.5))
    ratio = p["height"] / (2.0 * p["canopy_radius"])
    if not lo <= ratio <= hi:
        die("height/canopy_diameter %.2f 越界(%s 合法域 %.1f-%.1f): 调 height/canopy_radius"
            % (ratio, preset or "自由形态", lo, hi),
            {"height": "高宽比参考: 通直 3-4 / 开展 1-1.5 / 伞盖 0.5-0.8",
             "canopy_radius": "当前 height=%d, 建议 %d-%d" % (
                 p["height"], int(p["height"] / hi / 2), max(3, int(p["height"] / lo / 2)))})
    # 干径/冠幅护栏: 树冠体量必须由主干支撑 — 实测翻车"40 格球冠压 2x2 杆
    # =棒棒糖"。ts_min=canopy_radius/4(参考: 老树干径≈冠幅 1/4-1/6)。
    ts_min = max(2, min(12, int(math.ceil(p["canopy_radius"] / 4.0))))
    if p["trunk"] < ts_min:
        die("trunk=%d 撑不住 canopy_radius=%d(干径下限 %d=冠幅半径/4): 加 trunk 或减冠"
            % (p["trunk"], p["canopy_radius"], ts_min),
            {"trunk": "当前 canopy_radius=%d, 建议 trunk %d-%d" % (
                p["canopy_radius"], ts_min, min(12, ts_min + 3))})
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
