# 待办：老师 MCP 到货后的接入指引

> 20260917 留档。用户已和老师约好，后续会拿到老师的全部自建 MCP。文件到手后，把本文件路径和 MCP 压缩包一起丢给 agent，照下面执行即可。

## 一、会拿到什么（向老师要的清单）

| MCP | 用途 | 老师环境里的形态 | 到货后要确认的东西 |
|-----|------|----------------|------------------|
| **js-reverse-mcp（私改版）** | 带 `trace_function` / `inject_before_load` 的版本或 fork | 老师本地构建 | 是 fork 仓库还是 npm 旧版？build 产物还是源码？ |
| `scripts/mcp-launcher.js` + `.mcp.local.example.json` | 他 web 包 mcp.md 说的受控 MCP 启动器 | 项目 scripts/ 目录 | 完整文件 |
| `ios-device` | 自建 iOS 设备 MCP（16 工具：ios_info/ios_ssh/ios_frida…） | `E:\PythonCodeObject1\ios_reverser_opus\mcp\ios-device-mcp\server.py` | 源码 + 依赖清单（requirements） |
| `frida-orchestrator-mcp` | 自建安卓编排 MCP（81 工具） | `E:\...\APPCodeObjectdemo1\android_mcp\servers\frida_orchestrator_mcp\server.py` | 源码 + requirements + 它引用的 toolchain |
| `reverse-index-mcp` | 反编译产物索引（8 工具） | 同上 servers/ 目录 | 源码 + requirements |
| `algo-lab-mcp` | 算法实验台（11 工具） | 同上 servers/ 目录 | 源码 + requirements |
| ida-pro-mcp | Wasm/二进制（对应 commit 8461a5f7） | uv 项目 | **注意：需要付费 IDA，用户原则免费，可不装** |

## 二、到手后的接入步骤（给 agent 的指令模板）

1. **Windows 产物先甄别**：老师的包多半是 Windows 环境打包（`.exe`、`.bat`、`E:\` 路径、`venv\Scripts\`）。纯 Python/Node 源码可直接跨平台；含 Windows 二进制依赖（如 adb.exe）的部分，改用 mac 等价物（brew android-platform-tools 等）。
2. **每个 MCP 单独建 venv/隔离**：放到 `~/.claude/reverse-toolchain/vendor/<mcp名>/`，Python 的用 `uv tool install` 或 `uv run` 方式跑（参考 install.sh 里 frida/jadx 的装法），别污染全局。
3. **注册**：`claude mcp add --scope user <名字> -- <启动命令>`；同时镜像进 `~/.codex/config.toml` 的 `[mcp_servers.*]`（ZCode 用户级配置另配）。名字沿用老师的（frida-orchestrator、reverse-index、algo-lab、ios-device），与 SKILL.md 里的引用一致。
4. **回滚适配声明**：装好后删掉这 5 个 SKILL.md 顶部「本机环境适配（20260917 维护注）」里对应的「未装」条目（ios-recon / android-recon / android-dynamic / android-unpack / web-reverse-master），改写为实际可用的启动方式。
5. **私改版 js-reverse-mcp 若到手**：装到 vendor 后，把 install.sh 的 `add_mcp js-reverse` 条目命令从 `npx -y js-reverse-mcp` 换成本地构建路径；同时可恢复项目 CLAUDE.md 第 5.1 节的 `inject_before_load` 写法（先留着替代方案注释）。
6. **验收**：`claude mcp list` 全 ✔ Connected；随便开个项目让 agent 用新 MCP 做一次最小调用（如 ios-device 的 ios_info）。

## 三、装完后的维护

- 新 MCP 的说明补进：根 `CLAUDE.md` / `AGENTS.md` 的 MCP 清单、`claude-setup/README.md` 的 MCP 表、项目模版 `templates/CLAUDE.md` 第 7 节、`templates/mcp-optional.md`
- 若老师也给了新版 skills：直接替换 `claude-setup/skills/` 对应目录 → 重跑 `install.sh`（三平台软链自动跟上）→ Desktop 源与 `~/.claude/reverse-toolchain` 保持 diff 为零
