# 细节技法配方库:门口/窗户/屋檐/阳台/工作间/墙面 — 2026-08-06

> 定位:实机压测发现 AI 细节层全是纸糊的(门=裸门方块、窗=一圈环、屋顶=裸双坡、阳台=一格宽、工作间=工作方块排队)。本篇调研人类 MC 建筑师在 6 个细节主题上的具体做法,全部落到"方块名 + 格数 + 组合顺序"粒度,每个主题末尾给**生成器配方建议**(参数/默认值/变体清单,可直接写代码)。
>
> 与已有 reflib 的关系:立面进退三档词汇表/坡度数学/腰线位置学在 `reflib/facades-roofs.md`;做旧掺比/60-30-10/三层 depth 法则在 `reflib/detailing-depth.md`;房间尺度/动线在 `reflib/interiors.md`。本篇不重复其内容,只做 6 个主题的**施工级补完**;交叉处直接引用。
>
> 取证说明:本环境 reddit r/Minecraftbuilds、minecraft.wiki 英文版、YouTube 多次直连被拒(403/超时),相关条目经搜索摘要、波兰镜像站 minewiki.pl(fandom 原文镜像)、中文 wiki 与教程站交叉取证,逐条标注;未能取到硬数字的地方明示"推断"。审美基准:纯原版方块、零光影成立。

---

## 1. 门口设计(entrance/doorway)— 最高优先级

### 1.1 门洞尺寸分级与场合

| 门洞 | 场合 | 来源 |
|---|---|---|
| 1×2 | 民居/生存小屋默认(原版单门原生尺寸) | gamerempire 10 款民居门全为单门洞 |
| 2×2 | 双开门,小康民居正门 | minecraft.wiki Door + forum 机制帖 |
| 2×3 | 入口大厅/庄园正门 | MCS(reflib/interiors §1.1) |
| 拱洞 5–7 宽 | "好看门洞"甜区,民居拱门 | minecircles |
| 拱洞 9–11 宽 | 宏伟大门 | minecircles |
| 拱洞 13+ 宽 | 城门(可骑马通过) | minecircles |

**双开门机制**:想让两扇门铰链镜像对称,放第二扇时必须站到门洞对侧再放(门总是铰链靠"离玩家最近的边")。生成器放双开门要显式指定两半的 hinge 侧,不能连放两次同参数。([minecraft.wiki/w/Door](https://minecraft.wiki/w/Door),正文 403,机制取自搜索摘要 + [minecraftforum 双开门帖](https://www.minecraftforum.net/forums/minecraft-java-edition/survival-mode/231441-step-by-step-double-doors))

### 1.2 门框材料对比(深框浅墙)

- **铁律:门框料必须与墙面拉开明度差**。白墙配白框 = "感觉门口没做任何装饰"([17173 教程](https://news.17173.com/z/mc/content/10142019/153803173.shtml)明确反例)。
- 落地组合:`dark_oak`/`spruce` 系深框 + 浅墙(`white_concrete`/`terracotta`/浅色木板);反转型(深墙浅框)用 `quartz`/白混凝土框。ByPixelbot 美学小屋即全屋 `terracotta` 墙 × `dark_oak` 顶地的深-浅体系([bypixelbot](https://www.bypixelbot.com/blog/how-to-make-an-aesthetic-minecraft-house))。
- 门框是点缀块法定落点之一(detailing-depth §1.5),允许锐利色差——小件跳变规则。

### 1.3 门框构造三式(组合顺序)

1. **活板门包框(成本最低,默认式)**:1 扇 `oak_door` + **7 个 `oak_trapdoor`** 围贴门洞外圈(左右各 2、上 3)+ 两侧 2 个 `oak_log` + 2 个 `flower_pot`([gamerempire](https://gamerempire.net/10-stunning-minecraft-front-door-design-ideas/))。
2. **楼梯描边 + 雕饰门楣(石造)**:15 个 `stone_brick_stairs` 沿门洞外圈描边 + **门楣位 2 个 `chiseled_stone_bricks`** + 7 个 `oak_trapdoor` + 2 个 `spruce_button`(同上)。
3. **外凸门框 + 倒置楼梯压顶(官方建筑书)**:门框整体**凸出墙面 1 格**,顶沿一圈倒置楼梯(`*_stairs` half=top)收头([官方 Minecraft 建筑书 PDF](https://dl.gamesradar.com/bookazine_pdfs/GMP29.ebook_minecraft_vol20.pdf),沙漠神庙门改造段)。

### 1.4 拱形门洞参数化(minecircles,数字最硬的来源)

- **拱高 = 拱宽的一半**;5–7 宽门拱 → 3–4 格高;**中心净高 ≥3**(2 格行走 + 1 格头部余量,<3 碰头且压抑)。
- **拱厚 = 墙厚,至少 2 格**;1 格厚薄拱被点名为"looks flat/unfinished"。
- 施工顺序:取像素圆模板的上半弧,从一侧柱脚逐格沿弧线上到顶点,**镜像**另一侧——严禁徒手画(头号错误 = 左右不对称,"arches need perfect symmetry")。
- 平滑:弧线上用楼梯+半砖过渡("gradually decreasing the width",[ofzen 摘要](https://www.ofzenandcomputing.com/minecraft-archway-designs/),原文 403)。
- **拱顶正中央一块换异材质 = keystone**。
- 变体:哥特尖拱 = 两段错位半弧在顶点相交。
- 来源:[minecircles.com/blog/arches-curved-bridges-minecraft](https://minecircles.com/blog/arches-curved-bridges-minecraft/)。

### 1.5 凹龛、台阶(stoop)与雨棚(awning)

- **门退 1 格做凹龛**(Avomance, detailing-depth §1.1 已收)——本篇重申:这是门口最便宜的 depth。
- stoop 材料:石材混铺做旧(`cobblestone` + `mossy_cobblestone` 随机)([bypixelbot 橡木小屋](https://www.bypixelbot.com/blog/oak-starter-house))。**层数/进深各来源均无硬数字,按"地基抬高几格就做几步、每步进深 1"处理(本篇建议值)**。
- 门前陈设组合:`spruce_stairs` 矮凳 + `light_gray_carpet` 门垫 + `flower_pot`+`dandelion` + `mossy_stone_brick_wall` 矮栏([bypixelbot 小屋教程](https://www.bypixelbot.com/blog/minecraft-cottage-house-tutorial))。
- **篝火雨棚配方**:5 个 `campfire`(锹扑灭)并排当棚面板条 + 4 个 `spruce_fence` 立柱支撑 + 2 个 `lantern` + 5 个树叶垂边(gamerempire overgrown 门)。
- 极简雨棚:3 个 `*_slab` + 2 个 `*_stairs` 悬挑门楣位 + 檐下 2 个 `lantern`;出挑 1 格、宽 3(覆盖 1 宽门洞 + 两侧框,从材料量推断)。

### 1.6 门两侧装饰

- 灯笼柱:`dark_oak_fence` 1–2 格高 + 顶端 `lantern`,**左右对称各一根**,门阶口可配 `fence_gate`([bypixelbot starter cabin](https://www.bypixelbot.com/blog/minecraft-easy-and-simple-starter-survival-cabin))。
- 对称性是所有来源的共同模式:花盆/灯笼/长凳成对出现。

### 1.7 反例

- 徒手画拱、左右不对称(头号错误);拱只做 1 格厚;拱尺度与建筑不匹配;门洞净高 <3(minecircles 四条全收)。
- 门饰与墙体同色同料(17173)。
- 大宅/城堡门洞直接敞开,或"随便立两根栅栏堵门"(gamerempire 点名低级做法)。
- 裸门方块直接嵌在平板墙上 = 本项目现状,正是本篇要消灭的。

### 1.8 生成器配方建议:`doorway`(新,最高优先)

```
参数:
  opening_w: 1|2|3|5        # 默认 1(民居);5 走拱形
  opening_h: 2|3            # 默认 2;opening_w>=3 时默认 3
  shape: rect|arch          # 默认 rect;arch 时 arch_rise=opening_w/2, keystone=true
  recess: 0|1               # 默认 1(凹龛)
  wall_thickness: >=1       # arch 时拱厚=max(2, wall_thickness)
  frame_style: trapdoor_wrap(默认,1×2 门) | stairs_outline(石造) | protruding_lintel(官方书式)
  frame_material: 深色对照料 # 规则:与 wall_material 明度差 >= 阈值;浅墙→dark_oak/spruce,深墙→quartz
  double_door: bool         # opening_w==2 时默认 true,显式镜像 hinge
  stoop: {steps: 地基抬高分, tread: 1, material: cobblestone+mossy_cobblestone 混铺}
  awning: none|campfire|slab_stair   # 默认 slab_stair;projection=1, width=opening_w+2, 下挂 lantern×2
  side_decor: lantern_post|flower_pot|bench|none  # 默认 lantern_post,强制左右对称
组合顺序: 开洞(退 1 格) → 门框描边 → 门楣/拱(含 keystone) → 门扇(双开显式 hinge) → stoop → awning → 侧饰
变体清单: 民居活板门包框 / 石造雕饰楣 / 外凸官方书式 / 拱形(半圆/尖拱) / 双开 2×2 / 大厅 2×3
校验: 门洞净高>=3(arch);arch 厚>=2;frame_material 与墙明度差校验不通过 → 换料重抽
```

---

## 2. 窗户细节(window detailing)

### 2.1 窗洞定位公式

- **窗台(窗洞下沿)离地 1–2 格**(玩家视线高度,fandom 教程);**墙净高 ≥3,最好 ≥4**——2 格高房间开不了正常窗(wikiHow)。
- 现代定式:墙高 5,正面开 **3 宽 × 4 高** 洞口,洞口两侧各留 1 格实体边框([decorhomeguides](https://decorhomeguides.com/minecraft-modern-house-2/))。
- 顺序:先立墙定高 → 按"离地 1–2"开洞 → 后装玻璃。多层建筑同列窗必须对位、竖向窗间墙 ≥1(facades-roofs §1.4 已收,重申)。

### 2.2 玻璃纵深(窗户第一细节)

- **玻璃比墙面内凹 1 格**:双层墙外层留洞、玻璃放内层;或墙外再挂一层 `glass_pane` 当前景("set regular glass one block further into the wall",wikiHow)。内凹 1 格即可,无需更深。
- 反向纵深:圆形/外凸框 = 框凸 1 + 玻璃在框后(fandom 官方强烈推荐,facades-roofs §1.4 已收)。
- `glass_pane` vs `glass`:pane 自带细框连接感、可做前景层;整面幕墙用 block。例外:挡水必须用 block(pane 漏水,fandom)。

### 2.3 窗台/百叶/楣/拱心石(组合顺序)

1. **窗台**:窗洞下沿外贴半砖或**倒放楼梯**,出挑 ≤1;石墙配石半砖、木墙配木半砖(vectorlinux/tecnobits)。
2. **花箱(升级)**:窗台下放 `grass_block` + 侧面贴 `*_trapdoor` 包边 + 草上种花——wikiHow 评价"简单但观感提升巨大"。
3. **百叶**:**1×2 窗两侧各竖贴 1 个木质活板门**,合页朝窗、打开态贴墙(fandom 原文配方);2 宽窗左右各 1–2 扇。中世纪三件套 = `fence` 窗棂 + trapdoor 百叶 + slab/stair 阴影([exitlag 中世纪教程](https://www.exitlag.com/blog/minecraft-medieval-house/),403,搜索摘要)。
4. **窗楣/拱**:窗顶楼梯正放+倒放对拼出拱线;平顶过梁 = 一排石半砖出挑半格;拱顶中央换料 = keystone(与门拱同法)。教堂做法:窗顶沿口一圈倒放楼梯层叠线脚([edtechrce](https://edtechrce.org/how-to-make-a-small-church-in-minecraft/))。

### 2.4 凸窗(bay window)

- 整窗体量**外凸 1 格、宽 3**,形成"mini room"(fandom 原话);底部倒放楼梯/栅栏托底(oriel 效果),顶部自带小屋顶(facades-roofs §1.4 已收原则,本篇补数字)。

### 2.5 反例

- 玻璃与墙面齐平、无内凹无框(平面化 = 本项目现状)。
- 所有窗同形同尺寸(wikiHow 明确反对);但也不许 over-detailing。
- 窗型与建筑母题打架(fandom 官方案例:圆窗硬塞进凸窗母题被点名)。
- 墙高 <3 开矮窗;中世纪风用整面无框玻璃幕墙(中世纪 = 小窗多扇 + 栅栏棂 + 百叶);水景窗用 pane。

### 2.6 生成器配方建议:`window_trim` 扩参(在现有模式上叠加)

```
新增参数:
  recess: 0|1               # 玻璃内凹,默认 1(现状疑似为 0)
  pane: bool                # 默认 true(玻璃板);幕墙风格 false
  sill: none|half_slab|upside_down_stair|flower_box   # 默认 half_slab;田园/中世纪默认 flower_box
  shutters: bool            # 仅当窗洞 w==1 且 h==2 时默认 true;材料=trapdoor,合页朝窗
  lintel: none|slab|stair_arch   # 默认 slab;stair_arch 时 keystone_material 可另指
  bay: {enabled: bool, projection: 1, width: 3, base: corbel_stairs, roof: mini_gable}  # 默认关
组合顺序: 开洞(离地 sill_height=1~2) → recess 内衬 → 框(凸 0/1) → 玻璃(pane,退 recess) → 窗台 → 百叶 → 楣/拱
变体清单: 中世纪 1×2 四件套(百叶+半砖窗台+花箱+栅栏棂) / 田园花箱窗 / 现代 3×4 幕墙 / 教堂拱窗 / 凸窗
校验: 墙高<3 禁开窗;同列多层窗 x 对齐;中世纪卡禁 pane=false 幕墙
```

---

## 3. 屋檐与屋顶修饰(eaves & roof trim)

### 3.1 出挑与檐下收边(椽子)

- **出挑 1 格是小户型底线惯例**("give that roof a 1 block overhang though, that helps a lot",[FTB 帖](https://forum.feed-the-beast.com/threads/aesthetics-for-builds.5646/));大建筑/大坡度出挑 2。双坡适用宽度 ≤12(facades-roofs §1.5 已收)。
- **有挑檐必有椽子**(WesterosCraft 审核标准:"you want rafters beneath exterior roof blocks"):出挑底面下沿墙顶放反放楼梯 / 半砖 / `*_wall`(圆石墙当椽头极像),**间距 1–2 格一根**([WesterosCraft 帖](https://forum.westeroscraft.com/threads/thegoatlord-builder-application.2111/))。1.13+ 可用 `*_trapdoor` 贴檐口当封檐板。
- 平屋顶:反放楼梯一圈 = 檐沟(gutter),或告示牌一圈收边(minecraft.wiki Roof_types 原文)。
- 顺序:砌墙 → 屋顶最低一排楼梯外悬 1 格 → 逐排内收上升至脊 → 檐下补椽子。

### 3.2 屋脊与山墙收法

- 脊饰:`*_wall` / `*_fence` 沿脊通长一行,两端各加高 1 格做"脊端起翘/吻兽"暗示;**奇数宽**才能汇成居中尖脊(facades-roofs §1.5/1.6 已收,本篇补 WesterosCraft 之外的镜像源:[Roof_decorations](https://minewiki.pl/Specjalna:Obcoj%C4%99zyczne/minecraft.fandom.com%2CTutorials/Roof_decorations))。
- **阶梯山墙(corbie steps)**:山墙高出屋面,整砖逐层 1 进 1 退收阶梯,wiki 评价"simple, effective and distinctive",双坡端部首选变体。
- **山墙封檐(bargeboard 等价物)**:与阶梯山墙相反,屋面伸出山墙 1 格,楼梯沿斜坡边缘外露一圈。
- 变体:半歇山 = 下 3 排双坡 + 上 2½ 排四坡(含脊顶半砖层);盐盒 = 一侧坡远长于另一侧;交叉坡(T/L 平面)施工顺序 = **先建最高屋顶,次高向它逐格合拢,最后从室内删掉 V 形谷线内冗余块**([Roof_types](https://minecraft.wiki/w/Tutorial:Roof_types))。

### 3.3 老虎窗(dormer)放置纪律

- 最小单元 **3 格宽**(窗 1 + 两侧各 1 墙),自带 1:1 小双坡(2–3 排楼梯)或单坡(shed)。
- **三条放置铁律**(真实建筑规范直译,零成本可编码):① 老虎窗脊线/檐口必须**低于主屋顶脊线/檐口**;② 从山墙端**内退 ≥1 格**再布置;③ 多个等距排列且**与下层窗户对位**([dqfnottingham 住宅设计指南](https://www.dqfnottingham.org.uk/hhdg-proportions))。
- 变体全列(wiki 图库):gable/dog-house(默认)、hipped、shed、flat、eyebrow、wall(墙体上延)、blind(纯外观)、Nantucket(两 dog-house 夹一 shed)。
- 触发条件:平面 >15×15 或屋顶下空间够一层 → 必须开老虎窗或做孟莎顶(facades-roofs §1.5 已收)。

### 3.4 烟囱

- `minecraft:bricks` 截面 2×2 或 1×2,贴山墙外侧或穿脊线(link dormer,wiki 有专例);出脊线 **2–3 格**;顶口反放楼梯一圈或半砖压顶;内藏 `campfire`(垫 `hay_bale` 烟柱更高)([Roof_types](https://minecraft.wiki/w/Tutorial:Roof_types) + [forum 营火烟帖](https://www.minecraftforum.net/forums/minecraft-java-edition/creative-mode/3024937),403 搜索摘要)。

### 3.5 反例

- 屋顶与墙同材质、零出挑直接封顶(wiki:收边"唯一不该做的就是和建筑其余部分同材质")。
- 大平面一整片无窗无老虎窗巨坡("large featureless roofs tend to cover barns and hangars")。
- 偶数宽双坡还想门居中(脊线永远偏半格);老虎窗脊高过主脊/贴死山墙边/间距乱排;helm 屋顶楼梯朝四个方向(只应 N-S 或 E-W 两向);平顶不做防刷怪覆盖。

### 3.6 生成器配方建议:`eaves_trim`(新)+ `dormer`(新)+ `chimney`(新)

```
eaves_trim(挂在现有 gable/hip_roof 之后):
  overhang: 1|2             # 默认 1;建筑任一边>12 或坡度>45° 时 2
  rafter: {style: upside_down_stair|slab|wall, spacing: 1|2}  # 默认 stair, spacing=2;overhang>0 时强制开启
  fascia: none|trapdoor     # 默认 none
dormer:
  width: 3                  # 最小单元;宽坡面可 5(窗 2-3)
  type: gable|shed|hipped|eyebrow|wall|blind   # 默认 gable
  ridge_offset_below_main: >=1   # 强制
  gable_inset: >=1               # 强制
  align_to_ground_windows: true  # 与 room_partition 的 window_hints 联动
  spacing: 等距             # n 个均分坡面,净距 >=2
chimney:
  section: 2x2|1x2, material: bricks, height_above_ridge: 2|3
  cap: upside_down_stair_ring|slab, smoke: campfire(+hay_bale)
组合顺序: 主坡合拢 → 脊饰 → eaves_trim(椽子) → dormer 开洞立小立面扣小顶 → chimney → 山墙收法(阶梯/封檐)
```

---

## 4. 露台/阳台(balcony/terrace)

### 4.1 进深:能用的阳台 ≥2 格

- **1 格进深 = 消防梯/假阳台**:站人即贴栏杆,放不下任何家具(本篇综合推断;所有教程均 2 格起步)。
- 官方教程精确数字:门洞预留 5 格宽,阳台地面外挑 **2 格**、总面 **7×2**(比门洞每侧各宽 1 格),`spruce_trapdoor` 平铺地面 + 外缘一圈 `oak_fence`([TapTap 官方阳台教程](https://www.taptap.cn/moment/15205373841508551))。
- 2 格 = 最小可用(花盆+通行);3 格 = 可放桌椅(楼梯椅+台阶桌)。真实建筑阳台净深 1.2–1.8m 映射 MC = 1–2 紧凑、2–3 舒适,与教程一致。

### 4.2 栏杆材料风格查表

| 风格 | 栏杆 | 来源 |
|---|---|---|
| 田园/木屋 | `oak_fence`/`spruce_fence`,拐角顶灯笼 | TapTap / TheBestMods |
| 现代/豪宅 | `black_stained_glass_pane` 整圈 | [Charlie INTEL 豪宅](https://www.charlieintel.com/minecraft/how-to-build-a-mansion-in-minecraft-268722/) / [切游网](http://www.qieyou.com/content/202011/74692.html) |
| 石造/塔楼 | `iron_bars` | [GameSpecifications 灯塔](https://www.gamespecifications.com/lighthouse-minecraft/) |
| 厚重石栏 | `cobblestone_wall`/`stone_brick_wall` | wikiHow |
| 半透格栅 | 竖开 `*_trapdoor`/`fence_gate` | Coohom(410,搜索摘要) |

### 4.3 出挑与支撑(布尔规则)

- **出挑 1 格:可悬空免支撑**(同屋檐出挑规则)。
- **出挑 ≥2 格:必须给视觉支撑**——托臂 = 底板下沿贴墙一排朝外倒置楼梯;或两角立柱(`fence`/`wall`/去皮原木)落地;或端部斜撑([MinecraftForum 建筑帖](https://www.minecraftforum.net/forums/minecraft-java-edition/creative-mode/2736945-how-to-build-cool-houses) + [verbina29](https://verbina29.neocities.org/articles/mcBuilding):支撑件是制造深度的首要手段)。中世纪 jetty(上层整体外挑)= 外挑 1 + 底沿倒置楼梯托臂。

### 4.4 衔接三型与地面

- 凸出式(默认)/ 凹进式 loggia(立面内挖 2–3 深壁龛,栏杆与墙齐平;带顶大阳台实例 13×13 见 [GrabCraft Jungle Balcony](https://www.grabcraft.com/minecraft/jungle-balcony/tree-houses))/ 半凹半凸转角([EpicQuestz 瑞士村指南](https://forums.epicquestz.com/t/what-a-swiss-village-can-teach-us-about-building-in-minecraft/554))。
- 地面:薄地面 = 下半砖或活板门平铺;常规 = 楼板同材;现代 = 混凝土/石英台阶。
- **朱丽叶阳台**:0 进深——墙面开 2 格高落地门/窗洞,外侧齐墙装 `iron_bars`/黑玻璃板/竖开活板门,可加 1 格深台阶放花盆(社区共识,reddit 未能直连取证)。
- 露台(terrace)区别于阳台:大面积平台(屋顶/地面层),无进深限制,栏杆/女儿墙围合([Comparisons Wiki](https://comparisons.wiki/terrace-vs-balcony/))。

### 4.5 反例

- 1 格进深还想摆家具(本项目现状 = 一格宽露台)。
- 出挑 ≥2 无任何下部支撑,整块"飘"在墙上。
- 栏杆与墙同材同色一大坨(细节块应比主墙深一号,wikiHow);满墙堆细节。
- 阳台地面插火把(应挂墙灯笼,地面留 1 格通行线)。

### 4.6 生成器配方建议:`balcony`(新)

```
参数:
  depth: >=2                # 默认 2;3=可放家具;juliet 型固定 0
  width: door_w + 2         # 默认对齐上层门洞每侧各 +1
  type: protruding(默认)|loggia|corner|juliet
  floor: trapdoor(默认)|slab|slab_full
  railing: 风格查表         # rustic→fence / modern→black_stained_glass_pane / stone→iron_bars|wall
  support: auto             # depth>=2 → corbel(upside_down_stairs 一排) + corner_posts(fence 落地)
  door: 上层墙面对位开门洞(与 room_partition window_hints 同机制)
组合顺序: 对位开门 → 挑板(地面) → 支撑(托臂/柱) → 栏杆 → (可选)花箱/灯笼
变体清单: 田园木栏 2 深 / 现代黑玻璃 3 深 / 石造铁栏 loggia / 朱丽叶 / 转角半凹半凸
校验: depth<2 且 type!=juliet → 拒绝;depth>=2 且无 support → 拒绝
```

---

## 5. 工作间内饰(workstation cluster)

### 5.1 成组摆放,而非一字排开

人类惯例 = **功能组团**,不是沿墙等距排队:

1. **附魔修装组**:15 个 `bookshelf` 围 `enchanting_table` 成 5×5 环(台居中,环留 1 格出入口),**书架与台之间必须留 1 格空气缝**(放任何方块含地毯即失效),书架同层或高 1 格([aestheticgame](https://aestheticgame.com/minecraft-bookshelf-placement-guide/) / [shockbyte](https://shockbyte.com/blog/level-30-enchantments-in-minecraft))。旁置 `grindstone`+`anvil`(+`smithing_table`)构成装备维护角——官方 wiki 配图即此同框组合。
2. **熔炼组**:`furnace`+`blast_furnace`+`smoker` 各 ≥1 按功能相邻;论坛惯例 **2×4(8 台)熔炉墙**;自动熔炉组 8–32 台 + 顶部漏斗链 + 端头大箱([ScalaCube](https://scalacube.com/blog/minecraft/how-to-make-a-super-smelter-in-minecraft) / [MC Forum](https://www.minecraftforum.net/forums/minecraft-java-edition/survival-mode/2823991-question-2x4-furnace-wall-idea))。
3. **合成组**:`crafting_table` 居中,贴邻储藏区(少走回头路,[Coohom](https://www.coohom.com/article/how-to-optimize-your-minecraft-floor-plan-for-survival-gameplay))。
4. 朝向:熔炉系正面(开口面)朝走道,工作方块前方留 1–2 格净空;`grindstone` 可落地/挂墙/倒挂,挂墙是铁匠墙饰惯例([minecraft.wiki Grindstone](https://minecraft.wiki/w/Grindstone))。

### 5.2 铁匠铺调色板(GrabCraft 实测蓝图,直接当权重表)

[Detailed Medieval Blacksmith Forge](https://www.grabcraft.com/minecraft/detailed-medieval-blacksmith-forge/other-193)(17×18 占地、1471 方块):`cobblestone` 204 / `spruce_log` 164 / `oak_planks` 61 / `glass_pane` 62;功能件:`crafting_table`×6、`chest`×6、`furnace`×2、`lava`×4(锻炉火塘)、`cauldron`×2(装水 = 淬火槽)、**`chipped_anvil`+`damaged_anvil` 各 1(残损铁砧做旧)**、`cobweb`×30(角落做旧)、`redstone_lamp`×4。

### 5.3 储藏室箱墙(硬机制)

- **箱子正上方是实体(导电)方块则打不开**;上方放上半砖/楼梯(非导电)可正常开盖 → 箱子上必须盖半砖才能多层叠放([minecraft.wiki Chest](https://minecraft.wiki/w/Chest))。
- `barrel` 头顶有方块也能开 → **木桶墙可一路码到天花板**,适合边角与顶层([minecraft.wiki Barrel](https://minecraft.wiki/w/Barrel))。
- 排布:大箱子贴墙成排,**每侧墙 15 个大箱子**,箱列间留竖向柱位贴 `item_frame`(放代表物品当标签,优于木牌);分类 6 大区:建材/工具装备/食物药水/红石/矿石/生物掉落([MC Forum 储藏室帖](https://www.minecraftforum.net/forums/minecraft-java-edition/survival-mode/262465-storage-room-insight-ideas-and-examples) / [ExitLag 展示框](https://www.exitlag.com/blog/item-frame-minecraft/) / [AllAroundMoms](https://allaroundmoms.com/how-to-organize-storage-room-minecraft/))。
- 大规模阵列混木桶(实测箱海 8.4 TPS vs 木桶 19.2 TPS,[ExpertBeacon](https://expertbeacon.com/are-barrels-better-than-chests/),搜索摘要)。
- 房间模数 9×9 或 11×11,小房间 L 形工区。

### 5.4 杂物与灯光

- 杂物:炼药锅/盔甲架/花盆/地毯/`item_frame` 挂工具;地图房配方:4 云杉活板门+4 云杉楼梯+9 木桶+10 地图+10 展示框+盔甲架+旗帜+头颅+灯笼([TeamVisionary](https://teamvisionary.net/minecraft-building-tutorial-10-interior-details-for-spicing-up-your-minecraft-house/),403 搜索摘要)。
- 灯光:`chain` 垂 `lantern` 吊灯(底端距地 ≥2,interiors §1.5);海晶灯/萤石埋地毯下做隐藏光。

### 5.5 反例

- 箱上压实体方块 → 整排箱墙打不开(最低级错误)。
- 附魔台与书架缝里放地毯/火把 → 30 级附魔泡汤。
- 所有工作方块沿墙一字等距排开(本项目现状)。
- 满地插火把当主光源;只用木牌做标签。

### 5.6 生成器配方建议:`workshop_cluster`(新,替换"工作站排一排")

```
参数:
  groups: [enchant, smithing, smelting, crafting, storage]  # 按房间功能选 1-N 组
  模板(固定相对布局,旋转适配):
    enchant:  5x5 书架环(缺口 1)+ 1 格空气缝 + 邻位 grindstone/anvil/smithing_table
    smithing: cauldron(装水)+anvil(50% 概率换 chipped/damaged 做旧)+grindstone 挂墙+lava 火塘(石围)
    smelting: furnace+blast_furnace+smoker 相邻,正面朝走道,前方净空 1-2
    crafting: crafting_table 居中贴邻 storage 区
    storage:  大箱贴墙每侧 <=15,箱上盖上半砖,item_frame 标签,顶层层用 barrel;>30 箱时 chest:barrel≈1:1
  clutter: {cauldron, armor_stand, flower_pot, carpet, cobweb(角落,<=30 权重)}   # accent_detailing 已有 palette,补功能杂物
  lighting: chain+lantern 吊灯,底端距地 >=2
校验: 箱上必须是导电=false 方块;书架环 1 格缝内禁放任何方块;工作方块前方 1-2 格净空
```

---

## 6. 墙面肌理(wall detailing / depth)

> 通法(三层 depth 法则 / 60-30-10 / 三带做旧百分比 / 同色系混材)已在 `reflib/detailing-depth.md` 全收,本节只补施工级定位数字;线脚位置学与 facades-roofs §1.3 互为表里。

### 6.1 三条水平线脚的高度表([中文 wiki 墙壁与扶壁教程](https://zh.minecraft.wiki/w/Tutorial:%E5%A2%99%E5%A3%81%E5%92%8C%E6%89%B6%E5%A3%81) + exitlag 摘要)

| 线脚 | 高度 | 做法 |
|---|---|---|
| 踢脚/基座线 | 地面以上 1 格 | 一排对比块(深一号:`deepslate_tiles`/深色木台阶);基座出 1 高 1–2(facades-roofs §1.3) |
| 腰线/墙裙线 | 第 2–3 格(腰~胸高) | 窄条:活板门贴边或一排半砖;一条墙最多 2 条(facades-roofs §1.3) |
| 檐口线 | 墙顶下 0–1 格 | 室内净高 6–10 时用**倒置楼梯**一圈(coving);较矮墙用半砖 |

### 6.2 竖向构件:壁柱与 quoins

- 壁柱/竖梁(`stripped_*_log` 或 `*_wall`)**每 3–4 格一根,间距必须一致**;柱头柱脚用楼梯块收头收脚;柱间墙面做凹进面板([exitlag pale-oak 文](https://www.exitlag.com/blog/pale-oak-minecraft/),403 搜索摘要;项目 pilaster 已定 3–6 默认 4,与之兼容)。
- **quoins(墙角加固件)**:两面墙交角处 1 格宽竖向深色带(城堡调色板:墙身 `stone`/`stone_bricks` → 角部与底部 `cracked_stone_bricks`/`deepslate_bricks`),与浅色墙身成框景([minecraftgradient.blog](https://minecraftgradient.blog/minecraft-color-palette/))。
- 华饰高度纪律:2–4 格矮墙顶/底翻 1–2 格即可;高墙装饰带离顶/底边 1–2 层,别贴边;手法 1–4 种封顶(facades-roofs §1.1)。

### 6.3 深度三件套(每面外墙的最低消费)

官方 Avomance 五式的可执行子集([minecraft.net](https://www.minecraft.net/pl-pl/article/make-your-houses-better)):① 屋顶出挑 ≥1;② 门退 1 格凹龛;③ 窗用 pane 不用 block(自凹半格);④ 房基外圈一圈楼梯/半砖;⑤ 大墙用 fence/slab/button/trapdoor 贴片制造 0.1–0.5 格起伏。窗统一内凹 1 格 + 檐下留阴影袋 + 门套深色描边 + 基座加厚(exitlag 摘要)。

### 6.4 做旧与掺比(施工顺序)

- 三阶段管线:**先满铺主块(60%)→ 过渡块(30%)只加在边缘/墙角/阴影区/做旧区/地形接触带 → 点缀(10%)只落门窗框/屋脊等视觉停点**([blockblend 色彩理论](https://blockblend.app/guides/minecraft-color-theory) + minecraftgradient.blog)。
- 三带做旧百分比配方(rustic/ruins、带高 2–4、下脏上净、2–3% 侧放楼梯崩角)全表在 detailing-depth §1.4,生成时逐带加权随机,禁全墙均匀撒。
- 调色板 4–7 块封顶;同族异质感混用(`stone`+`stone_bricks`+`andesite`+`gravel`)比跨色混用安全。

### 6.5 反例

- 整面单一材料素墙(wiki 明确建议避免);"盲目扣洞"——满墙洞但本体火柴盒,细节喧宾夺主([游民星空转载教程](https://www.gamersky.com/handbook/201805/1054549.shtml))。
- 跨色系等强度混拼 = 噪声;点缀密度处处相同 = 点缀失效;黑色系当中调大面积铺(细节被吃掉);渐变直条纹。
- 2–4 格矮墙上堆满全部线脚。

### 6.6 生成器配方建议

```
base_course(新):        # 基座带
  height: 1|2(默认 1), projection: 1, material: 墙身深一号
string_course(兑现卡片已有声明,facades-roofs §4 列为最优先):
  height: 2|3(默认 2=窗台下皮或楼层板标高), projection: 0|1, thickness: 1, 每面墙 <=2 条
cornice(新):
  height: wall_top-1|wall_top, style: upside_down_stairs(净高>=6)|slab(矮墙), projection: 1
quoins(新):
  width: 1, material: 墙身深一号或 cracked/deepslate 系, full_height: true
pilaster(已有):spacing 3-6 默认 4,柱头柱脚楼梯收头
texture_bands(detailing-depth §4 已建议,重申):按带加权,禁全墙均匀
校验: 任一墙面连续 >=7x4 无凸出/无材质变化 → 报警(facades-roofs §3 已定);线脚总数 <=4 种
```

---

## 附:汇总来源表

- minecircles 拱教程:https://minecircles.com/blog/arches-curved-bridges-minecraft/(§1.4 全部拱数字)
- gamerempire 前门 10 式:https://gamerempire.net/10-stunning-minecraft-front-door-design-ideas/(§1.3/1.5 配方)
- 17173 门饰对比:https://news.17173.com/z/mc/content/10142019/153803173.shtml(§1.2)
- bypixelbot 教程族:https://www.bypixelbot.com/blog/how-to-make-an-aesthetic-minecraft-house 等 4 篇(§1.2/1.5/1.6)
- 官方建筑书 PDF:https://dl.gamesradar.com/bookazine_pdfs/GMP29.ebook_minecraft_vol20.pdf(§1.3 外凸门框)
- fandom Adding beauty(minewiki 镜像):§2 窗离地/pane/百叶/凸窗/圆框
- wikiHow Build the Exterior of a Minecraft House:https://www.wikihow.com/Build-the-Exterior-of-a-Minecraft-House(§2 墙高/内凹/花箱;§4 凸出体块)
- decorhomeguides 现代房:https://decorhomeguides.com/minecraft-modern-house-2/(§2.1 3×4 窗)
- minecraft.wiki Roof_types / Roof_construction_guidelines(minewiki 镜像):§3 出挑/变体/老虎窗 8 型/烟囱
- WesterosCraft 审核帖:https://forum.westeroscraft.com/threads/thegoatlord-builder-application.2111/(§3.1 椽子)
- FTB aesthetics 帖:https://forum.feed-the-beast.com/threads/aesthetics-for-builds.5646/(§3.1 出挑底线)
- dqfnottingham 住宅指南:https://www.dqfnottingham.org.uk/hhdg-proportions(§3.3 老虎窗三铁律)
- TapTap 官方阳台教程:https://www.taptap.cn/moment/15205373841508551(§4.1 7×2 配方)
- Charlie INTEL 豪宅:https://www.charlieintel.com/minecraft/how-to-build-a-mansion-in-minecraft-268722/(§4.2 黑玻璃栏)
- GrabCraft 铁匠铺:https://www.grabcraft.com/minecraft/detailed-medieval-blacksmith-forge/other-193(§5.2 材料表)
- minecraft.wiki Chest/Barrel/Grindstone/Enchanting_Table(搜索摘要):§5.1/5.3 机制
- aestheticgame/shockbyte 书架指南:§5.1 附魔环
- MC Forum 储藏室帖(搜索摘要):https://www.minecraftforum.net/forums/minecraft-java-edition/survival-mode/262465-storage-room-insight-ideas-and-examples(§5.3 15 箱)
- blockblend 色彩/渐变指南:https://blockblend.app/guides/minecraft-color-theory、https://blockblend.app/guides/cobblestone-gradient-guide(§6.4)
- 中文 wiki 墙壁与扶壁:https://zh.minecraft.wiki/w/Tutorial:%E5%A2%99%E5%A3%81%E5%92%8C%E6%89%B6%E5%A3%81(§6.1 线脚高度表)
- minecraftgradient.blog 色板指南:https://minecraftgradient.blog/minecraft-color-palette/(§6.2 quoins/§6.4)
- minecraft.net 官方 Avomance:https://www.minecraft.net/pl-pl/article/make-your-houses-better(§6.3)
- 游民星空进阶教程:https://www.gamersky.com/handbook/201805/1054549.shtml(§6.5 反例)

**未能取证渠道声明**:r/Minecraftbuilds 全部 6 个主题均直连被拒,reddit 高赞帖原文未纳入;YouTube 仅取证到标题/目录;stoop 层数、雨棚出挑长度、朱丽叶阳台三处无单一权威数字源,文中已标"推断/共识"。
