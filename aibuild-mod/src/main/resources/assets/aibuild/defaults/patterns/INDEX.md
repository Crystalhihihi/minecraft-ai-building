# 建造百科·索引卡(先读我)

> 本目录是所有可用资料的清单。**按需取用,不要全读**:任务书点名的卡必读,其余 Glob 文件名 + 本索引自取。
> 格式:风格卡(styles/)= JSON;模式卡(patterns/)= JSON 参数卡 + 同名 .py 生成器;规则文档= .md;验收器= patterns/validators/*.py(--params '{"blocks":"..."}')。

## 卡格式 v2(新卡必守)

- `use_for`:用途标签(风格/体量/构件),供匹配下发
- `pitfalls`:禁忌(常见错误摆法,写明即少犯)
- `validators`:本卡产物应过哪些验收器
- 几何规则必须参数化;朝向/半砖/转角由脚本推导,禁止手填

## 风格卡 styles/

| 卡 | use_for |
| --- | --- |
| plains_cabin | 平原小木屋/农舍,5×7~9×11 |
| medieval_tower | 中世纪塔楼 |
| waterfront_dock | 滨水码头 |
| stilt_house | 吊脚楼 |
| nordic_villa | 北欧别墅 |
| suzhou_garden | 苏州园林(中式) |

## 模式卡 patterns/(均有同名 .py 生成器)

| 卡 | use_for |
| --- | --- |
| gable_roof | 双坡屋顶(收分/屋脊/山墙) |
| hip_roof | 四坡屋顶 |
| dormer | 老虎窗(gabled/shed/hipped 三变体,窗洞切进坡面带 air 开凿) |
| gambrel_roof | 折线屋顶(下陡上缓,谷仓/荷兰殖民式) |
| mansard_roof | 孟莎屋顶(四向陡坡+顶部平台,大体量) |
| helm_roof | 盔顶(方塔四山墙,楼梯只两向+中缝半砖) |
| chimney | 烟囱(1×1/1×2/2×2 柱身+检修台泛水圈+campfire 冒烟/活板门压顶) |
| crenellation | 垛口/女儿墙 |
| buttress | 扶壁 |
| arch_window | 拱窗 |
| window_trim | 窗套(凸 0/1) |
| pilaster | 壁柱 |
| road_segment | 路段 |
| terraform_pad | 场地整平 |
| quadruped_statue | 四足雕像 |
| mirror_build | 镜像建造 |
| furniture | 家具图鉴(床/桌/椅/凳/沙发/书架/橱柜/厨台/书桌/落地灯/花盆/长椅/抽屉柜/壁炉/钢琴,piece 参数选件) |

## 规则文档

- `patterns/stair_orientations.md`:楼梯朝向铁律(facing=高侧;围合转角必用 corner shape;正放倒放叠放;光滑上升梯段)
- `patterns/roof_types.md`:屋顶选型速查(13 种顶型一句话+参数起点;老虎窗什么时候加;檐口/屋脊装饰;材料比例)
- `blocks.md`:常用方块 id 速查

## 验收器 patterns/validators/

| 器 | 查什么 |
| --- | --- |
| support_check | 悬空块/浮空上半砖 |
| slab_check | 半砖 type 缝/悬空上半砖(屋顶漏空) |
| stair_corner_check | 围合框架转角必须是 corner shape |
| symmetry_check | 对称性 |
| collision_check | 重叠冲突 |
