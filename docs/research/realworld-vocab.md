# 现实建筑传统范式细节词汇表(realworld-vocab)

> 用途:给细节层生成器(L2 模式卡/L3 profile/L4 肌理)提供"现实规则书"弹药。按 **传统 × 构件** 组织,每条样式给出:名称 / 比例模数 / 视觉特征 / 独有手法 / **MC 翻译建议** / 来源 URL。
> 调研日期:2026-08-06。来源以 Wikipedia、公版古典文献(Vitruvius、《营造法式》)、机构档案为主;查不到精确数字的标"通行说法"。

## 0. 换算约定与 MC 手法工具箱

**尺度约定**:1 格 = 1 m。现实模数换算到 MC 时按"格数锚点"取整:

- 层高 3-4 格(民居)/ 5-8 格(纪念性);柱高 = 层高 -1(留出檐部层)。
- 现实比例 < 0.5 格 → 省略或改用贴面(活板门/按钮)暗示;0.5-1.5 格 → 1 格;逐层出挑类(斗拱、jetty)每层固定 1 格。
- 细节层目标是**轮廓与节奏正确**,不是考古复原。每条 MC 建议给出"最小体量版"和(必要时)"大体量版"。

**MC 手法工具箱**(全文档复用,方块 id 以 `aibuild-mod/.../defaults/blocks.md` 为准):

| 现实构件 | MC 等价物 |
| --- | --- |
| 线脚/挑檐/托臂/牛腿 | 楼梯倒放(`*_stairs` upside-down),逐级出挑 1 格 |
| 腰线/窗台/出挑层 | 半砖(`*_slab`)整排 |
| 棂格/百叶/护板贴面 | 活板门(`*_trapdoor`)贴墙,不占体积 |
| 竖棂/小柱/栏杆 | 栅栏(`*_fence`)/ 铁栏杆(`iron_bars`)/ 墙(`*_wall`) |
| 窗面 | 玻璃板(`glass_pane` / `*_stained_glass_pane`) |
| 门钉/铆钉 | 按钮(`*_button`)阵列 |
| 尖顶饰/宝顶 | 墙块叠高 + 楼梯收尖 + `end_rod` 顶珠 |
| 屋面 45° 坡 | 楼梯逐排退 1 格;>45° 用整方块;缓坡(<30°)用半砖每 2 格升 1 |

---

## 一、中世纪欧洲(半木构 / 石砌,11-16c 英德法)

**三大特征一句话**:jetty 逐层悬挑形成"楼层腰线节奏" + 半木构板面划分(密柱/方格/人字纹)是立面唯一纹理来源 + 竖框窗(mullion)直通窗头、上覆挡水眉,是区别于哥特花格窗的世俗标志。

### 1.1 窗型谱系

**① 竖框窗(Mullioned window)**
- 比例模数:2-6 格窗光(lights),单格高宽比约 2:1(通行说法);高配加横档(transom)成十字窗。
- 视觉特征:竖棂空心倒角断面,16c 起标准线脚为 ovolo 卵圆形;洞口上方几乎必加挡水眉(hoodmould)。
- 独有手法:竖棂直通窗头、不做拱心花格——世俗建筑 vs 哥特教堂的分野。
- **MC 翻译**:洞口宽 2-3 格 × 高 2 格;竖棂用 `minecraft:stone_brick_wall`(石宅)或 `minecraft:spruce_fence`(木宅)把洞口隔成 1 格一条,后填 `minecraft:glass_pane`;窗上沿整排正放 `minecraft:stone_brick_stairs` 挑半格作挡水眉,下沿 `minecraft:stone_brick_slab` 窗台。高配:顶部加一排横档玻璃板成"上 1 下 2"十字窗。
- 来源:https://historicengland.org.uk/listing/the-list/list-entry/1184572 ;https://www.wychavon.gov.uk/component/fileman/file/Documents/History%20of%20windows%20and%20glass%20document.pdf

**② 菱形铅条玻璃窗(Diamond-leaded lights)**
- 比例模数:小块玻璃(quarries)以 H 断面铅条拼菱形网,仅开启扇为铁铰 casement;都铎民居最通用。
- 视觉特征:暖黄绿玻璃 + 深铅线菱形密网,是该传统窗户的"指纹"。
- **MC 翻译**:1 格粒度做不出菱形网——用 `minecraft:light_gray_stained_glass_pane` 整面 + 洞口收小(1×2 单格)暗示细密;开启扇贴一扇 `minecraft:spruce_trapdoor`。**禁止**用透明 glass_pane 大洞,那是现代窗。
- 来源:https://www.bronzecasements.com/articles/a-guide-to-traditional-leadlights/

**③ 凸肚窗(Oriel window)**
- 比例模数:半八边形平面悬于上层,宽约占一开间;15-16c 英格兰府邸高频身份构件。
- 视觉特征:由牛腿/托臂承托,配竖框+横档+铅条玻璃;不落地(区别 bay window)。
- **MC 翻译**:上层挑出 1 格、宽 3 高 2;底 2-3 个倒放 `minecraft:spruce_stairs` 作托臂,顶 `minecraft:spruce_stairs` 小披檐;三面贴 `minecraft:light_gray_stained_glass_pane`,转角用 `minecraft:spruce_fence` 收棱。
- 来源:https://www.thoughtco.com/what-is-an-oriel-window-177517

**④ 无玻璃直棂窗(Unglazed mullioned)**
- 比例模数:2-3 棂,菱形断面木棂;普通民居上层,靠内窗板封闭。
- **MC 翻译**:1×2 洞口,`minecraft:spruce_trapdoor` 竖排贴满(关)/留一格开(开);低成本民居默认窗。
- 来源:https://www.british-history.ac.uk/vch/warks/vol3/pp8-22

### 1.2 柱式与支撑(木框架体系,无古典柱式)

**① 开间模数(Bay)+ 瘤头柱(Jowled post)**
- 比例模数:开间 5-16 英尺,常见约 16 英尺(4.9 m),一对主柱+系梁桁架界定;转角柱上部加粗成瘤头。
- **MC 翻译**:开间宽 3-5 格(城镇窄面取 3);主柱 `minecraft:dark_oak_log` 落地整柱,转角柱顶端旁贴 1 格 `minecraft:dark_oak_stairs` 倒放作瘤头加粗。
- 来源:https://padletuploads.blob.core.windows.net/aws/102851167/c45e13315b23b28626a580dbbee7542c/WD_HARRIS_.pdf

**② 悬挑托臂 + 挑眉大梁(Jetty bracket / bressummer)**
- 视觉特征:悬挑层底缘是挑出的楼板搁栅端头,上覆带线脚的挑眉大梁;弧形木托加强。
- **MC 翻译**:上层外墙整体外挑 1 格;挑缘底整排 `minecraft:dark_oak_log`(bressummer),下方每隔 2-3 格倒放 `minecraft:dark_oak_stairs` 作弧形托臂。**这是该传统第一特征,必做**。
- 来源:https://www.designingbuildings.co.uk/wiki/Jetty

**③ 密柱式(Close studding)**
- 比例模数:间柱间距 ≈ 一根柱宽,柱等粗;模拟垂直哥特板面的炫富前脸。
- **MC 翻译**:前脸 `minecraft:dark_oak_log` 竖条每隔 1 格一根,间填 `minecraft:white_concrete`;仅用于"高身份"profile。
- 来源:http://www.lookingatbuildings.org.uk/styles/medieval/walls-and-windows/timber-walls/close-studding.html

**④ 德式斜撑(Andreaskreuz 圣安德鲁十字 / Kopfstrebe 弧形撑)**
- 视觉特征:墙板内 X 形斜撑抗侧移并装饰化;弧形撑连接柱与水平大梁。
- **MC 翻译**:X 形用 `minecraft:dark_oak_stairs` 对角摆进 2×2 板面;弧形撑=柱顶与梁交角处倒放楼梯各 1 格。
- 来源:https://www.tfguild.org/downloads/TF-123-St-Andrews-Cross-Moore.pdf

### 1.3 墙面做法(三段式的本土版)

- **基座段**:矮石勒脚上置木底梁;城镇型(阿尔萨斯/诺曼底)整层石材作底层。MC:1 格高 `minecraft:cobblestone` 勒脚,或首层整层 `minecraft:stone_bricks`。
- **墙身段**:早期大板面,后期小板面(近方格)+ 人字纹(chevron)/菱形/四叶饰(quatrefoil);填充篱笆泥+石灰水,英格兰东南部后改人字砌砖。**纠偏:黑白强对比是维多利亚焦油涂装,都铎原木色/通体石灰水**。MC:默认 `minecraft:stripped_oak_log` 或 `minecraft:oak_log` 浅框 + `minecraft:white_concrete` 填充,"黑白深框"(`dark_oak_log`)作为维多利亚变体 profile;人字纹用楼梯对角贴。
- **檐口段**:挑眉大梁线即水平分带,每层 jetty 一条腰线。MC:见 1.2②。
- 来源:https://frenchmoments.eu/half-timbered-houses-in-alsace/ ;https://godinton.kent.sch.uk/media/3107/year-5-tudor-houses.pdf

### 1.4 门与入口

**① 都铎四心拱门洞(Four-centred/Tudor arch)**
- 比例模数:门洞低窄,高宽比约 2:1(通行说法)。
- 视觉特征:浅四心尖拱 + 倒角门套 + 上覆挡水眉;竖拼板门、铁饰钉、长铰链。
- **MC 翻译**:洞口 1-2 宽 × 2-3 高,顶部两角各 1 个 `minecraft:stone_brick_stairs` 收成浅尖拱;门框用楼梯围一圈作倒角门套;门 `minecraft:dark_oak_door`,旁贴 `minecraft:iron_trapdoor` 作铁件感;上沿半砖挡水眉。
- 来源:https://historicengland.org.uk/listing/the-list/list-entry/1184572

**② 过廊平面入口(Cross-passage)**:门偏心开设,直通横穿过廊。MC:生成器把门位置从明间中轴偏移 1-2 格即可,成本为零、平面立刻"中世纪"。
- 来源:https://cadwpublic-api.azurewebsites.net/reports/listedbuilding/FullReport?id=2057

**③ 山墙门廊(Gabled porch)**:两层、山墙朝街,身份构件。MC:凸出 2 格深 × 2-3 宽,小双坡顶与主屋顶丁字相交。

**④ 德式铭文梁(Spruchbalken)**:门槛大梁刻年份+祈福句。MC:挑眉大梁上挂 `minecraft:oak_sign`(项目列表有 sign 类)——L4 点缀件。
- 来源:https://www.geschichtsverein-prignitz.de/19.pdf

### 1.5 屋檐与屋顶边缘

- **坡度模数**:英格兰实测集中 43/48/52/55/60° 五档;茅草/木瓦 52-55°,平瓦/石板约 48°(RCHME 肯特 110 例)。MC:楼梯 45° 为基准坡;茅草顶用 `minecraft:hay_block` 整方块阶梯(视觉更陡更厚),石板/瓦用 `minecraft:deepslate_tile_stairs` 或 `minecraft:brick_stairs`。
  来源:https://www.medievalbuildings.co.uk/pdfs/Carpenters-Knowledge.pdf
- **檐部惯例**:无檐沟,靠出檐+jetty 甩水;出檐短(约 0.3-0.5 m,通行说法)。MC:屋檐挑出 1 格即收,**禁止**大挑檐(那是中式/日式)。
- **山墙端部**:雕花封檐板(bargeboard),东盎格利亚最盛;石砌区用压顶山墙+尖饰(finial)。MC:山面檐边 `minecraft:spruce_stairs` 沿坡挑出 1 格,脊端垂 `minecraft:spruce_fence` 1-2 格作 finial;石砌变体山墙顶 `minecraft:cobblestone_wall` 压顶。
  来源:https://www.britannica.com/technology/bargeboard
- **端部形态**:茅草顶几乎全硬山,歇山罕见(剑桥郡 559 山墙 : 33 歇山)。MC:默认 gable,hip 设低频变体(权重 ≤10%)。
  来源:https://gala.gre.ac.uk/id/eprint/8753/

### 1.6 生成器落地清单(按出现频率排序)

| 优先级 | 变体 | 落点 |
| --- | --- | --- |
| P0 | jetty 悬挑 1 格 + 挑眉大梁 + 倒放楼梯托臂 | 新模式卡 `jetty` 或 medieval_house 卡 profile |
| P0 | 半木构板面划分(密柱/方格/人字纹 3 档)+ 原木浅框默认 | L4 肌理 + 变体枚举 |
| P0 | 竖框窗 2-3 格 + 挡水眉 + 菱形铅条玻璃板 | 新 `mullioned_window` 模式卡 |
| P1 | oriel 凸肚窗(高配 identity 件) | 模式卡变体 |
| P1 | 都铎浅四心拱门 + 偏心过廊入口 | 门变体 + 平面规则 |
| P2 | bargeboard + finial 山墙收边;茅草 hay_block 顶 | L4 收边件 |

---

## 二、哥特(教堂/尖塔,12-16c)

**三大特征一句话**:尖拱几何族(等边/柳叶/四心)一个参数贯穿门窗拱顶全部构件 + 每开间一道的飞扶壁+压重 pinnacle 是外轮廓基因 + 条形花棂(bar tracery)与玫瑰窗让"玻璃面积大于石材"。

### 2.1 窗型谱系

**① 柳叶窗(Lancet)**
- 比例模数:高宽比 >2:1,盛期达 3:1(通行说法);柳叶尖拱半径 > 窗宽;独占一扶壁间开间,窗宽占开间净宽 1/2-2/3。
- 视觉特征:单窗或三/五连成组;Early English 几乎只用柳叶窗。
- **MC 翻译**:1 格宽 × 3-4 格高,顶部 2 格两侧 `minecraft:stone_brick_stairs` 逐级收成尖(柳叶=每升 2 格内收 1;等边拱=每升 1 格收 1);窗面 `minecraft:iron_bars` 或 `glass_pane`;三连组间隔 1 格。
- 来源:https://www.britannica.com/technology/lancet-window

**② 条形花棂窗(Bar tracery)**
- 比例模数:下部 2-8 根竖棂垂直升起分偶数窗光,至拱头分叉成 Y/三叶/四叶;尖拱多用等边拱(半径=跨距)。
- 独有手法:plate tracery(石板凿孔,石>玻璃)→ bar tracery(玻璃>石)是 13c 哥特独有时间线(兰斯大教堂);英国 Perpendicular 再变直线竖棂+横档。
- **MC 翻译**:3 格宽 × 4-5 高;竖棂两条 `minecraft:iron_bars` 到底,上 1/3 用 `minecraft:stone_brick_wall` + 楼梯摆 Y 分叉;玻璃 `minecraft:light_gray_stained_glass_pane`(盛期)或彩色拼花(高配)。
- 来源:https://www.britannica.com/topic/bar-tracery

**③ 玫瑰窗(Rose window)**
- 比例模数:直径 ≈ 中殿净宽——沙特尔 13.36 m(殿宽 16.4 m)、巴黎圣母院南北 13.1 m;坐于底层连拱廊之上,撑满两塔间立面。
- 视觉特征:轮辐式石棂自圆心放射,辐间填三/四叶小孔。
- **MC 翻译**:小体量 5×5、大体量 7×7 圆形(整方块摆圆模板);辐条 `minecraft:stone_brick_wall` 8 向放射,格内填彩色 `*_stained_glass_pane`(蓝红为主)。只做西立面/横厅端面。
- 来源:https://www.wga.hu/html_m/zzzarchi/13c/2/1/04f_1204.html

**④ 高侧窗 + Triforium 条带**:三段立面的一部分,每开间一窗;triforium 为窄盲拱廊。MC:triforium 用一排 `minecraft:stone_brick_stairs` 倒放 + `iron_bars` 暗槽表达。
- 来源:https://echonode.blog/2025/11/02/the-hidden-mathematics-of-medieval-cathedrals-how-gothic-architecture-revolutionized-structural-engineering/

### 2.2 柱式与支撑

**① 束柱(Compound pier)**
- 比例模数:沙特尔核心宽 2.41 m、至起拱高 9.4 m,柱高:柱径 ≈ 4:1;核心四周附 4+ 小柱(colonnette),直径约核心 1/8-1/10(通行说法),各续接不同拱肋。
- 独有手法:"一柱对一肋"响应式束柱,视觉垂直不断线——哥特结构表现主义核心。
- **MC 翻译**:核心 `minecraft:stone_bricks` 1×1(大体量 3×3),四面贴 `minecraft:stone_brick_wall` 作附柱,从地面一路到顶不打断。
- 来源:https://paris.cdh.ucla.edu/wp-content/uploads/2019/01/Building-the-nave-piers.pdf

**② 飞扶壁 + 尖顶饰(Flying buttress & pinnacle)**
- 比例模数:每开间一道(盛期法式墩距约 12 m 量级);斜拱自高侧窗顶飞跨侧廊,落外部扶壁墩;墩顶必加压重 pinnacle。
- 独有手法:推力外置成"石骨架",墙体才得以开满窗;pinnacle 装饰与压重功能一体。
- **MC 翻译**(开间 3-4 格):外墩 `minecraft:stone_bricks` 1×2 凸出墙 1-2 格,墩顶 `minecraft:stone_brick_wall` 叠 2 格 + 楼梯收尖 + `minecraft:end_rod` 顶珠;斜拱用 `minecraft:stone_brick_stairs` 从墙顶每进 1 格降 1 格落到墩上。双层飞扶壁=再低一层重复。
- 来源:https://docs.itascacg.com/itasca900/3dec/docproject/source/examples/Buttress.html

### 2.3 墙面做法

- **三段立面(Arcade–Triforium–Clerestory)**:沙特尔配比拱廊:triforium ≈ 5:3,高侧窗:拱廊 ≈ 8:5(通行说法,音程比推导);中殿高宽比沙特尔约 2:1、亚眠 3:1、博韦 3.5:1 为极限。MC:教堂 profile 高度按 宽度×2 起步,三段高按 5:3:(8/5×5)=5:3:8 比例分配…… 落格数:总高 16 格 → 拱廊 5、triforium 3、高侧窗 8。
- **外墙基座与腰线**:每层一道突出腰线(string course)兼滴水;基座抬高 1-2 m 随墩外凸;墙面本质是"柱+窗"骨架,实墙退成填充。MC:腰线 `minecraft:stone_brick_slab` 整排挑半格,扶壁墩与内部束柱对位,每开间一个。
- 来源:https://libsysdigi.library.uiuc.edu/OCA/Books2009-11/5631512/5631512.pdf

### 2.4 门与入口

**西向门廊群(Portal ensemble)**
- 比例模数:门洞高宽比约 2:1(通行说法);门框 3-6 层向内递退叠涩线脚(receding orders),每层拱眉刻雕像;上方半月楣(tympanum)→ 层层拱眉 → 尖山花罩顶。
- 视觉特征:门柱立整排雕像柱,双扇门间立中柱(trumeau)。
- **MC 翻译**:洞口 2 宽 × 4 高;门框 2-3 层递退,每层内收 1 格、`minecraft:stone_brick_stairs` 围边;tympanum 区填 `minecraft:chiseled_stone_bricks`(雕刻感);中柱 `minecraft:stone_brick_wall` 1 根;门前 3 级 `minecraft:stone_brick_stairs` 浅台阶;门洞深凹 1-2 格形成遮光龛,**不做**独立雨棚。
- 来源:https://friendsofchartres.org/the-cathedral/art-architecture-history/art/sculptures/

### 2.5 屋檐与屋顶边缘

- **无挑檐:女儿墙 + 滴水兽**:哥特主动消灭挑檐;檐口透空石栏,栏下每隔 1-2 m 伸滴水兽抛雨;屋顶坡度约 55-60°(通行说法)。MC:檐口**零出挑**,`minecraft:stone_brick_wall` 女儿墙一圈(隔格镂空),每 2 格倒放 `minecraft:stone_brick_stairs` 挑 1 格作 gargoyle;坡度楼梯 45° 起步,高塔可整方块更陡。
  来源:https://www.ajhw.co.uk/books/book275/book275.html
- **尖塔三件套(broach / crocket / finial)**:方塔→八角尖顶由三角翼(broach)过渡;棱线等距缀卷叶(crocket);顶收 finial。尖塔高:塔身 ≈ 1:1(通行说法)。MC:broach=四角楼梯逐级内收过渡;crocket=棱线每 1-2 格凸 1 个 `minecraft:stone_brick_stairs`;finial=`stone_brick_wall` 尖 + `end_rod`。
  来源:https://buffaloah.com/a/virtual/fr/char/w/w.html

### 2.6 生成器落地清单

| 优先级 | 变体 | 落点 |
| --- | --- | --- |
| P0 | 尖拱参数族(等边=每升 1 收 1 / 柳叶=每升 2-3 收 1 / 四心=两段变率) | 几何库函数,门窗拱共用 |
| P0 | 飞扶壁+pinnacle 每开间一道 | 新 `flying_buttress` 模式卡(现有 buttress 卡加 variant) |
| P0 | 柳叶窗/条形花棂窗 | 新 `gothic_window` 模式卡 |
| P1 | 玫瑰窗 5×5/7×7 模板(仅教堂 profile) | 模式卡 |
| P1 | 递退门套 + trumeau + 深凹门洞 | 门变体 |
| P2 | 束柱四面贴 wall;女儿墙+gargoyle 零挑檐檐口 | L4 收边 |

---

## 三、中式(宫殿/合院/寺庙,《营造法式》与清《工程做法》体系)

**三大特征一句话**:材分/斗口两套模数统治全部尺寸(斗拱层=中式"柱头",唐宋斗拱高达柱高 1/3-1/2) + 出檐=柱高 3/10 叠加上生起、侧脚、反宇曲线四个简单规则即得"飞檐" + 开间满装隔扇/槛窗/支摘窗(上 6 下 4 六四分),"墙倒屋不塌"的可拆装墙。

**总纲模数**(一切比例的地基):
- 宋式材分制:1 材 = 15 份,断面高:宽 = 3:2;1 栔 = 6 份,1 足材 = 21 份;材分八等,一等广 9 寸用于 9-11 间大殿。来源:https://baike.baidu.com/item/材契/4398435
- 清式斗口制:坐斗开口宽为模数,分十一等;大式建筑全部尺寸以斗口倍数核算。来源:https://www.jgcm.ac.cn/jah/cn/article/pdf/preview/10.12329/20969368.2025.03015.pdf

### 3.1 窗型谱系

**① 支摘窗(和合窗)**
- 比例模数:每开间分上、下、左、右 4 扇,间柱居中;上扇外支、下扇可摘。棂格定型:步步锦、灯笼锦、龟背锦、冰裂纹、万字不到头。
- 地位:北京四合院与次要宫殿标配。
- **MC 翻译**:开间 3-4 格宽:上 2 格装窗——`minecraft:white_stained_glass_pane`(纸窗感)或 `glass_pane`,表面竖贴 `minecraft:dark_oak_trapdoor` 作棂格(步步锦=每格一扇);下 1 格槛墙 `minecraft:bricks`(民居)或 `minecraft:stone_bricks`。上扇可"支起"变体:最上一格贴斜放活板门。
- 来源:https://www.sohu.com/a/404904437_99935361

**② 槛窗**
- 比例模数:隔扇去掉裙板以下部分、安于槛墙之上;槛墙高 = 裙板高;与相邻隔扇门统一构图,用于郑重厅堂。
- **MC 翻译**:槛墙 1-2 格 + 上窗 2 格,窗宽与旁边隔扇门同(1 格/扇),保持竖向对位。
- 来源:https://www.sohu.com/a/332917021_617491

**③ 隔扇/落地明造**
- 比例模数:**六四分**——全高 10 份,格心上 6、裙板绦环下 4;单扇宽:高 ≈ 1:3-1:4,明间装 4/6/8 扇(偶数)。
- **MC 翻译**:扇宽 1 格 × 高 3-4 格:上 2 格(占 6/10)`glass_pane` + `dark_oak_trapdoor` 棂格,下 1-1.5 格(4/10)`minecraft:dark_oak_planks` 裙板 + `minecraft:spruce_trapdoor` 贴绦环板。
- 来源:https://www.pgm.org.cn/pgm/xsyjou/201507/c4cd52e8cacf4c8ea9fdeb65e1a42d42.shtml

**④ 直棂/破子棂窗**
- 唐宋以前主流,后归次要建筑;破子棂三角断面便于糊纸。与欧洲 tracery、日式格子区分度最高的"早期中式"窗。
- **MC 翻译**:`minecraft:dark_oak_fence` 竖排塞满 2 格高洞口,背后衬 `minecraft:white_stained_glass_pane`(糊纸)。用于库房/寺庙配殿。
- 来源:http://mp.weixin.qq.com/s?__biz=MzI4NTU0NDcxOQ==&mid=2247487473&idx=1&sn=dca4b73555c59e02ca1f8154212e3fde

### 3.2 柱式与支撑

**① 檐柱通则**
- 比例模数:清式无斗拱建筑柱高 = 明间面阔 8/10,柱径 = 面阔 7/100 → 高径比约 11:1;宋式"柱高不越间之广"。开间递减:明 > 次 > 梢 > 尽(清式按斗拱空当 7/6/5 攒递减)。
- **MC 翻译**:柱 `minecraft:stripped_mangrove_log`(红)或 `minecraft:stripped_spruce_log`(素木)1×1,高 6-8 格;开间宽:明 5 格、次 4、梢 3——生成器按等差收缩平面即可出"递减韵律"。
- 来源:https://www.jgcm.ac.cn/jah/cn/article/pdf/preview/10.12329/20969368.2025.03014.pdf

**② 侧脚 / 生起 / 收分(稳定性三件套)**
- 侧脚:正面每尺侧 1 分(柱高 1%),角柱双向;生起:檐柱自当心间向角柱逐间升 2 寸,檐口成缓和曲线;收分:柱身上 1/3 卷杀成梭形,清式约柱高 7‰。
- **MC 翻译**:1 格粒度下侧脚/收分忽略;**生起必做**——两端角柱/檐口各抬高 1 格,檐口线立刻出"两端上翘"的中式微笑曲线。
- 来源:https://www.shidianguji.com/book/SK1192/chapter/1l9lamw1slf6u

**③ 斗拱(铺作)= 中式柱头**
- 比例模数:出一跳为四铺作,每加一跳增一铺(至八铺作);每跳跳深不过 30 份;唐宋斗拱高可达柱高 1/3-1/2(佛光寺东大殿 ≈1/2),明清缩为装饰、攒档加密(清明间平身科 6-8 攒)。
- **MC 翻译**:柱头科=柱顶 `minecraft:mangrove_stairs` 倒放向外出挑 1 格 + 上叠 `minecraft:mangrove_slab`;每加一跳再外挑 1 格倒楼梯(大殿 2-3 跳=挑 2-3 格);补间科每开间 2-3 攒(即柱间等距重复同样小组件);转角科 45° 斜放楼梯。唐宋 profile:斗拱层总高 2-3 格;明清 profile:1 格简化。
- 来源:https://www.dpm.org.cn/Uploads/File/pdf/87/91/30/8791304e050abc22490357cb418682b7.pdf

**④ 雀替(牛腿等价物)**
- 比例模数:清官式长 = 净面阔 1/4,高同檐枋,厚 = 柱径 3/10。
- **MC 翻译**:柱顶与额枋交角处,两侧各贴 1 格倒放 `minecraft:mangrove_stairs`;高配加 `minecraft:dark_oak_trapdoor` 贴面作雕板。
- 来源:https://baike.baidu.com/item/雀替/6531732

### 3.3 墙面做法(台明—墙身—檐口)

- **台明(下段)**:小式台明高 = 柱高 1/5;台明出沿 = 上檐出 4/5,上下出之差"回水"护柱根。MC:柱高 6 → 台明 1 格:`minecraft:stone_bricks` 一圈 + `minecraft:smooth_stone_slab` 压顶,外沿比柱网宽出 1 格。
  来源:https://m.fbs.qq.com/read/1048818797/37
- **须弥座(高等级)**:总高约柱高 1/4-1/5,六段定型:圭角→下枋→下枭→束腰→上枭→上枋。MC:3 格版——底层 `stone_brick_stairs` 倒放(涩)、中层 `stone_bricks` 束腰(视觉内收:缩进不可行时用 `stone_brick_wall` 栏出束腰感)、顶层楼梯正放 + 半砖;太和殿级三层相叠仅大殿 profile 用。
  来源:https://www.dpm.org.cn/Uploads/File/2023/02/15/u63ec3cb1a5b6d.pdf
- **墙身(中段)**:"墙倒屋不塌"——墙不承重,前檐满装隔扇/槛窗,仅后檐与山面砖墙。MC:正面全开口装门窗体系(3.1),后墙 `minecraft:bricks`/`minecraft:gray_concrete` 实墙。
- **檐口(上段)**:阑额+普拍枋+斗拱层+挑檐檩构成水平檐部带,斗拱攒档即檐部节奏。MC:`minecraft:mangrove_log` 横枋一圈,上承斗拱层(3.2③)。

### 3.4 门与入口

**① 实榻大门 + 门钉等级**
- 比例模数:门钉皇宫九行九列 81、亲王 63、郡王 49——数字即等级编码;辅铺首、门簪 2-4 枚。
- **MC 翻译**:门洞 2-3 宽 × 3 高,门扇 `minecraft:dark_oak_planks` 或 `minecraft:mangrove_planks`;门钉 `minecraft:polished_blackstone_button` 按 3×3(庶民府邸)/5×5(高配)阵列贴门扇;铺首=门中央 1 格 `minecraft:bell`? 不——用 `minecraft:item_frame`? 实体慎用,改用一对 `minecraft:iron_trapdoor` 下角。
- 来源:https://www.dpm.org.cn/Uploads/pdf/1927/T00094_00.pdf

**② 抱厦/龟头屋(中式门廊)**
- 主体前凸出 1 或 3 间附属小殿,自有歇山/卷棚顶,与主体丁字/十字相交(摩尼殿四面出抱厦)。中式入口强调最强手法:不用门套,用"凸出一整个小屋顶"。
- **MC 翻译**:入口前凸 2 格深 × 3 格宽小体量,屋顶与主顶垂直相交;卷棚顶=顶部 2 格用半砖平收不起脊。
- 来源:https://baike.baidu.com/item/抱厦/2000247

**③ 踏跺**:垂带踏跺/如意踏跺;高等级中央御路。MC:台明前 `minecraft:stone_brick_stairs` 整宽 2-3 格;御路变体=中央 1 格换成 `minecraft:chiseled_stone_bricks`。

### 3.5 屋檐与屋顶边缘

- **出檐深度**:清小式上檐出 = 檐柱高 3/10,三分之(檐椽 2/3 + 飞椽 1/3);唐佛光寺东大殿出檐 3.96 m ≈ 檐口到柱底高度之半。MC:柱高 6 → 挑出 2 格(唐宋 profile 挑 3 格);双层表达:下层 `minecraft:dark_oak_slab` 一排(椽)、上层屋面楼梯再探 1 格(飞椽)。
  来源:https://max.book118.com/html/2023/0914/8125053010005132.shtm
- **檐口收边**:勾头(瓦当)、滴水收檐头;翼角老角梁+仔角梁起翘(南方发戗更陡),仔角梁头套兽。MC:檐口第一排瓦用 `minecraft:deepslate_tile_slab` 收边;翼角=转角处屋面楼梯抬高 1 格并斜放,端头 1 格 `minecraft:dark_oak_stairs` 倒卷作套兽。瓦材:民居青瓦 `deepslate_tile_stairs`,宫殿黄琉璃 `minecraft:yellow_terracotta` 阶梯体(无 stairs,用整方块退台)。
- **脊饰等级**:正脊两端鸱吻(明清吻兽+剑把);垂兽/戗兽;走兽序列 3/5/7/9 取单数。MC:正脊=`minecraft:deepslate_tile_wall` 一排;鸱吻=脊两端 `minecraft:deepslate_tile_stairs` 向内倒卷 1-2 格高;走兽=戗脊前端隔 1 格摆 1-3 个 `minecraft:stone_button`? 不——用 `minecraft:end_rod` 竖放或 `dead_bush`? 项目列表内最像蹲兽的小件是 `minecraft:bell`/`minecraft:flower_pot`,建议走兽用 1-3 个 `minecraft:gray_concrete`? 太小。落地方案:走兽仅大殿 profile 用 `minecraft:polished_blackstone_wall` 点 3 处。
  来源:https://www.dpm.org.cn/lemmas/241413.html
- **悬山端部**:檩挑出山墙成"出际";檩头封博风板,合尖垂**悬鱼**、两侧排**惹草**。MC:屋面挑出 1 格过山墙;博风板=`minecraft:dark_oak_stairs` 沿山面坡边贴一圈;悬鱼=合尖处下挂 `minecraft:dark_oak_trapdoor` 竖板 1-2 格。
  来源:https://baike.baidu.com/item/博风板/2553269
- **歇山收山**:自山面檐檩向内收一檩径定山花板,形成三角山花+博缝。MC:上层屋顶两端的下半坡用墙面封 1 格,形成悬山+四坡复合;山花面 `minecraft:white_concrete` + 博缝 `dark_oak_stairs` 勾边。
- **庑殿推山**:加长正脊使垂脊平面投影成曲线。MC:1 格粒度近似——四坡顶的脊线两端各延长 1 格再落坡,垂脊走折线而非直线。

### 3.6 生成器落地清单

| 优先级 | 变体 | 落点 |
| --- | --- | --- |
| P0 | 出檐 2 格双层(椽+飞椽)+ 生起(角柱 +1)+ 翼角起翘 | `chinese_eave` 模式卡,屋顶卡加参数 |
| P0 | 开间满装隔扇/槛窗/支摘窗体系(六四分、明间偶数扇) | `chinese_window` 模式卡 |
| P0 | 台明 1 格(柱高 1/5)+ 大殿须弥座 3 格变体 | 基座规则入风格卡 proportions |
| P1 | 斗拱层(柱头/补间/转角三科,跳数参数) | 新 `dougong` 模式卡(先 1 跳简化版) |
| P1 | 门钉按钮阵列(3×3/5×5 两档等级) | 门变体 |
| P2 | 悬鱼博风板、鸱吻、抱厦、直棂窗 | L4 收边件 / 高配 profile |

---

## 四、日式(町屋/城郭/神社寺院,镰仓—江户)

**三大特征一句话**:破风双璧(千鸟三角 + 唐破风 S 曲)作为纯贴面装饰跨城郭寺社全域出现 + 町屋格子(koshi)以棂条粗细编码行业的竖棂立面配虫笼窗二层 + 深出檐+二重垂木(平行/扇形两派)是所有子传统共有的檐下结构层。

### 4.1 窗型谱系

**① 格子窓(kōshi,京町家)**
- 比例模数:覆盖整间临街开间(1 间 ken ≈ 1.82 m)的竖条木格;条间距约 5-10 cm(通行说法),按行业分粗细:糸屋格子(细密、上部不到顶采光)/ 酒屋・米屋格子(粗壮)/ 下家格子(最细)。
- 独有手法:**棂条粗细编码店主职业**,立面即行业名片。
- **MC 翻译**:临街面 3-5 格宽 × 2-3 高,`minecraft:dark_oak_trapdoor` 每格竖贴一扇成密棂(细格子),或 `minecraft:dark_oak_fence` 隔 1 格一根(粗格子);糸屋变体最上 1 格留 `minecraft:white_concrete` 不贴。
- 来源:https://www.nippon.com/en/guide-to-japan/gu900011/

**② 虫笼窗(mushiko-mado)**
- 模数:二层"厨子二阶"(层高极低)土壁上小型固定窗,近方或略横长;竖棂整体抹土灰浆半埋,京都大火后防火规范产物。
- **MC 翻译**:二层 1×1 或 2×1 小洞,`minecraft:iron_bars` 嵌在 `minecraft:white_concrete` 墙内(棂半埋感);二层高压到 2 格。
- 来源:https://www.japanesewiki.com/building/Kyo-machiya.html

**③ 火灯窗(katō-mado 花頭窓)**
- 模数:禅宗样定型,上部火焰/花瓣形 S 双曲、下部矩形;禅寺佛殿与城郭天守(彦根城二三层全用)。
- **MC 翻译**:2-3 格宽:顶行中央凸 1 格、两翼 `minecraft:stone_brick_stairs` 下卷摆 S 形;窗面 `glass_pane` + `iron_bars`;框用 `white_concrete` 勾边。
- 来源:https://madoken.jp/en/series/15660/

**④ 连子窗(renji-mado)**
- 和样寺院定型,满开间细竖条板窗,条宽≈条距(通行说法);实心板条呈"木条幕墙"。
- **MC 翻译**:`minecraft:spruce_trapdoor` 整面竖贴,或 `spruce_fence` 满排;变体蔀戸(shitomi-dō)上下对开=上半贴活板门翻起位。
- 来源:JAANUS renjimado(aisf.or.jp)

### 4.2 柱式与支撑

**① 木割(kiwari)体系 vs 数寄屋反木割**
- 以柱径与柱间距为基本模数推全部尺寸,功能等同中式材分;书院造有木割,数寄屋造故意不用(桂离宫)。**对生成器:书院造 profile 严格柱距网格,数寄屋 profile 允许 ±1 格破网**——这是日式独有的"反模数"设计轴。
- 来源:https://accscience.com/journal/JCAU/2/1/10.36922/jcau.v2i1.259

**② 间(ken)柱网**
- 1 间 = 柱中至柱中,标准 6 尺 = 1.818 m;榻榻米 6×3 尺随之。
- **MC 翻译**:开间模数 2 格(小体量)/ 3 格(标准),平面按 ken 的整数倍扩张。
- 来源:https://infoscience.epfl.ch/server/api/core/bitstreams/85eaa33f-4580-4dd6-8486-4efad5d0f178/content

**③ 角柱(kakubashira)/ 圆柱收分 / 掘立柱**
- 书院造定型方柱带面取棱线;寺院圆柱有 entasis(法隆寺最早);神社民家古制柱直接埋地无柱础。
- **MC 翻译**:方柱 `minecraft:stripped_spruce_log`;神社/民家 profile 柱底**不放**柱础石块(与中式台明、西式建筑基座区分);圆柱感用 `spruce_log` 不剥皮。

**④ 贯(nuki)+ 出跳斗栱(大佛样)**
- 大佛样以穿柱横贯联结整排柱、斗栱直接插柱身;与和样"柱上置斗"不同。三样式(和样/大佛样/禅宗样)是柱头变体轴。
- **MC 翻译**:大佛样 profile:柱身中部横穿 `minecraft:spruce_log`(贯,凸出柱面半格感用楼梯),斗拱同中式 3.2③ 但只用柱头科、不做补间科;和样 profile 反之。
- 来源:https://www.woodworkersuk.co.uk/books/use-of-wood-in-japan-s-tuke-1895.pdf

### 4.3 墙面做法

**① 城郭三段式:石垣基座 + 白壁墙身 + 破风檐口**
- 比例:姬路城石垣 15 m : 天守本体 31.5 m ≈ **基座:墙身 = 1:2**;石垣变曲率剖面:底部约 30° 起坡、向天端渐陡至 75°("扇の勾配"/武者返し),实测均值 66.6°。
- **MC 翻译**:基座高 = 本体 1/2;坡面:底部 2 格直起,以上每升 2 格内收 1 格(变曲率折线近似);材料 `minecraft:andesite` + `cobblestone` + `stone` 掺混,缝隙用 `cobblestone_wall` 嵌点。
- 来源:https://atcuk.org/wp-content/uploads/2025/07/Himeji-Castle-1.pdf ;https://web-japan.org/nipponia/nipponia17/en/feature/feature03.html

**② 白壁 × 黒下见板水平分带**
- 天守各层白漆喰墙与黑色雨板交替分带(松本城"白上黑下");土藏用海鼠壁(namako-kabe,黑底凸灰网格)。
- **MC 翻译**:墙身 `minecraft:white_concrete`,底部 1-2 格 `minecraft:dark_oak_planks` 护板带;海鼠壁变体:`minecraft:black_concrete` 底 + `light_gray_concrete` 每隔 1 格十字凸点。
- 来源:https://samurai-archives.com/wiki/Matsumoto_castle

**③ 町屋三段式:犬矢来护脚 + 格子墙身 + 深檐**
- 犬矢来:约 60 cm 高弧形凹面密排竹片护脚(防泥防犬尿);墙身一层全木格子/蔀戸,二层土壁抹灰压低。
- **MC 翻译**:护脚 1 格高 `minecraft:scaffolding`(竹感)或 `bamboo_mosaic` 贴墙脚,弧形用 2 格折线近似;一层格子(4.1①),二层 `white_concrete` + 虫笼窗。
- 来源:https://www.aisf.or.jp/~jaanus/deta/i/inuyarai.htm

### 4.4 门与入口

**① 町屋全开"みせの間"**:白天卸下蔀戸整个开间对街敞开;入口旁设駒寄せ硬木矮栏,斧痕饰面。MC:一层临街整面可留空 2-3 格作"开店"变体,口部一排 `minecraft:spruce_fence` 矮栏(駒寄せ)。
- 来源:https://www.nippon.com/en/guide-to-japan/gu900011/

**② 城门:高丽门/薬医门(yakuimon)**
- 门带独立屋顶(切妻或入母屋),门柱+控柱四柱落地,屋顶占门楼总高约 1/3(通行说法);门扇以铁带横箍无门钉。
- **MC 翻译**:4 柱(2×2)门楼,柱高 2-3 格,上覆小屋顶 1-2 格高;门扇 `dark_oak_trapdoor` 贴面 + 横排 `minecraft:iron_bars` 作铁带。
- 来源:https://followingtheshogun.com/2025/06/08/himeji-castle-5-moats-walls/

**③ 神社入口方位:平入 vs 妻入**
- 神明造本殿入口开长边(平入),大社造开山面(妻入)——入口方位即样式判定轴;神明造高架离地(高床式)前设木台阶。
- **MC 翻译**:神社 profile 加 `entry_side` 参数(long/gable);高床=整体抬 1-2 格 `spruce_planks` 平台 + `spruce_stairs` 台阶。
- 来源:https://www.aisf.or.jp/~jaanus/deta/s/shinmeizukuri.htm

**④ 檐下通道"犬走り"**:町屋深檐下留出的沿街通行空间——入口与街的关系由檐而非门廊定义。MC:檐挑 2 格 + 其下不置墙,即天然犬走り。

### 4.5 屋檐与屋顶边缘

**① 深檐与二重垂木(futa-noki)**
- 和样塔檐自柱心出挑约 4.3 m,屋面坡度 6/12,双层垂木悬挑;垂木两派:和样平行垂木 / 禅宗样扇垂木(转角放射状)。
- **MC 翻译**:出挑 2-3 格;檐下第一层 `minecraft:spruce_slab` 密排(垂木),第二层 `spruce_stairs` 45° 坡;禅宗样 profile 转角处楼梯改斜 45° 摆作扇形放射。瓦顶 `minecraft:deepslate_tile_stairs`(寺院)/ `spruce_stairs`(町屋杪板)。
- 来源:https://nara-media.s3.amazonaws.com/electronic-records/rg-079/NPS_HI/04000020.pdf

**② 廂(hisashi)1 间深檐廊**
- 母屋外环一圈 1 间(≈1.82 m)深 hisashi,可再扩孫廂——"母屋+廂"同心扩张是书院造平面生成规则。
- **MC 翻译**:主体外墙外扩 2 格一圈廊(柱廊+半高下檐),平面生成规则直接可编码。
- 来源:https://www.aisf.or.jp/~jaanus/deta/s/shoinzukuri.htm

**③ 破风双璧:千鸟破风 + 唐破风**
- 千鸟破风:贴在屋面上的三角形装饰破风,强凹曲线、无窗纯装饰;唐破风:正脊中央下凹两端上翘的 S 双曲;城郭把千鸟/唐/切妻/入母屋密集混装同一天守各面。
- **MC 翻译**:千鸟=屋面中段贴 3 宽 2 高三角:`dark_oak_stairs` 摆两斜边 + 内填 `white_concrete`,底边半砖;唐破风=3-5 宽,脊线中央降 1 格、两端楼梯上翘 1 格成 S 曲线。混装密度做成 profile 参数(城郭高密度、町屋零破风)。
- 来源:https://www.aisf.or.jp/~jaanus/deta/c/chidorihafu.htm

**④ 神社脊饰:千木(chigi)× 鲣木(katsuogi)**
- 千木:两端屋脊交叉出脊的 X 形叉木,切口方向编码神格;鲣木:压脊圆木短柱,数量定型(伊势内宫 10 根);神明造坡度 ≤45°。
- **MC 翻译**:千木=脊两端 `minecraft:dark_oak_fence` 两根交叉伸出 1 格(X);鲣木=脊上每隔 1-2 格横放 `minecraft:dark_oak_log` 1 格。**成本极低、辨识度极高**。
- 来源:https://www.aisf.or.jp/~jaanus/deta/y/yuitsushinmeizukuri.htm

**⑤ 町屋一文字直檐 + 钟馗瓦像**:檐口边缘绝对直线不施装饰;鬼瓦位置换置钟馗陶偶(京都独有)。MC:檐口 `deepslate_tile_slab` 直线收边,默认 profile 不加任何端饰;钟馗=檐口中央 1 格 `minecraft:dark_oak_fence` + 头? 用 `minecraft:carved_pumpkin`? 过重——建议省略或 L4 点缀一个 `minecraft:bell`。

### 4.6 生成器落地清单

| 优先级 | 变体 | 落点 |
| --- | --- | --- |
| P0 | 千鸟/唐破风贴面山花(三角/双曲两 profile + 混装密度) | 新 `hafu` 模式卡 |
| P0 | 町屋格子立面(trapdoor 密棂/fence 粗棂两档)+ 虫笼窗二层 + 犬矢来护脚 | `machiya_facade` 模式卡/风格卡 profile |
| P0 | 深檐 2-3 格 + 二重垂木(slab 密排 + stairs 坡) | 屋顶卡加 `japanese_eave` 参数 |
| P1 | 石垣变曲率基座(1:2、先直后收)+ 白壁黑下见板分带 | 城郭 profile 三段规则 |
| P1 | 千木+鲣木脊饰包(神社) | L4 低成本高辨识件 |
| P2 | 火灯窗 S 曲顶、薬医门四柱门楼、平入/妻入参数 | 窗/门变体 |

---

## 五、地中海 + 沙漠(土坯/拱券/庭院,南欧/北非/中东)

**三大特征一句话**:拱型谱系(半圆→马蹄→尖拱 + 科尔多瓦双层叠拱 + alfiz 矩形外框)全域通用且几何最好参数化 + 庭院+连拱廊是民居到宫殿的通用平面骨架 + 厚墙小窗、平屋顶女儿墙、白抹面的"气候包"一次实现即可产出希腊岛/安达卢西亚/北非三个子变体。

### 5.1 窗型谱系

**① 单孔拱窗(Monofora,罗马式/拜占庭圆拱窗)**
- 比例模数:高宽比约 2:1-2.5:1,窄高;墙面斜切大八字内倾(splayed reveal)引光;墙厚 40 cm 以上,窗洞占墙面比例很小。
- **MC 翻译**:洞口 1 宽 × 2-3 高,顶两 `minecraft:smooth_sandstone_stairs` 左右对收成半圆;厚墙感=窗洞内侧面用倒放楼梯斜切 1 格(splay);墙身整体做 2 格厚(双层)。
- 来源:https://medievalheritage.eu/en/main-page/dictionary/bifora/

**② 双联窗(Bifora / 西语 Ajimez)**
- 比例模数:一洞内一根小柱分两个圆拱或马蹄拱,外罩更大半圆拱或卸荷平拱;三连为 trifora;外框高宽比约 1:1-1.2:1。经穆德哈尔传入西班牙。
- **MC 翻译**:2-3 宽 × 2-3 高;中央 `minecraft:stone_brick_wall` 小柱,两拱各用楼梯收顶;外罩一圈 `minecraft:smooth_sandstone_stairs` 大拱;伊斯兰变体外套矩形 alfiz 框(见 5.4②)。
- 来源:https://www.npao.ni.ac.rs/files/2619/2_19._EDA_2019_9_Dib_Krstic_Naffah_c8ae6.pdf

**③ 戴克里先窗(Diocletian / thermal window)**
- 比例模数:大直径半圆窗被两根竖棂分三格,高:宽 ≈ 1:2;源于罗马浴场,Serlio 列为定型。
- **MC 翻译**:3 宽 × 2 高半圆(楼梯摆弧),两条 `iron_bars` 竖棂;用于浴场/大殿 profile 高侧。

**④ 马什拉比亚(Mashrabiyya)**
- 伊斯兰住宅二层以上外凸木格栅笼窗(oriel),车旋木件几何密格,采光通风遮视线,阿拉伯街区天际线标志。
- **MC 翻译**:二层挑出 1 格、宽 2-3 高 2 的木盒,五面 `minecraft:jungle_trapdoor` 或 `oak_trapdoor` 贴满;底 2-3 个倒放 `spruce_stairs` 托臂;**与中式支摘窗、英式 oriel 并列为"凸窗三族"但贴面最密**。
- 来源:https://www.patternsofcairo.com/narratives/468

**⑤ 沙漠小方窗(土坯墙窗)**
- 近方形小洞,木过梁,下框距地较高;南欧加铁栅 reja;土坯/夯土墙高厚比上限通行 10:1。
- **MC 翻译**:1×1 洞口,窗台距地 3 格;铁栅变体贴 `minecraft:iron_bars`;墙 `minecraft:mud_bricks`(土坯)或 `minecraft:packed_mud`/`smooth_sandstone`(夯土)。
- 来源:https://www.greenhomebuilding.com/QandA/adobe/structural.htm

### 5.2 柱式与支撑

**① 古典柱式(希腊-罗马体系)**
- 比例模数:以柱径 D 为模数——多立克柱高 7D(早期 6D)、爱奥尼 9D、科林斯 10D,柱身 entasis 微凸;Vitruvius 最优柱式 eustyle 柱间距 2¼D。
- **MC 翻译**(D=1 格):柱身 `minecraft:quartz_pillar`(竖纹即凹槽)或 `smooth_sandstone`;多立克高 7,柱头 `smooth_stone_slab` + 正放楼梯一层(朴素);爱奥尼高 9,柱头两侧各 1 个倒放楼梯作涡卷;科林斯高 10,柱头倒放楼梯 + `minecraft:azalea_leaves` 点缀(叶饰);柱距净 2-3 格。
- 来源:https://www.classicist.org/articles/classical-comments-eustyle/ ;https://www.mdpi.com/2075-5309/15/17/3147

**② 拱柱连廊(罗马式发明)**
- 半圆拱架柱上、拱顶承檐部;罗马巴西利卡柱距约 2.87-3.62 D(实测);半圆拱矢高 = 跨度/2(180° 包容角是罗马经验法则)。
- **MC 翻译**:柱 1×1 高 3-5 格,柱间 2-3 格;拱 `minecraft:stone_brick_stairs` 从两柱头向心收(净跨 3 = 每侧各进 1 格);拱上 `*_slab` 檐部线脚一圈。
- 来源:http://engineeringrome.org/basilica-of-maxentius/

**③ 双层叠拱(科尔多瓦大清真寺,独有)**
- 短罗马柱抬高净高:下层马蹄拱上再叠半圆拱,柱头加超大垫块;马蹄拱包容角约 200°(超过半圆约 1/9-1/5,通行说法)。
- **MC 翻译**:下层马蹄拱=两侧楼梯先竖直下挂 1 格再内收(超半圆感),拱石红白相间(ablaq)= `minecraft:white_concrete` 与 `minecraft:red_terracotta` 交替摆;上层半圆拱同②;柱头垫块=1 格 `chiseled_stone_bricks`。
- 来源:https://westwards.de/2022/04/the-great-mosque-of-cordoba/

**④ 凉廊开间(Loggia bay / Serliana)**
- 开间近方或 1:1½-1¾(Palladio 房比例);Serliana=中央圆拱+两侧平楣小三开间,吸收不等跨。
- **MC 翻译**:顶层或立面一段做 3-5 开间连拱廊(柱+半圆拱,栏 `stone_brick_wall` 半高);Serliana=中拱两侧各 1 格平楣小洞(半砖压顶)。

**⑤ 出挑木檐托木(canes)/ 阳台牛腿**:安达卢西亚与北非成对木椽托檐;二层挑阳台成排石/木牛腿(通行做法)。MC:檐口下每隔 1 格 `minecraft:dark_oak_stairs` 正放挑 1 格(椽头);阳台底 2-3 个倒放楼梯牛腿。

### 5.3 墙面做法

- **三段版本**:基座=毛石/琢石高勒脚;墙身=大面积素抹灰/夯土实墙;檐口=出挑木檐或砖石叠涩线脚。MC:勒脚 1 格 `cobblestone`/`stone_bricks`,墙身 `white_concrete`(希腊)/ `smooth_sandstone`(南欧)/ `mud_bricks`(土坯),檐口砖叠涩=`brick_stairs` 逐级挑半格×2 层。
  来源:https://www.witpress.com/Secure/elibrary/papers/ARC06/ARC06010FU1.pdf
- **文艺复兴府邸三段(Palazzo Medici/Rucellai 范式)**:首层粗石(rustication)小窗铁栅 → piano nobile 大拱窗 → 顶层渐收;三条通长腰线分划,壁柱按开间等距;檐部 cornicione 大挑檐收头,出挑约立面总高 1/10(通行说法)。MC:首层 `minecraft:tuff_bricks`/`stone_bricks`(粗石感)+ 1×1 铁栅窗;腰线 `smooth_stone_slab` 每 3-4 格一条;壁柱 `quartz_pillar` 凸半格感(贴柱);cornicione=`stone_brick_stairs` 倒放整挑出 1 格。
  来源:https://www.sgira.org/palaces1.htm
- **厚墙小窗气候做法**:土坯/夯土高热容,墙高:厚 ≤10:1,单层 30 cm、两层 45 cm;"极小受控洞口"。MC:墙厚 2 格,窗密度参数压到每开间 ≤1 窗、洞口 ≤1×2。
  来源:https://www.huduser.gov/publications/pdf/southwesthousing/sht_ch3.pdf
- **伊斯兰堡垒墙面**:微收分(battered),顶砌阶梯状或圆头雉堞(merlon)女儿墙带——北非/安达卢西亚独有轮廓(通行说法)。MC:墙脚比墙顶宽 1 格;顶部 `sandstone_wall` 与空隔格交替(方雉堞)或 `sandstone_stairs` 正放(圆头近似)。

### 5.4 门与入口

**① 罗马神庙门洞模数(Vitruvius IV.6,可量化)**
- 门洞高分 12 份、底宽 5½ 份 → **高:宽 = 12:5.5 ≈ 2.18:1**;门洞上宽下窄收分(16 尺以下收 1/3 门梃宽);门楣顶线与廊柱柱头齐平。
- **MC 翻译**:门洞 2 宽 × 4 高(或 3 宽 × 6-7 高);门框 `smooth_sandstone_stairs` 围一圈,门楣 1 格整梁 + 上半砖檐口。
- 来源:https://www.loebclassics.com/view/vitruvius-architecture/1931/pb_LCL251.233.xml

**② Alfiz 门框(伊斯兰/穆德哈尔独有)**
- 马蹄拱门洞外套矩形雕带边框(alfiz),拱石红白相间(ablaq),拱肩填雕饰——把拱"装裱"进矩形,最易程序化识别的特征。
- **MC 翻译**:马蹄拱(5.2③)外圈 1 格宽矩形框,用对比色 `minecraft:red_terracotta`/`chiseled_sandstone`;拱肩两格填 `chiseled_sandstone` 或 `chiseled_stone_bricks`。
- 来源:https://docs.neu.edu.tr/library/7067691886.pdf

**③ 折角入口序列(zaguán / bent entrance)**
- 外街素墙只开一门,经折角门廊转折进庭院保私密;门槛前 1-3 级石阶;宫殿入口为连拱廊掩蔽深门廊(iwan 凹龛)。
- **MC 翻译**:街面只开 1 个 1-2 宽门洞,门后 2 格走廊转折 90° 进院;iwan 变体=立面凹进 2 格深大龛,顶半穹(楼梯收分)。
- 来源:https://archeyes.com/the-courtyards-of-cordoba/

### 5.5 屋檐与屋顶边缘

- **平屋顶 + 女儿墙(主干)**:干热气候默认平顶作露台(azotea);矮女儿墙收头,伊斯兰变体加阶梯雉堞;穹顶以突角拱(squinch)落方室。MC:平顶 `smooth_sandstone_slab` 或 `minecraft:terracotta` 铺面;女儿墙 `sandstone_wall` 一圈;穹顶:4 格方室上每圈内收 1 格(3×3→十字→1),squinch=四角先各倒放楼梯 1 格过渡;材料 `white_concrete`(希腊)/ `terracotta`(南欧)。
  来源:https://www.frontiersin.org/journals/built-environment/articles/10.3389/fbuil.2025.1686776/full
- **大挑木檐 alero(南欧坡屋面变体)**:低坡陶瓦(罗马筒瓦),檐口成对露明木椽挑出,出挑约 1/4-1/3 檐下墙高(通行说法);檐下砖叠涩逐级挑出收边。MC:坡顶 `minecraft:terracotta` 阶梯或 `brick_stairs` 缓坡(半砖每 2 格升 1);檐口挑 1-2 格,下沿每隔 1 格 `dark_oak_stairs` 正放露椽头。
  来源:https://twu-ir.tdl.org/server/api/core/bitstreams/b486ec64-4237-408e-af48-1d915cc3f16b/content
- **cornicione 大檐口(意大利府邸)**:顶部石构大挑檐整栋收头,兼作雨影线。MC:见 5.3 府邸段。

### 5.6 生成器落地清单

| 优先级 | 变体 | 落点 |
| --- | --- | --- |
| P0 | 拱型谱系(半圆=楼梯对收 / 马蹄=先下挂再收 / 尖拱)+ ablaq 红白交替 | 几何库 `arch` 函数,三传统共用 |
| P0 | 庭院+连拱廊骨架(庭院居中、一圈柱拱廊、折角入口) | 平面生成规则 `courtyard_plan` |
| P0 | 厚墙小窗+平顶女儿墙+白抹面气候包 | 风格卡 profile(mud_bricks/white_concrete/sandstone 三材质变体) |
| P1 | 古典柱式三档(7D/9D/10D + 柱头三式) | `classical_column` 模式卡 |
| P1 | alfiz 矩形外框 + mashrabiyya 凸窗 | 门/窗变体 |
| P2 | 双层叠拱(科尔多瓦)、穹顶 squinch、cornicione | 高配 profile / L4 收边 |

---

## 六、跨传统速查:同一构件的五种答案

| 构件 | 中世纪欧洲 | 哥特 | 中式 | 日式 | 地中海/沙漠 |
| --- | --- | --- | --- | --- | --- |
| 窗的签名 | 竖棂直通窗头+挡水眉 | 尖拱+花棂分叉 | 满开间 4-6 扇+棂格图案 | 竖棂粗细=行业 | 小洞+拱/格栅笼 |
| 支撑 | jetty 托臂+瘤头柱 | 束柱+飞扶壁 | 斗拱铺作+雀替 | 贯+角柱(无柱础) | 古典柱式 7/9/10D |
| 墙三段 | 石勒脚/半木构/挑眉梁 | 拱廊-triforium-高侧窗 5:3:8 | 台明/隔扇墙/斗拱檐部带 | 石垣 1:2/白壁/破风 | 粗石基座/素抹灰/cornicione |
| 门 | 浅四心拱+偏心过廊 | 递退门套+trumeau | 门钉等级+抱厦凸屋顶 | 全开店面/四柱门楼/平入妻入 | 12:5.5 门洞+alfiz+折角入口 |
| 檐 | 短挑 1 格,甩水靠 jetty | **零出挑**,女儿墙+gargoyle | 挑 2-3 格双层椽飞+生起翼角 | 挑 2-3 格二重垂木 | 木椽 alero 或平顶女儿墙 |

**一句话区分度自检**:给生成器出图做盲测——"有 jetty 腰线=中世纪;有飞扶壁=哥特;檐口两端上翘+斗拱=中式;贴面三角破风+竖棂格子=日式;小窗厚墙+拱+白/土色=地中海沙漠"。过不了这关的变体不值得做。

## 七、最能救现状的 5 个手法(与返回摘要一致)

1. **尖拱/圆拱参数族几何函数**(哥特+地中海共用):`arch(width, type)` 一个函数,楼梯对收的步进率决定等边拱(每升 1 收 1)/柳叶拱(每升 2-3 收 1)/四心拱(两段变率)/半圆拱/马蹄拱(先下挂 1 格再收)——门窗拱廊全受益。
2. **楼层腰线节奏**:jetty 挑眉大梁(中世纪)、string course 半砖线(哥特/府邸)、斗拱攒档带(中式)、白壁黑下见板分带(日式)——每层一条水平线,立面立刻不秃。
3. **生起+翼角:檐口两端 +1 格**(中式/日式):一行代码级的轮廓修改,飞檐曲线即出。
4. **贴面装饰件族**(trapdoor/button 零体积):千鸟破风三角、悬鱼、门钉阵列、棂格贴面、海鼠壁凸点、mashrabiyya 贴盒——成本 1 格不占空间,L4 白名单直接消化。
5. **基座-墙身-檐口三段强制分带**:每传统各有一套三段比例(城郭 1:2、哥特 5:3:8、中式台明 1/5 柱高、府邸 rustication 首层)——生成器先分带再填构件,杜绝"墙身一筒到顶"。

## 八、数据缺口与存疑

- 标"通行说法"处(单窗格高宽比、门洞高宽比、出檐绝对长度、马蹄拱精确弧度、alero 出挑比、merlon 尺寸)无单篇权威数字,已按教材通行概括给出;如需压死,建议实测科尔多瓦/阿尔罕布拉图纸(Fernández-Puertas 比例研究:https://digibug.ugr.es/bitstream/handle/10481/76515/s00004-022-00622-y.pdf)。
- 门钉金色、走兽蹲兽、钟馗瓦像等小件在 1 格粒度+项目方块白名单内无理想映射,文中给了降级方案或建议省略;若后续扩充方块白名单(如 `gold_block` 碎件、头颅),可升级。
- Wikipedia 直连在调研环境不稳定,关键数字均以机构一手来源(登录档案、大学 PDF、官方博物馆)核实替代。
