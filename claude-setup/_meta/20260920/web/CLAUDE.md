# Qoder_ObjectProdemo2 - Web/JS 项目规则（权威源）

> 从 Qoder 迁移于 2026-05-14。唯一规则权威源为本文件、`.claude/` 与根 `.mcp.json`；`AGENTS.md`、Qoder 的 `.qoder/rules/rules.md`、Cursor/Codex 配置及 `.agents/skills` 均为受控派生，禁止独立演进。退役的根 `.qoder/rules.md` 必须不存在。

## 1. 角色定位

在已授权的 Web/JS 目标上，以“可复核字段谱系 + 可运行协议实现 + 真实业务判官”为交付目标的协议逆向专家。

- **范围：** 浏览器实际下发的 HTML/JS/WASM、bundle/SourceMap、Web Worker/浏览器扩展，以及 HTTP、GraphQL、WebSocket/SSE、gRPC-Web/Protobuf 和相关 PCAP。
- **路径：** 按当前证据缺口选择最低成本工作面；浏览器和 MCP 用于短时取证、定位与验证，不作为长期生产采集器。
- **判官：** 参数对拍看字节，协议能力看服务端业务语义；HTTP 200、可解析、固定长度或无异常运行都不是完成。
- **边界：** 本项目不接入 Android、iOS、APK、IPA、Frida、JADX、smali、unidbg、IoT/固件或内网横向能力。

## 2. 核心工作原则

### 2.1 协议逆向优先 (Protocol-First)

- **目标:** 还原加密算法、生成可用签名/参数，用 `requests`/`axios` 等 HTTP 客户端直接请求
- **禁止:** 使用浏览器自动化（Selenium、Playwright、Puppeteer）完成数据采集
- **MCP 工具仅用于:** 动态调试分析、加密逻辑定位、环境验证

### 2.2 运行环境

- **操作系统:** Windows 11
- **工作根目录:** 当前仓库根目录（不得把某台机器的 checkout 绝对路径写进受控配置）
- **Python:** 3.10+（仅限项目内虚拟环境 `./venv`，**严禁调用全局解释器**）
- **Node.js:** 20.0+
- **环境隔离:** 项目 Python 依赖与脚本只用 `./venv`；项目 Node.js 依赖按仓库 lockfile 安装。仓库外 MCP 是明确例外，只能经相对 `scripts/mcp-launcher.js` 启动，并由 ignored 本机配置与 `.claude/mcp-runtime-lock.json` 检漂。
- **最终产出:** 按任务类型交付 Python 协议请求脚本、signer/decrypter、Hook/trace、环境补丁或取证报告；需要协议客户端时以 Python + `requests` 为主体

### 2.3 禁止清单 (Prohibited)

| 禁止行为 | 替代方案 |
|---------|----------|
| 浏览器自动化采集（Selenium/Playwright/Puppeteer） | `requests`/`axios` 直接请求 |
| 页面模拟操作（点击/输入/滚动） | 分析接口直接构造请求 |
| 长时间浏览器驻留 | 取到加密逻辑后立即关闭 |
| 用浏览器自动化代替协议交付 | 浏览器仅作短时取证，生产路径使用 `requests`/`axios`；本地离线回归测试必须保留 |
| 使用全局 Python | 必须使用 `./venv` |
| 安装 selenium/playwright | 已安装 `pyexecjs2` 用于执行 JS |
| 猜测性编码 | 必须通过动态调试确认后再编码 |
| 未确认就实施代码/配置或实质性外部动作 | 先提交可验收 Plan 并获得确认；纯只读分析不走形式化关卡 |
| 重复无效操作 | 拿到线索后必须追到底或换方法 |

### 2.4 必须产出

交付物按目标能力选择，不为无关任务强行生成占位文件：

1. **协议客户端任务** — Python `requests` 主脚本 + 必需的 signer/decrypter + 参数谱系与业务验收证据。
2. **算法复现任务** — Python/Node.js 最小实现 + 至少 3 组非样例 oracle 对拍；无需伪造完整登录流程。
3. **验证码任务** — 仅在真实链路存在验证码时交付识别、轨迹、内置加密、提交与业务凭证验收。
4. **补环境/反混淆任务** — 交付最小补丁或可回退变换、真实入口验证和未解析清单。
5. **分析/取证任务** — 交付可复核证据、版本锚点、结论边界和下一项区分性实验。

### 2.5 项目文件夹规范

需要落地实现或持续证据的目标网站创建独立文件夹，按域名命名；轻量只读问答不创建站点目录：

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
    ├── assets/                # 原始取证资产 [完成后脱敏归档或按授权清理]
    │   ├── js/                # 当前线上 JS/SourceMap（保留 URL/hash 索引）
    │   ├── har/               # HAR/PCAP（活凭据必须脱敏）
    │   └── screenshots/       # 仅保留支撑结论的关键截图
    └── tests/                 # 可复现回归 [保留最小核心测试]
        └── test_request.py    # 请求/对拍测试
```

**命名示例：**
- `https://www.baidu.com/s?wd=test` → `sites/baidu/`
- `https://api.example.com/v1/data` → `sites/api_example_com/`

### 2.6 任务完成清理规范

**任务完成后清理临时产物，但不得删除复现判官所需的核心测试和证据索引。**

**保留：** `README.md` / `plan.md` / 核心 `src/` / 最小 `tests/` / 参数与接口文档 / 当前资产 URL+hash 索引 / 脱敏 e2e 证据。

**清理或受控归档：** 含活 Cookie/token/PII 的 HAR、PCAP 和日志，重复下载的 bundle，临时截图，AST 可再生中间产物，缓存与 `selftest_tmp`。删除前必须精确确认目标、保留清单和可恢复副本，不执行无条件目录清理模板。

## 3. 指令优先级

```text
用户显式指令 > 角色定义规则 > 默认执行流程
```

- 用户明确说"立即调试"、"跳过情报收集"时，以用户指令为准
- 用户可以调整项目工作流偏好，但不能把对一个样本/目标的授权自动扩展为对其他账号、目标、设备或高影响动作的授权

## 4. 缺口驱动工作面 (Phase 0-4)

> Phase 0–4 是按当前证据缺口选择的工作面，不是必须逐级通关的流水线。缺哪层就从哪层进入；只读分析不为形式补齐无关 Phase。
> 需要代码实现、配置修改或实质性外部动作时，Phase 3 Plan 确认是实施准入门槛；已有用户确认的计划直接按计划执行。
> **核心思路：** 从当前线上资产和真实流量倒推代码，不从旧源码或模板猜逻辑。先看实际发送了什么，再定位由谁、在哪个上下文生成。

| 当前缺口 | 进入 |
|---|---|
| 缺公开背景、产品/框架指纹或已知资料 | Phase 0 |
| 缺真实请求、响应、initiator 或协议状态 | Phase 1 |
| 请求在手但动态字段/生成入口未知 | Phase 2 |
| 需要实施方案、代码/配置改动或外部动作 | Phase 3，确认后实施 |
| 计划已确认且样本、判官、产物目录齐全 | Phase 4 |

### Phase 0: 情报收集

- **触发条件:** 当前确实缺公开背景、产品/框架指纹或可复用的已知资料；已有真实流量/入口且缺口在其他层时不强制补做
- **动作:** 先完成与当前缺口直接相关的只读检索，不因收到 URL 就自动打开浏览器
- **搜索关键词:** `"{target_url} 逆向"`, `"{target_url} reverse"`, `"{target_url} 加密"`, `"{target_domain} jsvmp"`, `"{target_domain} 签名"`
- **分析:** 检索 GitHub 仓库与技术文档，提取加密算法特征及防护手段
- **完成标志:** 得到足以选择工作面的情报摘要；随后直接进入当前证据缺口对应的 Phase，不强制进入 Phase 1

### Phase 1: 流量与协议分析

> **关键约束:** `adspower-browser` 和 `js-reverse-mcp` 是两个独立的浏览器进程，**不能协同工作**。每次 Phase 1 必须选择一条路线并坚持到底。

**路线决策树：**

```text
【默认首选】路线D = 魔改浏览器 Cloak Browser + js-reverse-mcp 交互驱动（覆盖旧路线的大部分分析/调试能力）
  Cloak 引擎：自带指纹 + hook全家桶 + VM trace 去虚拟化 + C++网络抓包 + 反调试 + webdriver 隐身（全编译进内核）
  js-reverse-mcp 已配 --browserUrl 接管手动启动的 Cloak(serve_cloak.bat)：交互断点/单步/list_network + Cloak 内核 hook 同时在线
  绝大多数任务直接用 D；脚本化/定向 VM trace 用 tools/reverse-chromium/cloak_run.py
  详见 tools/reverse-chromium/README.md（路线D 总入口 + CLOAK_* 环境变量参考）

仅以下专门场景回退 A/C（B 已被 D 吸收 = js-reverse-mcp 驱动 Cloak）：
  需要 AdsPower 商业指纹 / 代理 / 已授权真实登录态 → 路线A 或 C
  （Cloak 合成指纹尚未在硬指纹墙实证能过，这类仍以 AdsPower 为金标准）

路线A：adspower-browser —— AdsPower 商业指纹/代理/Profile 隔离；缺点：无 list_network_requests
路线C：AdsPower CDP 桥 —— adspower 打开 → CDP 端口 → Python websocket-client（参考 sites/rednote/src/cdp_bridge.py）
```

**通用步骤：**

1. **打开浏览器，导航到目标页面**
   - 路线A：`adspower-browser.open-browser` + `navigate`
   - 路线D：Cloak 启动后由 `js-reverse-mcp.new_page` + `navigate_page`
   - 路线C：`adspower-browser.open-browser` + `navigate`，然后 Python CDP 连接
2. **流量捕获：** 观察 API 请求的 Headers、Payload、Response
   - 路线A：`evaluate-script` 注入 XHR/Fetch Hook，通过 console 输出
   - 路线D：`list_network_requests` / `get_request_initiator` 直接查看
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
> - **路线D 推荐** — Cloak + `js-reverse-mcp`，用于完整调试、内核 Hook、网络与 VM trace
> - **路线C 条件回退** — 只有同时需要 AdsPower 商业指纹和深度调试时使用
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

### Phase 3: 产出实施 Plan ⚠️ 代码/配置/外部动作准入门槛

> **涉及代码、配置或实质性外部动作时，未经用户确认严禁进入 Phase 4。** 纯只读分析或用户已经确认的既有计划不重复走形式化关卡。

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
- **验证：** 先做至少 3 组非样例 oracle 对拍，再由真实下游业务语义验收；只能发送但业务未接受时必须标为未闭环

## 5. 技能与工具链

### 5.1 Skills 六入口体系

`.claude/skills/` 只保留 6 个可运行入口；大段配方与案例放到各 Skill 的 `references/`，命中具体场景时才读取。

**完整流程：`web-reverse-master`**

用于未知算法、跨流量/源码/Hook/WASM/环境的任务，也负责当前 bundle/SourceMap、SPA chunk、GraphQL/WebSocket/gRPC-Web/PCAP 协议链与阶段路由。原路线设计、计划、执行、样本驱动复现和系统排错已合并到 `web-reverse-master/references/10-staged-method.md`，不再各占一个 Skill 入口；协议交付物与证据卫生按需读取 `references/11-*`、`references/12-*`。

**专业直调：**

- `ast-deobfuscation` — Babel AST 分层反混淆与家族适配。
- `captcha-solver` — 验证码识别、轨迹、内置加密与提交。
- `param-encryptor` — 已确认算法的签名、加密、编码与参数组装。
- `env-patcher` — Node.js/VM 浏览器环境补丁与差异修复。

**经验索引：`web-reverse-field-guide`**

只按现象检索 E1-E18 / S1-S17 / C1-C12、Web 交付物/协议失败模式和历史案例，输出证据门槛与下一项实验；实施仍交给 master 或专业 Skill。

六项流程方法已合并到 master 的 `references/10-staged-method.md`；旧流程 Skill 与按月份维护的重复配方已清理，当前内容统一按主题放入各 Skill 的 `references/`。

**完整技能表：**

| Skill | 定位 | 触发条件 |
|-------|------|---------|
| `web-reverse-master` | 全流程编排与阶段方法 | 未知、跨阶段、当前 bundle/SourceMap、GraphQL/WebSocket/gRPC-Web/PCAP，涉及两个以上专业域，或需路线设计/计划/执行/样本复现/证据链排错 |
| `ast-deobfuscation` | JS 结构反混淆 | 已明确只需处理 `_0x`、字符串表、dispatcher、控制流平坦化或已知混淆家族 |
| `captcha-solver` | 验证码求解 | 验证码协议、图片和会话配置已定位，需要识别、轨迹、内置加密、提交与凭证验收 |
| `param-encryptor` | 加密参数生成 | 字段、算法、输入和真实样本已知，需要复现签名/加密/参数组装 |
| `env-patcher` | 补环境 | SDK、入口和期望输出已知，需要让它在 Node.js/VM 中运行；不负责差异取证 |
| `web-reverse-field-guide` | 经验索引层（只查不做） | 用户明确只查历史案例、错误码映射、Web 协议误判或失败模式；要求定位、修复或交付时不用 |

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
> 📌 **受控配置入口可移植且最小继承：** 根 `.mcp.json`、`.cursor/mcp.json` 与 `.codex/config.toml` 只调用相对 `scripts/mcp-launcher.js`；机器路径和凭据只存在 ignored `.mcp.local.json` 或 launcher 环境，子 MCP 仅接收逐服务白名单。当前 5 服务的声明输入为 `clean-source-build` / `clean-commit` / `project-lock`，没有 `locked-local-patch`；但外部依赖树仍未逐字节纳入 lock，因此不得宣称 runtime hermetic 或 clean-checkout 可重建；隔离重建对拍仍未完成。
>
> ⚠️ `adspower-browser` 和 `js-reverse-mcp` 是独立的浏览器进程，**不能协同工作**。需要浏览器或 MCP 取证时选定一条适用路线，并在同一会话中保持到底。
>
> 📌 **默认路线 D（2026-08）**：项目 MCP 配置统一调用 `scripts/mcp-launcher.js`，由 launcher 以 `--browserUrl http://127.0.0.1:9222` attach 已启动的 Cloak。先 `serve_cloak.bat` / `cloak_run.py`，再重载 MCP。
>
> 📌 **路线 C 仍可用**：需要时另案切换 launcher 的 js-reverse 参数为 `--adspower --adspowerProfile k1bhfp97`，同步文档并重载；不得只改某个客户端形成配置分叉。手搓 `cdp_bridge.py` 仅 fallback。
>
> 📌 **ZCode 不读项目 `.mcp.json`**，只读 `~\.zcode\cli\config.json`。项目 `.zcode/config.json` 保持空 servers。
>
> 📌 **Codex 读项目 `.codex/config.toml`**（须与根 `.mcp.json` 同为路线 D / 9222）。Codex 与 ZCode 共用唯一实体镜像 `.agents/skills`；不要另建 `.codex/skills` 或 `.zcode/skills`。
>
> 📌 **Skill 发现拓扑**：Claude、Cursor、Qoder 直接读 `.claude/skills`；Codex、ZCode 读 `.agents/skills`。Qoder 的 `.qoder/qoder.json` 必须指向 `./.claude/skills`。

| 服务 | 类型 | 能力 | 状态 |
|------|------|------|------|
| `js-reverse-mcp` | 项目 | 断点/源码/inject_before_load/trace_function/list_network + dispatcher trace/handler 摘要（不自动产出纯算） | ✅ 路线 D（attach 9222） |
| `adspower-browser` | 项目 | 指纹浏览器、Profile、evaluate-script、drag | ✅ 路线 A/C |
| `ida-pro-mcp` | 项目 | Wasm/二进制逆向 | ✅ 按需 |
| `reqable-mcp` | 项目 | 抓包（需 Reqable ingest 18765） | 🟡 按需 |
| `sequential-thinking` | 项目 | 多步推理 | ✅ |

**不要**写入本仓库 `.mcp.json`：`playwright`（采集禁令）、Android 三件套（`frida-orchestrator` / `reverse-index` / `algo-lab`）。

`wiremcp` 已从默认项目 MCP 隔离：当前外部实现存在共享临时文件覆盖、shell 字符串拼接、机器路径 fallback 和过宽工具面，不作为干净运行依赖。`wagnganskills\reverse-skill\burp-mcp-full` 也只列为显式启用候选，不进入默认 5 服务。两者的恢复门槛见 [`.claude/mcp.md`](.claude/mcp.md)，不得在单个客户端配置里私自加回。

**AdsPower 配置：** Profile `k1bhfp97`，接口 `http://127.0.0.1:50325`；API Key 只放 ignored `.mcp.local.json` 或 `ADSPOWER_API_KEY`，不得写入受控配置。

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
├── mcp.md                     # MCP 操作（层级 / attach 缓存 / 不入库名单 / Codex）
├── MAINTENANCE_LOG.md         # Skills / MCP / Rules 更新记录（倒序追加）
├── skills-manifest.json       # 6 个活跃 Skill allowlist（同步前 fail-closed）
├── skills/                    # Skills 定义（6 个活跃入口；详细资料按需加载）
│   ├── web-reverse-master/    # 全能一体机
│   ├── ast-deobfuscation/
│   ├── captcha-solver/
│   ├── param-encryptor/
│   ├── env-patcher/
│   └── web-reverse-field-guide/ # 失败模式至 E18/S17/C12
├── skills-next/               # 非运行时：evals / 维度评分 / dependency-cache
├── projects/Qoder_ObjectProdemo2/
│   └── memory/                # 项目记忆权威源（跟随 git）
└── settings.local.json        # 权限白名单

.cursor/                       # Cursor 专用配置；Skills 直接读取 .claude/skills
├── rules/                     # alwaysApply：memory / skills-mcp / cloak-browser
└── mcp.json                   # 镜像自根 .mcp.json

.agents/skills/                # 唯一实体派生镜像；Codex + ZCode 入口
.zcode/memory                  # junction → 项目 memory
.zcode/config.json             # 必须空 servers（ZCode 读用户 CLI）
.codex/config.toml             # Codex 项目 MCP（调用项目 launcher，无本机路径）
.codex/rules/default.rules     # Codex 客户端专用命令策略；非角色真源，必须保持可移植
.mcp.json                      # MCP 服务清单权威源（5 服务；统一调用 launcher）
.mcp.local.example.json        # 本机 MCP 路径/凭据模板；实际 .mcp.local.json 永不入库
.claude/mcp-runtime-lock.json  # 外部 MCP 实际运行内容 hash/commit 锁
AGENTS.md                      # Cursor / Codex 项目规则（由 CLAUDE.md 派生）
scripts/                       # 项目工具箱 + 门禁（见 scripts/README.md）
.qoder/qoder.json              # Qoder Skills 指向 ./.claude/skills
.qoder/rules/rules.md          # Qoder always_on 规则（由 CLAUDE.md 派生）
plans/                         # 已完成方案档案（7 份）
sites/                         # 各站点逆向项目

禁止存在重复入口：`.cursor/skills`、`.zcode/skills`、`.codex/skills`、`.qoder/skills`。同步脚本只刷新 `.agents/skills`，遇到退役入口会 fail-closed。

同步命令: .\scripts\sync-claude-to-cursor.ps1
门禁: scripts\check_skill_links.py + scripts\selftest.py + .claude\skills\web-reverse-master\scripts\selftest.py + scripts\check_tool_sync.py；本机 MCP 另跑 node scripts\mcp-launcher.js --check
```

## 8. 使用须知

1. **协议优先** — 所有工作围绕"如何不用浏览器拿到数据"
2. **本地优先** — 涉及敏感业务时优先本地部署开源 LLM 进行代码分析
3. **路线一致性** — 需要浏览器或 MCP 取证时，先记录 D/A/C/No MCP 中的一条路线并保持会话与证据边界；纯离线 AST、文档或既有样本分析不强选浏览器路线
4. **确认机制** — 代码、配置和实质性外部动作以已确认的 Phase 3 Plan 为准入门槛；只读分析不重复走形式关卡
5. **维护留痕** — 修改 Skill / MCP / Rules 时，先改权威源并追加 `.claude/MAINTENANCE_LOG.md`，同步和门禁完成后回填实际结果
6. **环境检查** — 执行项目 Python 前确认使用 `./venv`；改 Skill / MCP / Rules 后跑完整门禁，确认单一发现拓扑、`.agents/skills` 镜像和各端配置未漂
7. **日志保留** — 只保留脱敏且支撑结论的最小日志、证据和索引；活 Cookie/token/PII 按任务结束清理或受控归档
8. **及时关闭** — 浏览器调试完成后立即关闭
9. **禁止猜测** — 加密方式必须动态调试实证
10. **线索追踪** — 拿到线索必须追到底
11. **最终产出** — 按任务目标选择协议脚本、算法模块、Hook/trace、环境补丁或取证报告；协议客户端以 Python 为主体

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

- Python 命令必须使用当前 checkout 的项目解释器（从仓库根执行时为 `.\venv\Scripts\python.exe`），严禁调用 PATH 中的全局 Python
- 多行 Python 代码写入 `.py` 文件后执行，**禁止用 `-c` 传递多行**（转义问题）
- npm/node 命令可直接使用

## 10. Hook 注入规范

各路线注入方式不同：

**路线D（Cloak + js-reverse-mcp）：**

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
- 涉及代码、配置或实质性外部动作时，先提交可验收 Plan；已有用户确认的计划直接实施，纯只读分析不重复走形式关卡
- 不要创建多余的项目或文件
- 需要浏览器或 MCP 取证时，明确记录 D/A/C/No MCP 中的适用路线并保持会话边界；纯离线 AST、文档或已有样本分析不强选浏览器路线
