# -*- coding: utf-8 -*-
"""
细节构件定量基准挖掘:门洞 / 窗洞 / 屋檐出挑 / 老虎窗 / 露台阳台 / 墙厚。

复用 scratch/phase9/gc_probe/layer_analyze.py 的 PNG 解析与幽灵块剔除(reconstruct),
在其输出的 layers_occ / layers_mat 上做结构特征检测。

口径要点(详见 stats_detail_elements.md):
- 地面层墙环由"前 K 层占用并集"作屏障掩膜求得(K=5),防止门洞空气缺口导致室内洪泛泄漏;
- 门洞 = 地面层墙环上的 门材质格 或 有上盖(lintel)的空气格,且内侧一格在第二层为空气(通向室内);
- 窗洞 = 墙身层墙环上的 玻璃格 或 上下皆有实心方块的空气格;
- 屋檐出挑 = 最低屋顶层(stairs 簇)相对其下两层墙身并集的外扩切比雪夫距离中位数(同 phase9 口径);
- 老虎窗 = 屋顶层内非 stairs 连通小块(2~40 格),上方 3 层内有 stairs 覆盖(低置信代理);
- 露台/阳台 = 墙身层(li>=1)悬挑于墙环外的平台:不占室内邻接、8 邻接贴墙、下层无支撑;
- 墙厚 = 墙身第 2/3 层从外轮廓四方向向内连续占用格数的众数。

用法:
  python details_mine.py --category medieval-houses --sample 20 --seed 1 --dump 3
  python details_mine.py --category modern-houses  --sample 300 --seed 42 --out modern.json
"""
import argparse
import collections
import json
import random
import sys
from collections import deque
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'phase9' / 'gc_probe'))
from layer_analyze import load_building, reconstruct, is_stairs  # noqa: E402

BARRIER_K = 5       # 地面层屏障掩膜取前 K 层并集
MAX_DOOR_W = 4      # 门洞宽上限,更宽视为建筑缺口
MAX_WIN_W = 16      # 窗洞宽上限(现代幕墙可能很宽,超出记 curtain 标记)
MIN_BALC_AREA = 3   # 露台连通块最小格数
MAX_BALC_DEPTH = 5


# ---------- 材质分类 ----------

def is_door(names):
    return any('Door' in n and 'Trapdoor' not in n for n in names)


def is_glass(names):
    return any('Glass' in n for n in names)


def is_fence(names):
    return any('Fence' in n or 'Wall' in n or 'Bars' in n for n in names)


def mat_tag(names):
    """取一个代表性材质名(排序后第一个)。"""
    return sorted(names)[0] if names else '?'


# 老虎窗代理过滤:墙体类材质 / 装饰类材质(屋脊花草、积雪、台阶饰线等)
WALLISH = ('Plank', 'Wood', 'Brick', 'Stone', 'Clay', 'Cobble', 'Concrete', 'Terracotta', 'Log')
DECOR = ('Slab', 'Carpet', 'Snow', 'Bluet', 'Flower', 'Tulip', 'Daisy', 'Orchid', 'Lantern',
         'Torch', 'Mushroom', 'Fern', 'Grass', 'Vine', 'Leaves', 'Web', 'Pot', 'Button',
         'Pressure', 'Sign', 'Ladder', 'Rail', 'Sapling', 'Wheat', 'Carrot', 'Potato')


# ---------- 平面几何 ----------

def geom_from_occ(occ, H, W):
    """由占用集合求 mask / exterior(外部空气) / filled(填洞后) / ring(外轮廓环) / interior。
    掩膜先外扩 1 格空气边再洪泛:GrabCraft 网格紧贴建筑外包盒,边缘墙格外即"外部"。"""
    mask = np.zeros((H + 2, W + 2), bool)
    for (r, c) in occ:
        mask[r + 1, c + 1] = True
    exterior = np.zeros_like(mask)
    q = deque()
    for r in range(H + 2):
        for c in (0, W + 1):
            if not mask[r, c] and not exterior[r, c]:
                exterior[r, c] = True
                q.append((r, c))
    for c in range(W + 2):
        for r in (0, H + 1):
            if not mask[r, c] and not exterior[r, c]:
                exterior[r, c] = True
                q.append((r, c))
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < H + 2 and 0 <= nc < W + 2 and not mask[nr, nc] and not exterior[nr, nc]:
                exterior[nr, nc] = True
                q.append((nr, nc))
    filled = ~exterior
    ring = set()
    interior = set()
    for r in range(1, H + 1):
        for c in range(1, W + 1):
            if not filled[r, c]:
                continue
            ext = exterior[r - 1, c] or exterior[r + 1, c] or exterior[r, c - 1] or exterior[r, c + 1]
            (ring if ext else interior).add((r - 1, c - 1))
    return mask[1:H + 1, 1:W + 1], exterior[1:H + 1, 1:W + 1], \
        filled[1:H + 1, 1:W + 1], ring, interior


def components(cells, conn8=False):
    """4/8 连通分量,返回 list[set]。"""
    rest = set(cells)
    out = []
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if conn8:
        dirs += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    while rest:
        seed = rest.pop()
        comp = {seed}
        grow = [seed]
        while grow:
            r, c = grow.pop()
            for dr, dc in dirs:
                p = (r + dr, c + dc)
                if p in rest:
                    rest.discard(p)
                    comp.add(p)
                    grow.append(p)
        out.append(comp)
    return out


def spread(comp):
    rs = [p[0] for p in comp]
    cs = [p[1] for p in comp]
    return max(rs) - min(rs) + 1, max(cs) - min(cs) + 1


# ---------- 屋顶识别(同 layer_analyze 口径) ----------

def find_roof_layers(layers_occ, layers_mat, nl):
    cand = []
    for li in range(nl):
        mm = layers_mat[li]
        nst = sum(1 for names in mm.values() if is_stairs(names))
        cand.append(nst >= 5 and nst >= 0.25 * max(1, len(layers_occ[li])))
    clusters = []
    li = 0
    while li < nl:
        if cand[li]:
            cl = [li]
            j = li
            while j + 1 < nl and (cand[j + 1] or (j + 2 < nl and cand[j + 2])):
                j += 1 if cand[j + 1] else 2
                cl.append(j)
            clusters.append(cl)
            li = j + 1
        else:
            li += 1
    return set(max(clusters, key=len)) if clusters else set()


# ---------- 单件分析 ----------

def analyze(bdir):
    got = load_building(Path(bdir))
    if got is None:
        return None
    meta, pal, grids = got
    nl = len(grids)
    if nl < 5:
        return None
    layers_occ, layers_mat, skip, total = reconstruct(pal, grids)
    block_est = sum(len(s) for s in layers_occ)
    if block_est < 50:
        return None
    H, W = grids[0][1].shape[:2]

    roof_layers = find_roof_layers(layers_occ, layers_mat, nl)
    wall_layer_ids = [li for li in range(nl) if li not in roof_layers and len(layers_occ[li]) >= 10]

    def occ_at(li, r, c):
        return 0 <= li < nl and (r, c) in layers_occ[li]

    def mat_at(li, r, c):
        return layers_mat[li].get((r, c)) if 0 <= li < nl else None

    # ---------- 地面层屏障与墙环 ----------
    K = min(BARRIER_K, nl)
    barrier = set()
    for li in range(K):
        barrier |= layers_occ[li]
    _, _, filled_fp, _, _ = geom_from_occ(barrier, H, W)
    ys = [r for r in range(H) if filled_fp[r].any()]
    xs = [c for c in range(W) if filled_fp[:, c].any()]
    bbox = (min(ys), max(ys), min(xs), max(xs)) if ys and xs else (0, 0, 0, 0)

    # ---------- 1. 门洞 ----------
    # 入口层不固定:部分建筑有实心台基/地下室,入口在 idx 1~2。逐层(0..2)检测。
    # 每层用"本层~本层+4 层并集"作屏障掩膜求墙环:门洞空气格被门楣盖住而不致洪泛进室内。
    # 门洞 = 墙环上的 门材质格,或 下方有支撑+内侧通向室内空气 的空气格。
    # 注意:空气落地开口与落地窗/柱廊开口在几何上不可区分,故 mat(门材质) 与 air 分开记录,
    # 主口径取 mat;一座建筑取"有 mat 门的最底层",无 mat 则取"有 air 开口的最底层"。
    def detect_doors(level):
        """返回 (mat_cells, air_cells) 两个候选格集合。
        mat: 本层单层墙环上的门材质格(单层环,避免挑檐上层把门洞藏进屏障内部;材质即证据,免内侧验证)。
        air: 屏障环上的空气格(需屏障防室内洪泛;需支撑+内侧通室内验证)。"""
        if level >= nl or len(layers_occ[level]) < 10:
            return set(), set()
        # mat: 本层~本层+2 层屏障环(3 层足够盖住门洞又不会被更高层挑檐藏起门);
        # air: 本层~本层+4 层屏障环(高门洞需要更高的门楣覆盖才能防室内洪泛)。
        _, _, _, ring_single, _ = geom_from_occ(layers_occ[level], H, W)
        barrier3 = set()
        for up in range(level, min(nl, level + 3)):
            barrier3 |= layers_occ[up]
        _, _, _, ring3, _ = geom_from_occ(barrier3, H, W)
        barrier_d = set()
        for up in range(level, min(nl, level + 5)):
            barrier_d |= layers_occ[up]
        _, _, _, ring_l, interior_l = geom_from_occ(barrier_d, H, W)
        mat_cells, air_cells = set(), set()
        for (r, c) in ring3:
            if not occ_at(level, r, c):
                continue
            m0 = mat_at(level, r, c)
            if m0 is not None and is_door(m0):
                mat_cells.add((r, c))
        for (r, c) in ring_l:
            if (r, c) in mat_cells or occ_at(level, r, c):
                continue
            if level >= 1 and not occ_at(level - 1, r, c):
                continue  # 悬空缺口不是门
            inward = False
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                # 内侧一格在其上 1~2 层为空气 => 通向室内(门口有楼梯时 +1 层可能被占)
                if (nr, nc) in interior_l and (not occ_at(level + 1, nr, nc)
                                               or not occ_at(level + 2, nr, nc)):
                    inward = True
                    break
            if inward:
                air_cells.add((r, c))
        return mat_cells, air_cells

    def group_doors(cells, level, dtype):
        out = []
        for comp in components(cells, conn8=True):
            wr, wc = spread(comp)
            w = max(wr, wc)
            if w > MAX_DOOR_W or len(comp) > w + 2:  # 过宽或 L 形折叠 => 建筑缺口
                continue
            hs = []
            for (r, c) in comp:
                h = 0
                # GrabCraft 层图只在门底一层画门材质,上半扇为空气 => mat 门高 = 门材质+连续空气,封顶 4
                cap = 4 if dtype == 'mat' else 6
                for up in range(level, min(nl, level + 8)):
                    if h >= cap:
                        break
                    m = mat_at(up, r, c)
                    if not occ_at(up, r, c) or (m is not None and is_door(m)):
                        h += 1
                    else:
                        break
                hs.append(h)
            h = int(round(float(np.median(hs))))
            if h < 2:
                continue
            # 居中度:沿墙展开轴,缺口中心相对地面层 footprint 外包盒中心(0=正中,1=贴角)
            r0, r1, c0, c1 = bbox
            if wc >= wr:  # 墙沿列向展开(水平墙)
                off = abs((np.mean([p[1] for p in comp]) - (c0 + c1) / 2) / max(1.0, (c1 - c0) / 2))
            else:
                off = abs((np.mean([p[0] for p in comp]) - (r0 + r1) / 2) / max(1.0, (r1 - r0) / 2))
            out.append({'w': w, 'h': h, 'li': level, 'type': dtype,
                        'off': round(min(1.0, float(off)), 2)})
        return out

    door_cells_used = set()  # 供窗洞检测排除
    doors_mat, doors_air = [], []
    door_level = None
    for level in range(0, 3):
        mc, ac = detect_doors(level)
        if mc and not doors_mat:
            doors_mat = group_doors(mc, level, 'mat')
            door_cells_used |= {(level, p) for p in mc}
            if doors_mat and door_level is None:
                door_level = level
        if ac and not doors_mat and not doors_air:
            doors_air = group_doors(ac, level, 'air')
            door_cells_used |= {(level, p) for p in ac}
            if doors_air and door_level is None:
                door_level = level
    doors = doors_mat if doors_mat else doors_air

    # ---------- 2. 窗洞 ----------
    # 墙环用"本层±1 层并集"作屏障掩膜:空气窗洞被窗台/窗楣盖住而不致洪泛进室内。
    # 窗洞 = 墙环上的 玻璃格,或 上下一格均实心(窗台+窗楣)的空气格。
    windows = []
    win_gaps = []
    per_layer_bands = {}
    for li in wall_layer_ids:
        if li < 1:
            continue  # 地面层只看门;窗从第二层墙身起
        barrier_w = set()
        for up in range(max(0, li - 1), min(nl, li + 2)):
            barrier_w |= layers_occ[up]
        _, _, _, ring_li, _ = geom_from_occ(barrier_w, H, W)
        if len(ring_li) < 12:
            continue
        cand = {}
        for (r, c) in ring_li:
            if (li, (r, c)) in door_cells_used:
                continue  # 门洞不重复计为窗
            m = mat_at(li, r, c)
            if m is not None and is_glass(m):
                cand[(r, c)] = 'glass'
            elif not occ_at(li, r, c):
                # 空气窗:上下一格均须为实心(窗台+窗楣),排除断头墙/垛口
                if occ_at(li - 1, r, c) and occ_at(li + 1, r, c):
                    cand[(r, c)] = 'air'
        for comp in components(cand, conn8=True):
            wr, wc = spread(comp)
            w = max(wr, wc)
            if w > MAX_WIN_W:
                continue
            n_glass = sum(1 for p in comp if cand[p] == 'glass')
            # 纯空气带两端必须是实心窗垛;玻璃为主则免验
            if n_glass <= len(comp) / 2:
                horiz = wc >= wr
                ok_ends = 0
                for p in comp:
                    for d in (-1, 1):
                        q = (p[0], p[1] + d) if horiz else (p[0] + d, p[1])
                        if q not in comp and occ_at(li, q[0], q[1]):
                            ok_ends += 1
                            break
                if ok_ends < 1 and len(comp) > 1:
                    continue
            hs = []
            sills = []
            for (r, c) in comp:
                # 窗带净高:以 li 为中心上下连续(玻璃或空气)的层数
                h = 1
                up = li + 1
                while up < nl and (not occ_at(up, r, c) or
                                   (mat_at(up, r, c) is not None and is_glass(mat_at(up, r, c)))):
                    h += 1
                    up += 1
                dn = li - 1
                while dn >= 0 and (not occ_at(dn, r, c) or
                                   (mat_at(dn, r, c) is not None and is_glass(mat_at(dn, r, c)))):
                    h += 1
                    dn -= 1
                # 窗台:窗带正下方连续实心墙的层数(≈窗底离地高度)
                sill = 0
                while dn >= 0 and occ_at(dn, r, c):
                    sill += 1
                    dn -= 1
                hs.append(h)
                sills.append(sill)
            h = int(round(float(np.median(hs))))
            if h < 1 or h > 6:
                continue
            windows.append({'li': li, 'w': w, 'h': h,
                            'type': 'glass' if n_glass > len(comp) / 2 else 'air',
                            'sill': int(round(float(np.median(sills))))})
            key = (li, 'row' if wc >= wr else 'col',
                   int(np.mean([p[0] for p in comp])) if wc >= wr else int(np.mean([p[1] for p in comp])))
            per_layer_bands.setdefault(key, []).append(comp)
    # 同层同墙面相邻窗带间距(墙格数)
    for (li, orient, _), bands in per_layer_bands.items():
        if len(bands) < 2:
            continue
        spans = []
        for comp in bands:
            cs = [p[1] for p in comp] if orient == 'row' else [p[0] for p in comp]
            spans.append((min(cs), max(cs)))
        spans.sort()
        for i in range(len(spans) - 1):
            g = spans[i + 1][0] - spans[i][1] - 1
            if 0 <= g <= 12:
                win_gaps.append(g)

    # ---------- 3. 屋檐出挑(同 phase9 口径) ----------
    overhang = None
    has_roof = bool(roof_layers)
    if roof_layers and wall_layer_ids:
        lowest_roof = min(roof_layers)
        below = [li for li in wall_layer_ids if li < lowest_roof]
        if below and lowest_roof > 0:
            wall = set()
            for li in below[-2:]:
                wall |= layers_occ[li]
            roof = layers_occ[lowest_roof]
            if wall and roof:
                outside = [p for p in roof if p not in wall]
                if not outside:
                    overhang = 0.0
                else:
                    wallist = list(wall)
                    dists = []
                    for (r, c) in outside:
                        d = min(max(abs(r - wr), abs(c - wc)) for wr, wc in wallist)
                        if d <= 6:
                            dists.append(d)
                    overhang = float(np.median(dists)) if dists else 0.0
    # 平顶出挑:无 stairs 屋顶簇时,比较顶层平面与其下一层的外扩(现代平顶房适用)
    flat_overhang = None
    if not roof_layers and nl >= 2:
        top, below = layers_occ[nl - 1], layers_occ[nl - 2]
        if len(top) >= 6 and len(below) >= 10:
            outside = [p for p in top if p not in below]
            if not outside:
                flat_overhang = 0.0
            else:
                blist = list(below)
                dists = []
                for (r, c) in outside:
                    d = min(max(abs(r - br), abs(c - bc)) for br, bc in blist)
                    if d <= 6:
                        dists.append(d)
                flat_overhang = float(np.median(dists)) if dists else None

    # ---------- 4. 老虎窗(低置信代理) ----------
    dormers = []
    if roof_layers:
        lowest_roof = min(roof_layers)
        for li in sorted(roof_layers):
            if li <= lowest_roof:
                continue
            solid = set()
            for (r, c) in layers_occ[li]:
                m = mat_at(li, r, c)
                if m is not None and is_stairs(m):
                    continue
                # 排除从下层延伸上来的墙体/烟囱(山墙):下方一格为非 stairs 实心的不算屋顶新生结构
                mb = mat_at(li - 1, r, c)
                if occ_at(li - 1, r, c) and not (mb is not None and is_stairs(mb)):
                    continue
                solid.add((r, c))
            for comp in components(solid):
                if not (2 <= len(comp) <= 40):
                    continue
                wr, wc = spread(comp)
                w = max(wr, wc)
                if not (2 <= w <= 8):
                    continue
                r0, r1 = min(p[0] for p in comp), max(p[0] for p in comp)
                c0, c1 = min(p[1] for p in comp), max(p[1] for p in comp)
                cap = False
                for up in range(li + 1, min(nl, li + 4)):
                    for (r, c) in layers_occ[up]:
                        if r0 - 1 <= r <= r1 + 1 and c0 - 1 <= c <= c1 + 1:
                            m = mat_at(up, r, c)
                            if m is not None and is_stairs(m):
                                cap = True
                                break
                    if cap:
                        break
                mats = collections.Counter()
                for (r, c) in comp:
                    m = mat_at(li, r, c)
                    if m is not None:
                        mats[mat_tag(m)] += 1
                mat_dom = mats.most_common(1)[0][0] if mats else '?'
                # 装饰/杂项材质过滤(屋脊花草、积雪、台阶饰线等不是老虎窗)
                mat_ok = (any(k in mat_dom for k in WALLISH)
                          and not any(k in mat_dom for k in DECOR))
                # 墙体延续:>=30% 格在上一层仍有占用(老虎窗墙 2~3 格高;雪堆/花箱 1 格高)
                up_overlap = sum(1 for p in comp if occ_at(li + 1, p[0], p[1])) / len(comp)
                # 邻近玻璃(老虎窗正脸通常有窗)
                glass_near = False
                for (r, c) in comp:
                    for dr in (-2, -1, 0, 1, 2):
                        for dc in (-2, -1, 0, 1, 2):
                            m = mat_at(li, r + dr, c + dc)
                            if m is not None and is_glass(m):
                                glass_near = True
                                break
                        if glass_near:
                            break
                    if glass_near:
                        break
                dormers.append({'li': li, 'w': w, 'size': len(comp), 'cap': cap,
                                'mat': mat_dom, 'mat_ok': mat_ok,
                                'up': round(up_overlap, 2), 'glass': glass_near})

    # ---------- 5. 露台/阳台 ----------
    balconies = []
    for li in wall_layer_ids:
        if li < 1:
            continue
        _, _, _, ring_li, interior_li = geom_from_occ(layers_occ[li], H, W)
        if len(ring_li) < 12:
            continue
        wallcells = set()
        for (r, c) in layers_occ[li]:
            if (r, c) in interior_li:
                continue
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (r + dr, c + dc) in interior_li:
                    wallcells.add((r, c))
                    break
        cand = set()
        for (r, c) in layers_occ[li]:
            if (r, c) in wallcells or (r, c) in interior_li:
                continue
            attach = False
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if (r + dr, c + dc) in wallcells:
                        attach = True
                        break
                if attach:
                    break
            if not attach:
                continue
            if occ_at(li - 1, r, c):
                continue  # 下层有支撑 => 非悬挑
            cand.add((r, c))
        ringlist = list(wallcells)  # 深度参照:有室内邻接的墙面格
        for comp in components(cand):
            if len(comp) < MIN_BALC_AREA:
                continue
            tags = collections.Counter()
            for (r, c) in comp:
                m = mat_at(li, r, c)
                if m is not None:
                    t = ('stairs' if is_stairs(m) else 'glass' if is_glass(m)
                         else 'door' if is_door(m) else 'fence' if is_fence(m) else 'solid')
                    tags[t] += 1
            n = len(comp)
            if tags['stairs'] + tags['fence'] + tags['door'] > n / 2:
                continue  # 排除室外楼梯 / 纯栏杆 / 门斗
            if not ringlist:
                continue
            depth = 0
            for (r, c) in comp:
                d = min(max(abs(r - rr), abs(c - rc)) for rr, rc in ringlist)
                depth = max(depth, d)
            if depth > MAX_BALC_DEPTH:
                continue
            touch = sum(1 for (r, c) in comp
                        if any((r + dr, c + dc) in wallcells for dr in (-1, 0, 1) for dc in (-1, 0, 1)))
            if touch > 0.6 * len(ring_li):
                continue  # 环绕整条外轮廓 => 挑檐带而非局部阳台
            balconies.append({'li': li, 'depth': depth, 'area': n,
                              'mat': tags.most_common(1)[0][0] if tags else '?'})

    # ---------- 6. 墙厚 ----------
    # 口径:取 idx1~3 中第一个"有真实室内空间(室内空气格>=8)"的层;
    # 对占用格做"距外部空气"的 4-连通 BFS(只经过占用格),贴室内空气的墙体格的 BFS 距离 = 该处墙厚。
    # 实心地板层/楼层板层没有室内空气 => 换层;整栋实心 => None。
    # 凸角/贴墙家具会产生少量偏大样本,以众数抗噪;与外墙不连通的室内家具无 BFS 距离,不产生样本。
    thick_runs = []
    wall_li = None
    for li in (1, 2, 3):
        if li >= nl or len(layers_occ[li]) < 10:
            continue
        _, _, _, _, interior1 = geom_from_occ(layers_occ[li], H, W)
        occ1 = layers_occ[li]
        interior_air = {p for p in interior1 if p not in occ1}
        if len(interior_air) >= 4:
            wall_li = li
            break
    if wall_li is not None:
        def is_ext_air(r, c):
            if not (0 <= r < H and 0 <= c < W):
                return True
            return (r, c) not in occ1 and (r, c) not in interior1

        # BFS 图中剔除楼梯格:大楼梯间是实心体量,BFS 会沿踏步深入,把墙厚冲到 5~7
        occ1b = {p for p in occ1
                 if not (layers_mat[wall_li].get(p) and is_stairs(layers_mat[wall_li][p]))}
        dist = {}
        q = deque()
        for (r, c) in occ1b:
            if any(is_ext_air(r + dr, c + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                dist[(r, c)] = 1
                q.append((r, c))
        while q:
            r, c = q.popleft()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                p = (r + dr, c + dc)
                if p in occ1b and p not in dist:
                    dist[p] = dist[(r, c)] + 1
                    q.append(p)
        for (r, c) in occ1b:
            if (r, c) in dist and any((r + dr, c + dc) in interior_air
                                      for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                thick_runs.append(min(dist[(r, c)], 5))
    wall_mode = wall_med = None
    if thick_runs:
        wall_mode = collections.Counter(thick_runs).most_common(1)[0][0]
        wall_med = float(np.median(thick_runs))

    footprint = len(set().union(*layers_occ)) if layers_occ else 0
    roof_area = len(set().union(*(layers_occ[li] for li in roof_layers))) if roof_layers else 0
    return {
        'slug': meta['slug'],
        'layers': nl,
        'footprint': footprint,
        'roof_area': roof_area,
        'skip_rate': round(skip / max(1, total), 3),
        'door_level': door_level,
        'doors': doors,
        'doors_mat_n': len(doors_mat),
        'doors_air_n': len(doors_air),
        'windows': windows,
        'win_gaps': win_gaps,
        'has_roof': has_roof,
        'overhang': overhang,
        'flat_overhang': flat_overhang,
        'dormers': dormers,
        'balconies': balconies,
        'wall_mode': wall_mode,
        'wall_med': wall_med,
        'wall_runs': collections.Counter(thick_runs).most_common(6),
    }


# ---------- 调试输出 ----------

def dump_building(bdir, ana, max_layers=6):
    got = load_building(Path(bdir))
    if got is None:
        print('  [dump] 无法解析')
        return
    meta, pal, grids = got
    layers_occ, layers_mat, _, _ = reconstruct(pal, grids)
    H, W = grids[0][1].shape[:2]
    nl = len(grids)
    roof_layers = find_roof_layers(layers_occ, layers_mat, nl)
    show = sorted(set(range(min(max_layers, nl))) |
                  ({min(roof_layers), min(roof_layers) + 1} if roof_layers else set()))
    print(f"== {meta['slug']}  layers={nl} roof={sorted(roof_layers)}")
    for li in show:
        if li >= nl:
            continue
        print(f"-- layer {li + 1}.png (idx {li}) occ={len(layers_occ[li])}")
        for r in range(H):
            line = []
            for c in range(W):
                if (r, c) not in layers_occ[li]:
                    line.append('.')
                    continue
                m = layers_mat[li].get((r, c))
                if m is None:
                    line.append('?')
                elif is_door(m):
                    line.append('D')
                elif is_glass(m):
                    line.append('G')
                elif is_stairs(m):
                    line.append('S')
                elif is_fence(m):
                    line.append('F')
                else:
                    line.append('#')
            print('   ' + ''.join(line))
    print('   doors:', ana['doors'])
    print('   windows:', ana['windows'][:12])
    print('   balconies:', ana['balconies'])
    print('   dormers:', ana['dormers'][:8])
    print('   overhang:', ana['overhang'], 'wall_mode:', ana['wall_mode'],
          'wall_runs:', ana['wall_runs'])


# ---------- 汇总 ----------

def quant(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return None
    a = np.array(vals, float)
    return {'n': len(vals), 'median': float(np.median(a)), 'p25': float(np.percentile(a, 25)),
            'p75': float(np.percentile(a, 75)), 'mean': float(a.mean())}


def hist(vals, max_key=None):
    c = collections.Counter(int(round(v)) for v in vals if v is not None)
    tot = sum(c.values())
    if not tot:
        return {}
    items = sorted(c.items())
    if max_key is not None:
        items = [(k if k <= max_key else f'{max_key}+', v) for k, v in items]
        c = collections.Counter()
        for k, v in items:
            c[k] += v
        items = sorted(c.items(), key=lambda kv: (isinstance(kv[0], str), kv[0]))
    return {str(k): round(v / tot, 3) for k, v in items}


def summarize(rows):
    out = {'n_buildings': len(rows)}
    doors = [d for r in rows for d in r['doors']]
    out['doors'] = {
        'n_buildings_with': sum(1 for r in rows if r['doors']),
        'n_buildings_mat': sum(1 for r in rows if r['doors_mat_n']),
        'n_buildings_air': sum(1 for r in rows if not r['doors_mat_n'] and r['doors_air_n']),
        'n_doors': len(doors),
        'n_mat': sum(r['doors_mat_n'] for r in rows),
        'n_air_fallback': sum(r['doors_air_n'] for r in rows if not r['doors_mat_n']),
        'level_hist': hist([d['li'] for d in doors]),
        'per_building': quant([len(r['doors']) for r in rows]),
        'w_hist': hist([d['w'] for d in doors]),
        'h_hist': hist([d['h'] for d in doors]),
        'w_quant': quant([d['w'] for d in doors]),
        'h_quant': quant([d['h'] for d in doors]),
        'type_hist': hist([1 if d['type'] == 'mat' else 0 for d in doors]),
        'double_ratio': round(sum(1 for d in doors if d['w'] >= 2) / len(doors), 3) if doors else None,
        # 居中度分桶(粗口径:相对外包盒中轴):<=0.15 居中 / 0.15~0.4 微偏 / 0.4~0.6 中段 / 0.6~0.85 偏侧 / >0.85 贴角
        'off_hist': (lambda bs: {k: round(v / len(doors), 3) for k, v in bs.items()})
                    (collections.Counter(
                        'centered' if d['off'] <= 0.15 else
                        'slight' if d['off'] <= 0.4 else
                        'mid' if d['off'] <= 0.6 else
                        'side' if d['off'] <= 0.85 else 'corner'
                        for d in doors)) if doors else {},
        # 按类型分开的门洞尺寸(mat=门材质,高置信;air=落地开口,与落地窗/柱廊不可区分)
        'mat_w_hist': hist([d['w'] for d in doors if d['type'] == 'mat']),
        'mat_h_hist': hist([d['h'] for d in doors if d['type'] == 'mat']),
        'air_w_hist': hist([d['w'] for d in doors if d['type'] == 'air']),
        'air_h_hist': hist([d['h'] for d in doors if d['type'] == 'air']),
    }
    wins = [w for r in rows for w in r['windows']]
    gaps = [g for r in rows for g in r['win_gaps']]
    glass = [w for w in wins if w['type'] == 'glass']
    out['windows'] = {
        'n_buildings_with': sum(1 for r in rows if r['windows']),
        'n_windows': len(wins),
        'w_hist': hist([w['w'] for w in wins], max_key=8),
        'h_hist': hist([w['h'] for w in wins], max_key=5),
        'w_quant': quant([w['w'] for w in wins]),
        'h_quant': quant([w['h'] for w in wins]),
        'sill_hist': hist([w['sill'] for w in wins], max_key=6),
        'sill_quant': quant([w['sill'] for w in wins]),
        'li_hist': hist([w['li'] for w in wins], max_key=8),
        'type_hist': hist([1 if w['type'] == 'glass' else 0 for w in wins]),
        'gap_hist': hist(gaps, max_key=8),
        'gap_quant': quant(gaps),
        # 玻璃窗(高置信子集)单独分布
        'glass_w_hist': hist([w['w'] for w in glass], max_key=8),
        'glass_h_hist': hist([w['h'] for w in glass], max_key=5),
        'glass_sill_hist': hist([w['sill'] for w in glass], max_key=6),
        'glass_sill_quant': quant([w['sill'] for w in glass]),
    }
    oh = [r['overhang'] for r in rows if r['has_roof'] and r['overhang'] is not None]
    foh = [r['flat_overhang'] for r in rows if r['flat_overhang'] is not None]
    out['overhang'] = {
        'n_with_roof': sum(1 for r in rows if r['has_roof']),
        'no_roof': sum(1 for r in rows if not r['has_roof']),
        'unmeasurable': sum(1 for r in rows if r['has_roof'] and r['overhang'] is None),
        'dist': hist(oh, max_key=3),
        'quant': quant(oh),
        'zero': sum(1 for v in oh if v == 0),
        'flat_dist': hist(foh, max_key=3),
        'flat_quant': quant(foh),
    }
    dorm = [d for r in rows for d in r['dormers'] if d['cap']]
    strict_d = [d for d in dorm if d['mat_ok'] and d['up'] >= 0.3]
    glass_d = [d for d in strict_d if d['glass']]
    out['dormers'] = {
        'n_buildings_with': sum(1 for r in rows if any(d['cap'] for d in r['dormers'])),
        'n_candidates': len(dorm),
        'n_candidates_nocap': sum(1 for r in rows for d in r['dormers'] if not d['cap']),
        # 过滤后(墙体材质+2 格高)的老虎窗代理;glass 子集为高置信
        'strict_n_buildings': sum(1 for r in rows
                                  if any(d['cap'] and d['mat_ok'] and d['up'] >= 0.3
                                         for d in r['dormers'])),
        'strict_n': len(strict_d),
        'strict_w_hist': hist([d['w'] for d in strict_d]),
        'strict_size_quant': quant([d['size'] for d in strict_d]),
        'glass_n_buildings': sum(1 for r in rows
                                 if any(d['cap'] and d['mat_ok'] and d['up'] >= 0.3 and d['glass']
                                        for d in r['dormers'])),
        'glass_n': len(glass_d),
        'glass_w_hist': hist([d['w'] for d in glass_d]),
        'w_hist': hist([d['w'] for d in dorm]),
        'mat_hist': collections.Counter(d['mat'] for d in dorm).most_common(8),
        # 占屋面比例:严格候选总面积 / 屋顶层并集面积(仅有候选的建筑)
        'area_ratio_quant': quant([
            sum(d['size'] for d in r['dormers'] if d['cap'] and d['mat_ok'] and d['up'] >= 0.3)
            / r['roof_area']
            for r in rows
            if r['roof_area'] and any(d['cap'] and d['mat_ok'] and d['up'] >= 0.3
                                      for d in r['dormers'])]),
    }
    balc = [b for r in rows for b in r['balconies']]
    strict = [b for b in balc if b['depth'] >= 2 and b['area'] >= 4]
    out['balconies'] = {
        'n_buildings_with': sum(1 for r in rows if r['balconies']),
        'n': len(balc),
        'depth_hist': hist([b['depth'] for b in balc]),
        'depth_quant': quant([b['depth'] for b in balc]),
        'area_quant': quant([b['area'] for b in balc]),
        'mat_hist': collections.Counter(b['mat'] for b in balc).most_common(6),
        # 严格口径:进深>=2 且面积>=4,才可容人,才算真露台/阳台(浅小凸块多为装饰/烟囱胸)
        'strict_n_buildings': sum(1 for r in rows
                                  if any(b['depth'] >= 2 and b['area'] >= 4 for b in r['balconies'])),
        'strict_n': len(strict),
        'strict_depth_hist': hist([b['depth'] for b in strict]),
        'strict_depth_quant': quant([b['depth'] for b in strict]),
    }
    out['wall'] = {
        'mode_hist': hist([r['wall_mode'] for r in rows]),
        'med_quant': quant([r['wall_med'] for r in rows]),
        # 每件建筑"墙皮样本中 dist=1 的占比":>50% 即外墙主体为 1 格厚,抗内隔墙/家具噪声
        'one_share_quant': quant([
            (lambda c: c.get(1, 0) / sum(c.values()) if sum(c.values()) else None)
            (dict(r['wall_runs'])) for r in rows]),
    }
    return out


def main():
    ap = argparse.ArgumentParser(description='GrabCraft 细节构件定量基准挖掘')
    ap.add_argument('--data', default=str(Path(__file__).resolve().parents[2] / 'phase9' / 'gc_probe' / 'gc_data'))
    ap.add_argument('--category', default='medieval-houses')
    ap.add_argument('--sample', type=int, default=20)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--dump', type=int, default=0, help='打印前 N 件的层图与检测结果')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    data = Path(args.data)
    cands = []
    for d in sorted(data.iterdir()):
        mp = d / 'meta.json'
        if not mp.exists() or not (d / 'layers').is_dir():
            continue
        try:
            m = json.load(open(mp, encoding='utf-8'))
        except Exception:
            continue
        if (m.get('url') or '').rstrip('/').endswith(args.category):
            cands.append(d)
    random.seed(args.seed)
    random.shuffle(cands)
    cands = cands[:args.sample]
    print(f'类目 {args.category}: 抽样 {len(cands)} 件', flush=True)

    rows, failed = [], 0
    for i, d in enumerate(cands):
        try:
            r = analyze(d)
        except Exception as e:
            print(f'  [err] {d.name}: {e}', flush=True)
            r = None
        if r is None:
            failed += 1
            continue
        rows.append(r)
        if i < args.dump:
            dump_building(d, r)
        if (i + 1) % 25 == 0:
            print(f'  {i + 1}/{len(cands)} ok={len(rows)} fail={failed}', flush=True)
    print(f'完成: 成功 {len(rows)}, 失败 {failed}', flush=True)

    summary = summarize(rows)
    result = {'category': args.category, 'sampled': len(cands), 'ok': len(rows),
              'failed': failed, 'seed': args.seed, 'summary': summary, 'rows': rows}
    out = args.out or str(Path(__file__).parent / f'details_{args.category}.json')
    Path(out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    print('写出', out, flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=1), flush=True)


if __name__ == '__main__':
    main()
