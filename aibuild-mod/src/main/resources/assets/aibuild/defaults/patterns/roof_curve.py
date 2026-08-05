#!/usr/bin/env python3
"""roof_curve.py — segmented curved roof (分段曲线屋顶) generator.

Discretizes an arbitrary-curvature roof slope into named segments (六段式
屋面曲线法, source: D:\\建筑资产\\调研\\图片造法提炼.md 屋顶教程组):
- segment library by run:rise (横向格数:升高): s4=4:1, s3=3:1, s2=2:1
  (shallow treads: 1 stair + (r-1) top slabs per cycle), s1=1:1 (45° stair),
  d2=1:2 (stacked pair: stair + upside-down stair, 2 y per column).
- zone rule baked into each profile: 起步区 (eave, shallowest, long) ->
  缓冲区 (mid, most transitions) -> 冲刺区 (near ridge, steepest, short).
- SLOPE BLENDING (斜率混淆): at every segment boundary the last column of
  the shallower segment and the first column of the steeper segment SWAP
  step distances (交界 ±1 步互插邻段步距) — a pure permutation of the
  height increments, so total rise is unchanged but the "屋面骨折" hard
  kink disappears. All profiles keep adjacent-segment rise ratio <= 2.

NOTE: the A-F run:rise ratios were estimated from tutorial images (文档
诚实声明); we bake conservative integer ratios (4:1/3:1/2:1/1:1/1:2) —
re-calibrate against the original text page if it surfaces.

Solid-core ridge (实芯脊, gable_roof E8 lesson: no floating slab ridge):
odd span gets a full beam column from roof base to the ridge slab; even
span caps both knife-edge columns. Stair facing/half derived by the script
— never hand-edit the output (禁止手改方向状态).

Usage:
  python roof_curve.py --params '{"origin":[100,80,100],"width":9,"depth":11,"profile":"classic_chinese"}' [--out roof.json]
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import Builder, die, require_suffix, stair, slab, write_out

# segment library: kind -> run (columns per +1 y); d2 = 2 y per column
RUNS = {"s4": 4, "s3": 3, "s2": 2, "s1": 1, "d2": 0.5}

PROFILES = {
    # 中式举折曲线: 檐口平缓 -> 中段均匀加速 -> 近脊陡起 (理想模型六段法的保守四段版)
    "classic_chinese": [("s4", 0.30), ("s2", 0.30), ("s1", 0.25), ("d2", 0.15)],
    # 缓曲线: 全程平缓, 适合大跨度低屋顶
    "gentle":          [("s4", 0.40), ("s3", 0.35), ("s2", 0.25)],
    # 陡曲线: 快速起坡, 适合小体量高脊
    "steep":           [("s2", 0.35), ("s1", 0.40), ("d2", 0.25)],
}

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] NW corner of the WALL footprint; y = roof base layer
    "width": 9,                    # wall footprint along x
    "depth": 11,                   # wall footprint along z (the slope span)
    "profile": "classic_chinese",  # baked segment table; see PROFILES
    "overhang": 1,                 # eaves past the wall line (0-2)
    "axis": "x",                   # ridge axis: "x" or "z"
    "material": "minecraft:spruce_stairs",
    "ridge_material": "minecraft:spruce_slab",
    "ridge_support": "minecraft:spruce_planks",  # solid core under the ridge (E8 实测)
    "end_fill": ""                 # e.g. "minecraft:oak_planks": solid gable-end walls inside the footprint
}

def allocate(segments, S):
    """Largest-remainder split of S columns over (kind, proportion) segments."""
    raw = [prop * S for _, prop in segments]
    counts = [max(1, int(v)) for _, v in zip(segments, raw)]
    while sum(counts) > S:  # trim from the largest segment
        i = counts.index(max(counts))
        counts[i] -= 1
    rem = S - sum(counts)
    order = sorted(range(len(segments)), key=lambda i: raw[i] - int(raw[i]), reverse=True)
    for i in order[:rem]:
        counts[i] += 1
    return counts

def height_increments(segments, S):
    """Per-column y increments eave->ridge, with slope blending at boundaries.

    Pure pattern: run r segment cycles [1,0,...] (r columns per step); d2 is
    all 2s. Blending: swap the increments of the boundary-adjacent column
    pair (k-1, k) — ±1 步互插邻段步距, total rise unchanged."""
    inc = []
    bounds = []
    for (kind, _), n in zip(segments, allocate(segments, S)):
        if kind == "d2":
            inc += [2] * n
        else:
            r = RUNS[kind]
            inc += [1 if t % r == 0 else 0 for t in range(n)]
        bounds.append(len(inc))
    blends = []
    for k in bounds[:-1]:
        if inc[k - 1] != inc[k]:
            inc[k - 1], inc[k] = inc[k], inc[k - 1]
            blends.append(k)
    inc[0] = max(1, inc[0])  # eave column is always a step (sits on roof base)
    return inc, blends

def build(p):
    ox, oy, oz = p["origin"]
    w, d = int(p["width"]), int(p["depth"])
    oh = max(0, int(p["overhang"]))
    mat, ridgem, fill = p["material"], p["ridge_material"], p["end_fill"]
    beam = p.get("ridge_support", "minecraft:spruce_planks")
    slabm = mat.replace("_stairs", "_slab")
    axis = p.get("axis", "x")
    if axis == "z":
        w, d = d, w
    T = d + 2 * oh
    S = T // 2
    segments = PROFILES[p["profile"]]
    inc, blends = height_increments(segments, S)
    off = []
    acc = 0
    for v in inc:
        acc += v
        off.append(acc)               # walking surface above oy for column j
    ytop = oy + off[-1]

    # axis=z transposes local coords (local x -> world z); facings rotate too
    FACING_ROT = {"south": "east", "east": "south", "north": "west", "west": "north"}
    b = Builder(rot=(lambda x, z: (z, x)) if axis == "z" else None,
                fmap=FACING_ROT if axis == "z" else None)

    def slope_row(rel, kind, surf):
        """One profile column at distance rel from each eave, mirrored.
        kind: 'stair' (45°) | 'tread' (top slab + support stair) | 'pair' (1:2)."""
        for x in range(-oh, w + oh):
            zn = -oh + rel
            zs = T - 1 - oh - rel
            for z, f in ((zn, "south"), (zs, "north")):
                if kind == "pair":
                    b.put(x, surf - 2, z, stair(mat, f))
                    b.put(x, surf - 1, z, stair(mat, f, half="top"))
                elif kind == "stair":
                    b.put(x, surf - 1, z, stair(mat, f))
                else:  # tread slab carried by a support stair (slab hole rule)
                    b.put(x, surf - 1, z, slab(slabm, "top"))
                    b.put(x, surf - 2, z, stair(mat, f))

    for j in range(S):
        kind = "pair" if inc[j] == 2 else ("stair" if inc[j] == 1 else "tread")
        slope_row(j, kind, oy + off[j])

    # ---- solid-core ridge (实芯脊) -----------------------------------------
    if T % 2 == 1:
        zmid = -oh + S
        for x in range(-oh, w + oh):
            for y in range(oy, ytop - 1):        # solid beam core, no悬空脊
                b.put(x, y, zmid, beam)
            b.put(x, ytop - 1, zmid, slab(ridgem, "top"))   # flush seam
            b.put(x, ytop, zmid, slab(ridgem, "bottom"))
    else:
        for x in range(-oh, w + oh):             # two knife-edge caps
            b.put(x, ytop, -oh + S - 1, slab(ridgem, "bottom"))
            b.put(x, ytop, T - oh - S, slab(ridgem, "bottom"))

    # ---- optional gable-end walls (收分三角形, inside the wall footprint) ---
    if fill:
        for y in range(oy, ytop):
            for x in (0, w - 1):
                for z in range(0, d):
                    if not b.has(x, y, z):
                        b.put(x, y, z, fill)
    if blends:
        print("slope blending at columns eave->ridge: %s" % blends, file=sys.stderr)
    return b.emit([ox, 0, oz])  # y already absolute (computed from oy)

def validate(p):
    try:
        w, d, oh = int(p["width"]), int(p["depth"]), int(p["overhang"])
    except (TypeError, ValueError):
        die("width/depth/overhang must be ints",
            {"width": "3-31", "depth": "3-31", "overhang": "0-2"})
    if not 3 <= w <= 31 or not 3 <= d <= 31:
        die("width/depth out of range", {"width": "3-31", "depth": "3-31"})
    if not 0 <= oh <= 2:
        die("overhang out of range", {"overhang": [0, 1, 2]})
    if p.get("axis", "x") not in ("x", "z"):
        die("axis must be x or z", {"axis": ["x", "z"]})
    if p["profile"] not in PROFILES:
        die("unknown profile", {"profile": sorted(PROFILES)})
    span = d + 2 * oh if p.get("axis", "x") == "x" else w + 2 * oh
    S = span // 2
    nseg = len(PROFILES[p["profile"]])
    if S < max(4, nseg):
        die("slope span %d columns too small for profile %s (%d segments); "
            "need span/2 >= %d" % (S, p["profile"], nseg, max(4, nseg)),
            {"min_span": 2 * max(4, nseg), "this_span": span})
    # 铁律: adjacent-segment rise ratio <= 2 (屋面骨折 pitfall)
    rises = [1.0 / RUNS[k] for k, _ in PROFILES[p["profile"]]]
    for a, bb in zip(rises, rises[1:]):
        if max(a, bb) / min(a, bb) > 2:
            die("profile %s has adjacent rise ratio > 2 (屋面骨折)" % p["profile"], {})
    require_suffix(p, "material", "_stairs",
                   ["minecraft:spruce_stairs", "minecraft:dark_oak_stairs",
                    "minecraft:deepslate_tile_stairs"])
    require_suffix(p, "ridge_material", "_slab",
                   ["minecraft:spruce_slab", "minecraft:dark_oak_slab",
                    "minecraft:deepslate_tile_slab"])
    if not str(p["material"]).replace("_stairs", "_slab").endswith("_slab"):
        die("cannot derive slab id from material", {"material": "minecraft:spruce_stairs"})
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,80,100]"})

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
            {"example": '{"origin":[100,80,100],"width":9,"depth":11,"profile":"gentle"}'})
    validate(p)
    write_out(build(p), a.out)

if __name__ == "__main__":
    main()
