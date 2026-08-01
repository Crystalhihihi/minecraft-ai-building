#!/usr/bin/env python3
"""railing.py — parametric railing/balustrade (护栏/栏杆) generator.

Six kinds from one generator (all classic MC build-circle recipes):
  fence      — fence-post run (wooden balustrade, the default)
  wall       — cobblestone/stone-brick WALL block run (chunky, castle/bridge)
  pane       — glass_pane / iron_bars infill between posts (light, modern)
  trapdoor   — vertical OPEN trapdoors (open=true), reads as panel balustrade
  stair_rail — handrail stepping along a stair slope (posts on each step)
  bridge     — deck + railings on both long edges (+ optional abutment piers)

Conventions (see stair_orientations.md; ALL direction states derived by the
script from origin/facing — never hand-edit 禁止手改方向状态):
- `facing` = the direction the run goes (origin -> far end); the script maps
  it to a canonical frame (u along the run, w to the run's right, v up).
- trapdoor panels: hinge+panel on the `outward` side (default = right of the
  run) so the rail reads as a fence line on the deck edge.
- stair_rail steps rise toward `facing` (stair facing = uphill, the iron
  rule); one rail post stands on each step.
- corners: `corner` adds an L-return at the far end; pane corners and both
  run ends get a post (panes/walls auto-connect, posts anchor the look).

Output: {"blocks":[{x,y,z,block}]} compatible with set_blocks_from_file.

Usage:
  python railing.py --params '{"kind":"fence","origin":[100,64,100],"facing":"east","length":6}' [--out rail.json]
  python railing.py --params '{"kind":"stair_rail","origin":[100,64,100],"facing":"north","length":5}'
  python railing.py --params '{"kind":"bridge","origin":[100,64,100],"facing":"south","length":8,"width":3}'
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
RIGHT = {"north": "east", "east": "south", "south": "west", "west": "north"}
KINDS = ("fence", "wall", "pane", "trapdoor", "stair_rail", "bridge")
CORNERS = ("none", "left", "right")

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] first cell of the run; y = layer the railing stands in
    "facing": "east",              # run direction (origin -> far end)
    "kind": "fence",               # fence | wall | pane | trapdoor | stair_rail | bridge
    "length": 5,                   # cells along the run (steps for stair_rail), 1-32
    "material": "minecraft:spruce_fence",   # rail block (fence/wall/pane/trapdoor id per kind)
    "height": 1,                   # rail height 1-2 (fence/wall/pane/trapdoor kinds)
    "outward": "auto",             # trapdoor panel side; auto = right of the run
    "corner": "none",              # none | left | right : L-return at the far end
    "corner_length": 3,            # return run length (corner cells beyond the junction)
    "post_material": "minecraft:spruce_fence",  # pane corner/end posts, stair_rail posts fall back here too
    "post_spacing": 3,             # pane: post every N cells (ends + corner always posted)
    # stair_rail:
    "step_material": "minecraft:oak_stairs",    # the stair flight under the handrail
    "with_steps": True,            # False = posts only (mount on an existing flight; validate with base=)
    # bridge:
    "width": 3,                    # deck width 1-5
    "deck_material": "minecraft:spruce_planks",
    "rail": "fence",               # bridge edge railing: fence | wall | pane
    "piers": True,                 # abutment piers under both deck ends
    "pier_drop": 2                 # pier layers below the deck
}


def stair(mat, facing, half="bottom"):
    return "%s[facing=%s,half=%s]" % (mat, facing, half)


def build(p):
    kind, F = p["kind"], p["facing"]
    length = int(p["length"])
    ox, oy, oz = [int(v) for v in p["origin"]]
    fx, fz = DIRS[F]                       # forward = run direction
    rx, rz = DIRS[RIGHT[F]]                # right of the run
    cells = {}                             # (u,w,v) -> block; last write wins (dedupe)

    def P(u, w, v, block):
        cells[(u, w, v)] = block

    def outward_dir(side="auto"):
        return RIGHT[F] if side == "auto" else side

    def trap(mat, facing_dir):
        return "%s[facing=%s,half=bottom,open=true]" % (mat, facing_dir)

    def run(u0, w0, du, dw, n, kind_, mat, outward, v0=0):
        """One straight railing segment of n cells starting at (u0,w0),
        stepping (du,dw) per cell, base layer v0."""
        height = int(p["height"])
        spacing = max(2, int(p["post_spacing"]))
        for i in range(n):
            u, w = u0 + du * i, w0 + dw * i
            if kind_ == "pane":
                is_post = (i % spacing == 0) or (i == n - 1)
                cell = p["post_material"] if is_post else mat
                for v in range(height):
                    P(u, w, v0 + v, cell)
            elif kind_ == "trapdoor":
                for v in range(height):
                    P(u, w, v0 + v, trap(mat, outward))
            else:  # fence / wall
                for v in range(height):
                    P(u, w, v0 + v, mat)

    if kind in ("fence", "wall", "pane", "trapdoor"):
        outw = outward_dir(p["outward"])
        run(0, 0, 1, 0, length, kind, p["material"], outw)
        corner = p["corner"]
        if corner != "none":
            cl = int(p["corner_length"])
            sd = 1 if corner == "right" else -1        # return run goes to this side
            # junction cell: pane gets an anchor post; others already placed
            if kind == "pane":
                for v in range(int(p["height"])):
                    P(length - 1, 0, v, p["post_material"])
            # outward of the return run: keeps enclosing the same area
            outw2 = F if corner == "left" else OPP[F]
            run(length - 1, sd, 0, sd, cl, kind, p["material"], outw2)

    elif kind == "stair_rail":
        step, post = p["step_material"], p["material"]
        if not (str(post).endswith("_fence") or str(post).endswith("_wall")):
            post = p["post_material"]
        for i in range(length):
            if p["with_steps"]:
                P(i, 0, i, stair(step, F))               # facing = uphill (iron rule)
            P(i, 0, i + 1, post)                         # one post per step

    else:  # bridge
        width = int(p["width"])
        deck, rail_kind = p["deck_material"], p["rail"]
        for u in range(length):
            for w in range(width):
                P(u, w, 0, deck)
        for w in (0, width - 1):                         # rails on both long edges
            run(0, w, 1, 0, length, rail_kind, p["material"], "auto", v0=1)
        if rail_kind != "pane" and width >= 2:           # corner anchor posts
            for u in (0, length - 1):
                for w in (0, width - 1):
                    P(u, w, 1, p["post_material"])
        if p["piers"]:                                   # abutments under both ends
            for u in (0, length - 1):
                for w in range(width):
                    for v in range(1, int(p["pier_drop"]) + 1):
                        P(u, w, -v, deck)
    return [{"x": ox + rx * w + fx * u,
             "y": oy + v,
             "z": oz + rz * w + fz * u,
             "block": block}
            for (u, w, v), block in sorted(cells.items())]


def validate(p):
    if p["facing"] not in DIRS:
        die("facing must be one of north/south/east/west", {"facing": list(DIRS)})
    kind = p["kind"]
    if kind not in KINDS:
        die("kind must be one of %s" % (KINDS,), {"kind": list(KINDS)})
    try:
        length, height = int(p["length"]), int(p["height"])
    except (TypeError, ValueError):
        die("length/height must be ints", {"length": "1-32", "height": "1-2"})
    if not 1 <= length <= 32:
        die("length out of range", {"length": "1-32"})
    if not 1 <= height <= 2:
        die("height out of range", {"height": "1-2"})
    mat = str(p["material"])
    need = {"fence": "_fence", "wall": "_wall", "trapdoor": "_trapdoor"}
    if kind in need and not mat.endswith(need[kind]):
        die("kind=%s needs a *%s material id" % (kind, need[kind]),
            {"material": ["minecraft:spruce_fence", "minecraft:cobblestone_wall",
                          "minecraft:oak_trapdoor"]})
    if kind == "pane" and not (mat.endswith("_pane") or mat == "minecraft:iron_bars"):
        die("kind=pane needs a *_pane id or minecraft:iron_bars",
            {"material": ["minecraft:glass_pane", "minecraft:iron_bars",
                          "minecraft:light_gray_stained_glass_pane"]})
    if p["corner"] not in CORNERS:
        die("corner must be one of %s" % (CORNERS,), {"corner": list(CORNERS)})
    if p["outward"] not in ("auto",) + tuple(DIRS):
        die("outward must be auto or a cardinal direction",
            {"outward": ["auto", "north", "south", "east", "west"]})
    if kind == "stair_rail" and not str(p["step_material"]).endswith("_stairs"):
        die("step_material must be a *_stairs id",
            {"step_material": ["minecraft:oak_stairs", "minecraft:stone_brick_stairs"]})
    if kind == "bridge":
        if p["rail"] not in ("fence", "wall", "pane"):
            die("bridge rail must be fence | wall | pane", {"rail": ["fence", "wall", "pane"]})
        if not 1 <= int(p["width"]) <= 5:
            die("bridge width out of range", {"width": "1-5"})
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
            {"example": '{"kind":"fence","origin":[100,64,100],"facing":"east","length":6}'})
    validate(p)
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
