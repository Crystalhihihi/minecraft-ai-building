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
| medieval_house | 中世纪民居/客栈/铁匠铺,木骨石基+上层悬挑(jetty),7×9~13×15 |
| medieval_tower | 中世纪塔楼 |
| waterfront_dock | 滨水码头 |
| stilt_house | 吊脚楼 |
| nordic_villa | 北欧别墅 |
| modern_house | 现代民居(白盒+灰底+大玻璃,平顶),11×9~21×15 |
| tree_house | 树屋(干穿屋+小屋吊桥+镂空叶团),5×5~9×9 |
| sakura_japanese | 樱花风日式民居/仓库(石基木骨白壁+深瓦缓坡深檐),7×9~13×11 |
| castle_fortress | 城堡/军事要塞(石砖掺旧+垛口+扶壁+门楼),主楼 9×9~15×15 |
| church_chapel | 教堂/礼拜堂(高厅+竖长尖拱彩窗+陡坡+塔尖),小堂 7×13 起 |
| brick_townhouse | 砖石联排屋(窄面宽多层+窗列对位+烟囱阵),面宽 5~9 |
| farm_estate | 农场庄园(主屋+折线顶谷仓+场院围栏+梯田),场院 21×21 起 |
| suzhou_garden | 苏州园林(中式) |
| chinese_palace | 中式殿堂/官式建筑(歇山顶+斗拱+高台基+中轴对称),主殿 9×13~15×21 |
| elven_tree | 精灵树居(有机白壁+圆平面+活树干贯穿),主室直径 7~11 |
| desert_adobe | 沙漠/中东土坯(砂岩陶土+平顶女儿墙+穹顶+拱廊内院,厚墙小窗) |
| japanese_castle | 日式天守阁(石垣收分+白壁+叠层歇山+千鸟破风;xieshan_roof 复用) |
| gothic_cathedral | 哥特主教堂(十字平面+双塔西立面+大玫瑰窗+束柱高厅) |

## 模式卡 patterns/(均有同名 .py 生成器)

| 卡 | use_for |
| --- | --- |
| gable_roof | 双坡屋顶(收分/屋脊/山墙) |
| roof_plan | 组合平面屋顶(L/T/U 分翼垂直相交+45°谷沟; 与 plan_shape 同 seed; 组合平面禁用单坡卡) |
| hip_roof | 四坡屋顶 |
| dormer | 老虎窗(gabled/shed/hipped 三变体,窗洞切进坡面带 air 开凿) |
| gambrel_roof | 折线屋顶(下陡上缓,谷仓/荷兰殖民式) |
| mansard_roof | 孟莎屋顶(四向陡坡+顶部平台,大体量) |
| helm_roof | 盔顶(方塔四山墙,楼梯只两向+中缝半砖) |
| xieshan_roof | 歇山顶(下段四坡收肩+上段双坡垂直山花;东亚通用句法,只沿 z 收分) |
| dome | 穹顶(hemisphere/paraboloid/onion 三 profile;ellipse 圆切片;顶部实芯收口) |
| roof_curve | 分段曲线屋顶(六段式举折:classic_chinese/gentle/steep 段表+段界斜率混淆;实芯脊) |
| chimney | 烟囱(1×1/1×2/2×2 柱身+检修台泛水圈+campfire 冒烟/活板门压顶) |
| dougong | 斗拱(檐下柱位层叠出挑承托,斗座+倒放楼梯拱+顶枋;东亚通用句法) |
| crenellation | 垛口/女儿墙 |
| buttress | 扶壁(stepped 3-2-1 收分 / flying 飞扶壁:墩+斜拱臂+可选尖塔,哥特高厅隔间构件) |
| arch_window | 拱窗 |
| rose_window | 哥特玫瑰窗(辐条+外圈+玻璃填充,嵌墙 air 开凿;ellipse 复用) |
| window_trim | 窗套(凸 0/1) |
| pilaster | 壁柱 |
| facade_depth | 立面纵深(三段式:基座放脚/墙身线脚壁龛/檐口封檐+交接专章;profile 机制,统计校准) |
| timber_structure | 木构梁架(三角屋架 3 种/托臂/45°斜撑/梁端收分/暴露节奏;间距校准 2-5) |
| road_segment | 路段 |
| terraform_pad | 场地整平 |
| quadruped_statue | 四足雕像 |
| windmill_blade | 风车叶片(4 叶 X/+ 形,骨架+可选半砖蒙布;旋转角脚本推导) |
| mirror_build | 镜像建造 |
| furniture | 家具图鉴(床/桌/椅/凳/沙发/书架/橱柜/厨台/书桌/落地灯/花盆/长椅/抽屉柜/壁炉/钢琴,piece 参数选件) |
| balcony | 阳台(cantilever 挑板/recessed 凹进;support 托臂/立柱;railing 四材质) |
| railing | 护栏/栏杆(fence/wall/pane/trapdoor+楼梯扶手+桥栏;转角自动推导) |
| wall_weathering | 墙壁肌理(掺比 preset/基座深浅分层/壁柱线脚分格/垂藤做旧) |
| accent_detailing | 点缀学(碎件依附结构缝/成组 2~3/密度随面宽;palette=风格白名单 L4a:medieval/japanese/elven/industrial;seed 确定性) |
| interior_rooms | 房间陈设模板(bedroom/kitchen/living/dining/study/corridor;碰撞+通道自动校验) |
| staircase | 室内楼梯(straight/L/U 三形态+扶手+梯腹;facing=上行方向全自动推导,治手摆楼梯放歪) |
| fountain | 喷泉(圆/方,1~3 层,楼梯/半砖压边,中心墙柱) |
| flower_field | 花海/花境(single/stripes/gradient/meadow;小径穿插;边缘渐稀) |
| terrace_farm | 梯田(层高差 1、宽 2~4,田埂压边,zigzag 层间下灌) |
| plaza | 广场铺装(同心圆/放射/棋盘/镶边;中心点缀位;灯椅节奏) |
| garden_tree | 庭院小树(<=4 格冠; 橡/桦/樱/杉; 更大的树一律 giant_tree) |
| giant_tree | 巨树/景观大树(空间殖民+形态卡: 直/弯/斜/螺旋干, 云片分层冠, 板根; 11 preset 形态卡; 高 10-60) |
| round_plan | 圆环墙/收分圆塔(taper 逐层内收;solid 实心/空心;cap 封盘;圆塔/灯塔/精灵圆屋) |
| altar | 祭坛(多层台座+顶饰) |
| settlement | 聚落布局(产 scene 空间计划非方块;grid/radial/organic/park) |
| scene_load | scene 计划重建为方块(pattern 构件调生成器,style 地块产占位建筑;可选地形适配+碰撞避让) |
| plan_shape | 平面形状(rect/L/T/U/rect_bump/O围合/cluster簇群;构图轴语料校准;治只会矩形) |
| connector | 体块连接件(open露天桥/covered连廊/enclosed走廊;cluster 簇群必配;门洞清单输出) |
| clutter_pile | 杂物堆(干草/原木/箱桶/劈柴;seed 随机游走簇形,治无菌感) |
| wear_path | 踩出来的路(两点间 seed 扰动带弯;dirt_path+渐稀收边;轻重磨损档) |
| room_partition | 分房生成器(回刀式二分+隔墙吸附开间网格+门树动线;内置 BFS 可达校验,不可达 die;输出 rooms/window_hints 供 interior_rooms 与外墙开窗对齐) |
| roof_ornament | 屋脊装饰(chinese 鸱吻脊兽/gothic 尖塔/japanese 鬼瓦/european 脊冠风向标;白名单分风格) |

> 公共模块:`patterns/ellipse.py`(圆/椭圆栅格化 circle_ring/ellipse_ring/disc,**单一来源**——后续 dome/rose_window 等新卡必须复用,禁止各写一份);`patterns/contract_check.py` 为卡-代码契约校验工具(开发期用,不进世界工作目录)。

## 规则文档

- `patterns/stair_orientations.md`:楼梯朝向铁律(facing=高侧;围合转角必用 corner shape;正放倒放叠放;光滑上升梯段)
- `patterns/roof_types.md`:屋顶选型速查(13 种顶型一句话+参数起点;老虎窗什么时候加;檐口/屋脊装饰;材料比例)
- `patterns/wall_weathering.md`:墙壁肌理规则(掺比公式/上浅下深/做旧手法)
- `patterns/interior_layout.md`:室内布局规则(分房五步法/最小开间/走廊与动线/家具尺度/门窗对位)
- `blocks.md`:常用方块 id 速查

## 验收器 patterns/validators/

| 器 | 查什么 |
| --- | --- |
| support_check | 悬空块/浮空上半砖 |
| slab_check | 半砖 type 缝/悬空上半砖(屋顶漏空) |
| stair_corner_check | 围合框架转角必须是 corner shape |
| symmetry_check | 对称性 |
| collision_check | 重叠冲突 |
| walkability_check | 可进入性(门口 flood-fill,2 格净空能否走到每个家具前;治"有内饰人进不去") |
