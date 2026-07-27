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

### 3.3 产物三:agent 工作目录(每存档一个,自动生成)

位于 `<存档>/aibuild/`,mod 自动维护:

- `.kimi-code/mcp.json`——项目级 MCP 配置,stdio 方式指向 bridge jar(带端口与 token 参数)
- `AGENTS.md`——施工规范:坐标系说明、边界约束、工具用法、"先规划、自下而上、盖完渲染自检"的流程要求(Kimi Code 启动时自动加载)
- `task.json`——本次任务:玩家描述、选区/确认范围、限制参数
- `terrain.json` + ASCII 高度图——spawn 前由 mod 生成的周边地形摘要(高度图/水体/坡度/平坦度)
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

原则:**批量优先、读操作省 token、写操作全异步**。

### 5.1 写工具(返回 `job_id`,后台分帧执行;越界直接拒绝)

| 工具 | 说明 |
| --- | --- |
| `fill(box, block, mode)` | 主力,语义对齐原版 `/fill`(replace/keep/outline/hollow) |
| `set_blocks([{x,y,z,block}...])` | 批量精细操作;**单次请求 ≤ 4096 条目**(防 JSON 包过大;一个 job 可由多次请求累积) |
| `set_block(x,y,z,block)` | 单块修补 |
| `get_job_status(job_id)` | 查 job 进度 |

### 5.2 读工具(同步返回)

| 工具 | 说明 |
| --- | --- |
| `get_block(x,y,z)` | 点查询 |
| `get_region_summary(box)` | 方块统计 + 每层 ASCII 平面图(不给全量坐标流,省 token) |
| `get_terrain_summary(center, radius)` | 高度图/水体/坡度/平坦度(spawn 前 mod 已自动给了一份周边摘要,此工具用于查看别处) |
| `render_region(box, {azimuth, elevation})` | 渲染 PNG,走 MCP image content 直接回 AI 上下文;视角参数 AI 自选,默认 45° 等轴 |

### 5.3 流程工具

| 工具 | 说明 |
| --- | --- |
| `propose_site(box)` | 无选区时的第一个调用;触发玩家确认,确认前写工具锁定 |

不設 `get_constraints`、`report` 等冗余工具——任务约束在 task.json,进度汇报走 stdout 转发。

## 6. 异步 job 与快照/undo

- **所有写操作都是异步 job**:工具调用立即返回 `job_id`,mod 后台**分帧执行**(每 tick 放 N 块),聊天栏显示进度。10 万方块级操作不会冻结游戏。
- **快照**:建造前用**原版结构方块机制(StructureTemplate)**对施工范围做快照——调色板 + 索引数组,保存快、恢复带方块实体处理,不手写 BlockChange 列表。
- **undo**:`/aiundo` 分帧恢复快照,聊天栏显示进度。

## 7. 视觉反馈:渲染

- **主方案**:用游戏自身渲染管线,从任意视点离屏渲染到 framebuffer,读回像素存 PNG——画面与玩家亲眼所见一致(有光照有材质)。
- **回退方案**(渲染管线失败时自动切换,保证"看图"永远可用):
  - **V1 回退:俯视平面图**(XZ 平面 + 高度着色/标注)——一天能写完的复杂度,不挖新坑;
  - **V2 回退:等轴软件投影**——主链路跑通后再做。

## 8. 会话续聊

- `/aichat` = 在**同一 agent 会话**上继续,AI 记得之前盖了什么。
- 首选 `kimi -c -p "<消息>"`(`-c` 续当前目录最近会话,工作目录固定所以天然匹配);文档未明文禁止该组合,但也未定义行为,**实施第一步必须实测**。
- fallback:`kimi -S <session_id> -p "<消息>"`;session id 从 stream-json 输出或 kimi 会话存储目录取得,写入工作目录 `.session_id`。
- 注意:`-c` 与 `-S` 互斥,不能组合;不带 `-p` 会进 TUI,不是无头。

## 9. 超时与错误处理

### 9.1 agent 进程超时(双阈值)

- **静默超时**:默认 **20 分钟**(可配)。口径 = **stdout+stderr 双通道无任何字节**。注意:stream-json 模式明文不写 thinking 内容,深度推理期间可能真的全程无事件,所以阈值要宽松;实施 spike 需实测"推理期间 stderr 是否有活动",若无则依赖宽松阈值兜底。
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
- agent 进程 cwd 限定在工作目录;`kimi -p` 默认 auto 权限,静态 deny 规则仍生效。

## 11. 测试策略

- **mc-mcp-bridge**:纯 Java 无 MC 依赖,是全场最适合自动化的部分——mock HTTP server 单测 MCP↔HTTP 翻译;
- **mod HTTP API**:开发环境进游戏,用 curl 把每个端点打一遍(集成测试清单);
- **端到端验收 3 场景**:
  1. 圈选区盖小房子;
  2. 不圈地,AI 选址 + 玩家确认流程;
  3. `/aichat` 修改 + `/aiundo` 撤销。

## 12. 技术风险与实施顺序

风险排序(决定实施顺序):

1. **续聊验证**(`-c -p` vs `-S <id> -p`;thinking 在 stream-json 下的可观测性)——纯命令行实验,最先做;
2. **离屏渲染 PNG**——mod 内最大技术风险,早期 spike,失败立刻切 V1 软件回退,不恋战;
3. **bridge 与 Kimi Code 的实际 MCP 握手**——协议细节(初始化、image content 返回)以实测为准。

建议实施顺序:续聊验证 → HTTP API + curl 联通 → bridge + kimi 端到端盲盖 → 选区杖 + propose_site → 快照/undo → 渲染(spike 提前并行做)→ 打磨。

## 13. 仓库结构(monorepo)

```
minecraft-ai-building/
├── docs/
│   └── specs/
│       └── 2026-07-27-minecraft-ai-building-design.md   ← 本文档
├── mc-mcp-bridge/     # bridge 源码(独立 Gradle 模块)
├── aibuild-mod/       # Fabric mod 源码
└── README.md
```
