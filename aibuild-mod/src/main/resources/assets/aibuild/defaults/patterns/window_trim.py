#!/usr/bin/env python3
"""window_trim.py — window surround v2 (窗套+纵深细节) around an opening.

V1 emitted a flat decorative ring (side jambs + header + sill rows) and got
called "纸糊" (flat). V2 keeps the ring and adds the cheap-depth moves from
docs/research/detail-techniques.md §2, each an optional switch:
  recess     glass set `recess` cells INTO the wall (0-2, default 1) — the
             cheapest depth there is (玻璃内凹 1 格, §2.2)
  sill       protruding ledge under the opening (bottom slab, or upside-down
             stair when sill_material is *_stairs; §2.3.1)
  shutters   open trapdoors standing in the wall cells flanking the opening,
             hinge toward the window (合页朝窗、打开态贴墙, §2.3.3)
  flowerbox  grass soil row + trapdoor wrap + flowers under the window (the
             田园 upgrade of the sill, §2.3.2; overrides the sill ledge cells)
  lintel     cap row above the opening (窗楣, §2.3.4)
Default combo = recess + sill. All V1 params (projection / corner_material /
sill_material ...) are UNTOUCHED — V1 param sets still run; pass
glass_material="" to go back to the V1 trim-only output.

projection=0 puts the ring in the wall plane (replaces wall blocks flanking
the opening); projection=1 hangs it one block OUT of the wall face. When a
protruding piece (sill/flowerbox/lintel) lands on a ring cell (projection=1),
the piece wins. All direction states (stair facing/half, trapdoor
facing/open) are DERIVED by the script — never hand-edit them in the output
(禁止手改方向状态). Output: {"blocks":[...]}.

Usage:
  python window_trim.py --params '{"origin":[100,70,100],"width":2,"height":3,"facing":"south"}' [--out t.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out  # noqa: E402

DEFAULTS = {
    "origin": [0, 64, 0],               # [x,y,z] bottom-LEFT cell of the window OPENING, seen from outside
    "width": 2,                         # opening width
    "height": 3,                        # opening height
    "facing": "south",                  # outward direction of the wall face
    "projection": 1,                    # 0 = in the wall plane, 1 = one block out of the face
    "material": "minecraft:dark_oak_planks",
    "corner_material": "",              # e.g. "minecraft:smooth_stone": the 4 ring corners (角件)
    "sill_material": "",                # V1: ring bottom row override; V2: also the sill-ledge material when set
    # ---- V2 switches (default combo = recess + sill) ----
    "recess": 1,                        # glass depth INTO the wall, 0-2 (0 = flush — the 反例 look, curtain walls only)
    "glass_material": "minecraft:glass_pane",  # "" = no glass (V1 trim-only), "minecraft:air" = unglazed slit (carves)
    "sill": True,                       # protruding ledge under the opening
    "shutters": False,                  # open trapdoors in the wall cells flanking the opening
    "flowerbox": False,                 # grass+trapdoor+flowers under the window (overrides the sill ledge)
    "lintel": False,                    # cap row above the opening
    "lintel_material": "",              # "" = minecraft:stone_brick_slab
    "trapdoor_material": "minecraft:spruce_trapdoor",  # shutters + flowerbox wrap
    "flower_material": "minecraft:poppy"
}

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
DIR_NAME = {v: k for k, v in DIRS.items()}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}

def ledge_block(mat, facing):
    """Protruding sill/lintel piece: *_slab -> bottom slab, *_stairs ->
    upside-down stair facing out of the wall, anything else stays plain."""
    if mat.endswith("_slab"):
        return mat + "[type=bottom]"
    if mat.endswith("_stairs"):
        return mat + "[facing=%s,half=top]" % facing
    return mat

def trapdoor_panel(mat, facing):
    """Open trapdoor standing vertically on the `facing`-side face of its
    cell (合页在 facing 侧, 打开态贴到该侧墙面)."""
    return "%s[facing=%s,half=bottom,open=true]" % (mat, facing)

def build(p):
    ox, oy, oz = p["origin"]
    w, h = int(p["width"]), int(p["height"])
    facing = p["facing"]
    if facing not in DIRS:
        die("facing must be one of %s" % (tuple(DIRS),), {"facing": list(DIRS)})
    dx, dz = DIRS[facing]
    ux, uz = (1, 0) if facing in ("south", "north") else (0, 1)  # along-wall axis
    proj = max(0, min(1, int(p["projection"])))
    recess = max(0, min(2, int(p["recess"])))
    mat, corner, sillm = p["material"], p["corner_material"], p["sill_material"]
    glass = p["glass_material"]
    on = {k: bool(p[k]) for k in ("sill", "shutters", "flowerbox", "lintel")}
    trap, flower = p["trapdoor_material"], p["flower_material"]
    lintelm = p["lintel_material"] or "minecraft:stone_brick_slab"
    sill_mat = sillm or "minecraft:stone_brick_slab"
    cells = {}

    def put(u, v, r, block):
        """u along the wall (0..w-1 = the opening), v up from the opening
        bottom, r depth OUT of the wall face (negative = into the wall)."""
        cells[(ox + ux * u + dx * r, oy + v, oz + uz * u + dz * r)] = block

    def ring_block(u, v):
        is_corner = (u in (-1, w)) and (v in (-1, h))
        if is_corner and corner:
            return corner
        if v == -1 and sillm:
            s = sillm
            return s + "[type=bottom]" if s.endswith("_slab") else s
        return mat

    # ---- the V1 ring: jambs at u=-1/w, header at v=h, sill row at v=-1,
    # spanning u in [-1, w], v in [-1, h], in the ring plane r=proj ---------
    for v in range(-1, h + 1):
        for u in (-1, w):
            put(u, v, proj, ring_block(u, v))
    for u in range(0, w):
        put(u, h, proj, ring_block(u, h))     # header row
        put(u, -1, proj, ring_block(u, -1))   # sill row

    # ---- recess: glass set INTO the wall (§2.2, 成本最低纵深) -------------
    for u in range(0, w):
        for v in range(0, h):
            for r in range(1, recess):
                put(u, v, -r, "minecraft:air")   # recess=2: open the tunnel
            if glass:
                put(u, v, -recess, glass)

    # ---- sill ledge: out of the face under the opening (§2.3.1) -----------
    # (lands on the ring bottom row when projection=1 — the ledge wins;
    # flowerbox is the sill's upgrade and replaces it)
    if on["sill"] and not on["flowerbox"]:
        for u in range(-1, w + 1):
            put(u, -1, 1, ledge_block(sill_mat, facing))

    # ---- lintel: cap row above the opening (§2.3.4) -----------------------
    if on["lintel"]:
        for u in range(-1, w + 1):
            put(u, h, 1, ledge_block(lintelm, facing))

    # ---- shutters: open trapdoors in the WALL PLANE flanking the opening,
    # hinge toward the window (合页朝窗), panel flush with the facade (§2.3.3)
    if on["shutters"]:
        left = DIR_NAME[(ux, uz)]        # from u=-1 the window lies at +u
        right = DIR_NAME[(-ux, -uz)]
        for v in range(0, h):
            put(-1, v, 0, trapdoor_panel(trap, left))
            put(w, v, 0, trapdoor_panel(trap, right))

    # ---- flowerbox: soil row out of the face + trapdoor wrap + flowers
    # (§2.3.2; the soil row covers the sill-ledge cells) --------------------
    if on["flowerbox"]:
        back = OPP[facing]                       # panel flat on the soil face
        left, right = DIR_NAME[(ux, uz)], DIR_NAME[(-ux, -uz)]
        for u in range(0, w):
            put(u, -1, 1, "minecraft:grass_block")
            put(u, -1, 2, trapdoor_panel(trap, back))    # front wrap
            put(u, 0, 1, flower)                         # flowers on the soil
        put(-1, -1, 1, trapdoor_panel(trap, left))       # left end wrap
        put(w, -1, 1, trapdoor_panel(trap, right))       # right end wrap

    return [{"x": x, "y": y, "z": z, "block": b}
            for (x, y, z), b in sorted(cells.items())]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    p = dict(DEFAULTS)
    try:
        p.update(json.loads(a.params) if a.params.strip() else {})
    except json.JSONDecodeError as e:
        die("--params is not valid JSON: %s" % e,
            {"example": '{"facing":"south","width":2,"height":3}'})
    write_out(build(p), a.out)

if __name__ == "__main__":
    main()
