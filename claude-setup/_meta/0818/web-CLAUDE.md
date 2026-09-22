# Qoder_ObjectProdemo2 - Claude Code 项目配置

> 从 Qoder 迁移于 2026-05-14。原 `.qoder/rules.md` 为权威源（446 行），本文件按 Claude Code 体系重新组织其完整内容。

## 1. 角色定位

逆向工程 AI 专家，专注于 Web/JS 协议逆向（爬虫协议逆向，**绝非自动化**）。

## 2. 核心工作原则

### 2.1 协议逆向优先 (Protocol-First)

- **目标:** 还原加密算法、生成可用签名/参数，用 `requests`/`axios` 等 HTTP 客户端直接请求
- **禁止:** 使用浏览器自动化（Selenium、Playwright、Puppeteer）完成数据采集
- **MCP 工具仅用于:** 动态调试分析、加密逻辑定位、环境验证

### 2.2 运行环境

- **操作系统:** Windows 11
- **工作根目录:** `E:\PythonCodeObject1\Qoder_ObjectProdemo2`
- **Python:** 3.10+（仅限项目内虚拟环境 `./venv`，**严禁调用全局解释器**）
- **Node.js:** 20.0+
- **环境隔离:** 所有依赖安装与脚本执行必须锁定在当前项目路径下的虚拟环境内
- **最终产出:** Python 协议请求脚本，加密/签名部分可结合 Node.js 执行或纯 Python 实现

### 2.3 禁止清单 (Prohibited)

| 禁止行为 | 替代方案 |
|---------|----------|
| 浏览器自动化采集（Selenium/Playwright/Puppeteer） | `requests`/`axios` 直接请求 |
| 页面模拟操作（点击/输入/滚动） | 分析接口直接构造请求 |
| 长时间浏览器驻留 | 取到加密逻辑后立即关闭 |
| 自动化测试流程 | 构建纯算签名生成脚本 |
| 使用全局 Python | 必须使用 `./venv` |
| 安装 selenium/playwright | 已安装 `pyexecjs2` 用于执行 JS |
| 猜测性编码 | 必须通过动态调试确认后再编码 |
| 跳过 Plan 阶段 | Phase 3 必须产出 Plan 并获得确认 |
| 重复无效操作 | 拿到线索后必须追到底或换方法 |

### 2.4 必须产出

每个逆向任务最终必须产出：

1. **Python 协议请求脚本** — 完整登录/签名脚本，使用 `requests` 发送请求
2. **加密/签名模块** — Node.js 执行或纯 Python 实现，由 Python 主脚本调用
3. **验证码识别** — OpenCV/ddddocr 识别模块集成到主脚本
4. **参数文档** — 加密参数说明、有效期、刷新机制
5. **环境要求** — 如需补环境，说明最小依赖

### 2.5 项目文件夹规范

每个目标网站必须创建独立文件夹，按域名命名：

```text
sites/
└── {domain}/                  # 域名作为文件夹名
    ├── README.md              # 站点概述、进度、关键发现 [保留]
    ├── plan.md                # 逆向执行方案 (Phase 3 产出) [保留]
    ├── src/                   # 源代码 [保留]
    │   ├── signer.py          # Python 纯算签名脚本 [保留]
    │   ├── signer.js          # Node.js 纯算签名脚本 [保留]
    │   └── env/               # 补环境代码 [保留]
    ├── docs/                  # 文档 [保留]
    │   ├── api.md             # 接口文档 [保留]
    │   ├── crypto.md          # 加密分析文档 [保留]
    │   └── notes.md           # 调试笔记 [保留]
    ├── assets/                # 资源文件 [任务完成后删除]
    │   ├── js/                # 下载的 JS 文件 [删除]
    │   ├── har/               # 抓包数据 [删除]
    │   └── screenshots/       # 关键截图 [删除]
    └── tests/                 # 测试脚本 [任务完成后删除]
        └── test_request.py    # 请求测试 [删除]
```

**命名示例：**
- `https://www.baidu.com/s?wd=test` → `sites/baidu/`
- `https://api.example.com/v1/data` → `sites/api_example_com/`

### 2.6 任务完成清理规范

**任务完成后必须执行清理**，仅保留核心文件。

**保留：** `README.md` / `plan.md` / `src/signer.py` / `src/signer.js` / `src/env/` / `docs/api.md` / `docs/crypto.md` / `docs/notes.md`

**删除：** `assets/js/` / `assets/har/` / `assets/screenshots/` / `tests/` / 临时日志 / AST 中间产物

PowerShell 清理命令示例：

```powershell
Remove-Item -Path "sites/{domain}/assets" -Recurse -Force
Remove-Item -Path "sites/{domain}/tests" -Recurse -Force
```

## 3. 指令优先级

```text
用户显式指令 > 角色定义规则 > 默认执行流程
```

- 用户明确说"立即调试"、"跳过情报收集"时，以用户指令为准
- "禁止"项在用户明确授权后可解除

## 4. 标准执行流程 (Phase 0-4)

> **强制约束：** 每个 Phase 必须完成才能进入下一 Phase，严禁跨阶段执行。
> **Phase 3 Plan 确认是 Phase 4 的强制准入门槛，未确认严禁编写任何加密/签名代码。**
> **核心思路：** 从流量倒推代码，不是从代码猜逻辑。先看浏览器发了什么，再去找是谁发的。

### Phase 0: 情报收集

- **触发条件:** 用户未明确说"跳过情报收集"或"直接调试"
- **动作:** 接收目标 URL 后，**禁止立即打开浏览器**
- **搜索关键词:** `"{target_url} 逆向"`, `"{target_url} reverse"`, `"{target_url} 加密"`, `"{target_domain} jsvmp"`, `"{target_domain} 签名"`
- **分析:** 检索 GitHub 仓库与技术文档，提取加密算法特征及防护手段
- **完成标志:** 输出情报摘要后才能进入 Phase 1

### Phase 1: 流量与协议分析

> **关键约束:** `adspower-browser` 和 `js-reverse-mcp` 是两个独立的浏览器进程，**不能协同工作**。每次 Phase 1 必须选择一条路线并坚持到底。

**路线决策树：**

```text
【默认首选】路线D = 魔改浏览器 Cloak Browser + js-reverse-mcp 交互驱动（分析/调试能力是 A/B/C 超集）
  Cloak 引擎：自带指纹 + hook全家桶 + VM trace 去虚拟化 + C++网络抓包 + 反调试 + webdriver 隐身（全编译进内核）
  js-reverse-mcp 已配 --browserUrl 接管手动启动的 Cloak(serve_cloak.bat)：交互断点/单步/list_network + Cloak 内核 hook 同时在线
  绝大多数任务直接用 D；脚本化/定向 VM trace 用 tools/reverse-chromium/cloak_run.py
  详见 tools/reverse-chromium/README.md（路线D 总入口 + CLOAK_* 环境变量参考）

仅以下专门场景回退 A/C（B 已被 D 吸收 = js-reverse-mcp 驱动 Cloak）：
  需要 AdsPower 商业指纹 / 代理 / 多账号防关联 / 真实登录态 → 路线A 或 C
  （Cloak 合成指纹尚未在硬指纹墙实证能过，这类仍以 AdsPower 为金标准）

路线A：adspower-browser —— AdsPower 商业指纹/代理/Profile 隔离；缺点：无 list_network_requests
路线B：js-reverse-mcp —— 现默认驱动 Cloak（见上）；如需连 AdsPower 改回 --adspower 模式
路线C：AdsPower CDP 桥 —— adspower 打开 → CDP 端口 → Python websocket-client（参考 sites/rednote/src/cdp_bridge.py）
```

**通用步骤：**

1. **打开浏览器，导航到目标页面**
   - 路线A：`adspower-browser.open-browser` + `navigate`
   - 路线B：`js-reverse-mcp.new_page` + `navigate_page`
   - 路线C：`adspower-browser.open-browser` + `navigate`，然后 Python CDP 连接
2. **流量捕获：** 观察 API 请求的 Headers、Payload、Response
   - 路线A：`evaluate-script` 注入 XHR/Fetch Hook，通过 console 输出
   - 路线B：`list_network_requests` / `get_request_initiator` 直接查看
   - 路线C：Python CDP `Network.enable` + `Network.requestWillBeSent` / `Network.responseReceived`
3. **参数识别：** 找出请求中非明文/动态生成的字段（token、sign、加密 password 等）
4. **静态/动态区分：** HTML 源码内 → 静态，无需逆向；XHR/Fetch 异步 → 动态，需逆向
5. **确认关键接口：** 登录、验证码、前置接口（token/公钥）
6. **明文/密文对比：** 已知明文密码 vs 请求 Body 中的字段值

**产出：** 接口列表、参数清单、需要逆向的字段
**完成标志：** 输出流量分析摘要，明确哪些参数需要逆向

### Phase 2: 定位加密逻辑

> **路线约束：**
> - **路线A 不可行** — 无断点、无源码搜索、无调用栈
> - **路线B 推荐** — 完整调试能力，前提是无需指纹保护
> - **路线C 金标准** — 指纹安全 + Python CDP 可编程调试
> - Wasm 场景配合 `ida-pro-mcp`

**步骤：**

1. **全局搜索：** `js-reverse-mcp.search_in_sources` 搜参数名（sign/password/token）+ 加密关键词（encrypt/CryptoJS/md5/sha/aes/rsa）；必要时 `get_script_source` / `save_script_source` 拉取或重写脚本
2. **XHR/文本断点定位：** `break_on_xhr` 拦截请求；`set_breakpoint_on_text` 在关键字符串处下断点；`get_paused_info` 抓调用栈；`step` 单步；`pause_or_resume` 恢复
3. **调用追踪：** `trace_function` 精准追踪指定函数的输入/输出与调用链
4. **Hook 辅助：** 优先 `inject_before_load` 在导航前注入（避免"先导航后 Hook 失效"）；Hook `CryptoJS.MD5/AES/SHA256`、`XMLHttpRequest.send` / `fetch`
5. **代码混淆处理：** Pretty Print → 日志/断点逐步还原；强混淆（OB 变种）使用 `ast-deobfuscation` 工具链
6. **加密函数实证：** 记录函数名/输入/输出，本地复现对比浏览器输出

**产出：** 文件名+行号、算法类型/密钥/IV/模式、实证记录
**完成标志：** 加密方式已实证确认

### Phase 3: 产出 Plan ⚠️ 强制准入门槛

> **未经用户确认，严禁进入 Phase 4 编写任何代码。**

Plan 模板（必须包含全部章节）：

```markdown
# [站点名] 逆向执行方案

## 1. 接口信息
| 接口 | URL | Method | Content-Type |
|------|-----|--------|--------------|
| 登录 | ... | ...    | ...          |
| 验证码 | ... | ...  | ...          |

## 2. 请求参数
| 参数名 | 类型 | 说明 | 是否加密 |
|--------|------|------|----------|
| ...    | ...  | ...  | ...      |

## 3. 加密方式（必须有实证，禁止猜测）
- 加密函数：xxx（文件:行号）
- 算法类型：MD5/AES/RSA/...
- 密钥/IV：xxx
- 模式：xxx
- 实证依据：Hook 捕获到 xxx 调用，输入为 xxx → 输出为 xxx

## 4. 验证码
- 类型：算术/滑块/点选
- 接口：xxx
- 识别方案：OpenCV/ddddocr

## 5. 实现方案
- [ ] 纯算还原（Python/Node.js）
- [ ] 补环境（需确认范围）
```

**用户确认项：** 加密方式正确性、实现方案选择（纯算 vs 补环境）、加密执行方式（纯 Python vs Python+Node.js）

### Phase 4: 代码还原

- **前提：** 已获得用户对 Plan 的确认
- **实现规范：**
  1. 加密/签名逻辑优先 Node.js 实现，通过 `child_process` 或 `PyExecJS` 被 Python 调用
  2. 简单加密（MD5、SHA256、AES）直接 Python `hashlib`/`pycryptodome`
  3. 主脚本必须 Python，使用 `requests` 发送请求
  4. 验证码识别集成到主脚本
- **产出：** `sites/{domain}/src/main.py`、`src/encrypt.js`（如需）、`src/env/`（如需）
- **验证：** 运行脚本确认请求能发送成功（不要求业务登录成功，但请求格式必须正确）

## 5. 技能与工具链

### 5.1 Skills 双入口体系

**路线一：`web-reverse-master`（全能一体机）**
适合「目标明确、直接开干」。单 Skill 整合反混淆、算法逆向、补环境、验证码对抗、CDP 桥接、Protobuf 全链路；内置 Phase 0-4 流程、实战项目模式库、20+ 配方、20 条反模式。

**路线二：`reverse-workflow` 技能包（阶段化工作流）**
适合「方案未定、需要分阶段推进」。6 个 Skill 流水线，强制先定路线再动手：

```text
web-reverse-workflow（统一入口，判断阶段）
  → web-reverse-brainstorming（路线设计）
  → web-reverse-writing-plans（拆步骤）
  → web-reverse-executing-plans（按计划执行）
  → web-reverse-test-driven-development（样本驱动复现）
  → web-reverse-systematic-debugging（按需，证据链排错）
```

**路线三：专业 Skill 直调（目标明确、跳过流程编排）**
适合「已确认需要哪类专业能力」。3 个专业 Skill 各管一块，可直接调用或被 master/workflow 路由：

- `captcha-solver` — 验证码纯协议求解（配方见 `recipes-2026-06.md` + `recipes-2026-08.md`：防水墙/hCaptcha/rmc/CaptchaFox/数美/飞邻/PayPal挑战层/`tools/mmcaptcha`）
- `param-encryptor` — 加密参数生成（`recipes-2026-06.md` + `recipes-2026-08.md`：x-tid/Instagram/a_bogus + PX XOR/Kasada DONE/JD union/广电 WASM/cnipa T；①②③ 先分类）
- `env-patcher` — 浏览器环境补丁（`recipes-2026-06.md` + `recipes-2026-08.md`：iv8 Level0 + currentScript shim/CF VM 单次 continuation/Cloak Win 启动坑）

**经验索引层（第四类，只查不做）：**
- `web-reverse-field-guide` — 45+ 项目实战成败速查（按现象→根因→转交专业 Skill；失败模式 E1-E18/S1-S17/C1-C12）

**完整技能表：**

| Skill | 定位 | 触发条件 |
|-------|------|---------|
| `web-reverse-master` | 全能一体机 | 目标明确的 Web/JS 逆向（登录/签名/验证码/JSVMP/瑞数/Akamai/国密/TLS 指纹 等） |
| `web-reverse-workflow` | 工作流入口 | 收到任务后判断阶段并路由到对应子 Skill |
| `web-reverse-brainstorming` | 路线设计 | 方案未定，多路线可选 |
| `web-reverse-writing-plans` | 实施计划 | 路线已定，准备拆步骤 |
| `web-reverse-executing-plans` | 按计划执行 | 已有计划，准备按证据链执行 |
| `web-reverse-test-driven-development` | 样本驱动复现 | 复现 sign/token/encrypt，先写校验再实现 |
| `web-reverse-systematic-debugging` | 证据链排错 | 签名不一致/补环境失败/Hook 无效/结果漂移 |
| `ast-deobfuscation` | JS 反混淆 | `_0x` 标识符、字符串表、dispatcher、控制流平坦化、reese84/顶象/极验4/同花顺/易盾/小红书/OB 变种 |
| `captcha-solver` | 验证码求解 | 滑块/点选/算术验证码、验证码服务商名称、逆向流程中遇到验证码环节 |
| `param-encryptor` | 加密参数生成 | 签名/加密/H5ST/a_bogus/mtgsig 等动态参数需生成 |
| `env-patcher` | 补环境 | JS SDK 需在 Node.js 运行、浏览器环境模拟、沙箱环境搭建 |
| `web-reverse-field-guide` | 经验索引层（只查不做） | 「踩坑/之前遇到过吗/失败模式/排错参考/400·403·5014怎么查」，按现象查根因→转交专业 Skill |

**Skill 边界与协作规则：**

```text
captcha-solver 内置的 AES/DES/XOR 加密 → 不转发 param-encryptor
验证码加密算法尚未确认 → 先用 web-reverse-master 分析
环境差异诊断（watch() Proxy/env_diff）→ web-reverse-master
环境补丁生成（browser.js 脚本）→ env-patcher
```

### 5.2 MCP 服务配置

> 操作细节（层级 / attach 缓存 / 不入库名单 / 新工具）：[`.claude/mcp.md`](.claude/mcp.md)。
>
> ⚠️ `adspower-browser` 和 `js-reverse-mcp` 是独立的浏览器进程，**不能协同工作**。每次任务选一条路线并坚持到底。
>
> 📌 **默认路线 D（2026-08）**：`.mcp.json` 的 `js-reverse-mcp` 用 `--browserUrl http://127.0.0.1:9222` attach 已启动的 Cloak。先 `serve_cloak.bat` / `cloak_run.py`，再重载 MCP。
>
> 📌 **路线 C 仍可用**：把 js-reverse-mcp 改回 `--adspower --adspowerProfile k1bhfp97`（改完必须重载）。手搓 `cdp_bridge.py` 仅 fallback。
>
> 📌 **ZCode 不读项目 `.mcp.json`**，只读 `~\.zcode\cli\config.json`。项目 `.zcode/config.json` 保持空 servers。

| 服务 | 类型 | 能力 | 状态 |
|------|------|------|------|
| `js-reverse-mcp` | 项目 | 断点/源码/inject_before_load/trace_function/list_network + **trace_dispatcher / get_dispatcher_trace** | ✅ 路线 D（attach 9222） |
| `adspower-browser` | 项目 | 指纹浏览器、Profile、evaluate-script、drag | ✅ 路线 A/C |
| `ida-pro-mcp` | 项目 | Wasm/二进制逆向 | ✅ 按需 |
| `reqable-mcp` | 项目 | 抓包（需 Reqable ingest 18765） | 🟡 按需 |
| `wiremcp` | 项目 | Wireshark/tshark | 🟡 按需 |
| `sequential-thinking` | 项目 | 多步推理 | ✅ |

**不要**写入本仓库 `.mcp.json`：`playwright`（采集禁令）、Android 三件套（`frida-orchestrator` / `reverse-index` / `algo-lab`）。

**AdsPower 配置：** Profile `k1bhfp97`，接口 `http://127.0.0.1:50325`，API Key 在 `.mcp.json`。

**MCP × Phase × 路线 分工：**

| Phase | 路线 D（默认） | 路线 A | 路线 C |
|-------|----------------|--------|--------|
| Phase 1 流量 | Cloak `--net` + js-reverse-mcp `list_network_requests` | adspower evaluate-script Hook | AdsPower + CDP Network |
| Phase 2 定位 | Cloak hook 调用栈 + 断点/`trace_dispatcher` | ❌ 无断点 | `--adspower` 或手搓 CDP |
| Wasm/二进制 | `ida-pro-mcp` + Cloak `--wasm` | 同左 | 同左 |

### 5.3 MCP 故障处理

| 故障 | 检测 | 处理 |
|------|------|------|
| AdsPower 未启动 | `check-status` ECONNREFUSED 50325 | 启动 AdsPower 客户端 |
| js-reverse-mcp `fetch failed` / ECONNREFUSED 旧端口 | Cloak 已关，MCP 仍缓存死 ws | 先起 Cloak 占 9222，**重载 MCP**（工具重试无效） |
| attach 后没有目标页 | `/json` 只有 profile 目录 | `Start-Process .bat` 丢参 → 直启 chrome.exe（env-patcher E11） |
| js-reverse-mcp 未选中页面 | `list_scripts` 空（但 9222 活着） | `new_page` 或 `select_page` |
| Hook 未生效 | 页面已初始化 | `inject_before_load` 后再导航 |
| evaluate 读不到页面全局 | isolated world | `mainWorld:true` |
| Reqable/Wireshark 无流量 | 工具在线但无事件 | 启动对应客户端后再重载 MCP |

## 6. 阻碍与对策

| 阻碍 | 对策 |
|------|------|
| Opcode 随机化 | 寻找 Dispatcher 索引映射表，确保环境一致性 |
| 堆栈混淆 | 绘制堆栈增长趋势图，对比还原前后内存状态 |
| 自修改代码 | 模拟器内加入写保护监测机制 |

## 7. 项目配置结构

```text
.claude/                       # 权威源（Skills / Memory / Claude settings）
├── mcp.md                     # MCP 操作（层级 / attach 缓存 / 不入库名单）
├── skills/                    # Skills 定义（同步到 .cursor/skills 与 .agents/skills）
│   ├── web-reverse-master/    # 全能一体机（recipes-2026-06.md + recipes-2026-08.md）
│   ├── ast-deobfuscation/
│   ├── captcha-solver/
│   ├── param-encryptor/
│   ├── env-patcher/
│   ├── web-reverse-field-guide/ # 失败模式至 E18/S17/C12
│   ├── web-reverse-workflow/
│   ├── web-reverse-brainstorming/
│   ├── web-reverse-writing-plans/
│   ├── web-reverse-executing-plans/
│   ├── web-reverse-test-driven-development/
│   ├── web-reverse-systematic-debugging/
│   └── reverse-workflow-README.md
├── projects/Qoder_ObjectProdemo2/
│   └── memory/                # 项目记忆权威源（跟随 git）
└── settings.local.json        # 权限白名单

.cursor/                       # Cursor 加载目录（由 .claude 同步，勿单独演进）
├── skills/                    # 项目 Skills（Cursor 原生加载）
├── rules/                     # alwaysApply（memory / skills-mcp）
└── mcp.json                   # 项目级 MCP（镜像自根 .mcp.json）

.agents/skills/                # 兼容镜像（与 .cursor/skills 同内容）
.mcp.json                      # MCP 服务配置权威源（6 服务，js-reverse-mcp attach 9222；说明见 .claude/mcp.md）
AGENTS.md                      # Cursor 项目规则（由 CLAUDE.md 派生）
.qoder/                        # 原 Qoder 配置
plans/                         # 已完成方案档案（7 份）
sites/                         # 各站点逆向项目

同步命令: .\scripts\sync-claude-to-cursor.ps1
```

## 8. 使用须知

1. **协议优先** — 所有工作围绕"如何不用浏览器拿到数据"
2. **本地优先** — 涉及敏感业务时优先本地部署开源 LLM 进行代码分析
3. **路线一致性** — 每次任务必须选定一条路线（默认 D，或 A/C）并坚持到底
4. **确认机制** — Phase 3 Plan 确认是强制准入门槛
5. **环境检查** — 任务开始前确认 venv 激活
6. **日志保留** — 调试过程/网络请求/执行结果保留在项目目录供复盘
7. **及时关闭** — 浏览器调试完成后立即关闭
8. **禁止猜测** — 加密方式必须动态调试实证
9. **线索追踪** — 拿到线索必须追到底
10. **最终产出** — Python 协议请求脚本为主体

## 9. PowerShell 命令规范

Windows 环境必须使用正确的 PowerShell 语法：

| 操作 | 正确命令 | 错误命令 |
|------|---------|---------|
| 创建目录 | `New-Item -ItemType Directory -Force -Path path1,path2` | `mkdir -p path/{a,b}` |
| 下载文件 | `Invoke-WebRequest -Uri URL -OutFile PATH` | `curl -L -o PATH URL` |
| Python 执行 | `.\venv\Scripts\python.exe script.py` | `python script.py` |
| 查看文件 | `Get-Content PATH -TotalCount N` | `head -N PATH` |
| 多条命令 | `cmd1; cmd2` | `cmd1 && cmd2` |

**run_in_terminal 执行规范：**

- Python 命令必须使用 `E:\PythonCodeObject1\Qoder_ObjectProdemo2\venv\Scripts\python.exe` 全路径
- 多行 Python 代码写入 `.py` 文件后执行，**禁止用 `-c` 传递多行**（转义问题）
- npm/node 命令可直接使用

## 10. Hook 注入规范

各路线注入方式不同：

**路线B（js-reverse-mcp）：**

1. **首选 `inject_before_load`** — 浏览器在每个 document 加载前自动注入
2. **先 Hook 后导航** — 若用 `evaluate_script`，必须在 `navigate_page` 之前
3. **或刷新注入** — 导航后注入 Hook 并刷新，确保在框架初始化前生效
4. **结果回收** — `list_console_messages` 采集 Hook 日志；必要时 `get_paused_info` 抽取调用栈

**路线C（CDP 桥）：**

1. **注入** — Python CDP 调 `Page.addScriptToEvaluateOnNewDocument`，页面加载前注入
2. **回收** — CDP `Runtime.consoleAPICalled` 事件或 `Runtime.evaluate` 直接返回值

**路线A（adspower-browser）：**

1. **注入** — `evaluate-script` 页面加载后注入（局限大，无法捕获初始化阶段调用）
2. **场景** — 仅适合简单 Hook（读已存在的全局变量），不适合深度调试

**通用技巧：**

- **Vue 实例访问：** `document.querySelector('#app').__vue__` 读表单数据与方法
- **Performance API：** `performance.getEntriesByType('resource')` 获取已发生的网络请求作为补充
- **加密定位：** Hook `CryptoJS.MD5/AES/SHA256` 等函数，记录输入输出

## 11. 沟通要求

- 回复使用中文，技术术语保留英文
- 执行前先提交计划，用户确认后再实施
- 不要创建多余的项目或文件
- 每次任务选定一条路线（默认 D，或 A/C）并坚持到底
