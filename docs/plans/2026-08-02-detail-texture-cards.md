# 细节肌理卡调研计划 v2(2026-08-02 定稿)

> 框架:肌理卡按**手艺逻辑**分五大类——骨/形/色/饰/景。交接层(檐口/基座/泛水/场地收边)不独立成卡,并入 B 类"形"作端点专章。
> 组合方式:**组合下沉到生成器**——风格卡只写 profile 名,生成器内部展开全套参数(单一口径,防内联漂移);禁止把肌理参数复制进风格卡。
> 纪律:INDEX 按五类分组、保持小体积;B1+D1 落地后**停手打标杆**,用验收数据驱动后续,不再凭感觉加卡。
> 决策边界(四层模型):L1 风格=选身份、L2 模式=选组件、L3 变体=参数、L4 肌理=分布。LLM 只做 L1/L2 选择题;**L3 参数预烘焙进命名 profile 不下放**(E8 漂移教训:LLM 碰原始数值必漂移),L4 分布算法全在规则层。五大类(骨形色饰景)是横向手艺域,四层是纵向决策深度,交叉表稀疏,不为凑格子造卡。

## 五大类与现状映射

| 类 | 治什么 | 现状 | 缺口 |
| --- | --- | --- | --- |
| A 骨 | 为什么立得住(结构逻辑) | buttress/pilaster/crenellation | timber_structure |
| B 形 | 为什么不是平的(Z 轴纵深) | window_trim/arch_window/dormer | **facade_depth(含交接专章)** |
| C 色 | 平面内部为什么不单调(材质) | wall_weathering | 无(闭环) |
| D 饰 | 碎件该往哪放(位置语法) | 空白 | **accent_detailing** |
| E 景 | 有机形怎么不乱(规则内不规则) | garden_tree/flower_field/terrace/plaza | 树枝+地被升级 |

## 证据来源

1. **零额度·程序化层图分析**(首选):语料 2587 件带层图(53182 张 PNG),meta.json 材质带 color 色板→像素反解方块 id。统计:檐口出挑深度/墙面凹凸率/木构间距/分枝几何 → `stats_details.md`
2. **低额度·知识直写**:子代理产卡,用户实机验证迭代
3. **中额度·视觉提炼**:K3 读精品层图,额度宽裕时校准,不急

## 执行序(B→D→A→E:通用先行,专项靠后)

### B1 `facade_depth` 立面纵深(含交接专章)
- 三段式:基座放脚(墙退 1 基座凸出再收分)/墙身(进退面、线脚系统、壁龛)/檐口封檐(出挑深度、封檐板、檐下阴影)
- 交接专章:墙-地面(放脚)、墙-屋顶(檐口出挑+封檐)、屋顶-烟囱(泛水圈)、建筑-场地(挡土墙/踏步)
- **profile 机制**:卡内定义 3~5 个命名 profile(如 medieval_townhouse/modern_flat/sakura_shinkabe),生成器内部展开参数;风格卡 depth 段只引用 profile 名
- 参数:`origin/facing/width/height` + `profile` 或显式覆盖(`base_height/cornice/string_course_every/recess_panels/relief_budget`)
- 校准:层图统计墙面凹凸率分布定 relief_budget;檐口出挑分布定 overhang 默认
- 边界:管几何不管材质(wall_weathering 管材质),卡内互相 pitfalls 声明

### D1 `accent_detailing` 点缀学
- 位置语法:碎件(藤蔓/花盆/灯笼/旗帜/按钮/蜡烛)必依附结构缝(转角/门窗边/檐下/柱脚),成组 2~3 不孤立,密度随面宽
- 参数:`surface`(wall/corner/eave/column_base)+ `density` + `palette`(按风格选件)+ `seed`(确定性)
- **L4a/L4b 拆分**:palette 即风格化白名单(L4a,随风格卡/profile 选定——中世纪={藤蔓,旗帜,铁栏}、日式={竹帘,石灯笼,苔藓}),撒点算法(L4b)只管分布不选件;禁止全局通用点缀清单(防日式灯笼挂进中世纪塔楼)
- 形式:规则文档+薄生成器(在已有墙面上撒点)

### A3 `timber_structure` 木构梁架
- 梁的句法:三角屋架(简支/带立柱/锤梁 3 种)、托臂、斜撑、梁端收分、梁柱交接垫块、暴露屋架节奏(间距 3~5)
- 参数:`kind` + `span` + `material` + `spacing`
- 配套:support_check 补斜撑 45 度判定规则

### E4/E5 现有卡升级(不新增)
- garden_tree:三级分枝+锥度(log→fence/wall→slab 收细)+垂枝/板根变体
- flower_field:地被三层法+companion 参数(花:草:蕨:空)+散置石/枯木

## 实施步骤

1. 层图分析器 `layer_analyze.py`(scratch/phase9/gc_probe/):色板反解+4 项统计 → `stats_details.md`(纯 Python 零额度)
2. B1+D1 两个子代理并行(读 stats_details 校准)→ 冒烟+验收
3. A3 一个子代理(连带 support_check 斜撑规则)
4. E4/E5 一个子代理(改现有两卡)
5. 合并注册(INDEX 按五类分组/WorkDir/DEFAULT_ASSETS)→ 构建部署(游戏关闭时)
6. **停手打标杆**:用户实机完整闭环,验收数据驱动下一轮
7. git 提交+experiments.md

## 风险

- 层图近色歧义:只取高置信主材,歧义色跳过
- pitfalls 必须实测驱动,不写空泛规则
- profile 机制要在卡格式 v2 里写明(INDEX 卡格式说明同步更新)
