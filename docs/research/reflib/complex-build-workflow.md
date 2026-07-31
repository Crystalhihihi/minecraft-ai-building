> 调研日期 2026-07-31,来源 8 个

# 参考知识库:复杂大型建筑施工分解方法论(complex-build-workflow)— 2026-07-31

> 定位:跨风格**施工流程层**——人类建造大教堂/城堡群/蒸汽朋克飞艇这类复杂建筑时如何分解任务、定尺寸、分阶段验收。与姊妹篇分工:具体风格数值(斗拱/混比/举折)在各风格卡片,本篇只管"先做什么后做什么、每阶段做到什么程度算完"。
> 口径:MC 原生(1 格=1m)。所有结论均来自下述可引用来源;搜索中未能证实的部分在 §6 如实标注。

## 0. 核心问题裁决:frame-first 还是 layer-by-layer?

证据一致指向 **frame-first(先骨架/体块,后逐层执行)**,两者不是对立而是嵌套:

- 战略层 frame-first:Grian mega base 教程(两人五周只做外壳)顺序为 灵感图 → 羊毛彩块勾勒轮廓 → 地形改造 → **3D 骨架(skeleton)定型** → 定调色板 → 外壳细部 → 内饰;明确说细部阶段"by far the most lengthy"[S1]。
- 战术层 layer-by-layer:骨架定型之后,执行按层/按段推进——Litematica 的 render layer 模式就是为"一次只看一层/一个截面,不被整个投影淹没"设计的[S4][S5];wikiHow 城堡教程也是"先铺**单层**地基感受布局,再向上起楼层"[S2]。
- 城市/城堡群级别还有第三种分解:**分区 plotting**(地面彩色羊毛/玻璃方块标记"这里建什么、什么形状",颜色=建筑类型,另放方块指定屋顶材料)[S6];Lannisport 城按"东北→西南码头"分四期施工,大型单体(宫殿/大教堂)从城市工程中拆出单独立项[S7]。

## 1. 尺寸规划:先锁关键尺寸,再细化

- **1:1 复刻派(Cathedral Talk / THSchutt)**:开工前从真实数据锁定全部关键尺寸,允许整体 ~10% 容差只为让 MC 细部好做。Amiens 大教堂实案(模型格 vs 真实米):中殿高 44/42.3、总长 165/148、立面宽 39/36、北塔 64.5/61、尖顶 121/112.7。资料缺失处(通道/钟位)允许"合理猜测",并显式记录为待修正项[S8]。
- **比例推导派(飞艇)**:无真实原型时用模数比。齐柏林式气囊 长:直径 = 6:1 ~ 8:1(例:截面直径 20 格 → 气囊长 120~160 格);参考锚点:兴登堡号真实 41m 宽 × 245m 长;船体内部按功能甲板分区(炮甲板/舰桥/机房),舱室规划先行("proper planning and compartmenting, anything is possible")[S9]。
- **纸面布局派(wikiHow)**:网格纸画平面图,先只铺**一层**地基方块验证房间流动与比例,满意后才向上建;外墙留到最后建,以便内部扩建不被锁死[S2]。

## 2. 蓝图工具链:投影验收的机器化

Litematica 工作流(对应 AI 施工可逐项映射)[S3][S4][S5]:

- **全息投影(hologram)**:把目标结构以幽灵块形式叠加在世界中,直接显示"哪格该放什么" → 对应 AI 的 target-state diff。
- **材料清单(Material List)**:全结构方块数量清单,HUD 实时跟踪已收集/已放置 → 对应进度量化(已放 N / 总数 M)。
- **分层渲染(render layer)**:一次只显示一层或一个子选区,大工程不被整体投影淹没 → 对应"当前工作层"上下文裁剪。
- **Schematic Verifier**:全图扫描,逐块列出 missing/wrong block/wrong state,错块画橙色线框 → 对应机器可判定的**阶段验收标准**:verifier 零 diff = 该阶段完成。

## 3. 分阶段验收(人类实际用的检查点)

- **WesterosCraft 验收流**:每栋建筑挂 builder tag(责任人)→ 施工期任何人可用西瓜块留反馈 → 整改完放 "Done" 块 → **项目负责人批准后才算完成**[S6]。
- **阶段顺序实案**:Harrenhal 城堡"先按完好状态整体建完,再统一做废墟化处理"——破损/做旧是独立后置阶段,不与结构施工混在一起[S7]。
- **里程碑粒度**:White Harbor 城以"半年 386 栋房屋/累计 1124 栋、159 名建造者"计量;大型单体(城堡、大教堂)从群体工程中拆为独立子项目,各有负责人[S7]。
- **教程内建检查点**:"Step back often to check proportions;avoid over-detailing early on"(建一段退远看比例,早期不过度细部)——教堂教程把"比例复核"放在细部之前[S10 见 §6 注]。

## 4. 完整 walkthrough 摘要(3 个文字版全过程)

**A. Grian mega base(minecraft.net 官方文章转述)[S1]** —— 通用大型建筑:
灵感图收集 → 彩色羊毛勾勒占地轮廓 → 地形改造(WorldEdit 或手工外壳)→ 3D 骨架定剪影 → 调色板(下简上繁、下浅上艳,引导视线上移)→ 外壳细部(屋檐线脚/阳台/窗/烟囱/柱/拱/凹槽/饰带,"greeble",耗时最长)→ 内饰最后。两人五周仅完成外壳。

**B. wikiHow 城堡(生存/创造通用)[S2]** —— 防御性建筑群:
选址(高地/隘口)→ 平整土地 → 网格纸平面布局 → 圆形塔楼用预制圆模板(7 格圆等)→ 铺单层地基验证布局 → 主楼(keep)先行、逐层向上 → 庭院马厩等场地 → **外墙最后建** → 屋顶用楼梯块 → 雉堞用石栅栏 → 铁门 → 护城河(≥3 格深)最后挖。

**C. THSchutt Amiens 大教堂(cathedraltalk.fm 建造者自述)[S8]** —— 1:1 复刻:
真实图纸/数据锁定 9 项关键尺寸 → 整体放大 ~10% 换取细部容错 → 外壳(含双塔、飞扶壁、尖顶)→ 内饰完整做完(含多层廊道);资料缺失处做有据猜测并标记待修。同一建造者另有巴黎圣母院、斗兽场等同尺度复刻,尺寸互相校准保持一致比例体系。

## 5. 复杂建筑施工分解模板(喂给 AI 的可执行版)

```
阶段 0 参考与尺寸锁定
  输入:参考图/真实尺寸/模数比(如飞艇长径比 6:1~8:1、教堂中殿高)
  输出:关键尺寸表(长/宽/高/塔高/跨度),整体容差 ≤10%
  验收:所有后续阶段的坐标推导只能引用本表,不得即兴改比例

阶段 1 选址与地基准备
  地形整平/架空壳;放出占地轮廓(羊毛/标记块)
  验收:轮廓外无结构方块;地面高程符合计划

阶段 2 体块与骨架(frame-first)
  3D 骨架定剪影:主体体块、塔位、屋顶脊线、气囊/船体轴线
  大建筑群先做 plotting:彩色标记分区,大型单体拆为独立子项目
  验收:剪影/俯视轮廓与参考匹配;退远检查比例(人检)或
         bounding box 与关键尺寸表 diff = 0(机检)

阶段 3 外壳填充(逐层执行,layer-by-layer)
  按层/按段推进,当前工作层之外不生成;调色板"下简上繁"
  外墙/围护最后收口(保留扩建余地,wikiHow 原则)
  验收:外壳 diff=0(对照蓝图/投影);材料消耗与清单偏差可报告

阶段 4 细部(detailing,预计耗时 ≥ 阶段2+3 之和)
  线脚/拱/窗套/檐口/破损做旧(Harrenhal 原则:做旧是独立后置阶段)
  验收:不新增体块外轮廓改动;细部密度符合风格卡数值

阶段 5 内饰
  外壳签认后才进场;舱室/楼层功能分区表先行
  验收:功能清单逐项打钩(每间房有指定用途与最小家具集)

贯穿机制
  - 每阶段产出 = 下一阶段输入 + 可机检 diff(参照 Litematica verifier 模型)
  - 反馈回路:施工中允许标注"待修正项"(参照 Amiens 猜测记录),不阻塞主流程
  - 责任分解:每个子项目/分区有单一负责人(agent 语境:单一任务上下文)
```

## 6. 证据不足之处(如实标注)

- **"分阶段验收标准"的量化阈值**(如"剪影偏差 ≤5%")在人类社区不存在成文数值;人类靠"退远看比例"这种目检。模板中的机器 diff 验收是从 Litematica verifier 功能[S3][S5]推导的等价物,非社区原文。
- **蒸汽朋克飞艇的完整 walkthrough 文字版**未检索到(视频为主,文字教程稀缺);§1 的比例数据来自论坛讨论帖[S9],样本量小(单帖),长径比 6:1~8:1 与真实齐柏林一致,可信度尚可但非多方交叉验证。
- S10(ExitLag 教堂教程,exitlag.com/blog/minecraft-church/)为商业博客 SEO 内容,"退远看比例/早期不过度细部"两条建议与 Grian 流程一致故引用,但本身权威性弱,仅作旁证。
- 大教堂/城堡群**内部施工顺序**(先拱顶还是先扶壁)未有文字 walkthrough 支撑,本模板不展开。

## 来源列表

- [S1] minecraft.net — How to do MEGA builds(Grian 两集教程文字转述):https://www.minecraft.net/en-us/article/how-do-mega-builds
- [S2] wikiHow — Make a Castle in Minecraft:https://www.wikihow.com/Make-a-Castle-in-Minecraft
- [S3] CurseForge — Litematica 官方功能描述(hologram/material list/verifier):https://www.curseforge.com/minecraft/mc-mods/litematica
- [S4] godlike.host — Litematica Guide(材料清单 HUD/错块高亮):https://godlike.host/litematica-guide-how-to-install-and-use-schematics-in-minecraft-blog/
- [S5] GitHub Michaelangel007/litematica_instructions(verifier 逐块校验操作流程):https://github.com/Michaelangel007/litematica_instructions
- [S6] WesterosCraft Docs — General Building Guidelines(plotting/反馈/Done 块/分级项目制):https://westeroscraft.com/docs/rules-and-guidelines/general-building-guidelines
- [S7] WesterosCraft Wiki — Lannisport(四期施工)/ Harrenhal(先完好后做旧)/ White Harbor(分区 plotting 与子项目):https://westeroscraft.com/locations/westerlands/lannisport ,https://westeroscraft.com/locations/riverlands/harrenhal ,https://westeroscraft.com/locations/north/white-harbor
- [S8] Cathedral Talk — Amiens Cathedral 1:1(关键尺寸表/容差/建造者自述):https://www.cathedraltalk.fm/minecraft/amienscathedral1-1
- [S9] Minecraft Forum — Tips for building an airship?(长径比 6:1~8:1/兴登堡锚点/功能甲板):https://www.minecraftforum.net/forums/minecraft-java-edition/survival-mode/221663-tips-for-building-an-airship
- [S10] ExitLag — Minecraft Church Build Guide(旁证,见 §6):https://www.exitlag.com/blog/minecraft-church/
