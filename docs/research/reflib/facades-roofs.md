# 参考知识库:立面进深与屋顶细部(facades-roofs)— 2026-07-30

> 来源:explore 子代理,为模式库/风格卡片服务。调研范围:minecraft.wiki 教程族(墙/屋顶类型/曲面屋顶/屋顶装饰/美化)、WesterosCraft 建筑规范、MCS 比例体系、中式建筑社区教程(举折/飞檐/重檐)。审美基准:全程零光影、纯原版方块成立的技法才收录。

## 1. 核心技法

### 1.1 进深的层次(出 1/出 2/入 1 的节奏)
- **三档进深词汇表**:出 2 = 承重感构件(门廊柱、角柱、扶壁);出 1 = 常规细部(壁柱、窗套、腰线、檐口);入 1 = 窗洞/门洞/神龛。一面墙至少同时用两档,单档 = 平板墙。(综合 Grian/Master Builder 与 wiki 墙体教程)
- **节奏密度**:出 1 凸件沿墙间距 **3–6 格**(项目 pilaster 已定 3–6,默认 4),两端必须各落一个;凸件宽 1,超过 1 宽就变成体量而不是细部。
- **阶梯式凸出**:projection=2 时按"下 1/3 出 2、上 2/3 出 1"收分(项目 pilaster 已实现),重心下沉。
- **墙高与细部幅度**:墙高 2–4 时,分割线/收边上下错 **1 格**效果已很明显;墙更高时,顶部和底部各留 **1–2 格**不动,细部集中在中间带(wiki: Walls,flourish 规则)。
- **每面墙选 1–4 种细部手法并全楼统一**(wiki 原话),手法堆叠 = 乱,不是丰富。
- **二维配色也是进深**:双色墙"深下浅上"(下深接地面/基座,上浅接屋顶);渐变中**最深色与最浅色不得直接相邻**,必须有过渡色;深色斑点靠噪声成簇,不逐块随机(WesterosCraft 渐变铁律)。

### 1.2 楼梯/半砖/活板门做细部的惯例
- **楼梯块**:柱头/柱础的帽子与底座(Master Builder);倒置楼梯 = 檐口线脚(coving),层高 ≥6 才用;倒置楼梯沿檐口一圈 = 天沟(gutter);楼梯朝柱 = 墙到顶的过渡件。
- **半砖**:压顶(墙帽、檐口压边、窗台);上下半砖交替 = 22.5° 缓坡屋面;半砖腰线(出半格,最薄的水平线脚)。
- **活板门**:1×2 窗两端竖放 = 百叶窗板;贴墙面 = 假镶板/假抽屉面。**注意**:WesterosCraft 禁用活板门糊墙(客人可扳动 + 贴图差)——生成建筑里活板门只做窗板/小件,不做大面积肌理。
- **按钮/告示牌**:点缀级肌理,撒在石材面上当"碎石/铆钉",密度 ≤1 个/4 格,不可成行成列。
- **栅栏/墙块**:屋脊装饰(见 §1.6)、窗棂、托臂(corbel,出 1 格承托檐口或阳台)。

### 1.3 檐口与腰线位置学
- **竖向三段式**(基座—墙身—檐口):基座出 1、高 1–2;墙身是主面;檐口在**墙顶下 0–1 格**出 1(倒置楼梯或整砖+半砖压边)。
- **腰线(串腰线/string course)**:一条异材质水平带,位置三选一——楼层板标高处(多层建筑默认)、窗台下皮、门窗过梁上皮;出 0(墙面内换材质)或出 1(半砖/整砖凸出);**厚 1 格,一条墙最多 2 条**。
- **平屋顶檐口**:女儿墙(parapet)高 1–2 +  inward 走道 1 格,可把过高屋顶的视高压低 ~2 格(wiki: Roof construction guidelines 的 20m 宽例:11 高 → 视高 7)。
- **中式对照**:斗拱层 = 檐口线脚(柱顶上一圈出挑);重檐下檐定位在上檐**下方 2 格、出挑比上檐多 1 格**(4399 重檐教程)。

### 1.4 窗的"框"怎么凸
- **基本原则:框凸玻凹**。框出 1(项目 window_trim projection=1 已实现),玻璃留在墙面内或退 1;圆形/拱形外框 + 玻璃后置是社区公认的"高级感"做法(wiki: Adding beauty)。
- **凸窗(bay window)**:整窗体量出 1–2、宽 2–3,下用 corbel/楼梯收,自带小屋顶。
- **窗台**:窗框下皮一行半砖(sill),出 1;窗高 1×2 时两端活板门百叶。
- **窗尺寸(MCS)**:舷窗 1×1;地下室窗 1×N;标准窗 2×N;大窗 3×N;窗底距室内地面 1–2(玩家视线)。
- **多层建筑同列窗必须对位**,竖向窗间墙宽 ≥1。

### 1.5 屋顶坡度与建筑宽度的关系
- **坡度配方**:63.4° = 整砖 2 升 1;**45° = 楼梯 1 升 1(默认)**;22.5° = 上下半砖交替 2 进 1;中间坡用"半砖—倒置楼梯—楼梯"循环,5 升 7 进(wiki: Roof construction guidelines)。MCS 角度表:15°=1/3、30°=1/2、45°=1/1、60°=2/1、75°=3/1(y/x)。
- **屋脊高度铁律**:居建筑屋顶高 = **1–2 个层高**;层高 4 → 屋脊高 **5–7**。20m 宽建筑做单坡 45° 人字顶 = 脊高 10–11(2.5 层)→ 必须拆成 2–3 段(每段升 5–7),或加女儿墙压视高。大体量仓房式屋顶是反例。
- **人字顶适用宽度 ≤ ~12**;建筑任一边 >15 就必须分体块、多个屋顶交接(T/L/十字形),不允许一整片(wiki: Roof types / guidelines)。
- **奇偶规则**:屋脊要在正中特色(大门)正上方收尖 → 该向宽度取**奇数**;双开门等偶数中心特色 → 宽度取偶数(两坡各半在屋脊处拼半砖脊)。
- **气候语义**:茅草顶 ≥45°(否则"不防水",WesterosCraft);雪区坡陡、干区坡缓;缓坡(22.5°)只配单层披屋/门廊。
- **体块 >15×15** 或屋顶下空间够一层 → 必须开老虎窗(dormer)或做孟莎顶利用阁楼,否则大片空坡 = 谷仓。

### 1.6 屋脊/檐口的收法
- **正脊**:脊上一行半砖封顶(项目 gable/hip_roof 已做);升级 = 脊上砌**墙块/栅栏行**(装饰脊,wiki: Roof decorations),两端上翘 1 格(鸱尾/脊兽 = 楼梯或整砖端部抬 1–2)。
- **檐口挑檐**:出挑 1–2(项目 overhang 参数),挑檐下必做**椽子观感**——楼梯/半门在檐下间隔 2–3 格排列;**从室内不应看到屋面块底面**(WesterosCraft 椽条规则)。
- **山墙收法三选一**:① 挑出山墙面(默认,overhang);② 阶梯山墙(corbie steps,山墙沿坡度逐格收进,北欧/中式硬山皆宜);③ 女儿墙高出屋面(联排/城市建筑,端部加 corbel 收头)。
- **半歇山(half-hip)配方**:下部 3 行人字坡 + 上部 2.5 行四坡(wiki 实例数字)。
- **盔顶(helm)**:只用于**奇数宽方形塔**,楼梯只朝两个方向,其余用整砖填;7×7 塔是下限尺寸。
- **攒尖/塔尖(cone)**:直径列表法,每 **3–5 格高**才缩一次半径(例:直径 8 → 8,8,8,6,6,6,4,4,4,2,2,2);奇数直径更尖;顶点半径 3 的圈改 4 块菱形摆,尖端加栅栏 1–2 格。
- **穹顶(dome)**:直径列表逐层收环,相邻层直径**同奇同偶**(直径 17 → 17,17,15,15,13,11,9,5);截顶穹顶 = 取更大圆的顶部几行(直径 22 圆 → 14,12,6);鼓座穹顶 = 底部直径重复 N 次抬柱身。曲线半径 <6 时人眼读成折线坡顶,**穹顶是唯一能小尺度成立的曲线**。
- **飞檐(中式凹曲)**:下缓上陡"举折",**3 段上升(大型 4 段)**:半砖做法 = 缓升段升 ½ 格、收尾段升 1 格;整砖做法 = 缓升 1 格、收尾 2 格;出挑外层比内层长(外 3 内 2 / 外 4 内 3 内 2),**内层延伸不得长于外层**;檐角(翼角)末端再上翘 1–2。小尺度做不出凹曲线时用折线近似 + 端部上翘,不要硬弯(wiki: Curved roofs)。

## 2. 范例
1. [Tutorial:Roof construction guidelines — minecraft.wiki](https://minecraft.fandom.com/wiki/Tutorials/Roof_construction_guidelines):坡度配方(63.4°/45°/22.5°)、屋脊高 1–2 层、女儿墙压视高、奇偶宽度规则,本文 §1.5 主源。
2. [Tutorial:Roof types — minecraft.wiki](https://minecraft.fandom.com/wiki/Tutorials/Roof_types):人字/四坡/盐盒/孟莎/盔顶/蝴蝶顶全目录,人字顶 ≤12 宽、孟莎 ≥16×20 的尺度门槛。
3. [Tutorial:Curved roofs — minecraft.wiki(archive)](https://web.archive.org/web/2024/https://minecraft.wiki/w/Tutorials/Curved_roofs):穹顶/攒尖直径列表法、同奇同偶校验、截顶/鼓座变体、曲率半径 ≥6 判据,§1.6 主源。
4. [Tutorial:Roof decorations — minecraft.wiki(archive)](https://web.archive.org/web/2024/https://minecraft.wiki/w/Tutorials/Roof_decorations):装饰脊(墙块压脊)、阶梯山墙、端部女儿墙 + corbel。
5. [Tutorial:Walls and buttresses — minecraft.wiki(archive)](https://web.archive.org/web/2024/https://minecraft.wiki/w/Tutorials/Walls_and_buttresses):双色墙深下浅上、分割线位置学、flourish 幅度(矮墙错 1 格)、coving 用倒置楼梯、1–4 种手法上限,§1.1/§1.3 主源。
6. [Tutorial:Adding beauty to constructions — minecraft.wiki](https://minecraft.fandom.com/wiki/Tutorials/Adding_beauty_to_constructions):窗的进深(凸窗/圆框玻凹)、活板门百叶、楼梯做墙顶过渡。
7. [WesterosCraft: Basic Building Guide(archive)](https://web.archive.org/web/2024/https://westeroscraft.fandom.com/wiki/Basic_Building_Guide_for_Applicants):零光影审美标杆——渐变三色不直接相邻、深色斑点近地面、茅草 ≥45°、椽条规则(室内不见屋面底)、拒绝立方体体量。
8. [Minecraft Architectural Standards(MCS)— Minecraft Forum](https://www.minecraftforum.net/forums/minecraft-java-edition/creative-mode/365473-minecraft-architectural-standards-block-system):窗尺寸表(1×1/1×N/2×N/3×N)与屋顶角度—坡度对照表,§1.4/§1.5 数据源。
9. [中国风建筑教程:屋顶弧度 — 百度经验](https://jingyan.baidu.com/article/08b6a591a5db8b14a9092256.html):举折 3–4 段、半砖/整砖两套升跌数字、外长内短收分,§1.6 飞檐主源。
10. [中式屋顶重檐图文教学 — 4399](https://m.4399.cn/news-id-567127.html):柱高 7 间距 3、下檐低 2 格出挑多 1 格、翘角做法。
11. [Plotz Sphere Generator](https://www.plotz.co.uk/minecraft-sphere-generator.php):穹顶/球体逐层蓝图生成器,直径 >18 时替代手工直径列表。

## 3. 反例
- **平板墙(full flat)**:单材质、零进退、无基座无檐口的方盒子——wiki 与 WesterosCraft 共同点名的一号错误。validator 应检测:任一墙面连续 ≥7×4 格无凸出/无材质变化 → 报警,强制加基座 + 檐口 + 一档出 1 细部。
- **细部无节奏乱贴**:凸件间距忽 2 忽 6、渐变深浅色直接相邻、褪色块随机单点撒(茅草顶"花斑狗"反例)、一面墙堆 >4 种手法。规则:间距等差、渐变有过渡色、色斑成簇(噪声掩码)、手法 ≤4 种全楼统一。
- **屋顶坡度与体量不符**:宽度 >12 还做单片人字顶、>15×15 只盖一整片屋顶、屋脊高 >2 层无老虎窗无分段(谷仓感)、小房子压孟莎顶、曲率半径 <6 硬凹曲线(读成折线事故)。规则:roof_rise ∈ [story, 2×story],超出 → 拆体量或加女儿墙。

## 4. 对模式库的建议
已有:`pilaster`(出 1–2 壁柱)、`window_trim`(框凸 0/1 窗套)、`gable_roof`/`hip_roof`(45° 坡 + 脊半砖 + overhang)、`buttress`、`arch_window`、`crenellation`。风格卡片 `details.depth` 已声明 `string_course` 但**无对应模式文件**——最优先补。

按优先级:
- **string_course(腰线)**:参数 `height`(默认=楼层板标高)、`projection(0/1)`、`material`、`thickness(1)`;绕四面墙连续,遇门窗洞口断开让行。直接兑现卡片里已有的声明。
- **cornice(檐口线脚)**:墙顶下一圈,`style(stairs_upside_down/slab/blocks)`、`projection(1)`;与屋顶 overhang 联动:有挑檐时檐口在墙顶,平屋顶时升级成 parapet(高 1–2)。
- **ridge_decor(装饰脊/脊兽)**:在现有 `ridge_material` 之上叠加 `style(wall_row/upturned_ends)`,端部抬 1–2 格做鸱尾;中式卡片必配。
- **flying_eave(飞檐)**:参数 `stages(3/4)`、`unit(half/full)`(半砖举折升 ½→1,整砖升 1→2)、`overhang(外3内2)`、`corner_upturn(1–2)`;输出凹曲檐口 + 翘角,作为 gable/hip_roof 的檐边修饰层而非独立屋顶。
- **dome(穹顶)/cone_spire(攒尖)**:直径列表生成器,内置同奇同偶校验;`variant(hemisphere/segmented/surmounted)`;直径 ≤18 内置查表,>18 走算法。
- **stepped_gable(阶梯山墙)**:gable 端墙沿坡度逐格收进的端部收法,与现有 `end_fill` 参数联动。
- **bay_window(凸窗)**:出 1–2 的窗体量 + corbel 底托 + 小屋顶,复用 window_trim 做框。
- **validators 增补**:① 平板墙检测(连续大面无进退/无换色);② 屋脊高/层高比 ∈ [1,2];③ 渐变相邻色阶差 ≤1 档;④ 檐口下室内视点可见屋面块 → 提示加椽条/吊顶。
