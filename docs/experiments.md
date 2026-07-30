# 实验记录(E 系列:多 agent 可行性验证)

> 目的:验证多 agent(planner + N worker)在 MC 建筑上的速度与质量。每项记结论与数据。

## E0:便宜工人能否按任务书施工 —— ✅ 通过(2026-07-30)

- **结论**:K2.7 Coding(managed 套餐)工人能力合格:读任务书/选风格卡/propose/勘察/放置零错误/渲染自检/诚实汇报。塔(7x7x21,地基+墙+扶壁+窗+垛口+人字顶)结构核对全对
- **附带发现 1**:选址审美是 planner 的活——工人把塔盖在了山腰里(埋进深板岩),施工全对但位置失败。planner-worker 分工被反例证实
- **附带发现 2**:SiliconFlow 券级限流(429 风暴+无缓存豁免)判生产不可用;模型分工终版改 Kimi 原生梯队(K3 规划+K2.7 worker,见 BACKLOG B1)
- **附带发现 3**:bridge 参数类型脆弱性(Postel 宽容化已修,85/85 测试绿)
- **附带发现 4**:基础设施税是最大隐性成本——dev server 超时杀 job、选址确认存内存随重启归零(加固项:SiteGate 状态落盘、job 恢复、429 自动续跑)

## E1:并发放置吞吐 —— ✅ 放置不是瓶颈(2026-07-30)

- 4 并发 14x30x14(5880 each):全部 0.3s 完成,零失败,聚合 ~79k blocks/s
- 2 并发 30x35x30(31500 each):0.2-0.4s,零失败,聚合 ~161k blocks/s
- 早期"32³≈1.5s"的成本大头是**首次 chunk 加载**(ticket 系统一次性),不是放置本身
- **结论**:热区块并发放置 ~10⁵ blocks/s,比 agent 思考速率(分钟级)高 4-5 个数量级。并行建造永远不会卡在放置上,瓶颈只有模型延迟

## E2:单 agent 基线 —— ✅ 完成(2026-07-30,K3)

- **数据**:36 轮 / 52 次工具调用 / 放置约 13.8 万块(含清空 13 万旧废料)/ **墙钟 16.1 分钟** / 放置零失败 / 4 轮渲染自检
- **建成**:42×32 幕墙(高7+勒脚+crenellation.py 垛口)、四角圆塔(直径7高12,自写 manor_gen.py 生成锥顶)、门楼(3x4 门洞+iron_bars 闸门)、21×12 双层主楼(26 箭窗 arch_window.py + gable_roof.py)
- **结论**:K3 单干 16 分钟一座合格庄园——这是 E4 要打败的锚点。注意它还自写生成器脚本(圆塔锥顶),代码建模已是本能

## E3:mod 并发切片 —— ✅ 通过(2026-07-31,commit d9be573)

- **改动**:AgentSessionManager/AgentSession 新增(注册表上限 4、每会话 SiteGate/收件箱/token、sessions.json 原子落盘+重启恢复+旧 state.json 迁移);BridgeHttpServer 多 token 路由+propose 跨会话相交 409;AgentRunner 每会话进程引擎+429/异常退出 30s 自动 `kimi -c` 续跑(≤3 次);JobManager 快照按会话 tag 盖戳分账;/aistatus 新增
- **E2E 五证据**:① 双会话并发建造实物互不干扰(消耗分账正确);② 相交 propose → 409;③ /aistatus 多行状态;④ 建造中途 stop → sessions.json 落 running+confirmed bounds,重启恢复并可 /aichat 续(实锤痛点闭环);⑤ taskkill 强杀 kimi → 30s 自愈续跑盖完,5/5 立方体验货
- **偏差记录**:主 token 走最新 running 会话(无 running 写 409 读放行);超时不自愈(只自愈进程非零退出);冲突只统计 RUNNING 会话;/aichat 暂无会话号参数
- **遗留**:DONE 会话 stale last_error 已修未回归;sessions/s<n>/ 只增不减需清理策略;每会话目录从 jar 重释放默认资产(旧根 styles/ 手改不带入)

## E4:并行 A/B —— 待做

## E5:疯狂修改压力测试 —— 待做
