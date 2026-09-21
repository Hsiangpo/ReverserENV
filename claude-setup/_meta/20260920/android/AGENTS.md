
> **便携分发适用规则**：开始任务先读本目录 [PORTABLE.md](PORTABLE.md)。原机设备、端口、工具版本、MCP 数量和历史通过结果不代表接收电脑当前状态；本包不含 MCP 程序、工具链、凭据或业务项目。原机设备标识已替换为占位符。仅在当前任务已有授权内操作已核实的目标；不自动同步用户全局配置或写入记忆。当前 Skills 与本条便携边界优先于历史附录。

# APPCodeObjectdemo1 — Codex runtime shim

本仓库的唯一项目规则真源是 [CLAUDE.md](CLAUDE.md)。开始任务时完整读取并按其中的 Android-only 范围、默认本地授权、4 个任务 Skill、MCP、设备恢复、证据门和目录约束执行。

- Skill 真源：`.claude/skills/`；`.agents/skills/` 是 Codex/ZCode/Qoder/Pi 的唯一同步镜像。不得创建 `.codex/.cursor/.grok/.qoder/.zcode/skills`；只改真源，再运行 `python .claude/scripts/sync_shared_skills.py`。
- MCP 真源：根 `.mcp.json`；`.codex/config.toml` 是生成镜像。只改真源，再运行 `python .claude/scripts/sync_mcp_mirrors.py`。
- 证据准则：`.zcode/memory/reverse_principles.md`。相关任务再读 `.zcode/memory/MEMORY.md`；只有用户明确要求时才更新记忆。
- 维护手册与按时区更新记录：`docs/SKILLS_MCP_RULES_MAINTENANCE.md`。
- 仓库内 Android 样本、Pixel 6 与指定测试账号默认已获本地授权，不重复询问；范围扩展到仓库外目标/第三方系统时才重新确认。

本 shim 不复制设备版本、工具数或测试结果；这些事实以 `CLAUDE.md`、实现和当前测试为准。
