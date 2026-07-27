# 交接文档 — 2026-07-28(额度耗尽,29 号恢复)

> 写给 29 号的自己/协作者:恢复时先读本文件,再看 spec 与 plan。

## 1. 现状快照

**已完成并提交(git 工作区干净)**:

| 阶段 | 内容 | 验证 |
| --- | --- | --- |
| 设计 | `docs/specs/2026-07-27-minecraft-ai-building-design.md`(14 节,含风格系统 §5.4) | 用户逐节批准 + 两轮修正 |
| 调研 | 前人项目/离屏渲染/工具链/MCP 桥,结论已固化进 spec | — |
| 计划 | `docs/plans/2026-07-27-implementation-plan.md` | 用户批准 |
| Phase 0 | kimi CLI 行为验证(见 §4) | 全部实测通过 |
| Phase 1 | `mc-mcp-bridge/`:手写 JSON-RPC stdio MCP server + HTTP 翻译 | **37/37 单测绿** |
| Phase 2 | `aibuild-mod/`:Fabric 1.21.11 骨架 + HTTP bridge(5 端点)+ 异步分帧 job | curl **8/8** |
| Phase 3 | AgentRunner:`/aibuild` `/aichat` `/aicancel` + 续聊 + 收件箱捎带 | dev server E2E 通过;**用户真机 M1 测试:合格、速度快** |
| Phase 4 | 选区杖 + `propose_site` 两阶段确认 + `get_terrain_summary` + 写工具边界强制(SiteGate) | dev server E2E 三路径全过 |

**已部署**:PCL 实例 `D:\PCL 正式版 2.13.0.1\word\versions\1.21.11-aibuilding-test\mods\aibuild-1.0.0.jar` = **Phase 4 版**(重建命令:在 `aibuild-mod/` 跑 `./gradlew build`,产物在 `build/libs/`,复制到该 mods 目录)。

**最近提交**:`fb93be6` Phase 4 ← `f199602` Phase 3 ← `ba5b497` Phase 2 ← `0e05a01` Phase 1。

## 2. 中止点

- **Phase 5(快照 + `/aiundo`)子代理已杀,未产生任何代码变更**(杀掉时 git 干净)。29 号从这里继续。
- Phase 5 任务要点(重述,免去翻会话):每次 `/aibuild` 在 bounds 确定后用 `StructureTemplate#fillFromWorld` 快照到 `<世界>/aibuild/snapshots/`(留最近 10 份);`/aiundo` 只回退最近一次,**恢复必须复用 JobManager 分帧机制**(禁止原子 placeInWorld 26 万块);agent 运行中禁 undo;mojmap 读取模板方块列表的 API 需 javap 核实。

## 3. 待办(按序)

1. **Phase 5**:快照 + undo(见上)
2. **Phase 6**:渲染 `render_region`(主方案:WorldMesh+离屏 framebuffer,移植 Isometric Renders 的 MIT 模式;V1 回退:MapColor 俯视光栅)——**有一个用户未回答的决策**:渲染是纯客户端代码,dev server 测不了,要么允许我 `gradlew runClient`(会在用户桌面弹 MC 窗口,自动测完自动关),要么用户真人测。29 号先问
3. **Phase 7**:AGENTS.md 打磨 + 3-5 张手写 baseline 风格卡片(`styles/`)+ 三场景验收

## 4. 关键环境事实(恢复时免重新调研)

- **kimi CLI**:`C:\Users\zengd\.kimi-code\bin\kimi.exe`(0.29.2,官方脚本安装,与 Kimi 桌面版共享 `~/.kimi-code` 登录态)。**每次 agent 调用消耗用户模型额度——E2E 一律用最小任务,能 curl/RCON 测的绝不调 AI**
- **CLI 行为**(0.29.2 实测):`kimi -p --output-format stream-json` 输出 JSONL;assistant 文本 `{"role":"assistant","content":...}`;**session id 在 meta 行**(`session.resume_hint`);续聊 `kimi -r <id> -p`(首选)或 `-c -p`;长回复期间 stdout/stderr 全程零字节是常态(静默超时=双通道无字节,默认 20min)
- **工具链**:MC 1.21.11 + Mojang mappings(`loom.officialMojangMappings()`)+ Loom 1.17-SNAPSHOT + Gradle 9.5.1(wrapper 已含腾讯镜像)+ Java 21(Zulu 在 PATH)+ Fabric API 0.141.5+1.21.11
- **dev server 测试法**:`aibuild-mod/` 下 `./gradlew runServer`(headless);`run/` 已配 eula/RCON/`run/rcon.py` 驱动脚本;无玩家时需 `forceload` 否则区块不加载(1.21 已取消 spawn chunks);空服 60s 会暂停 tick(原版行为)
- **1.21.11 API 变动**(已踩过):`Identifier`(无 ResourceLocation)、`Entity#level()`、`Commands.hasPermission(LEVEL_GAMEMASTERS)`、`getRespawnData().pos()`、物品注册带 RegistryKey、`ClickEvent.RunCommand("/cmd")` 挂 `Style`
- **mod jar 内含** bridge jar(`assets/aibuild/mc-mcp-bridge.jar`,gradle 任务自动从兄弟模块构建复制)

## 5. 真机待验证项(29 号用户测)

- [ ] `propose_site` 聊天栏**可点击 [确认]/[拒绝] 按钮**(API 字节码核实过,真实客户端未点过)
- [ ] 选区杖左/右键点击设定两角(物品 `/give @s aibuild:selection_wand`)
- [ ] 越界拒放(界外条目 job 报 `out_of_bounds` failed)
- [ ] `/aiselect show/clear/set`

## 6. 注意事项

- RCON 控制台中文回显乱码仅为 Windows 控制台编码,文件与游戏内均为正常 UTF-8
- dev server `run/` 目录在 .gitignore 内(含 rcon.py 测试工具,不进仓库)
- 曾被杀掉的 32³ obsidian 测试任务在 dev 世界 y≈220 有残留方块(测试世界,无所谓)
