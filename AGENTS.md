# 给 agent：这个文件夹是什么、拿到它该做什么

这是一套 Web/JS + iOS/Android **协议逆向**（爬虫协议还原，不是浏览器自动化）的工具链。
用户会把这个文件夹的路径发给你，意思是「把它装到这台机器上」或「照它的规矩干活」。**路径不固定**，一切以本文件所在目录为准。

## 用户让你「装一下」时

只跑这一条，幂等，重跑即更新：

```bash
bash "<本目录>/claude-setup/install.sh"
```

它会：把 skills / templates / newrev 复制到 `~/.claude/reverse-toolchain/` → 17 个 skill 软链到 `~/.claude/skills/`、`~/.zcode/skills/`、`~/.codex/skills/` 三平台（20260920 内部版：web 6 + 安卓 6 + iOS 5）→ 全局逆向准则挂载（`~/.claude/CLAUDE.md` @include + `~/.codex/AGENTS.md` 内联，真源 `claude-setup/rules/`）→ `newrev` 软链到 `~/.local/bin/` → 下载并装好全部免费依赖（CloakBrowser 二进制、Reqable 免费版、JDK 21 + jadx + 插件、frida、wedecode、wabt，约 450MB；`--skip-downloads` 跳过大文件，`--core-only` 只装 Web 核心）→ 用 `claude mcp add --scope user` 注册 9 个 MCP（`js-reverse` / `js-reverse-cloak` / `roxybrowser-playwright` / `chrome-devtools` / `wiremcp` / `reqable` / `jadx` / `frida-agent` / `wedecode`；`roxybrowser` 需 API Key，共 10 个）。

**Codex 注意**：MCP 注册段写的是 Claude 的 `~/.claude.json`；Codex 读 `~/.codex/config.toml`。若用 Codex 干活，把 10 个 MCP（含 roxybrowser，它需要 `env` 段写 `ROXY_API_KEY/HOST/TIMEOUT` 三个变量，参考本机已配好的 `~/.codex/config.toml`）按 stdio 命令镜像进 `[mcp_servers.*]`；已配好则跳过（`grep js-reverse ~/.codex/config.toml` 检查）。

跑完看输出：

- **`roxybrowser` 没装** 是正常的，它需要 API Key。告诉用户：打开 RoxyBrowser 客户端 → API → 启用 → 复制 Key，然后 `ROXY_API_KEY=xxx bash <本目录>/claude-setup/install.sh` 再跑一次。**不要替用户猜 Key，不要把 Key 写进任何项目目录。**
- 已有的 MCP 会显示「已有，跳过」，不会覆盖用户现有配置。
- **`ida-pro` 不装**：ida-pro-mcp 不支持 IDA Free，用户明确要免费的。wasm 用 wabt（`wasm2wat` / `wasm-decompile`）。
- `reqable` 用的是 Reqable **自带的官方 MCP**（`/Applications/Reqable.app/Contents/Helpers/mcp-server`），不需要配 Report Server；Reqable 首次打开会引导装根证书，那步要用户自己点（要输系统密码，你不能代输）。jadx MCP 用之前先开 `jadx-gui` 加载 apk。
- Reqable 是 Flutter 应用，AppleScript / 辅助功能看不到它的 UI 元素，别试图自动化点它的界面。
- 装完后本目录可以搬走或删掉。**不要在 `~/.codex/AGENTS.md` 或任何全局配置里写死本目录的路径**——用户会把这个文件夹放到不同位置。

## 用户在某个项目里说「看逆向文件夹 / 按这个接入」时（标准流程：检查 + 按需接入）

1. **体检（缺才补，不重装）**
   - `ls ~/.codex/skills/web-reverse-master/SKILL.md` 存在 → skills 就绪；缺 → 跑 `bash <本目录>/claude-setup/install.sh`
   - `grep js-reverse ~/.codex/config.toml` 命中 → MCP 就绪；缺则按本文件上方 Codex 镜像说明补
2. **判断平台，套对应模版**（判断不了就问用户一句，别猜）

   | 目标特征 | 平台 | 当前目录已有内容 | 空目录/新建 |
   |---|---|---|---|
   | URL / 网站 | Web | `newrev --here [URL]` | `newrev <名> [URL]` |
   | APK / 包名 / 安卓真机 | 安卓 | `newrev --here --android [包名]` | `newrev --android <名> <包名>` |
   | IPA / bundle id / 越狱真机 | iOS | `newrev --here --ios [bundle id]` | `newrev --ios <名> <bundle id>` |

   已生成 CLAUDE.md/AGENTS.md、目录骨架、`.venv`（禁用全局 python3）。目录里已有 CLAUDE.md 时 newrev 会拒绝覆盖——先读它，只在用户要求时手动合并。
3. **开工**：按项目 CLAUDE.md 的规矩执行（协议优先、缺口驱动 Phase、确认门槛、止损纪律）。

## 不要做的事

- 不要把 `claude-setup/skills/` 复制进项目目录。全局是软链，项目里再放一份会重复加载。
- 不要在项目 `.mcp.json` 里重复定义那 10 个 MCP，会和全局打架。
- 不要照抄 `claude-setup/_meta/` 各期归档里的配置——那是老师包的原始留存（含其 Windows 机器路径、AdsPower、设备信息），只作参考，不是本机环境。
- RoxyBrowser 的工具名是 `roxy_profile_*` / `roxy_proxy_*` / `roxy_platform_account_*`；`roxy_list_browsers` / `roxy_open_browsers` / `roxy_health_check` 这套**不存在**，别从记忆里编。

详细说明看 `README.md` 和 `claude-setup/README.md`。
