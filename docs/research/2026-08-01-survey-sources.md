# 大调查·调研源清单(2026-08-01,全部公开免费,已验证在线)

> 铁律:产出必须文字/代码化(worker 无视觉)。源分两类:**结构数据型**(给方块级 ground truth,最值钱)与**灵感图片型**(主会话看图转文字卡)。

## 结构数据型(方块级)

| 源 | 内容 | 消费方式 | 授权 |
| --- | --- | --- | --- |
| **GrabCraft** [grabcraft.com](https://www.grabcraft.com) | **6000+ 件,逐层蓝图**:建筑 4322(房屋 3019:中世纪 1227/现代 346/木屋 211;教堂 77;农场 227;军事 341;城堡 24)、户外 928(桥 42/路 45/公园)、雕像 386(动物 71/虚构 142)、交通 1550 | 主会话看蓝图页转卡;批量爬取待探针(本机无 Chrome,playwright 暂不可用) | 浏览免费;转卡学习属合理使用,不整件搬运 |
| **Minecraft Schematics** [minecraft-schematics.com](https://www.minecraft-schematics.com) | .schematic/.litematic+存档下载,Java/Bedrock | 下载→本地解析→块清单/对比数据 | 看单件说明 |
| **PlanetMinecraft** [planetminecraft.com](https://www.planetminecraft.com/projects/tag/litematica/?share=schematic) | 项目页带下载 | 同 reflib schematic-sources 调研(340+ 可解析) | **红线:解析学习可,再分发不可** |
| **abfielder.com** | schematic 商店(免费下载,有广告),litematic/schem/mcstructure | 下载解析 | 看单件说明 |
| **crabmatica.crabcore.org** | 开源 schematic 分享新站(2026-03),原生 litematic+浏览器 3D 预览 | 下载解析 | 开源社区 |
| PhantomMarket [market.phantom-node.com](https://market.phantom-node.com) | 免费 litematic/schematic 市场 | 下载解析 | 免费 |

## 灵感图片型(主会话转文字卡)

| 源 | 用途 |
| --- | --- |
| **r/DetailCraft**(reddit) | 家具/窗饰/护栏/小装饰做法灵感库(P0 家具图鉴主源) |
| **YouTube / B站教程** | "XX 个家具点子"类视频;截帧转卡(`优秀建筑图片/` 即此来源,已验证可行) |
| **BlockPalettes** [blockpalettes.com](https://blockpalettes.com) | 材质板/配色方案(T4 风格材质板主源),另有月赛作品集 |

## 工具(解析管线备用)

- **bloxelizer.com/viewer**:在线 schematic 3D 查看+材料表
- **shulkr.com/convert**、**createmod.com**:.litematic⇄.schem⇄.nbt⇄.mcstructure 互转(浏览器内本地转换)

## 第一批选择

- 房屋/公共建筑/雕像/桥 → **GrabCraft**(逐层蓝图=现成 ground truth)
- 家具/窗饰/护栏 → r/DetailCraft + 视频截帧
- 材质板 → BlockPalettes + GrabCraft 实物反推
- 批量对比数据 → PMC/minecraft-schematics 下载解析

## 国内源(2026-08-01 补,已逐个验证)

| 源 | 状态 | 用途 |
| --- | --- | --- |
| **B站(bilibili)** | ✅ 主力 | 国内建筑教程最大库;UP 主实证(用户参考图水印):RenZhen/绿绿lisepr/黑奶Black_Milk/花狐JRainbowfox/DAXAR123/沐夏夏;消费=截帧转文字卡(已验证管线)。搜索 API 需签名,走 WebSearch+视频页 |
| **MCBBS 旧贴存档** [archives.mcbbs.co](https://archives.mcbbs.co) | ✅ 存档 | MCBBS(2024-01 永久关闭,官方确认不复开)旧贴存档库——**中文建筑教程的时代富矿**,古建筑/中式尤甚 |
| **红石中继站** [forum.mczwlt.net](https://forum.mczwlt.net) | ✅ 活 | MCBBS 精神延续(2025-01 原管理组创立),帖子多资源少,活跃 |
| **苦力怕论坛** [klpbbs.com](https://klpbbs.com) | ✅ 活(HTTP 200) | 综合论坛,资源/问答 |
| **我的世界中文下载站** [minecraftxz.com](https://www.minecraftxz.com) | ✅ | 资源贴多(存档/schematic 搬运,注意授权) |
| MCNav [mcnav.net](https://www.mcnav.net) | ✅ | MC 网址导航,找新源用 |

**定位**:中式建筑(斗拱飞檐/园林/徽派)国内源是唯一富矿(GrabCraft 几乎空白)——B站+MCBBS 存档为中式专题主源;风格卡体系(T4)的"中式"四件套从这里出。

## 待办

- ~~GrabCraft 蓝图页批量抓取探针~~ **已验证(2026-08-01):纯 HTTP 全通,无需浏览器**
  - 对象 URL 可从分类页 HTML 提取(`/minecraft/<slug>/<category>`)
  - 对象页含完整材料表("Blocks you'll need: Sandstone Stairs 173, ...")
  - 层图直链:`https://bprints.grabcraft.com/<id>/Y/combined/<layer>.png`(597² PNG,当前层彩色+邻层轮廓,每格=1 方块,可程序化解析)
  - 探针产物:`scratch/phase9/gc_probe/bp_{1,2,5,9}.png`
