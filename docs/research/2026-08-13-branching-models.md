# 程序化树分枝拓扑模型调研 — 巨树生成器"合轴化"改造选型

> 2026-08-13。目标:给 `giant_tree.py`(单轴 leader + 从属侧枝,用户实机判不合格)的骨架大改造选型。
> 约束:种子确定性 / 纯 stdlib Python / 体素输出 / 树高 10–150 / 秒级生成。
> 目标形态:真实阔叶树的**合轴/假二叉分枝** —— 干失势后裂成 2–4 条势均力敌共干,四面八方,递归逐级。
> 已有调研(tree-forms.md / trees-vegetation.md / giant-tree-v3-status.md)不重复,本文只含增量。

## 结论(先行)

**骨架用 Weber & Penn 的"克隆分裂"算子 + Honda 式不对称比例做轻量核心,宽度用整数管模型(da Vinci d²=Σdᵢ²),方位分布抄 ez-tree 的槽位抖动法。** 空间殖民与全参数 L-system 出局(理由见对比表)。fancy oak 的包络球 + 0.381 坡度 + 20% 规则作为体素层启发式保留。现有 `fork=2|3`(forked_halberd,v12)就是该体系的 0 级特例,改造 = 把它从"一次性参数"泛化成递归算子。

---

## ① 模型对比表

| 模型 | 核心机制 | 分叉几何(方位/倾角) | 宽度法则 | 确定性体素适配 | 计算量 | 合轴适配 |
|---|---|---|---|---|---|---|
| **Honda 1971** | 递归二叉:1 母段→2 子段,常数分枝角 θ₁θ₂ + 长度比 R₁R₂ | 方位靠发散角 δ 逐代旋转;无随机时完美自相似(显假,需 ±25–30% 抖动) | 原模型无;外挂 da Vinci d²=Σdᵢ² 或 d^Δ=Σdᵢ^Δ(Δ≈2 自相似,≈3 填空) | ★★★ 每节点 4–5 float,二叉树拓扑,零依赖 | O(2^depth),depth 8–10 → 10²–10³ 段,五个里最便宜 | 天然支持:θ₁≈θ₂ 且 R₁≈R₂ 即假二叉;θ₁≈0 即单轴。但**只有二叉**,3–4 叉要扩 |
| **Weber & Penn 1995** | 按 level(0=干,≤3–4)参数化;每干一段 nCurveRes 段曲线;两种正交算子:**splits=同级克隆(合轴算子)**, children=降一级(单轴算子) | 子枝:nDownAngle±V 倾角,nRotate±V 螺旋方位(≈140°=黄金角;负值=对生扇形);分裂:nSplitAngle±V + **回弯补偿**(裂后逐段向原方向收,树冠不炸) | 子半径 = 母半径 ×(子长/母长)^RatioPower(橡树 1.3,近似但不守恒)——**建议换成管模型** | ★★★ 全是三角函数 + 误差扩散累加器;局部抽随机数,固定遍历序+种子即逐位可复现;**有 MC 体素先例(GiantTrees 插件=Arbaro 体素化)** | O(stems×CurveRes) ≈ 10³–10⁵ 采样,纯 Python 秒级 | **最准**:0BaseSplits≥1 + 0SegSplits>0 + 小 SplitAngle = "2–4 条共干"的显式旋钮;分数分裂用 Floyd–Steinberg 式误差扩散(确定性,不扎堆) |
| **参数化 L-system**(ABOP 1990) | 并行字符串重写 + 3D 海龟解释(F + & / [ ]) | 角度是产生式里的字面常量;习性靠调文法"调出来" | 无内建守恒,全手写进产生式 | ★★ 确定性可做(单种子+固定推导序),但**合轴树冠要靠文法调试发现**,上下文敏感规则有乱序抽数风险 | 重写 O(串长)×推导次数,指数增长 | 表达力够但 authoring 成本最高;同参数直接性远逊 WP |
| **Space colonization**(Runions 2007) | 冠包络撒吸引点(N=10²–10⁴),骨架朝"影响域内点的归一化均向"逐节生长,近距杀点 | **无角度参数**——分叉是吸引点集分裂的涌现;di 小→扭曲,dk 大→稀疏 | 事后管模型回填:rⁿ=r₁ⁿ+r₂ⁿ | ★ 确定性可保,但纯 stdlib 没有 CGAL,邻居搜索要手写网格哈希;v3 已实测它把云片盘淤成 1–2 格厚平板木 | 朴素 O(N点×N点×迭代) ≈ 10¹⁰+,最重 | 论文自认宽冠下主干不 delineated——**合轴只能涌现,无法参数指定"高 h 处裂 3 叉"**;轮廓控制好,结构控制弱 |
| **Pipe model**(Shinozaki 1964 / da Vinci) | 不是骨架模型,是**宽度分配律**:任意高度截面积 = 其上所有子轴基面积之和 | n/a | 分叉口 **d² = Σ dᵢ²**;体素版:每枝带整数 pipe 数 p(梢 p=1,父=子和),半径 r = round(k·√p) —— 整数开方天然确定性,子枝脱落自动收分 | ★★★ 纯算术,O(1)/节点 | 忽略 | 任何骨架都能叠;专治 WP RatioPower 不守恒 |
| **ez-tree**(2024–2026,THREE.js) | 现代开源实现:WP 思想简化版。BFS 队列递归(levels≤3–4),**阔叶每枝=1 条顶端延续(继承梢半径)+ children[level] 条侧枝** | 侧枝方位=2π/count **等分槽 + ±半槽抖动 + 槽位随机置换 + 每父枝整体转 φ₀**(解耦高度↔方位,防螺旋纹);倾角=固定 angle[level](70/60/60°) | radius[level] × 母枝着生点局部半径(默认 0.7,**不守恒**) | ★★★ MWC 种子 RNG,全部抽数集中在骨架 pass,BFS 序固定,v2.0.0 保证同种子逐位一致 | 默认参数 457 枝/768 叶,~10⁴ 浮点 ops | 顶端延续+多侧枝 = 合轴感涌现(母轴被 N+1 条均分),但无显式"等粗共干"旋钮 |

**fancy oak(原版)单列**:它本质是"包络球约束的一次性放射枝"——无递归,见 ③。

## ② ez-tree 参数结构摘录(源码核实,MIT)

仓库 `dgreenheck/ez-tree`,`src/lib/options.js` + `tree.js`。所有分枝参数都是**按 level 的字典**:

```js
branch = {
  levels: 3,                             // 0=干;levels=递归深度
  angle:    { 1: 70,   2: 60,   3: 60 }, // 侧枝与母轴倾角,度(固定值,无随机散布)
  children: { 0: 7,    1: 7,    2: 5 },  // 该级每条枝的侧生枝数(固定,非随机区间)
  length:   { 0: 20, 1: 20, 2: 10, 3: 1 },   // 每级绝对长度(非母长比例!)
  radius:   { 0: 1.5, 1: 0.7, 2: 0.7, 3: 0.7 }, // 0 级绝对;≥1 级=乘母枝局部半径
  start:    { 1: 0.4, 2: 0.3, 3: 0.3 },  // 侧枝在母枝上的最低着生位置(比例)
  taper:    { 0: 0.7, ... },             // 基→梢半径收
  gnarliness: { 0: 0.15, ... },          // 每段随机弯折;×1/√radius(细梢更弯)
  twist:    { 0: 0, ... },               // 每段绕轴自旋
  force: { direction: {0,1,0}, strength: 0.01 },  // 趋性;步长 ×1/radius
}
```

递归核心(`#growBranch`,BFS 队列):

- **阔叶树每枝必产 1 条顶端延续枝**(同级+1,继承母枝梢半径),再产 `children[level]` 条侧枝 → 实际分叉因子 = 1+children。这就是它的"合轴感"来源:母轴不独大,末端被 N+1 条均分。
- 侧枝着生:沿母枝 `[start[level], 1]` **分层采样**(槽 i + 槽内抖动),方位槽 `2π(i+jitter)/count + radialOffset` 且槽↔子枝随机置换(Fisher–Yates,种子 RNG)。
- 叶只长在末级枝梢(骨架驱动叶,和我们"叶挂枝梢"原则一致)。
- 复杂度实测推算:默认 457 枝;`oak_large` 预设(children 9/5/3)311 枝。**种子确定性**:单 MWC RNG 实例 + BFS 固定消费序。
- 一个可抄的小坑提醒:它源码里 `'Deciduous'` 大小写不匹配导致一段除法永不触发——移植时别照抄那段。

## ③ 原版 fancy oak 算法要点(gist + 反编译源码交叉核实)

配置:`FancyTrunkPlacer(3,11,0)` + `FancyFoliagePlacer(r=2, offset=4, h=4)`。常数为反编译原值:

- **高度**:treeHeight = 3+rand(12) → 3–14;有效高 k = +2 → 5–16。**干高 = floor(0.618·k)**(1/φ;干占 0.618,冠占顶部 0.7)。
- **枝候选**:从 k−5 层往下到 0.3·k(向上取整)每层 1 个候选(经典版高 ≥11 时每层 2 个;现代代码 `min(1,…)` 疑似 Mojang 长年 quirk,恒 1),外加 1 个保底"顶簇"(只长叶不长木)。
- **包络**:`treeShape(k,o) = 0.5·√((k/2)² − (k/2−o)²)` —— 半径 k/2、心在 k/2 的球的半截面。枝端水平距 = treeShape × (rand+0.328),即全树冠约束在球内。
- **每枝一条直线段**:方位角 θ=rand·2π 均匀;**着生点 y = 端点y − 水平距×0.381**(BRANCH_SLOPE,即枝以恒定 0.381 坡度从干上斜出),钳 ≤ 干顶。**无逐步重随机、无长度衰减迭代**。
- **淘汰**:端点上方 5 格叶空间被占 → 整枝丢弃;`着生高 − 基高 < 0.2·k` → 枝木不生成(20% 规则 = 冠底清干)。
- **叶**:每存活枝端 + 顶簇,4 层圆盘半径自下而上 2,3,3,2(切角),簇径 ~5–7。
- **体素细节**:枝用 Bresenham 走格,log axis 取主导轴(所以原版枝是"横放原木")。
- 旁证(同族 placer):**dark_oak** = 2×2 干 + 顶部 4×4 环 12 个位置各 1/3 概率垂 2–4 格竖直枝柱(期望 4 条);**mega_jungle** = 2×2 干,上半段每隔 2–5 格出一条 5 格枝(每步外 1 格、每两步上 1 格,坡度 0.5,仅 top half);**acacia(forking)** = 干在 h−rand(4)−1 处弯 1–3 步 + 异向第二枝 1–3 步。
- **启示**:原版证明了"球包络 + 恒坡度 + 着生高下限 + 端点叶簇"在体素下就够出可辨识阔叶树;但它**无递归、无等粗共干**——正是用户嫌弃的形态天花板。

## ④ 选型建议(WP 克隆算子 × Honda 比例 × 管模型宽度 × ez-tree 方位)

### 为什么是这套杂交

1. **合轴/假二叉 = WP 的 splits(同级克隆)算子**:干长到失势点后裂成 K 条同级共干,每条继承全部参数递归——这正是"2–4 条势均力敌共干,递归逐级"的显式表达。`nBaseSplits`(基段分裂)直接覆盖 stubby/丛生,`forked_halberd` 是 K∈{2,3}、只裂一次的现成特例。
2. **防树冠爆炸靠 WP 回弯补偿**:克隆枝裂开后逐段向原生长方向回收(splitAngle 按剩余段数反向分摊),否则递归分裂的冠会摊成大饼。这一条是 WP 相对 Honda 的关键增量,必须抄。
3. **Honda 提供不对称旋钮**:K=2 时 θ₁≠θ₂ / R₁≠R₂ 可在"单轴(θ₁≈0)↔假二叉(θ₁≈θ₂)"间连续插值——preset 卡只需要一对标量就能从栎树调到杉树,不用换算法。
4. **宽度换整数管模型**(替掉 WP/ez-tree 都不守恒的 ratio 乘法):梢 p=1、父=Σ子、r=max(1, round(k·√p)),分叉口自动满足 d²=Σdᵢ²,缩径天然平滑,且整数开方绝对确定。k 用现有护栏标定(ts≈H/15–H/25)。
5. **方位分布抄 ez-tree 槽位法**:K 等分槽 + ±半槽抖动 + 槽位随机置换 + 每母枝整体随机旋转。一行代码防"同高同向枝"(现有校验器 #3)和螺旋纹。
6. **确定性纪律照 ez-tree**:单一 `random.Random(seed)` 实例,**全部抽数集中在骨架 pass(BFS 队列固定消费序)**,栅格化/叶/装饰阶段零抽数。这和我们 v3 以来"同参同种同树"的契约一致。
7. **fancy oak 遗留两件套**:冠包络球(约束枝端,防飘出冠幅——替代现有解析偏移钳制)和 20% 清干规则(分叉点不得低于 0.2–0.3·H)。
8. **出局**:空间殖民(成本+无显式共干旋钮+v3 平板木前科,包络思想已被球包络吸收);全参数 L-system(表达力相同,authoring 成本数倍)。

### 参数骨架(伪代码级)

```python
# 按 level 的参数表(level 0 = 干),数值为阔叶基准, preset 覆盖
P = {
  "levels": 4,                      # 递归深度上限
  # 失势分裂(合轴算子): 每条干/共干走到 fork_pos 处裂 K 条同级共干
  "fork": {
      0: {"k": (2, 3), "pos": (0.30, 0.50), "angle": (25, 40)},  # 干: 高 0.3-0.5H 处裂 2-3
      1: {"k": (2, 2), "pos": (0.55, 0.75), "angle": (20, 35)},  # 共干: 后半程再裂
      2: {"k": (2, 2), "pos": (0.60, 0.80), "angle": (15, 30)},
      # k 取区间随机整数; angle 为离母轴倾角(度), 一级分叉 = 干"失势"
  },
  # 从属侧枝(单轴算子, 补充细节; ez-tree 式 stratified 布置)
  "children": {0: (0, 2), 1: (2, 4), 2: (2, 4), 3: (1, 2)},
  "child_start": {1: 0.4, 2: 0.35, 3: 0.3},   # 侧枝最低着生(母枝比例)
  "child_angle": {1: (40, 70), 2: (35, 60), 3: (30, 55)},  # 度, 区间内均匀
  "child_len":  {1: 0.65, 2: 0.55, 3: 0.45},  # ×母枝剩余长(Honda 比例)
  # 形态扰动
  "gnarliness": {0: 0.04, 1: 0.10, 2: 0.16, 3: 0.20},  # 每段弯折弧度, ×1/√r
  "tropism":    {"dir": (0, 1, 0), "strength": 0.02},  # 趋光回正, ×1/r
  "env_radius": 0.5,                # 冠包络球半径 = env_radius × H(fancy oak 0.5)
  "clear_frac": 0.25,               # 着生/分叉不得低于 0.25·H(20% 规则推广)
  "pipe_k": None,                   # r = max(1, round(pipe_k·√p)); 按 ts≈H/15-25 标定
}

def gen_tree(H, seed):
    rng = random.Random(seed)
    queue = [Stem(origin=base, dir=up, level=0, pipes=pipes_for(H))]
    terminals = []
    while queue:                              # BFS: 固定消费序 = 确定性
        s = queue.pop(0)
        pts = walk(s, rng)                    # 段列: gnarliness 弯折 + tropism 回正
                                              #       + 分裂回弯补偿(见下)
        if s.level < P["levels"] - 1:
            f = P["fork"][s.level]
            K = rng.randint(*f["k"])          # 2-3; H≥60 可放行 4
            az = slotted_azimuths(K, rng)     # 2π(i+jitter)/K + φ0, 槽位置换
            for i in range(K):
                child = split(s, pts, pos=rng.uniform(*f["pos"]),
                              angle=rng.uniform(*f["angle"]), azimuth=az[i])
                child.pipes = alloc(s.pipes, K, rng)   # 整数分配, Σchild = parent
                # 回弯补偿: child 的目标方向 = 母方向 + splitAngle,
                # 之后每段按 1/剩余段数 摊还, 末端回到母轴方位(防冠炸)
                queue.append(child)
            for c in lateral_children(s, pts, rng):    # ez-tree 槽位法从属侧枝
                queue.append(c)
        else:
            terminals.append(tip_of(s))       # 叶锚点 → 现有 metaball 叶场
    rasterize_with_pipe_radii(queue)          # r = max(1, round(k·√p)),
                                              # 缩径层铺半砖(沿用现有做法)
```

复杂度估算:K 平均 2.2、3 级分裂 → 共干 ≈ 2.2³ ≈ 11 条 + 侧枝 ~10² 条,每条 10–40 段 → 10³–10⁴ 次 vline 印章,纯 Python **0.1–0.5s**(与现有辐扇同量级,远低于 v2 殖民的 40s)。

### 落地路径(对现有代码的最小侵入)

1. `Tree` 里新增 `_stems()` 递归生成器替代 `_leader()+_limbs()`;`fork=0|2|3` 旧参数映射为 `fork[0].k=(0,0)|(2,2)|(3,3)` 保持旧 preset 兼容。
2. 段列走格、截面收分、半砖过渡、flood-fill、metaball 叶场、decor 钩子全部复用——**只换拓扑**。
3. 校验器新增:共干数 2–4、同侧两枝高差 ≥2、分叉点 ≥ clear_frac·H、分叉口 d²≈Σdᵢ²(±1 格量化容差)。
4. 风险:递归分裂 + 侧枝叠加可能枝数爆炸 → 用 children 区间下限 0、分裂仅在 level≤2,并用现有 aesthetic 扇区校验兜底补枝。

## ⑤ 来源

学术/工业:
- Honda 1971: https://pubmed.ncbi.nlm.nih.gov/5557081/ ;方程整理(Jinasena & Sonnadara 2013): https://pdfs.semanticscholar.org/e968/349daf5adf349110efcc5b63671fb4b2153b.pdf
- Weber & Penn 1995 论文(Duke 镜像 PDF): https://courses.cs.duke.edu/fall01/cps124/resources/p119-weber.pdf
- Arbaro(WP 的 Java 实现,含 ca_black_oak.xml 参数实例): https://github.com/wdiestel/arbaro / https://arbaro.sourceforge.net/
- GiantTrees(Bukkit 插件,WP/Arbaro 的 MC 体素化先例): https://github.com/rmichela/GiantTrees
- ABOP(L-system 圣经): https://algorithmicbotany.org/papers/#abop
- Runions 2007 空间殖民论文: https://algorithmicbotany.org/papers/colonization.egwnp2007.pdf
- 管模型综述(Lehnebach 2018): https://pmc.ncbi.nlm.nih.gov/articles/PMC5906905/
- Blender Sapling(WP Python 实现): https://github.com/abpy/improved-sapling-tree-generator

ez-tree(全部 main 分支源码核实):
- 仓库: https://github.com/dgreenheck/ez-tree
- tree.js: https://raw.githubusercontent.com/dgreenheck/ez-tree/main/src/lib/tree.js
- options.js: https://raw.githubusercontent.com/dgreenheck/ez-tree/main/src/lib/options.js
- rng.js: https://raw.githubusercontent.com/dgreenheck/ez-tree/main/src/lib/rng.js
- oak_large 预设: https://raw.githubusercontent.com/dgreenheck/ez-tree/main/src/lib/presets/oak_large.json

Minecraft 原版:
- Tree definition: https://minecraft.wiki/w/Tree_definition
- Tree(树种变体): https://minecraft.wiki/w/Tree
- Earthcomputer fancy oak 逐行解析: https://gist.github.com/Earthcomputer/41addf80c12d001dfa4391c3a0d03be8
- 反编译源码(23w51b,FancyTrunkPlacer 等): https://github.com/MCFireworkDev/MinecraftDeobfuscated-Mojang/tree/snapshot/minecraft/src/net/minecraft

MC 建造社区增量(剔除已知后的新货):
- Hypixel 树指南(作业顺序:干→根→主枝→次枝→叶最后;线稿先行再加粗): https://hypixel.net/threads/guide-tree-guide.1694197/
- minecraftforum 巨树老帖(亮羊毛骨架再包木;原版树冠借种法): https://www.minecraftforum.net/forums/minecraft-java-edition/discussion/162246-how-to-build-a-giant-tree
- hangoutmc 建造课(干顶部分叉处也要加宽): https://hangoutmc.com/threads/creative-build-school-4-custom-trees.1302/(仅搜索摘要,正文未验证)
- empireminecraft Jelle 指南(至少露一处不被叶遮的树干分叉): https://empireminecraft.com/threads/jelles-build-guide-its-back-d.77162/(仅搜索摘要,正文未验证)
- bilibili 盆景多干式教程(中文圈把"一本多干/多干式"当独立风格做,无文字数值): https://www.bilibili.com/video/BV1xrQkYiEQq/
- GameRant Yggdrasil 100 小时报道(无枝干分解,仅体量参考): https://gamerant.com/minecraft-player-yggdrasil-tree-100-hour-build/

**社区调研的诚实结论**:可访问的中英文文字资料里**不存在**"主干裂 2–4 等粗共干"的成文程序化步骤、同级分叉夹角数值或枝干/叶工时占比——合轴化没有社区作业可抄,只能走学术模型(WP/Honda)落地。MegRae 幻想树教程(bilibili BV1x7411w7V4 / BV1vP4y1k7ku)本环境不可达,建议人工补看。
