# MCP 配置片段参考

**本机这些已经全部由 install.sh 装进全局了**，这个文件只在「换机器、不想跑 install.sh、手动抄配置」时有用。

> 片段里的 `<HOME>` 换成本机 `echo $HOME` 的结果（JSON 不展开 `~` 和 `$HOME`）。绝对路径只写进本机配置，别提交回本仓库。

分工：

- **全局已装**（`~/.claude.json` 的 `mcpServers`，所有目录都能用）：`js-reverse`、`js-reverse-cloak`、`roxybrowser`、`roxybrowser-playwright`、`chrome-devtools`、`wiremcp`、`reqable`、`jadx`、`frida-agent`、`wedecode`。项目里**不要**再定义同名条目，否则会和全局的打架，而且 Roxy 的 API Key 会被复制进每个项目目录（可能跟着 git 泄出去）。
- **项目级**（本目录 `.mcp.json`）：默认为空，只放下面这些按需的。

前六个覆盖 Web 逆向的日常，后四个是 App / 小程序 / 抓包扩展。下面这些都是「有对应的本地客户端/工具时才有意义」，装了空跑只会浪费启动时间。

---

## 路线3 接管：js-reverse-mcp 连 RoxyBrowser 的 CDP（要断点时才需要）

日常接管 Roxy 窗口用全局的 `roxybrowser-playwright`（`browser_connect_roxy` 运行时传 ws 地址，不用改配置、不用重连）。
只有**需要在 Roxy 窗口里下断点**时才加这条：先 `roxy_profile_open` + `roxy_profile_connection_info` 拿到端口，把 `<PORT>` 换掉，再 `/mcp` 重连。

```json
"js-reverse-roxy": {
  "command": "npx",
  "args": ["-y", "js-reverse-mcp", "--browserUrl", "http://127.0.0.1:<PORT>"]
}
```

嫌每次改端口麻烦就用 Python CDP 桥（见 `~/.claude/skills/web-reverse-master/references/08-tool-reference.md` 接管方式 C）。

---

## Reqable 抓包 —— 已全局装（官方 MCP）

Reqable 免费版在 `/Applications`，3.2+ 自带官方 MCP server，直接用它，**不需要配 Report Server**。

```json
"reqable": {
  "command": "/Applications/Reqable.app/Contents/Helpers/mcp-server",
  "args": ["--scope", "all"]
}
```

App 没装时的兜底：`"command": "npx", "args": ["-y", "reqable-mcp-server", "--scope", "all"]`。
`--scope minimal`（默认）只注册常用工具，`all` 注册 100+ 全部。

---

## IDA Pro（Wasm / 二进制逆向）—— 没装，只能付费

ida-pro-mcp 明确不支持 IDA Free。wasm 用免费的 wabt（已 `npm i -g`）：

```bash
wasm2wat xxx.wasm -o xxx.wat        # 反汇编成文本
wasm-decompile xxx.wasm -o xxx.dcmp # 伪 C 风格反编译，更好读
```

哪天真买了 IDA Pro：

```bash
uv tool install ida-pro-mcp && ida-pro-mcp --install
```

```json
"ida-pro": { "command": "ida-pro-mcp" }
```

---

## JADX（安卓 APK 反编译）—— 已全局装

JDK 21 + jadx + jadx-ai-mcp 插件都在 `~/.claude/reverse-toolchain/vendor/`，`jadx` / `jadx-gui` 命令已带好 JAVA_HOME。用之前先 `jadx-gui` 开着并加载 apk。

```json
"jadx": {
  "command": "<HOME>/.local/bin/uv",
  "args": ["--directory", "<HOME>/.claude/reverse-toolchain/vendor/jadx-mcp-server", "run", "--python", "3.12", "jadx_mcp_server.py"]
}
```

---

## Frida（安卓/iOS 动态插桩）—— 已全局装

`uv tool install --with 'mcp<2' frida-mcp`（必须钉 mcp<2）。目标设备要 root/越狱并跑着 frida-server。

```json
"frida-agent": { "command": "<HOME>/.local/bin/frida-mcp" }
```

---

## WireMCP（Wireshark / tshark 抓包）—— 已全局装

`install.sh` 会把它从 GitHub 拉到 `~/.claude/reverse-toolchain/vendor/WireMCP/` 并注册为全局 `wiremcp`。
它自己会找 `/Applications/Wireshark.app/Contents/MacOS/tshark`，不需要 tshark 在 PATH 里。
抓包需要当前用户在 `access_bpf` 组（装 Wireshark 时勾 ChmodBPF）。工具：`capture_packets` / `get_summary_stats` / `get_conversations` / `check_threats` / `check_ip_threats` / `analyze_pcap` / `extract_credentials`。

它抓的是**系统级**流量（所有进程），适合看 TLS 握手、非浏览器客户端、DNS；浏览器里的 HTTP 明细还是 `js-reverse` 的 `list_network_requests` 更直接。

---

## 微信小程序反编译（wedecode）—— 已全局装

install.sh 已 clone + build 到 `~/.claude/reverse-toolchain/vendor/wedecode/`。

```json
"wedecode": {
  "command": "node",
  "args": ["<HOME>/.claude/reverse-toolchain/vendor/wedecode/dist/mcp/wedecode-mcp.js"]
}
```

⚠️ mac 上小程序包在 `~/Library/Containers/com.tencent.xinWeChat/Data/.wxapplet/packages/` 或 `.../Applet/`，跟 Windows 路径不同，让 agent 先 `find` 一下。

---

## 关于那两个 zip 里的东西

- `mcp_不需要都安装按需配置.zip` 里的 `chrome-devtools-mcp` / `js-reverse-mcp` / `reqable-mcp`：都是上游仓库的拷贝，**不要用里面的 `node_modules`**（是 Windows 上 pnpm 装的，带 `win32-x64` 的 esbuild.exe）。上面的 `npx` 配置会自动拉 macOS 版本。
- `ChromeDebug/`：Windows 的 Chrome 用户资料，mac 上没用。
- `mcps.zip` 里的 Camoufox / CloakBrowser / FireFox Reverse AI / WMPFDebugger：全是 Windows 二进制（`chrome.exe` / `.dll`），mac 跑不了。CloakBrowser 的能力现在由 `js-reverse-mcp --cloak` 自动下载对应平台版本提供，不需要这份。
