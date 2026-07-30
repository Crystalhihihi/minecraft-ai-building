# 参考知识库:雕像/雕塑(MC 原生雕塑 vs 照片转体素) — 2026-07-30

> 来源:explore 子代理,reflib 类目调研。交叉验证对象:`defaults/patterns/quadruped_statue.py`、`mirror_build.py`。
> 重灾区界定:**MC 原生雕塑** = 手工/参数化、剪影驱动、调色板克制;**照片转体素** = 照片/3D 模型经 voxelizer 自动转块(ObjToSchematic、Bloxelizer、Spritecraft 系)——本文将其整体列为反面教材,唯一例外见 §3 末"边界情形"。
> 数字标注:[引] = 有社区出处;[推] = 解剖惯例/实践推导,已交叉核对现有脚本。

## 1. 核心技法(每条带数字)

- **剪影优先(outline-first)**:标准流程 = 参考图 → **单色**方块勾正面/侧面轮廓 → 填体积 → 细节[引]。生成顺序必须是"轮廓先行",禁止先堆体块再修形。验收标准:主观赏轴 **30–50 格**距离、忽略颜色只认轮廓,能认出物种即合格(眯眼测试)。雕像按 **1 个主观赏面**设计(广场/道路朝向),辨识特征(吻/角/耳/翼尖)比真实比例**夸张 1–2 格**[推]。
- **调色板克制(3–5 色)**:最小集 = 基色 + 阴影色 + 点缀色 **3 种**;上限 5,官方建造书给 3–8(含互补+对比)[引]。铁律:**禁"叙事块"**——TNT/蜂巢/带釉陶瓦箭头/矿石贴面,近看即穿帮("为什么墙里埋着 TNT",octopuchi 排除准则)[引];禁方向敏感块(原木顶底面、菌丝体、灰化土);曲面皮肤/毛发只用无图案块。
- **关节/姿态的体素表达**:腿至少 **2 段**(大腿+小腿,膝部 45° 折 1 格)才读作"腿";颈/尾 = 椎骨链,**每段截面变化 ≤1 格、转向每段偏 1 格**;头颈连接重叠 1 格防漂浮头;行走姿态对角腿前后错位 **1–2 格**(打破镜像,现有脚本做不到,见 §4);**禁止 1×1 斜线悬丝**(20 格外消失),最小截面 2×2,尖端允许 1×1 但长度 ≤2[推]。
- **渐变在曲面的用法**:明度 ramp 沿竖直轴 = 顶浅 1 档、腹/腿内侧深 1 档,**3–5 阶**(伪 AO);阶间边界混掺 **20–30%** 棋盘噪声防硬线(与 modern-nordic 混掺规则同源);每阶厚度 **≥2 格**,大曲面 3–4 格,否则渐变读作条纹;色序直接查社区 ramp 表(octopuchi 全色卡 / HueBlocks·CrabCraft OkLAB 生成器)[引]。
- **尺度选择(多大才开始像)**:阈值 = 最小辨识特征(眼/耳/角)**≥1 格**。下推:双足人形 **≥12–16 格高**(头 ≥3×3);四足躯干长 **≥8–10**(现脚本 5–16 区间吻合);带翼龙躯干 **≥20–30**[推]。皮肤雕像惯例:**1 皮肤像素 = 1–4 格**[引]。**>100 格 = "巨建"门类**,为截图不为游玩,模式库不服务该尺度。基座 = 总高 15–25%,宽出足印 1–2 格[推]。
- **比例基准**:
  - 双足(MC 皮肤基准)[引]:头:躯干:腿 = **8:12:12**(¼:⅜:⅜),肩宽 = 头宽 8px,臂宽 4px,整体 16×32×8 px;雕像可读性修正:头放大到总高 **1/5–1/4**[推]。
  - 四足(与 quadruped_statue.py 对齐)[推]:腿高 ≈ **0.30–0.35 L**(L=躯干长),躯干高 ≈ 宽 ≈ **0.30 L**,头 ≈ **0.9 × 躯干宽**,颈 ≈ **0.15 L**;站立总高 ≈ 0.6–0.65 L(≈马肩高≈体长的解剖惯例)。
  - 翼/龙[推]:翼展 = **1.5–2 × 体长**(鼻到尾);翼根弦长 ≈ 0.3–0.4 × 半翼展;**3–4 根指骨**撑膜三角;颈长 0.5–0.75 × 躯干长;尾长 ≈ 1 × 躯干长,递减至 1×1 尖。

## 2. 范例(正面)

- [[STATUES] Everything you need to know to build a player statue — Minecraft Forum](https://www.minecraftforum.net/forums/minecraft-java-edition/creative-mode/369134-statues-everything-you-need-to-know-to-build-a):皮肤比例唯一文字正典(8:12:12、16×32×8、1–4 格/像素);并记载 MCEdit 皮肤雕像滤镜的史实(见 §3 边界)。
- [Minecraft Statue Ideas & Tips — That VideoGame Blog](https://thatvideogameblog.com/minecraft-statue/):"单色勾型→正面/侧面轮廓→填充→上色"流程出处;并明确 2D 像素画生成器只用于**规划轮廓**。
- [Master Builder 官方书摘 — Bloomsbury](https://media.bloomsbury.com/rep/files/master-builder-extract.pdf):调色板 3–8 块、"互补+对比"分工的官方表述。
- [Crafting Content(职业建造团队民族志)— Nottingham ePrints](https://eprints.nottingham.ac.uk/51744/1/Crafting%20Content%20The%20Discovery%20of%20Minecraft's%20Invisible%20Digital%20Economy.pdf):职业 builder 开工前先铺 material palette 的实证,调色板克制不是审美口号是行业流程。
- [ブロックカラーチャート — octopuchi](https://octopuchi.com/block-color-chart/):全色系渐变 ramp 查表(生存可得)+ 叙事块/方向敏感块排除准则,§1 渐变与调色板主源。
- [HueBlocks](https://1280px.github.io/hueblocks/) / [CrabCraft Block Gradient](https://crabcraft.net/tools/block-gradient):OkLAB 色差的方块渐变序列生成器,ramp 配色直接出表。
- [ManDooMiN(YouTube)](https://www.youtube.com/@ManDooMiN):韩系 organic/龙雕塑代表,曲面渐变与翼膜处理的扒带对象。
- [MythicalSausage(YouTube)](https://www.youtube.com/@MythicalSausage):生存实况语境下的雕像建造(自由女神、龙等),尺度与场地整合参考。

## 3. 反例:照片转体素为什么"看着很好但不符合游戏审美"

三个结构性原因,全部指向同一根源:**输出为截图优化,不为游玩距离优化**。

- **尺度错位**:voxelizer 为保住网格细节,典型输出 **100–300 格**高(Bloxelizer"丢进 OBJ/STL 直接切片"、ObjToSchematic 即此类)。网页 3D 预览里惊艳;装进存档后玩家站 20–60 格外,单块亚像素化,形读作噪点。强行缩到 40 格内,薄件(手指/翼膜/尾尖 <1 格)直接消失或成漂浮孤岛。典型:工具商店的"雕塑样例"页,截图与实机两回事。
- **颜色糊**:转换器逐体素做全色库最近色匹配(TwentyFiveSoftware/voxelizer README 自述:texel→RGBA→感知色空间找最近方块),一座雕像用 **80–100+ 种方块**,混入矿石/带釉陶瓦/海晶灯等图案块;无明度分组,曲面读作电视雪花。典型:Spritecraft/minecraftart.net 系的照片输出——远处是照片,近处每块都在"讲故事",违背 §1 调色板全部规则。
- **无剪影**:体素化继承照片姿态(3/4 正面)与光滑曲面采样,曲面边缘全是锯齿阶梯,换角度轮廓即崩;工具自己的教程都承认"**选剪影清晰的照片、方块越粗越好**"(ASCII Magic)——即可读性完全押注在源图上,零姿态设计。典型:照片转 3D 的人物/宠物雕像,正面截图成立,侧面看是一块平板加毛边。

**边界情形(不算反例)**:① 2D 像素画生成器做**轮廓规划**(§1 流程第一步,人工仍管体积);② MCEdit 皮肤雕像滤镜/皮肤挤出——皮肤本身就是 16 色级、为网格设计的像素画,8:12:12 比例内置,属于"原生格式转原生",与照片(1600 万色、无网格先验)有本质区别。判断准则一句话:**源是否已为网格设计过**。

## 4. 对模式库的建议

现有 `quadruped_statue.py`:静态直立、直颈直腿、尾 2 格、全镜像——比例已合格,缺姿态与表面两道层。建议:

- **姿态参数化(最优先)**:`pose(standing/walking/rearing/sitting)`、`neck_pitch`、`head_yaw`、`leg_phase`、`tail_curve`;walking/rearing 需打破镜像(mirror 只作用躯干,四肢按相位差单独生成)——这正是"抽象牛"到"像动物"的下一步。
- **biped_statue.py(新)**:8:12:12 皮肤基准 + `px_per_block(1–4)` + `arm_pose`;直接编码 §1 双足比例表。
- **wing.py(新)**:指骨(3–4 根)+ 膜三角帆,`span = 1.5–2 × body_len`;与四足模块组合出龙/狮鹫。
- **gradient_ramp 工具(新)**:输入 3–5 色 ramp 序列 + 表面 y/法线 → 顶部+1 档、腹部−1 档、边界 20–30% 噪声混掺;色序查表内置(octopuchi/HueBlocks 序)。
- **表面平滑 pass(新)**:阶梯面转 stairs/slabs 半格平滑——这是职业 organic 与 voxelizer 输出的分水岭,也是反例区 §3"无剪影"的正解。
- **validators 扩展**:`silhouette_check`(主轴投影 + 连通性 + 最小特征 ≥2×2)、`thin_feature_check`(1×1 悬丝/漂浮孤岛)、`palette_check` 复用 modern-nordic 结论并加**叙事块黑名单**(矿石/带釉陶瓦/TNT 类)。
- **管线红线**:不接照片/3D 模型体素化输入;用户给参考图时只允许 2D 投影提取剪影作为 outline 起点,体积与配色必须走参数化生成(对应 §3 边界准则)。
