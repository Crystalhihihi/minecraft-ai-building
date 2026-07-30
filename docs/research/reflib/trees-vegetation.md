# 参考知识库:树与植被(大型自定义树/奇幻树)— 2026-07-30

> 来源:explore 子代理。数字均为 MC 原生方块(1 格 = 1 m),版本基准 1.21.11(leaf litter / firefly bush / pale oak 全可用)。
> 零滤镜原则:凡标注"原生画面"的源均无光影,无光影下成立才算数;标注"光影存疑"的展示只取剪影与结构,不取氛围。

## 1. 核心技法

### 1.1 树干渐细与弯曲节奏
- **Fibonacci 分段渐细**(PMC 配套指南,Avomance 法):主干柱 47 高示例;自顶向下 **5 / 8 / 13 / 21** 格处标记收窄区,逐段围墙高 **13 → 8 → 5** 形成三阶渐细;顶端再加 3–8 格"树梢棍"。
- 塑形三手法:改段高(±1–3)、单侧加块对侧减块(整段平移 1 格)、向某角平移。干身保持"相对规则",夸张留给枝与根。
- **弯曲节奏**(DiamondLobby):小树第 **3** 格就开始分叉;大树 3×3 基座,弯曲 = 每 **2–4** 格侧移 **1** 格(示例:高 4 处右移 1,再上 2 格再移 1)。
- **倾斜即叙事**:主干倾斜时,大多数枝朝倾斜方向生长,反方向只留 1 根(DiamondLobby)。
- 综合判据:干基粗 / 总高,小树 ≈ 1/4,巨树 ≈ 1/8(由 §2 各案例反推,非原文数字)。

### 1.2 板根 / 根脚
- **数量克制**(PMC):全树主根 **3–5 条** —— 斜根 1–2 + 直根 1–3;**绝不八面均匀**长根。
- 根曲线 = 抛物线,步长用 Fibonacci **1,1,2,3…**(前几级垂直、后几级水平的过渡)。
- **根-干联动**:根低则该侧干段降、根高则升,环绕主干形成一条起伏螺旋(PMC)。
- 根脚原木高出地面 ≤ **2–3** 格(DiamondLobby);混 `mangrove_roots` / `muddy_mangrove_roots` 出绞杀感;基座换 coarse dirt 铺底(AstroWorld)。

### 1.3 枝干分叉角度与层次
- **铁律:绝不两根枝同高、同形**(DiamondLobby)。一低一短、一高一长;枝"离干远"优先于"长得高"。
- 主分叉 Y 型,近顶再分一次(AstroWorld);分叉角度/方位全部不等。
- 枝走抛物线,Fibonacci 步长;橡树型枝序示例 **8,5,3,2,1 | 1,2,3,5,8**(两侧镜像但上下错位,PMC)。
- 微件:弯折处垫**楼梯/台阶**显粗(视觉渐细);栅栏/墙作细枝梢(DiamondLobby)。
- **叶只挂枝梢与细枝,干上几乎不直接长叶** —— 与原版树的最大区分点(4netplayers)。

### 1.4 树冠团簇:大小 / 间距 / 密度
- 团簇生长流程(DiamondLobby):枝梢 **1 格叶环** → 逐层外扩(**枝基处最宽**) → 轮廓**圆不圆方** → 向上每层内收 1 成穹顶 → 相邻团簇**合并** → 再加减侵蚀出参差。
- 密度分层:**枝下叶量 < 枝上叶量**;冠顶最厚。
- 先实后雕(AstroWorld):实块堆出宽圆冠,四向探出枝架之外,再**凿穿洞**让光斑透下(dapple),边缘半径抖动 ±1–2。
- 团簇间留 0–2 格缝隙;两色叶混合(综合)。

### 1.5 树叶材料搭配(几种叶 + 点缀)
- 主叶 **2 色混合**(AstroWorld);同树种可混 azalea / flowering azalea 出花树。
- 奇幻替代(DiamondLobby):樱花 = 粉羊毛 + 粉陶瓦 + 粉染色玻璃;秋色 = 多色羊毛混合;垂柳 = 近垂直栅栏枝 + 藤蔓垂 2–5 格。
- 点缀层:spore blossom 悬于冠内(持续落花粒子)、藤蔓/垂根/发光浆果藤垂坠、樱花叶自带花瓣粒子。
- 地面落叶:1.21.5+ 用 `leaf_litter`(1–4 层);旧版做法 = 地毯 + 按钮 + 混凝土粉末(DiamondLobby)。

### 1.6 发光元素嵌入(萤石/菌光体位置学)
- 光级表:`shroomlight` / `glowstone` / `sea_lantern` / `froglight` = **15**;灯笼 15(挂低枝下垂 1–3);`glow_berries` 藤 14;`glow_lichen` 7;`firefly_bush` 2(1.21.5+,带萤火虫粒子)。
- **三点位**(AstroWorld + Reddit):① 藏枝干间、冠缘**内埋 1–2 格**(叶对光衰减约 1/格,光能渗出表面);② 低枝悬挂灯笼;③ 干身 glow lichen 补丁。
- 照亮**冠底**一举两得:防刷怪 + 夜景轮廓光(AstroWorld)。
- shroomlight 优于 glowstone 的工程点:实体方块、可承重、透红石信号(minecraft.wiki)。
- 反"光污染":发光藤满挂显 tacky(Reddit 照明帖),优先内嵌 + 点光,忌均布。

### 1.7 大型树的尺度控制
- 起步线(AstroWorld):要"读作自定义树",干 ≥ **2×2**、≥ **10** 高;巨型主角树 **30+**。
- **反棒棒糖判据:冠宽 > 干高**;冠宽 ≈ **1.5×** 冠高(AstroWorld)。
- 案例标尺:Avomance 徒手巨树 ≈ **70** 高;Teldrassil 复刻 addon = **360** 高(极端)。
- 自检法:关光影看剪影 —— 棒棒糖与蘑菇轮廓在原生画面下立现(Reddit 反例帖)。

### 1.8 植被点缀(地表 + 干身)
- 树下环带 ≈ 冠幅半径:蕨 / 草 / 杜鹃丛 / 苔藓地毯 / 野花 / leaf litter;阴面加棕红蘑菇。
- 干身:藤蔓、苔藓块、glow lichen、hanging roots(根拱下)。
- 每树 2–4 种点缀,沿滴水线成环,忌均匀撒布(综合)。

## 2. 范例
- [Avomance — How to Build a GIANT Custom Tree Freestyle](https://youtu.be/lOklBDwfPM4):徒手无 WE 建 ≈70 格巨树,**原生画面**,流程派主源。
- [PMC 配套图文指南(web.archive 镜像)](https://web.archive.org/web/2023/https://www.planetminecraft.com/blog/a-companion-guide-to-avomance-s-how-to-build-a-giant-custom-tree-freestyle-tutorial/):Fibonacci 分段 / 根曲线 / 枝序数字全集,§1.1–1.3 主源。
- [DiamondLobby — How to Build a Custom Tree](https://diamondlobby.com/minecraft/how-to-build-custom-tree-in-minecraft/):分叉不对称铁律、团簇生长流程、材料替代表,**原生画面**,§1.3–1.5 主源。
- [AstroWorldMC — Custom Tree 五阶段指南](https://guide.astroworldmc.com/how-to-build-a-custom-tree):反棒棒糖比例数字 + 藏光三点位,§1.4/1.6/1.7 主源。
- [4netplayers — Minecraft Tree Design](https://www.4netplayers.com/en/blog/minecraft/minecraft-build-your-own-trees/):"叶挂枝梢"原则与五步法。
- [The ULTIMATE GUIDE to Building CUSTOM TREES (2026)](https://www.youtube.com/watch?v=8ldF8-2_lIA):最新综合视频指南,干/枝/冠三段框架,社区共识现状快照。
- [Custom Glowing Tree Designs](https://www.youtube.com/watch?v=sMdOIyDZKZM):萤石树 / 魔法树等发光奇幻树具体设计合集。
- [Solongo_Pixels — How to build Fantasy Tree](https://www.youtube.com/watch?v=3vfrCAOIPg4):中小型奇幻树逐格教程,适合拆参数。
- [Yggdrasil 世界树 Timelapse (2024)](https://www.youtube.com/watch?v=iWtVuHC5nNA):超大尺度世界树展示;光影加持,只取剪影与枝干结构。
- [r/Minecraft 双周挑战 #151:World Tree](https://www.reddit.com/r/Minecraft/comments/v5nn1l/minecraft_biweekly_build_challenge_151_world_tree/):社区世界树作品集中帖,风格样本库。
- [Teldrassil 复刻 addon](https://creativemode.net/mod/teldrassil-vlzltd5d):360 格单树极端尺度参考(WoW 世界树 1:1 意图)。

## 3. 反例
- **棒棒糖 / 蘑菇树**:干细长无渐细 + 顶上一个小球冠,冠宽 ≤ 干高即中招(AstroWorld 判据);Reddit 奇幻城大树被群评"某些角度像蘑菇",病因正是干:冠比例失调([反例帖](https://www.reddit.com/r/Minecraft/comments/jc400o/i_asked_myself_what_is_my_awesome_fantasy_city/))。生成时强制 冠宽 > 干高、干基/H ≥ 1/8。
- **实心球冠 + 干上长叶**:团簇不凿洞、不分层、叶子直接贴主干 = 放大版原版树(4netplayers),无光影下冠内死黑一团。必须凿穿洞透光、叶只挂枝梢邻域。
- **对称同高分叉**:两枝同高同形同角度,树冠几何过圆无抖动(DiamondLobby 明令禁止)。校验:同侧任意两枝高差 ≥2、方位角差有下限、冠缘半径抖动 ±1–2。

## 4. 对模式库的建议
现有栈:递归渐细主干 + 达芬奇分支 + 径向 flare 板根 + 空间殖民冠层外围 + 抖动椭球团 + 噪声雕腔 + 发光距离场壳。社区技法中仍可参数化的增量:

- **Fibonacci 阶梯曲线** `curve_step_seq(fibonacci|noise)`:干收窄台、根/枝抛物线的步长用 Fibonacci 序列 —— 手工美感的确定性近似,零额外成本,直接替换均匀噪声。
- **分叉不对称约束**:`branch_min_dh(≥2)` 同侧枝最小高差、`azimuth_min_sep` 方位角下限;**倾斜偏置** `lean_dir + lean_bias(0–1)` 让枝朝向分布倒向主干倾斜侧。
- **叶挂枝梢硬约束**:attractor 只散布于枝梢端,`min_dist_from_trunk`;`canopy_top_bias` 使冠顶密度 > 枝下密度。
- **雕腔增强**:已有噪声雕腔 + `gap_through(凿穿洞概率)` 出光斑、团簇合并后再做一遍边缘侵蚀 pass。
- **叶材调色板**:`leaf_palette[(block, weight)]`(2 主色)+ `accent_palette`(flowering azalea / spore blossom / 樱花)+ 垂坠层 `hanging(vines|glow_berries|hanging_roots, len 1–4)`。
- **发光三点位**(补距离场壳之外):`lantern_hang`(低枝下垂 1–3)、`glow_lichen_patch`(干身,光 7)、`glow_inset(1–2)` 冠缘内埋深度;接内饰文档的照明求解器,校验冠底 min light ≥1。
- **根-干联动**:根鳍落点处干段高度 ±1 联动,绕干成螺旋;`root_count: 斜 1–2 + 直 1–3`,禁止全角全边。
- **微件细节层**:弯折处自动垫楼梯/台阶(`bend_smoothing`),细枝梢换栅栏/墙(`twig_tips`)。
- **地表点缀环** `ground_ring(r ≈ 冠半径)`:coarse dirt / mangrove roots 基座 + leaf litter / 蕨 / 丛 2–4 种,沿滴水线布点。
- **校验器(validators)**:① 反棒棒糖 `canopy_w > trunk_h`;② `trunk_base/H ∈ [1/8, 1/4]`;③ 无同高同向枝;④ 叶全在枝梢邻域;⑤ **程序化放叶必须 `persistent=true`**(否则 distance >6 即枯萎)——这是生成器相对手建最容易翻车的一条;⑥ 冠底夜间光级 ≥1。
