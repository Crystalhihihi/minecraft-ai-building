#!/usr/bin/env python3
"""interior_rooms.py — furnished-room generator (房间陈设模板).

Fills a rectangular INTERIOR (walls/floor/ceiling already built) with a
canonical furniture set per room type. The AI does NOT free-style: every
piece comes from patterns/furniture.py (same recipes, same derived
direction states) and the generator itself enforces

- every piece flush against a wall (or the dining table centred),
- no two pieces overlapping, nothing outside the room rect,
- nothing on a door-approach cell (the cell just inside each doorway),
- a connected >=1-wide walkway: from every door you can walk (4-neighbour,
  one cell wide, two cells high) to the approach cells of every required
  piece.

If a piece cannot be placed without breaking those rules it is slid along
its wall through its candidate list; required pieces that fit nowhere abort
with a legal-values error, optional pieces are dropped.

Coordinates: the room interior is cells [0..width-1] x [0..depth-1] with
walls OUTSIDE that rect (north wall at z=-1, south at z=depth, west at
x=-1, east at x=width). origin = the room's min-corner interior cell,
y = the layer furniture stands in (one above the floor blocks).

Output: {"blocks":[{x,y,z,block}...]} compatible with set_blocks_from_file.

Usage:
  python interior_rooms.py --params '{"room":"bedroom","origin":[100,65,100],"width":5,"depth":5}' [--out bedroom.json]
  python interior_rooms.py --params '{"room":"living","origin":[100,65,120],"width":6,"depth":6,"doors":[{"wall":"south","at":3}],"fireplace":true}'
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import furniture                       # patterns/furniture.py — piece canon
from roof_common import die, write_out

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
WALL_IN = {"north": "south", "south": "north",
           "west": "east", "east": "west"}          # wall -> facing into room

ROOMS = ("bedroom", "kitchen", "living", "dining", "study", "corridor")
# (min width, min depth) of the interior rect, any rotation allowed
MIN_SIZE = {"bedroom": (4, 4), "kitchen": (4, 4), "living": (5, 5),
            "dining": (4, 5), "study": (4, 4), "corridor": (1, 3)}

DEFAULTS = {
    "origin": [0, 65, 0],
    "room": "bedroom",
    "width": 5,                        # interior cells along x, 1-16
    "depth": 5,                        # interior cells along z, 1-16
    "doors": [],                       # [{"wall":"south","at":2}]; [] = auto
    "bed_color": "red",                # bedroom
    "storage": "dresser",              # bedroom: dresser(抽屉柜) | cabinet(衣柜)
    "fireplace": False,                # living: True = fireplace else lamp
    "wood": "spruce",                  # stair wood for sofa/counter/desk
}

_placed = {}                            # name -> (x, z, facing, cols), filled
                                        # as assemble() accepts pieces; recipe
                                        # candidate fns read it (bed->nightstand)


# ------------------------------------------------------------- geometry ----
def wall_len(wall, W, D):
    return W if wall in ("north", "south") else D


def approach_cell(wall, k, W, D):
    """The interior cell just inside a doorway on `wall` at offset k."""
    return {"north": (k, 0), "south": (k, D - 1),
            "west": (0, k), "east": (W - 1, k)}[wall]


def flush(wall, k, W, D, length=1):
    """(origin_xz, facing) for a piece `length` wide flush against `wall`,
    spanning cells k .. k+length-1 along the wall. furniture.build extends
    a piece along RIGHT[facing] (which may run AGAINST the wall axis), so
    the origin cell is shifted to keep the span anchored at k."""
    (ax, az), facing = approach_cell(wall, k, W, D), WALL_IN[wall]
    rx, rz = DIRS[furniture.RIGHT[facing]]
    wx, wz = (1, 0) if wall in ("north", "south") else (0, 1)
    if (rx, rz) != (wx, wz):
        ax += wx * (length - 1)
        az += wz * (length - 1)
    return (ax, az), facing


def bed_flush(wall, k, W, D):
    """Bed with its HEAD against `wall`: origin = foot cell (one cell in),
    facing = foot->head = toward the wall."""
    (ax, az), inward = approach_cell(wall, k, W, D), WALL_IN[wall]
    dx, dz = DIRS[inward]
    return (ax + dx, az + dz), wall


def clear_cells(mode, cols, facing, W, D):
    """Cells that must stay free (walkable) for a placed piece."""
    out = set()
    fx, fz = DIRS[facing]
    bx, bz = DIRS[OPP[facing]]
    for cx, cz in cols:
        if mode == "front":
            targets = [(cx + fx, cz + fz)]
        elif mode == "back":
            targets = [(cx + bx, cz + bz)]
        elif mode == "bed":
            # front of the FOOT cell + its two side cells (the head side may
            # legitimately be taken by a nightstand, so it is exempt)
            hx, hz = cx + fx, cz + fz          # foot's neighbour toward head
            if (hx, hz) not in cols:           # only the FOOT cell contributes
                continue
            targets = [(cx - fx, cz - fz),     # beyond the foot
                       (cx + fz, cz + fx),     # sides of the foot cell
                       (cx - fz, cz - fx)]
        elif mode == "ring":
            targets = [(cx + dx, cz + dz) for dx, dz in DIRS.values()]
        else:  # "none" — decorative, no dedicated approach
            targets = []
        for t in targets:
            if t not in cols and 0 <= t[0] < W and 0 <= t[1] < D:
                out.add(t)
    return out


def connected(occ, need, W, D):
    """True if every cell in `need` lies in one 4-neighbour component of
    the free cells (not occupied by furniture columns)."""
    free = {(x, z) for x in range(W) for z in range(D)} - occ
    start = next(iter(need), None)
    if start is None or start not in free:
        return not need
    seen = {start}
    stack = [start]
    while stack:
        cx, cz = stack.pop()
        for dx, dz in DIRS.values():
            n = (cx + dx, cz + dz)
            if n in free and n not in seen:
                seen.add(n)
                stack.append(n)
    return need <= seen


# ---------------------------------------------------------------- engine ----
def assemble(p, steps, doors, W, D):
    ox, oy, oz = p["origin"]
    door_cells = {approach_cell(d["wall"], d["at"], W, D) for d in doors}
    occ = set()                    # blocking columns (blocks at y+0/y+1)
    must_reach = set(door_cells)   # walkway graph must keep these connected
    blocks = []

    for st in steps:
        ok = False
        for (x, z), facing in st["cands"]():
            try:
                pb = furniture.build({"piece": st["piece"],
                                      "origin": [ox + x, oy, oz + z],
                                      "facing": facing, **st.get("extra", {})})
            except ValueError:
                continue
            cols = {(b["x"] - ox, b["z"] - oz) for b in pb if b["y"] - oy <= 1}
            if any(not (0 <= cx < W and 0 <= cz < D) for cx, cz in cols):
                continue                       # spills out of the room
            if cols & occ or cols & door_cells:
                continue                       # overlaps furniture / doorway
            clear = clear_cells(st.get("clear", "front"), cols, facing, W, D)
            if clear & occ:
                continue                       # approach blocked by furniture
            need = must_reach | clear
            if not connected(occ | cols, need, W, D):
                continue                       # would sever the walkway
            occ |= cols
            blocks.extend(pb)
            _placed[st["name"]] = (x, z, facing, cols)
            if not st.get("optional"):
                must_reach |= clear
            ok = True
            break
        if not ok and not st.get("optional"):
            die("room %s: required piece %r fits nowhere in a %dx%d interior "
                "(enlarge the room or move the door)"
                % (p["room"], st["name"], W, D),
                {"min_size": MIN_SIZE[p["room"]],
                 "doc": "patterns/interior_layout.md"})
    return blocks


def step(name, piece, cands, extra=None, clear="front", optional=False):
    return {"name": name, "piece": piece, "cands": cands,
            "extra": extra or {}, "clear": clear, "optional": optional}


def main_wall(doors, prefs=("north", "east", "west", "south")):
    """First preference wall that has no door on it."""
    used = {d["wall"] for d in doors}
    for w in prefs:
        if w not in used:
            return w
    return prefs[0]


def slide(wall, length, W, D, centre=True):
    """Candidate offsets for a `length`-wide piece along `wall`, centred
    first then outward."""
    L = wall_len(wall, W, D)
    if length > L:
        return []
    ks = list(range(0, L - length + 1))
    if centre:
        ks.sort(key=lambda k: abs(k - (L - length) / 2))
    return ks


def side_walls(wall):
    return {"north": ("west", "east"), "south": ("east", "west"),
            "west": ("south", "north"), "east": ("north", "south")}[wall]


# ---------------------------------------------------------------- recipes ----
def r_bedroom(p, W, D, doors):
    wall = main_wall(doors)
    sw1, sw2 = side_walls(wall)
    storage = p.get("storage", "dresser")

    def bed_cands():
        return [bed_flush(wall, k, W, D) for k in slide(wall, 1, W, D)]

    def night_cands():  # nightstand beside the bed's head, on the wall row
        if "bed" not in _placed:
            return []
        bx, bz, bf, _ = _placed["bed"]
        hx, hz = bx + DIRS[bf][0], bz + DIRS[bf][1]      # head cell
        rx, rz = DIRS[{"north": "west", "south": "east",
                       "east": "north", "west": "south"}[bf]]
        return [((hx + rx * s, hz + rz * s), WALL_IN[wall]) for s in (1, -1)]

    def store_cands():
        out = []
        for w in (sw1, sw2, OPP[wall]):
            for k in slide(w, 2, W, D):
                out.append(flush(w, k, W, D, 2))
        return out

    def lamp_cands():
        w = OPP[wall]
        return [(approach_cell(w, wall_len(w, W, D) - 1, W, D), WALL_IN[w]),
                (approach_cell(w, 0, W, D), WALL_IN[w])]

    return [
        step("bed", "bed", bed_cands, {"color": p.get("bed_color", "red")},
             clear="bed"),
        step("nightstand", "table", night_cands, {"wood": "oak", "width": 1},
             optional=True),
        step("storage", storage, store_cands, {"width": 2, "height": 3}),
        step("lamp", "lamp_post", lamp_cands, {"height": 2},
             clear="none", optional=True),
    ]


def r_kitchen(p, W, D, doors):
    wall = main_wall(doors)
    L = max(2, min(4, wall_len(wall, W, D) - 1))
    mat = "minecraft:%s_stairs" % p.get("wood", "spruce")
    sw1, sw2 = side_walls(wall)

    def counter_cands():
        return [flush(wall, k, W, D, L) for k in slide(wall, L, W, D)]

    def cabinet_cands():
        out = []
        for w in (sw1, sw2, OPP[wall]):
            for k in slide(w, 2, W, D):
                out.append(flush(w, k, W, D, 2))
        return out

    return [
        step("counter", "kitchen_counter", counter_cands,
             {"material": mat, "length": L}),
        step("cabinet", "cabinet", cabinet_cands, {"width": 2, "height": 2}),
    ]


def r_living(p, W, D, doors):
    wall = main_wall(doors)
    L = max(2, min(4, wall_len(wall, W, D) - 2))
    mat = "minecraft:%s_stairs" % p.get("wood", "spruce")
    sw1, sw2 = side_walls(wall)
    use_fire = bool(p.get("fireplace"))

    def sofa_cands():
        return [flush(wall, k, W, D, L) for k in slide(wall, L, W, D)]

    def table_cands():  # coffee table two rows in front of the sofa
        if "sofa" not in _placed:
            return []
        sx, sz, sf, cols = _placed["sofa"]
        fx, fz = DIRS[sf]
        if sf in ("north", "south"):
            m = sorted(c[0] for c in cols)[len(cols) // 2]
            return [((m, sz + fz * 2), sf)]
        m = sorted(c[1] for c in cols)[len(cols) // 2]
        return [((sx + fx * 2, m), sf)]

    def shelf_cands():
        out = []
        for w in (sw1, sw2):
            for k in slide(w, 2, W, D):
                out.append(flush(w, k, W, D, 2))
        return out

    def hearth_cands():
        w = OPP[wall]
        if use_fire:
            return [flush(w, k, W, D, 3) for k in slide(w, 3, W, D)]
        return [(approach_cell(w, 0, W, D), WALL_IN[w]),
                (approach_cell(w, wall_len(w, W, D) - 1, W, D), WALL_IN[w])]

    return [
        step("sofa", "sofa", sofa_cands, {"material": mat, "length": L}),
        step("coffee_table", "table", table_cands, {"wood": "oak", "width": 2},
             clear="ring", optional=True),
        step("bookshelf", "bookshelf", shelf_cands, {"width": 2, "height": 2}),
        step("hearth", "fireplace" if use_fire else "lamp_post", hearth_cands,
             {"chimney": 0} if use_fire else {"height": 2},
             clear="front" if use_fire else "none",
             optional=not use_fire),
    ]


def r_dining(p, W, D, doors):
    tw = max(2, min(4, W - 2))
    tz = D // 2
    t0 = (W - tw) // 2
    chair_offs = [0] if tw < 3 else [0, tw - 1]   # armrest signs need 1 gap

    def chair_cands(side):
        facing = "south" if side == -1 else "north"
        return [((t0 + i, tz + side), facing) for i in chair_offs]

    def lamp_cands():
        return [((0, 0), "south"), ((W - 1, D - 1), "north"),
                ((W - 1, 0), "south"), ((0, D - 1), "north")]

    return [
        step("table", "table", lambda: [((t0 + tw - 1, tz), "south")],
             {"wood": "oak", "width": tw}, clear="none"),
        step("chair_a", "chair", lambda: chair_cands(-1),
             {"material": "minecraft:oak_stairs"}, clear="back"),
        step("chair_b", "chair", lambda: chair_cands(1),
             {"material": "minecraft:oak_stairs"}, clear="back"),
        step("lamp", "lamp_post", lamp_cands, {"height": 2},
             clear="none", optional=True),
    ]


def r_study(p, W, D, doors):
    wall = main_wall(doors)
    L = max(2, min(3, wall_len(wall, W, D) - 1))
    mat = "minecraft:%s_stairs" % p.get("wood", "spruce")
    sw1, sw2 = side_walls(wall)

    def desk_cands():
        return [flush(wall, k, W, D, L) for k in slide(wall, L, W, D)]

    def shelf_cands():
        out = []
        for w in (sw1, sw2, OPP[wall]):
            for k in slide(w, 2, W, D):
                out.append(flush(w, k, W, D, 2))
        return out

    def lamp_cands():
        w = OPP[wall]
        return [(approach_cell(w, 0, W, D), WALL_IN[w]),
                (approach_cell(w, wall_len(w, W, D) - 1, W, D), WALL_IN[w])]

    return [
        step("desk", "desk", desk_cands, {"material": mat, "width": L}),
        step("bookshelf", "bookshelf", shelf_cands, {"width": 2, "height": 3}),
        step("lamp", "lamp_post", lamp_cands, {"height": 2},
             clear="none", optional=True),
    ]


def r_corridor(p, W, D, doors):
    long_x = W >= D
    L = W if long_x else D
    if (D if long_x else W) < 2 or L < 4:
        return []                       # 1-wide or tiny corridor: bare, see .md
    if long_x:
        lamp_pos = ((L // 3, 0), "south")
        pot_pos = ((2 * L // 3, D - 1), "north")
    else:
        lamp_pos = ((0, L // 3), "east")
        pot_pos = ((W - 1, 2 * L // 3), "west")
    return [
        step("lamp", "lamp_post", lambda: [lamp_pos], {"height": 2},
             clear="none"),
        step("plant", "flower_pot", lambda: [pot_pos],
             {"pedestal": True}, clear="none", optional=True),
    ]


RECIPES = {"bedroom": r_bedroom, "kitchen": r_kitchen, "living": r_living,
           "dining": r_dining, "study": r_study, "corridor": r_corridor}


def default_doors(p, W, D):
    if p["room"] == "corridor":
        if W >= D:
            return [{"wall": "west", "at": D // 2},
                    {"wall": "east", "at": D // 2}]
        return [{"wall": "north", "at": W // 2},
                {"wall": "south", "at": W // 2}]
    return [{"wall": "south", "at": W // 2}]


# ------------------------------------------------------------------ glue ----
def validate(p):
    if p["room"] not in ROOMS:
        die("room must be one of %s" % (ROOMS,), {"room": list(ROOMS)})
    try:
        W, D = int(p["width"]), int(p["depth"])
    except (TypeError, ValueError):
        die("width/depth must be ints", {"width": "1-16", "depth": "1-16"})
    if not (1 <= W <= 16 and 1 <= D <= 16):
        die("width/depth out of range", {"width": "1-16", "depth": "1-16"})
    mw, md = MIN_SIZE[p["room"]]
    if not ((W >= mw and D >= md) or (W >= md and D >= mw)):
        die("%s interior too small: need at least %dx%d (any rotation); "
            "got %dx%d" % (p["room"], mw, md, W, D),
            {"min_size": [mw, md], "doc": "patterns/interior_layout.md"})
    if p.get("storage", "dresser") not in ("dresser", "cabinet"):
        die("storage must be dresser(抽屉柜) or cabinet(衣柜)",
            {"storage": ["dresser", "cabinet"]})
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,65,100]"})
    for d in p.get("doors") or []:
        if d.get("wall") not in DIRS:
            die("door wall must be one of north/south/east/west",
                {"doors": [{"wall": "south", "at": 2}]})
        try:
            at = int(d.get("at"))
        except (TypeError, ValueError):
            die("door at must be an int offset along the wall",
                {"doors": [{"wall": "south", "at": 2}]})
        if not 0 <= at < wall_len(d["wall"], W, D):
            die("door at=%d outside wall %s (len %d)"
                % (at, d["wall"], wall_len(d["wall"], W, D)),
                {"at": "0..%d" % (wall_len(d["wall"], W, D) - 1)})


def build(p):
    global _placed
    W, D = int(p["width"]), int(p["depth"])
    doors = list(p.get("doors") or []) or default_doors(p, W, D)
    _placed = {}
    return assemble(p, RECIPES[p["room"]](p, W, D, doors), doors, W, D)


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
            {"example": '{"room":"bedroom","origin":[100,65,100],"width":5,"depth":5}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
