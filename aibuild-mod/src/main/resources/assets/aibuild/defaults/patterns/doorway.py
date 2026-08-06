#!/usr/bin/env python3
"""doorway.py — parametric doorway (门口) generator: the full 7-layer human
entrance, not a bare vanilla door block.

Layers (组合顺序 per docs/research/detail-techniques.md §1.8):
  1. opening carved into the wall (explicit minecraft:air cells, force-carve
     like dormer's window tunnel — the hole cuts INTO the wall, it is not
     pasted onto it)
  2. recess niche (recess 0-2: the door leaf sits that many cells deep)
  3. frame ring around the opening (深框浅墙铁律: default frame is darker
     than a typical wall). Three construction modes by material suffix:
       *_trapdoor -> 活板门包框: open trapdoors flat on the wall face around
                     the opening (7 个 for 1x2: 左右各 2 + 上 3) + solid side
                     posts in the wall plane (gamerempire 配方)
       *_stairs   -> 楼梯描边: jambs face into the opening, lintel/arch band
                     is upside-down stairs (倒置楼梯压顶)
       else       -> solid inlaid ring in the wall plane
  4. lintel / arch band above the opening. arch: stepped half-arch,
     rise = ceil(width/2) (拱高=拱宽一半), sampled on a semicircle at cell
     centers so it is mirrored by construction (严禁徒手画拱); top-centre
     band cell(s) swap to `keystone` material (拱顶换料) for width>=3.
  5. door leaves (vanilla *_door; width>=2 = double doors with explicitly
     mirrored hinges — hinge sides are set per leaf, never two identical
     placements). odd width: single centre leaf + full adjacent pairs
     flanking it (width 3 -> centre leaf only).
  6. stoop: one stair row in front of the door, tread 1, span = opening +
     frame (地基抬高一级就做一步).
  7. canopy awning (雨棚): slab (or closed trapdoor when frame is a
     trapdoor) row, projection 1, span = opening + frame, one lantern
     hanging under each end.
  8. side decor: symmetric lantern posts (fence/wall post + sitting lantern)
     one cell beyond the frame.

ALL direction states (stair facing/half, trapdoor hinge/open, door
facing/hinge, lantern hanging) are DERIVED by the script from origin+params
(canonical frame: front faces south, u -> +x = viewer's right, v -> up,
w -> -z into the wall; rotated via roof_common.FACING_ROT). Never hand-edit
them in the output; change params and re-run (禁止手改方向状态).

Output: {"blocks":[{x,y,z,block}...]} (set_blocks_from_file compatible; air
cells carve via place_air).

Usage:
  python doorway.py --params '{"origin":[100,64,100],"facing":"south"}' [--out d.json]
  python doorway.py --params '{"origin":[100,64,120],"style":"arch","width":3,"height":3,"frame":"minecraft:stone_brick_stairs"}'
"""
import argparse, json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import Builder, FACING_ROT, die, slab, stair, write_out

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] bottom-LEFT cell of the opening (seen from outside), y = sill layer
    "facing": "south",             # direction the doorway faces (outward)
    "width": 1,                    # opening width 1-5; 1-2 rect 民居, >=3 建议 arch
    "height": 2,                   # opening leg height 2-4 (arch: 拱下直段高, 总高=height+ceil(width/2))
    "style": "rect",               # rect 直门洞 | arch 拱形门洞
    "frame": "minecraft:dark_oak_stairs",  # frame material (浅墙深框: default darker than the wall)
    "recess": 1,                   # recess niche depth 0-2 (door sits this deep); wall should be >= recess+1 thick
    "canopy": True,                # small awning above the frame (slab / closed trapdoor), projection 1
    "steps": True,                 # one stoop stair row in front (tread 1)
    "door_block": "minecraft:oak_door",    # door leaf id, or "none" = open hole only
    "side_decor": True,            # symmetric lantern posts beside the door
    "keystone": "minecraft:chiseled_stone_bricks",  # arch apex swap material; "" = off
}

STYLES = ("rect", "arch")
FACINGS = ("north", "south", "east", "west")
_WOODS = ("dark_oak", "pale_oak", "oak", "spruce", "birch", "jungle",
          "acacia", "mangrove", "cherry", "bamboo", "crimson", "warped")
# full blocks with no stair/slab/wall derivative — fall back instead
_NOSTEP = ("smooth_stone", "smooth_quartz", "quartz_block", "glass",
           "obsidian", "bedrock", "gold_block")


def rhu(v):
    """Round half up (deterministic). Same idiom as buttress.py."""
    return int(math.floor(v + 0.5))


def _base(mat):
    n = str(mat).split(":")[-1]
    for suf in ("_stairs", "_slab", "_trapdoor", "_planks", "_log"):
        if n.endswith(suf):
            return n[:-len(suf)]
    return n


def _derived(mat, kind, fallback):
    """Same-family derivative: kind = stairs | slab | fence | log.
    fence: wood -> *_fence, stone-ish -> *_wall (lantern post).
    log:   wood -> *_log (trapdoor-wrap side posts, gamerempire 配方)."""
    base = _base(mat)
    if base.endswith("_bricks"):
        base = base[:-len("_bricks")] + "_brick"      # stone_bricks -> stone_brick
    wood = next((wd for wd in _WOODS if base == wd), None)
    if base in _NOSTEP:
        return fallback
    if kind == "log":
        return "minecraft:%s_log" % wood if wood else fallback
    if kind == "fence":
        return "minecraft:%s_fence" % wood if wood else "minecraft:%s_wall" % base
    return "minecraft:%s_%s" % (base, kind)           # stairs | slab


def build(p):
    w, h = int(p["width"]), int(p["height"])
    style = p["style"]
    frame = str(p["frame"])
    recess = int(p["recess"])
    keystone = str(p["keystone"])
    rot, fmap = FACING_ROT[p["facing"]]
    b = Builder(rot=rot, fmap=fmap)

    # arch profile: extra opening cells above the rect top, per column.
    # Semicircle radius = width/2 sampled at cell centres -> mirrored by
    # construction (拱高=拱宽一半; 左右对称是铁律, 绝不徒手画).
    profile = [0] * w
    if style == "arch":
        r = w / 2.0
        cx = w / 2.0
        for u in range(w):
            du = abs(u + 0.5 - cx)
            profile[u] = max(1, rhu(math.sqrt(max(0.0, r * r - du * du))))
    maxp = max(profile)
    ymax = h + maxp                    # top of the frame band (rect: maxp=0)

    # ---- 1+2. carve the opening tunnel (face plane + recess depth) --------
    opening = set()                    # (u,y) cells in the face plane
    for u in range(w):
        for y in range(h + profile[u]):
            opening.add((u, y))
            for z in range(0, -recess - 1, -1):
                b.carve(u, y, z, force=True)

    # ---- 3+4. frame outline: 4-neighbour ring around the opening ----------
    # (rect -> Π jambs+lintel; arch -> jambs rising along the arch legs +
    # stepped voussoir band), plus corner caps closing the frame corners.
    ring = set()
    for (u, y) in opening:
        for du, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (u + du, y + dy)
            if q not in opening and -1 <= q[0] <= w and 0 <= q[1] <= ymax:
                ring.add(q)
    ring.add((-1, h + profile[0]))     # corner caps (symmetric by profile)
    ring.add((w, h + profile[0]))
    keystone_cells = set()
    if style == "arch" and keystone and w >= 3:
        keystone_cells = {(u, h + maxp) for u in range(w) if profile[u] == maxp}

    td_mode = frame.endswith("_trapdoor")
    st_mode = frame.endswith("_stairs")
    if td_mode:
        # 活板门包框: open trapdoors flat on the wall face (hinge to wall),
        # solid side posts in the wall plane (oak_log per the recipe).
        post = _derived(frame, "log", "minecraft:oak_log")
        for (u, y) in sorted(ring):
            if (u, y) in keystone_cells:
                b.put(u, y, 0, keystone)          # apex swaps to stone, in-plane
                continue                          # (a trapdoor there would float)
            if p["canopy"] and style == "rect" and y == h and u in (-1, w):
                continue                          # canopy lanterns take the corners
            b.put(u, y, 1, "%s[facing=north,half=bottom,open=true]" % frame)
        for u in (-1, w):
            for y in range(h):
                b.put(u, y, 0, post)
    elif st_mode:
        for (u, y) in sorted(ring):
            if (u, y) in keystone_cells:
                b.put(u, y, 0, keystone)
            elif u == -1:
                b.put(u, y, 0, stair(frame, "east"))       # jamb faces into opening
            elif u == w:
                b.put(u, y, 0, stair(frame, "west"))
            else:
                b.put(u, y, 0, stair(frame, "south", half="top"))  # 倒置楼梯压顶
    else:
        for (u, y) in sorted(ring):
            b.put(u, y, 0, keystone if (u, y) in keystone_cells else frame)

    # ---- 5. door leaves (双开门铰链显式镜像, wiki/forum 机制) ---------------
    door = str(p["door_block"])
    if door != "none":
        zd = -recess
        if w == 1:
            leaves = [(0, "left")]
        elif w % 2 == 0:
            leaves = [(u, "right" if u % 2 == 0 else "left") for u in range(w)]
        else:
            c = w // 2
            leaves = [(c, "left")]
            u = c - 2                            # full adjacent pairs flanking
            while u >= 0:
                leaves += [(u, "right"), (u + 1, "left")]
                u -= 2
            u = c + 1
            while u + 1 <= w - 1:
                leaves += [(u, "right"), (u + 1, "left")]
                u += 2
            leaves.sort()
        for u, hinge in leaves:
            b.put(u, 0, zd, "%s[facing=south,half=lower,hinge=%s]" % (door, hinge))
            b.put(u, 1, zd, "%s[facing=south,half=upper,hinge=%s]" % (door, hinge))

    # ---- 6. stoop: one stair row, tread 1, span = opening + frame ---------
    if p["steps"]:
        sm = _derived(frame, "stairs", "minecraft:stone_brick_stairs")
        for u in range(-1, w + 1):
            b.put(u, -1, 1, stair(sm, "south"))  # riser faces the visitor

    # ---- 7. canopy awning: projection 1, span = opening + frame -----------
    if p["canopy"]:
        cy = ymax + 1
        if td_mode:
            for u in range(-1, w + 1):           # closed trapdoor panels
                b.put(u, cy, 1, "%s[facing=north,half=top,open=false]" % frame)
        else:
            cm = _derived(frame, "slab", "minecraft:spruce_slab")
            for u in range(-1, w + 1):
                b.put(u, cy, 1, slab(cm, "bottom"))
        for u in (-1, w):                        # 檐下两端各挂一灯笼
            b.put(u, cy - 1, 1, "minecraft:lantern[hanging=true]")

    # ---- 8. side decor: symmetric lantern posts one cell beyond the frame -
    if p["side_decor"]:
        post = _derived(frame, "fence", "minecraft:dark_oak_fence")
        for u in (-2, w + 1):
            b.put(u, -1, 1, post)
            b.put(u, 0, 1, "minecraft:lantern[hanging=false]")

    return b.emit(p["origin"])


def validate(p):
    if p["facing"] not in FACINGS:
        die("facing must be one of %s" % (FACINGS,), {"facing": list(FACINGS)})
    if p["style"] not in STYLES:
        die("style must be one of %s" % (STYLES,), {"style": list(STYLES)})
    try:
        w, h, recess = int(p["width"]), int(p["height"]), int(p["recess"])
    except (TypeError, ValueError):
        die("width/height/recess must be ints", {"width": "1-5", "height": "2-4", "recess": "0-2"})
    if not 1 <= w <= 5:
        die("width %s out of range" % w, {"width": "1-5"})
    if not 2 <= h <= 4:
        die("height %s out of range" % h, {"height": "2-4"})
    if not 0 <= recess <= 2:
        die("recess %s out of range" % recess, {"recess": "0-2"})
    if not str(p["frame"]).strip():
        die("frame must be a block id", {"frame": ["minecraft:dark_oak_stairs",
                                                   "minecraft:stone_brick_stairs",
                                                   "minecraft:oak_trapdoor"]})
    door = str(p["door_block"])
    if door != "none" and not door.endswith("_door"):
        die("door_block must be a *_door id or \"none\"",
            {"door_block": ["minecraft:oak_door", "minecraft:dark_oak_door",
                            "minecraft:iron_door", "none"]})
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,64,100]"})


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
            {"example": '{"origin":[100,64,100],"facing":"south","width":2,"style":"rect"}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
