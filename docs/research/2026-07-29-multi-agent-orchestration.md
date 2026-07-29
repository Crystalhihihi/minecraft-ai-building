# 调研:多 agent 编排与混合模型路由 — 2026-07-29

> 来源:explore 子代理(thorough 档),为多 agent 集群阶段(BACKLOG B1)服务。原始结论未删改,仅排版。

## 1. Kimi Code CLI 机制(文档实查)

- **自定义 agent**:`~/.kimi-code/agents/` 或项目 `.kimi-code/agents/` 的 Markdown+YAML 文件,支持 tools/disallowedTools(MCP glob)、subagents 白名单、`model_preference: primary|secondary`——**没有 per-agent 具体模型字段**
- **模型绑定**:实验性 `[secondary_model]`(`KIMI_CODE_EXPERIMENTAL_SECONDARY_MODEL=1` 开启):新 spawn 的子 agent 默认绑 secondary;主 agent 可按 spawn 选 primary。secondary 可指向**任意 OpenAI 兼容端点**(DeepSeek/Qwen/Ollama),reasoning_content 自动处理
- **无头 `kimi -p` 可 spawn 子 agent**:Agent 工具在 print 模式自动放行;`print_background_mode="steer"` 默认保活,后台子 agent 结果以合成 user 消息回喂;print 模式子 agent 超时默认 0(不限)
- **AgentSwarm**:单 `prompt_template` + `{{item}}` + items,≤128 子 agent,等全部完成聚合返回——单模板不适合"每栋建筑不同任务书";**异构任务用 N 个后台 Agent 调用**
- **隔离**:子 agent 只见任务描述,仅最终消息回传;coder 子 agent 可再嵌套
- **限额**:`[background] max_running_tasks` 并发上限(示例 4);managed Kimi ~30 并发请求、300-1200 req/5h——planner+workers 共用一个 managed key 会互相挤
- 文档矛盾点:tools.md 说 Agent 任务"固定 30 分钟超时",配置参考说默认 2h——用时要实测

## 2. 编排模式

- 参照系:[Anthropic 多 agent 研究系统](https://www.anthropic.com/engineering/multi-agent-research-system)——Opus 主 + Sonnet 工,评测 +90.2%,代价 **~15× token**(单 agent ~4×);token 消耗解释 ~80% 性能方差。**多 agent 是花更多 token 并行买时间,不是省 token**
- **任务书契约**(共识):worker 只见 brief,planner 必须给自足契约——本项目即:边界、材料/调色板、逐层计划或风格引用、验收标准、"最终消息=完整结果"(Kimi 自定义 agent 需在正文显式写明)
- **失败处理**:后台 agent 报终态;`resume` 续实例或重开;skip-and-report 优于静默重试;每 worker 状态必须可见,否则部分失败消失在聚合里
- **反模式**:强耦合子任务、需要共享上下文的 worker、编排者同步死等。Cognition《Don't Build Multi-Agents》:共享隐式上下文时多 agent 必败——**我们的"独立结构+不相交边界"恰是多 agent 成立的那类负载**

## 3. 混合路由经济学

- RouteLLM(LMSYS/Berkeley):成本降至 1/3.66,~85% 节省保持 95% GPT-4 质量——但那是 chat 基准,不是 agentic 工具循环
- 质量悬崖正中我们领域:小模型在**多步工具使用与空间推理**退化最狠([Project Sid](https://arxiv.org/pdf/2411.0114):连前沿 agent 都是 MC 空间/建筑技能最弱)——worker 任务书必须**接近确定性**(精确调色板+逐层计划);审美裁决(选址、终审 render)必须留强模型
- 实战补充(用户铁锈战争项目):deepseek-v4-flash 规划 + qwen3-30b 执行,生产环境验证"大+小"比纯大模型省**数百倍**
- 并发现实:managed Kimi ~30 并发;"几十个本地 Ollama"是 VRAM 做梦(30B Q4≈20GB,会串行化);真并发靠托管便宜 API(DeepSeek/Qwen,各自有限流)

## 4. 并发世界编辑

- 共识:**分区优于合并**(Claude Code agent teams 用 git worktree+文件所有权;lost-update 与语义冲突是主导失败模式;CoAgent 探索事务式并发控制)
- MC 落地:mod 侧强制不相交空间边界(SiteGate 现成的)——写集不相交=无合并冲突;残余风险是**接缝**(相邻建筑风格冲突)与**边界地形**——planner 留缓冲带 + 事后 render 复审,不搞 worker 间协商

## 推荐形态

1 个 `kimi -p` planner(K3 或 flash 级)+ N 个后台 Agent spawn 绑 `[secondary_model]`(DeepSeek/Qwen 端点),每 worker 一个自定义 agent 文件(own system prompt,`tools: mcp__mc__*`),bridge 按会话路由锁,`max_running_tasks` 按便宜端点限流调。A/B 对照:K3 单干 / K3+Qwen / flash+Qwen(+K3 终审)。
