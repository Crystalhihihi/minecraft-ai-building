# 参考知识库:内饰与内部空间布局 — 2026-07-30

> 来源:explore 子代理。数字均为 MC 原生方块(1 格 = 1 m,玩家高 1.8 格),版本基准 1.18+ 光照机制。

## 1. 核心技法

### 1.1 层高与房间尺度(MCS 标准,Minecraft Forum)
- 层高:阁楼/地窖 2;小屋/温馨 3;舒适标准 **4**;挑高 5;教堂/大厅 6–8。
- 门洞:原生门 1 宽 × 2 高;双开门 2×2;入口大厅门可 2×3。
- 房间净尺寸(宽 × 深,格):
  - 起居:小 8×9 / 中 11×11 / 豪 14×14
  - 厨房:小 6×8 / 中 8×9 / 大 11×11
  - 卧室:小 8×9 / 大 10×11 / 主卧 12×13
  - 卫浴:半浴 6×7 / 标准 7×9 / 主卧浴 9×10
- 墙厚:普通 1;贴面/双层 2;防御性 ≥3。楼层板厚 1(阁楼/地窖)~2(标准)。

### 1.2 功能分区(起居/餐厨/卧/浴)
- **地板材质即分区语言**:换材质 = 换空间,无需砌墙(Wiki: Making nice floors)。
  - 餐厨 → "瓷砖感":磨制安山岩+磨制闪长岩交替,或黑白混凝土棋盘格
  - 起居/门厅 → 彩色羊毛/混凝土居中图案,或带釉陶瓦,外围木板收边
  - 卧室 → 个性化:羊毛/地毯/深色方块
  - 储藏/地下室 → 圆石、安山岩+闪长岩随机混合(侵蚀感)
- 厨房台沿墙一排整砖(石砖/木板),地面用石质不用木板(社区惯例)。
- 几何语义:居中对称图案 → 视觉聚焦(门厅);棋盘/密铺 → 空间显大(小房间)。

### 1.3 动线与边距
- 走廊:1 格能走但压抑;**2 格 = 舒适标准**;主廊 3 格(MCS + Forum 共识)。
- 家具默认贴墙;独立家具(餐桌、茶几)四周留 ≥1 格通行,理想 2 格。
- 沙发前留 1–2 格放台阶茶几;书桌贴墙可省 1 格进深。
- 壁炉安全:可燃物距火焰方块 <4 格高或相邻会被点燃; campfire 不引燃邻块但仍灼伤实体(Wiki: Furniture)。

### 1.4 楼梯井
- 宽度:辅助梯 1,主楼梯 **2**;梯上净高 ≥2(玩家 1.8),建议 3。
- 扶手:栅栏/圆石墙/玻璃板,外侧一格即可;转角用楼梯块自动连接。

### 1.5 照明点位与防刷怪(1.18+)
- 敌怪只在**方块光 0** 生成 → 目标:每格光级 ≥1 即可,不必满亮。
- 火把/灯笼光级 14,每格衰减 1 → 平面间距 ≤12(无暗角);室内建议 **8–10** 交错布点;萤石/海晶灯/菌光体光级 15,间距可放宽 1。
- 隐藏光:光源埋地板下盖**地毯**(地毯不挡光)、或藏画后/台阶下。
- 零光源防刷怪:下半砖、地毯、玻璃、按钮、压力板、铁轨覆盖的地面不刷怪(Wiki: Spawn-proofing)。
- 吊灯:链条自顶垂下 + 中心块 + 栅栏/末地烛臂 + 灯笼;**底端距地 ≥2**(层高 4 时挂第 3 格),否则撞头。

### 1.6 天花板/地板搭配
- 地板两色交替出"精致感":原木+木板、磨制安山岩+闪长岩、黑白混凝土。
- 天花比地板**浅一档**(白/桦木/石英)防压抑,层高 3 时尤其重要。
- 层高 ≥4 加原木横梁降视觉高度;梁下可挂吊灯补足中部光。
- 大床注意:床上方留 ≥2 格净空,否则出生点判定失败/起床卡头(Wiki: Furniture)。

## 2. 范例
- [Tutorial:Furniture — minecraft.wiki](https://minecraft.wiki/w/Tutorials/Furniture):家具方块语汇总集(沙发=楼梯+告示牌扶手、桌=栅栏+压力板、壁炉安全半径 4 格)。
- [Tutorial:Making nice floors — minecraft.wiki](https://minecraft.wiki/w/Tutorials/Making_nice_floors):两色交替地板公式 + 按房间类型选地板材质的分区建议。
- [Tutorial:Spawn-proofing — minecraft.wiki](https://minecraft.wiki/w/Tutorial:Spawn-proofing):1.18+ 光 0 生成规则,火把间距 ~14 上限,下半砖/地毯免照明方案。
- [Minecraft Architectural Standards — Minecraft Forum](https://www.minecraftforum.net/forums/minecraft-java-edition/creative-mode/365473-minecraft-architectural-standards-block-system):MCS 比例体系,层高/墙厚/窗尺寸/各房型净尺寸全表,本文 §1.1 主源。
- [Minecraft Mob Spawning Mechanics — gamqo](https://gamqo.com/minecraft-mob-spawning-mechanics/):开阔区火把间距 12、走廊 6–8 的实操值。
- [How far apart should torches be — ORBISPatches](https://orbispatches.com/gaming-faq/how-far-do-torches-prevent-mobs-from-spawning):1 宽隧道地面火把每 13 格、眼高每 11 格的精确间距。
- [Minecraft Chandelier Ideas — ExitLag](https://www.exitlag.com/blog/minecraft-chandeliers-creative-lighting):吊灯结构套路(链+中心块+臂+光源)。
- [Tutorial:Adding beauty to constructions — minecraft.wiki](https://minecraft.wiki/w/Tutorials/Adding_beauty_to_constructions):通用美化原则,深度/细节与内饰互补。

## 3. 反例
- **家具卡墙/卡头**:楼梯沙发的告示牌扶手嵌进墙体;吊灯底端距地 <2 格;床上方净高 <2 → 出生点失效。生成时必须做碰撞与净高校验。
- **大空厅**:14×14 房间只放一桌一椅,或层高 5+ 无梁无吊灯,上半截全空 — 房间尺度必须与家具清单联动(§1.1 表),家具占地不足就缩房或加分区。
- **照明死角**:只在房间中心放 1 个光源,四角光级 0 → 夜间室内刷怪。必须逐格校验 min light ≥1,角落和家具阴影处是漏点高发区。

## 4. 对模式库的建议
- **家具套件**参数化:`type(sofa/chair/table/desk/shelf/bed/dresser/counter)`、`length(2–6)`、`material_palette`、`armrest(bool)`、`wall_attached(bool)`、`facing`;桌类加 `leg_style(fence/piston/stairs)`。所有件带包围盒,接入碰撞 validator。
- **楼梯井**参数化:`width(1–2)`、`headroom(≥2,默认3)`、`railing(fence/wall/pane/none)`、`landing(bool)`;转角复用已有楼梯连接逻辑。
- **吊灯**参数化:`drop(1–3)`、`chain_len`、`arms(0/4)`、`source(lantern/end_rod/shroomlight/glowstone)`,约束 `ceiling_y − drop ≥ floor_y + 2`。
- **照明求解器**:对房间体素逐格算光级,贪心补灯直到 min ≥1;候选点位 = 天花(吊灯/嵌入)+ 地板下隐藏光,默认间距 8。
- **房间模板**:`room_type(living/kitchen/bed/bath/storage) × size(s/m/l)` 查表 → 净尺寸 + 地板材质对 + 家具清单 + 照明密度,直接对接 §1.1/§1.2 的数字。
