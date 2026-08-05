# 产卡任务书(外部 agent 用)v1 · 2026-08-02

> 本文件给**零项目上下文的外部 agent**:为 Minecraft AI 建造系统的"建造百科"补充风格卡(任务包 A),可选承接肌理卡(任务包 B)。
> 产出由项目内 agent 按第 5 节 checklist 逐条验收,不合格打回附原因。
> 能访问本仓库:第 2/4 节点名的文件**必读**。不能访问:向用户索要这些文件的副本再开工。

## 0. 一句话背景

Minecraft 1.21 Fabric mod 内的 LLM 建造 agent,靠"建造百科"卡施工。卡是知识资产:**LLM 读卡做选择题,Python 生成器做计算题**。卡存在的全部意义是让 LLM 不自由发挥——已实测:无卡自由发挥=外立面光秃、内部空壳、半砖悬空。

## 1. 四层决策模型(先理解再动手)

| 层 | 回答什么 | LLM 角色 | 载体 |
| --- | --- | --- | --- |
| L1 风格卡 | 这是什么建筑 | 选身份 | `styles/*.json` |
| L2 模式卡 | 用什么形式 | 选组件 | `patterns/*.json` + 同名 `.py` |
| L3 变体 | 长什么样 | **不参与** | 模式卡内命名 profile / 参数默认值 |
| L4 肌理 | 表面什么质感 | **不参与** | 生成器分布算法 + 风格化白名单 |

铁律:

- **LLM 只做 L1/L2 选择题**。L3 参数预烘焙进 profile,禁止 LLM 现场填数值(实测必漂移:同一"檐深"两次两种算法)。
- L4 拆两层:**L4a 风格化白名单**(点缀件清单随风格卡/profile 选定,如中世纪={藤蔓,旗帜,铁栏}、日式={竹帘,石灯笼,苔藓})+ **L4b 程序化分布**(撒点算法只管分布不选件)。禁止全局通用点缀清单。

## 2. 卡的三种形态(解剖)

### 2.1 风格卡 `styles/<style_id>.json`

必读范例:`medieval_house.json`(木骨石基民居)、`sakura_japanese.json`(东方风格)、`modern_house.json`(现代)。字段逐个:

| 字段 | 要求 |
| --- | --- |
| `style_id` / `name` | 小写蛇形 id;name 英+中 |
| `use_for` | 匹配标签:风格+体量+构件,供任务匹配下发 |
| `palette_stats` | 材质占比统计及**出处**(语料库件数/真实案例) |
| `proportions` | 高宽比/层高/墙厚/典型占地/门高 + 风格特有项(如 jetty 悬挑) |
| `materials` | ground_floor/upper_walls/frame/roof/accent 五组,全带 `minecraft:` 前缀 id + `_mix` 掺比 + `_use` 用法;掺比引用生成器 preset |
| `roof` | type/slope/overhang/ridge_support/dormers/chimney——**引用模式卡**,不自己造轮子 |
| `windows` | pattern/size/material/frame |
| `details` | base/lighting/weathering/interior + `depth`(pilaster/window_trim/string_course 参数) |
| `pitfalls` | ≥3 条实测翻车点,"禁止 X,因为 Y"式,空泛=打回 |
| `validators` | 从 5 个验收器里选(见 2.4) |

### 2.2 模式卡 `patterns/<name>.json` + 同名 `.py`

必读范例:`gable_roof`(标准参数卡)、`dormer`(**一卡三变体 gabled/shed/hipped 的先例**)、`chimney`、`wall_weathering`(L4 肌理先例)。

- JSON:`name` / `description` / `when_to_use` / `params`(每个参数:`type`/`range`/`default`/`notes`,notes 写清参考点) / `example`(真实可跑命令行)
- `.py` 生成器铁律:无头可跑(纯命令行,输出 block JSON)、确定性(seed 可复现)、**朝向/半砖/转角全部脚本推导**(禁止输出后手改方向状态)、超 range 参数拒绝。

### 2.3 规则文档 `patterns/*.md`

速查/铁律类(`stair_orientations.md` 是范例)。优先把规则塞进 JSON 字段,不够表达才补 md。

### 2.4 验收器 `patterns/validators/`(5 个,新卡从这里选 validators)

`support_check`(悬空)/`slab_check`(半砖缝、浮空上半砖)/`stair_corner_check`(围合转角 corner shape)/`symmetry_check`/`collision_check`。

## 3. 变体规则(防卡泛滥,重要)

同一结构的"更多变体"按三层吸收,**不为变体开新卡**:

- **新几何形式**(歇山顶 vs 人字顶)→ 新模式卡,或已有卡加 variant 参数(先例:dormer 一卡三变体)
- **同形式不同参数集**(檐深 2 vs 3)→ 卡内命名 profile 或默认值,**禁止内联进风格卡**
- **表面细节**(雕刻/起伏/配色)→ L4 肌理层:材质 mix/palette 白名单/accent 点缀,属任务包 B 范畴

判据:**一个变体不能用一个枚举参数表达,才配开新卡。**

## 4. 现有资产清单(禁止重复)

以 `patterns/INDEX.md` 为准,摘要:

- **风格卡 14**:plains_cabin / medieval_house / medieval_tower / waterfront_dock / stilt_house / nordic_villa / modern_house / tree_house / sakura_japanese / castle_fortress / church_chapel / brick_townhouse / farm_estate / suzhou_garden
- **模式卡 27**:gable_roof / hip_roof / gambrel_roof / mansard_roof / helm_roof / dormer / chimney / crenellation / buttress / arch_window / window_trim / pilaster / balcony / railing / wall_weathering / interior_rooms / furniture(15 件) / fountain / flower_field / terrace_farm / plaza / garden_tree / road_segment / terraform_pad / quadruped_statue / mirror_build
- **规则文档 5**:stair_orientations / roof_types(13 种顶型速查) / wall_weathering / interior_layout / blocks.md(方块 id 速查)

## 5. 合格标准(验收 checklist,逐条打钩)

- **A 格式**:JSON 合法;风格卡必备字段齐(`use_for`/`pitfalls`/`validators` 缺一不可);模式卡同名 `.py` 存在且 `example` 命令真实可跑
- **B 方块**:全部原版 1.21 合法 id、带 `minecraft:` 前缀、与 `blocks.md` 一致;禁用模组块/不存在 id
- **C 口径**:每个尺寸参数有唯一参考点定义(origin/朝向由脚本推导);无明确参考点的数值=打回
- **D 证据**:`palette_stats`/参数注明出处(语料统计/真实案例/实机实测);`pitfalls` ≥3 条且具体;拍脑袋数值、空泛禁忌=打回
- **E 引用**:卡内引用的 `patterns/xxx.py` 全部真实存在;引用不存在的卡=打回
- **F 不重复**:与第 4 节清单无功能重叠;近似风格必须在 `use_for` 说清与现有卡的差异
- **G 体量**:风格卡 ≤100 行 JSON,模式卡 JSON ≤40 行。读者是 token 紧张的 LLM,废话=打回
- **H 可施工**:数值在 params range 内;结构句法闭合(悬挑必带支撑、墙必落地、屋顶必收脊);生成器冒烟跑通 + 声明的 validators 全绿
- **I 交接**:产出放 `scratch/external_cards/`(下分 `styles/` `patterns/`),附 README 列产出清单+每张卡自检表。**不要直接改** `defaults/`、`INDEX.md`、`WorkDir.java`——合并注册由验收方做

## 6. 任务包 A:新风格卡(按优先级)

| # | style_id | 定位 | 为什么缺/依据 | 复用与前置 |
| --- | --- | --- | --- | --- |
| 1 | `chinese_palace` | 中式殿堂(歇山/庑殿+斗拱+高台基) | suzhou_garden 是园林非殿堂;中式大屋顶高频需求;语料库无中式分类→知识直写+公开案例 | 斗拱/歇山顶现有模式卡不能表达→**先产模式卡**再写风格卡引用 |
| 2 | `elven_tree` | 精灵树居(白石材+有机曲线+树木共生) | 项目验收标杆刚需(用户点名"精灵树");复用 garden_tree | 曲线句法可知识直写 |
| 3 | `japanese_castle` | 日式天守阁(石垣+层层收分+破风) | 与 sakura_japanese 民居互补;用户已实测日式方向有反馈 | 屋顶复用 gable/hip+收分参数 |
| 4 | `gothic_cathedral` | 哥特主教堂(飞扶壁+玫瑰窗+双塔) | church_chapel 只是小堂;MC 经典题材,语料丰富 | 飞扶壁→ buttress 加 variant;玫瑰窗→新模式卡 |
| 5 | `desert_adobe` | 沙漠/中东风(砂岩陶瓦+平顶+穹顶+拱廊) | 全新材质体系,与现有 14 卡零重叠 | 穹顶→新模式卡 |
| 6 | `mediterranean_villa` | 地中海/托斯卡纳(陶瓦坡顶+灰泥+拱廊) | 与 brick_townhouse 区分:南欧乡村庄园 vs 城市联排 | 复用现有屋顶/拱窗 |
| 7 | `steampunk_workshop` | 铜工业工坊(砖+铜+玻璃暖房) | 1.21 铜块氧化变色是天然做旧素材 | 复用现有 |
| 8 | `lighthouse` / `windmill` | 地标小品(灯塔/风车) | 小体量高频;风车叶片是独特结构句法→新模式卡 | 可两卡也可合一张"地标"卡,自定 |

缓做(写了也压后验收):`nether_fortress`(下界黑石系)、`mushroom_manor`(童话蘑菇)、`viking_longhouse`(与 nordic_villa 重叠风险,要写必须说清差异)。

每卡流程:读 3 张范例卡 → 按 2.1 解剖写 JSON → 素材 mix 标出处 → 尽量引用现有模式卡 → 现有卡表达不了的结构句法,先产模式卡(2.2 规范)再引用。

## 7. 任务包 B:肌理卡(可选,**需仓库访问**)

完整规范必读:`docs/plans/2026-08-02-detail-texture-cards.md`。摘要:

- **步骤 0(零额度,纯 Python)**:写 `scratch/phase9/gc_probe/layer_analyze.py`——语料 `scratch/phase9/gc_probe/gc_data/<slug>/meta.json`(材质带 color 色板)反解 `layers/*.png` 像素→方块 id(先验证 PNG 语义:像素=方块?色板精确匹配?空气=透明?);统计 4 项:檐口出挑深度/墙面凹凸率/木构柱距/屋顶层占比(抽 200~400 件中世纪)→ 产 `stats_details.md`。Pillow 装 `gc_probe/.venv` 隔离环境
- **B1 `facade_depth`**:立面纵深三段式(基座放脚/墙身进退线脚/檐口封檐)+ 交接专章(墙-地/墙-顶/屋顶-烟囱泛水/建筑-场地收边);3~5 个命名 profile,生成器内部展开参数
- **D1 `accent_detailing`**:碎件位置语法(依附结构缝/成组 2~3/密度随面宽);`palette`=L4a 风格白名单(见第 1 节),撒点算法不选件
- **A3 `timber_structure`**:木构梁架句法(三角屋架 3 种/托臂/斜撑/梁端收分/暴露节奏 3~5 间距);连带 support_check 补 45° 斜撑规则
- **E4/E5 升级**(改现有卡不新增):garden_tree 三级分枝+锥度+垂枝/板根变体;flower_field 地被三层法+companion 参数
- 纪律:B1+D1 落地即停手,打标杆用验收数据驱动,不凭感觉加卡;pitfalls 必须实测驱动

## 8. 交接与验收流程

产出 → `scratch/external_cards/` → 项目 agent 验收:自动(JSON lint + 方块 id 校验 + 引用存在性)+ 第 5 节 checklist 逐条 + 生成器冒烟 → 合并注册(INDEX 按五类分组 / WorkDir DEFAULT_ASSETS)→ 构建部署(需游戏关闭)→ 实机打标杆。不合格项逐条打回附原因,改完再验。
