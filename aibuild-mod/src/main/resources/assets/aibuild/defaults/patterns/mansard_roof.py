#!/usr/bin/env python3
"""mansard_roof.py — parametric mansard roof (孟莎屋顶) generator.

Four-direction slopes (like a hip) with a steep lower pitch and a FLAT top
deck — the wiki: a mansard "always has a shallow or flat section higher up".
The flat deck is the point: without it the roof is just a pyramid. Built as:
- steep rings: stacked stair pairs (bottom + upside-down, 2 y per 1 inset,
  ~63 degrees) shrinking on all four sides, corners outer-shaped (derived);
- optional 45-degree transition rings when a smaller platform is requested;
- flat deck: every deck slab (type=top, flush with the last stair surface)
  is carried by a hidden support stair directly below (floating top slabs
  fail validation; stairs are exempt).

For big buildings only (wiki: needs ~16x20 m before it looks right) and it
almost always wants dormers — pair with dormer.py.

Output: {"blocks":[{x,y,z,block}...]}. ALL direction states derived; never
hand-edit (禁止手改方向状态).

Usage:
  python mansard_roof.py --params '{"origin":[100,80,100],"width":13,"depth":13}' [--out roof.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import Builder, die, require_suffix, stair, slab, write_out

DEFAULTS = {
    "origin": [0, 64, 0],          # [x,y,z] NW corner of the WALL footprint; y = roof base layer
    "width": 13,                   # wall footprint along x
    "depth": 13,                   # wall footprint along z
    "lower_rise": 2,               # steep segment: stacked-pair rings (2 y each)
    "platform": None,              # [pw,pd] flat deck size; null = auto (= opening after steep rings)
    "overhang": 1,                 # eaves past the wall line (0-2)
    "material": "minecraft:deepslate_tile_stairs",
    "platform_material": ""        # deck slab id; "" = derived from material (_stairs -> _slab)
}

def ring(b, inset, tw, td, y, mat, half):
    """One perimeter ring at the given inset; facing uphill (toward center).
    Corner shapes are resolved automatically by the Builder."""
    x0, x1 = inset, tw - 1 - inset
    z0, z1 = inset, td - 1 - inset
    for x in range(x0, x1 + 1):
        b.put(x, y, z0, stair(mat, "south", half=half))
        b.put(x, y, z1, stair(mat, "north", half=half))
    for z in range(z0 + 1, z1):
        b.put(x0, y, z, stair(mat, "east", half=half))
        b.put(x1, y, z, stair(mat, "west", half=half))

def build(p):
    oy = p["origin"][1]
    w, d = int(p["width"]), int(p["depth"])
    oh = max(0, int(p["overhang"]))
    h1 = int(p["lower_rise"])
    hu = p["_hu"]                  # derived during validation
    pw, pd = p["_platform"]        # derived during validation
    tw, td = w + 2 * oh, d + 2 * oh
    mat = p["material"]
    deck = p["platform_material"] or mat.replace("_stairs", "_slab")
    b = Builder()

    # ---- steep lower rings (stacked pairs, 2 y per ring) ------------------
    for k in range(h1):
        y = oy + 2 * k
        ring(b, k, tw, td, y, mat, "bottom")
        ring(b, k, tw, td, y + 1, mat, "top")
    # ---- 45-degree transition rings (only if a smaller deck was asked) ----
    for j in range(hu):
        ring(b, h1 + j, tw, td, oy + 2 * h1 + j, mat, "bottom")

    # ---- flat deck: hidden support stair + flush top slab per cell --------
    y_deck = oy + 2 * h1 + hu - 1          # slab layer; surface flush w/ rim
    x0 = (tw - pw) // 2
    z0 = (td - pd) // 2
    for x in range(x0, x0 + pw):
        for z in range(z0, z0 + pd):
            face = "north" if z - z0 < pd / 2.0 else "south"
            b.put(x, y_deck - 1, z, stair(mat, face))   # hidden deck joist
            b.put(x, y_deck, z, slab(deck, "top"))
    return b.emit([p["origin"][0] - oh, 0, p["origin"][2] - oh])  # local (0,0) = the -oh eave corner; y already absolute

def legal_platforms(tw, td, h1):
    ow, od = tw - 2 * h1, td - 2 * h1
    out = []
    k = 0
    while ow - 2 * k >= 1 and od - 2 * k >= 1:
        out.append([ow - 2 * k, od - 2 * k])
        k += 1
    return out

def validate(p):
    try:
        w, d = int(p["width"]), int(p["depth"])
        h1 = int(p["lower_rise"])
        oh = int(p["overhang"])
    except (TypeError, ValueError):
        die("width/depth/lower_rise/overhang must be ints",
            {"width": "5-41", "depth": "5-41", "lower_rise": ">=1", "overhang": "0-2"})
    if not 5 <= w <= 41 or not 5 <= d <= 41:
        die("width/depth out of range (mansard is for big buildings)",
            {"width": "5-41", "depth": "5-41"})
    if not 0 <= oh <= 2:
        die("overhang out of range", {"overhang": [0, 1, 2]})
    tw, td = w + 2 * oh, d + 2 * oh
    ow, od = tw - 2 * h1, td - 2 * h1
    if h1 < 1 or ow < 1 or od < 1:
        die("lower_rise=%s leaves no opening (need >= 1x1 after the steep "
            "rings)" % h1, {"lower_rise_for_this_span": "1-%d" % (min(tw, td) // 2 - 1),
                            "platform": legal_platforms(tw, td, max(1, min(tw, td) // 2 - 1))})
    platforms = legal_platforms(tw, td, h1)
    plat = p.get("platform")
    if plat is None:
        plat = [ow, od]
    try:
        plat = [int(plat[0]), int(plat[1])]
    except (TypeError, ValueError, IndexError):
        die("platform must be [pw,pd]", {"legal_platforms": platforms})
    if plat not in platforms:
        die("platform %s does not fit: rings shrink both axes equally, so "
            "(opening-pw) must equal (opening-pd) and be even" % plat,
            {"legal_platforms": platforms})
    p["_platform"] = plat
    p["_hu"] = (ow - plat[0]) // 2
    require_suffix(p, "material", "_stairs",
                   ["minecraft:deepslate_tile_stairs", "minecraft:spruce_stairs",
                    "minecraft:dark_oak_stairs"])
    if p["platform_material"]:
        require_suffix(p, "platform_material", "_slab",
                       ["minecraft:deepslate_tile_slab", "minecraft:spruce_slab"])
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
            {"example": '{"origin":[100,80,100],"width":13,"depth":13,"lower_rise":2}'})
    validate(p)
    write_out(build(p), a.out)

if __name__ == "__main__":
    main()
