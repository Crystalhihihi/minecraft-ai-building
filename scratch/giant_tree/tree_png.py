#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tree_png.py — blocks json 快速 3D 渲染(matplotlib voxel), 供离线形态检查。
用法: python tree_png.py tree.json out.png [az] [el]"""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

src, out = sys.argv[1], sys.argv[2]
az = float(sys.argv[3]) if len(sys.argv) > 3 else -60
el = float(sys.argv[4]) if len(sys.argv) > 4 else 18

blocks = json.load(open(src, encoding="utf-8"))["blocks"]
xs = [b["x"] for b in blocks]; ys = [b["y"] for b in blocks]; zs = [b["z"] for b in blocks]
x0, y0, z0 = min(xs), min(ys), min(zs)
shape = (max(xs) - x0 + 1, max(ys) - y0 + 1, max(zs) - z0 + 1)
filled = np.zeros(shape, dtype=bool)
colors = np.empty(shape + (4,), dtype=float)
for b in blocks:
    i, j, k = b["x"] - x0, b["y"] - y0, b["z"] - z0
    filled[i, j, k] = True
    if "_leaves" in b["block"]:
        colors[i, j, k] = (0.25, 0.6, 0.25, 1.0)
    elif "_fence" in b["block"]:
        colors[i, j, k] = (0.6, 0.45, 0.25, 1.0)
    else:
        colors[i, j, k] = (0.45, 0.3, 0.15, 1.0)

fig = plt.figure(figsize=(10, 10))
ax = fig.add_subplot(111, projection="3d")
ax.voxels(filled, facecolors=colors, edgecolor=None, shade=True)
ax.view_init(elev=el, azim=az)
ax.set_box_aspect((shape[0], shape[1], shape[2]))
ax.set_axis_off()
plt.tight_layout()
plt.savefig(out, dpi=110, bbox_inches="tight")
print("saved", out, "shape", shape)
