---
description: APPCodeObjectdemo1 Android 逆向工程权威规则
alwaysApply: true
---

> **便携分发适用规则**：开始任务先读本目录 [PORTABLE.md](PORTABLE.md)。原机设备、端口、工具版本、MCP 数量和历史通过结果不代表接收电脑当前状态；本包不含 MCP 程序、工具链、凭据或业务项目。原机设备标识已替换为占位符。仅在当前任务已有授权内操作已核实的目标；不自动同步用户全局配置或写入记忆。当前 Skills 与本条便携边界优先于历史附录。


# APPCodeObjectdemo1

## 范围与授权

本仓库只做 Android APK/DEX/ART/JNI/SO、Android 网络协议和真机运行期分析。不要引入 iOS/IPA/Mach-O/越狱、PE、通用 Web 或 CTF 工作流。

仓库内样本、工具、项目目录、Pixel 6 `<ANDROID_SERIAL_P6>`、Pixel 4 XL `<ANDROID_SERIAL_P4XL>` 及用户指定测试账号默认属于用户已授权的本地 Android 环境。对这些既定对象执行静态分析、低风险真机验证、MCP 回归和恢复操作时，不重复询问授权，也不用泛化免责声明阻塞工作。

只有以下情况重新确认范围：

- 目标/设备/账号/网络系统扩展到仓库约定之外；
- 要写真实全局配置、联系第三方、公开/推送或产生明显外部影响；
- 用户选择会实质改变交付形态或高风险设备动作。

授权默认不取消工程护栏：唯一 serial、写前备份、写后验证、失败恢复、防 PID 复用、超时隔离、无效请求止损和真实判官仍强制执行。

## 真源

| 内容 | 唯一编辑源 | 派生/说明 |
|---|---|---|
| 项目角色、工具链、MCP 工作流、目录与授权规则 | `CLAUDE.md` | 其他 runtime rule 只加载本文件 |
| Skills | `.claude/skills/` | 只同步到唯一非 Claude 运行镜像 `.agents/skills/` |
| MCP 配置 | 根 `.mcp.json` | 生成 Cursor/Codex/Grok 项目镜像 |
| 逆向证据/交付准则 | `.zcode/memory/reverse_principles.md` | 不复制到各 rule |
| 项目记忆 | `.zcode/memory/` | 只有用户明确要求时更新 |

禁止独立演化镜像，禁止再创建 `.codex/.cursor/.grok/.qoder/.zcode/skills` 项目入口。

## Skills 拓扑

任务只路由到 4 个 Android Skill：

1. `android-recon`：设备/样本预检、APK 拉取、malformation 与壳初判、jadx/apktool、网络栈、API/调用链、设备注册入口与风控 SDK 分诊、抓包治理。
2. `android-unpack`：真实 DEX/VDEX 或运行期解密 SO 段提取与 fresh JADX/结构验收。
3. `android-dynamic`：Frida/trace/RPC、反注入判因、SSL/native 网络、运行期快照，以及注册关系、凭证与风控状态的最窄运行期取证。
4. `protocol-signature-reverser`：设备注册/绑定/一机一密、安装标识/密钥/平台证明/设备令牌/账号会话的谱系与生命周期，传输/算法/环境/业务拒绝分层判因，以及 unidbg/Unicorn 和三级交付。Play Integrity / Key Attestation 问题按该 Skill 的证明边界核证。

`reverse-skill-evolver` 只维护上述 Android Skills/Rules/MCP；`darwin-skill` 只作通用维护框架，不参与 Android 任务路由。不要新增重叠的 jadx、apktool、Frida、SO 或“mobile reverse” Skill。

收到与上述职责匹配的请求时，先读取对应 `.claude/skills/<skill>/SKILL.md` 再执行，并简短说明选用了哪个 Skill；已有明确缺口时直接选专项。只按需读取其引用资源。维护 Skill 仅在用户请求或授权维护时选用，普通逆向任务结束不自动启动维护。客户端发现 Skill、模型选择 Skill、实际读取正文是不同环节；正文“触发词”不是执行 hooks，目录可见不能作为已调用的证据。

Skill 发现拓扑只有两层：Claude 使用 `.claude/skills/` 真源；Codex、ZCode、Qoder、Pi 使用 `.agents/skills/` 单镜像。Cursor 对 `.claude` 与 `.agents` 的同路径 Skill 按规范化键去重并优先真源；Grok 当前按名称去重，六个项目 Skill 的有效来源为 `.agents/skills/`。任何 runtime 专属 `skills/` 目录重现都视为重复发现故障。

## MCP 拓扑

根 `.mcp.json` 是配置真源。当前仓库自建 Android MCP 恰好 3 个：

| MCP | 工具数 | 职责 |
|---|---:|---|
| `frida-orchestrator-mcp` | 81 | 唯一设备/ADB/Root/Frida/WebView/AlgorithmAide/LSPosed/HMA/代理编排 |
| `reverse-index-mcp` | 8 | 对 `projects/<target>/decompiled/` 建索引并查 endpoint/symbol/string/签名候选 |
| `algo-lab-mcp` | 11 | 编码/Protobuf wire、请求差分、hash/HMAC 候选、复现与字节验证 |

工具数必须由 `android_mcp/tests/smoke_test_mcp.py` 的注册结果确认，不手填猜测。

项目 MCP 保持精确 7 个：上述 3 个自建 Android MCP，加 IDA、Reqable、Playwright、js-reverse 4 个按需辅助 MCP。每次会话是否 `online/validated` 需单独探测；配置存在只算 `declared`。Playwright/js-reverse 只在 Android WebView/混合 App 确实需要时使用，不扩展为通用 Web 任务。

不注册通用推理 MCP；它不提供 Android 领域能力。Reqable 是本仓库唯一抓包 MCP，Charles 可作为人工代理工具但不再重复注册 MCP，也不使用运行时下载的 `uvx` 入口。

Ghidra GUI/headless 已记录在工具链；GhidraMCP 当前仅 `documented`，未注册到 `.mcp.json`、未完成 stdio 生命周期验收，不得称 `online` 或 `validated`。

## 真机与工具链

| 项 | 规则 |
|---|---|
| 设备 | 双真机：Pixel 6 `<ANDROID_SERIAL_P6>` / Android 14 / arm64（主力，gpay/tiktok 战场）；Pixel 4 XL `<ANDROID_SERIAL_P4XL>` / Android 13 / arm64（印度支付矩阵机，Tricky_Store+HookVIP）。两台均 APatch/LSPosed root；文档是基线，运行前仍探测当前状态，多设备在线时固定唯一 serial |
| ADB | 只用 `android_mcp\toolchain\bin\windows\platform-tools\adb.exe`；每个写/进程操作固定唯一 serial |
| 设备侧工具 | 两台 `/data/local/tmp/` 均有 patched frida-server `new-server`、`ecapture`、`stackplz`、`okhttpfind.dex`；P4XL 另有 frida-gadget×2。P6 的 new-server 常驻，P4XL 默认未运行 |
| Frida Python | 专用 venv `.venv-frida-16.5.9`，不假定 `frida-ps.exe` 或 PATH CLI |
| Frida server | 主 `/data/local/tmp/new-server` 16.5.8-dev.11；client/server/ABI 必须匹配 |
| JADX | `tools\jadx\bin\jadx.bat` |
| apktool | `tools\apktool.bat` |
| native | IDA Pro 优先；`tools\so-reverse/` 的 rabin2/Ghidra headless/QBDI 等按需使用 |

Frida server 只监听设备 loopback；宿主临时 forward 使用 `--no-rebind`，结束精确删除。停止进程前核对 session/package/PID/start identity，禁止旧 PID 或 `pkill -f` 误杀。

## 标准闭环

1. `android-recon`：固定 APK/version/hash、包名、serial/ABI 和可证伪目标；拉 base/splits，反编译到新目录，识别网络栈。
2. 有壳则 `android-unpack`：取得真实 DEX/SO 段，并通过结构检查和 fresh JADX/反汇编验收。
3. `reverse-index-mcp`：建立静态索引并闭合 request/API/JNI 调用链。
4. `protocol-signature-reverser` + `algo-lab-mcp`：建立字段与注册谱系，区分安装、设备、密钥、账号、会话身份，连通生产者、持久化、消费者及刷新/轮换/注销；纯算、设备态、上游透传分列，未知阶段不补造。按证据确定请求到达层，再分传输、算法、生命周期、平台证明和业务拒绝；保留 TLS/HTTP/QUIC、pinning/mTLS 与抓包盲区，错误码或漏包不直接归因。
5. 需要运行证据时 `android-dynamic`：先保留已有注册关系与进程/会话，使用最窄 Hook/trace/RPC；验证失败回到静态/假设层，不机械升级侵入度。SDK/API 字符串与官方文档不证明目标 App 实际调用或服务端验收。
6. 以谱×物×证×界按开工确定的目标交付：完整协议验服务端语义或账号可见效果；纯算法离线实现验同版本目标原版向量或适用的解密/验签，业务效果可标未验证。HTTP 200、可解析、长度正确、Hook 命中或工具退出码只算中间证据。

这是按缺口选路的闭环，不是要求每项顺序通关。

## 设备写入与恢复

设备/网络动作前：

- 确认唯一 serial、包名、PID/ABI、目标路径和新输出目录；
- 保存 proxy/NAT/forward、前台 App、Frida/Zygisk/LSPosed/AlgorithmAide/HMA 状态；
- Root 文件写入保存旧内容、owner/mode/SELinux context；
- 明确恢复命令。

注册分析先读现有状态；本地静态梳理/设计不自动启动登录、注册、重放或重置。清数据、重装、刷机、切账号不作为采样前置；一次性 challenge/token 不为对拍数量重复消费。密钥不可导出不等于不可调用，调用证据、硬件安全级别和服务端验证分别核对。

写后读取验证；失败立即恢复并复核。MCP 特别不变量：

- `/data/system/junge/<pkg>/` 为 `system:system`（目录 0700、文件 0600）；
- `root_push_file` 首写继承目标或最近存在祖先属主，并 chown 新建目录；
- 配置读取失败不得退化为空配置覆盖；
- 非协作工具超时后 server quarantine，需重启 MCP，不创建第二执行器绕过；
- localhost HTTP probe 禁继承宿主代理，并逐跳拒绝非 loopback redirect。

## 证据与止损

- 终止性结论遵循 `.zcode/memory/reverse_principles.md` 的证据牌照。
- 同一请求同字节累计最多 3 次（含首次和已有尝试），出现漂移更早停止；同接口同错误连续 3 次也停止同类请求并归因。预算不因换脚本、工具或操作者重置。
- 验证期单设备单账号；单 IP 不碰多号，不批量发送无效签名。
- 解析型/绕过型/止损型必须分开；真机/RPC/replay/oracle 依赖显式列出。
- 确定性纯算最低 3 组任意输入对拍，仍须字段谱系闭合；100+ 只作增强回归。合法随机输出按明文、参数与解密/验签验证。标准密码 KAT 只自检工具链，不能证明目标模拟执行可作为 oracle。
- 脱壳必须通过 DEX/ELF 结构与 fresh JADX/反汇编；退出码和文件名不算成功。

## 项目目录

新目标必须自包含于 `projects/<target>/`，目录名 ASCII，至少有 `README.md`：

```text
projects/<target>/
├── apk/
├── decompiled/
├── hooks/
├── scripts/
├── so_analysis/
├── capture/
├── artifacts/
├── docs/
└── README.md
```

通用 Hook 才放 `hooker/js/`；第三方工具放 `downloads/`。不要在仓库根散落单项目代码、APK、截图或 dump。

## 同步与验证

Rules 只保留本文件与根 `AGENTS.md` 薄 shim。Cursor、Qoder、ZCode、Grok 使用各自的 `AGENTS.md`/`CLAUDE.md` 兼容发现，不再维护 `.cursor/.qoder/.grok/rules` 副本。不得新增 `AGENTS.override.md` 或第二份 runtime 规则覆盖入口；项目记忆仍只有用户明确要求时才更新。

改 Skill：

先对照当前 Skill 复核本文“Skills 拓扑”“标准闭环”“设备写入与恢复”“证据与止损”的语义摘要；职责、触发条件、状态保护或判官变更必须同步修订，记录对应源段落与已更新/无需修改的理由。`AGENTS.md` 只保留真源入口，不复制领域细则。

```powershell
python .claude\scripts\sync_shared_skills.py
```

同步脚本只处理 4 个任务 Skill、`reverse-skill-evolver`、`darwin-skill` 及允许的运行资源，不会自动更新本文的职责或工作流摘要；镜像一致不代表 Rules 语义已对齐。脚本在发现多余 runtime Skill 根时 fail-closed。旧的 `codex/qoder/zcode` 参数只作为 `.agents` 兼容别名，绝不生成第二镜像。禁止 `Get-Content -Raw` 读写 UTF-8 中文文件；验证无 BOM、预期路径替换和运行时名称唯一。

改 MCP：

```powershell
python .claude\scripts\sync_mcp_mirrors.py
```

脚本生成 `.cursor/mcp.json`、保留 Codex 非 MCP 表后更新 `.codex/config.toml`、生成 `.grok/config.toml`，并以组回滚保护三份镜像。ZCode/Qoder 用户目录 MCP 只显式核对，不由项目脚本暗改。

Grok 1.0.x 的 Claude/Cursor 兼容开关属于用户级配置，项目 `.grok/config.toml` 只生成原生 MCP 表，不能宣称隔离全局合并。`grok inspect --json` 若显示额外用户级 MCP/Rules，只脱敏记录来源；不得由项目同步脚本修改用户全局状态。

完整维护流程、更新模板和逐次时间线见 `docs/SKILLS_MCP_RULES_MAINTENANCE.md`；该文档不得放入任何 Skill 发现根或被同步复制。

离线回归：

```powershell
python -m unittest discover -s android_mcp/tests -p "test_*.py" -v
python android_mcp/tests/smoke_test_mcp.py
```

最近已留存真机报告：`android_mcp/_work/test_reports/frida_orchestrator_live_20260905_235826.json`，23/23；包含专用 venv 的 `frida_ps` USB/进程枚举。它是当前版本基线，修改设备控制实现后仍需重新低风险验收。
