# claude-setup — 逆向工具链安装与使用

## 分层设计

```
安装副本 ~/.claude/reverse-toolchain/   skills / templates / bin 的拷贝（源目录搬走不影响）
项目 .claude/skills/（newrev 挂载）     17 个 skill（默认项目级；--global-skills 才软链进 ~/.claude|~/.zcode|~/.codex/skills）
全局 ~/.claude.json mcpServers          10 个：js-reverse / js-reverse-cloak / roxybrowser / roxybrowser-playwright / chrome-devtools /
                                        wiremcp / reqable / jadx / frida-agent / wedecode
vendor ~/.claude/reverse-toolchain/vendor/   WireMCP / jdk-21 / jadx（+ jadx-ai-mcp 插件）/ jadx-mcp-server / wedecode
~/.local/bin                            newrev / jadx / jadx-gui / frida / frida-mcp / wasm2wat 等
~/.cloakbrowser                         CloakBrowser 二进制（js-reverse-cloak 用）
/Applications/Reqable.app               Reqable 免费版
规则 templates/CLAUDE.md                规则本体（禁自动化、Phase 0-4、Phase 3 确认门槛），不进全局
项目（可选，newrev 生成）               ./CLAUDE.md 副本 / 权限白名单 / .venv（3.12）/ 站点骨架
```

**为什么这么分：**

- **Skills 默认项目级**（20260922 起）—— 全局挂载会让 17 个 frontmatter 约 **2.4k tokens 常驻每个会话**，且逆向措辞会让业务会话被 [cyber] 分类降级；所以默认只在逆向项目里由 `newrev` 挂载。确实要全局时 `--global-skills`。
- **MCP 全部全局** —— `js-reverse-mcp` 的浏览器是**第一次调工具时才启动**（`getContext()` 懒加载），会话开始只有一个 node 进程，所以全局放着没负担。工具 schema 也是按需加载的。
- **规则 CLAUDE.md 不进全局** —— 314 行强约束（禁止 Selenium、必须过 Phase 3 确认），塞进全局会让写普通脚本的会话也被管住。`newrev` 会把它复制进项目；不建项目时用户把本目录路径发给 agent，agent 按根目录 `CLAUDE.md` 的指引去读。
- **全局配置里不写死本目录路径** —— 用户会把这个文件夹放到不同位置、不同机器。所以安装是「复制到 `~/.claude/reverse-toolchain/`」而不是软链回源目录，装完源目录可以搬走。

## 安装

```bash
bash "<本目录>/install.sh"
```

一条命令做完：检查依赖（缺 `uv` 会自动装）→ 复制 `skills/templates/bin` 到 `~/.claude/reverse-toolchain/` → skills 默认项目级（`--global-skills` 才软链三平台）→ 逆向准则：Claude 由仓库 CLAUDE.md 相对导入（`--global-rules` 才挂全局），Codex 内联 `~/.codex/AGENTS.md`（真源 `rules/`）→ 软链 `newrev` → 拉 WireMCP → 预下载 CloakBrowser 二进制 → `npm i -g wabt` → 装 Reqable 免费版到 `/Applications` → 下 JDK 21 + jadx + jadx-ai-mcp 插件 + python server → `uv tool install` frida-tools / frida-mcp → clone + build wedecode → `claude mcp add --scope user` 注册 MCP（含 adb + 安卓三件套，原包在时）。幂等，已有的跳过，**重跑 = 更新**。

大文件合计约 450MB（CloakBrowser 150 / JDK 200 / jadx 70 / Reqable 33）。只想要 Web 核心、不要 App/小程序那些：

```bash
bash "<本目录>/install.sh" --core-only
```

`--skip-downloads` 则跳过所有大文件下载。

`roxybrowser` 需要 API Key，脚本不会猜。RoxyBrowser 客户端 → API → 启用 → 复制 Key：

```bash
ROXY_API_KEY=你的Key bash "<本目录>/install.sh"
```

端口以客户端 API 页显示为准（默认 50000，不同就再加 `ROXY_API_HOST=http://127.0.0.1:端口`）。

### 全局模式（可选，默认不开）

```bash
bash "<本目录>/install.sh" --global-skills --global-rules
```

默认 skills 不进全局，由 `newrev` 在每个新项目里软链到 `./.claude/skills/`；准则由本仓库 CLAUDE.md 相对导入。
上面两个开关才把它们挂进全局（代价：每个会话常驻 2.4k tokens，且业务会话也会带上逆向准则）。

`newrev` 会自动判断：`~/.claude/skills/web-reverse-master` 存在就用全局的，不存在就链进项目，不会重复加载。

### PATH

`install.sh` 会提示 `~/.local/bin` 在不在 PATH 里。不在就：

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

## 用 newrev 开新项目（可选）

不建项目也能干活：在任何目录说「帮我逆向 xxx」，agent 会读规则、在当前目录建 `.venv` 开工。
`newrev` 只是把「建目录 + 复制规则 + 建 venv + 权限白名单 + 站点骨架」打包成一条命令，想要整齐的项目结构时用：

```bash
newrev douyin                          # 只建项目骨架
newrev douyin https://www.douyin.com   # 顺带建 sites/douyin_com/ 站点目录
cd douyin && claude
```

生成：

```
douyin/
├── CLAUDE.md                      项目规则（已填好项目名）
├── .mcp.json                      默认为空（10 个 MCP 都在全局）
├── mcp-optional.md                按需 MCP 的配置片段，用时复制进 .mcp.json
├── .gitignore
├── .claude/settings.local.json    权限白名单（acceptEdits）
├── .venv/                         Python 3.12 + requests / curl_cffi / pycryptodome
├── sites/{domain}/                src / docs / assets / tests + README
├── plans/  scripts/
```

## RoxyBrowser

API Key 已经配在全局 `~/.claude.json` 的 `roxybrowser` 条目里，**项目 `.mcp.json` 不再重复定义** —— 否则每建一个项目就把 Key 复制一份到项目目录，跟着 git 推出去就麻烦了。

用之前确认：RoxyBrowser 客户端已启动 → API 开关已打开（客户端 → API）。本地 API 端口以客户端面板为准（默认 `http://127.0.0.1:50000`；探活 `curl http://127.0.0.1:50000/health` 应回 200）。客户端没开或端口配错时 `roxybrowser` MCP 会直接加载失败。

探活：调 `roxy_workspace_list`（**没有** `roxy_health_check` 这个工具）。

### 两个 Roxy MCP 的分工

| MCP | 包 | 有什么 |
|-----|-----|--------|
| `roxybrowser` | `@roxybrowser/openapi` | `roxy_profile_*` / `roxy_proxy_*` / `roxy_platform_account_*` / `roxy_workspace_list` / `roxy_project_list` / `roxy_label_list`。**没有任何页面操作工具** |
| `roxybrowser-playwright` | `@roxybrowser/playwright-mcp` | `browser_connect_roxy` + `browser_navigate` / `browser_click` / `browser_evaluate` / `browser_network_requests` / `browser_snapshot` 等 |

接管一个指纹窗：

```
roxy_profile_list                        → 拿 dirId
roxy_profile_open(dirId=...)             → 开窗
roxy_profile_connection_info(dirIds=[…]) → 拿 ws://127.0.0.1:<动态端口>/devtools/browser/xxx
browser_connect_roxy(cdpEndpoint=<ws>)   → 之后页面操作都作用在这个窗口
```

端口每次开窗都变，但 `browser_connect_roxy` 是运行时传参，**不用改配置也不用重连 MCP**。
需要下断点抠闭包时 `roxybrowser-playwright` 不够用（Playwright 工具集没有断点），改用 js-reverse-mcp 接管，见 `skills/web-reverse-master/references/08-tool-reference.md` 的「接管方式 B / C」。

## js-reverse 和 js-reverse-cloak 是什么

同一个包 `js-reverse-mcp`（v4.0.3）起两个实例，工具集完全一样（24 个：`new_page` / `navigate_page` / `list_network_requests` / `search_in_sources` / `set_breakpoint_on_text` / `get_paused_info` / `evaluate_script` / `get_websocket_messages` …），区别只在**用哪个浏览器**：

| | `js-reverse` | `js-reverse-cloak` |
|---|---|---|
| 浏览器 | 你电脑上装的 Google Chrome | CloakBrowser：一个把 Chromium C++ 源码改过再编译的浏览器 |
| 反检测 | 协议层（Patchright fork：不发 `Runtime.enable`、去掉自动化启动参数） | 协议层 + 源码层（`navigator.webdriver`、canvas、WebGL、audio、字体、屏幕、WebRTC、TLS 指纹全 patch） |
| Profile | `~/.cache/chrome-devtools-mcp/chrome-profile` | `~/.cache/chrome-devtools-mcp/cloak-profile`（物理隔离） |
| 什么时候用 | 默认，80% 目标 | 路线1 被 Cloudflare Turnstile / DataDome / FingerprintJS 这类指纹风控拦住时 |
| 额外成本 | 无 | 需要约 150MB 的 CloakBrowser 二进制。`install.sh` 已预下载好；没下的话第一次调工具时会静默下载，看起来像卡住 |

「cloak」= 隐身。它**不是**另一个 MCP 产品，就是 `js-reverse-mcp --cloak` 这个开关。

## 三条浏览器路线

| 路线 | 怎么起 | 什么时候用 |
|------|--------|-----------|
| 1（默认） | `js-reverse` MCP，直接 `new_page` | 绝大多数目标 |
| 2 | `js-reverse-cloak` MCP | 路线1 被指纹风控 / 反调试挡住 |
| 3 | Roxy 开窗 + 接管 | 需要稳定登录态 / 多账号隔离 / 固定代理出口 / 路线1、2 被风控挡住 |

**先试路线1**，别一上来就开指纹浏览器。一次任务只用一个浏览器上下文，不要在两个进程间横跳。

## 17 个 Skill（20260920 内部版）

| Skill | 用途 |
|-------|------|
| `web-reverse-master` | 全能一体机：目标明确直接开干（Phase 0-4 + 20+ 配方 + 反模式） |
| `web-reverse-field-guide` | 45+ 项目实战踩坑索引，按现象查根因 |
| `ast-deobfuscation` | JS 反混淆（`_0x`、字符串表、控制流平坦化、OB 变种） |
| `param-encryptor` | 签名/加密参数实现 |
| `env-patcher` | 补环境（browser.js 生成） |
| `captcha-solver` | 验证码纯协议求解（11 家服务商、20+ 配方） |
| `ios-recon` / `ios-unpack` / `ios-dynamic` / `ios-protocol-signature` | iOS 全工序：侦察 → 砸壳 → Frida 动态对抗 → 签名还原；`ios-skill-evolver` 维护进化 |
| `android-recon` / `android-unpack` / `android-dynamic` / `protocol-signature-reverser` | Android 全工序：侦察反编译 → 脱壳 → 动态插桩 → 签名还原；`reverse-skill-evolver` 维护 |
| `darwin-skill` | 通用 skill 维护框架（不参与任务路由） |

用法：目标明确 → `web-reverse-master`；阶段方法在 `web-reverse-master/references/10-staged-method.md`（旧 7 个流程/trace skill 已按老师 20260920 版清理合并）。

## 扩展 MCP（也都全局装了，全是免费软件）

| MCP | 依赖（已装） | 用途 | 用之前 |
|-----|------|------|------|
| `wiremcp` | Wireshark 4.4（本机原有） | 系统级抓包：TLS 握手、DNS、非浏览器客户端 | 无 |
| `reqable` | Reqable 免费版 `/Applications/Reqable.app`，用的是它**自带的官方 MCP server**（`Contents/Helpers/mcp-server --scope all`，100+ 工具：抓包查询、生成 cURL、断点、重写、脚本、集合） | HTTPS 抓包 + 改包重放，对比「浏览器请求 vs Python 复现」 | Reqable 在运行即可（菜单栏 R 图标）。根证书已装。**不需要 Report Server**，那是社区版 reqable-mcp 的做法，已弃用。少数工具（集合云同步之类）要登录 Reqable 账号，抓包相关的不用 |
| `jadx` | Temurin JDK 21 + jadx 1.5.6 + jadx-ai-mcp 插件（`vendor/`） | 安卓 APK 反编译，**不是 Web** | 先终端敲 `jadx-gui` 开着，加载一个 apk |
| `frida-agent` | frida-tools 17 + frida-mcp（`uv tool`） | 手机动态插桩，**不是 Web** | 需要 root/越狱设备跑着 frida-server |
| `wedecode` | 自己 build 的 MCP-WEDECODEMCP（`vendor/`） | 微信小程序反编译 | mac 上小程序包在 `~/Library/Containers/com.tencent.xinWeChat/.../Applet/`，让 agent 自己找 |
| `frida-orchestrator-mcp` / `reverse-index-mcp` / `algo-lab-mcp` | 老师安卓三件套（`vendor/android_mcp`，venv 钉 frida 16.5.9 + mcp<2）+ Google platform-tools adb（`vendor/platform-tools` → `~/.local/bin/adb`） | 安卓真机编排 / 反编译索引 / 算法对拍 | 原包 `mcps/安卓/android_mcp.zip` 不入 git，换机器要手动拷过来再跑 install.sh。老师包只带 Windows `adb.exe`，mac 靠 `ANDROID_MCP_ADB` 指到 platform-tools 的 adb（install.sh 注册时自动带上）。**魔改 frida-server `new-server-arm64-16.5.8-dev.11` 不在包里**，`push/start_patched_frida_server` 要拿到文件放进 `vendor/android_mcp/toolchain/device/frida/` 才能用 |

**没装的只有 `ida-pro`**：ida-pro-mcp 明确写着不支持 IDA Free，只能付费。wasm 用免费的 wabt（`wasm2wat` / `wasm-decompile`，已 `npm i -g`）足够。

`templates/mcp-optional.md` 保留了各 MCP 的配置片段和 `js-reverse-roxy`（在 Roxy 指纹窗里下断点用，见上文接管方式 B），换机器不跑 install.sh 时照着抄。

## 已知环境事实（原装机实测；换机器以当前机器实测为准）

- `node` v24.20.0，`npx` 11.19.0 —— 满足 js-reverse-mcp 的 20.19+ 要求
- PATH 上的 `python3` 是 **macOS 自带 3.9.6（已 EOL）**；真正该用的是 `~/.local/bin/python3.12`。`newrev` 已自动挑最新的，脚本里别硬写 `python3`
- 没装 `brew`。Wireshark 4.4.18 装在 `/Applications`，tshark 不在 PATH 但 WireMCP 会自己去 `.app` 里找
- 开着系统代理时（`HTTPS_PROXY` 有值，端口各机不同，别写死），**Node 的 `fetch` 默认不走这个代理**，所以 cloakbrowser 这类用 fetch 下载的工具会直连 GitHub 然后超时；`install.sh` 已加 `NODE_USE_ENV_PROXY=1` 解决。`js-reverse-cloak` 第一次用时如果二进制不在也会遇到同样问题，所以要靠 install.sh 预下载
- `uv` 在 `~/.local/bin/uv`。`timeout` 命令 macOS 没有，脚本里别用
- **Python `mcp` SDK 2.x 改了 API**（`FastMCP` 改名 `MCPServer`），`frida-mcp` 还在用旧的，必须钉 `mcp<2`，install.sh 已处理
- Reqable 有两个 MCP：社区的 `reqable-mcp`（PyPI，要配 Report Server 推 HAR，且也有 mcp<2 问题）和**官方的 `reqable-mcp-server`**（Dart，随 App 附带在 `Contents/Helpers/mcp-server`，直接读 Reqable 本地 API）。用官方的。
- Reqable 是 Flutter 写的，**辅助功能（AppleScript / System Events）看不到它的界面元素**，只能看到菜单栏。想自动化点它的 GUI 基本没戏，好在官方 MCP 不需要
- wabt 的 GitHub mac 二进制依赖 brew 的 openssl（本机没 brew），所以用 npm 版
- `chrome-devtools` 全局配的是 `--browserUrl http://127.0.0.1:9222`（接管已有 Chrome），所以要先起一个带 `--remote-debugging-port=9222` 的 Chrome，它不会自己拉浏览器

## 改了 skill 之后

全局用的是 `~/.claude/reverse-toolchain/` 里的副本。改了本目录 `skills/` 或 `templates/` 之后**重跑一次 `install.sh`** 同步过去（一秒钟的事）。
