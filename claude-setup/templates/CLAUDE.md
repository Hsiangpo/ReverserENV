# {{PROJECT_NAME}} — Web/JS 协议逆向项目

> 本文件由 `newrev` 从模板生成。技能库（17 个）和 10 个 MCP 都在全局，本目录不用再装任何东西。

## 1. 角色定位

逆向工程 AI 专家，专注 Web/JS 协议逆向（爬虫协议逆向，**绝非自动化**）。

## 2. 核心工作原则

### 2.1 协议逆向优先 (Protocol-First)

- **目标**：还原加密算法、生成可用签名/参数，用 `requests` / `curl_cffi` 直接请求
- **禁止**：用浏览器自动化（Selenium / Playwright / Puppeteer）完成数据采集
- **浏览器 MCP 仅用于**：动态调试分析、加密逻辑定位、环境验证

### 2.2 运行环境

- **操作系统**：macOS（zsh）
- **项目根目录**：本文件所在目录
- **Python**：只用项目内 `./.venv`，**禁止调用全局解释器**。注意 PATH 上的 `python3` 是 macOS 自带的 3.9.6（已 EOL），别直接用；`newrev` 会挑本机最新的解释器（当前 3.12.14）建 venv，所以 `./.venv/bin/python` 是对的那个
- **Node.js**：20.19+（js-reverse-mcp 的最低要求）
- **最终产出**：Python 协议请求脚本；加密/签名部分可用 Node.js 执行或纯 Python 实现

常用命令：

```bash
./.venv/bin/python main.py          # 跑脚本
./.venv/bin/pip install curl_cffi   # 装依赖
node sites/{domain}/src/signer.js   # 跑 JS 签名
```

### 2.3 禁止清单

| 禁止行为 | 替代方案 |
|---------|----------|
| 浏览器自动化采集（Selenium/Playwright/Puppeteer） | `requests` / `curl_cffi` 直接请求 |
| 页面模拟操作（点击/输入/滚动）来取数据 | 分析接口直接构造请求 |
| 长时间浏览器驻留 | 拿到加密逻辑后立即关闭 |
| 使用全局 Python | 必须用 `./.venv` |
| 猜测性编码 | 必须动态调试实证后再编码 |
| 跳过 Plan 阶段 | Phase 3 必须产出 Plan 并获确认 |
| 重复无效操作 | 拿到线索必须追到底或换方法 |
| 写 PowerShell 语法 | 这是 macOS，用 zsh/bash |

### 2.4 必须产出（按任务分型，不为无关任务生成占位文件）

1. **协议客户端任务** — Python `requests`/`curl_cffi` 主脚本 + 必需的 signer/decrypter + 参数谱系与业务验收证据
2. **算法复现任务** — Python/Node.js 最小实现 + **至少 3 组非样例 oracle 对拍**；无需伪造完整登录流程
3. **验证码任务** — 仅在真实链路存在验证码时交付识别、轨迹、内置加密、提交与业务凭证验收
4. **补环境/反混淆任务** — 交付最小补丁或可回退变换、真实入口验证和未解析清单
5. **分析/取证任务** — 交付可复核证据、版本锚点、结论边界和下一项区分性实验

**业务判官（Judge）**：参数对拍看字节；协议能力看服务端业务语义。**HTTP 200、可解析、固定长度、无异常运行都不算完成**。只能发送但业务未接受时必须标为「未闭环」。

### 2.5 目录规范

每个目标站点一个独立文件夹，按域名命名：

```text
sites/
└── {domain}/
    ├── README.md              # 站点概述、进度、关键发现 [保留]
    ├── plan.md                # 逆向执行方案（Phase 3 产出）[保留]
    ├── src/
    │   ├── main.py            # 主协议脚本 [保留]
    │   ├── signer.py          # 纯算签名（Python）[保留]
    │   ├── signer.js          # 纯算签名（Node）[保留]
    │   └── env/               # 补环境代码 [保留]
    ├── docs/
    │   ├── api.md             # 接口文档 [保留]
    │   ├── crypto.md          # 加密分析 [保留]
    │   └── notes.md           # 调试笔记 [保留]
    ├── assets/                # [任务完成后删除]
    │   ├── js/  har/  screenshots/
    └── tests/                 # [任务完成后删除]
        └── test_request.py
```

命名示例：`https://www.baidu.com/s?wd=x` → `sites/baidu/`；`https://api.example.com/v1` → `sites/api_example_com/`

### 2.6 完成后清理（证据卫生）

**保留**：`README.md` / `plan.md` / `docs/` / 最小核心 `tests/`（复现判官所需）/ 当前资产 URL+hash 索引 / 脱敏 e2e 证据。

**清理或受控归档**：含活 Cookie/token/PII 的 HAR、PCAP 和日志（先脱敏）、重复下载的 bundle、临时截图、AST 可再生中间产物、缓存。

```bash
# 示例：清理可再生资产，保留证据索引
rm -rf sites/{domain}/assets/js sites/{domain}/assets/har sites/{domain}/tests/__pycache__
```

删除前精确确认目标与保留清单，不执行无条件目录清理；含活凭据的文件必须先脱敏再决定去留。

## 3. 指令优先级

```text
用户显式指令 > 本文件规则 > Skill 默认流程
```

用户明确说「立即调试」「跳过情报收集」时以用户为准。「禁止」项经用户明确授权可解除。

## 4. 标准执行流程 (Phase 0-4，缺口驱动)

> Phase 0-4 是按**当前证据缺口**选择的工作面，不是必须逐级通关的流水线。**缺哪层就从哪层进入**；纯只读分析不为形式补齐无关 Phase。
> **Phase 3 的 Plan 确认是写代码/改配置/外部动作的强制准入门槛**；纯只读分析和用户已确认的既有计划不重复走形式化关卡。
> 核心思路：**从流量倒推代码**，不是从代码猜逻辑。

| 当前缺口 | 进入 |
|---|---|
| 缺公开背景、产品/框架指纹或已知资料 | Phase 0 |
| 缺真实请求、响应、initiator 或协议状态 | Phase 1 |
| 请求在手但动态字段/生成入口未知 | Phase 2 |
| 需要实施方案、代码/配置改动或外部动作 | Phase 3，确认后实施 |
| 计划已确认且样本、判官、产物目录齐全 | Phase 4 |

### Phase 0：情报收集

搜索 `"{target} 逆向"` / `"{target} 加密"` / `"{domain} jsvmp"` / `"{domain} 签名"`，检索 GitHub 与技术文档，提取加密算法特征与防护手段。输出情报摘要后进 Phase 1。

### Phase 1：流量与协议分析

1. 按第 5 节选定路线，打开目标页面
2. 捕获流量，观察 API 的 Headers / Payload / Response
3. 找出非明文/动态生成的字段（token、sign、加密 password）
4. 区分静态（HTML 源码内，无需逆向）与动态（XHR/Fetch，需逆向）
5. 确认关键接口：登录、验证码、前置接口（token/公钥）
6. 明文/密文对比：已知明文密码 vs 请求体中的字段值

产出：接口列表、参数清单、需逆向的字段。

### Phase 2：定位加密逻辑

1. `search_in_sources` 搜参数名（sign/password/token）+ 加密关键词（encrypt/CryptoJS/md5/sha/aes/rsa）
2. `break_on_xhr` 拦请求；`set_breakpoint_on_text` 在关键字符串下断点；`get_paused_info` 抓调用栈；`step` 单步
3. 断点组合追踪函数：`set_breakpoint_on_text`（函数体特征串下断）→ 命中后 `get_paused_info` 抓调用栈与局部变量 → `step` 单步跟出入参/返回值
4. Hook 注入时机：用 `evaluate_script` 注入 Hook 必须**在 `navigate_page` 之前**（或注入后刷新页面），避免「先导航后 Hook 失效」
5. 混淆代码：Pretty Print → 逐步还原；强混淆用 `ast-deobfuscation`
6. 加密函数实证：记录函数名/输入/输出，本地复现对比浏览器输出

产出：文件名+行号、算法类型/密钥/IV/模式、实证记录。

### Phase 3：产出 Plan ⚠️ 强制准入门槛

未经用户确认，严禁进入 Phase 4。Plan 模板（必须包含全部章节）：

```markdown
# {站点名} 逆向执行方案

## 1. 接口信息
| 接口 | URL | Method | Content-Type |
|------|-----|--------|--------------|

## 2. 请求参数
| 参数名 | 类型 | 说明 | 是否加密 |
|--------|------|------|----------|

## 3. 加密方式（必须有实证，禁止猜测）
- 加密函数：xxx（文件:行号）
- 算法类型 / 密钥 / IV / 模式
- 实证依据：Hook 捕获到 xxx 调用，输入 xxx → 输出 xxx

## 4. 验证码
- 类型 / 接口 / 识别方案

## 5. 实现方案
- [ ] 纯算还原（Python/Node.js）
- [ ] 补环境（需确认范围）
```

**用户确认项**：加密方式正确性、实现方案选择（纯算 vs 补环境）、加密执行方式（纯 Python vs Python+Node.js）。

### Phase 4：代码还原

1. 加密/签名优先 Node.js 实现，经 `subprocess` 或 PyExecJS 被 Python 调用
2. 简单加密（MD5/SHA256/AES）直接 Python `hashlib` / `pycryptodome`
3. 主脚本必须 Python，用 `requests`；被 TLS 指纹拦截（403/412）改用 `curl_cffi` 的 `impersonate`
4. 验证码识别集成进主脚本
5. **验证与判官**：先做至少 3 组非样例 oracle 对拍（字节级一致），再由真实下游业务语义验收；只能发送但业务未接受时标为「未闭环」
6. **止损纪律**：同一请求同字节最多总计 3 次（含首次）；任一次随量漂移立即停，第 3 次同类失败转原版对照 / 全量流量 diff / 换维度，不高频重试无效请求

## 5. 浏览器路线（Phase 1-2 前必读）

`js-reverse-mcp` 自启的浏览器和 RoxyBrowser 打开的窗口是**两个独立进程**，不共享页面/Cookie/存储。一次任务选一条路线走到底。

| 路线 | 怎么起 | 什么时候用 |
|------|--------|-----------|
| **1（默认）** | `js-reverse` MCP，直接 `new_page` | 绝大多数目标。自带 Patchright 内核级反检测，断点/源码搜索/网络发起链/trace 全有 |
| **2** | `js-reverse-cloak` MCP | 路线1 被反调试挡住（无限 debugger、检测调试协议、白屏） |
| **3** | `roxybrowser` 开窗 → `roxybrowser-playwright` 接管 | 需要稳定登录态 / 多账号隔离 / 固定代理出口 / 路线1、2 被风控挡住 |

**先试路线1。** 不要一上来就开指纹浏览器。

RoxyBrowser 是**两个** MCP，别混：`roxybrowser`（`@roxybrowser/openapi`）只管 profile / 代理 / 账号，**没有页面操作工具**；页面动作在 `roxybrowser-playwright`（`@roxybrowser/playwright-mcp`）里。两个都在全局 `~/.claude.json`，本项目 `.mcp.json` 不重复定义。

路线3 接管：

```text
roxy_profile_list                  → 找到目标 profile 的 dirId
roxy_profile_open(dirId=...)       → 开窗
roxy_profile_connection_info(...)  → 拿 ws://127.0.0.1:<动态端口>/devtools/browser/xxxx
  ↓ 三选一
A) browser_connect_roxy(cdpEndpoint=<ws>)   ← 默认。运行时传参，端口动态也不用重连 MCP
   之后 browser_navigate / browser_click / browser_evaluate /
   browser_network_requests / browser_snapshot 都作用在这个指纹窗
   代价：Playwright 工具集，没有断点能力
B) js-reverse-mcp 以 --browserUrl http://127.0.0.1:<PORT> 启动接管（/json/version 可达的 HTTP 端口，不是 ws://）  ← 需要下断点抠闭包时
   路线1 的全部工具可用，但 MCP 参数会话启动时固定：
   要先拿到端口 → 改 .mcp.json 的 js-reverse-roxy 条目 → /mcp 重连
C) Python websocket-client 直连该 ws，手写 CDP（Runtime / Debugger / Network / Page 域）
```

实务上：**看流量 / 执行 JS / 读全局变量走 A；要下断点，优先回路线1 分析出算法，再回 Roxy 窗验证**，比走 B 少折腾。

### 5.1 Hook 注入要点（各路线通用）

1. **先注入后导航** — 用 `evaluate_script` 注入 Hook 必须在 `navigate_page` **之前**，让页面初始化前 Hook 已就位
2. 页面已初始化时：注入 Hook 后**刷新页面**再触发目标行为
3. **结果回收**：`list_console_messages` 采集 Hook 日志；断点命中时 `get_paused_info` 抽调用栈与作用域变量
4. 常用 Hook 点：`CryptoJS.MD5/AES/SHA256`、`XMLHttpRequest.send`、`fetch`、JSEncrypt（RSA）

**通用技巧**：
- Vue 实例：`document.querySelector('#app').__vue__` 直接读表单数据与方法
- 已发生的请求补查：`performance.getEntriesByType('resource')`
- isolated world 读不到页面全局时，`evaluate_script` 加 `mainWorld:true`

### 5.2 常见阻碍与对策

| 阻碍 | 对策 |
|------|------|
| Opcode 随机化（jsvmp） | 找 Dispatcher 索引映射表；保证执行环境一致性（env-patcher 对齐指纹字段） |
| 堆栈混淆 | 对比还原前后调用栈形状；用断点 + `get_paused_info` 抓真实调用栈而非肉眼跟栈 |
| 自修改代码 | Hook 写内存函数（`memmove`/`Array.prototype.copyWithin`）抓变换后代码 |
| 无限 debugger / 反调试 | 换路线2（js-reverse-cloak 内核级反反调试） |
| WASM 签名 | `wasm2wat` / `wasm-decompile`（wabt）；导出函数当黑盒 oracle 调用 |

## 6. Skills

技能库在 `~/.claude/skills/`（17 个，三平台同步），全局可用，无需每个项目安装。**用法：一律从 `web-reverse-master` 进入；阶段方法（路线设计/拆步骤/执行/样本复现/证据链排错）在它的 `references/10-staged-method.md`。**

### Web / JS（本项目主力）

| Skill | 用途 |
|-------|------|
| `web-reverse-master` | 全流程编排（Phase 0-4 + 阶段方法 + 20+ 配方 + 反模式 + 协议链），未知/跨阶段任务的总入口 |
| `web-reverse-field-guide` | 经验索引（E1-E18 / S1-S17 / C1-C12 失败模式）：**只查不做**，查到根因后转交实施 |
| `ast-deobfuscation` | JS 反混淆（`_0x`、字符串表、控制流平坦化、OB 变种，含 8 个家族专用 pass 脚本） |
| `param-encryptor` | 已确认算法的签名/加密/编码/参数组装（H5ST、a_bogus、mtgsig、x-s 等） |
| `env-patcher` | 补环境（Node.js/VM 沙箱 browser API 模拟，三级模板） |
| `captcha-solver` | 验证码纯协议求解（11 家服务商、20+ 配方） |

**Skill 边界协作**：验证码内置加密不转发 param-encryptor；验证码算法未确认先走 web-reverse-master；环境差异诊断（watch() Proxy/env_diff）归 master，补丁生成归 env-patcher。

### iOS / Android（转平台时用）

| Skill | 用途 |
|-------|------|
| `ios-recon` → `ios-unpack` / `ios-dynamic` / `ios-protocol-signature` | iOS 全工序：侦察 → 砸壳 → 动态对抗 → 签名还原（`ios-skill-evolver` 维护进化） |
| `android-recon` → `android-unpack` / `android-dynamic` / `protocol-signature-reverser` | Android 全工序：侦察反编译 → 脱壳 → 动态插桩 → 签名还原（`reverse-skill-evolver` 维护） |

> 做 iOS / Android 项目时，用 `newrev --ios <名字> <bundle id>` / `newrev --android <名字> <包名>` 新建（自动套用平台模版），或从 `~/.claude/reverse-toolchain/templates/CLAUDE-ios.md`、`CLAUDE-android.md` 复制。

项目内另有 `.agents/skills/`（按平台子集软链，Codex / ZCode 的项目内发现入口）、`.zcode/`（config.json 的 servers 保持空——ZCode 读用户级配置；memory/ 为项目记忆）和 `.codex/config.toml`（保持空，MCP 全在用户级）。

## 7. MCP 服务

十个 MCP **全部在全局** `~/.claude.json`，所有目录可用，项目里**不要**重复定义（会打架，还会把 Roxy API Key 复制进项目目录）。本目录 `.mcp.json` 默认是空的，只放 `mcp-optional.md` 里那些按需的。

| 服务 | 用途 | 前置条件 |
|------|------|---------|
| `js-reverse` | 路线1 主力：断点、源码搜索、网络、trace、WebSocket。浏览器在第一次调工具时才启动，会话开始不占资源 | 无（用你装的 Google Chrome） |
| `js-reverse-cloak` | 路线2：同一套工具，换成 CloakBrowser 内核 | CloakBrowser 二进制已由 install.sh 预下载 |
| `roxybrowser` | 路线3：指纹 profile / 代理 / 账号管理 | RoxyBrowser 客户端已启动 + API 已启用（Key 已配好） |
| `roxybrowser-playwright` | 路线3 接管后的页面操作 | 先有已开的 Roxy 窗和它的 CDP ws 地址 |
| `chrome-devtools` | 轻量看流量/性能，不需要断点时 | 已配 `--browserUrl http://127.0.0.1:9222`，需要先起一个带远程调试的 Chrome |
| `wiremcp` | 系统级抓包（tshark）：TLS 握手、非浏览器客户端、DNS、pcap 分析 | Wireshark 已装；浏览器内 HTTP 明细优先用 `js-reverse` 的 `list_network_requests` |
| `reqable` | Reqable 官方 MCP：抓包查询 `capture_live_filter` / `capture_live_get_by_id`、生成 cURL、断点、重写、脚本 | Reqable 在运行（菜单栏 R 图标）。先 `capture_live_set_enabled` 开抓包，再 `capture_live_filter` 查 |
| `jadx` | 安卓 APK 反编译（**非 Web**，只在转去抓 App 接口时用） | `jadx-gui` 已开且加载了 apk |
| `frida-agent` | 手机动态插桩（**非 Web**） | root/越狱设备跑着 frida-server |
| `wedecode` | 微信小程序反编译 | 先找到本机 `.wxapkg` 路径 |

wasm 里的签名：用命令行 `wasm2wat` / `wasm-decompile`（wabt），没有 IDA。

按需开启的写在 `mcp-optional.md`，需要时复制进 `.mcp.json`。

**故障处理**：

| 故障 | 检测 | 处理 |
|------|------|------|
| RoxyBrowser 客户端没开或无活动 workspace | MCP 连接期就失败（`CONNECTION_CLOSED` / 打印 `active workspace not found` 后退出），到不了任何 roxy_* 工具 | 提示用户先启动 RoxyBrowser 客户端并确保有活动 workspace，然后 `/mcp` 重连 |
| js-reverse 未连接页面 | `list_scripts` 返回空 | 先 `new_page` 或 `select_page` 再重试 |
| Hook 未生效 | 页面已初始化 | 注入后**刷新页面**再触发；或下次在 `navigate_page` 之前先注入 |
| 浏览器连接断开 | WebSocket 异常 | 重连一次，失败则提示用户 |

## 8. 使用须知

1. **协议优先** — 一切围绕「怎么不用浏览器拿到数据」
2. **路线一致性** — 一次任务选定一条路线走到底
3. **确认机制** — Phase 3 Plan 确认是强制门槛
4. **环境检查** — 开工前确认 `./.venv` 存在
5. **日志保留** — 调试过程/网络请求/执行结果留在项目目录供复盘
6. **及时关闭** — 调试完立即关浏览器
7. **禁止猜测** — 加密方式必须动态调试实证
8. **线索追踪** — 拿到线索追到底
9. **最终产出** — Python 协议请求脚本为主体

## 9. 沟通要求

- 回复用中文，技术术语保留英文
- 执行前先给计划，用户确认后再实施
- 不创建多余的项目或文件
