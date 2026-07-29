# 调研:MC 程序化生成(PCG)算法族 — 2026-07-29

> 来源:explore 子代理(medium 档),为精灵树专项与后续 PCG 模式库服务。原始结论未删改,仅排版。

## 1. 树

- **空间殖民(Space Colonization,Runions 2007)**:在树冠体积内散布吸引点,枝干末梢向邻近点生长(kill/influence 半径),回 path 上按管道模型加粗。三种里最有机、最不对称,是写实树的标准。体素实证:[joesobo/ProceduralVoxelTree](https://github.com/joesobo/ProceduralVoxelTree)、[dsforza96/tree-gen](https://github.com/dsforza96/tree-gen)、[Blender 插件](https://extensions.blender.org/add-ons/space-colonization-tree-generator/)。参数:点数/分布、kill/influence 半径、步长、渐细指数。难度 **M**(纯数学零依赖)。
- **L-system**:字符串重写→海龟解释。适合风格化重复树形,主角资产显假;MC 经典用法是 MCEdit 滤镜。参数:公理/规则/角度/迭代。难度 **S**。
- **递归渐细枝干**:递归分裂,方位/倾角随机,半径按达芬奇规则 r³≈Σ子³ 缩减。便宜可控,多数 GDMC 树代码的骨干。难度 **S**。
- **树干 flare/板根**:径向渐细剖面(r(y)=base·(1−y/H)^k+tip)+ 3-8 条根鳍(从基部向地形高度图的短程下行空间殖民)。
- **树冠**:末梢抖动重叠球/椭球团,或对剩余吸引点填 alpha-shape;噪声雕内腔透光。
- **发光脉络**:骨架距离场,0.9·r ≤ d < r 处放发光块(树皮内侧);或沿主干样条开槽填菌光体/萤光藓。

## 2. 建筑

- **WFC(波函数坍缩)**:Niels-NTG 用于平面布局;GDMC 2024 地下图书馆特等奖([nielspoldervaart.nl/gdmc](https://nielspoldervaart.nl/gdmc));[ScholliYT/MGAIA](https://github.com/ScholliYT/MGAIA-Minecraft-GDMC)。难度 **M–L**(简单 tiled WFC 可零依赖,避开重回溯变体)。
- **2025 冠军 "Gaussianly Filtered"**:高斯滤波+图像处理+数学模式贯穿高度图([github.com/IsaacBraamGit/gdcm2025](https://github.com/IsaacBraamGit/gdcm2025))。
- **BSP 房间细分**:足迹递归二分,叶子是房间、分缝是走廊。零依赖简单。**S**。
- **立面节奏**:参数网格(层高×开间),按节奏开窗,各层腰线/窗台材料变化(Parish & Müller 形状文法,[GDMC paper §4.3](https://ar5iv.labs.arxiv.org/html/1803.09853))。**S**。

## 3. 广场与道路

- **坡度惩罚 A***:cost = 距离 + w₁·|Δh|² + w₂·水/岩浆惩罚;加宽→样条平滑→沿路整平。GDMC 2025 Slothlab 自定义成本函数避陡坡与水域([github.com/yawgmoth/GDMC25](https://github.com/yawgmoth/GDMC25))。**M**。
- **水流/吸引点寻路**:2025 冠军用"类水模拟"得自然曲线;或下坡+朝吸引点的 walker 累积流量铺路。**S–M**。
- **广场**:种子点 flood-fill 平坦度评分,边缘高斯渐变进地形。

## 4. 地形装饰

- **噪声散布**:自写 value/Perlin(~40 行)做密度掩码;泊松式拒绝采样保证间距;岩石(blob 并集)、灌木(叶球)、池塘(噪声低于水位线→挖+填)。**S**。
- **高斯融合**:建筑周边过渡带内按距离+噪声抖动在建筑高度与地形高度间 lerp。2025 冠军核心手法。**S**。

## 5. LLM 调参 PCG

- **LLMs4PCG Competition**(IEEE COG 2025):LLM 写/评/迭代生成器;[PCG+LLM 综述(arXiv 2410.15644)](https://arxiv.org/html/2410.15644v1)收录"LLM 作为设计者调 PCG"循环;DreamCraft 做文本引导 MC 环境生成。我们的渲染自检环正是综述里的 "LLM + feedback" 模式——MC 领域做渲染反馈调参的公开工作很少,**属于相对空地**。

## 精灵树首批算法栈(推荐)

**递归渐细主干 + 达芬奇分支 + 径向 flare 板根(核心,S,参数可解读)→ 空间殖民只用于冠层外围枝梢与根尖(最要有机感处,M)→ 树冠=末梢抖动椭球团+噪声雕腔 → 发光=骨架距离场壳 + 2-3 条噪声破碎的根到冠脉络。**

理由:纯递归核心给 LLM 少量可解释参数(taper/flare/split angle/count)供渲染反馈调优;空间殖民只留在"美感大于不可控"的部位——GDMC 各队殊途同归的杂交方案([GDMC 经验报告](https://arxiv.org/pdf/2108.02955))。
