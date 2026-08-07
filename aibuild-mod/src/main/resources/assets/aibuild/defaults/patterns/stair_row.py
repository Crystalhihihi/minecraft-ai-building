#!/usr/bin/env python3
"""stair_row.py — 楼梯行/环推导器(治"外墙阶梯朝向一直错").

原理: facing/half 由几何推导, 不由人挑; **shape 不写** — 游戏放置时经
ChunkSupport 的 shape replay 自动算转角(inner/outer), 用原版逻辑兜底。

模式:
- run 直行: a→b 轴对齐。同 y=平推行(檐口线/线脚/窗台/滴水);dy!=0=上升行
  (每步 +1y, facing=上坡方向;smooth=true 时踏面/踢面交替(bottom/top),
  即 stair_orientations.md §3 的光滑梯段)
- ring 矩形环: a=min角, b=max角, 同 y。back_mode=out: 背朝外(踏步向环心
  下, 自动 inner 转角) — 檐口环/帽线环;back_mode=in: 背朝环心(踏步向外
  下, 自动 outer 转角) — 女儿墙/围栏基座。

facing 语义(vanilla): facing=上行方向=高背侧。平推行 back=高背朝哪边
(檐口=朝屋面/脊, 墙裙=朝墙, 压顶=朝外)。
Output: {"blocks":[{x,y,z,block}...]}, stair 只带 facing/half。

Usage:
  python stair_row.py --params '{"a":[0,-51,0],"b":[10,-51,0],"back":"north","material":"minecraft:spruce_stairs","half":"top"}' [--out s.json]
  python stair_row.py --params '{"a":[0,-51,0],"b":[10,-51,6],"mode":"ring","back_mode":"out","material":"minecraft:spruce_stairs","half":"top"}'
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof_common import die, write_out

DEFAULTS = {
    "a": [0, 64, 0],
    "b": [10, 64, 0],
    "mode": "run",              # run | ring
    "back": "north",            # run: 高背朝向 north|south|east|west
    "back_mode": "out",         # ring: out=背朝外(inner 转角) | in=背朝心(outer)
    "half": "bottom",           # bottom | top(倒挂: 檐下/拱腹/吊顶线脚)
    "smooth": False,            # 上升行: 踏面/踢面交替(光滑梯段)
    "material": "minecraft:spruce_stairs",
}
DIR_FACING = {"north": "north", "south": "south", "east": "east", "west": "west"}


def stair(x, y, z, facing, half):
    return {"x": x, "y": y, "z": z,
            "block": "%s[facing=%s,half=%s]" % (MAT, facing, half)}


def build(p):
    ax, ay, az = (int(v) for v in p["a"])
    bx, by, bz = (int(v) for v in p["b"])
    out = []
    if p["mode"] == "ring":
        if ay != by:
            die("ring 模式 a/b 必须同 y(环在一个平面上)", {})
        # 四条边: back_mode=out → 各边 facing 朝外(背朝外, 转角自动 inner)
        face = {"out": {"z_min": "north", "z_max": "south", "x_min": "west", "x_max": "east"},
                "in": {"z_min": "south", "z_max": "north", "x_min": "east", "x_max": "west"}}[p["back_mode"]]
        for x in range(min(ax, bx), max(ax, bx) + 1):
            out.append(stair(x, ay, min(az, bz), face["z_min"], p["half"]))
            out.append(stair(x, ay, max(az, bz), face["z_max"], p["half"]))
        for z in range(min(az, bz) + 1, max(az, bz)):
            out.append(stair(min(ax, bx), ay, z, face["x_min"], p["half"]))
            out.append(stair(max(ax, bx), ay, z, face["x_max"], p["half"]))
        return out

    dx, dy, dz = bx - ax, by - ay, bz - az
    if dx and dz:
        die("run 模式必须轴对齐(a→b 只能沿一个水平轴; L 弯拆两段各跑一遍, 转角交给游戏自动算)", {})
    facing = DIR_FACING[p["back"]]
    if dy == 0:                                 # 平推行
        steps = max(abs(dx), abs(dz))
        sx = 1 if dx > 0 else (-1 if dx < 0 else 0)
        sz = 1 if dz > 0 else (-1 if dz < 0 else 0)
        for i in range(steps + 1):
            out.append(stair(ax + i * sx, ay, az + i * sz, facing, p["half"]))
        return out
    # 上升行: 每步 +1y(或 -1y 下行), facing=上坡方向(自动取行走轴反/正)
    steps = max(abs(dx), abs(dz))
    if abs(dy) != steps:
        die("上升行要求每步恰好 1 格高差: |dy| 必须等于水平步数 %d" % steps, {})
    sx = 1 if dx > 0 else (-1 if dx < 0 else 0)
    sz = 1 if dz > 0 else (-1 if dz < 0 else 0)
    if dy > 0:                                  # 上坡: facing=行进方向
        up = "east" if sx > 0 else ("west" if sx < 0 else ("south" if sz > 0 else "north"))
    else:                                       # 下坡: facing=行进反方向(高背朝上)
        up = "west" if sx > 0 else ("east" if sx < 0 else ("north" if sz > 0 else "south"))
    for i in range(steps + 1):
        if p["smooth"]:                         # 踏面(bottom)/踢面(top)交替
            half = "bottom" if i % 2 == 0 else "top"
        else:
            half = p["half"]
        out.append(stair(ax + i * sx, ay + i * (1 if dy > 0 else -1), az + i * sz,
                         up, half))
    return out


MAT = "minecraft:spruce_stairs"


def validate(p):
    for k in ("a", "b"):
        if len(p[k]) != 3:
            die("%s must be [x,y,z]" % k, {k: "[0,64,0]"})
    if p["mode"] not in ("run", "ring"):
        die("mode must be run|ring", {"mode": "run"})
    if p["back"] not in DIR_FACING:
        die("back must be north|south|east|west", {"back": "north"})
    if p["back_mode"] not in ("out", "in"):
        die("back_mode must be out|in", {"back_mode": "out"})
    if p["half"] not in ("bottom", "top"):
        die("half must be bottom|top", {"half": "bottom"})
    if not str(p["material"]).endswith("_stairs"):
        die("material must be a *_stairs id", {"material": ["minecraft:spruce_stairs",
                                                            "minecraft:stone_brick_stairs"]})


def main():
    global MAT
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    p = dict(DEFAULTS)
    try:
        p.update(json.loads(a.params) if a.params.strip() else {})
    except json.JSONDecodeError as e:
        die("--params is not valid JSON: %s" % e,
            {"example": '{"a":[0,-51,0],"b":[10,-51,0],"back":"north","material":"minecraft:spruce_stairs","half":"top"}'})
    validate(p)
    MAT = p["material"]
    write_out(build(p), a.out)


if __name__ == "__main__":
    main()
