#!/usr/bin/env python3
"""roof_ornament.py — ridge ornament (屋脊装饰) generator.

THIN generator: emits only the small ornaments sitting ON an existing ridge
line — never the roof itself (先发屋顶再压脊饰). Styles are a hard whitelist
(L4a), 脊饰不只中式:

- chinese:  鸱吻/翘角 (ridge ends: stair pair upturned — bottom stair facing
  outward + upside-down stair stacked on it + slab 台阶 onto the ridge) +
  正脊兽 (small post studs at rhythm positions along the ridge).
- gothic:   finial 尖塔 (post+post+stair tip 收尖) at both ends and the
  midpoint, plus small pinnacles (post + top slab) on the rhythm.
- japanese: 鬼瓦 (ridge ends: wall-post body + slab cap + a half-top stair
  前凸板 protruding one cell past the ridge end, side-attached to the body).
- european: cresting 脊冠 (iron-bars row along the whole ridge) + weathervane
  风向标 at one seed-picked end (fence×2 + standing banner flag + end_rod tip).

Geometry: origin = the FIRST cell of the ridge line, y = ridge TOP surface
layer (the ridge slab row; ornaments start at y+1); axis = ridge direction;
length = ridge length in cells — both must match the roof card's own call
(gable_roof ridge runs the full width+2*overhang along its axis). Rhythm
positions (ends / midpoint / every-2/3 studs) derive from length. ALL facing/
half/rotation states are derived by the script — never hand-edit (禁止手改).

Usage:
  python roof_ornament.py --params '{"origin":[100,84,100],"axis":"x","length":11,"style":"chinese"}' [--out orn.json]
"""
import argparse, json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import Builder, die, require_suffix, slab, stair, write_out

STYLES = ("chinese", "gothic", "japanese", "european")

# post (柱件) derivation: wood stair families taper with fences, stone with walls
WOODS = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove",
         "cherry", "pale_oak", "bamboo", "crimson", "warped")
WALL_OK = ("stone_brick", "mossy_stone_brick", "deepslate_brick",
           "deepslate_tile", "brick", "mud_brick", "cobblestone",
           "mossy_cobblestone", "andesite", "diorite", "granite", "sandstone",
           "red_sandstone", "blackstone", "polished_blackstone", "prismarine",
           "nether_brick", "red_nether_brick", "end_stone_brick", "tuff",
           "tuff_brick", "polished_tuff")

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] 屋脊线起点格;y=脊顶层(脊半砖所在层)
    "axis": "x",                   # 屋脊走向: "x" | "z"
    "length": 9,                   # 3-48, 脊长(格);与屋顶卡脊长一致
    "style": "chinese",            # L4a 风格白名单,无全局通用脊饰
    "material": "minecraft:stone_brick_stairs",  # 鸱吻/尖顶主体;slab/post 由它推导
    "seed": 7
}


def post_id(material):
    """fence for wood families, wall for stone families (收尖小柱)."""
    base = str(material).split(":", 1)[-1].replace("_stairs", "")
    if base in WOODS:
        return "minecraft:%s_fence" % base
    if base in WALL_OK:
        return "minecraft:%s_wall" % base
    return "minecraft:stone_brick_wall"


def build(p):
    ox, oy, oz = [int(v) for v in p["origin"]]
    L = int(p["length"])
    mat = p["material"]
    slb = mat.replace("_stairs", "_slab")
    post = post_id(mat)
    axis = p["axis"]
    rng = random.Random(int(p["seed"]))

    # local frame: ridge along +x, u in 0..L-1; axis=z transposes on emit
    FACING_ROT = {"south": "east", "east": "south", "north": "west", "west": "north"}
    b = Builder(rot=(lambda x, z: (z, x)) if axis == "z" else None,
                fmap=FACING_ROT if axis == "z" else None)
    ENDS = ((0, "west"), (L - 1, "east"))   # (u, 脊端朝外 facing)

    style = p["style"]
    if style == "chinese":
        for u, out in ENDS:                # 鸱吻/翘角: 脊端上翘小结构(楼梯+台阶)
            b.put(u, 1, 0, stair(mat, out))
            b.put(u, 2, 0, stair(mat, out, half="top"))
            b.put(u + (1 if u == 0 else -1), 1, 0, slab(slb, "bottom"))
        u = 2                              # 正脊兽: 节奏小兽柱(seed 控制缺省)
        while u <= L - 3:
            if rng.random() < 0.75:
                b.put(u, 1, 0, post)
            u += 3
    elif style == "gothic":
        tips = {0: "west", L - 1: "east", L // 2: "east"}
        for u, tip in tips.items():        # finial 尖塔: post+post+楼梯收尖
            b.put(u, 1, 0, post)
            b.put(u, 2, 0, post)
            b.put(u, 3, 0, stair(mat, tip))
        off = rng.choice((0, 1))           # 小尖顶: post+顶半砖, 节奏错缝
        for u in range(2 + off, L - 2, 4):
            if u not in tips:
                b.put(u, 1, 0, post)
                b.put(u, 2, 0, slab(slb, "top"))
    elif style == "japanese":
        for u, out in ENDS:                # 鬼瓦: 脊端前凸板(侧贴本体)
            step = 1 if u == 0 else -1
            b.put(u, 1, 0, post)                      # 鬼瓦本体
            b.put(u, 2, 0, slab(slb, "bottom"))       # 压顶
            b.put(u - step, 1, 0, stair(mat, out, half="top"))  # 前凸板
        off = rng.choice((0, 1))           # 脊瓦帽: 节奏半砖
        for u in range(2 + off, L - 2, 2):
            b.put(u, 1, 0, slab(slb, "bottom"))
    else:  # european
        for u in range(L):                 # cresting 脊冠: 铁艺通长一排
            b.put(u, 1, 0, "minecraft:iron_bars")
        u, out = ENDS[rng.choice((0, 1))]  # 风向标: 栅栏+旗+箭头尖
        b.put(u, 2, 0, post)
        rot = {"x": {"west": 4, "east": 12}, "z": {"west": 8, "east": 0}}[axis][out]
        b.put(u, 3, 0, "minecraft:white_banner[rotation=%d]" % rot)
        b.put(u, 4, 0, "minecraft:end_rod[facing=up]")
    return b.emit([ox, oy, oz])


def validate(p):
    if p["style"] not in STYLES:
        die("style must be one of %s (L4a 风格白名单,脊饰不只中式)" % (STYLES,),
            {"style": list(STYLES)})
    if p["axis"] not in ("x", "z"):
        die("axis must be x or z", {"axis": ["x", "z"]})
    try:
        L = int(p["length"])
    except (TypeError, ValueError):
        die("length must be an int", {"length": "3-48"})
    if not 3 <= L <= 48:
        die("length out of range", {"length": "3-48"})
    require_suffix(p, "material", "_stairs",
                   ["minecraft:stone_brick_stairs", "minecraft:dark_oak_stairs",
                    "minecraft:deepslate_tile_stairs"])
    if not str(p["material"]).replace("_stairs", "_slab").endswith("_slab"):
        die("cannot derive slab id from material", {"material": "minecraft:stone_brick_stairs"})
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,84,100]"})


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
            {"example": '{"origin":[100,84,100],"axis":"x","length":11,"style":"gothic"}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
