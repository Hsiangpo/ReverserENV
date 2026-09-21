
> **便携分发适用规则**：开始任务先读本目录 [PORTABLE.md](PORTABLE.md)。原机设备、端口、工具版本、MCP 数量和历史通过结果不代表接收电脑当前状态；本包不含 MCP 程序、工具链、凭据或业务项目。原机设备标识已替换为占位符。仅在当前任务已有授权内操作已核实的目标；不自动同步用户全局配置或写入记忆。当前 Skills 与本条便携边界优先于历史附录。

# AGENTS.md — Cursor / Claude / ZCode / Codex 共用入口

本仓库以 **`.claude/skills` / `.claude/memory`、根 `.mcp.json`、`CLAUDE.md` + 本文件**分别作为 Skills/Memory、MCP、项目规则真源；派生入口只联接或同步，不独立演化。

开始任务先**完整读取根 `CLAUDE.md`**，再按当前缺口读取对应 `.claude/skills/<name>/SKILL.md`。本文件是跨客户端入口，不用下方摘要代替总规和 Skill 正文。

| 用途 | 权威路径 | Cursor | Claude Code | ZCode | Codex |
| --- | --- | --- | --- | --- | --- |
| 项目总规 | `CLAUDE.md` + 本文件 | `.cursor/rules/ios-reverser.mdc` | 自动读根文件 | 读根文件 | 读根 `AGENTS.md` |
| Skills | `.claude/skills/*/SKILL.md` | `.cursor/skills` junction | `.claude/skills` | `.zcode/skills` junction | `.codex/skills` junction |
| 项目记忆 | `.claude/memory/` | `.cursor/rules/project-memory.mdc` | `.claude/memory` | `.zcode/memory` junction | 经本文件指向 `.claude/memory` |
| MCP | 根 `.mcp.json` | `.cursor/mcp.json`（对用户全局去重；本机 `~/.cursor/mcp.json` 为空，三台都进项目） | 根 `.mcp.json` | `.zcode/config.json` 的 `mcp.servers`（对 `~/.zcode/cli/config.json` 去重，故项目侧通常只有 ios-device + frida-mcp；ida 在 ZCode 用户全局） | `.codex/config.toml` 的 `[mcp_servers.*]` |

## 按证据缺口选 Skill

- 入口/静态证据不明 → `ios-recon`；仅目标代码所在 FairPlay 区间未解 → `ios-unpack`，区间外可读材料先分析。
- 需要运行期、设备注册状态或传输证据 → `ios-dynamic`；仅本地分析不连接设备，保留已有进程/密钥/session，工具默认 spawn 不覆盖该要求。
- 设备注册谱系、Keychain/Secure Enclave、App Attest/DeviceCheck、签名或风险分层判因 → `ios-protocol-signature`；按生产者→存储→消费者及生命周期取证，静态、原生 hook、unicorn 按缺口选，不设顺序链。

完整字段谱系与传输判因引用协议 Skill 的 `references/ios-device-enrollment.md`、`references/ios-risk-transport.md`；历史记忆按需读且核版本/证据。Keychain 数据项不等于可导出的硬件私钥；证明回调、HTTP 200 或结构对拍不等于设备登记与业务验收。本地算法与含外部依赖的协议分别交付，判官边界遵循 `CLAUDE.md`。

启动客户端时选择整个 `ios_reverser_opus` 项目根。2026-09-19 对本机 ZCode bundled CLI 0.16.5 的原生列表验证：项目根发现 5 个 Skill，`tools` 子目录发现 0 个；此项目没有 `.git`，该版本不会从子目录向上发现根 Skill 或根配置。ZCode CLI 显式使用 `--cwd .`，IDE 则选择该根目录为工作区。不要用新建 `.git`、全局注册或每个子目录复制 Skills 规避此边界。该验证只证明发现，不证明模型实际调用。

既有机器契约：设备 iOS 15.8.8 / Dopamine 3.0.4；设备端 frida **只连 27045**（主机端口冲突可改开）；relay 冷启动与 Frida 握手分开给 20s；魔改 agent **无 ObjC bridge**，但已知类/selector 可用 runtime C API 定点换 IMP。按实际 `libboringssl` / Network.framework / HTTP / QUIC 路径取证；注入用 `ios-device` 的 `ios_frida`，不用 USB 27042 的 `frida-mcp`。每次复用/新建 relay 先核完整 UDID 与监听归属；握手 hang 不自动切 SSH-L 或 kickstart，按 ios-dynamic 的故障证据、任务范围与会话影响条件恢复，见 [[windows-amds-flap-zombie-relay]]。

`ios-device` 当前 **16 个公开工具**；系统级证据用 `ios_diagnostics`，实时动作限 **1–15 秒**、PCAP 限 **1–100 包**且拒绝覆盖，不启动业务 App。同一请求同字节最多总计3次（含首次发送）；漂移更早停，第3次同类失败停止同类线上实验，先离线差分，再设计当前范围内的原版对照或维度实验；一次性材料不为凑次数重放。

## Rules 语义对齐与同步

更新 Skill 时须同时复核 `CLAUDE.md`、本文件和 Cursor Rules 的角色、职责、匹配词、工作闭环、工具默认与交付判官。junction/hash 只证明可见性，不替代正文语义对照；checker 通过也不证明客户端自动选用。`ios-skill-evolver` 仅用于用户请求或授权的维护，普通分析不自动改 Skills 或记忆。

```powershell
# Skill 更新后刷新协议 Rule 元数据，其余 Rule 摘要人工语义对齐
.\.venv\Scripts\python.exe .\tools\write-cursor-signature-rule.py
# 完成语义复核后运行静态检查
.\.venv\Scripts\python.exe .\tools\check-ios-skills-mcp.py
```

仅根 MCP 配置实际变化时，运行 `tools/sync-claude-to-cursor.ps1` 和 `tools/sync-claude-to-zcode.ps1`；Skill 摘要修改不要求重写无关 MCP 配置。

- Cursor 脚本：校验 `.cursor/skills` junction、把 `.mcp.json` 去重写入 `.cursor/mcp.json`、确认 `.zcode/memory` junction，并调用 Python writer 刷新协议 Skill 的薄 Rule（禁止 PowerShell `Get-Content` 默认编码）。它不自动改写其他 Rule 摘要，语义对齐仍须逐项复核。
- ZCode 脚本：校验 `.zcode/skills` junction、把 `.mcp.json` 去重写入 `.zcode/config.json`。
- 都不上拉、不改写用户目录记忆。用户 Claude/ZCode 记忆只作增量来源（[[claude-zcode-memory-sync-procedure]]）；仓库才是权威。
- Codex：本仓库 `.codex/skills` junction + `.codex/config.toml`；改 MCP 后改根 `.mcp.json` 再跑上述两项同步，并核对 `.codex/config.toml` 三台 server 命令是否仍对齐。
- 更新记录：统一追加 `.claude/skills/EVOLUTION_LOG.md`，使用 Asia/Shanghai 精确时间并写明更新内容、涉及文件、同步影响、验证结果和边界/回滚；不另建第二份日志。
