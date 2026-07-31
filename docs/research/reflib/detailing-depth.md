> 调研日期 2026-07-31,来源 8 个

# 参考知识库:立面细节与质感通用手法(detailing-depth)— 2026-07-31

> 定位:跨风格通用层,产出直接喂 AI 当施工参考,只收可量化、可执行、带来源的规则。风格专属条目在姊妹篇:坡度/屋脊数学与中式举折见 facades-roofs.md,城堡墙面 50/30/15/5 混比见 medieval-castle.md,路面破损 10–20% 见 roads-plazas.md,地形过渡见 terrain-blending.md。r/Minecraftbuilds 与 TrixyBlox 的取证情况见 §2 注。

## 1. 核心技法

### 1.1 depth:三层法则与"夸张进深"
- **三层结构**(MCF depth 指南,"at least 2-3 layers"):第 1 层 = 主体墙面(最靠后,相对平);第 2 层 = 窗框、立柱、大支撑件,与第 1 层换材质形成对比;第 3 层 = 按钮/栅栏/墙块等"小于一整块"的构件,要能透过它看到背后两层。**任何尺寸建筑至少 2 层,正常 3 层**。
- **必须夸张**:现实建筑的进深靠曲线与异尺寸材料,MC 方块同尺寸,只有**夸大进深**才读得出层次(MCF 指南明确论点)。
- **消灭 flat areas**(官方 Avomance 教程第一式):屋顶加挑檐、墙面换材质、玻璃块换玻璃板退进墙内、门退 1 格做凹龛、房基四周摆楼梯/半砖,让房子不像"一坨方块戳在地上"。
- **细部是配菜不是主菜**(Raeyzeus,官方采访):整面墙**不得被细部全覆盖**,必须留 negative space;柱等结构件为主体,细部只绕其边缘;拉远看全图,噪声不能盖住单体特征——"远看一墙颜色但看不出是什么"即失败。
- 与 facades-roofs §1.1 的"出 2/出 1/入 1 三档词汇表"是同一规律的两种表述(三档进退 ≈ 三层);凸件间距 3–6、阶梯收分等数字在该篇,本篇不重复。

### 1.2 texturing:同色系多材质混合
- **第一原则:同色系、异质感**。灰系示例集(官方 Avomance 与 BlockBlend 色彩理论同源):圆石、石头、石砖、安山岩(+沙砾);白系示例集(Raeyzeus):骨块、白色羊毛、石英、白混凝土。判定标准 = 颜色近、贴图噪声密度不同。
- **三种混合几何**(Jelle's Build Guide):
  ① 随机混合(random texturing):WorldEdit `//replace 墙块 x%块A,y%块B`,适合小型人造建筑;
  ② 脉状混合(veins):1–2 种对比块成脉穿插,适合地形/废墟,**脉用块 ≤2 种**;
  ③ 团块混合(blobs):同色不同块成大团(例:白墙分羊毛团/混凝土团/粉末团),只适合大体量墙面与放大尺度景观。
- **比例定标**:通用墙面起点 60/30/10(§1.3);做旧墙逐带百分比查 §1.4 配方表;工具流程 = 先试 **7×7 小样**、在与成品相同的光照下确认后再上墙(minecraftgradient.blog)。
- **大面缓变、小件跳变**(minecraftgradient.blog):大墙面用近色、质感缓慢变化;窗框/招牌/饰条等小件允许更锐利的色差以读清形状。

### 1.3 palette 构成与梯度
- **60/30/10 铁律**(BlockBlend 色彩理论、minecraftgradient.blog 双源一致):60% 主块定调、30% 过渡块、10% 跳色点缀;互补色组合(橙陶瓦↔青混凝土等)只配当 10% 跳色,不可等量对撞。
- **调色板大小 4–7 块**(minecraftgradient.blog):1 主块 + 2–3 过渡 + 1–2 点缀(+1 照明块)。小建筑用色数(Raeyzeus):柱 1 色 + 细部 1–2 色 + 背景墙面 1 色 ≈ **4 色**,加屋顶 **5 色**;巨型建筑可到 15–30 种块。
- **小建筑 3 色构成法**(Jelle):2 个中性色 + 1 个跳色;单色建筑几乎必死(只能靠树叶等绿色救场);多跳色并用时按互补配对:蓝&黄 / 紫&橙 / 红&绿。
- **大建筑多调色板**(Jelle):按楼层或体块分板,各板共享同一个平淡基色,板间不许冲突;跳色在各板间保持互补。
- **环境色板**:建筑色板必须考虑群系底色(自然 = 棕+绿为主)(Jelle);草/树叶/水色随群系变化,同一配方换群系要重新试样(minecraftgradient.blog)。
- **竖向梯度方向——两源有分歧,如实并列**:Grian 巨型建筑教程(官方整理)= 底部简单形状+浅色,顶部用更兴奋的颜色,把视线向上引;WesterosCraft(facades-roofs 已引)= 明度深下浅上。可执行的折中(本篇综合,非原文):明度深下浅上接地,彩度/细部密度上引。
- **梯度边界处理**(minecraftgradient.blog):禁直条纹;边界打散成团簇,中间过渡块向两侧邻域各撒一把;铜/黑石/深板岩在室内光下比日光下深得多,必须在实际光照环境试样。

### 1.4 weathering:做旧掺比(石系定量配方)
逐带百分比来自 BlockBlend 配方库;带高 **2–4 格**,方向 = **下脏上净**(越靠地越破越苔,与 medieval-castle "苔藓靠下与背阴"一致):
- **乡村古堡墙(rustic wall)**:
  - 底带:圆石 40 / 苔圆石 30 / 石头 20 / 石砖 10
  - 中带:圆石 25 / 苔圆石 20 / 石头 30 / 石砖 25
  - 顶带:圆石 10 / 苔圆石 10 / 石头 30 / 石砖 50
- **废墟(ruins,加重裂纹+苔)**:
  - 最破带:圆石 45 / 裂纹石砖 30 / 苔石砖 15 / 石砖 10
  - 半破带:圆石 20 / 裂纹石砖 35 / 苔石砖 25 / 石砖 20
  - 近完整带:圆石 5 / 裂纹石砖 15 / 苔石砖 20 / 石砖 60
- **崩角点缀**:任意带随机替换 **2–3%** 为侧放圆石楼梯/石砖楼梯,模拟棱角崩落。
- **快速记忆锚**:圆石系老墙整体配比 ≈ 圆石 40 → 苔圆石 25 → 石头 20 → 石砖 15(BlockBlend Quick Answer);深板岩下探、山体碎石、村庄路、酒馆地板另 4 套配方见原文。
- **原版佐证**:要塞墙体 = 石砖混"偶发"的裂纹石砖与苔石砖(minecraft.fandom wiki)——Mojang 官方生成器自己就用同族破损块做旧。

### 1.5 窗户处理(通用层)
- **玻退框凸**:玻璃块换玻璃板并退进墙体(Avomance 明确技巧),窗框留墙面或凸 1;入户门退 1 格成凹龛。工程参数(框凸 1/窗台半砖/活板门百叶/窗尺寸表 1×1–3×N/多层对位)全部在 facades-roofs §1.4,本篇不重复。
- **窗是"视线停靠点"**:窗框、门框、烟囱、屋脊、桥墩 = 跳色/点缀块的法定落点(minecraftgradient.blog 点缀分布规则);每个区域的点缀密度不可相同,否则点缀失效。

### 1.6 屋顶边缘与轮廓细部清单
- **挑檐是 depth 第一手段**(Avomance):屋顶必须出挑;出挑 1–2、椽间隔 2–3、装饰脊/阶梯山墙/飞檐数字全部在 facades-roofs §1.6,本篇不重复。
- **Grian "greeble" 清单**(官方整理的巨型建筑教程,明示中小建筑同样适用):屋顶饰条(trims)、阳台、窗、烟囱、柱、拱、凹龛(indents)、饰带(friezes)与色带(strips of colour)——用大色带/饰带打断大体块,是"把大形拆小"的通用手段。

## 2. 来源
1. [Minecraft 官方:Make Your Houses Better(Avomance 5 式)](https://www.minecraft.net/en-us/article/make-your-houses-better):depth 消灭 flat areas(挑檐/换材质/玻璃板/门退 1/基座楼梯)、同色系混材第一原则(圆石+石头+石砖+安山岩)、栅栏半砖按钮活板门细部件。§1.1/§1.2/§1.5/§1.6 主源。
2. [Minecraft 官方:Raeyzeus' Top 5 Building Tips](https://www.minecraft.net/en-us/article/raeyzeus-top-5-building-tips):小建筑 4–5 色、大建筑 15–30 块、白系混材集(骨块/羊毛/石英任意白色块)、negative space 反过度细部。§1.1/§1.2/§1.3 主源。
3. [Minecraft 官方:How to do MEGA builds(Grian 两部教程整理)](https://www.minecraft.net/en-us/article/how-do-mega-builds):羊毛打稿 → 调色板(底部浅色简单形、顶部兴奋色、视线上引)→ greeble 细部清单。§1.3/§1.6 主源。
4. [Minecraft Forum:Depth in Building! A Simple Way to Improve All Structures](https://www.minecraftforum.net/forums/minecraft-java-edition/creative-mode/369294-depth-in-building-a-simple-way-to-improve-all):2–3 层法则、各层分工(主体/框柱/小件)、MC 必须夸张进深的论证。§1.1 主源。
5. [Empire Minecraft:Jelle's Build Guide](https://empireminecraft.com/threads/jelles-build-guide-its-back-d.77162/):texturing 三几何(随机/脉/团块,含 WE `x%` 语法)、3 色板 = 2 中性 + 1 跳色、多板共享基色、互补跳色配对、环境色板。§1.2/§1.3 主源。
6. [BlockBlend:Cobblestone Gradient Guide(6 配方)](https://blockblend.app/guides/cobblestone-gradient-guide):rustic/ruins 逐带百分比、2–3% 楼梯崩角、带高 2–4、圆石 40/苔 25/石 20/石砖 15 锚点配比。§1.4 全部数字源。
7. [BlockBlend:Minecraft Color Theory for Builders](https://blockblend.app/guides/minecraft-color-theory):60/30/10、暖冷色族、互补色只做 10% 点缀、同色异质感灰系示例(石头/石砖/安山岩/沙砾)。§1.2/§1.3 主源。
8. [Minecraft Gradient Generator:Minecraft Color Palette Guide](https://minecraftgradient.blog/minecraft-color-palette/):60/30/10、色板 4–7 块、7×7 试样、过渡块落点(边/角/阴影/做旧区/地形接触带)、点缀落点(门窗框/烟囱/脊)、禁直条纹、群系与光照重测。§1.2/§1.3 主源。

注:**r/Minecraftbuilds 在本环境直连与搜索均不可用(连接被拒),高赞帖原文无法取证——该渠道证据不足,本版不含 reddit 专属条目**,社区生态位由来源 4/5(论坛长文指南)填补;**TrixyBlox 无文字化教程**(USW 系列为纯视频),同样不引。medieval-castle.md 已引 minecraftgradient.blog 的城堡墙面渐变文,与来源 8 是同站不同文:那篇给城堡专用 50/30/15/5,本篇引通用 60/30/10。另:[Stone Bricks — minecraft.fandom wiki](https://minecraft.fandom.com/wiki/Stone_Bricks)(要塞偶发裂纹/苔石砖,§1.4 旁证)。

## 3. 反例
- **过度细部**(Raeyzeus 点名的头号错误):整墙糊满楼梯半砖,远看一团噪声。规则:细部绕结构件边缘布置,墙面必须留 negative space;拉远看不清单体特征 → 减细部。
- **彩虹色板 / 多跳色同强度**:金块、钻石块、铜、诡异木全上 = 噪声不是丰富。规则:跳色只留 1 个主导、总量 ≤10%,其余压成中性(gradient.blog/BlockBlend 共指)。
- **单一材质大墙**:连 texturing 都没有的纯石砖墙。规则:同色系 ≥3 块混合,大墙必须混(全部来源一致)。
- **直条纹渐变 / 均匀棋盘噪声**:渐变带边界成水平直线,或破损块均匀随机撒成"花斑狗"。规则:边界成团打散、过渡块向两侧邻域各撒、WorldEdit 按带加权而非全墙均匀。
- **苔/裂纹块乱撒**:苔石出现在屋顶、墙顶等干燥高处。规则:做旧块只向下集中(靠地 2–4 格底带)与背阴潮湿面,带内百分比按 §1.4 向上递减。
- **只贴"画上去的细节"**:纯换色、零进退的墙。规则:MC 同尺寸方块下必须真凸真凹,三层结构缺一即提示(MCF 论证)。

## 4. 对模式库的建议
- **texture_bands(新,通用)**:参数 `bands:[{y_range, mix:{block:pct}}]`、`band_height(2–4)`、`broken_trim_pct(2–3,侧放楼梯)`;内置预设 `rustic_wall`/`ruins`(直接抄 §1.4 表)/`deepslate_descent`(源文配方 3)。medieval-castle.md 已提议的 `texture_mixer` 是其带 y 权重的特例,应合并实现而非各做一套。
- **depth_layers 校验器**:把墙面识别为三层——后层(主体)、中层(框/柱)、前层(小件);缺中层或前层 → 提示;小件覆盖率过高(建议阈值 >50%)→ 触发"过度细部"警告(Raeyzeus negative space 规则的量化近似,阈值为本篇建议值,源文无数字)。
- **palette 生成约束**:色板 4–7 块、权重 60/30/10;高饱和/发光块总权重 ≤10% 且只落在 anchor 列表(门窗框/脊/烟囱/招牌/桥墩);渐变相邻带权重连续变化,禁直条纹。
- **weathering 方向规则**:苔/裂纹块权重随高度单调递减,底带 2–4 格内取峰值;潮湿群系(沼泽/丛林)峰值上调一档,干燥群系(沙漠/恶地)禁用苔藓系(群系修正为本篇推论,源文未给数字)。
- **window_recess 默认值**:`glass=pane`、`recess=0–1`、`frame_projection=1`,与 facades-roofs 的 window_trim 合并参数面;入户门默认 `recess=1`(Avomance)。
