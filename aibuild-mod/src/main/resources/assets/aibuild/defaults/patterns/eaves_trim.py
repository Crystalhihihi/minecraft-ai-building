#!/usr/bin/env python3
"""eaves_trim.py — eaves finishing (檐口修饰) for a stair-skin roof.

"有挑檐必有椽子" (WesterosCraft review line, detail-techniques §3.1): any
overhanging eave needs rafters beneath the roof blocks, or the overhang
reads as paper. Reads a roof blocks json (gable_roof / hip_roof /
xieshan_roof output), DERIVES the eave lip from the geometry — the lowest
stair cells whose outward cell (opposite the stair's facing; stair facing
points uphill) is empty — and emits the TRIM ONLY:

  1) rafters (椽子): every `rafter_spacing` lip cells, one cell directly
     BELOW the lip stair, poking out under the eave — upside-down stair
     (反放楼梯, default) / bottom slab / wall (圆石墙椽头)
  2) edge strip (檐口收边条): contrast material along the eave outline —
     fascia = open trapdoors flat on the lip's outer face, plus end caps at
     row ends/corners (封檐板); slab = a bottom-slab row on top of the lip

Overlay the output on the roof json: the trim NEVER writes a cell the roof
already occupies (collision_check-clean by construction). All facing/half/
open states are DERIVED by the script — never hand-edit them in the output
(禁止手改方向状态). Output: {"blocks":[...]}.

Usage:
  python gable_roof.py --params '{"origin":[100,80,100],"width":7,"depth":9}' --out roof.json
  python eaves_trim.py --params '{"roof":"roof.json"}' --out trim.json
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mirror_build  # noqa: E402  (patterns/: load_blocks)
from roof_common import DIRS, die, require_suffix, slab, stair, write_out  # noqa: E402

DEFAULTS = {
    "roof": "",                      # path to the roof blocks json (gable/hip/xieshan output)
    "rafters": True,                 # 椽子 under the eave lip
    "rafter_style": "stairs",        # stairs (反放楼梯) | slab (下半砖) | wall (圆石墙当椽头)
    "rafter_spacing": 2,             # one rafter every N lip cells (间距 1-2, §3.1)
    "rafter_material": "",           # "" = auto per style (dark_oak_stairs / dark_oak_slab / cobblestone_wall)
    "edge": "fascia",                # fascia (trapdoor 封檐板) | slab (檐口半砖收边) | none
    "edge_material": ""              # "" = auto per edge (dark_oak_trapdoor / dark_oak_slab)
}

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
AUTO_RAFTER = {"stairs": "minecraft:dark_oak_stairs",
               "slab": "minecraft:dark_oak_slab",
               "wall": "minecraft:cobblestone_wall"}
AUTO_EDGE = {"fascia": "minecraft:dark_oak_trapdoor",
             "slab": "minecraft:dark_oak_slab"}
RAFTER_SUFFIX = {"stairs": "_stairs", "slab": "_slab", "wall": "_wall"}
EDGE_SUFFIX = {"fascia": "_trapdoor", "slab": "_slab"}

def parse(spec):
    """'minecraft:x_stairs[facing=south,half=bottom]' -> (name, {props})."""
    if "[" in spec:
        name, props = spec[:-1].split("[", 1)
        return name, dict(kv.split("=", 1) for kv in props.split(","))
    return spec, {}

def build(p):
    try:
        roof_blocks = mirror_build.load_blocks(p["roof"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as e:
        die("cannot read roof json '%s': %s" % (p["roof"], e),
            {"roof": "path to a set_blocks_from_file-compatible json (run gable_roof.py --out roof.json first)"})
    occupied = {}
    for b in roof_blocks:
        if b["block"] in ("air", "minecraft:air"):
            continue
        occupied[(b["x"], b["y"], b["z"])] = b["block"]
    if not occupied:
        die("roof json has no solid blocks", {"roof": p["roof"]})
    min_y = min(y for _, y, _ in occupied)

    # ---- derive the eave lip: lowest stair cells with an empty outward cell
    lips = []  # (x, z, stair facing, outward)
    for (x, y, z), spec in sorted(occupied.items()):
        if y != min_y or "_stairs" not in spec:
            continue
        _, props = parse(spec)
        f = props.get("facing", "")
        if f not in DIRS:
            continue
        o = OPP[f]
        dx, dz = DIRS[o]
        if (x + dx, y, z + dz) not in occupied:
            lips.append((x, z, f, o))
    if not lips:
        print("warning: no stair eave lip found in %s — nothing to trim"
              % p["roof"], file=sys.stderr)
        return []
    cells = {}

    # ---- ① rafters: directly below the lip ("rafters beneath exterior roof
    # blocks"), every `rafter_spacing` cells along each eave row ------------
    if p["rafters"]:
        style = p["rafter_style"]
        mat = p["rafter_material"] or AUTO_RAFTER[style]
        spacing = int(p["rafter_spacing"])
        rows = {}
        for x, z, f, o in lips:
            along, perp = (x, z) if f in ("north", "south") else (z, x)
            rows.setdefault((f, perp), []).append((along, x, z, o))
        for key in sorted(rows):
            for i, (along, x, z, o) in enumerate(sorted(rows[key])):
                if i % spacing:
                    continue
                if (x, min_y - 1, z) in occupied:
                    continue
                if style == "stairs":
                    block = stair(mat, o, half="top")  # 反放楼梯, 薄端朝外 = 椽头
                elif style == "slab":
                    block = slab(mat, "bottom")
                else:
                    block = mat
                cells[(x, min_y - 1, z)] = block

    # ---- ② edge strip along the eave outline ------------------------------
    edge = p["edge"]
    if edge != "none":
        mat = p["edge_material"] or AUTO_EDGE[edge]
        for x, z, f, o in lips:
            if edge == "fascia":
                # open trapdoor flat on the lip's outer face (封檐板)
                dx, dz = DIRS[o]
                if (x + dx, min_y, z + dz) not in occupied:
                    cells[(x + dx, min_y, z + dz)] = (
                        "%s[facing=%s,half=bottom,open=true]" % (mat, f))
                # end caps where the row ends / turns a corner (along-axis
                # neighbour at the eave layer missing)
                ax = ("east", "west") if f in ("north", "south") else ("north", "south")
                for c in ax:
                    cx, cz = DIRS[c]
                    if (x + cx, min_y, z + cz) not in occupied:
                        cells[(x + cx, min_y, z + cz)] = (
                            "%s[facing=%s,half=bottom,open=true]" % (mat, OPP[c]))
            else:  # slab strip on top of the lip (檐口第一排瓦收边)
                if (x, min_y + 1, z) not in occupied:
                    cells[(x, min_y + 1, z)] = slab(mat, "bottom")

    return [{"x": x, "y": y, "z": z, "block": b}
            for (x, y, z), b in sorted(cells.items())]

def validate(p):
    if not str(p["roof"]):
        die("param 'roof' is required",
            {"roof": "roof.json (gable_roof/hip_roof/xieshan_roof output)"})
    if p["rafter_style"] not in AUTO_RAFTER:
        die("rafter_style must be one of %s" % (tuple(AUTO_RAFTER),),
            {"rafter_style": list(AUTO_RAFTER)})
    if p["rafters"]:
        try:
            spacing = int(p["rafter_spacing"])
        except (TypeError, ValueError):
            die("rafter_spacing must be an int", {"rafter_spacing": [1, 2]})
        if spacing not in (1, 2):
            die("rafter_spacing %s out of range (檐口椽距 1-2, §3.1)" % spacing,
                {"rafter_spacing": [1, 2]})
        if p["rafter_material"]:
            require_suffix(p, "rafter_material", RAFTER_SUFFIX[p["rafter_style"]],
                           list(AUTO_RAFTER.values()))
    if p["edge"] not in AUTO_EDGE and p["edge"] != "none":
        die("edge must be one of %s" % (tuple(AUTO_EDGE) + ("none",),),
            {"edge": list(AUTO_EDGE) + ["none"]})
    if p["edge"] in AUTO_EDGE and p["edge_material"]:
        require_suffix(p, "edge_material", EDGE_SUFFIX[p["edge"]],
                       list(AUTO_EDGE.values()))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}", help="JSON object of parameters")
    ap.add_argument("--out", default="", help="output file (default: stdout)")
    a = ap.parse_args()
    p = dict(DEFAULTS)
    try:
        p.update(json.loads(a.params) if a.params.strip() else {})
    except json.JSONDecodeError as e:
        die("--params is not valid JSON: %s" % e, {"example": '{"roof":"roof.json"}'})
    validate(p)
    write_out(build(p), a.out)

if __name__ == "__main__":
    main()
