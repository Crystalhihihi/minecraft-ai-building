# 体素/程序化树叶质感技术调研 — 巨树叶层改造储备(2026-08-13)

> 背景:v11 把叶图元从"离散镂空椭球簇"改成"metaball 全冠单一场 + 低频噪声阈值 + 剥壳 2-3"。
> 实机判定:**整冠融成光滑实心气球("一坨"),簇间沟壑被填平,表面只有低频起伏没有高频叶感;云片也是一坨**。
> 目标形态:"枝内融合成簇、枝间留沟壑、表面有叶碎感"。本文回答:融合粒度怎么改对。
> 约束:纯 stdlib Python、种子确定性(h3/vnoise3 已在)、秒级生成、单树 ≤10 万量级。

## 0. 一句话诊断

当前实现把**全部**簇心求和进一个场(`Field.add` 无分组),沟壑只能指望鞍部值低于阈值——
而簇距 `gap≈1.3-1.5×base_r` 远小于场源截断半径 `K·r=2.2r`,相邻枝的簇群在场里必然连通,
T 不敢升(升=整冠缩水、枝内也断);同时 `noise_L=r/3`(r=50 时波长≈17 格)只给剪影级起伏,
剥壳边界=等值面本身光滑,飞叶仅外向 10%/4.5% 无内向咬缺。**三个旋钮全都作用在错误的粒度上。**

## 1. 技术清单(机制 / 效果 / 成本 / 确定性适配)

### 1.1 原版 MC foliage placer:逐附着点叶团 + 方层角切 + 参数化孔洞
- **机制**:树生成时每个枝端产生一个 `TreeNode`(foliage attachment,自带 `foliageRadius` 与
  `giantTrunk` 标记),叶团**逐附着点**生成,不是整冠一个包络。成面靠 `generateSquare`
  (逐 y 层铺方形叶行,层径向上收分) + `isInvalidForLeaves`(子类排除特定位置,
  **角部随机切除**——橡树"圆感"的真相就是方层切角);cherry 系用
  `generateSquareWithHangingLeaves`,把 `wide_bottom_layer_hole_chance` /
  `corner_hole_chance` / `hanging_leaves_chance` / `hanging_leaves_extension_chance`
  **做成显式参数**(镂空率、垂叶率在原版就是一等公民)。
- **效果**:5-7 格小冠就有蓬松感;边缘缺角 + 层间收分打破完美几何。
- **成本**:每候选格一次随机判断,O(冠体积),零开销。
- **确定性适配**:我们的 `h3(x,y,z,seed^salt)` 即等价物,直接可用。
- **佐证级别**:方法结构与参数名经 yarn 映射 + Forge javadoc 核实(见 §4);"角切条件、
  层径公式"等公式级细节为源码记忆,语义可靠、常数未逐行核对。
- **对我们的启示**:原版的"蓬松"= **逐枝附着点放团** + **边界逐格随机剔除** + **层径收分**,
  三件事都不贵;原版从不用"整冠一个光滑场"。

### 1.2 TerraformGenerator(Bukkit 插件,生产级):逐枝椭球 + 5 八度 fBm 扰动半径 + 垂叶
- **机制**(`FractalLeaves.java`,代码已核读):每根枝端/枝段放一个椭球叶团
  (森林树 r=4、ry=2-2.5,**横竖比 ≈1.6-2:1**);成面判据
  `x²/rx² + y²/ry² + z²/rz² <= 1 + 0.7 × fBm(x,y,z)`,fBm = simplex 分形 **5 八度**,
  基频 0.09(λ≈11 格,对 r=4 的团即 λ≈2.75×簇径)。**噪声扰动的是"半径/边界"而非阈值**;
  `hollowLeaves` 内阈值做壳;`setWeepingLeaves(0.3-0.5, len 1-3)` 从叶团外沿向下垂叶柱;
  每格从材质数组随机选一(混叶);`unitLeaf` 撒随机小方块(毛边)。
- **关键细节**:纹理来自**高八度**(λ≈1.4/2.75/5.5 格),基频只管团块级起伏——
  与我们"单八度、波长随 r 缩放"正好相反,它的波长是**绝对格数**。
- **成本**:逐格 1 次 5 八度 fBm(它没用快通道);我们保留快通道后只边界格求值,更省。
- **确定性适配**:它用世界 seed 的 FastNoise;我们用 seeded vnoise3 叠八度即等价。
- **来源**:见 §4(生产插件,数十万服务器在跑,参数是实战调出来的)。

### 1.3 EZ-Tree(dgreenheck,three.js,1.6k star):叶只长在末级枝节段上,分层抽样
- **机制**(`src/lib/tree.js`,代码已核读):叶 quad **只**在最后一级枝上生成;
  沿枝长**分层抽样**(`leafStart = startMin + (i+jitter)/count`,均匀但抖动),
  绕枝方位角**槽位抽签**(2π/count 槽 + Fisher-Yates 洗牌 + ±半槽抖动,槽位与高度槽去相关);
  尺寸方差 `size × (1 ± sizeVariance)`;法线用"叶法线+指向枝心"混合(rounded normals)
  → 单叶有碎感,整体仍读成圆冠。
- **效果**:冠=绕枝的簇云并集,枝间沟壑**天然存在**(那里本来就没有叶)。
- **对我们的启示**:沟壑不是"挖"出来的,是"从不填"出来的——**叶挂枝梢邻域**这条
  本地 reflib 已有的原则,在成面层同样成立:场源分组=枝,组间不融合,沟壑自生。
- **确定性适配**:分层抽样/槽位洗牌我们已有等价 rng 用法;零新成本。

### 1.4 SpeedTree 叶簇 card 理念(非体素,理念输入)
- 理念:小枝级以下不做真几何,用"end branch card + 叶 card"——**叶是绕枝的簇云,
  不是包络面**;叶簇间的碰撞剔除(`Cull tolerance`)只做"疏",不做"连"。
- 对我们的启示:体素里的等价物=**每组簇云独立成面再并集**,而不是一个标量场包一切;
  "簇间碰撞剔除"对应我们的"组间不融合"。

### 1.5 壳面侵蚀 / 咬缺(cellular 多数表决)
- **机制**:对已剥出的壳层做一遍 26 邻表决:邻居数 ≤ k 且有外向空气面的壳格,
  按 hash 概率删除(咬缺);可镜像做"添加"(飞叶,现有 2 轮就是)。
  MC 手建社区的原话版:AstroWorld"先实后雕"、DiamondLobby"合并后再加减侵蚀"。
- **效果**:光斑透下(dapple)、外轮廓线破碎——治"剥壳面太干净"的直接手段。
- **成本**:O(壳格 × 26)一遍,大树壳面 1-3 万格 → 几十万次 dict 查询,Python 可接受。
- **确定性适配**:h3 门控,全确定性。

### 1.6 双色/多材质混叶
- **机制**:emit 时按 h3 从调色板选叶块(主叶 ~80% + 次叶/azalea ~20%);
  TFG 每格从材质数组随机选;社区"主叶 2 色混合"(AstroWorld)。
- **效果**:**零几何成本的颜色级纹理**——远看平滑色块被打破,近看有叶色颗粒;
  对"一坨感"的缓解在截图里立即可见(原版双色叶树从不显气球)。
- **成本**:零(不增块数、不改几何)。
- **注意**:azalea/flowering azalea 都有 persistent 属性,可正常用。

### 1.7 明确排除的做法
- **升 T 逼簇分离**:整冠均匀缩水、枝内也断,错杀融合。
- **白噪声(h3 原值)当高频项**:椒盐麻点不是叶感;高频也要相干(vnoise3 λ≈1.7)。
- **加厚壳层**:更实心更重,与"壳体留空藏灯"既定方向相反。
- **噪声波长继续随 r 缩放**:r=50 时 λ=17 格=只有剪影起伏,本次翻车根源之一。

## 2. MC 社区经验法则(可编码数字)

来源:本地 `docs/research/reflib/trees-vegetation.md`(已含一手 URL)+ 本次核读的两个生产代码库。
量级对齐:1 格 = 1m。

| 量 | 数字 | 出处 |
|---|---|---|
| 叶团横竖比 | ≈1.6-2:1(r=4/ry=2-2.5;手建"穹顶逐层内收 1") | TFG FractalTypes FOREST;DiamondLobby |
| 团簇间缝隙 | **0-2 格**(并簇后仍留缝) | reflib §1.4(综合) |
| 镂空率(卡级) | 0.1-0.35(密冠 0.1,疏朗/云片 0.3-0.35) | tree-forms F01/F03/F08 |
| 冠缘半径抖动 | ±1-2 格 | AstroWorld |
| 叶量分层 | 枝下叶量 < 枝上叶量,冠顶最厚 | DiamondLobby |
| 噪声基频 | λ ≈ 2.75× 簇径(f=0.09 对 r=4);**纹理靠 2-4 号八度 λ≈1.4-5.5 格** | TFG FractalLeaves |
| 边界扰动幅度 | 半径的 ±0.2r 量级(0.7 乘数作用于椭球方程) | TFG FractalLeaves |
| 垂叶 | 概率 0.3-0.5,长 1-3 格,只从外沿/冠底下垂 | TFG(weeping);原版 cherry hanging 参数同生态位 |
| 混叶 | 主叶 2 色;azalea/flowering azalea 点缀 | AstroWorld;TFG material[] 逐格随机 |
| 叶团挂点 | 枝端附着点各自成团(vanilla TreeNode);手建"叶只挂枝梢与细枝" | yarn 映射;4netplayers |
| 双色以上点缀 | spore blossom/垂藤/发光浆果藤,垂坠 1-4 格 | reflib §1.5 |

尺度外推注:手建教程的团簇(径 2-4 格)对应我们 r≤15 的树;r=30-50 地标树的"簇"应读作
**主枝级簇群**(径 6-10 格),内部再靠 1.4-5.5 格频段出碎感——粒度的锚是**枝**不是簇。

## 3. 对我们的具体建议(伪代码级)

改动集中在两处:`foliage()` 给场源打组号;`Field.rasterize` 改"组内 sum、组间 max-并集 +
多八度阈值";剥壳后加一遍咬缺 pass。`Field` kernel 的 splat/剥壳主体不动。

### R1 枝级分场(治"枝间沟壑被填平",核心)

```python
# foliage(): 每个场源带 gid;规则 — 主枝链/其侧枝链/其梢簇 = 同一 gid(枝内融合);
# 顶穹团/冠心团 = 各自独立 gid;blob 壳层环按方位归最近主枝 gid(不再当全局融合剂)
for gi, chain in enumerate(limb_chains):
    tufts_along(chain, start_frac, gid=gi)
for tid in terminals:  gid = gid_of_nearest_limb(tid)
self._field_tuft(顶穹团, gid=n_limbs)
self._field_tuft(冠心团, gid=n_limbs + 1)

# Field 侧:F_g(p) 组内照旧求和;总成面 = 各组独立取等值面后并集,再统一剥壳一次
# (并集后剥壳,内腔/藏灯特性不变;flood-fill prune 以 wood∪leaves 连通,各组都贴枝,安全)
def rasterize_grouped(self, wood, T, amp, shell, noise):
    solid = set()
    for g in self.groups():                    # 实现可从简: 每组一个子 Field
        solid |= g.threshold_solid(wood, T, amp, noise)   # 噪声函数共享(同坐标同值)
    return peel(solid, shell)
```

- 为什么用"并集"而不是调 T:并集保证**组间鞍部永不被填**(两组场不相加),枝内 sum 融合照旧。
- 成本:总 splat 数不变(每源只 splat 一次);阈值求值按组重叠度 +20-50% 上界,通常远低于此。
- 沟壑宽度由骨架保证:主枝梢间距本就 0-2 格缝隙量级(§2),场不再把它抹掉。
- 注意:确定性不变(组号来自 chain 索引);与 v12 的输出差异是本轮预期内的。

### R2 三octave相干噪声阈值(治"只有低频起伏",核心)

```python
# 剪影 octave 随波长冠幅缩放(保留现状);纹理 octaves 用绝对格数(不随 r!)
n = 0.55 * vnoise3(x, y, z, max(3.0, r / 3.0), seed ^ S1) \   # 剪影团块(远视距读作团簇冠)
  + 0.30 * vnoise3(x, y, z, 4.0,                 seed ^ S2) \   # 簇级破碎 3-5 格
  + 0.15 * vnoise3(x, y, z, 1.7,                 seed ^ S3)     # 叶碎感 1.5-2.5 格
T_eff = T * (1 + amp * (2 * n - 1))      # n∈[0,1),权重和=1
```

- amp 沿用分档:厚冠 0.35-0.45,薄冠(umbrella flat_min<0.45)0.25(防穿孔,现状已验)。
- 快通道保留:`f >= T(1+amp)` 必实 / `f < T(1-amp)` 必空,只在边界带求 3 次噪声(现 1 次 → 3 次)。
- r≤10 小树:剪影 octave λ≈3 本就带纹理,三octave叠加后只会更碎一点,不收口(旧实机无投诉频段)。

### R3 壳面咬缺 pass(治"壳太干净",抛光)

```python
# 剥壳之后、飞叶之前,一遍 26 邻表决:
for c in list(leaves):
    if outward_air_faces(c) == 0:        continue          # 只动表面
    if leaf_neighbors26(c) > 10:         continue          # 保厚区(防断连/穿孔)
    if h3(c[0], c[1], c[2], seed ^ BITE) < 0.10 + 0.10 * (leaf_density - 0.6):
        leaves.discard(c)                                   # 咬缺 → 光斑/碎轮廓
# 现有 2 轮外向飞叶(0.10 / 0.045)保留 — 咬缺(内向) + 飞叶(外向) = 双向毛边
```

- 咬缺率 0.10-0.15 对应镂空卡 0.1-0.35 的表层折算(镂空只发生在壳面 2-3 格深)。
- 大树壳面 ~1-3 万格 × 26 邻 → 一遍 <0.5s 量级;只对 `leaves` 集合操作,不碰场。

### R4(可选,装饰位)垂叶绦 + 双色叶

- 垂叶:冠底壳(逐列最低叶)按 p=0.3、len 1-3 向下垂 1 宽叶柱(遇空才垂)——
  TFG/原版 cherry 同款;与 decor=vines 不冲突(材质是叶不是藤)。放 `_decorate` 同级。
- 双色叶:`Voxel.emit` 时按 `h3(cell, salt) < 0.2` 换次叶(如 oak→birch/azalea),
  权重可偏向外壳面/冠顶(亮部);零几何成本,先小比例试。

### 施工顺序建议

1. R1 + R2(同一次实机验收:看"枝间沟壑回来没"+"中近景碎感")——这两个治本。
2. R3(咬缺率从 0.10 起调,对照镂空卡)。
3. R4 按截图再定。
4. 回归口径:本轮允许叶层整体重排;骨架/木部输出应逐字节不变(场源只动分组与噪声)。

### 风险/边界

- r=50 地标:源数已被 tcap/gap×1.6 收住(v13 教训),分场不增块数;咬缺+飞叶 ±10% 块数。
- 分场后若某主枝簇群过稀(单源 r 小),组内也可能不成面 → 校验:每 gid 至少 2 源或源 r≥1.6。
- mist 雾团:侧枝加密+高方差叠放本来就是"多团各自独立"风格,gid 按侧枝链分即可,勿全树一组。

## 4. 来源

代码级(已核读原文):
- TerraformGenerator `FractalLeaves.java`(椭球+5八度fBm半径扰动+壳+垂叶+混叶):
  https://github.com/Hex27/TerraformGenerator/blob/master/common/src/main/java/org/terraform/tree/FractalLeaves.java
- TerraformGenerator `FractalTypes.java`(各树种的团径/噪声频率/垂叶数字):
  https://github.com/Hex27/TerraformGenerator/blob/master/common/src/main/java/org/terraform/tree/FractalTypes.java
- TerraformGenerator `FractalTreeBuilder.java`(dangleLeavesDown 冠沿垂叶):
  https://github.com/Hex27/TerraformGenerator/blob/master/common/src/main/java/org/terraform/tree/FractalTreeBuilder.java
- EZ-Tree `src/lib/tree.js`(末级枝分层抽样放叶/槽位洗牌/尺寸方差/rounded normals):
  https://github.com/dgreenheck/ez-tree
- yarn 1.21.1 `FoliagePlacer.mapping`(TreeNode 逐附着点叶团、generateSquare 角部排除、
  generateSquareWithHangingLeaves 垂叶参数):
  https://github.com/FabricMC/yarn/blob/1.21.1/mappings/net/minecraft/world/gen/foliage/FoliagePlacer.mapping

文档级:
- minecraft.wiki Tree definition(11 种 foliage placer 类型;cherry 四孔洞/垂叶概率参数):
  https://minecraft.wiki/w/Tree_definition
- Forge 1.18.2 javadoc FoliagePlacer(placeLeavesRow/shouldSkipLocationSigned/tryPlaceLeaf 方法结构):
  https://nekoyue.github.io/ForgeJavaDocs-NG/javadoc/1.18.2/net/minecraft/world/level/levelgen/feature/foliageplacers/FoliagePlacer.html
- minecraft.wiki Oak(fancy oak 源自 Paul Spooner 的 Forester 脚本;balloon oak 反例=纯球冠):
  https://minecraft.wiki/w/Oak
- SpeedTree 叶簇 card 工作流(The Rookies,UE5 环境教程):"end branch cards + leaf cards":
  https://discover.therookies.co/2024/01/24/creating-open-world-environments-in-unreal-engine-part-2/
- SpeedTree 官方文档 batched_leaf_generator / leaf collision cull tolerance:
  https://docs8.speedtree.com/modeler/doku.php?id=batched_leaf_generator
- NGNT treegen-pinegen(MagicaVoxel 体素树生成器,"leaf bundles at end of branches",种子确定):
  https://github.com/NGNT/treegen-pinegen

本地已固化(社区手建数字的一手出处在这里面):
- `docs/research/reflib/trees-vegetation.md` §1.4-1.5(DiamondLobby 团簇生长流程 /
  AstroWorld 先实后雕+边缘抖动±1-2 / 团簇间 0-2 格缝 / 双色混叶 / 垂坠层 1-4 格)
- `docs/research/tree-forms.md`(Ori 远视距规律:远=团簇球冠、中近景读层次;F01-F11 镂空率卡值)
