# Minecraft AI Building — 设计文档

- 日期:2026-07-27
- 状态:已评审(两轮设计修正已并入)
- 项目代号:aibuild

## 1. 目标与非目标

**目标**:制作一个 Minecraft mod,把现成的 coding agent CLI(Kimi Code,兼容 Claude Code 等)接入游戏。玩家在游戏内用自然语言下指令,AI 利用其工具调用、规划与迭代能力,在指定范围内自动建造建筑。

**核心思路**:不做"调 LLM API + 自建生成管线"。mod 只做"工具提供者",思考全部由 coding agent 完成。

**非目标**:
- 不做 AI 人物/bot(走动、寻路、第一人称视角)——盖建筑用上帝视角,bot 只带来 token 爆炸
- 不做多人服务器权限体系(v1 纯单机)
- 不做生存模式材料校验(创造模式语义,方块凭空放置)
- 不自己实现 LLM 调用、prompt 工程框架、建筑模板库
- 不做 schematic 解析/风格蒸馏管线——风格卡片手写,蒸馏留作 V2 可选方向
- **不在 mod 里内置建筑生成算法**(WFC/形状文法等 GDMC 路线):agent 沙盒里现写生成器脚本就是程序化生成(数据由地形摘要供给,落地走 `set_blocks_from_file`);mod 只提供好数据与快通道
- **现阶段不引入小模型分工**(如 Qwen3-30B 干杂活):杂活的第一优解是确定性代码(零 token);看图自检必须多模态模型;真到用量大时再利用 Kimi Code 多 provider + sub-agent 分模型,属优化项而非架构项

## 2. 关键决策汇总

| 决策点 | 结论 |
| --- | --- |
| 版本/加载器 | Minecraft Java **1.21.11** + **Fabric**(用户最初说的 "1.12.10" 系看错;Fabric 官方不支持 1.12.x) |
| 运行形态 | 纯单机,客户端 mod(内含逻辑服务端) |
| 交互界面 | 游戏内聊天驱动:`/aibuild` 拉起无头 agent |
| AI 连接方式 | mod 起简单 HTTP API + 随 mod 分发的 stdio MCP 桥(**方案 B**) |
| 视觉反馈 | 渲染工具(AI 自选视角)+ 数据查询工具;无 bot |
| 建造范围 | 选区杖手动圈地 + AI 自选位置(需玩家确认),两种都要 |
| Agent CLI | 默认 Kimi Code(`kimi -p` 无头模式);命令行可配,兼容其他支持 MCP 的 CLI |

## 3. 总体架构

```
玩家 ──/aibuild "盖座塔"──▶ Fabric mod ──spawn──▶ kimi -p(无头 agent)
                                │                        │
                                │                        │ MCP 工具调用(stdio)
                                │                        ▼
                                │                 mc-mcp-bridge.jar
                                │                        │ HTTP 127.0.0.1(带 token)
                                │◀───────────────────────┘
                                ▼
                     主线程执行世界操作(放方块/查询/渲染)
mod ──解析 agent stdout(stream-json)──▶ 进度转发到游戏聊天栏
```

### 3.1 产物一:`aibuild` mod(Fabric, MC 1.21.11, Java 21)

内部 5 个模块,单一职责:

- **Selection**——选区杖(自定义物品)。左键点一角、右键点对角,圈定长方体;聊天栏回显选区尺寸;选区按存档持久化。
- **BridgeHttpServer**——内嵌极简 HTTP 服务(JDK 自带 `com.sun.net.httpserver`,零额外依赖)。只绑 `127.0.0.1`、每次启动随机端口 + 随机 token;所有世界操作排队到**游戏主线程**执行(MC 硬性要求)。
- **Render**——把指定区域从指定视点渲染成 PNG(详见 §8,含回退方案)。
- **Snapshot**——建造前快照选区,支持 `/aiundo`(详见 §7)。
- **AgentRunner**——准备 agent 工作目录、拉起 agent 进程、解析 stream-json 输出并转发聊天栏、管理会话与超时。

### 3.2 产物二:`mc-mcp-bridge.jar`

独立 Java 程序,打包进 mod jar 的资源里,首次运行自动释放到工作目录。作为 stdio MCP server 被 agent 拉起,把 MCP 工具调用翻译成 mod 的 HTTP 请求,把结果(含 PNG 图片,走 MCP image content)翻译回 MCP 响应。无 MC 依赖,可独立单元测试。用户玩 MC 必有 Java,零额外环境要求。

**实现方式(调研定案)**:**手写换行分隔 JSON-RPC 2.0**(Jackson + stdin/stdout,约 300 行),不用官方 Java SDK(会拖入 Reactor + Jackson 3,shaded 约 5.5MB,为 8 个工具不值得)。协议要点:stdout 只走协议消息(日志一律 stderr/文件)、Windows 显式 UTF-8、每条消息 flush、`ping` 回 `{}`、通知类消息不回复、`id` 原样回显、业务错误返回 `isError:true` 的正常 result(让 AI 能自我纠正)而非 JSON-RPC error、`initialize` 时协议版本回显客户端版本、capabilities 只声明 `{"tools":{}}`。

### 3.3 产物三:agent 工作目录(每存档一个,自动生成)

位于 `<存档>/aibuild/`,mod 自动维护:

- `.kimi-code/mcp.json`——项目级 MCP 配置,stdio 方式指向 bridge jar(带端口与 token 参数)
- `AGENTS.md`——施工规范:坐标系说明、边界约束、工具用法、"先规划、自下而上、盖完渲染自检"的流程要求(Kimi Code 启动时自动加载)
- `task.json`——本次任务:玩家描述、选区/确认范围、限制参数
- `terrain.json` + ASCII 高度图——spawn 前由 mod 生成的周边地形摘要(高度图/水体/坡度/平坦度)
- `styles/`——风格卡片目录(见 §5.4),mod 首次运行释放 3-5 张 baseline 卡片
- `prompt.txt` 等中间产物、agent 自己的图纸文件

**prompt 组装原则**:`kimi -p` 的 prompt 永远只有一两句("阅读本目录 AGENTS.md 与 task.json,按任务施工"),所有大内容全是文件,AI 用自己的 Read 工具读。命令行永远几百字符,彻底避开 Windows 命令行长度上限(/cmd 8191、CreateProcess 32767)。

## 4. 玩家交互

玩家侧只有 1 把杖 + 4 条命令:

| 入口 | 行为 |
| --- | --- |
| 选区杖 | 左键一角、右键对角;有选区时施工严格限制在选区内 |
| `/aibuild <描述>` | 发起建造;无选区时进入 AI 选址两阶段流程 |
| `/aichat <话>` | 修改/续聊(同一会话,AI 带全部记忆);建造进行中说的话捎带给 AI |
| `/aiundo` | 撤销上一次建造,恢复快照 |
| `/aicancel` | 杀 agent 进程;已放方块保留,可再 `/aiundo` |

### 4.1 一次建造的完整流程

1. mod 校验:无 agent 在跑、选区体积 ≤ 上限 → 快照选区;
2. **AI 选址两阶段确认**(仅无选区时):AI 已读过 terrain.json,第一个工具调用必须是 `propose_site(范围)`;mod 把范围发到聊天栏并附**可点击 [确认] 按钮**(MC 聊天栏点击事件执行命令),玩家确认前写工具锁定;
3. AgentRunner 刷新工作目录 → spawn `kimi -p "<短 prompt>" --output-format stream-json`,cwd = 工作目录;
4. agent 施工:调 MCP 工具 → bridge → HTTP → mod 主线程执行 → 返回;
5. agent 的文本输出被 mod 逐条解析,以 `[AI]` 前缀转发聊天栏;
6. **建造中插话**:`/aichat` 的消息进收件箱,**捎带在下一个工具调用的返回值里**送达(附"玩家有 N 条新消息");若 AI 正在思考,聊天栏立即回显"[已排队,AI 下次行动时送达]",不装死;
7. agent 退出 → 聊天栏报告完成/失败 → 快照保留,`/aiundo` 可撤销。

## 5. MCP 工具集

原则:**批量优先、读操作省 token、写操作全异步**。写工具的返回(job 完成后经 `get_job_status` 或结果摘要)必须回显**放置/失败计数**——前人项目的经典投诉是"静默部分失败",AI 需要知道自己哪步没成功。

### 5.1 写工具(返回 `job_id`,后台分帧执行;越界直接拒绝)

| 工具 | 说明 |
| --- | --- |
| `fill(box, block, mode)` | 主力,语义对齐原版 `/fill`(replace/keep/outline/hollow) |
| `set_blocks([{x,y,z,block}...])` | 批量精细操作;**单次请求 ≤ 4096 条目**(防 JSON 包过大;一个 job 可由多次请求累积) |
| `set_block(x,y,z,block)` | 单块修补 |
| `set_blocks_from_file(path)` | **代码建模通道**(bridge 本地工具,mod 零改动):AI 的沙盒脚本把坐标写成 JSON 文件(同 set_blocks 条目格式),bridge 读文件自动按 4096 条/批分解为多个 set_blocks 调用;**同时支持 `.schem` 文件**(Sponge v2/v3,~120 行只读解析,调色板字符串与 BlockSpecParser 同格式;跳过 BlockEntities;无法解析的调色板条目报 failed)。LLM 不再搬运大批量坐标——复杂几何(球/拱/曲面屋顶)一律写成生成器脚本走此通道 |
| `get_job_status(job_id)` | 查 job 进度 |

### 5.2 读工具(同步返回)

| 工具 | 说明 |
| --- | --- |
| `get_block(x,y,z)` | 点查询 |
| `search_blocks(query)` | 注册表模糊搜索方块 id(复用建议器逻辑),回答"有哪些颜色的玻璃"这类问题,省 token |
| `get_region_summary(box)` | 方块统计 + 每层 ASCII 平面图(不给全量坐标流,省 token) |
| `get_terrain_summary(center, radius)` | 高度图/水体/坡度/平坦度(spawn 前 mod 已自动给了一份周边摘要,此工具用于查看别处) |
| `render_region(box, {azimuth, elevation})` | 渲染 PNG,走 MCP image content 直接回 AI 上下文;视角参数 AI 自选,默认 45° 等轴 |

### 5.3 流程工具

| 工具 | 说明 |
| --- | --- |
| `propose_site(box)` | 无选区时的第一个调用;触发玩家确认,确认前写工具锁定 |

不设 `get_constraints`、`report` 等冗余工具——任务约束在 task.json,进度汇报走 stdout 转发。

### 5.4 风格系统(约束,不是形容词)

LLM 自由发挥盖出来的建筑大概率是"盒子+尖顶",风格必须以**可量化参数**表达,而不是 prompt 形容词。

- **风格卡片**:JSON 文件,含材料白名单(primary/secondary/accent)、高宽比范围、屋顶类型与悬挑、开窗节奏、装饰件(扶壁/垛口/火把间距等);
- **存放与匹配**:卡片在工作目录 `styles/` 下,AI 用自己的文件工具读取、按任务自行匹配;**mod 不写任何匹配逻辑**;
- **baseline**:首次运行释放 3-5 张手写卡片(中世纪塔楼/平原木屋/临水码头/山腰吊脚等),由开发者直接编写——不做 schematic 解析蒸馏管线(V2 可选);
- **风格变更**:AI 想突破卡片约束,用文字提出,玩家 `/aichat` 回复——复用现有通道,不加专用工具;
- **沉淀新风格**:玩家说"这个风格存起来",AI 用自己的文件工具把当前参数写成新卡片——零 mod 代码;
- **质量底线**(写进 AGENTS.md 施工规范):比例不畸形(高宽比 1:1~4:1)、屋顶与墙体材质区分、开窗有节奏不随机、材料呼应地形(森林木/沙漠砂岩/雪地云杉)、底部与地形衔接不浮空不半埋。

## 6. 异步 job 与快照/undo

- **所有写操作都是异步 job**:工具调用立即返回 `job_id`,mod 后台**分帧执行**,聊天栏显示进度。
- **放置性能**(FAWE/WorldEdit 调研定案):
  - **毫秒预算制**:每 tick 放置预算默认 10ms(可配),花多少放多少,自适应 TPS——取代固定块数;
  - **flag 2 + chunk 分桶**:放置用 `setBlock(pos, state, 2)`(抑制逐块邻居更新/客户端通知),放置按 chunk 分桶,每完成一个 chunk 统一重算该 chunk 光照并发一次 chunk 包——取代逐块 flag 3 的最差路径;
  - **chunk ticket**:job 开工前给区域所有 chunk 拿 ticket 保证加载,完工释放——不再"未加载记 failed";
  - 直接 `LevelChunkSection` 写入是进一步优化,现阶段不做(YAGNI,先测毫秒预算够不够)。
- **快照**:建造前(bounds 确定后、job 开始前)用**原版 StructureTemplate#fillFromWorld** 对施工范围一次性同步快照——调色板 + 索引数组,方块实体 NBT 免费带上,保存快;存 `<世界>/aibuild/snapshots/`,留最近 10 份。API 无 48³ 限制(那只是结构方块 UI 限制)。
- **undo**:`/aiundo` 恢复最近一次快照;**禁止原子 placeInWorld 26 万块**——按 chunk 或 Y 层切片,在毫秒预算内分帧恢复,聊天栏显示进度。

## 7. 视觉反馈:渲染

- **主方案**(调研定案,难度中等):照 [Isometric Renders](https://github.com/gliscowo/isometric-renders)(MIT,可合法借鉴;官方支持到 1.21.4,我们移植其模式而非依赖)的管线——**WorldMesh 把区域烘焙成网格 → `SimpleFramebuffer` 离屏渲染 → 自定义投影矩阵 + 方位角/仰角旋转 → `NativeImage` 读回像素**,PNG 写出用原版 `ScreenshotRecorder`。画面与玩家亲眼所见一致(有光照有材质)。约束:目标区域区块必须已在客户端加载(单机 + 玩家附近天然满足;渲染前可强制加载)。ReplayMod 是 GPL,只能参考思路,不能抄代码。
- **回退方案**(渲染管线失败时自动切换,保证"看图"永远可用):
  - **V1 回退:俯视光栅图**——原版自带方块→颜色表(`BlockState#getMapColor`)+ 地图高度着色逻辑(参考 `FilledMapItem#updateColors`),无需自写投影,复杂度比预想更低;
  - **V2 回退:等轴软件投影**——主链路跑通后再做。

## 8. 会话续聊

- `/aichat` = 在**同一 agent 会话**上继续,AI 记得之前盖了什么。
- **已实测通过(kimi 0.29.2)**:stream-json 的 meta 行直接给出 session id 和续聊命令(`{"role":"meta","type":"session.resume_hint","session_id":"...","command":"kimi -r ..."}`)。
- **首选 `kimi -r <session_id> -p "<消息>"`**:mod 解析 meta 行存下 session id(写工作目录 `.session_id` 兜底),显式续聊,不受"目录最近会话"歧义影响;
- **fallback `kimi -c -p "<消息>"`**(续当前目录最近会话):同样实测通过,工作目录固定所以天然匹配。
- 注意:`-c` 与 `-r`/`-S` 互斥,不能组合;不带 `-p` 会进 TUI,不是无头。

## 9. 超时与错误处理

### 9.1 agent 进程超时(双阈值)

- **静默超时**:默认 **20 分钟**(可配)。口径 = **stdout+stderr 双通道无任何字节**。**已实测**:stream-json 只发完整消息、无增量输出,无工具调用时 stderr 全空——一次数分钟的长回复期间双通道真的全程静默,这是常态不是卡死;阈值宽松是必要的,不能依赖 stderr 做活性判断。
- **硬上限**:默认 60 分钟(可配),到点杀掉并提示可 `/aichat` 继续。

### 9.2 其他错误处理

- agent 崩溃/非零退出 → 聊天栏报错,完整输出留档工作目录,可 `/aichat` 继续;
- HTTP API:校验失败一律 403;
- 非法方块 id → 报错并列出近似名,防 AI 瞎猜;
- 渲染失败 → 自动切回退方案(§7);
- bridge 崩溃:它是 agent 的子进程,AI 会收到工具错误并自行重试;mod 侧 HTTP 服务不受影响;
- 世界一致性:所有操作在主线程、区块标 dirty,走原版保存;快照文件存存档目录。

## 10. 安全与限制(单机场景,AI 是唯一风险源)

- 写工具强制边界:选区内,或玩家确认过的 `propose_site` 范围内;
- **选区体积上限**默认 64³ = 262144(可配);
- **单 job 方块上限**默认 = 选区体积上限(262144),两者同源可配;
- `set_blocks` 单请求 ≤ 4096 条目(请求体大小限制,与 job 上限是两个层面);
- `/aiundo` 兜底一切误操作;
- agent 进程 cwd 限定在工作目录;`kimi -p` 默认 auto 权限,静态 deny 规则仍生效;
- **schematic 版权红线**:Planet Minecraft 等社区作品默认保留所有权利——`.schem` 只做"用户自行导入",**本项目绝不打包/分发任何社区 schematic 文件**。

## 11. 测试策略

- **mc-mcp-bridge**:纯 Java 无 MC 依赖,是全场最适合自动化的部分——mock HTTP server 单测 MCP↔HTTP 翻译;
- **mod HTTP API**:开发环境进游戏,用 curl 把每个端点打一遍(集成测试清单);
- **端到端验收 3 场景**:
  1. 圈选区盖小房子;
  2. 不圈地,AI 选址 + 玩家确认流程;
  3. `/aichat` 修改 + `/aiundo` 撤销。

## 12. 技术风险与实施顺序

风险排序(决定实施顺序):

1. ~~**续聊验证**~~ —— ✅ 已排除(Phase 0):`-r <id> -p` 与 `-c -p` 均实测通过;session id 由 stream-json meta 行直接给出;
2. **离屏渲染 PNG**——调研已把难度从"高"降为"中等"(WorldMesh + 离屏 framebuffer,MIT 模式可移植),仍需早期 spike;失败立刻切 V1 软件回退,不恋战;
3. ~~**bridge 与 Kimi Code 的 MCP 握手**~~ —— ✅ 已排除(Phase 0):手写 JSON-RPC server 与 kimi 0.29.2 握手、并行工具调用、image content 回传全部实测通过;
4. **可点击聊天事件 API**——`propose_site` 的 [确认] 按钮依赖聊天栏点击事件,该 API 在 1.21.5 时代有改动(调研未能确认现状),实现时实测,不行就退回"输入 `/aiconfirm` 确认"。

建议实施顺序:续聊验证 → HTTP API + curl 联通 → bridge + kimi 端到端盲盖 → 选区杖 + propose_site → 快照/undo → 渲染(spike 提前并行做)→ AGENTS.md 施工规范与 baseline 风格卡片编写 → 打磨。

## 13. 工具链版本(调研定案,2026-07-27 核实)

| 项 | 版本 |
| --- | --- |
| Minecraft | 1.21.11 |
| 映射 | **Mojang 官方映射**(Yarn 止于 1.21.11,26.1+ 官方不混淆;官方模板已默认 mojmap,跟随模板不自行迁移) |
| Fabric Loader | 0.19.3 |
| Fabric API | 0.141.5+1.21.11 |
| Fabric Loom | 1.17-SNAPSHOT(Gradle 9.5.1,Java 21) |
| 快照 API(mojmap) | `StructureTemplate#fillFromWorld` / `placeInWorld` + `StructurePlaceSettings` |
| Agent CLI | Kimi Code CLI ≥ 0.29.2(官方 PowerShell 安装脚本;与 Kimi 桌面版共享 `~/.kimi-code` 登录态;`kimi` 需在 PATH) |

已知版本坑(1.21.1→1.21.11):物品注册必须带 `RegistryKey`(1.21.2+);`Entity#getWorld` → `getEntityWorld`(1.21.9+);聊天 Text 点击事件 API 有改动(见风险 4)。

## 14. 仓库结构(monorepo)

```
minecraft-ai-building/
├── docs/
│   └── specs/
│       └── 2026-07-27-minecraft-ai-building-design.md   ← 本文档
├── mc-mcp-bridge/     # bridge 源码(独立 Gradle 模块)
├── aibuild-mod/       # Fabric mod 源码
└── README.md
```
