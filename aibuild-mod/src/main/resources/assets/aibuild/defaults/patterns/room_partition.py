#!/usr/bin/env python3
"""room_partition.py — room partition generator (分房生成器).

Slices a rectangular shell INTERIOR into the demanded rooms and emits one
JSON with three parts:

  1. "blocks": 1-thick full-height partition walls + >=1x2 door openings
     (real door blocks with derived states, or plain air when
     door_material=""),
  2. "rooms": per-room annotations — each entry is directly splat-able into
     patterns/interior_rooms.py params (room/origin/width/depth/doors, world
     frame; the entrance door is included and flagged entrance:true),
  3. "window_hints": advisory facade window positions (one per habitable
     room). NO blocks are emitted for them — 分房先于外墙开窗: the facade
     caller carves windows from these hints, aligning them to rooms.

Guarantees (all checked BEFORE emission; failure -> seeded retry -> die with
reason, never garbage):
  - every room satisfies its interior_rooms min size (any rotation),
  - bedroom/living/study touch an exterior wall (interior_layout.md 采光面),
    and the entrance opens into a public room (living/corridor/dining) when
    one was demanded (动线: 入口 -> 公共 -> 私密),
  - a 2D BFS from the entrance cell reaches every cell of every room
    through the door cells.

Layout search: seeded guillotine (binary-space) cuts; partition lines prefer
the structural grid (wall line at a multiple of `grid` cells from the
interior corner, falling back off-grid in tight shells); door graph is a
spanning tree that attaches private rooms last; best of ATTEMPTS seeded
attempts wins (score: kitchen next to living/dining, bedroom doors off
public rooms, full grid snap). Deterministic: same seed -> same bytes.

Canonical frame: front = south, origin = interior north-west min cell,
y = furniture standing layer (one above the floor blocks) — same convention
as plan_shape/interior_rooms. Rotated to `facing` on emit.

Usage:
  python room_partition.py --params '{"width":9,"depth":11,"rooms":"living:1,kitchen:1,bedroom:2"}' [--out part.json]
"""
import argparse, json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, FACING_ROT

MIN_SIZE = {"bedroom": (4, 4), "kitchen": (4, 4), "living": (5, 5),
            "dining": (4, 5), "study": (4, 4), "corridor": (1, 3)}
MIN_AREA = {r: a * b for r, (a, b) in MIN_SIZE.items()}
PUBLIC = ("living", "corridor", "dining")      # 入口先到的公共房间
NEED_EXT = ("bedroom", "living", "study")      # 必须分到外墙面(采光)
RANK = {"living": 0, "corridor": 0, "dining": 1, "kitchen": 1,
        "study": 2, "bedroom": 2}              # 门树: 私密房间最后挂接
ATTEMPTS = 64
MAX_ROOMS = 12

DEFAULTS = {
    "origin": [0, 65, 0],
    "facing": "south",
    "width": 7,
    "depth": 9,
    "height": 3,
    "rooms": "bedroom:1,kitchen:1",
    "entrance": None,                          # {"wall":"south","at":k}; None = 正面居中
    "grid": 0,                                 # 0 = auto (max(W,D)<=10 -> 3 else 4)
    "wall_material": "minecraft:spruce_planks",
    "door_material": "minecraft:oak_door",     # "" = 门洞留 air
    "seed": 7,
}

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


def parse_rooms(s):
    if not isinstance(s, str) or not s.strip():
        die("rooms must be a demand string like \"bedroom:2,kitchen:1,living:1\"",
            {"rooms": "bedroom:2,kitchen:1,living:1", "legal": list(MIN_SIZE)})
    out = []
    for tok in s.split(","):
        name, _, cnt = tok.strip().partition(":")
        if name not in MIN_SIZE:
            die("unknown room type %r in rooms" % name,
                {"legal": list(MIN_SIZE)})
        if name in out:
            die("duplicate room %r — write it once with a count, e.g. %s:2"
                % (name, name), {"rooms": "bedroom:2"})
        try:
            c = int(cnt) if cnt else 1
        except ValueError:
            die("room count for %r must be an int" % name, {"rooms": "bedroom:2"})
        if c < 1:
            die("room count for %r must be >= 1" % name, {"rooms": "bedroom:1"})
        out += [name] * c
    if len(out) > MAX_ROOMS:
        die("too many rooms (%d > %d)" % (len(out), MAX_ROOMS),
            {"max_rooms": MAX_ROOMS})
    return out


def fits(room, w, d):
    a, b = MIN_SIZE[room]
    return (w >= a and d >= b) or (w >= b and d >= a)


def group_ok(rooms, w, d):
    """Necessary condition: group min areas fit and every room could still
    fit the (sub-)rect alone — further splits only shrink it."""
    return (sum(MIN_AREA[r] for r in rooms) <= w * d
            and all(fits(r, w, d) for r in rooms))


def partition(rect, rooms, grid, rng):
    """Guillotine-split rect=(x0,z0,w,d) so each leaf holds one room.
    Returns (leaves, walls) or None. walls: (axis, line, start, span)."""
    x0, z0, w, d = rect
    if len(rooms) == 1:
        return ([(rooms[0], rect)], []) if fits(rooms[0], w, d) else None
    axes = ["x", "z"] if w >= d else ["z", "x"]
    if rng.random() < 0.25:
        axes.reverse()
    n = len(rooms)
    ks = list(range(1, n))
    rng.shuffle(ks)
    ks.sort(key=lambda k: abs(k - n / 2))          # balanced groups first
    for axis in axes:
        span = w if axis == "x" else d
        for k in ks:
            g1, g2 = rooms[:k], rooms[k:]
            cands = []
            for p in range(1, span):               # the wall eats 1 cell
                w1, w2 = p, span - p - 1
                if w1 < 1 or w2 < 1:
                    continue
                r1 = (x0, z0, w1, d) if axis == "x" else (x0, z0, w, w1)
                r2 = ((x0 + w1 + 1, z0, w2, d) if axis == "x"
                      else (x0, z0 + w1 + 1, w, w2))
                if group_ok(g1, r1[2], r1[3]) and group_ok(g2, r2[2], r2[3]):
                    line = (x0 + w1) if axis == "x" else (z0 + w1)
                    cands.append((line % grid != 0, line, r1, r2))
            rng.shuffle(cands)
            cands.sort(key=lambda t: t[0])         # grid-snapped lines first
            for _, line, r1, r2 in cands:
                ra = partition(r1, g1, grid, rng)
                if ra is None:
                    continue
                rb = partition(r2, g2, grid, rng)
                if rb is None:
                    continue
                wall = (axis, line, z0, d) if axis == "x" else (axis, line, x0, w)
                return (ra[0] + rb[0], ra[1] + rb[1] + [wall])
    return None


def entrance_cell(ent, W, D):
    return {"north": (ent["at"], 0), "south": (ent["at"], D - 1),
            "west": (0, ent["at"]), "east": (W - 1, ent["at"])}[ent["wall"]]


def shared_seg(a, b):
    """Wall segment shared by leaf rects a,b: (axis, line, lo, hi) or None."""
    ax0, az0, aw, ad = a
    bx0, bz0, bw, bd = b
    if ax0 + aw + 1 == bx0 or bx0 + bw + 1 == ax0:
        line = ax0 + aw if ax0 + aw + 1 == bx0 else bx0 + bw
        lo, hi = max(az0, bz0), min(az0 + ad, bz0 + bd) - 1
        if lo <= hi:
            return ("x", line, lo, hi)
    if az0 + ad + 1 == bz0 or bz0 + bd + 1 == az0:
        line = az0 + ad if az0 + ad + 1 == bz0 else bz0 + bd
        lo, hi = max(ax0, bx0), min(ax0 + aw, bx0 + bw) - 1
        if lo <= hi:
            return ("z", line, lo, hi)
    return None


def try_layout(rooms, W, D, grid, ent, rng):
    order = list(rooms)
    rng.shuffle(order)
    got = partition((0, 0, W, D), order, grid, rng)
    if not got:
        return None
    leaves, walls = got
    ecell = entrance_cell(ent, W, D)
    wall_cells = set()
    for ax, line, s, ln in walls:
        for i in range(s, s + ln):
            wall_cells.add((line, i) if ax == "x" else (i, line))
    if ecell in wall_cells:
        return None
    ei = next(i for i, (_, (x0, z0, w, d)) in enumerate(leaves)
              if x0 <= ecell[0] < x0 + w and z0 <= ecell[1] < z0 + d)
    # 动线: entrance opens into a public room when one was demanded
    if any(r in PUBLIC for r in rooms) and leaves[ei][0] not in PUBLIC:
        return None
    # 采光: bedroom/living/study must touch the exterior shell wall
    for name, (x0, z0, w, d) in leaves:
        if name in NEED_EXT and not (x0 == 0 or z0 == 0
                                     or x0 + w == W or z0 + d == D):
            return None
    # adjacency graph + door spanning tree (private rooms attach last)
    n = len(leaves)
    adj = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            seg = shared_seg(leaves[i][1], leaves[j][1])
            if seg:
                adj[i].append((j, seg))
                adj[j].append((i, seg))
    in_tree = {ei}
    doors = []                                     # (i, j, axis, line, at)
    while len(in_tree) < n:
        cand = [(max(RANK[leaves[i][0]], RANK[leaves[j][0]]), i, j, seg)
                for i in sorted(in_tree) for j, seg in adj[i]
                if j not in in_tree]
        if not cand:
            return None
        rng.shuffle(cand)
        cand.sort(key=lambda t: t[0])
        _, i, j, (ax, line, lo, hi) = cand[0]
        doors.append((i, j, ax, line, (lo + hi) // 2))   # 门开墙中部
        in_tree.add(j)
    door_cells = {(line, at) if ax == "x" else (at, line)
                  for _, _, ax, line, at in doors}
    # BFS: from the entrance every cell of every room must be reachable
    free = {(x, z) for x in range(W) for z in range(D)} - (wall_cells - door_cells)
    seen = {ecell}
    stack = [ecell]
    while stack:
        cx, cz = stack.pop()
        for dx, dz in DIRS.values():
            q = (cx + dx, cz + dz)
            if q in free and q not in seen:
                seen.add(q)
                stack.append(q)
    for _, (x0, z0, w, d) in leaves:
        if any((x, z) not in seen
               for x in range(x0, x0 + w) for z in range(z0, z0 + d)):
            return None
    # score: 厨卫相邻(kitchen next to living/dining), bedroom doors off
    # public rooms, full grid snap
    names = [l[0] for l in leaves]
    score = 0
    for i in range(n):
        for j, _ in adj[i]:
            if j > i and {names[i], names[j]} in ({"kitchen", "living"},
                                                  {"kitchen", "dining"}):
                score += 2
    for i, j, _, _, _ in doors:
        pair = {names[i], names[j]}
        if "bedroom" in pair and pair & {"living", "corridor"}:
            score += 1
    if all(line % grid == 0 for _, line, _, _ in walls):
        score += 1
    return {"leaves": leaves, "walls": walls, "doors": doors,
            "entrance_idx": ei, "score": score}


def emit(p, lay, ent):
    ox, oy, oz = [int(v) for v in p["origin"]]
    rot, fmap = FACING_ROT[p["facing"]]
    W, D, H = int(p["width"]), int(p["depth"]), int(p["height"])
    mat = p["wall_material"]
    door_mat = p.get("door_material") or ""
    door_cells = {(line, at) if ax == "x" else (at, line)
                  for _, _, ax, line, at in lay["doors"]}
    cells = {}
    for ax, line, s, ln in lay["walls"]:
        for i in range(s, s + ln):
            cx, cz = (line, i) if ax == "x" else (i, line)
            for y in range(H):
                if (cx, cz) in door_cells and y < 2:
                    continue                     # door opening (1x2)
                wx, wz = rot(cx, cz)
                cells[(wx, oy + y, wz)] = mat
    for _, _, ax, line, at in lay["doors"]:
        cx, cz = (line, at) if ax == "x" else (at, line)
        wx, wz = rot(cx, cz)
        if door_mat:
            face = fmap.get({"x": "east", "z": "south"}[ax])
            cells[(wx, oy, wz)] = "%s[facing=%s,half=lower,hinge=right]" % (door_mat, face)
            cells[(wx, oy + 1, wz)] = "%s[facing=%s,half=upper,hinge=right]" % (door_mat, face)
        else:
            cells[(wx, oy, wz)] = "minecraft:air"
            cells[(wx, oy + 1, wz)] = "minecraft:air"

    def world_rect(r):
        x0, z0, w, d = r
        pts = [rot(x0, z0), rot(x0 + w - 1, z0), rot(x0, z0 + d - 1),
               rot(x0 + w - 1, z0 + d - 1)]
        xs = [q[0] for q in pts]
        zs = [q[1] for q in pts]
        return min(xs), min(zs), max(xs) - min(xs) + 1, max(zs) - min(zs) + 1

    rooms_out = []
    for idx, (name, r) in enumerate(lay["leaves"]):
        mx, mz, rw, rd = world_rect(r)
        drs = []
        for i, j, ax, line, at in lay["doors"]:
            if idx not in (i, j):
                continue
            cx, cz = (line, at) if ax == "x" else (at, line)
            wx, wz = rot(cx, cz)
            side = (("east" if r[0] + r[2] == line else "west") if ax == "x"
                    else ("south" if r[1] + r[3] == line else "north"))
            wall = fmap.get(side, side)
            off = (wx - mx) if wall in ("north", "south") else (wz - mz)
            drs.append({"wall": wall, "at": off})
        if idx == lay["entrance_idx"]:
            ex, ez = rot(*entrance_cell(ent, W, D))
            ewall = fmap.get(ent["wall"], ent["wall"])
            off = (ex - mx) if ewall in ("north", "south") else (ez - mz)
            drs.append({"wall": ewall, "at": off, "entrance": True})
        rooms_out.append({"room": name, "origin": [ox + mx, oy, oz + mz],
                          "width": rw, "depth": rd, "doors": drs})

    hints = []                                     # advisory only, no blocks
    for name, (x0, z0, w, d) in lay["leaves"]:
        if name == "corridor":
            continue
        edges = []                                 # (side, start, len), 优先南
        if z0 + d == D:
            edges.append(("south", x0, w))
        if x0 + w == W:
            edges.append(("east", z0, d))
        if x0 == 0:
            edges.append(("west", z0, d))
        if z0 == 0:
            edges.append(("north", x0, w))
        if not edges:
            continue
        edges.sort(key=lambda e: -e[2])            # longest exterior edge
        side, s0, ln = edges[0]
        ww = 1 if name == "kitchen" else min(2, ln)   # 厨房 1x1 高窗
        wh = 1 if name == "kitchen" else min(2, H - 1)
        wy = min(2, H - 1) if name == "kitchen" else 1
        at0 = s0 + (ln - ww) // 2
        pts = []
        for t in range(ww):
            c = ((at0 + t, 0 if side == "north" else D - 1) if side in ("north", "south")
                 else (0 if side == "west" else W - 1, at0 + t))
            pts.append(rot(*c))
        px = min(q[0] for q in pts)
        pz = min(q[1] for q in pts)
        hints.append({"room": name, "wall": fmap.get(side, side),
                      "pos": [ox + px, oy + wy, oz + pz],
                      "width": ww, "height": wh})
    blocks = [{"x": x, "y": y, "z": z, "block": b}
              for (x, y, z), b in sorted(cells.items())]
    return {"blocks": blocks, "rooms": rooms_out, "window_hints": hints}


def validate(p):
    if p["facing"] not in FACING_ROT:
        die("facing must be one of north/south/east/west",
            {"facing": list(FACING_ROT)})
    try:
        W, D, H = int(p["width"]), int(p["depth"]), int(p["height"])
    except (TypeError, ValueError):
        die("width/depth/height must be ints",
            {"width": "3-31", "depth": "3-31", "height": "2-8"})
    if not (3 <= W <= 31 and 3 <= D <= 31):
        die("width/depth out of range", {"width": "3-31", "depth": "3-31"})
    if not 2 <= H <= 8:
        die("height out of range", {"height": "2-8"})
    try:
        grid = int(p["grid"])
    except (TypeError, ValueError):
        die("grid must be an int", {"grid": "0=auto, 3-5"})
    if grid != 0 and not 3 <= grid <= 5:
        die("grid out of range", {"grid": "0=auto, 3-5"})
    try:
        int(p["seed"])
    except (TypeError, ValueError):
        die("seed must be an int", {"seed": 7})
    if len(p["origin"]) != 3:
        die("origin must be [x,y,z]", {"origin": "[100,65,100]"})
    if (not str(p["wall_material"]).startswith("minecraft:")
            or "[" in str(p["wall_material"])):
        die("wall_material must be a plain full-block id (no block states)",
            {"wall_material": "minecraft:spruce_planks"})
    dm = str(p.get("door_material") or "")
    if dm and not (dm.startswith("minecraft:") and dm.endswith("_door")):
        die("door_material must be a minecraft:*_door id or \"\" (air opening)",
            {"door_material": "minecraft:oak_door"})
    ent = p.get("entrance")
    if ent is not None:
        if not isinstance(ent, dict) or ent.get("wall") not in DIRS:
            die("entrance wall must be one of north/south/east/west "
                "(canonical frame, front=south)",
                {"entrance": {"wall": "south", "at": 3}})
        try:
            at = int(ent.get("at"))
        except (TypeError, ValueError):
            die("entrance at must be an int offset along the wall",
                {"entrance": {"wall": "south", "at": 3}})
        ln = W if ent["wall"] in ("north", "south") else D
        if not 0 <= at < ln:
            die("entrance at=%d outside wall %s (len %d)" % (at, ent["wall"], ln),
                {"at": "0..%d" % (ln - 1)})


def build(p):
    W, D = int(p["width"]), int(p["depth"])
    grid = int(p["grid"]) or (3 if max(W, D) <= 10 else 4)
    rooms = parse_rooms(p["rooms"])
    ent = p.get("entrance") or {"wall": "south", "at": W // 2}
    for r in set(rooms):
        a, b = MIN_SIZE[r]
        if not fits(r, W, D):
            die("%s needs at least a %dx%d interior (any rotation); got %dx%d"
                % (r, a, b, W, D), {"min_size": MIN_SIZE[r],
                                    "doc": "patterns/interior_layout.md"})
    need = sum(MIN_AREA[r] for r in rooms) + (len(rooms) - 1) * 3
    if need > W * D:
        die("cannot fit %d rooms (%s) in a %dx%d=%d interior: min room areas "
            "+ partition walls need >= %d cells — reduce the room list or "
            "enlarge the interior"
            % (len(rooms), p["rooms"], W, D, W * D, need),
            {"min_size": MIN_SIZE, "doc": "patterns/interior_layout.md"})
    seed = int(p["seed"])
    best = None
    for a in range(ATTEMPTS):
        lay = try_layout(rooms, W, D, grid, ent,
                         random.Random((seed + 1) * 100003 + a))
        if lay and (best is None or lay["score"] > best["score"]):
            best = lay
    if best is None:
        die("no valid partition for rooms \"%s\" in a %dx%d interior after %d "
            "seeded attempts (entrance %s): reduce the room list, enlarge the "
            "interior, or move the entrance"
            % (p["rooms"], W, D, ATTEMPTS, ent),
            {"min_size": MIN_SIZE, "doc": "patterns/interior_layout.md"})
    return emit(p, best, ent)


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
            {"example": '{"width":9,"depth":11,"rooms":"living:1,kitchen:1,bedroom:2"}'})
    validate(p)
    out = build(p)
    txt = json.dumps(out, ensure_ascii=False)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt + "\n")
        print("wrote %d blocks (%d rooms) to %s"
              % (len(out["blocks"]), len(out["rooms"]), a.out), file=sys.stderr)
    else:
        print(txt)


if __name__ == "__main__":
    main()
