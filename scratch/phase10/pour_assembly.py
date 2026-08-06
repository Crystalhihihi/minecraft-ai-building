#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pour_assembly.py — R10 拼装真实灌入验证(纪律:不信离线,读回才算数)。

1) 平移 assembly_merged.json 到目标点 + 建筑上空清表空气
2) confirm_site(master 后门) + place 灌入
3) 逐格读回比对 id
4) 用真实读回的方块跑 walkability_check(主门→附属体块)
跑法: cd scratch/phase10 && python pour_assembly.py --at 500 70 40
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, r"D:\建筑资产\验证")
sys.path.insert(0, r"D:\minecraft-ai-building\aibuild-mod\src\main\resources\assets\aibuild\defaults\patterns")
sys.path.insert(0, r"D:\minecraft-ai-building\aibuild-mod\src\main\resources\assets\aibuild\defaults\patterns\validators")

import bridge, verify, walkability_check  # noqa: E402

HERE = Path(__file__).parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", nargs=3, type=int, required=True, help="目标点(原 local 原点 0,64,0 的落点)")
    args = ap.parse_args()
    tx, ty, tz = args.at
    dx, dy, dz = tx, ty - 64, tz

    raw = json.loads((HERE / "assembly_merged.json").read_text(encoding="utf-8"))
    blocks = [{"x": b["x"] + dx, "y": b["y"] + dy, "z": b["z"] + dz, "block": b["block"]}
              for b in raw["blocks"]]
    xs = [b["x"] for b in blocks]; ys = [b["y"] for b in blocks]; zs = [b["z"] for b in blocks]
    mn = [min(xs) - 2, min(ys) - 1, min(zs) - 2]
    mx = [max(xs) + 2, max(ys) + 5, max(zs) + 2]
    # 清表: 建筑上方(地板+1 到顶+5)全部空气, 含周边 2 格
    clears = []
    for x in range(mn[0], mx[0] + 1):
        for z in range(mn[2], mx[2] + 1):
            for y in range(min(ys) + 1, mx[1] + 1):
                clears.append({"x": x, "y": y, "z": z, "block": "minecraft:air"})
    pour = clears + blocks   # 先清后建
    f = HERE / "assembly_pour.json"
    f.write_text(json.dumps({"blocks": pour}, ensure_ascii=False), encoding="utf-8")

    r = bridge.post_json("/tools/confirm_site", {"min": mn, "max": mx})
    print("confirm_site:", json.dumps(r, ensure_ascii=False)[:140])

    class A: pass
    a = A(); a.blocks = str(f); a.session = r.get("session"); a.token = None
    a.batch = 4096; a.timeout = 600; a.game_dir = bridge.DEFAULT_GAME_DIR
    verify.cmd_place(a)

    # 读回比对(只看建筑块, 不看清表空气)
    fails = []
    for b in blocks:
        rb = bridge.post_json("/tools/get_block", {"x": b["x"], "y": b["y"], "z": b["z"]})
        exp = b["block"].split("[")[0]
        if rb.get("block") != exp:
            fails.append("%s,%s,%s 期望 %s 实际 %s" % (b["x"], b["y"], b["z"], exp, rb.get("block")))
    print("读回比对:", "全过" if not fails else "%d 处不符" % len(fails))
    for x in fails[:10]:
        print("  FAIL", x)

    # 真实方块跑 walkability: 区域全部读回(含空气)
    real = []
    for x in range(mn[0], mx[0] + 1):
        for z in range(mn[2], mx[2] + 1):
            for y in range(mn[1], mx[1] + 1):
                rb = bridge.post_json("/tools/get_block", {"x": x, "y": y, "z": z})
                blk = rb.get("block", "minecraft:air")
                if blk != "minecraft:air":
                    real.append({"x": x, "y": y, "z": z, "block": blk})
    rf = HERE / "assembly_real.json"
    rf.write_text(json.dumps({"blocks": real}, ensure_ascii=False), encoding="utf-8")
    door_local = [0, 65, 2]      # assembly_test 打印的主门外落点
    annex_req = [12, 65, 3]
    w = walkability_check.check({
        "blocks": str(rf),
        "door": [door_local[0] + dx, door_local[1] + dy, door_local[2] + dz],
        "require": [[annex_req[0] + dx, annex_req[1] + dy, annex_req[2] + dz]]})
    ok = w.get("ok") and all(q.get("reachable") for q in w.get("requires", []))
    print("真实 walkability:", json.dumps(w, ensure_ascii=False)[:240])
    print("结果:", "全绿" if ok and not fails else "有问题")
    sys.exit(0 if ok and not fails else 1)


if __name__ == "__main__":
    main()
