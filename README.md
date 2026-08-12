# minecraft-ai-building

把 coding agent CLI(Kimi Code 等)接入 Minecraft,游戏内自然语言指令自动建造建筑。

- 平台:Minecraft Java 1.21.11 + Fabric(单机)
- 架构:游戏内 `/aibuild` 拉起无头 agent;mod 暴露 HTTP API;独立 stdio MCP 桥(`mc-mcp-bridge`)翻译工具调用
- 设计文档:[docs/specs/2026-07-27-minecraft-ai-building-design.md](docs/specs/2026-07-27-minecraft-ai-building-design.md)

## 仓库结构

- `aibuild-mod/` — Fabric mod 源码
- `mc-mcp-bridge/` — MCP 桥源码(独立可测)
- `docs/specs/` — 设计文档

## License

- **代码**（`aibuild-mod/`、`mc-mcp-bridge/`、生成器脚本）：[AGPLv3](LICENSE)——衍生作品必须同协议开源并署名，网络提供服务同样触发。
- **非代码资产**（`docs/`、风格卡、实验语料、图片）：CC BY-NC-SA 4.0——署名、非商用、相同方式共享。
- `精灵树图片/` 内的游戏截图仅作风格参考，权利归原游戏公司所有。
