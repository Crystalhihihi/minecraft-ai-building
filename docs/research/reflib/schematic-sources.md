> 调研日期 2026-07-31,来源 14 个

# Planet Minecraft Schematic 资源调研

## 1. PMC 上 medieval/town/castle schematic 供给情况

PMC 官方支持 schematic 作为独立下载类型(项目页出现 "Download Schematic" 按钮),且项目列表提供
`?share=schematic` 官方筛选器,medieval / castle / town 等 tag 均可按此过滤:
- https://www.planetminecraft.com/projects/tag/medieval/?share=schematic
- https://www.planetminecraft.com/projects/tag/castle/?share=schematic

精确比例 PMC 未公布(证据不足以给出百分比),但 medieval tag 带 schematic 的列表分页到第 17 页以上
(每页 20 条,即 340+ 条),castle/town tag 同样有独立筛选页,量级估计各在数百至上千条。注意 PMC 页面
有反爬(直接抓取返回 403),批量采集需用搜索缓存或其 3D 预览(pmcview3d/schemagic)旁路,或改用
abfielder.com 这类聚合站(同作者同步发布 .litematic/.schem 双格式)。

### 10 个最佳 exemplar(medieval/town/castle,均确认提供 schematic 类下载)

| # | 名称 | 作者 | 类别/风格 | 尺寸 | 数据 | 链接 |
|---|------|------|-----------|------|------|------|
| 1 | KCD2 Suchdol Castle inspired | Nequ (Lv27 Expert Architect) | 城堡,Kingdom Come: Deliverance II 写实 | 未获取(PMC 反爬) | 5,744 浏览 / 1,506 下载 / 21 钻 (2025-08 发布) | https://www.planetminecraft.com/project/kcd2-suchdol-castle-inspired/ |
| 2 | Walled Medieval Town | TheAvatar | 中世纪城墙小镇(刻意做小而自足,可直接嵌入任意世界) | 未获取 | 33.8k 浏览 / 5k 下载 / 87 钻 (2013 老帖长青) | https://www.planetminecraft.com/project/walled-medieval-town/ |
| 3 | Medieval Town Bundle [7 Houses + Assets] | Lumilins | 7 栋中世纪民居+构件包,适合拆件学习 | 未获取 | assets/village/town 多 tag 高分常客 (2018) | https://www.planetminecraft.com/project/medieval-town-bundle-download/ |
| 4 | Small, Medieval Spawn [FREE SCHEMATIC] | MIDNITEE | 中世纪城堡式 spawn | 未获取 | 25,818 浏览 / 4,469 下载 (2015) | https://www.planetminecraft.com/project/small-medieval-spawn-free-schematic-download/ |
| 5 | Medieval Castle Schematic | MCMystical | 中世纪城堡;在 Sketchfab 以 CC-BY 镜像 | 未获取 | Sketchfab 6.7k 浏览 | https://www.planetminecraft.com/project/medieval-castle-schematic-5777013/ |
| 6 | Cozy Medieval Barn 1.21 (Free Download) | — | 中世纪谷仓/马厩,村落填充件 | 未获取 | 2025-11 发布,新版本方块 | https://www.planetminecraft.com/project/cozy-medieval-barn-1-21-free-download/ |
| 7 | Medieval Hub / Spawn-Lobby | BuildBucket | 浮空岛中世纪城堡 hub(含酒馆/市集摊位) | 未获取 | 2025-06,作者明示允许服务器使用 | https://www.planetminecraft.com/project/medieval-hub-spawn-lobby/ |
| 8 | Cute Diagonal Medieval Wooden House | — | 斜向中世纪木屋(对角线工艺参考) | 未获取 | 2026-07 发布 | https://www.planetminecraft.com/project/cute-diagonal-medieval-wooden-house-schematic/ |
| 9 | Medieval Castle (abfielder) | LeoHunter065 | 中世纪城堡,.litematic | 88×75×57,46,043 方块 | abfielder 免费下载 | https://abfielder.com/Products/ProductDetails.php?id=3275 |
| 10 | Medieval Castle (abfielder) | PepaBw | 中世纪城堡,.litematic(同站另有 Factory Castle 60,278 浏览) | 3,793 方块 | abfielder 免费下载 | https://abfielder.com/Products/ProductDetails.php?id=2940 |

补充参照(非 PMC):9Minecraft "Medieval Castle Undecorated Interior Schematic" 64×46×88 / 24,705 方块,
空内饰中等城堡,适合当体量基准(https://www.9minecraft.net/medieval-castle-undecorated-interior-schematic/)。

## 2. 社区对 schematic 二次使用的通行授权态度

通行规则可概括为「下载自用默许,再分发禁止,整合发布需署名」:

1. **PMC 平台层面:盗用他人作品会被下架**。有管理员处理记录:接到举报后移除全部 stolen submissions,
   并指引用 submission 上的 flag 举报(来源:MCBBS Wiki 收录的 PMC 管理员回复,
   https://mcbbs.wiki/index.php?title=LonelyLoner )。
2. **作者个体声明是主要授权载体**,三档常见措辞:
   - 允许使用但要求署名:"feel free to use it however you like… please give credit to me"
     (ClassyEnglishman, Hub Style Spawn, https://www.planetminecraft.com/project/hub-style-spawn-schematic-amp-world-save/ );
   - 允许服务器使用、署名非强制:BuildBucket "we don't mind hosting and using our buildings as
     decorations on your server… place a small plaque"(见上表 #7);
   - 禁止转载/冒名:"DO NOT re-upload… You WILL be caught"(Derivation 材质包,
     https://www.planetminecraft.com/texture-pack/derivation-1-16/ )。
3. **少数作者上明确许可证**:MCMystical 的 Medieval Castle Schematic 在 Sketchfab 镜像标注
   CC Attribution(https://sketchfab.com/3d-models/castle-schematic-8d87dfec36d24cc9a9335054c5e252ba )。
4. **schematic 专门站的转载惯例是先取得原作者许可**:minecraft-schematics.com creation #3412 的上传者
   明确写到先向原作者要到 go ahead 才上传(https://www.minecraft-schematics.com/schematic/3412/ )。
5. **整合再发布的实操惯例:全量列出来源链接**。CurseForge 大型地形图 Tater Lands 把用到的每个
   PMC/builtbybit 资源逐条列链接以示 credit(https://www.curseforge.com/minecraft/worlds/tater-lands-the-mystical-caverns-3072x3072 )。

对本项目的含义:把 schematic 当**离线解析的训练/参考数据**(不外发原文件)风险最低;若将来要把参考件
嵌入公开发布的地图,按"署名+链接回源"执行即可满足通行惯例;原样再分发 schematic 文件本身是红线。

## 3. .schem / .litematic 解析的现成库

格式基础:两者均为 **gzip 压缩的 NBT**;.schem 官方规范为 SpongePowered/Schematic-Specification,
当前 v3(2021-05-04,v2 加实体/生物群系/DataVersion,v3 加 3D 生物群系),
https://github.com/SpongePowered/Schematic-Specification 。

**Java(与 aibuild-mod 同栈,优先)**
- **schematic4j** — 一个依赖同时读 `.schem`(v1/v2/v3)、`.litematic`、legacy `.schematic`;
  Maven Central `net.sandrohc:schematic4j:1.1.0`;API:`SchematicLoader.load()` → width/height/length/
  block(x,y,z)/blockEntities/entities。注意:Sponge 论坛有用户反馈其维护不活跃且有怪异行为,
  建议用前先做样例验证。https://github.com/SandroHc/schematic4j
- **WorldEdit/FAWE Clipboard API** — 最成熟路径,`BuiltInClipboardFormat.SPONGE_V3_SCHEMATIC` 读、
  `ClipboardFormats.findByFile()` 自动识别;加载后得到 `Clipboard`(本质就是方块数组+origin),
  可直接遍历而非必须 paste。教程:https://madelinemiller.dev/blog/how-to-load-and-save-schematics-with-the-worldedit-api/
- hollow-cube/schem — Minestom 生态的 schematic 库,可脱离服务端用。https://github.com/hollow-cube/schem

**Python(做离线批量分析/特征提取用)**
- **litemapy** — `.litematic` 读写全功能(区域、方块存储、元数据),PyPI `pip install litemapy`,
  文档在 ReadTheDocs。https://github.com/SmylerMC/litemapy
- **mcschematic** — `.schem` 生成(写入)库,`pip install mcschematic`,setBlock/save 工作流,
  适合程序化产出参考件;读取 `.schem` 无专门主流库,可按 Sponge 规范用 NBT 库自行解析(格式即 gzip NBT)。
  https://github.com/Sloimayyy/mcschematic

**其他语言(备选/交叉验证)**
- Go: oriumgames/schem — Sponge v1-v3、Litematica、Axiom、MCEdit 多格式自动检测。
  https://github.com/oriumgames/schem
- TypeScript: tribixbite/craftmatic — 解析/生成/渲染 Sponge v2。https://github.com/tribixbite/craftmatic

格式互转(应急):Lite2Edit(.litematic→.schem,Java CLI)、Shulkr/Bloxelizer 在线转换(浏览器本地执行)。
