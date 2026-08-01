#!/usr/bin/env python3
"""roof_common.py — shared helpers for the roof-pack generators (roof pack).

- stair/slab block-state builders
- Builder: canonical-frame block accumulator with dedupe + automatic
  corner-shape resolution + rotation to a target facing
- the corner-shape table derived from the hand-built ground truth
  (patterns/stair_orientations.md + docs/research/stair-orientations.md):
  backs outward -> inner corners, backs inward -> outer corners.
  Shapes are INTENTS (the mod may re-derive at placement); what matters is
  facing/half geometrically correct + frame corners never "straight".
- die()/validate_material() for the "illegal params -> error listing legal
  values" contract.

Generators in this pack: dormer, gambrel_roof, mansard_roof, helm_roof,
chimney. All emit set_blocks_from_file-compatible {"blocks":[...]}.
"""
import json, sys

# ------------------------------------------------------------- block specs --
def stair(base, facing, half="bottom", shape=None):
    s = "%s[facing=%s,half=%s" % (base, facing, half)
    if shape:
        s += ",shape=" + shape
    return s + "]"

def slab(base, type_):
    return "%s[type=%s]" % (base, type_)

# ------------------------------------------------------- corner shape table --
def _rot_cw(d):
    return {"north": "east", "east": "south", "south": "west", "west": "north"}[d]

def _build_corner_table():
    # anchors from ground truth: outer frame TL = (south,{e,s}) -> outer_left
    # (hip_roof nw); inner frame TL = (west,{e,s}) -> inner_right (front
    # neighbor's facing = CW rotation of ours). Rotated into the full table.
    table = {}
    for facing, pair, shape in [
        ("south", ("east", "south"), "outer_left"),
        ("south", ("west", "south"), "outer_right"),
        ("west", ("east", "south"), "inner_right"),
        ("south", ("north", "west"), "inner_left"),
    ]:
        f, (a, b), s = facing, pair, shape
        for _ in range(4):
            table[(f, frozenset((a, b)))] = s
            f, a, b = _rot_cw(f), _rot_cw(a), _rot_cw(b)
    return table

CORNER_TABLE = _build_corner_table()
PERP_PAIRS = (("north", "east"), ("east", "south"), ("south", "west"), ("west", "north"))
DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}

def corner_shape(facing, neighbors):
    """Intent for a stair cell whose stair neighbors at the same y are exactly
    two perpendicular directions."""
    return CORNER_TABLE.get((facing, frozenset(neighbors)), "outer_left")

# ------------------------------------------------------------------ Builder --
class Builder:
    """Accumulates (x,y,z)->spec cells, dedupes (last write wins), resolves
    stair corner shapes against the final geometry, emits world blocks.

    frame: pass rot=None to emit cells as-is (already world-local); or pass
    rot/fmap callables to rotate canonical (x,z) + facing on emit.
    """

    def __init__(self, rot=None, fmap=None):
        self.cells = {}
        self.air = set()
        self.rot = rot
        self.fmap = fmap

    def put(self, x, y, z, block):
        self.cells[(x, y, z)] = block

    def has(self, x, y, z):
        return (x, y, z) in self.cells

    def carve(self, x, y, z, force=False):
        """Carve an air cell. force=True wins over own body (window tunnel
        must penetrate cheeks/walls); non-forced yields to body blocks."""
        if force:
            self.cells.pop((x, y, z), None)
            self.air.add((x, y, z))
        else:
            self.air.add((x, y, z))

    def resolve_corners(self):
        stairs = {k: v for k, v in self.cells.items() if "_stairs" in v}
        for (x, y, z), spec in stairs.items():
            if "shape=" in spec:
                continue
            present = {d for d, (dx, dz) in DIRS.items()
                       if (x + dx, y, z + dz) in stairs}
            if len(present) == 2 and any(a in present and b in present
                                         for a, b in PERP_PAIRS):
                facing = spec.split("facing=")[1].split(",")[0].rstrip("]")
                shape = corner_shape(facing, present)
                self.cells[(x, y, z)] = spec.rstrip("]") + ",shape=%s]" % shape

    def emit(self, origin):
        self.resolve_corners()
        ox, oy, oz = origin
        blocks = []
        for (x, y, z) in sorted(self.air):
            if (x, y, z) in self.cells:
                continue  # own body wins; never carve our own blocks
            wx, wz = self.rot(x, z) if self.rot else (x, z)
            blocks.append({"x": ox + wx, "y": oy + y, "z": oz + wz, "block": "minecraft:air"})
        for (x, y, z), spec in sorted(self.cells.items()):
            wx, wz = self.rot(x, z) if self.rot else (x, z)
            blocks.append({"x": ox + wx, "y": oy + y, "z": oz + wz, "block": self._world(spec)})
        return blocks

    def _world(self, block):
        if not self.fmap or "[" not in block:
            return block
        base, props = block[:-1].split("[", 1)
        out = []
        for kv in props.split(","):
            k, _, v = kv.partition("=")
            if k == "facing":
                v = self.fmap.get(v, v)
            out.append("%s=%s" % (k, v))
        return base + "[" + ",".join(out) + "]"

# canonical frame for face-able pieces: front = south, u -> +x (viewer's
# right), v -> -z (into the structure). Rotations preserve stair shape
# chirality; only facing maps.
FACING_ROT = {
    "south": (lambda x, z: (x, z),  {}),
    "north": (lambda x, z: (-x, -z), {"north": "south", "south": "north", "east": "west", "west": "east"}),
    "east":  (lambda x, z: (z, -x), {"south": "east", "north": "west", "east": "north", "west": "south"}),
    "west":  (lambda x, z: (-z, x), {"south": "west", "north": "east", "east": "south", "west": "north"}),
}

# ----------------------------------------------------------------- cli glue --
def die(msg, legal):
    print(json.dumps({"error": msg, "legal": legal}, ensure_ascii=False), file=sys.stderr)
    sys.exit(2)

def require_suffix(p, key, suffix, examples):
    if not str(p[key]).endswith(suffix):
        die("%s must be a *%s id" % (key, suffix), {key: examples})

def write_out(blocks, out_path):
    out = json.dumps({"blocks": blocks}, ensure_ascii=False)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print("wrote %d blocks to %s" % (len(blocks), out_path), file=sys.stderr)
    else:
        print(out)
