# 交接文档 — 2026-07-30 深夜(供压缩上下文后恢复)

> 读我即恢复全部关键状态。详细历史:git log;实验数据:`docs/experiments.md`;延后事项:`docs/BACKLOG.md`;调研:`docs/research/`(含 reflib 8 类目)。

## 当前里程碑

- **M1(盲盖闭环)/ M2(安全闭环)/ M3(质量闭环)全部完成**:风格卡片 6 张(含 suzhou_garden)、模式库 10+、渲染自检(GL+topdown)、undo、异步 job、形状回放、support_check、bridge 宽容化(Postel)
- **真机验证通过**:苏式园林终测合格;教堂四缺陷(鱼鳞顶/偏殿/卡墙/平板墙)已修复
- **E 系列实验**(docs/experiments.md):
  - E0 ✅ 工人(K2.7)能力合格;发现"选址审美是 planner 的活"(塔被盖进山腰)
  - E1 ✅ 并发放置非瓶颈(热区块 ~161k 块/秒,瓶颈只有模型延迟)
  - E2 ✅ K3 单 agent 庄园基线:**16.1 分钟 / 36 轮 / 52 调用 / 零失败**(幕墙+圆塔+门楼+主楼)
  - **E3 进行中(agent-35)**:mod 并发会话切片——会话注册表(上限4)、每会话 SiteGate(边界相交 409)、会话 token 路由、**选址状态落盘**、**429 自动 -c 续跑**。代码已改完构建过,正在 dev server E2E
  - E4 待做:K3 planner + 4×K2.7 worker 同庄园 vs E2 基线;E5 疯狂修改压测

## 模型分工终版(BACKLOG B1)

**K3 规划+终审,K2.7 Coding 搬砖,全在 managed 套餐内。外部供货商全部放弃**(SiliconFlow 券级限流 429 实测生产不可用;百炼/MiniMax/OpenRouter 免费档同属共享池病)。

## 环境事实(恢复时不用重新调研)

- mod 部署:`aibuild-mod && ./gradlew build` → 复制 `build/libs/aibuild-1.0.0.jar` 到 `D:\PCL 正式版 2.13.0.1\word\versions\1.21.11-aibuilding-test\mods\`
- dev 测试:`aibuild-mod && ./gradlew runServer`(headless),RCON `python run/rcon.py "cmd"`,bridge.json 在 `run/aibuild/`
- 手动驱动 agent:在世界 `aibuild/` 工作目录跑 `kimi -p/-c -p -m <alias> --output-format stream-json`;模型 alias:`kimi-code/k3`、`kimi-code/kimi-for-coding`(K2.7)、`kimi-code/kimi-for-coding-highspeed`
- **每次 server 重启必须同步 mcp.json 的 port/token**;SiteGate 重启归零(E3 正在修)
- Blender spike 已通(Kimi→MCP→Blender 9876),精灵树专项用得上(PCG 算法栈在 `docs/research/2026-07-29-pcg-algorithms.md`)
- 硅基 key 已在聊天中泄露过,建议轮换

## 下一步(按序)

1. 等 E3(agent-35)交卷 → 审查+提交+重建部署
2. E4 并行 A/B:同庄园,planner 拆 4 区 + 4 worker,对比 E2 基线
3. E5 疯狂修改压测
4. 之后:复杂建筑阶段验收(有设计的中世纪庄园)→ 精灵树专项(PCG+Blender)→ 多建筑群景观
