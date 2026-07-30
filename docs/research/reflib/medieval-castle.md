# 参考知识库:中世纪 / 城堡建筑(MC 原生审美)

> 来源:explore 子代理,2026-07-30。面向模式库与风格卡的类目调研。
> 口径:MC 原生比例(门 2 / 层高 3-4 / 墙厚 1),零滤镜审美(无光影也成立的才算数),拒绝现实比例。
> 现有相关资产:patterns/{crenellation, buttress, arch_window, gable_roof, hip_roof, pilaster, window_trim, mirror_build} + styles/medieval_tower.json。

## 1. 核心技法

### 1.1 比例基准
- 单体:门高 2,层高 3-4(净高),墙厚 1;塔/主楼高宽比 **2.5:1 ~ 4:1**;塔基座 5x5~9x9,圆塔直径取奇数 **5 / 7 / 9**(门才能居中)。
- 群体:幕墙高 **6-9**,走道宽 1-2;塔高 = 墙高 **+3~6**;长墙每 **15-25** 格一座中段塔(MCME 给现实尺度 150-200m,压缩到 MC 原生);主楼(keep)总高 ≈ 幕墙高 **1.5-2 倍**。
- 规划顺序:**由内而外**——先定房间/楼梯井尺寸再定外轮廓,楼梯井位置先行(贯穿全楼,后补必丑)(MCForum 指南第 1-2 条)。

### 1.2 体量分解
- 严禁单盒子:主楼 + 配楼 = **2-4 个体量**,体量间高差 2-4,轮廓线呈阶梯。
- 塔楼必须**外凸墙面 1-2 格**(防御上消除墙根死角 = enfilade;视觉上打破平轮廓)——MCME 与 MCForum 一致强调,凸出塔 > 贴墙塔。
- 转角必设角塔;凸弧形外墙上塔距要比直墙更密(外凸弧线产生新死角)。

### 1.3 墙面进深(零滤镜审美的核心)
- 每 **3-5** 格安排一次 1 格进退:扶壁(3-2-1 收分)/ 壁柱 / 窗套外凸 1 / 每层楼板线 1 格腰线 / 底部 1-2 格基座 flare。
- 材质渐变:主材 **~50%** / 过渡 **~30%** / 次纹理 **~15%** / 强对比点缀 **≤5%**(minecraftgradient 50-30-15-5;现有风格卡 80/15/5 同族)。**团簇分布,禁止水平条纹,禁止均匀随机噪声**;苔藓/裂纹靠下与背阴,洁净砖靠上与雉堞周边。
- 大墙 5-7 种灰系块足够;点缀块处处出现 = 不再是点缀。

### 1.4 屋顶形态
- 人字顶 **45°**(每层收 1 进 1 上),出檐 1,脊线用台阶封口;城堡读感偏陡,主楼/塔尖可至 **60°**(1 进 2 上)。
- 圆塔配圆锥顶:底部 45° 起、顶部加陡,出檐 1。
- 屋顶材料必须**与墙体不同族**(dark_oak_stairs / deepslate_tile_stairs 是社区标配);楼梯成排铺设,脊线干净,禁止在屋顶做材质噪声。

### 1.5 塔楼与雉堞
- 雉堞**只放墙体外沿**(内沿放堞 = 给攻方掩护,MCForum 点名错误);间距 2(1 堞 1 缺);wall 类块高 1,若用整块则高 2(MCME 要求掩体 ≥2)。
- **machicolation(突堞)**:堞口整体外挑 1 格 + 底板留洞/活板门,置于大门上方与长墙中段——1 格外挑同时贡献防御叙事与墙面进深,性价比最高。
- 箭窗节奏:1 宽 x 2 高竖缝,每 **3** 格墙长一缝,各层竖向对齐成列(现有 medieval_tower 卡已收录)。
- 大门:拱洞 **3 宽 x 4 高**;双门 + 闸门(portcullis,fence/iron_bars 格栅);两门之间留 killing zone,上方 winch room——防御逻辑可直接转装饰语言。

### 1.6 材料纪律
- 三层调色板(MCForum primary / floor / trim 体系):主材石砖系 **70-80%**;结构次材云杉/深色橡木(木骨架、楼板、过梁);点缀只给墙角、门框、檐口。
- 一种构件讲一个材料故事;屋顶 ≠ 墙面;墙角收口材料全楼统一。
- 混合必须**按位置确定性**(可种子化),不许每次随机——否则无法复现与验证。
- 全部用生存可量产块(stone 系、spruce、dark_oak、deepslate 系),本身就是审美约束。

## 2. 范例

- [MCME — Castle Realism Guide](https://www.mcmiddleearth.com/community/resources/castle-realism-guide.154/):防御布局逻辑(塔外凸、machicolation、双门 killing zone);取其结构逻辑,尺度压缩到 MC 原生。
- [Minecraft Forum — What Castle Builders Aught to Know](https://www.minecraftforum.net/forums/minecraft-java-edition/survival-mode/2205478-guide-what-minecraft-castle-builders-aught-to):城堡解剖学 + 由内而外规划 + primary/floor/trim 调色板 + 雉堞外沿规则。
- [Minecraft Wall Gradient — 9 Palettes + Ratios](https://minecraftgradient.blog/minecraft-wall-gradient/):50/30/15/5 混比、9 套现成城堡墙面配方、"团簇非条纹"原则。
- [BlueNerd — How to Build a Castle Gate(190 万播放)](https://www.youtube.com/watch?v=X3yY8Di71Eg):零光影也好 vanilla 门楼模块,学门洞比例与塔楼收口。
- [dudieboy — Norman Castle Keep](https://www.youtube.com/watch?v=rMQZJtUBHhM):主楼体量分解 + 扶壁节奏,MC 原生比例教科书。
- [dudieboy — Fortified Walls and Towers](https://www.youtube.com/watch?v=sV-YNRnDHOM):幕墙 + 塔的组合节奏,直接对应 curtain_wall 生成器。
- [ItsMarloe — Ultimate Castle Survival Base](https://www.youtube.com/watch?v=zS1u_HQtjDY):生存尺度城堡总平面,庭院与功能布局。
- [TrixyBlox 频道](https://www.youtube.com/@TrixyBlox) + [作品盘点](https://www.sportskeeda.com/minecraft/top-5-minecraft-mega-builds-trixyblox):巨型城堡与地形的融合(整平、过渡带),学"建筑贴地"而非悬浮。
- [Grian 技法总结(Sportskeeda)](https://www.sportskeeda.com/minecraft/grian-s-helpful-building-techniques-minecraft):细节块思维(楼梯/活板门/按钮做进深与器具暗示),内饰与微进深素材库。
- [r/Minecraftbuilds](https://www.reddit.com/r/Minecraftbuilds/):零滤镜评审文化现场——"好看只是因为光影"在社区即判负,可当作验收标准语料。

## 3. 反例

- **盒子平墙**:单材料、无进退、无扶壁/腰线节奏、无基座 flare → 远读是一张"灰色 sheet",无光影下彻底死亡。修法:每 3-5 格一次 1 格进退 + 底部 flare + 顶部雉堞三层收口。
- **鱼鳞顶 / 噪声顶**:屋顶铺满楼梯-台阶"鳞片"或多色随机补丁。屋顶的职责是干净的大色块轮廓(单材楼梯排 + 脊线);材质变化属于墙面且按比例团簇。顶上一噪声,全楼显脏。
- **现实比例大教堂/宫殿**:门 6+ 高、墙 3-5 厚、跨度 40+——玩家(2 格高)在里面丢失尺度,无光影时内部是一片空洞;细节密度被尺度稀释。MC 原生审美以门 2 / 层高 3-4 / 墙厚 1 为锚,宏大感靠**体量组合与塔楼群**而非单体内空。
- (次级)雉堞内外沿都放、塔与墙齐平不凸:防御逻辑错 + 轮廓平,属于"贴图式城堡"。

## 4. 对模式库的建议

已有覆盖:crenellation(雉堞)、buttress(扶壁)、arch_window(拱窗)、gable_roof / hip_roof、 pilaster / window_trim / string-course 参数(壁柱/窗套/腰线)、mirror_build(对称)、validators(symmetry_check / collision_check)。

**缺口(按优先级)**:

| 新 pattern | 参数面 | 说明 |
| --- | --- | --- |
| `curtain_wall` | origin, length, height(6-9), thickness(1), buttress_spacing(4-5, 0=off), walkway_overhang(0-1), parapet(crenellation\|slab), base_flare(0-2), material | 幕墙段生成器;**组合调用** crenellation + buttress,不重复造轮子 |
| `round_tower` | center, diameter(5\|7\|9), height, taper(0-2), base_flare(0-2), material | MC 圆必须模板化;奇数直径门居中 |
| `conical_roof` | center, diameter, pitch(45\|60), overhang(0-1), spire(0-3), material | 圆塔尖顶;底部 45° 顶部加陡两段式 |
| `machicolation` | origin, length, side, projection(1), material, gaps(every 2-3) | 堞口外挑 1 格 + 底板留洞;置于门洞上方与长墙中段 |
| `gatehouse` | origin, width(7-13), arch(3x4), portcullis(iron_bars\|spruce_fence), flank_towers(diameter 5-7), killing_zone_depth | 门楼总成;portcullis 可独立成小 pattern(格栅 + 底部尖齿) |
| `texture_mixer` | region, bands:[{material, weight, y_min, y_max}], seed | 把风格卡 primary_mix(80/15/5)落成确定性按位置混合;支持"下脏上净"的 y 向渐变权重;现有风格卡的 mix 描述目前没有执行体 |
| `spiral_stair` | center, footprint(3\|5), floors, floor_height(3-4), material | 塔楼内芯;楼梯井先行原则的载体 |
| `window_column` | origin, storeys, spacing(3), size(1x2), lintel_material | 箭窗竖列节奏放置,补 arch_window 的群体排布 |

**validators 增补建议**:`proportion_check`(门 2 / 层高 3-4 / 墙厚 1 / 高宽比 1:1-4:1)、`palette_check`(点缀比 ≤15%、屋顶材料 ≠ 墙面)、`flat_run_check`(无进退平直墙段 >7 格报警——对应"盒子平墙"反例的自动拦截)。
