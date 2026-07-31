# 参考知识库:雕像/有机体建造法(施工方法论) — 2026-07-31

> 调研日期 2026-07-31,来源 9 个(7 个全文验证 + 2 个仅搜索引擎摘要级,可达性见 §6)
> 与 `statues.md` 分工:statues.md = 比例基准/调色板/照片转体素反例;**本文 = 施工流程(骨架 vs 切片)、体素曲面抗锯齿、翻车点清单与 AI 步骤卡**。数字标注沿用惯例:[引] = 有社区出处;[推] = 解剖惯例/实践推导。比例与调色板基础数据一律交叉引用 statues.md,不重复造数。

## 1. 起手式之争:骨架先行 vs 轮廓切片 vs 素体组装

顶级 builder 的 organic 起手式实测存在**三个流派**,各有适用域,选型错误本身就是翻车源(见 §4-1/§4-6)。

### 1.1 骨架/线框先行(armature-first)— 动态生物首选

- **流程(Be_a_St, NewHeaven 团队成员, minecraft.net 官方专访)**[引]:确定姿态 → **搭"火柴人"骨架,关节处放球体** → 沿骨架拉线框(wireframe)→ 填充体积成皮肤 → 机械/装饰件**单独建造后嫁接(graft)**到 organic 本体上。其自述爪子在早期阶段"像面条",靠"retry and retry"迭代收敛。
- **旁证**:Planet Minecraft《Finem Terrae》龙教程(仅摘要级验证):"Begin your organic by making a 'stickman' version of your organic (also known as a wire-frame)";Be_a_St 同时推荐 Hytherde 的 YouTube organic 线框大师课(原话:学 organic 看**工具教程**(WorldEdit/VoxelSniper/GoBrush),别看太多成品建造教程,会带偏构图直觉)[引]。
- **人形特例(ManaCube 教程)**[引]:figure drawing 惯例直接映射 —— **关节=球、骨骼=线**(肩/肘/膝/踝放球,连线为骨),再在骨骼间填 ovoid 肌肉段。
- **AI 可执行参数化**:骨架 = 关节点坐标表 + 骨骼段列表;每关节放球,**球半径 = 该处肢体截面半径 +0~1 格**[推];骨骼链相邻段截面差 ≤1 格(与 statues.md 椎骨链规则同源);**比例在骨架阶段即可验收**——头身比/腿长直接量关节坐标,不用等填体积。

### 1.2 轮廓切片法(slice/outline-first)— 静态雕像与回转体部件首选

- **2D 剪影层**:statues.md §1 已立"剪影优先"铁律(单色勾轮廓→填体积→细节),本文不重复。
- **3D 切片层(本文新增)**[引]:球/椭球 = **堆叠变径圆切片**,中间层直径最大,向两端逐层收;施工纪律 = 先放 X/Y/Z 中轴标记 → 先做中间层 → 上下对称逐层外推 → 多视角巡检(四个正方向投影都该是圆)。**尺寸阈值:直径 <10 格 = 方块感重;15–25 格 = 可辨但有阶梯;30–50 格 = 光滑,主流区间;60+ = 极光滑但料耗巨大**。空心壳 vs 实心按用途切换;**光面块(石英/混凝土/海晶)藏阶梯,粗纹理块(圆石)放大阶梯**。
- **AI 可执行参数化**:任意回转体部件 = 主轴 + 半径函数 r(h)(球=余弦曲线);切片轮廓直接查圆表(= 预计算 run-length,见 §3.1);相邻切片半径差应单调,禁止忽大忽小[推]。

### 1.3 素体组装(primitive assembly)— 卡通/中小型圆润 organic 首选

- **流程(ManaCube《Seeing the Simple Shapes》)**[引]:参考图分解为圆/椭圆 → 用 WorldEdit `//sphere`(可给不等三轴生成 ovoid)摆素体 → 需要锐边就把 ovoid **放大一倍再 `//cut` 切半** → 四肢/手指/耳等小件用 `/brush sphere` 刷 → 手工修形收尾。明示局限:**人形面部细节是该方法短板**,素体只能给底座,传神靠手修。
- **破对称**:该教程点评范例时专门指出"**并非完全对称,这是给作品生气的手法**"[引]——与 statues.md 行走姿态打破镜像互证。
- **AI 可执行参数化**:每部件 = 椭球(中心/三轴半径/旋转)± 裁切平面集;组装后必须接 §3.3 表面平滑 pass,否则读作"一堆球"。

### 1.4 选型决策表[推]

| 目标 | 推荐起手式 |
|---|---|
| 有四肢/翼/尾的**动态**生物(龙/兽/人形动作) | 1.1 骨架先行 |
| **静态正面观赏**雕像(纪念像/头像/胸像) | 1.2 剪影+切片 |
| 躯干/头颅等**近回转体部件** | 1.2 切片(作为 1.1/1.3 的部件工艺) |
| 圆润卡通角色、中小型动物 | 1.3 素体组装 |
| >50 格巨型且多姿态 | 1.1 骨架定大局 + 1.2 切片做躯干 + 手修细节 |

## 2. 比例规范(增量部分)

主体数据在 statues.md §1(双足 8:12:12 皮肤正典、可读性头放大到总高 1/5–1/4、四足/翼龙全套)。本文只补三条:

- **骨架阶段验比例**[推]:比例检查前移到 armature 完成时——在关节坐标表上直接断言(头高/总高、腿长/躯干长),比填完体积再改成本低一个数量级。
- **尺度与细节的硬挂钩**[引]:MegRae(后与 ManDooMiN 齐名的 organic 教程作者)在 Minecraft Forum 自述雕像"只有预期一半大小,细节被迫受限,脸想做得有体积感但做不好"——脸做平的第一原因是**尺度不够**,不是技法不够。对应 statues.md 阈值:最小辨识特征 ≥1 格,双足人形 ≥12–16 格高。
- **写实 7.5–8 头身**:美术通识基准,**本次未找到 MC 专属文字源**,列此仅作风格化参考系;MC 雕像实务以 8:12:12 皮肤正典+头部夸张为准[推,证据等级低]。

## 3. 体素曲面抗锯齿(三层模型)

把像素画 AA 理论(PixelJoint 经典教程)映射到 3D 体素,分**结构/明暗/几何**三层,各有独立验收法。

### 3.1 结构层:轮廓阶梯的 run-length 纪律

- **病因**:锯齿(jaggies)= 阶梯段长不一致。修复 = 让段长序列均匀[引]。
- **量化判据**:好的斜线 run 序列 = **2-2-2、1-2-1-2** 这类规则序列;坏序列 = **1-3-1-1-4**(忽长忽短)[引]。3D 推广:曲面任何投影轮廓的阶梯 run 序列必须**单调或对称**,违者即 jaggies[推]。
- **工程化解法**:不要徒手拍脑袋数格子——圆/椭圆/球直接用生成器查表,等于白拿预计算的 run-length[引]。
- **AA 用不用的尺度开关**:像素画惯例 **≥64 px 才值得做颜色 AA,≤32 px 时 AA 本身读作噪点**[引];映射到 MC:**<15 格的小部件别做渐变 AA(老实用单色+清晰剪影),30+ 格大曲面必须做**(与 §1.2 球体阈值、statues.md 尺度阈值三方互证)[推]。

### 3.2 明暗层:渐变纪律与 dithering

- **选色优先级**:value(明度)> colour(色相)> texture(贴面)[引, ArdaCraft];与 statues.md "明度 ramp"一致。
- **禁跳阶**:新手毁渐变的第一方式是漏掉中间阶(红直接贴黄);除贴面干扰等少数例外,**严格按 palette 顺序逐阶过渡**[引]。
- **splatter 反模式**:随机撒点不是纹理;正确图案 = **有结构的 blob 团块**(模拟水渍/风化的聚集),团块轮廓**忌 45° 斜泻长条**;拿不准就眯眼看主形[引]。
- **banding(条带化)四形态**:hugging(阴影与轮廓平行等宽)/ fat pixels / skip-one / 45° 对齐——本质是**像素对齐暴露网格**[引, PixelJoint]。曲面表现 = 阴影带处处等宽绕体一周;**修复 = 带宽做渐变,或 dither 打断**[引, Sprite-AI]。
- **pillow shading(枕头阴影)**:阴影沿轮廓走而不是沿光源走,成品像充气枕头[引]。修复 = **固定单一光源方向**;MC 天然解 = 天光:顶面亮一档、底/腹面暗一档(即 statues.md 竖直轴 ramp,本文给出"为什么")[推]。
- **dithering 用量**:50/50 棋盘为主,过渡带可加 25/75、75/25 档[引];**dither 面积过半就该新增一个中间色而不是继续抖**[引];两色对比越低 dither 越隐形[引];**random dither = 噪点,禁**[引]。对应 statues.md "阶间 20–30% 棋盘噪声混掺"。
- **流程铁律(canvas-first)**:先用羊毛/素色做素模定形,**渐变是建造的最后一步——"伟大的渐变救不了拉垮的形体"**[引, ArdaCraft]。

### 3.3 几何层:半格平滑与材质

- 阶梯面转 **stairs/slabs 半格过渡**(statues.md §4 已列为待建 surface-smoothing pass,本文确认其为职业 organic 与 voxelizer 输出的分水岭)。
- **材质选择影响阶梯可见度**:光面均色块藏阶梯,强贴面块放大阶梯[引, sphere guide];曲面皮肤禁用图案贴面块(statues.md 叙事块禁令)与之同源。
- **孤立块 = 噪点**:不属于任何同色簇的单块只暴露网格、制造噪声;唯二合法用途 = 高光点、不可或缺的小细节[引, PixelJoint]——即 statues.md `thin_feature_check` 的理论依据。

## 4. 常见翻车点(症状 → 病因 → 修复,全部带源)

| # | 症状 | 病因 | 修复 | 源 |
|---|---|---|---|---|
| 1 | 平板脸 + 1×1 塔身 + 两根棍当手臂 | 2D 平面思维,无体积 | 骨架/素体先行,先体积后细节 | Minecraft Forum 新手自曝[引] |
| 2 | 脸做平、细节糊 | **尺度不足**(预期一半大小,细节被迫放弃) | 放大到阈值以上或主动简化特征 | MegRae 论坛自述[引] |
| 3 | 漂浮手指/断件 | 连通性缺失 | `thin_feature_check`;头颈重叠 1 格 | 论坛 critique[引]+statues.md |
| 4 | 渐变脏、色块打架 | 跳阶 + splatter 撒点 | 按阶过渡,blob 团块结构化 | ArdaCraft[引] |
| 5 | 曲面像充气枕头 | pillow shading,无光源 | 固定天光方向,顶亮腹暗 | PixelJoint[引] |
| 6 | 阴影绕体等宽像描边 | banding | 带宽渐变 + dither 打断 | PixelJoint/Sprite-AI[引] |
| 7 | 轮廓毛边锯齿 | run-length 混乱 | 单调/对称 run 序列,查圆表 | PixelJoint/Sprite-AI[引] |
| 8 | 姿态僵硬像摆件 | 全镜像对称 | 破对称:腿部相位差/头部偏转 | ManaCube[引]+statues.md |
| 9 | 方形基座抢戏 | 锐角+长平行线把视线拉走 | 基座也做 organic 收边,避长直平行线 | AvionPhoton 论坛 critique[引] |
| 10 | 爪/尾尖像面条 | 截面过细过长 | 最小截面 2×2,尖端 1×1 长 ≤2 | Be_a_St 自述[引]+statues.md |
| 11 | 曲面阶梯感刺眼 | 粗纹理块做曲面 | 换光面均色块 + stairs/slabs | sphere guide[引] |
| 12 | 先堆细节后修形,越修越乱 | 流程倒置 | canvas-first:素模→验收→最后渐变 | ArdaCraft[引] |

另:Be_a_St 的元翻车提醒——**项目级烂尾**是最大翻车(Carbon Roar 本体 1.5 个月,收尾拖了 1.5 年);对策 = 分期交付(本体→基座→环境)[引]。

## 5. AI 可执行步骤卡(主流程)

```
Step 0  定标:主观赏轴 + 目标高度 H(校验:最小特征 ≥1 格;双足 H≥12–16)
Step 1  选型:按 §1.4 决策表选 骨架/切片/素体 起手式
Step 2  起形:
        [骨架] 关节坐标表+骨骼链(段截面差 ≤1,关节球 r=肢体 r+0~1)
               → 骨架上验比例(头/H、腿/躯干)→ 填体积
        [切片] 主轴+r(h) 半径函数 → 逐层圆表切片(中轴标记,上下对称)
        [素体] 椭球参数表 ± 裁切平面 → 组装
Step 3  体积验收:30–50 格眯眼剪影测试 + 连通性检查(禁 1×1 悬丝/漂浮孤岛)
Step 4  表面 pass:阶梯面 → stairs/slabs 半格;贴面统一换光面块
Step 5  明暗 pass:3–5 阶明度 ramp(顶+1/腹−1),按阶不跳;
        阶间 25/75→50/50 dither 过渡带(占比 ≤30%);阴影带宽做渐变防 banding
Step 6  细节+破对称:表情/关节/纹理最后做;镜像只作用躯干,
        四肢给相位差,头部 yaw/pitch 偏 1 档
Step 7  验收清单(逐项过 §4 翻车表 12 条)
```

## 6. 来源清单

全文验证(7):

1. [Beastly Build — minecraft.net 官方专访 Be_a_St](https://www.minecraft.net/en-us/article/beastly-build):骨架+关节球+线框流程、件体嫁接、迭代与烂尾教训、Hytherde 大师课与"看工具教程"建议。§1.1/§4-10/§4 末主源。
2. [Seeing The Simple Shapes (A Beginner's Guide to Organics) — ManaCube 论坛教程](https://manacube.com/threads/basics-seeing-the-simple-shapes-a-beginners-guide-to-organics.79653/):参考图形状分解、WorldEdit ovoid+裁切、关节=球骨骼=线、破对称、方法局限自承。§1.1/§1.3 主源。
3. [Gradient Guide — ArdaCraft Wiki](https://wiki.ardacraft.me/index.php/Gradient_Guide):value>colour>texture、禁跳阶、splatter 反模式、blob 团块、canvas-first。§3.2 主源。
4. [The Pixel Art Tutorial (cure) — Pixel Joint](https://pixeljoint.com/forum/forum_posts.asp?TID=11299):jaggies/banding 四形态/pillow shading/dithering 体系/孤立像素=噪点/调色板控制。§3.1/§3.2 主源。(打印版: https://pixeljoint.com/forum/printer_friendly_posts.asp?TID=11299)
5. [Pixel art fundamentals — Sprite-AI](https://www.sprite-ai.art/guides/pixel-art-fundamentals):run 序列量化判据(2-2-2 好 / 1-3-1-1-4 坏)、AA 尺度开关(≥64 用 / ≤32 弃)、banding 修复、调色板色数表。§3.1/§3.2 辅源。
6. [How to Build a Sphere in Minecraft Step by Step — Minecraft Circle Generator](https://minecraftcircle-generator.com/blog/how-to-build-a-sphere-in-minecraft):切片堆叠法、尺寸阈值(<10/15–25/30–50/60+)、中轴标记、对称施工、材质对阶梯可见度的影响。§1.2/§3.3 主源。
7. [Thoughts on this build? (and more) — Minecraft Forum](https://www.minecraftforum.net/forums/minecraft-java-edition/creative-mode/2869803-thoughts-on-this-build-and-more):MegRae 雕像 critique 原帖(脸平/断指/尺度不足自承)、AvionPhoton 基座 critique、新手"6×6 脸+1×1 塔身"自曝。§2/§4 主源。

摘要级验证(2,Planet Minecraft 全站 Cloudflare 403,仅搜索引擎摘要可核实,引用语句照录摘要):

8. [Finem Terrae (Organic Showcase and Tutorial) — Planet Minecraft](https://www.planetminecraft.com/project/finem-terrae-organic-showcase-and-tutorial/):确认"stickman/wire-frame 起步"与"通用 organic 流程"定位。§1.1 旁证。
9. [Organic Building Tutorial! - Lesson 1 — Planet Minecraft](https://www.planetminecraft.com/blog/organic-building-tutorial---lesson-1/):确认存在 4 课系列 organic 教程(非 step-by-step,方法论取向)。§1.1 旁证。

## 7. 证据不足声明(诚实清单)

- **Reddit r/Minecraftbuilds**:本调研环境 
reddit.com 全域不可达(curl 超时、FetchURL network error),未取得任何帖子原文。Reddit 渠道**证据不足**,本文件无任何依赖 Reddit 的结论。
- **YouTube 文字版**:youtube.com 直连不可达;字幕镜像 youtubetotranscript.com 返回 403、invidious 实例超时。仅核实到教程存在(MegRae《Knight Statue》366–460K 播放、《Dwarf Statue》、《Wizard》;TrixyBlox《Dwarf Statue》508K 播放;andyisyoda《How to Build an Epic Statue》84K 播放;Be_a_St 推荐的 Hytherde 线框大师课),**正文内容未验证**,故本文不引用其任何具体论断。后续若网络可达,优先补 Hytherde 大师课与 MegRae 骑士雕像两篇文字版。
- **7.5–8 头身写实基准**:无 MC 专属文字源,§2 已标 [推,证据等级低]。
- **PMC 两篇全文**:Cloudflare 拦截(403),仅摘要级;若后续取得全文,重点核对 Finem Terrae 的 wireframe→填充→表面处理细节步骤。
