# 参考知识库:风景/自然景观与建筑的地形融合(terrain-blending)— 2026-07-30

> 来源:explore 子代理,为模式库/风格卡片服务。调研范围:MC terraforming 社区教程、自然系 build 经验、GDMC 地形适配文献与获奖方案。

## 1. 核心技法

### 1.1 建筑↔地面过渡带
- **放坡(过渡带)**:建筑台地边缘到原地面留渐变带,宽 4–16 格(项目 `terraform_pad` 已定 ≤16、默认 8);带内用 smoothstep/高斯插值从台地高度渐变到地面高度,叠加 ±1 格确定性噪声,杜绝"尺子坡"。GDMC 2025 冠军核心手法即建筑高度↔地形高度的高斯 lerp。
- **台地规则(手工教程经验值)**:相邻两层台地轮廓不得重合;先做 3–4 层"进 1 升 1"的 1:1(45°),之后改"进 2 升 1"的 2:1(≈27°)放缓;顶部轮廓不与侧壁平行。
- **挡土墙**:高差 ≥2 格(MC 玩家不可跳上,GDMC 以此划"不可建边")时用挡土墙收边而非放坡。材料与建筑基座一致(石/砖);顶部压 1 格半砖/台阶帽;墙面每 3–5 格加扶壁凸出 1 格(复用 buttress/pilaster 节奏)。高差 ≤1 格直接吃进入口台阶。
- **桩柱**:坡地高差 2–8 格时(项目 `stilt_house` 卡片区间)下坡侧用桩柱而非填方;桩脚落在石垫块上;桩高 >4 格加 X 交叉撑;桩径 1 格原木,间距 3–4 格,与立面开间节奏对齐。
- **水岸**:临水建筑用桩柱(码头式),水线处石/砂岩压边 1–2 格;岸线做浅坡(先 2–3 格平缓再抬升),沙+砂砾+黏土混铺。

### 1.2 植被点缀:密度与分组
- **成簇不散布**("plants get lonely"):植被 3–7 棵/簇,簇内间距 1–2 格,簇间留白 ≥ 簇直径;禁止孤立单树——孤树周围至少配 3–5 个灌木/蕨/高草。
- **密度分层**:距建筑 2–4 格内圈用矮植被(花/草/蕨,覆盖率 ~30–50%);中带灌木(叶块高 1–2 格,~15–25%);外圈才上树。密度用噪声掩码驱动,泊松式拒绝采样保证最小间距 2 格。
- **野花草地密度**:每 3×3 约 2–4 个点缀块;花集中在路径两侧 1 格带与水体边缘,不全场撒。

### 1.3 岩石与水景
- **层序铁律**:草方块下至少 1 格泥土再到石头(MC 自然生成规律);悬崖/陡坡剖面 = 顶草皮 → 1–2 格泥土 → 石头主体,石面占比自 ~25% 起随坡度增加。
- **巨砾**:3–7 块圆石/安山岩/石头抱团,半埋 1 格。
- **悬崖**:外挑(overhang)1–2 格制造阴影;崖面不垂直到底,中段内收或外鼓 1–2 格。
- **水景**:水体放局部最低点;湖岸轮廓不规则(禁止正圆);底铺沙+砂砾+黏土 3 种混合;河流走阻力最小路径,任何方向直线段 ≤7 格。

### 1.4 路径与地形起伏
- 路径沿等高线横坡走,避免直冲坡面;必须爬升时用"平 2 升 1"台阶节奏(楼梯/半砖),纵坡 ≤1:2,缓坡段 1:3。
- 路宽:村道 2–3 格,主路 3–5 格;路肩高差 ≥2 格处加矮挡土墙或放坡+植被,不做裸切坡。
- 路面材料渐变:中心压实土/石,边缘 1 格混入砾石/草。
- 生成式做法:坡度惩罚 A*,cost = 距离 + w₁·|Δh|² + w₂·水体惩罚(GDMC 2025 Slothlab)。

### 1.5 色彩渐变(土壤—石材—植被)
- 剖面上色:"顶草皮 → 1–2 格泥土 → 石头";雪山按"石基底 → 泥土 → 顶雪层"。
- 调色板:主色 1 种 + 点缀 3–4 种(草/泥土/粗泥/灰化土;石/安山岩/圆石);点缀按噪声成簇,频率 ~10–25%,不逐块随机。
- 基座过渡:建筑石材基座 → 凝灰岩/安山岩 → 泥土/草,2–3 列内完成渐变(项目 `stilt_house` 卡片 `details.base_transition` 已写)。
- 群系匹配:沙漠=沙岩系+枯灌木,针叶林=灰化土+云杉,雪地坡顶加雪层。

## 2. 范例
1. [ManaCube《Terraforming; A Deeper Analysis》](https://manacube.com/threads/terraforming-a-deeper-analysis.11330/) — 曲线/随机两大原则、水体居最低点、植被成群、草>泥>石层序、"先大建筑后地形"的顺序讨论。
2. [Skyblock《A Beginners Guide to Terraforming Ep.1》](https://skyblock.net/threads/a-beginners-guide-to-terraforming-episode-1-grass-biomes.138002/) — 手工台地:相邻层轮廓不重合,3–4 层后改 2:1 放缓。
3. [GDMC 竞赛论文(ar5iv 1803.09853)§2.1](https://ar5iv.labs.arxiv.org/html/1803.09853) — "适应地形"评分标准:贴合地形、不大面积推平、结构反映环境材料;Fig.3 给出原版村庄"门悬空"反例。
4. [GDMC 首年经验报告(UH PDF)](https://uhra.herts.ac.uk/id/eprint/8237/2/GDMC_1st_year.pdf) — 高度图相邻格高差 ≥2 判"不可跨越边",选址直接剔除陡坡。
5. [GDMC 2025 冠军 Gaussianly Filtered](https://github.com/IsaacBraamGit/gdcm2025) — 高斯滤波贯穿高度图;建筑↔地形高斯渐变过渡带。
6. [GDMC 2025 Slothlab(yawgmoth/GDMC25)](https://github.com/yawgmoth/GDMC25) — 坡度惩罚 A* 路网,避陡坡与水域。
7. [caspianlack/mcvillagegenerator](https://github.com/caspianlack/mcvillagegenerator) — MCPI 地形感知村庄:biome 化 terraform、寻路贴地形、硬地形碰撞规避。
8. [Of Zen and Computing《15 Best Minecraft Terraforming Tips》](https://www.ofzenandcomputing.com/minecraft-terraforming/) — 海岸浅坡、雪顶分层(石→泥→雪)、巨砾/倒木/池塘细节件。
9. [GTXGaming《Minecraft Terrain Hacks》](https://www.gtxgaming.co.uk/minecraft-terrain-hacks-how-to-make-realistic-landscapes/?lang=en-us) — 直线段 ≤7 格、悬崖外挑、自下而上分层铺色。
10. [Minecraft Wiki《Tutorials/Walls and buttresses》](https://minecraft.wiki/w/Tutorials/Walls_and_buttresses) — 挡土墙/扶壁官方教程条目(挡土墙=阻止土砂滑下斜坡的墙,两侧高差显著)。

## 3. 反例
- **建筑浮空/半埋**:模板按"平均高度"落地,下坡侧悬空(门离地数格,GDMC 论文 Fig.3 原版村庄病)或上坡侧埋进土里。规则:每根承重柱/墙线都落到地面;高差 >2 用桩柱或挡土墙,禁止空鼓。
- **过渡带一刀切**:台地边缘一圈笔直 45° 坡或一圈等高挡墙,无噪声、无材料渐变;相邻层轮廓完全重合的"结婚蛋糕"山。规则:过渡带必须 ±1 噪声 + 轮廓逐层错位 + 坡度从 1:1 渐缓到 2:1;任何方向直线段 ≤7 格。
- **点缀撒芝麻**:植被/岩石/花按均匀概率全场薄撒,无簇无留白、密度处处一致。规则:成簇(3–7/簇)+ 噪声掩码 + 最小间距 2 格;孤树必配灌木群。

## 4. 对模式库的建议
> 对齐现有 `patterns/*.json+.py` schema(params 带 type/range/default/notes、确定性噪声 h2、脚本不读世界,ground 从 terrain.json 传入)。

- **新 pattern `slope_blend`(放坡带)**:把 `terraform_pad` 的过渡带泛化到任意建筑足迹。参数:`footprint`(矩形列表)、`ground`、`band_width`(1–16,默认 8)、`profile`(smoothstep|linear|stepped)、`noise_amp`(0–2,默认 1)、四材 palette 同 `terraform_pad`;`stepped` 模式输出 1:1→2:1 台地阶梯。
- **新 pattern `retaining_wall`(挡土墙)**:参数 `line`(折线点列)、`height_top`/`height_bottom`(段高差 2–6)、`material`、`cap`(slab|stairs)、`buttress_spacing`(0=关,3–5)、`buttress_projection`(1);复用 buttress/pilaster 节奏逻辑。
- **新 pattern `stilt_foundation`(桩柱基座)**:参数 `polygon`、`floor_y`、逐角 `ground` 列表、`stilt_material`、`spacing`(3–4)、`brace_threshold`(默认 4)、`pad_material`;桩高区间 2–8 对齐 `stilt_house` 卡片。
- **新 pattern `scatter_vegetation`(植被散布)**:参数 `region`、三档 `density`(默认 0.35/0.2/0.05 对应内圈/中带/外圈)、`cluster_size`(3–7)、`min_gap`(2)、`mask_noise_scale`、palette 权重。必须成簇 + 拒绝采样,禁止均匀伯努利散布。
- **新 pattern `boulder_cluster` / `pond`**:巨砾 3–7 块抱团半埋 1 格;池塘 = 噪声低于水位线挖坑 + 底材沙/砂砾/黏土混合 + 不规则岸线。
- **既有件增补**:`terraform_pad` 加 `profile` 参数(现仅 smoothstep)与 stepped 台地模式;`road_segment` 加 `max_rise_per_run`(默认 1:2)、`switchback`(超阈值用之字弯)、`edge_retaining`(高差≥2 侧自动矮挡墙);风格卡片把"过渡带调色板+带内点缀频率"抽成卡片级字段 `terrain_blend:{band, palette, rock_ratio}` 供坡地风格复用。
- **validator 增补**:`grounding_check` — 建筑足迹每根承重柱/墙线下探至地面,悬空 >1 格报警(对应反例 1);`transition_check` — 检测台地边缘直线段长度(>7 报警)与相邻层轮廓重合度(对应反例 2)。与现有 `collision_check`/`symmetry_check` 并列。
