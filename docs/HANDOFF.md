# 交接文档 — 2026-07-31 傍晚(供压缩上下文后恢复)

> 读我即恢复全部关键状态。详细历史:git log;实验数据:`docs/experiments.md`;延后事项:`docs/BACKLOG.md`;调研:`docs/research/`(reflib 13 篇)。

## 当前里程碑

- **M1/M2/M3 全闭环**(风格卡/模式库/渲染自检/undo/形状回放/bridge 宽容化)
- **E 系列**(docs/experiments.md):
  - E0-E2 ✅(E2 基线:K3 单 agent 庄园 16.1min/36轮/52调用)
  - E3 ✅ mod 并发切片(d9be573):会话注册表(上限4)/每会话 SiteGate+token+sessions.json 落盘/429 自动续跑
  - E4 首轮 ❌(4×K2.7 盖庄园 28.3min 输基线;败因=图纸歧义:各自定 y、剖切主楼屋顶、无整地工序)
  - **E4 复赛 ✅**(K3 planner+3×K3 worker 临水镇,25.9min 盖 3 倍体量,83 轮;分工修正全生效:绝对标高/单体零剖分/显式整地桩基/依坡就势)
- **新增 mod 能力**:`/aibuild @path` 从 aibuild 根目录读任务书(d496881);config `agent_model`(spawn 时 -m 注入);worker 默认已切回 `kimi-code/kimi-for-coding`(K3 只当 planner——**成本顾虑已于 31 日晚解除,见指令 3,K3 worker 解禁**)

## 用户四条最高优先指令(2026-07-31)

1. **本地程序优先**:算得准的全给程序(选址分析/碰撞登记/参数化屋顶/量化验收),AI 只做审美决策
2. **建筑碰撞**:小镇把庄园吞了(x[0,20]×z[96,111] 重叠)——选址必须过"已占用地图"(sessions.json 里所有 confirmed bounds)
3. **消耗(2026-07-31 晚用户修正)**:非套餐折合约 50 元/建筑,但走会员额度,用户明确"单建筑对额度完全可接受"——**成本不再是约束**:K3 worker、足量渲染自检、多轮迭代全部解禁;token 账单仍补,目的改为观测而非省钱(额度周期性刷新,不等于无限)
4. **风格单一/复杂建筑**:调研已做(reflib 新增 5 篇);Blender 探针验证"预制模块装配"路线

## 在途 agent(恢复时查 TaskList)

- **大调查进行中**(plan:`docs/plans/2026-08-01-grand-survey.md`):抓取器 `scratch/phase9/gc_probe/grabcraft_scrape.py`;已入库 starter-houses 16+教堂 15+桥 16+木屋 16(补抓农场中);家具图鉴已入库部署(我校审过);下一步屋顶专题(老虎窗)
- **agent-36**(续跑中):mod 改造——已占用地图+`analyze_site` 选址工具+propose 警告+token 账单(stream-json usage 解析)
- **agent-45**:Blender 装配探针——模块=带 block 元数据的单位立方体,导出走块清单不做体素化(设计:docs/plans/2026-07-31-blender-assembly-spike.md);探针题目=小教堂,验收=屋顶/楼梯朝向零错误

## 调研新增(reflib,全部含来源 URL)

schematic-sources(PMC 340+ 可解析,授权红线=再分发)/chinese-monumental(斗拱飞檐模数)/detailing-depth(depth三层+weathering掺比)/statues-organic(三派起手式)/complex-build-workflow(Litematica verifier=机器验收模型)

## 环境事实

- mod 部署:`cd aibuild-mod && ./gradlew build` → jar 复制到 `D:\PCL 正式版 2.13.0.1\word\versions\1.21.11-aibuilding-test\mods\`;**纪律:游戏开着时禁止部署 jar**(2026-08-01 事故:游戏运行中覆盖 jar,JVM 缓存视图损坏,命令报"意外错误"后崩溃 ZipException invalid LOC header——部署只在游戏关闭时做,或让用户先关游戏)
- dev server:`./gradlew runServer`(后台);RCON `python run/rcon.py "cmd"`;bridge.json 在 `run/aibuild/`;**杀 server 要直接 taskkill java PID,杀 gradlew 会留孤儿**
- 世界 aibuild 根:`run/world/aibuild/`(tasks/ 放任务书,sessions/s<N>/ 每会话目录)
- 庄园 x[0,41] z[80,111];小镇 x[-40,20] z[96,150](有重叠带,验货时注意);E3 测试盒 y=180
- Blender 4.2.23 在 `D:\blender-4.2.23-windows-x64`;blender-mcp addon 在 `scratch/blender-mcp/addon.py`(曾跑通,端口 9876)
- Windows python 不认 /d/ 和 /tmp 路径,要用 D:/ 和 C:/Users/zengd/AppData/Local/Temp
- python 写 JSON 必须 encoding='utf-8'(系统默认 GBK);console 乱码是 GBK 显示问题,文件本身多半没坏

## 下一步(按序)

1. **大调查**(plan:`docs/plans/2026-08-01-grand-survey.md`,2026-08-01 任务):T0 机制层(索引卡/卡格式 v2/两条 validator)→ T1 家具图鉴 15 件 → 屋顶老虎窗
2. **E7 从里到外造楼**:✅ 首题两段闭环(布局验收→外壳→复测全通)。下一题接大调查产出再吃
3. agent-45 Blender 探针已完成(✅ 朝向零错误)→ 决策:放大 Blender 路线 or 退回游戏内生成器模块库
4. 风格卡体系升级(吃 reflib 新 5 篇)——并入大调查 T4
5. 感知升级:多角度渲染包+接缝扫描+量化检查(schematic verifier 思路)
6. E5:同一建筑多 worker 并发修改

## 2026-08-01 深夜快照(额度收官)

**系统现状**:访谈(ask_player)+建造闭环全通,14 张风格卡+11 专项模式卡+共享风格库。最新提交 dc9cf85,jar 已部署(23:02,PCL mods)。
- 访谈流程: /aibuild→访谈 agent(单问题 ask_player,可点按钮,无限等待)→intake_brief.md→自动交接建造 agent;无卡先造卡(styles/<id>.json),新卡自动提升到 <世界>/aibuild/shared_styles/
- 用户实测反馈(本轮): 卡片让建造明显变快、消耗明显变小
- 额度账单机制: sessions.json stats(token_in/out/cache_read),缓存命中 90%+,省钱靠 READ LIGHT/断路器/渲染预算(都在 22:27+ jar)
- **部署纪律修正**: 游戏进程= java.exe(命令行带 Mojang/natives),不是 javaw!检查: powershell Get-CimInstance Win32_Process java.exe 排除 gradle。曾因误判热替换 jar 导致游戏内类加载崩溃

**抓取(零额度,挂着跑)**: scratch/phase9/gc_probe/(grabcraft_scrape.py --shard=k/n)
- 4 分片(task bash-lbmpu3nc/tkpayj2p/o0yj6eah/s93ql8b8)啃 medieval-houses 1227 件,542 全量,nohup 组(group1-4.log)啃 modern/sightseeing/tree-houses/fictional/castles
- 全库 2429 件 meta,1257 带层图。GrabCraft 限流(~60 件/h 总),预计上午收完
- GrabCraft 无日式分类;日式样本 51 件已统计并出 sakura_japanese 卡

**下次开工先做**: ① 查抓取完成度(上表) ② 全量统计补 stats_palettes ③ 细节肌理卡调研(facade_depth>accent_detailing>timber_structure>树枝升级>花园层次,见 2026-08-01 讨论) ④ 用户实机测完整闭环(14 卡)

## 2026-08-02 快照(额度等待期)

- 抓取全收: 3666 件/2587 带层图/53182 PNG(scratch/phase9/gc_probe/),stats_palettes.md 已按全量刷新
- **肌理卡整批延期至 5 号额度刷新后执行**(用户拍板: 做完整版,含层图分析器校准; 计划= docs/plans/2026-08-02-detail-texture-cards.md,五类框架/骨形色饰景,B1→D1→A3→E,组合下沉 profile 机制)
- 复工第一步: layer_analyze.py(gc_probe 下,验证 PNG 语义→4 项统计→stats_details.md),然后 B1/D1 子代理并行
- 14 张风格卡 jar 已部署(23:02),实机完整闭环测试用户择机进行

## 2026-08-06 凌晨快照(全线收口,读我恢复全部状态)

**最新提交 f5acd0a;jar 已部署(00:49,PCL mods)。资产总账:19 风格卡 + 47 模式生成器 + 6 验收器。**

### 用户已定稿的路线图(docs/plans/2026-08-05-roadmap.md,grill 敲定)

R1 卡格式 v3 ✅ → R2 内饰包 ✅ → R3 A/B 实验 A 组 ✅ → R4 零钱组合 ✅ → R5 脊饰卡 ✅ → **R6 环境轴(进行中,见下)** → R7 二批 3 卡 ✅ → R8 巨树调研(原型已出) → R9 聚落(放最后)。冻结:B12 大串烧/B1 集群(精灵树后)。**系统已达"普通玩家水平"(用户认定)**。

### 本轮落地(全部已部署)

- **多样性机制(B13)**:16 卡 lottery 白名单字段 + lottery.py 抽签器(rules 收敛/requires/确定性)+ 访谈后抽签产出 build_order 任务单(与访谈答案同权威,默认不可推翻)。**缺省 seed 已改 SystemRandom 真随机**——A/B 实测抓到访谈 agent 爱用当天日期当 seed(5/8),同一天任务单全同
- **plan_shape**(L/T/U/凹凸平面,语料凹凸率分档校准,治剪影单一)、**clutter_pile**(杂物堆)、**wear_path**(踩径)、wall_weathering+patch_pct(补丁)
- **room_partition 分房生成器**(回刀二分+隔墙吸附开间+门树动线+BFS 内置可达校验,不可达 die;输出 rooms[] 直接喂 interior_rooms,window_hints 供外墙开窗对齐——**分房先于开窗**)。手册已接线
- **accent_detailing 室内 palette**(挂毯/壁灯/蜡烛/书架墙/顶角线/盆栽;1.21 放不了 painting 实体,挂画用 wall_banner)
- **roof_ornament 通用脊饰**(中鸱吻/哥特尖塔/日鬼瓦/欧脊冠风向标)
- **风格卡二批 3 张**:desert_adobe/japanese_castle/gothic_cathedral(带 lottery+interview_prompts;产卡任务书已升 v3,在 docs/specs/)
- **giant_tree 巨树原型**(空间殖民,干径 2×2/3×3、板根、验收绿,INDEX 标实验品;已知不足在 scratch/giant_tree/notes.md:主枝缺"平展再上扬"曲线、叶团葡萄串感)
- **16 卡 interview_prompts**(每卡自带必问清单:rooms+结构决策点+skip_if);访谈手册已接线
- **消耗播报**:会话终结时聊天栏播 token 账单(AgentRunner.broadcastTokenBill)
- **B9 修复**:set_blocks_from_file 路径围栏(BlocksFilePlacer,洞在 bridge 不在 mod;测试用 -Daibuild.bridge.fileRoot 覆盖口)

### 关键修复与事故教训(这轮全是干货)

- **超时三层套娃**(访谈"1 分钟就自答"的真凶):kimi MCP 客户端 60s > bridge HTTP 30s(真凶) > mod 等待片 60s。已对齐:mod 45s < bridge 120s(默认+显式传参双保险) < kimi 180s(mcp.json toolTimeoutMs)
- **选区残留 bug**:选区杖选区永久落盘从不消费,旧选区静默绑定后续建造、访谈跳过选址——已改一次性消费(AgentCommands.aibuild)。锚点取交接时玩家当前位置
- **树叶消失**:树叶必须带 [persistent=true](garden_tree 已修,手册有铁律)
- **手摆楼梯必歪**:staircase 卡(straight/L/U,facing 全自动)
- **思考等级**:游戏 agent 之前跑 low(kimi 全局 [thinking] effort 盖掉模型默认)——已改 C:\Users\zengd\.kimi-code\config.toml 的 effort="high"(全局,注意它也影响交互 CLI)
- **agent_model 配置**:`<游戏目录>/aibuild/config.json`(PCL 那份已是 kimi-code/k3-256k;dev server run/ 那份也改过)
- **并发纪律**:账号并发上限 4——用户测试期间主 agent 并行子代理 ≤2
- **部署纪律**:先查游戏 java 进程(命令行带 Mojang/natives,排除 gradle)为 0 才覆盖 jar;**mod jar 打包 bridge jar,改了 bridge 要先重建 mc-mcp-bridge 再重建 aibuild-mod**

### A/B 实验 E9 结论(docs/experiments.md,数据在 scratch/ab_test/)

8 跑同提示词(纯计划版,单次仅 ~15k 输入):1/3 阈值=非强坍缩;风格轴收敛(8/8 plains_cabin,有语义合理性),参数轴被抽签器注入真多样性。软抵抗实例:s29 builder 没按任务单盖(机器抽查必要性实锤)。**B 组(无抽签对照)未跑,可选**;lottery 权重校准=攒 lottery_log.jsonl 跑量回收,不占开工位

### 外部资产(D:\建筑资产\)

- **terrain/ 聚落引擎**(B10):根因已定位(采样把树叶当地表等 4 条),R6 已修第①步采样白名单(verify.py,9 测试过);KNOWN_ISSUES.md 有最新进展。**剩余 ②③④ 随聚落线重开**
- **调研/**:13+1 篇全部有料(图片造法提炼.md 是 32 张参考图蒸馏)
- **验证/**:verify.py 工具链(bridge 直连,灌入/渲染/校验);**陈列馆已灌进 PCL 世界**(-52,-60,248 起 255×187,39 零件,manifest 在 scratch/gallery/)
- 交付清单-彻查版.md 是它全部产物的索引

### 下一步(按序)

1. **用户实机验证当前版**:重点分房器(内饰乱不乱/进不进得去)、抽签多样性(同提示词连造两栋)、新风格卡(天守阁/沙漠)
2. R6 环境轴剩余:B10②③④(楼梯 facing/支撑/真 hmap 自检)+地形适配进推导链;纪律=真实灌入验证
3. R8 巨树下一步:对照精灵树图片调主枝样条/叶团形态(scratch/giant_tree/notes.md 有清单)
4. R9 聚落:最后
5. git:当前全部已提交(f5acd0a)
