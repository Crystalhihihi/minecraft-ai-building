# 量化数据审计（minecraft-ai-building，2026-08-13）

> 审计范围：项目全部游戏侧建造会话（91 个，2026-07-30 23:44 → 2026-08-10 17:22 本地时间）+ 建制前可辨认的 E0/E2 wire 记录。
> 数据源（全部为只读取证）：
> ① 游戏侧 `saves/<世界>/aibuild/sessions.json`（mod 落盘的每会话 stats：轮次/调用/方块/墙钟/token 三项）；
> ② kimi CLI 会话存储 `C:/Users/zengd/.kimi-code/sessions/wd_<目录>_<hash>/<kimi_session_id>/agents/*/wire.jsonl` 的 `usage.record` 行（每次 LLM 调用一条，含 model 字段，=mod 账单的原始来源，见 `aibuild-mod/src/main/java/com/aibuild/mod/agent/TokenUsage.java:49-99`）；
> ③ 游戏侧 `sessions/s<N>/logs/agent-*.log`（stream-json stdout）；
> ④ `docs/experiments.md`、`docs/HANDOFF.md`、mod 源码注释。
> token 口径（与 mod 完全一致，TokenUsage.java:25-27）：输入 = inputOther + inputCacheCreation；输出 = output；缓存 = inputCacheRead。墙钟口径 = sessions.json `stats.wall_ms`（本地时间戳来自 `created_at`）。
> 对账验证：82/91 会话可定位 wire；其中 70 个 wire 汇总与 sessions.json 逐 token 一致，9 个 sessions.json 比 wire 多记 20-27k 输入（详见末节"数据质量"），E9 文档数与 wire 逐位吻合（见 §1.4）。

## 1. 成本重算：K2 错误旧账 vs K3 真实新账

### 1.1 定价证据

| 指标 | 数值 | 证据 |
| --- | --- | --- |
| 旧账口径（Kimi 档） | 输入 ¥4/M、输出 ¥16/M、缓存读 ¥1/M | `aibuild-mod/.../AgentRunner.java:655-656` 注释"其余按 Kimi K2 量级价"，:660-663 公式；`docs/HANDOFF.md:9` |
| Kimi K2 官方价 | 输入 ¥4/M、输出 ¥16/M、缓存命中 ¥1/M | Moonshot 官方公告（platform.moonshot.cn 上架价），见腾讯新闻/知乎转载："每百万 Token 输入 4 元，输出 16 元，命中缓存的输入为 1 元"（news.qq.com/rain/a/20251110A0244A00；zhuanlan.zhihu.com/p/1969908447005873171）——与旧账口径一致，旧账确实按 K2 刊例 |
| Kimi K3 官方价（真实用模型） | 输入 ¥20/M（未命中）、缓存命中 ¥2/M、输出 ¥100/M；$3.00/$0.30/$15.00 | 多来源引 Moonshot 官方定价：segmentfault.com/a/1190000048143515（"输出¥100/输入¥20/缓存命中¥2"）；xn--mcs150c49js1e.cn（$3/$0.30/$15 对照表）；blog.csdn.net/ylscode/article/details/162975689（官方文档+独立验证） |
| deepseek/v4-flash 档 | 输入 ¥1/M、输出 ¥2/M、缓存读 ¥0.02/M | 项目自记"2026-08 官价"：AgentRunner.java:655；HANDOFF.md:9 |
| 实际使用的模型（wire 证据） | k3/k3-256k 59 会话、kimi-for-coding(K2.7) 5 会话、deepseek/v4-flash 16 会话、无 wire 11 会话 | 各 wire.jsonl `usage.record.model` 字段；汇总命令输出见 §1.2 |

结论：Kimi 档会话实际跑的是 K3（wire 的 model 字段逐条为 `kimi-code/k3` / `kimi-code/k3-256k`），旧账却按 K2 刊例 ¥4/¥16/¥1 估算；K3 刊例为 ¥20/¥100/¥2，即输入 5×、输出 6.25×、缓存 2×。例外：E4 首轮 5 个 worker 会话实为 `kimi-code/kimi-for-coding`（K2.7），其 K2 档估价与 K2.7 量级大体相符（且当时走 managed 套餐、边际成本为 0），新旧两账保持不变。

### 1.2 总账（91 个游戏建造会话，07-30 23:44 → 08-10 17:22）

| 指标 | 数值 | 证据 |
| --- | --- | --- |
| token 总量 | 输入 5,088,607 / 输出 1,650,524 / 缓存读 180,275,619 | 审计脚本对 82 个 wire.jsonl 的 `usage.record` 逐行求和（9 个无 wire 会话按 sessions.json stats 补，均为 0） |
| 旧账合计（按 K2 档记 Kimi 系） | **¥144.23** | 同上 token × ¥4/¥16/¥1（Kimi 系）+ ¥1/¥2/¥0.02（flash 16 会话 ¥4.48 不变） |
| 新账合计（K3 真实价） | **¥345.28** | 同上 token × ¥20/¥100/¥2（59 个 K3 会话）；K2.7 5 会话 ¥24.48 与 flash ¥4.48 不变 |
| 差距 | **2.39×（少记 ¥201.05）** | 计算：345.28/144.23 |
| 其中 K3 会话子账（59 个） | 旧 ¥115.27 → 新 **¥316.31**（2.74×） | 59 会话 wire 汇总：输入 3,013,769 / 输出 729,557 / 缓存 91,540,885 |
| 单次建造成本（done 且 blocks>0，n=57） | 旧均 ¥2.11/栋 → 新均 **¥4.84/栋**；单栋区间 ¥0.59–¥33.01 | 57 个 done 会话逐栋换算；最大单栋=新的世界（4) s10 橡木别墅（124 轮/50.8min/5,776 块，新账 ¥33.01，ksid=session_ef75733a-…） |
| 对比：项目既有记录 | "非套餐折合约 50 元/建筑"（2026-07-31 晚用户修正） | `docs/HANDOFF.md:204`；实测 K3 刊例均值 ¥4.84/栋，该记录高估约 10 倍 |
| 建造总量 | 57 栋建成会话共 1,522,409 块，平均墙钟 13.5 min | sessions.json stats.blocks_placed / wall_ms 汇总 |

### 1.3 标志性建造的单次成本（旧账 vs 新账）

| 指标 | 数值 | 证据 |
| --- | --- | --- |
| E2 单 agent 基线（07-30，K3，庄园） | 36 次 LLM 调用；输入 77,248 / 输出 20,419 / 缓存 2,456,126；旧账 ¥3.09 → **新账 ¥8.50** | wire：`wd_aibuild_79150e6e8a0c/session_d91c400a-2ddb-4616-83e5-b40a963ba242`（36 条 usage.record，22:24–22:40 本地，model=kimi-code/k3；内容关键词 幕墙×45/门楼×42/垛口×44/庄园×7，与 docs/experiments.md:20-24 的 E2 记载吻合；E2 早于 sessions.json 建制，docs 无 token 记录，此为补齐数据） |
| E4 首轮（07-31，4×K2.7 worker） | 四区合计旧账 ¥23.70（10.16+4.86+3.90+4.78）；新旧同价（K2.7 档） | sessions.json DEVSERVER s13-s16 stats + wire（model=kimi-code/kimi-for-coding）；轮块数据与 experiments.md:38 一致 |
| E4 复赛（07-31，3×K3 worker） | 三人合计旧账 ¥9.36 → **新账 ¥28.69**（6.59+10.66+11.44） | sessions.json DEVSERVER s17-s19 + wire（model=kimi-code/k3）；轮块数据与 experiments.md:52 一致 |
| 典型 K3 大树（08-06→08-08，n=15 棵 done） | 新账均价 **¥5.75/棵**（¥3.15–¥14.52），均时 17.2 min | 世界（4)-(12) 各 sessions.json + wire；清单见 §3 |
| 典型 flash 大树（08-08→08-10，n=14） | **¥0.16–¥0.40/棵，均值 ¥0.20**（两账同价，该档 08-08 已分档） | 世界（13)-(16) sessions.json + wire（model=deepseek/v4-flash） |

### 1.4 管线自检（wire 数据可信度）

| 指标 | 数值 | 证据 |
| --- | --- | --- |
| E9 文档账 vs wire 重算 | 文档"合计全价输入 121k + 缓存读 2.52M + 输出 8k"（experiments.md:141）；wire 重算 = 输入 120,912 / 缓存 2,519,040 / 输出 8,131 | DEVSERVER s27-s34 wire 逐条求和，三项均吻合（输入差 0.07% 为文档约数） |
| wire ↔ sessions.json 一致性 | 82 个可定位会话中 70 个逐 token 一致；9 个 sessions.json 多记 20-27k 输入；3 个 sessions.json 有账但 wire 已不可考按 sessions.json 计 | 对账脚本输出；差异会话：世界（10)s1、(12)s1、(4)s4/s7、(5)s1、(6)s1、(7)s1、(8)s1、(9)s1 |
| 既有消耗口径记录 | "正常建造 20-60k 全价输入 + 1-10k 输出/把，缓存命中 89-97%" | experiments.md:135；与 wire 分布一致（多数 done 会话输入 2.5 万-13 万、输出 4k-65k、缓存占比 90%+） |

## 2. deepseek/v4-flash：08-08 前后对比

### 2.1 之前（仅 E6 两次，2026-07-31 晚）

| 指标 | 数值 | 证据 |
| --- | --- | --- |
| 任务 | s1 处理组（照 spec 建深色云杉木屋）/ s2 对照组（常规流程照图施工） | experiments.md:72-75；sessions.json 新的世界（3) s1/s2 |
| 成功率 | 2/2 done（均建成放置，非"跑不起来"） | sessions.json 状态；s1 ksid=session_7027ddb1-…、s2 ksid=session_9c5c0a19-…（wire model=deepseek/v4-flash） |
| 墙钟 | s1 26.7min/27 轮/833 块；s2 24.1min/40 轮/1,448 块 | sessions.json stats（与 experiments.md:74-75 一致） |
| token/成本 | 两会话合计：输入 324,904 / 输出 323,984 / 缓存 10,975,744；成本 ¥0.60 + ¥0.59（flash 档两账同价） | 两条 wire 的 usage.record 求和 × ¥1/¥2/¥0.02 |
| 速度画像 | 单次 LLM 调用平均流式时长 **35.3s**（83 次调用）；曾单条响应连写 77.9k token/12.3min（"假死"） | wire step.end.llmStreamDurationMs 汇总；experiments.md:74 |
| 质量判决 | 用户叫停 v2"已经乱七八糟"；E6 总结#5："极限论需重测：E6 质量数据全部来自 deepseek/v4-flash（配置漏设），非 K3" | experiments.md:89、:101 |

### 2.2 之后（2026-08-08 15:00 → 08-10 17:22，模型正式切换后）

| 指标 | 数值 | 证据 |
| --- | --- | --- |
| 切换动作 | 08-08 14:57 jar 部署 + 游戏 config 切 `deepseek/v4-flash`（原 k3-256k） | HANDOFF.md:9；`…/1.21.11-aibuilding-test/aibuild/config.json` 实测 `"agent_model": "deepseek/v4-flash"` |
| 任务/成功率 | 14 个建造会话（地标树/庭院树/樱花树/雪原树等），**14/14 done、0 failed、0 自愈**；另 1 个 intake 问答被用户 0.8min 取消（世界（14)s7，非模型失败） | sessions.json 世界（13)s1-s3、(14)s1-s8、(15)s1、(16)s1-s3；wire model 全为 deepseek/v4-flash |
| 墙钟 | 4.8–12.3 min，**均值 7.9 min** | 同上 stats.wall_ms |
| 产出 | 合计 632,392 块（单棵最大 98,526 块=世界（14)s4 樱花树，8.5min） | 同上 stats.blocks_placed |
| token/成本 | 合计输入 1,286,459 / 输出 422,485 / 缓存 57,923,584；**单棵 ¥0.16–¥0.40，均值 ¥0.24，14 棵共 ¥3.30** | wire 求和 × flash 档价 |
| 速度画像 | 单次 LLM 调用平均流式时长 **6.2s**（570 次调用），较 E6 时期的 35.3s 快 5.7×；首 token 0.5s | wire step.end 汇总 |
| 对照：同期 K3 建树 | 15 棵 done 均值 17.2min / 新账 ¥5.75；flash 比之**快 2.2×、便宜约 96%** | §1.3 同口径 |
| 日志健康度 | 抽查 s1/s4/s8/s3 等日志无 API 级 429/鉴权/超时失败（仅工具脚本自身 stderr 噪音，如 chrome 安装失败、JSONDecodeError） | `sessions/s<N>/logs/agent-*.log` grep 'error\|429\|failed\|exception' 输出 |

### 2.3 关于"08-08 之前完全不可用"的核查结论

日志与文档**不支持**"之前完全不可用（跑不起来）"：08-08 前该模型仅有 E6 两次使用且均 done 建成。可考的负面记录是"慢"（单次流式 35.3s、77.9k token 假死）与"质量不被采信"（v2 叫停、"极限论需重测"）。"完全可用、又快又准"的后半有数据支撑（14/14 成功、7.9min 均值、6.2s/调用、¥0.24/棵）；"准"无机器验收分（树不跑 walkability/flatness），仅有用户连续复用 16 次、零 failed 的行为证据。

## 3. HANDOFF 封存（08-08）之后的新运行（只有日志、无文档）

口径：`created_at ≥ 2026-08-08 00:00` 本地的游戏会话共 **20 个**（19 done + 1 cancelled），横跨世界（10）至（16)。docs 内零记载（grep `新的世界 (1x)`/`08-08` 仅命中 HANDOFF.md:8-11 的部署与计划，无任何运行记录）。

| 指标 | 数值 | 证据 |
| --- | --- | --- |
| 会话数/成功率 | 20 个（19 done，1 cancelled=世界（14)s7 intake 0.8min） | 各世界 sessions.json |
| 世界（10)-(12)（K3，08-08 00:08–12:32，封存当夜边界） | 5 会话全 done：s1 74,246 块/28.1min；s1 50,239/12.1；s2 44,609/7.8；s1 114,820/10.0；s2 18,875/10.1；新账成本 ¥4.69/5.92/5.18/5.58/6.50 | 各 sessions.json + wire（model=kimi-code/k3-256k） |
| 世界（13)-(14)（flash 切换首日，08-08 15:00–16:45） | 10 建造会话全 done，共 487,047 块 | 同上（model=deepseek/v4-flash） |
| 世界（15)-(16)（08-08 17:37、08-10 17:06–17:22，完全无文档） | 4 会话全 done：76,285 块/7.0min；63,085/6.8；2,772/4.8；3,203/12.3min（雪樱花 S 形主干，81 轮） | 同上；(16)s3 ksid=session_06ceac40-… |
| 封存后合计 | 935,181 块；K3 段新账 ¥27.87 + flash 段 ¥3.30 = **¥31.17**；均时 9.0min | 审计汇总（summary.json post_seal） |
| 产物 | 每会话目录含 intake_brief.md/build_order.json/renders（topdown+gl）/logs，渲染 PNG 时间戳与会话一致 | 如 `世界(14)/sessions/s4/renders/render_20260808_162039_307_topdown.png` |

## 4. 可直接用于简历的表述

- 搭建 Minecraft 多 agent 自动建造系统（Fabric mod + MCP bridge + kimi CLI 子进程编排），K3 单 agent 16.1 分钟建成 42×32 中世纪庄园（36 轮/52 调用，实测 token 成本 ¥8.50）。
- 设计 planner-worker 并行建造：K3 planner + 3 worker 以 25.9 分钟/83 轮完成 3 倍体量临水镇（27,218 块），纠正首轮 4 并发方案 28.3 分钟/218 轮的败局，并行效率首次跑通。
- 实现基于 stream-json wire 解析的 token 账单管线（90%+ 缓存命中），57 栋建成会话共放置 152 万块，单栋实测成本均值 ¥4.84（K3 刊例）。
- 主导游戏 agent 模型切换至 deepseek/v4-flash：14/14 建造成功，单棵地标树均值 7.9 分钟、¥0.24，较 K3 方案快 2.2×、单次成本降约 96%。
- 跑通 8 连跑 plan-only 重复性实验（合计 2.52M 缓存 token/¥8 量级），用 Jaccard/CV/众数三指标量化并定位 AI 建造 mode collapse 边界。
- 建立"访谈→风格卡→抽签→生成器→机器验收→渲染自检"全链路，walkability 验收 8/8 全通，建造瓶颈量化证明在模型延迟而非放置（~10⁵ blocks/s）。

## 5. 找不到的数据（如实清单）

- E0（07-30 K2.7 塔）与 E1（并发放置）无 sessions.json 记录（早于 07-31 E3 建制）；E0 塔仅从 wire 补到 token（session_46bd5…，27 调用，输入 202,139/输出 21,868/缓存 1,632,685，K2.7 档 ¥2.79），E1 无 token 数据。
- 07-27→07-30 白天 6 个 SiliconFlow 实验 wire（sf/qwen3-coder-30b、sf/qwen3-vl-32b，最大单会话输入 4.85M）与具体实验编号的映射无文档可查，未计入总账。
- 开发侧主交互会话（wd_minecraft-ai-building 等，写代码/调研消耗的 K3 token）不在本审计口径内，项目文档也无其成本记录。
- v4-flash 08-08 后建造的质量机器评分（无 walkability/flatness/IoU 跑分日志）。
- 游戏内聊天栏广播的账单原文（AgentRunner.broadcastTokenBill 输出）未落盘。
- 11 个会话无 wire 可查（7 个 failed/cancelled/intake 本就走零 token；4 个 wire 已被清理，按 sessions.json 计入，其中 3 个为零）。

## 6. 数据质量备注

- 9 个会话 sessions.json 比 wire 多记 20-27k 输入（约 +2-11%），输出/缓存多数一致；疑似 mod 的 stream-json 兜底通道（AgentRunner.java:247-252）与 wire 回填双计，未完全定位。本审计一律以 wire 为准并在此声明；若按 sessions.json 口径，总账约高 ¥6-8。
- 时间戳口径：sessions.json `created_at` 为 epoch 毫秒，本文统一转本地时间（UTC+8）；state.json 的 createdAt 为 UTC 字符串。
- "行数"口径：会话数按 sessions.json 条目计（91）；调用数有两口径——stats.tool_calls（工具调用）与 wire usage.record 条数（LLM 调用/轮次），本文分别标注。
- K2.7 会话两账同价的理由：①其真实刊例（约 $0.95/$4，gate.ai 转引官方）高于 K2 档但同量级；②当时走 managed 套餐无按 token 账单。若严格按 K2.7 刊例重估，5 个会话约 ¥46（+¥21），不改变总结论。
