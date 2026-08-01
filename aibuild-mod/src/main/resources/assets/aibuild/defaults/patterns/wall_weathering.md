# Wall weathering rules (墙壁肌理规则)

> 配套生成器:`wall_weathering.py`(参数化实现下述全部手法)。
> 数据基础:1668 件 GrabCraft 样本材质统计(scratch/phase9/gc_probe/stats_palettes.md)
> + 社区渐变配方([BlockBlend cobblestone gradient guide](https://blockblend.app/guides/cobblestone-gradient-guide))。

立面"光秃秃"的根因永远是:**单一材质 × 单一深度 × 无竖向分段**。以下四招任意用两招,
墙面就不再是糊上去的纸板。

## 1. 材质掺比(material mixing)

- 公式:1 主材(>=55%)+ 2~3 辅材(各 5~25%),加权随机混入,**不是周期图案**。
- 辅材首选主材的"亲缘变体":`mossy_*` / `cracked_*` / 未加工原型(如 stone_bricks ← cobblestone)。
  跨族混搭(石墙掺木板)几乎必翻车。
- 样本佐证(GrabCraft):石砌类主材 stone_bricks 占 23-30%,cobblestone 8-9%;
  中世纪民居 oak/spruce planks + cobblestone + stone_bricks 混合;没有人会 100% 单材。
- 常用起点(生成器 presets 即这些数字):
  - 石砖做旧:stone_bricks 60 / cracked 15 / mossy 15 / cobblestone 10
  - 圆石田园:cobblestone 55 / mossy_cobble 20 / stone 15 / andesite 10
  - 社区城堡墙基座带:cobblestone 40 / mossy_cobble 30 / stone 20 / stone_bricks 10

## 2. 深浅分层(vertical banding)

- **基座深、上部浅**:底部 1-2 层换更重更深的料(cobble/mossy_cobble/deepslate),
  既给建筑"体重",又天然是防溅带。
- 风化从地面爬上来:gradient=true 时辅材(尤其 mossy/cracked)占比向基座递增,
  顶部接近纯主材。社区配方同一逻辑(基座带 mossy 30% → 中段 20% → 上段 10%)。
- 反例:顶重脚轻(上部深色基座浅色)视觉必塌,禁止。

## 3. 壁柱 / 线脚分格(pilasters & string courses)

- 竖向:每 3-4 格一根通高壁柱(原木=木骨架,stone_bricks=古典),墙面立刻有了"开间"。
- 横向:楼层交界处一条线脚/横梁(整行替换;log 梁的 axis 由脚本沿墙推导)。
  木骨架风的骨架 = pilaster_every 3-4 + course_rows 楼层线 + plaster 填充。
- 分格后每格 2-3 格宽最舒服;间距 ≤2 成栅栏,≥6 没效果。

## 4. 藤蔓 / 苔藓做旧(aging)

- 藤蔓:每列 5-15% 概率垂一条 1-3 格藤(民居);废墟 25-40%;现代 0%。
  只挂外立面,从上往下垂,别从地上长。
- 苔藓用材质而非植物:mossy_cobblestone / mossy_stone_bricks 靠 gradient 集中在基座,
  比撒 moss_carpet 自然。
- cracked_* 系列是"年久失修"的最短路径:废墟把它提到 30-45%。

## 禁忌速查

- 单色满铺 >3×3 = 不及格;辅材 >3 种或占比 >45% = 杂色糊墙。
- 手动摆棋盘格/竖条纹 ≠ 掺比(掺比是加权随机分布)。
- 门窗洞口不归本卡:先发墙,再用 window_trim / arch_window 切。
- 改 seed 换分布;同参数同 seed 输出恒定(可复现)。
