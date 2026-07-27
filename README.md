# minecraft-ai-building

把 coding agent CLI(Kimi Code 等)接入 Minecraft,游戏内自然语言指令自动建造建筑。

- 平台:Minecraft Java 1.21.11 + Fabric(单机)
- 架构:游戏内 `/aibuild` 拉起无头 agent;mod 暴露 HTTP API;独立 stdio MCP 桥(`mc-mcp-bridge`)翻译工具调用
- 设计文档:[docs/specs/2026-07-27-minecraft-ai-building-design.md](docs/specs/2026-07-27-minecraft-ai-building-design.md)

## 仓库结构

- `aibuild-mod/` — Fabric mod 源码
- `mc-mcp-bridge/` — MCP 桥源码(独立可测)
- `docs/specs/` — 设计文档
