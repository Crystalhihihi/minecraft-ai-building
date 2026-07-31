# 交接文档 — 2026-07-31 傍晚(供压缩上下文后恢复)

> 读我即恢复全部关键状态。详细历史:git log;实验数据:`docs/experiments.md`;延后事项:`docs/BACKLOG.md`;调研:`docs/research/`(reflib 13 篇)。

## 当前里程碑

- **M1/M2/M3 全闭环**(风格卡/模式库/渲染自检/undo/形状回放/bridge 宽容化)
- **E 系列**(docs/experiments.md):
  - E0-E2 ✅(E2 基线:K3 单 agent 庄园 16.1min/36轮/52调用)
  - E3 ✅ mod 并发切片(d9be573):会话注册表(上限4)/每会话 SiteGate+token+sessions.json 落盘/429 自动续跑
  - E4 首轮 ❌(4×K2.7 盖庄园 28.3min 输基线;败因=图纸歧义:各自定 y、剖切主楼屋顶、无整地工序)
  - **E4 复赛 ✅**(K3 planner+3×K3 worker 临水镇,25.9min 盖 3 倍体量,83 轮;分工修正全生效:绝对标高/单体零剖分/显式整地桩基/依坡就势)
- **新增 mod 能力**:`/aibuild @path` 从 aibuild 根目录读任务书(d496881);config `agent_model`(spawn 时 -m 注入);worker 默认已切回 `kimi-code/kimi-for-coding`(K3 只当 planner,用户嫌 K3 worker 太贵)

## 用户四条最高优先指令(2026-07-31)

1. **本地程序优先**:算得准的全给程序(选址分析/碰撞登记/参数化屋顶/量化验收),AI 只做审美决策
2. **建筑碰撞**:小镇把庄园吞了(x[0,20]×z[96,111] 重叠)——选址必须过"已占用地图"(sessions.json 里所有 confirmed bounds)
3. **消耗恐怖**(非套餐 ~50 元/建筑):worker 用 K2.7、压轮次、减渲染自检;**先补 token 账单再谈优化**
4. **风格单一/复杂建筑**:调研已做(reflib 新增 5 篇);Blender 探针验证"预制模块装配"路线

## 在途 agent(恢复时查 TaskList)

- **agent-36**(续跑中):mod 改造——已占用地图+`analyze_site` 选址工具+propose 警告+token 账单(stream-json usage 解析)
- **agent-45**:Blender 装配探针——模块=带 block 元数据的单位立方体,导出走块清单不做体素化(设计:docs/plans/2026-07-31-blender-assembly-spike.md);探针题目=小教堂,验收=屋顶/楼梯朝向零错误

## 调研新增(reflib,全部含来源 URL)

schematic-sources(PMC 340+ 可解析,授权红线=再分发)/chinese-monumental(斗拱飞檐模数)/detailing-depth(depth三层+weathering掺比)/statues-organic(三派起手式)/complex-build-workflow(Litematica verifier=机器验收模型)

## 环境事实

- mod 部署:`cd aibuild-mod && ./gradlew build` → jar 复制到 `D:\PCL 正式版 2.13.0.1\word\versions\1.21.11-aibuilding-test\mods\`
- dev server:`./gradlew runServer`(后台);RCON `python run/rcon.py "cmd"`;bridge.json 在 `run/aibuild/`;**杀 server 要直接 taskkill java PID,杀 gradlew 会留孤儿**
- 世界 aibuild 根:`run/world/aibuild/`(tasks/ 放任务书,sessions/s<N>/ 每会话目录)
- 庄园 x[0,41] z[80,111];小镇 x[-40,20] z[96,150](有重叠带,验货时注意);E3 测试盒 y=180
- Blender 4.2.23 在 `D:\blender-4.2.23-windows-x64`;blender-mcp addon 在 `scratch/blender-mcp/addon.py`(曾跑通,端口 9876)
- Windows python 不认 /d/ 和 /tmp 路径,要用 D:/ 和 C:/Users/zengd/AppData/Local/Temp
- python 写 JSON 必须 encoding='utf-8'(系统默认 GBK);console 乱码是 GBK 显示问题,文件本身多半没坏

## 下一步(按序)

1. agent-36 落地 → 构建部署 → 验证 analyze_site/token 账单
2. agent-45 Blender 探针结果 → 决策:放大 Blender 路线 or 退回游戏内生成器模块库
3. 风格卡体系升级(吃 reflib 新 5 篇)
4. 感知升级:多角度渲染包+接缝扫描+量化检查(schematic verifier 思路)
5. E5:同一建筑多 worker 并发修改
