#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_smoke.py — doorway.py smoke: exit codes + support_check + ASCII 截面目检.

Usage: python scratch/doorway_smoke/run_smoke.py
Exit 0 = all cases ran clean and passed support_check.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAT = ROOT / "aibuild-mod/src/main/resources/assets/aibuild/defaults/patterns"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

CASES = [
    # 任务要求的 4 组全组合(canopy+steps 默认开)
    ("rect_1x2_full",   {"origin": [0, 64, 0], "facing": "south", "width": 1, "height": 2}),
    ("rect_2x3_full",   {"origin": [0, 64, 0], "facing": "south", "width": 2, "height": 3}),
    ("arch_3x3_full",   {"origin": [0, 64, 0], "facing": "south", "style": "arch", "width": 3, "height": 3,
                         "frame": "minecraft:stone_brick_stairs", "door_block": "none"}),
    ("double_2x2_full", {"origin": [0, 64, 0], "facing": "south", "width": 2, "height": 2,
                         "door_block": "minecraft:dark_oak_door"}),
    # 补测: 三模式/凹龛/旋转/裸洞
    ("rect_1x2_trapdoor", {"origin": [0, 64, 0], "facing": "south", "width": 1, "height": 2,
                           "frame": "minecraft:oak_trapdoor"}),
    ("rect_2x2_solid_r0", {"origin": [0, 64, 0], "facing": "south", "width": 2, "height": 2,
                           "frame": "minecraft:dark_oak_planks", "recess": 0}),
    ("arch_5x3_east",   {"origin": [0, 64, 0], "facing": "east", "style": "arch", "width": 5, "height": 3,
                         "frame": "minecraft:stone_bricks", "door_block": "none", "recess": 2}),
    ("arch_3x2_north_bare", {"origin": [0, 64, 0], "facing": "north", "style": "arch", "width": 3, "height": 2,
                             "canopy": False, "steps": False, "side_decor": False, "door_block": "none"}),
    ("rect_1x2_min",    {"origin": [0, 64, 0], "facing": "south", "width": 1, "height": 2,
                         "canopy": False, "steps": False, "side_decor": False, "recess": 0}),
]


def glyph(block):
    n = block.split("[")[0]
    if n == "minecraft:air":
        return "·"
    if "chiseled" in n:
        return "K"
    if n.endswith("_door"):
        return "D"
    if "lantern" in n:
        return "l" if "hanging=true" in block else "L"
    if n.endswith("_trapdoor"):
        return "T" if "open=true" in block else "t"
    if n.endswith("_stairs"):
        return "S" if "half=top" in block else "s"
    if n.endswith("_slab"):
        return "-"
    if n.endswith("_fence"):
        return "F"
    if n.endswith("_wall"):
        return "W"
    if n.endswith("_log"):
        return "P"
    return "#"


def ascii_panels(name, blocks):
    """face plane (z=0) / front layer (z=+1) / side section at door centre."""
    xs = [b["x"] for b in blocks]; ys = [b["y"] for b in blocks]; zs = [b["z"] for b in blocks]
    x0, x1, y0, y1, z0, z1 = min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1, min(zs) - 1, max(zs) + 1
    at = {(b["x"], b["y"], b["z"]): b["block"] for b in blocks}

    def panel(zfix, title):
        print("  %s (z=%d)" % (title, zfix))
        for y in range(y1, y0 - 1, -1):
            row = "".join(glyph(at[(x, y, zfix)]) if (x, y, zfix) in at else " "
                          for x in range(x0, x1 + 1))
            print("   y=%2d |%s|" % (y, row))
        print("        " + "".join(str(x % 10) for x in range(x0, x1 + 1)))

    print("== %s ==" % name)
    panel(0, "墙面层 face plane")
    panel(1, "门前层 front layer")
    cx = sorted({b["x"] for b in blocks if b["block"] == "minecraft:air"})
    cx = cx[len(cx) // 2] if cx else (x0 + x1) // 2
    print("  侧截面 side section (x=%d, 右=门外)" % cx)
    for y in range(y1, y0 - 1, -1):
        row = "".join(glyph(at[(cx, y, z)]) if (cx, y, z) in at else " "
                      for z in range(z0, z1 + 1))
        print("   y=%2d |%s|" % (y, row))
    print("        " + "".join(str(z % 10) for z in range(z0, z1 + 1)))


def main():
    fails = []
    for name, params in CASES:
        out = OUT / (name + ".json")
        r = subprocess.run([sys.executable, str(PAT / "doorway.py"),
                            "--params", json.dumps(params), "--out", str(out)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            fails.append((name, "gen exit=%d %s" % (r.returncode, r.stderr.strip()[:200])))
            print("FAIL gen %s: %s" % (name, r.stderr.strip()[:200]))
            continue
        blocks = json.loads(out.read_text(encoding="utf-8"))["blocks"]
        print("%-22s exit=0 blocks=%d  (%s)" % (name, len(blocks), r.stderr.strip()))
        sc = subprocess.run([sys.executable, str(PAT / "validators/support_check.py"),
                             "--params", json.dumps({"blocks": str(out)})],
                            capture_output=True, text=True)
        rep = json.loads(sc.stdout)
        if sc.returncode != 0:
            fails.append((name, "support_check: %s" % json.dumps(rep["floaters"][:5], ensure_ascii=False)))
            print("  support_check FAIL: %s" % json.dumps(rep["floaters"][:5], ensure_ascii=False))
        else:
            print("  support_check OK (checked=%d)" % rep["checked"])
        if params.get("facing", "south") == "south":
            ascii_panels(name, blocks)
            # 渲染用无空气副本(tree_png 把 air 也画成实体)
            noair = [b for b in blocks if b["block"] != "minecraft:air"]
            (OUT / (name + ".noair.json")).write_text(
                json.dumps({"blocks": noair}, ensure_ascii=False), encoding="utf-8")
    if fails:
        print("\n%d FAILURES" % len(fails))
        return 1
    print("\nALL %d CASES PASS (exit=0, support_check green)" % len(CASES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
