#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_in_wall.py — 把 doorway 产物嵌进测试墙渲染(墙+地被挖洞/放件后的形态目检)。
用法: python render_in_wall.py <case.json> <out.png> [az] [el]"""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

src, out = sys.argv[1], sys.argv[2]
az = float(sys.argv[3]) if len(sys.argv) > 3 else 155
el = float(sys.argv[4]) if len(sys.argv) > 4 else 10

blocks = json.loads(Path(src).read_text(encoding="utf-8"))["blocks"]
ox = min(b["x"] for b in blocks); oy = min(b["y"] for b in blocks); oz = min(b["z"] for b in blocks)

# 测试墙: 覆盖门洞区, 2 厚(z=0,-1), 浅灰石砖; 地面 y=oy-2(被台阶/灯柱落位)
cells = {}
for x in range(ox - 4, ox + 9):
    for y in range(oy - 1, oy + 9):
        for z in (0, -1):
            cells[(x, y, z)] = "minecraft:stone_bricks"
for x in range(ox - 4, ox + 9):
    for z in range(-1, 5):
        cells[(x, oy - 2, z)] = "minecraft:grass_block"
for b in blocks:
    k = (b["x"], b["y"], b["z"])
    if b["block"] == "minecraft:air":
        cells.pop(k, None)           # 掏洞
    else:
        cells[k] = b["block"]

COLORS = [
    ("grass", (0.35, 0.6, 0.3, 1)), ("lantern", (1.0, 0.85, 0.2, 1)),
    ("chiseled", (0.55, 0.55, 0.6, 1)), ("_door", (0.55, 0.35, 0.15, 1)),
    ("dark_oak", (0.25, 0.15, 0.08, 1)), ("oak_", (0.6, 0.45, 0.25, 1)),
    ("spruce", (0.35, 0.22, 0.1, 1)), ("stone_brick_stairs", (0.5, 0.5, 0.5, 1)),
    ("stone_brick_slab", (0.5, 0.5, 0.55, 1)), ("stone_brick_wall", (0.45, 0.45, 0.45, 1)),
    ("stone_bricks", (0.72, 0.72, 0.7, 1)), ("_fence", (0.4, 0.28, 0.12, 1)),
    ("_trapdoor", (0.5, 0.35, 0.15, 1)),
]

def color(n):
    for key, c in COLORS:
        if key in n:
            return c
    return (0.7, 0.4, 0.4, 1)

xs = [k[0] for k in cells]; ys = [k[1] for k in cells]; zs = [k[2] for k in cells]
x0, y0, z0 = min(xs), min(ys), min(zs)
# matplotlib voxels: 数组第 3 轴才是竖直轴 —— 按 (x, z, y) 摆, MC-y 垫底竖起来
shape = (max(xs) - x0 + 1, max(zs) - z0 + 1, max(ys) - y0 + 1)
filled = np.zeros(shape, dtype=bool)
colors = np.empty(shape + (4,), dtype=float)
for (x, y, z), n in cells.items():
    filled[x - x0, z - z0, y - y0] = True
    colors[x - x0, z - z0, y - y0] = color(n)

fig = plt.figure(figsize=(11, 9))
ax = fig.add_subplot(111, projection="3d")
ax.voxels(filled, facecolors=colors, edgecolor=(0, 0, 0, 0.15), shade=True)
ax.view_init(elev=el, azim=az)
ax.set_box_aspect((shape[0], shape[1], shape[2]))
ax.set_axis_off()
plt.tight_layout()
plt.savefig(out, dpi=110, bbox_inches="tight")
print("saved", out, "shape", shape, "cells", len(cells))
