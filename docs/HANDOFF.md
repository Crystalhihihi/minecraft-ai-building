# 交接文档 — 2026-07-31 傍晚(供压缩上下文后恢复)

> 读我即恢复全部关键状态。详细历史:git log;实验数据:`docs/experiments.md`;延后事项:`docs/BACKLOG.md`;调研:`docs/research/`(reflib 13 篇)。

## 2026-08-07 凌晨快照④(多样性四连: species/facade_scan/三树/stair_row)

**用户拍板的四步全部落地部署(04:5x jar, 资产 157 文件)。全部未提交(连同前 3 批)。**

- **①species 材质库**: giant_tree SPECIES 扩到 9 种(birch/spruce/jungle/acacia/cherry/mangrove/pale_oak 新增), 新 preset 4 张: cherry_blossom(樱花粉叶)/birch_grove/mangrove_swamp/pale_oak_garden(材质系卡, 同骨架换树皮, ASPECT 域已配)
- **②装饰感知**: facade_scan.py(立面扫描→门窗洞/平整区段/候选锚点(corner_pilaster/base_footing/string_course/eave_cornice/window_trim/accent_cluster)+每面 budget 2-4) + decoration_menu.md(每锚点配方级文字描述, 来源 realworld-vocab+detail-techniques) — 治"强行让 AI 修饰";手册 FACADE DEPTH 改为"先扫再饰, 锚点外的面是留白";真房子(s3)实测输出正常
- **③三树拆分**: tree_common.py(共享 kernel: h3/rhu/vline/Voxel/tuft/9 species;giant_tree.py 内嵌拷贝冻结未回拆) + conifer_spire.py(spire 云杉锥/cedar 分层塔/pine 伞松, 裙边下垂撕裂) + palm_umbrella.py(棕榈羽状叶+椰团/平顶金合欢 60% 双干) + weeping_tree.py(垂坠叶帘 0.35-0.6h 透缝渐稀);**踩坑: 弯干对角断开+羽叶/叶盘脱离干顶, 全靠 vline 连通桥, 否则 flood-fill 全剪**(palm 曾只产 8 块)
- **④stair_row.py**: facing/half 几何推导, **shape 不写 — ChunkSupport 的 shape replay(UPDATE_CLIENTS|KNOWN_SHAPE)让游戏放置时自动算转角**(原版逻辑);run 平推/上升(smooth 踏踢交替)/ring 矩形环(back_mode out=inner/in=outer)
- 全部 validators 过(support_check 0 浮空);手册已接线(针叶走 conifer 不走 giant_tree/装饰先扫/排梯必跑 stair_row)

债: 精灵装饰 special 钩子仍压;weeping/palm 渲染仅离线低角度验证, 等实机;commit 等用户一句话

## 2026-08-07 凌晨快照③(树 v4 沿枝簇生+骨架 v3.2+圆台收分)

**GitHub 调研落地(ez-tree/AJM/vanilla placer)后重写: 树叶 v4 + 骨架 v3.2 已部署(03:4x jar, 部署时游戏进程=1, 用户须知重启游戏加载新 jar)。未提交(连同 v3.1+手册批一起)。**

- **树叶 v4(ez-tree generateLeaves 体素化)**: 废除盘壳, 沿每条辐条/主枝外侧段分层撒叶簇(位置分层+抖动, 簇径 ±30% 方差, 簇距随簇径缩放保证交叠, 梢端大团封顶 r≤5, 边界 2 轮飞叶 10%/4.5%);蓬松感=尺寸方差+边界噪声。小树主枝起簇 0.55→0.3
- **骨架 v3.2**: trunk 上限 2-7(粗高 ts≈h/15, 细高 ts≈h/25);spiral 加**盘旋棱脊**(干身绕轴棱线 pitch=ts*3+8 层/圈, 粗干双棱, 端面纹理条纹 — 盘旋靠棱脊不靠漂干);curved 弯幅 min(3.0, 0.6ts+0.6)
- **参考固化**: ez-tree tree.js 语义(子枝粗细随父枝局部半径/扭曲度 1/√半径/twist 绕生长轴逐段累加), AJM 等值面冠, vanilla foliage placer
- 验证: 4 树 support_check 全绿 0 浮空;高度: 冠顶可冒 2-4 格(叶簇+飞叶, 卡面已注);块数 22 高 1.7k/100 地标 3.4 万
- **部署事故自查**: 进程查询返回 1(游戏开着)仍 cp 覆盖 jar——命令链没按计数分支, 下次必须先判 0 再部署
- 下一步: 装饰感知工具+锚点菜单(治"强行让 AI 修饰"; 参考=docs/research/realworld-vocab.md+detail-techniques.md, 菜单项带文字描述防乱造) / stair_row 楼梯行推导 / 精灵装饰钩子仍压

## 2026-08-07 凌晨快照②(系统级反弹: 手册松绑+树 v3.1+plaza circle)

**用户实机三连测(世界5 s1 树+广场/s2 秋色树/s3 民居)后系统级否定: "这些东西彻底限制死了 llm"。树 v3.1 + 手册大改已部署(02:5x jar)。未提交。**

病根(证据链, 全部来自会话取证):
- 手册 `INTERIORS LAST` 明文规定先墙后家具 → 用户的"从里到外"从未落实(s3 plan 证实, 家具最后塞, walkability 验到超时)
- 手册"元素有生成器却徒手=失败"+flatness 硬门"裸墙=失败建筑" → AI 每窗必窗套堆饰(用户: 谁说窗户一定要装饰的?)
- 生成器输出被当圣旨(手册禁止手改) → plaza 拿着就用(巨树下孤立方垫子, 逆天)
- 树: taper 到 1x1=筷子干(s1 115 高地标); 主枝 45% 裸露段用户嫌丑(s2 AI 自己写 tip_tuft 补丁救枝尖); 盘壳剪影每棵一样; **比例失控**(s2 55高×52冠煎饼, 再被 AI 自写换色脚本糊成炒蛋羊毛)

改动:
- **giant_tree v3.1**: 收分 tip=max(1,ts-2)(ts=5 冠下保持 3x3); 主枝盘链 45%→25%+枝端埋尖+辐条止壳内(不捅出叶壳)+辐条仰角钳位(防下垂裸枝); 逐盘 dr/dh 抖动+35% 卫星小团(破"每棵一样"); **冠区干身盘链**(0.6/0.72/0.84h 三盘裹上段干, 治 15-20 格冠区裸干段); **高宽比硬护栏**(按 preset 合法域, 越界 die 拒生成)
- **plaza**: 新增 shape=circle(边缘 seed 抖动±1+外圈 dirt_path 磨损带+环形灯椅), 树下/喷泉/神像必用; 曾踩掉模块 docstring 闭合引号(整文件变字符串, 已修)
- **手册(WorkDir.java AGENTS_MD)**: ①INTERIOR FIRST 从里到外五阶段(分隔→楼板梯→家具开敞落位→闭壳→walkability 门); ②生成器两层制(正确性关键件仍强制: 屋顶/楼梯/门口/连廊/平面/整地/镜像/分隔/宿主树; 其余=可跳可删改的草稿, 禁手改仅限楼梯方向态); ③装饰预算(窗套正立面或隔窗, 次立面可留白, flatness 只查零 relief 面非配额); ④plaza 尺度贴主体纪律
- 验证: 5 树高度达标+support_check 全绿+裸木检测(仅主干/板根段, 正确)+plaza circle 边缘有机+比例护栏拦下煎饼树

债: 精灵装饰 special 钩子(发光/垂藤/灯笼); 树按几何原型拆分(conifer/palm/willow); 等实机验收本批

## 2026-08-07 凌晨快照(巨树 v3,读我恢复全部状态)

**用户实测报"树断头/粗细变化差/60 上限"。giant_tree 重写为 v3 并部署(01:2x jar)。完整简报(给评审 agent)在 `docs/research/giant-tree-v3-status.md`。**

- **根因链(全部数据证实)**:①主干止于冠底+顶盘超殖民半径锁死=断头;②弯/螺旋干截面对角断开被 flood-fill 剪掉整段顶梢;③吸引点均布盘内→细枝淤成平板木;④收分单档突变;⑤height≤60 上限
- **v3 架构**:顶梢干贯顶(树脊)+主枝样条(起角 0.25-0.45,枝长 0.5-0.7 冠幅)+沿枝盘链+核心盘+顶盘+**盘内确定性辐枝扇**(废除空间殖民,地标级 40s→0.2s)+盘壳叶(小盘补实)+渐进收分半砖台阶+解析有界干形(螺旋半径≤2.5)+vline 层内连通桥;上限 height 150/canopy 50/trunk 2-5
- **验证**:5 树(22/35/40/60/100)高度全达标±1,support_check 全绿,除板根鳍尖外全部木块 2.5 格内有叶;**教训:matplotlib 单视角渲染多次误导,评审须 az=0/45/90+纯叶对照或直接用裸木检测脚本**
- **同步**:giant_tree.json 卡面/INDEX/两张宿主树风格卡(elven_tree 35-150, tree_house 25-60)
- **未实机验证**:用户首测重点=60 高 spirit 剪影/100 高地标体量/半砖收分观感/2 万块放置耗时
- **债**:精灵装饰 special 钩子(发光脉络/垂藤/灯笼=标杆六条核心欠款);**按几何原型拆分树生成器**(用户拍板要做):giant_tree 留阔叶云片,新 conifer_spire(针叶裙边)/palm_umbrella(伞盖)/weeping_tree(垂柳),共享 kernel 抽 tree_common.py;banyan 多干/willow 垂坠当前是近似卡
- **git**:本批改动未提交,等用户确认

## 2026-08-06 深夜快照(细节层闭环,读我恢复全部状态)

**最新提交 7a7fd05;jar 已部署(23:41,PCL mods)。系统已达"理论完全体":访谈(提案制)→风格卡(19)→抽签(参数+构图双轴)→生成器(49 含连接件)→验收(7 含 flatness)→渲染自检,全链路无空环。**

### 今天落地的(全部已提交已部署)

- **R6 环境轴收口**:roadfit 楼梯 facing 重写(vanilla 语义 facing=上坡;R=1 高格换楼梯,R≥2 低点柱叠楼梯);`验证/road_test.py` 真灌入读回验证 harness;TerrainSummary 野地虚空 bug 修复(getChunk 预载);builder 手册地形适配推导规则
- **访谈提案制重写**:Q1 用途剪枝(纯观赏外壳才砍内饰,通达性保留)/结构点≤3/材质永不问/体量六档(超小~地标)/收尾=全决策回放([开工]/[我要补充]/[逐项过一遍]);19 卡 size_tiers 标注
- **访谈 bug 修复**:PlayerInbox.take 丢唤醒竞态;"已排队"误导回显;看门狗 8min idle 杀+自动续跑(此前只杀不救);k3 思考慢是常态不是卡死
- **R10 体块编排层(前半+后半)**:构图原型聚类(scratch/phase10/composition/,1867 建筑:rect 78%/L 4.6%/cluster 4.3%/O 1.8%);19 卡 composition 轴按类目加权;plan_shape 扩 O 围合+cluster 簇群;connector.py 连廊(open/covered/enclosed,L 弯,门洞 sidecar);拼装验收=collision+walkability 组合;真实灌入验证全绿(scratch/phase10/pour_assembly.py)
- **roof_plan.py**:L/T/U 分翼垂直屋顶+45°谷沟(止于脊下);修"L 形盖两个平行双坡"翻车;**重大教训:DEFAULT_ASSETS 是手工清单,新生成器必须登记(connector 曾漏登导致游戏 agent 收不到)**
- **R8 巨树形态库**:giant_tree v2(显性主枝样条低位起叉先平展再上扬/云片层盘/干形四式直弯斜螺旋/沿骨架收分);11 形态卡 preset(spirit_candelabra=Ori 标杆);调研 docs/research/tree-forms.md;宿主树接线(elven_tree/tree_house 卡+手册);`scratch/giant_tree/tree_png.py` matplotlib voxel 离线渲染器(形态目检主力工具)
- **细节构件卡族**(治"细节纸糊"):doorway.py(7层门口)/window_trim v2(内凹默认)/eaves_trim(椽子+封檐)/gable flare_corners(翼角)/furniture 5 组团模板(箱上半砖铁律)/抽签校准(dormers→5%,悬挑露台→5%);**flatness_check.py 光秃墙验收器**(细节硬门);plan.md 构件→生成器映射强制(有生成器却徒手=失败)
- **调研三路**:detail-techniques.md(MC builder 技法配方)/realworld-vocab.md(5传统×5构件,74 URL)/stats_detail_elements.md(语料定量 540 件)

### 用户实测反馈(压测中,按时间序)

1. 地标级树造成庭院级 → 巨树形态库立项(已修)
2. 双体图书馆翻车(屋顶/楼梯/融合怪) → 诊断=资产不用非缺资产 → 手册牙齿化
3. 卡死 14 分钟 → 看门狗自动续跑(已修)
4. L 形房盖平行双坡 → roof_plan(已修)
5. 门=原版门方块/工作方块排一排/家具堵死房/一格露台/窗只有一圈环 → 细节构件卡族(已修,待实机验收)
6. **形态(剪影/比例/体块)用户确认过关**——L1/L2 层立住了

### 下一步(按序)

1. **用户实机验收细节层**(建议场景:中世纪民居 小/中档——最能压住房门口/窗/檐口/家具)
2. 精灵树标杆六条硬指标(8-06 用户发的 bilibili 图定为验收锚点):干发光脉络/冠内光点/垂藤/环形拱廊/拼花广场/花坛基座——缺:发光脉络/垂挂/arcade_ring 生成器
3. 用户截图投喂(优秀建筑图片/:门口/窗/屋檐/工作间/露台/墙面)——口味校准
4. R9 聚落(地形引擎 B10②③④ 已修完,聚落接通);B12 大串烧/B1 集群仍冻结(精灵树标杆后)
5. 可选:grabcraft-to-schema 评估(层图 PNG→3D 精确数据升级语料)

### 血泪纪律(新增)

- **DEFAULT_ASSETS 手工清单**:新生成器/卡文件必须登记进 WorkDir.java 的 DEFAULT_ASSETS,否则游戏 agent 收不到(connector 事故)
- flatness_check 判据:凸出+1 格深覆盖都计 relief;窗洞碎面逃避问题已修(覆盖格计入面积)
- 用户游戏 jar 在 PCL mods;部署前查 java 进程(Mojang|natives 过滤,排除 Daemon)
- 游戏里查 agent 状态:sessions.json 在 saves/<世界>/aibuild/;日志在 sessions/s<N>/logs/
- jar 大小≈2.7MB 稳定:文本资源 zip 高压缩,加生成器几乎不涨,不是没打进去

---

## 历史快照(更早状态见 git log)

## 当前里程碑(2026-07-31 口径)

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
