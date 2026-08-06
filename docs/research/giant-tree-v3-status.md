# 巨树生成器 v3 状态与问题清单(供评审/接手)

> 2026-08-07。面向另一个 agent 的评审简报:文件在哪、架构是什么、这轮修了哪些根因、还剩什么债、以及"按树型拆分生成器"的提案。结论先行:**机械性 bug 已全部修完并有数据证明;剩下的全是形态打磨项,逐项列在第 3 节。**

## 0. 文件地图

| 文件 | 作用 |
|---|---|
| `aibuild-mod/src/main/resources/assets/aibuild/defaults/patterns/giant_tree.py` | 生成器本体(唯一算法实现,~560 行,纯 stdlib,确定性) |
| `.../patterns/giant_tree.json` | 模式卡(参数/用法/pitfalls,游戏内 agent 读这张) |
| `.../patterns/INDEX.md` | 全模式索引(giant_tree 行已同步 v3) |
| `.../styles/elven_tree.json` / `tree_house.json` | 风格卡里的宿主树引导语(preset/height 指引) |
| `docs/research/tree-forms.md` + `scratch/giant_tree/tree_forms.json` | 11 张形态卡的调研依据(社区案例来源 URL 都在) |
| `scratch/giant_tree/tree_png.py` | 离线 voxel 渲染器(matplotlib),形态目检主力 |
| `scratch/giant_tree/final2_*.json/.png` | 本轮验证产物(5 棵树:22/35/40/60/100 高) |
| 原版算法社区参考 | [Earthcomputer 的 fancy oak 算法解析(gist)](https://gist.github.com/Earthcomputer/41addf80c12d001dfa4391c3a0d03be8)、[minecraft.wiki Tree definition(trunk/foliage placer)](https://minecraft.wiki/w/Tree_definition) |

验证方法(任何人可复跑):
```bash
cd aibuild-mod/src/main/resources/assets/aibuild/defaults/patterns
python giant_tree.py --params '{"origin":[0,0,0],"height":60,"canopy_radius":16,"trunk":3,"seed":5,"preset":"spirit_candelabra"}' --out t.json
python validators/support_check.py --params '{"blocks":"t.json"}'   # 须 all_supported=true
cd ../../../../../.. && python scratch/giant_tree/tree_png.py <t.json> out.png 45 10  # 形态目检
```

## 1. 架构现状(回答"是不是所有树共用一个算法")

**是:一台引擎 + 11 张参数预设卡。** 引擎流程:
1. **顶梢干(leader)**:从地面一路长到树梢(树脊),干形四式(straight/curved/leaning/spiral)以**解析偏移曲线**驱动(偏移有界,不会漂出冠幅)。
2. **显性主枝**:3-6 条样条,低位起叉(0.35-0.55 树高),短平展再上扬。
3. **云片层盘**:沿主枝后半程布盘链 + 分叉区核心盘 + 顶盘(盘顶≈树梢)。
4. **盘内辐枝扇**:每盘锚枝到盘心,5-7 条辐条打到壳缘(dr≥10 的盘辐根 2 宽)。
5. **栅格化**:主干按截面逐格画(渐进收分 ts×ts→1x1,缩径层铺 bottom 半砖台阶;每层 vline 桥保底连通),枝按 desc 管径分级(2 宽 log 梁/单 log/fence 梢),板根阶梯鳍。
6. **叶**:每盘镂空壳层(v∈[0.68,1] 或贴木 2.4 内;小盘降内界+减镂空补实),全部 persistent=true。
7. **flood-fill 剪枝**:不连通的木/叶全剪(连通性有兜底,正常剪 0-3%)。

## 2. 本轮(v3)修复的根因 — 全部有数据证明

| 症状(实测) | 根因 | 修法 |
|---|---|---|
| **断头**:要 40 高得 28,要 60 得 50 | ①v2 主干止于冠底,顶盘离所有节点超过殖民影响半径(4 格)永久锁死;②弯/螺旋干逐层截面中心漂移,相邻层 xz 各偏 1 格=对角接触,flood-fill 把整段顶梢+顶盘剪没 | 顶梢干直贯树梢(干即树脊);主干每层铺 vline 层内连通桥 |
| **粗细突变** | 收分只在 65% 处缩一档 | 沿顶梢 25% 后渐进收分到 1x1,每档缩径层旧截面外环铺 bottom 半砖(0.5 格台阶) |
| **平板木**(1-2 格厚水平木板穿冠) | 空间殖民的吸引点均布在扁椭球盘内 → 细枝把整盘淤成实心木板 | 废除殖民改**确定性辐枝扇**(轮辐内构=真实云片树);附带收益:地标级从 ~40s → 0.2s |
| **葡萄串冠** | v2 叶=末梢绒球 | 盘壳叶(壳层+贴木簇) |
| **虫蛀冠**(小树) | 小盘壳仅 1 格厚,镂空一挖就穿 | 小盘壳内界 0.68→0.45、镂空按 dr/5 缩放 |
| **螺旋干漂出冠**(读成悬空裸枝) | 偏向积分漂移,半径=a/f 不可控 | 解析偏移曲线差分驱动,螺旋半径钳 ≤2.5、蛇形振幅 ≤2.0 |
| **高度上限** | height≤60/canopy≤20/trunk≤3,地标级造不出 | 10-150 / 3-50 / 2-5 |
| **蜘蛛腿** | 主枝起角 0.1-0.2 rad 太平、枝长 0.75-0.95 冠幅 | 起角 0.25-0.45、枝长 0.5-0.7 冠幅、平展段 25-40% |

验证:5 棵树(22/35/40/60/100 高,5 种 preset)实测 ymax 全部达标(±1);support_check 全绿(0 浮空);生成 0.1-0.2s;裸木检测:除板根鳍尖外所有木块 2.5 格内有叶(主枝前 45% 平展段是**刻意留白**的可读枝构,真实树木如此,tree-forms.md 规律 2)。

**渲染器注意**:tree_png.py 是 matplotlib 单视角投影,遮挡严重,斜视角下"冠下枝干"极易误读成"悬空裸枝"——本轮多次被它误导。评审形态请至少看 az=0/45/90 三个角度 + 纯叶渲染对照,或直接用第 0 节的裸木检测脚本拿数据。

## 3. 剩余债(按优先级)

1. **精灵装饰 special 钩子**(精灵树标杆六条欠债):干发光脉络(替换 5-8% 干柱为发光块?)/冠内光点/垂藤(从盘缘垂下 vine 链)/灯笼挂饰。目前是纯绿树,奇幻感=0。建议在 foliage() 后加 `decorate()` 钩子层,preset 带 special 字段驱动。
2. **按树型拆分**(见第 4 节)。
3. **垂柳/榕树是真缺算法**:weeping_willow 的垂坠枝、banyan 的多干+气生根当前是近似卡(pitfalls 已注明)。
4. **针叶塔形缺**:sky_pillar 用盘链近似锥形,不像真云杉(层叠裙边)。MC 社区针叶树成熟做法=逐层环(半径随高度递减+裙边下垂),与阔叶盘链不同构。
5. **半砖过渡目前只在主干缩径**;主枝 2 宽→1 宽的过渡是突变(暂可接受,枝径小)。
6. **板根方向与干形不解耦**:螺旋干基部已 ramp 归零,板根永远正向;斜生树的"高岸侧抓地根"未做(leaning_river 卡期望)。

## 4. 拆分提案(用户 2026-08-07 提出,我同意按几何原型拆)

**判据沿用项目惯例:新几何才开新文件,参数差异不开。** 现状是所有树挤在一台引擎里,针叶/垂枝/伞盖其实表达不了。

| 文件(拟) | 覆盖 | 几何差异 |
|---|---|---|
| `giant_tree.py`(现状保留) | 阔叶云片树:ancient_oak/world_tree/spirit_candelabra/gnarled_twist/cloud_disc/banyan_court(近似) 等 | 主枝样条+层盘+辐扇 |
| `conifer_spire.py`(新) | sky_pillar/雪松/云杉/塔形针叶 | 逐层环裙边,无层盘概念 |
| `palm_umbrella.py`(新) | umbrella_acacia/棕榈/平顶伞盖 | 顶端单盘+放射羽状/伞骨,无分层 |
| `weeping_tree.py`(新) | weeping_willow 垂柳 | 主枝+垂坠链(重力向下),与一切上扬逻辑相反 |
| 共享 kernel(抽到 `tree_common.py`) | vline/h3/rhu/截面收分/半砖过渡/flood-fill/emit | 不重复造轮子 |

dead_snag 留在 giant_tree(no_foliage 已支持)。拆分后 INDEX/卡面/preset→生成器映射需要一处路由(建议 preset 名字空间前缀或直接给 card 加 generator 字段)。

## 5. 未实机验证声明

v3 全部只有离线验证(渲染+validators+数据检测)。游戏内首测待用户进行;重点看:① 60 高 spirit_candelabra 实机剪影;② 100 高地标(world_tree,trunk=5)实机体量感;③ 半砖收分台阶实机观感;④ 2 万块地标树的放置耗时(游戏内 agent 分批放块)。
