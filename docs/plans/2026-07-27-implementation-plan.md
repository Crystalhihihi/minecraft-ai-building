# Minecraft AI Building — 实施计划

- 日期:2026-07-27
- 对应规格:[2026-07-27-minecraft-ai-building-design.md](../specs/2026-07-27-minecraft-ai-building-design.md)
- 原则:按风险排序,每个 Phase 有明确验证出口,不验证不进入下一阶段。

## Phase 0:CLI 行为验证(纯命令行,不写项目代码)—— ✅ 已完成(2026-07-27,kimi 0.29.2)

- [x] 0.1 `kimi -p --output-format stream-json` 正常;assistant 消息为 `{"role":"assistant","content":...}`;**meta 行直接给出 session_id 与续聊命令**;与桌面版共享 `~/.kimi-code` 登录态,开箱即用
- [x] 0.2 **续聊**:`kimi -c -p` 与 `kimi -r <id> -p` **均实测通过**(都正确答出上轮的 42);首选 `-r <id>`(显式、id 来自 meta 行),`-c` 兜底
- [x] 0.3 **静默可观测性**:长回复期间 stdout/stderr **全程零字节**(stream-json 只发完整消息,无增量;无工具时 stderr 全空)→ 静默超时口径=双通道无字节,默认 20min 合理,不能依赖 stderr 做活性判断
- [x] 0.4 **MCP 握手**:项目级 `.kimi-code/mcp.json` 生效;假 stdio server 的 initialize/tools/list/tools/call 全通;**并行工具调用**正常;**base64 PNG image content 真的被模型看到**(正确描述红底蓝斜线)
- [x] 0.5 最终命令形态:`kimi -p "<短 prompt>" --output-format stream-json`,cwd=工作目录;续聊 `kimi -r <id> -p "<消息>"`;CLI 安装=官方 PowerShell 脚本(`~/.kimi-code/bin/kimi.exe`,自动上 PATH)

## Phase 1:mc-mcp-bridge(独立 Gradle 模块)—— ✅ 已完成(commit `0e05a01`,37/37 单测绿)

不依赖 MC,先行开发,全部可单测。

- [x] 1.1 `mc-mcp-bridge/` Gradle Java 21 项目;唯一依赖 Jackson;shadow jar 产出单文件可执行 jar
- [x] 1.2 JSON-RPC stdio 主循环:换行分隔、显式 UTF-8、逐条 flush、日志只去 stderr/文件;`initialize`(回显客户端协议版本、capabilities 只声明 tools)、`notifications/*` 不回复、`ping` 回 `{}`、`id` 原样回显
- [x] 1.3 `tools/list`:9 个工具的 JSON Schema(fill、set_blocks、set_block、get_job_status、get_block、get_region_summary、get_terrain_summary、render_region、propose_site)
- [x] 1.4 `tools/call` → HTTP 翻译层(JDK `java.net.http`),token/端口从命令行参数读;业务失败 → `isError:true` + 文本;协议错误 → JSON-RPC error
- [x] 1.5 image content:HTTP 返回 PNG 字节 → base64 image block
- [x] 1.6 单测:mock HTTP server 覆盖全部工具的参数序列化与响应翻译;真实 jar 端到端协议回归通过

出口:`./gradlew test` 全绿;Phase 0.4 的假 server 换成真 bridge 后 kimi 仍可调用(用 curl 起个假 HTTP 后端配合)。

## Phase 2:aibuild-mod 骨架 + HTTP API + 异步 job —— ✅ 已完成(commit `ba5b497`,curl 8/8)

- [x] 2.1 `aibuild-mod/` Fabric 模板:MC 1.21.11、Mojang mappings、Loom 1.17-SNAPSHOT、Gradle 9.5.1、Java 21、Fabric API 0.141.5+1.21.11;`gradlew runServer` headless 验证(禁用 runClient 防弹窗)
- [x] 2.2 `BridgeHttpServer`:`com.sun.net.httpserver`,绑 127.0.0.1 随机端口、启动时生成随机 token(写 `<gameDir>/aibuild/bridge.json`);校验失败 403;所有世界操作封装成任务投递到游戏主线程执行,HTTP 线程只负责收发
- [x] 2.3 世界操作端点:`fill`、`set_blocks`(单请求 ≤4096 条目)、`set_block`、`get_block`;方块 id 走注册表校验(支持 `[state]` 语法),非法 id 返回近似名建议
- [x] 2.4 **异步 job**:写操作返回 `job_id`,主线程每 tick 放置默认 4096 块;`job_status?id=` 返回进度与**放置/失败计数**;聊天栏进度播报
- [x] 2.5 curl 集成清单:每个端点正例 + 反例(越界、坏 id、坏 token)全部过一遍

出口:进游戏后纯 curl 能放方块、查进度,主线程不卡。

## Phase 3:端到端盲盖(最小闭环)—— ✅ 已完成(commit `f199602`,M1;用户真机测试合格)

- [x] 3.1 工作目录生成:`<存档>/aibuild/` 下生成 `.kimi-code/mcp.json`、释放 bridge jar、写初版 `AGENTS.md` 与 `task.json`
- [x] 3.2 `AgentRunner`:spawn `kimi -p <短 prompt> --output-format stream-json`(命令行可配);逐行解析 stdout,assistant 文本以 `[AI]` 前缀转发聊天栏;stderr 进日志文件;session id 存 `.session_id`
- [x] 3.3 超时:双通道( stdout+stderr )静默 20min + 硬上限 60min,均可配;`/aicancel` 杀进程
- [x] 3.4 收件箱:`/aichat` 消息在建造进行中捎带于下一个工具响应(403 除外);思考期发送立即回显"[已排队]"
- [x] 3.5 `/aibuild <描述>` 命令注册;**E2E:5×5×5 石砖盒子 AI 独立完成;续聊 `kimi -r <id> -p` 放火把通过;/aicancel 通过**

出口:第一个端到端闭环跑通(盲盖,无选区无渲染)。

## Phase 4:选区杖 + 选址确认 —— ✅ 已完成(commit `fb93be6`,E2E 三路径全过;真机点击待用户验证)

- [x] 4.1 选区杖物品(RegistryKey 注册);`AttackBlockCallback`/`UseBlockCallback` 选角;聊天栏回显尺寸;选区按存档持久化(`selection-<uuid>.json`)
- [x] 4.2 写工具边界强制:有选区限选区;无选区限 `propose_site` 确认范围(越界记 `out_of_bounds` failed)
- [x] 4.3 `propose_site` 端点 + 可点击 [确认]/[拒绝] 按钮(`ClickEvent.RunCommand` 已字节码核实;真实客户端点击待验证;`/aiconfirm` `/aireject` 命令兜底可用)
- [x] 4.4 spawn 前生成 `terrain.json`(radius=64)+ `get_terrain_summary` 端点(ASCII 高度图/平坦度/候选区域)

出口:E2E 场景②(不圈地,AI 选址 + 玩家确认)通过。

## Phase 5:快照与 undo + 放置性能升级(FAWE/WE 调研已并入)

- [ ] 5.1 `Snapshot`:建造前(bounds 确定、job 开始前)`StructureTemplate#fillFromWorld` 一次性同步快照施工范围(含方块实体 NBT),存 `<世界>/aibuild/snapshots/`,留最近 10 份
- [ ] 5.2 `/aiundo`:恢复最近一次;**按 chunk 或 Y 层切片分帧恢复**(禁止原子 placeInWorld),聊天栏进度;连续 undo 无快照时友好提示;agent 运行中禁 undo
- [ ] 5.3 放置性能:毫秒预算制(默认 10ms/tick,可配)取代固定 4096 块;`setBlock` flag 3→2;按 chunk 分桶、每 chunk 完成后统一重算光照+发 chunk 包
- [ ] 5.4 chunk ticket:job 开工前给区域 chunk 拿 ticket,完工释放,不再"未加载记 failed"
- [ ] 5.5 `search_blocks(query)` mod 端点(复用建议器逻辑,供 bridge 同名工具调用)

出口:E2E 场景③(`/aichat` 修改 + `/aiundo`)通过;32³ 建造/undo 无明显卡顿。

## Phase 5.5:代码建模通道(纯 bridge 为主)

- [ ] 5.5.1 `set_blocks_from_file(path)` bridge 工具:读 JSON 条目文件(格式同 set_blocks),自动按 4096 条/批分解为多个 set_blocks 调用,汇总报告 placed/failed
- [ ] 5.5.2 `.schem` 支持:同工具接受 Sponge Schematic v2/v3(gzip NBT,~120 行只读解析;跳过 BlockEntities;DataVersion 过旧导致无法解析的调色板条目报 failed);**绝不打包任何社区 schematic(版权)**
- [ ] 5.5.3 `search_blocks(query)` bridge 工具(调 mod 新端点)
- [ ] 5.5.4 AGENTS.md 更新:生成器脚本模式(复杂几何一律写脚本 + set_blocks_from_file)、search_blocks 用法
- [ ] 5.5.5 bridge 单测全覆盖(含 .schem 解析 fixture:用 Java 代码现场生成一个合法 v2/v3 .schem 字节流)

出口:bridge 测试全绿;dev server 上 AI 用脚本+文件通道盖一个球体(如 radius=8 石砖球),零坐标搬运。

## Phase 6:渲染与数据读工具

- [ ] 6.1 **spike(提前并行)**:WorldMesh 烘焙区域 → `SimpleFramebuffer` → 自定义投影 + azimuth/elevation → `NativeImage` 读回 → `ScreenshotRecorder` 存 PNG(移植 Isometric Renders 的 MIT 模式,不依赖该 mod)
- [ ] 6.2 `render_region` 端点(渲染前确认区块已加载);bridge 侧 image content 联调
- [ ] 6.3 **V1 回退**:`BlockState#getMapColor` + `FilledMapItem` 高度着色的俯视光栅图;主方案失败自动切换
- [ ] 6.4 `get_region_summary`(方块统计 + 分层 ASCII 平面图)
- [ ] 6.5 AGENTS.md 加入"盖完必渲染自检"流程

出口:AI 能在一次 `/aibuild` 中自主调用 render 并据图修改。

## Phase 7:风格卡片与打磨

- [ ] 7.1 手写 3-5 张 baseline 风格卡片(中世纪塔楼/平原木屋/临水码头/山腰吊脚),含质量底线清单进 AGENTS.md
- [ ] 7.2 E2E 三场景全量验收(spec §11)
- [ ] 7.3 配置项收口(端口、超时、上限、agent 命令行);README 使用说明;整理 AGENTS.md

出口:按规格 §11 的验收标准全部通过。

## 里程碑视图

- **M1(Phase 0-3)**:盲盖闭环——能玩,但丑且没边界
- **M2(Phase 4-5)**:安全闭环——选区、确认、undo 齐备
- **M3(Phase 6-7)**:质量闭环——渲染自检 + 风格系统,达到"不丑"验收线
