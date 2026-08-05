# -*- coding: utf-8 -*-
"""
GrabCraft 层图分析器:从 layers/*.png 反解逐层方块占用,统计肌理卡校准参数。

PNG 语义(实验验证,详见 stats_details.md):
- PNG 为 RGB 四象限复合图:左上=正视线框图,右=侧视线框图,左下=当前层俯视平面图(白底网格)。
- 平面图区:空气=纯白 (255,255,255),图外=GrabCraft 蓝 (3,80,162),网格线=浅蓝/浅灰。
- 每格 18~20px(逐图检测),格心 5x5 中位数色与 meta.json 的 color 色板精确匹配。
- 重要:PNG n 在"本层为空气、下一层(y=n-1)有方块"的格子上会透视显示下一层方块(幽灵块)。
  重建规则:同一 (格子,颜色) 连续出现 k 次且未达顶层 => 最高一次为幽灵,剔除;其余保留。
"""
import json
import random
import argparse
import collections
from pathlib import Path

import numpy as np
from PIL import Image

AIR = (255, 255, 255)


# ---------- PNG 解析 ----------

def plan_bbox(im):
    """定位左下平面图区域:从左下角对"非蓝"像素做洪泛,取连通域外接框。
    (平面图白底+彩格为非蓝,背景/立面线框为蓝,蓝色分隔线天然阻断洪泛。)"""
    from collections import deque
    h, w = im.shape[0], im.shape[1]
    r, b = im[..., 0], im[..., 2]
    blocked = (b - r > 60) & (b > 120)
    start = None
    for y in range(h - 1, max(h - 30, -1), -1):
        for x in range(0, 30):
            if not blocked[y, x]:
                start = (y, x)
                break
        if start:
            break
    if start is None:
        return None
    seen = np.zeros((h, w), bool)
    q = deque([start])
    seen[start] = True
    y0 = y1 = start[0]
    x0 = x1 = start[1]
    n = 0
    while q:
        y, x = q.popleft()
        n += 1
        y0 = min(y0, y); y1 = max(y1, y)
        x0 = min(x0, x); x1 = max(x1, x)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and not blocked[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    if n < 2000:  # 区域太小,判定失败
        return None
    return y0, y1, x0, x1


def lattice1d(chg):
    """从一维边界变化率求网格 pitch 与相位。边界=相邻像素颜色突变且变化率>0.25 的列/行。"""
    cands = np.where(chg > 0.25)[0]
    groups = []
    for x in cands:
        if groups and x - groups[-1][-1] <= 2:
            groups[-1].append(x)
        else:
            groups.append([x])
    centers = [int(gp[len(gp) // 2]) for gp in groups]
    if len(centers) < 2:
        return None
    pitch = int(round(np.median(np.diff(centers))))
    if pitch < 6:
        return None
    off = collections.Counter(c % pitch for c in centers).most_common(1)[0][0]
    return pitch, off


def extract_grid(path, geom=None):
    """抽取平面图格子矩阵,返回 (H,W,3) int 数组(格心 5x5 中位数色)及几何参数。"""
    im = np.asarray(Image.open(path).convert('RGB')).astype(int)
    if geom is None:
        bb = plan_bbox(im)
        if bb is None:
            return None, None
        y0, y1, x0, x1 = bb
        sub = im[y0:y1 + 1, x0:x1 + 1]
        colchg = (np.abs(np.diff(sub, axis=1)).sum(axis=2) > 0).mean(axis=0)
        rowchg = (np.abs(np.diff(sub, axis=0)).sum(axis=2) > 0).mean(axis=1)
        lc, lr = lattice1d(colchg), lattice1d(rowchg)
        if lc is None or lr is None:
            return None, None
        geom = (y0, y1, x0, x1, lc, lr)
    y0, y1, x0, x1, (px, ox), (py, oy) = geom
    sub = im[y0:y1 + 1, x0:x1 + 1]
    xs = list(range(ox + px // 2, sub.shape[1] - 2, px))
    ys = list(range(oy + py // 2, sub.shape[0] - 2, py))
    out = np.full((len(ys), len(xs), 3), -1, int)
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            patch = sub[max(0, y - 2):y + 3, max(0, x - 2):x + 3].reshape(-1, 3)
            out[iy, ix] = np.median(patch, axis=0)
    return out, geom


# ---------- 单件建筑分析 ----------

def load_building(bdir):
    """返回 layers: list[(y_index, grid)]、palette: color->names、meta。"""
    meta = json.load(open(bdir / 'meta.json', encoding='utf-8'))
    pal = collections.defaultdict(list)
    for mt in meta['materials']:
        c = mt['color']
        if isinstance(c, str) and len(c) == 7 and c.startswith('#'):
            try:
                pal[tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))].append(mt['name'])
            except ValueError:
                pass
    ldir = bdir / 'layers'
    nums = sorted(int(p.stem) for p in ldir.glob('*.png') if p.stem.isdigit())
    grids, geom = [], None
    for n in nums:
        g, geom = extract_grid(ldir / f'{n}.png', geom)
        if g is None or not grids and geom is None:
            return None
        if grids and g.shape != grids[0][1].shape:
            return None  # 层间尺寸不一致,跳过
        grids.append((n, g))
    return meta, pal, grids


def reconstruct(pal, grids):
    """幽灵块剔除 + 色板反解。
    返回 occ: list[set((r,c))] 每层占用; mats: dict[(layer,r,c)] -> frozenset(names);
    skip: 未知色格数; total_cells: 非空气格数(含幽灵)。"""
    shape = grids[0][1].shape[:2]
    nl = len(grids)
    # 每格颜色的精确色板命中
    hit = []  # list of (name-set-or-None) 2D object arrays
    skip = 0
    total = 0
    for _, g in grids:
        m = np.empty(shape, object)
        for r in range(shape[0]):
            for c in range(shape[1]):
                t = tuple(g[r, c])
                if t == AIR or t == (-1, -1, -1):
                    m[r, c] = None
                elif t in pal:
                    m[r, c] = frozenset(pal[t])
                else:
                    m[r, c] = '?'  # 非空但未命中色板
        hit.append(m)
        skip += int((m == '?').sum())
        total += int((m != None).sum())  # noqa: E711
    # 幽灵剔除:同格同内容(精确同色,即 name-set 相同且非'?')的连续段,未达顶层的段去掉最高层
    occ = []
    for li in range(nl):
        s = set()
        m = hit[li]
        for r in range(shape[0]):
            for c in range(shape[1]):
                v = m[r, c]
                if v is None:
                    continue
                if v != '?' and li + 1 < nl and hit[li + 1][r, c] is not None \
                        and hit[li + 1][r, c] == v:
                    # 上方同格同色:本格在 li+1 层仍出现。若该连续段延伸到顶层则都真实,
                    # 否则段顶为幽灵 —— 段顶判定在下方统一做。
                    pass
                s.add((r, c, v))
        occ.append(s)
    # 逐格纵向扫描,标记幽灵格
    ghost = set()
    for r in range(shape[0]):
        for c in range(shape[1]):
            li = 0
            while li < nl:
                v = hit[li][r, c]
                if v is None or v == '?':
                    li += 1
                    continue
                top = li
                while top + 1 < nl and hit[top + 1][r, c] == v:
                    top += 1
                if top > li and top < nl - 1:
                    ghost.add((top, r, c))  # 段顶未达 PNG 顶层 => 幽灵
                elif top > li and top == nl - 1:
                    pass  # 到达顶层,无法区分,全部保留
                li = top + 1
    layers_occ = []
    layers_mat = []
    for li in range(nl):
        s, mm = set(), {}
        for (r, c, v) in occ[li]:
            if (li, r, c) in ghost:
                continue
            s.add((r, c))
            if v != '?':
                mm[(r, c)] = v
        layers_occ.append(s)
        layers_mat.append(mm)
    return layers_occ, layers_mat, skip, total


def is_stairs(names):
    return all('Stairs' in n for n in names)


def is_log(names):
    # GrabCraft 命名:"Oak Wood"=原木柱,"Oak Wood Plank"=木板;排除 Plank/Stairs/Fence 等
    bad = ('Plank', 'Stairs', 'Fence', 'Slab', 'Door', 'Trapdoor', 'Bark', 'Beam')
    return any('Wood' in n and not any(b in n for b in bad) for n in names)


def convex_hull_area(points):
    """单调链凸包(格点),返回凸包面积(格子数口径:面积+边界修正用简单面积即可)。"""
    pts = sorted(set(points))
    if len(pts) < 3:
        return len(pts)
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    area = abs(sum(hull[i][0] * hull[(i + 1) % len(hull)][1]
                   - hull[(i + 1) % len(hull)][0] * hull[i][1]
                   for i in range(len(hull)))) / 2
    # Pick 定理口径:格点多边形覆盖格子数 ≈ area + boundary/2 + 1
    b = 0
    for i in range(len(hull)):
        x1, y1 = hull[i]
        x2, y2 = hull[(i + 1) % len(hull)]
        import math
        b += math.gcd(abs(x2 - x1), abs(y2 - y1))
    return area + b / 2 + 1


def analyze_building(bdir):
    """返回 dict 或 None(无法解析)。"""
    got = load_building(bdir)
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

    # --- 屋顶层识别:stairs 占比高的层为候选;取允许 1 层间隔的最大连续簇 ---
    # (烟囱等会造成顶层零星 stairs,孤立小簇不取;medieval 坡屋顶 stairs 跨多 y 层)
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
    roof_layers = set(max(clusters, key=len)) if clusters else set()
    wall_layer_ids = [li for li in range(nl) if li not in roof_layers and len(layers_occ[li]) >= 10]

    # --- d. 屋顶层占比 ---
    roof_ratio = len(roof_layers) / nl if roof_layers else 0.0

    # --- a. 檐口出挑:最低屋顶层相对其下墙身占用的外扩距离 ---
    overhang = None
    if roof_layers and wall_layer_ids:
        lowest_roof = min(roof_layers)
        below = [li for li in wall_layer_ids if li < lowest_roof]
        if below and lowest_roof > 0:
            wall = set()
            for li in below[-2:]:  # 取屋顶下最近两层墙身
                wall |= layers_occ[li]
            roof = layers_occ[lowest_roof]
            if wall and roof:
                outside = [p for p in roof if p not in wall]
                # 每个外扩格到墙体的切比雪夫距离
                wallist = list(wall)
                dists = []
                for (r, c) in outside:
                    d = min(max(abs(r - wr), abs(c - wc)) for wr, wc in wallist)
                    if d <= 6:
                        dists.append(d)
                if len(dists) >= 4:
                    overhang = float(np.median(dists))

    # --- b. 墙面凹凸率:墙身层外轮廓相对凸包的凹陷占比(先填室内空洞),取各层中位数 ---
    bump = None
    rates = []
    H, W = grids[0][1].shape[:2]
    for li in wall_layer_ids:
        pts = layers_occ[li]
        if len(pts) < 20:
            continue
        mask = np.zeros((H, W), bool)
        for (r, c) in pts:
            mask[r, c] = True
        # 洪泛外部 => 空洞=未占用且非外部
        from collections import deque
        outside = np.zeros((H, W), bool)
        q = deque()
        for r in range(H):
            for c in (0, W - 1):
                if not mask[r, c] and not outside[r, c]:
                    outside[r, c] = True; q.append((r, c))
        for c in range(W):
            for r in (0, H - 1):
                if not mask[r, c] and not outside[r, c]:
                    outside[r, c] = True; q.append((r, c))
        while q:
            r, c = q.popleft()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and not mask[nr, nc] and not outside[nr, nc]:
                    outside[nr, nc] = True
                    q.append((nr, nc))
        filled = mask | ~outside
        fpts = [tuple(p) for p in np.argwhere(filled)]
        hull = convex_hull_area(fpts)
        if hull > 0:
            rates.append(max(0.0, (hull - len(fpts)) / hull))
    if rates:
        bump = float(np.median(rates))

    # --- c. 木构柱距:纵向 log 柱(同格连续>=3层 log)的水平最近邻间距 ---
    spacing = None
    posts = []
    for r in range(grids[0][1].shape[0]):
        for c in range(grids[0][1].shape[1]):
            run = 0
            best = 0
            for li in range(nl):
                names = layers_mat[li].get((r, c))
                if names and is_log(names):
                    run += 1
                    best = max(best, run)
                else:
                    run = 0
            if best >= 3:
                posts.append((r, c))
    if len(posts) >= 2:
        # 相邻(切比雪夫距离1)的柱格先并簇(宽厚柱/并列柱视为一根),再取最近邻间距
        pset = set(posts)
        clusters = []
        while pset:
            seed = pset.pop()
            cl = [seed]
            grow = [seed]
            while grow:
                r, c = grow.pop()
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        p = (r + dr, c + dc)
                        if p in pset:
                            pset.discard(p)
                            cl.append(p)
                            grow.append(p)
            clusters.append(cl)
        cents = [(round(sum(p[0] for p in cl) / len(cl)),
                  round(sum(p[1] for p in cl) / len(cl))) for cl in clusters]
        ds = []
        for i, (r, c) in enumerate(cents):
            d = min((max(abs(r - r2), abs(c - c2))
                     for j, (r2, c2) in enumerate(cents) if j != i), default=None)
            if d:
                ds.append(d)
        if ds:
            spacing = float(np.median(ds))
        n_posts = len(cents)
    else:
        n_posts = len(posts)

    footprint = len(set().union(*layers_occ)) if layers_occ else 0
    return {
        'slug': meta['slug'],
        'layers': nl,
        'block_count': meta.get('block_count'),
        'block_est': block_est,
        'footprint': footprint,
        'skip_rate': skip / max(1, total),
        'overhang': overhang,
        'bump_rate': bump,
        'post_spacing': spacing,
        'n_posts': n_posts,
        'roof_ratio': roof_ratio,
    }


# ---------- 汇总 ----------

def quant(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return None
    a = np.array(vals, float)
    return {
        'n': len(vals),
        'median': float(np.median(a)),
        'p25': float(np.percentile(a, 25)),
        'p75': float(np.percentile(a, 75)),
        'mean': float(a.mean()),
    }


def mode_bucket(vals, step):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, {}
    hist = collections.Counter()
    for v in vals:
        if step == 1:
            hist[int(round(v))] += 1
        else:
            hist[round(v / step) * step] += 1
    total = sum(hist.values())
    top = hist.most_common(1)[0]
    return (top[0], top[1] / total), {k: round(v / total, 3) for k, v in sorted(hist.items())}


def main():
    ap = argparse.ArgumentParser(description='GrabCraft 层图肌理统计')
    ap.add_argument('--data', default=str(Path(__file__).parent / 'gc_data'))
    ap.add_argument('--category', default='medieval-houses')
    ap.add_argument('--sample', type=int, default=300)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--out', default=str(Path(__file__).parent / 'layer_stats.json'))
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
        if args.category and args.category not in (m.get('url') or ''):
            continue
        cands.append(d)
    random.seed(args.seed)
    random.shuffle(cands)
    cands = cands[:args.sample]
    print(f'类目 {args.category}: 候选命中后抽样 {len(cands)} 件')

    rows, failed = [], 0
    for i, d in enumerate(cands):
        try:
            r = analyze_building(d)
        except Exception as e:
            print(f'  [err] {d.name}: {e}')
            r = None
        if r is None:
            failed += 1
        else:
            rows.append(r)
        if (i + 1) % 50 == 0:
            print(f'  {i + 1}/{len(cands)} ok={len(rows)} fail={failed}')
    print(f'完成: 成功 {len(rows)}, 跳过/失败 {failed}')

    fp = sorted(r['footprint'] for r in rows)
    fp_med = fp[len(fp) // 2] if fp else 0

    def subset(rs):
        return {
            'overhang': quant([r['overhang'] for r in rs]),
            'bump_rate': quant([r['bump_rate'] for r in rs]),
            'post_spacing': quant([r['post_spacing'] for r in rs]),
            'roof_ratio': quant([r['roof_ratio'] for r in rs]),
            'overhang_dist': mode_bucket([r['overhang'] for r in rs], 1),
            'spacing_dist': mode_bucket([r['post_spacing'] for r in rs], 1),
            'skip_rate_mean': float(np.mean([r['skip_rate'] for r in rs])) if rs else None,
            'skip_rate_max': float(np.max([r['skip_rate'] for r in rs])) if rs else None,
        }

    small = [r for r in rows if r['footprint'] <= fp_med]
    big = [r for r in rows if r['footprint'] > fp_med]
    result = {
        'category': args.category,
        'sampled': len(cands),
        'ok': len(rows),
        'failed': failed,
        'footprint_median': fp_med,
        'all': subset(rows),
        'small': subset(small),
        'big': subset(big),
        'n_small': len(small),
        'n_big': len(big),
        'rows': rows,
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    print('写出', args.out)


if __name__ == '__main__':
    main()
