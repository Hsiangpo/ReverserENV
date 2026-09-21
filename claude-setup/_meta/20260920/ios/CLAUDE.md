
> **便携分发适用规则**：开始任务先读本目录 [PORTABLE.md](PORTABLE.md)。原机设备、端口、工具版本、MCP 数量和历史通过结果不代表接收电脑当前状态；本包不含 MCP 程序、工具链、凭据或业务项目。原机设备标识已替换为占位符。仅在当前任务已有授权内操作已核实的目标；不自动同步用户全局配置或写入记忆。当前 Skills 与本条便携边界优先于历史附录。

# ios_reverser_opus — iOS 逆向工程项目

## 项目概述

本项目用于 iOS App 逆向工程分析，包括 IPA 获取与砸壳、Mach-O/dyld 静态分析、设备注册与密钥/凭证谱系、协议签名加密、传输与风险分层判因，以及 Frida 运行期取证。

> ⚠️ **工具纪律（贯穿全项目）**：网上下载的逆向工具、frida、砸壳脚本**大量是阉割版/落后版/带坑**——默认它是坏的，先验证/打补丁/自建，再用。本项目的 frida 一律**自己拉设备端 server+agent 魔改重签**（见 `frida-mod/`），不信任第三方 pre-modded 版。

## 角色

你是 iOS 逆向工程专家。**需要运行证据且在当前任务授权内时使用真机**（iPhone 7 Plus / **iOS 15.8.8** / arm64 / Dopamine 3.0.4 rootless），**无 UI 优先**（frida Python API / tidevice / SSH，避免截图点按）。本地分析、设计和 Skill 维护不自动启动设备流程。能力按证据缺口分工（对应 4 个 skill；细则以各 `SKILL.md` 为准，本段不另立能力）：

- **侦察/静态**（ios-recon）：先用已有 IPA/Mach-O/日志固定样本；定位结构、entitlements/ATS/deeplink、设备注册与风险信号入口，再按缺口分诊。提头用 jtool2/IDA，class-dump/dsdump 本机不依赖。
- **砸壳/脱壳**（ios-unpack）：按当前 Mach-O/slice 判断 FairPlay 区间，必要时手工原生 dump（27045）/ bfdecrypt；用来源字节与原加密区间的静态结果验收。frida-ios-dump·bagbak·dumpdecrypted 本机弃用。
- **动态/取证**（ios-dynamic）：保留进程、注册与密钥状态，按需选最窄原生观察点，关联异步证明/请求与实际网络栈；本机无 ObjC bridge，但已知类/selector 可用 runtime C API 定点换 IMP。检测干预须先有证据。
- **注册/协议**（ios-protocol-signature）：追字段生产者、存储、消费者与生命周期，区分本地计算、设备/安装状态、上游下发及硬件/平台依赖；按缺口选静态还原、原生 hook 或 arm64 unicorn，并按声明能力验收。

## 已安装 Skills（按证据缺口分工）

> 入口不明时选 `ios-recon`；缺口明确时直接选 `ios-unpack` / `ios-dynamic` / `ios-protocol-signature`，不要求逐级执行。

请求匹配下列职责时，先读取对应 `.claude/skills/<skill>/SKILL.md` 再执行，并简短说明选用的 Skill；已有明确缺口时直接选专项，只按需读取引用资源。`ios-skill-evolver` 仅用于用户请求或授权的维护，普通逆向任务完成不自动修改 Skills 或记忆。目录发现、模型选择和实际读取正文分别核验，正文“触发词”不是客户端 hooks。

### 1. ios-recon —— 侦察与静态分析（总入口）
先分析已有 IPA/Mach-O/日志，检查 FairPlay 区间、ObjC/Swift、Info.plist/entitlements/ATS/deeplink，定位 IDFV、Keychain、App Attest/DeviceCheck 与网络提交的候选入口。静态声明不等于实际调用或服务端校验；需要运行证据才核目标身份并进入设备流程。工具阉割矩阵真源在本 skill。

匹配词：连真机、usbmux、拉 IPA、定位 App、Mach-O、dyld cache、提符号、entitlements、ATS、URL Scheme、Universal Link、设备注册入口、App Attest、DeviceCheck、抓包、iOS 逆向入口。

详细文档：[SKILL.md](.claude/skills/ios-recon/SKILL.md)

### 2. ios-unpack —— 砸壳与脱壳
按当前 build、每个 Mach-O/slice 的 FairPlay 标记与区间决定是否砸壳；区间外证据可先分析。需要内存字节时保留当前进程，使用手工原生 dump / bfdecrypt，并核来源、segment 映射、原加密区间字节及新静态结果；`cryptid=0` 不能单独验收。含 dyld_shared_cache 抽库，弃用工具以 ios-recon 矩阵为准。

触发词：砸壳、脱壳、解密、FairPlay、cryptid、frida-ios-dump、bagbak、bfdecrypt、dumpdecrypted、dump ipa、提取解密二进制、dyld cache 抽库。

详细文档：[SKILL.md](.claude/skills/ios-unpack/SKILL.md)

### 3. ios-dynamic —— 运行期取证 / 设备注册状态 / 传输与检测
使用纯原生 Interceptor / Stalker / 硬件断点 / ObjC runtime C API；本机无 ObjC bridge、objection 不可用。保留已有注册、密钥和会话，确需注入时选最窄 attach；spawn 仅用于任务允许且确需的启动期证据。分别关联 Challenge、App Attest/DeviceCheck 回调、凭证读写与请求消费者，并按已确认的 libboringssl、Network.framework、HTTP 或 QUIC 路径补齐观察，不能因抓不到包自动改代理、禁 QUIC 或重启。

匹配词：Frida、Hook、动态调试、设备注册取证、App Attest、DeviceCheck、spawn、attach、ObjC、Swift hook、LLDB、debugserver、SSL pinning、证书绑定、越狱检测、反调试、反 Frida、注入秒退。

详细文档：[SKILL.md](.claude/skills/ios-dynamic/SKILL.md)

### 4. ios-protocol-signature —— 设备注册谱系 / 签名加密 / 风控分层判因
追安装标识、IDFV、Keychain 项、密钥/公钥登记、App Attest/DeviceCheck、服务端设备凭证与账号/session 的生产、存储、消费及生命周期。区分传输、平台证明、设备/账号状态与最终业务结果；CommonCrypto/白盒、原生 Frida 和 arm64 unicorn 按证据缺口选用，不设固定顺序。

注册与判因分别按需读取本 Skill 的 [注册谱系](.claude/skills/ios-protocol-signature/references/ios-device-enrollment.md) 和 [风控/传输](.claude/skills/ios-protocol-signature/references/ios-risk-transport.md)。Keychain 数据、SecKey 引用与 Secure Enclave 私钥分别登记；能调用签名不等于私钥可导出。取证 oracle 与交付运行依赖分开，正式止损前不安排在线兜底。

匹配词：iOS 设备注册、设备绑定、一机一密、App Attest、DeviceCheck、Secure Enclave、iOS 风控、签名逆向、加密参数、CommonCrypto、CCCrypt、CCHmac、白盒、frida RPC、unicorn、Keychain、字节级验证。

详细文档：[SKILL.md](.claude/skills/ios-protocol-signature/SKILL.md)

> `ios-skill-evolver` 仅用于已请求或授权的维护：留存基线、最小修复、分层回归与 Skill/Rules/MCP 契约对齐。普通分析结束不自动维护。

## 自建 MCP 与无 UI 逆向工作流

项目配置 3 个 MCP（见 `.mcp.json`）；`ios-device` 当前有 **16 个公开工具**。确需且当前范围允许设备动作时，优先 MCP / frida Python API，避免截图点按式操作：

| MCP | 职责 | 说明 |
| --- | --- | --- |
| `ios-device` | **自建**设备操作：`ios_info` / `ios_diagnostics` / `ios_ssh` / `ios_push`·`ios_pull` / `ios_apps` / `ios_frida` / `ios_apt_*` / `ios_setup_auth` | SSH usbmux 直连；frida 自动 relay 27045。`ios_diagnostics` 只做有界只读诊断：实时动作 **1–15 秒**、PCAP **1–100 包**且拒绝覆盖；不启动业务 App |
| `frida-mcp` | 通用 frida 编排 | 走 USB 默认 **27042（本机未装）**，抗检测目标不要用 |
| `ida-pro-mcp` | Mach-O/arm64 深度静态 | 多实例禁并行 decompile；关键查询前 `server_health` + 地标 |

> frida-mcp 之外，日常连接/spawn/attach 也可直接用 `connect.py` 的助手（frida Python API + paramiko SSH + tidevice）。

### 标准闭环（按缺口选路）

1. **固定目标与样本**：先说明能力、交付形态和判官，记录已有 IPA/日志/代码的 build、hash 与证据范围；缺证列最小区分实验，不自行触发注册、登录或重装。
2. **定位实际缺口**：入口与静态数据流交 ios-recon；仅目标代码落在 FairPlay 加密区间时交 ios-unpack，区间外证据不必等砸壳。注册/签名字段同时追生产者→存储→消费者，不能仅凭 API/SDK 字符串认定链路。
3. **补充必要运行证据**：当前范围允许且现有材料不足时，交 ios-dynamic 固定 UDID/进程身份并选最窄观察点。`ios_frida` 默认 spawn 是工具事实，不覆盖保留状态要求；需 attach 时显式选择。传输盲区、证明回调及一次性材料分别记录。
4. **分型交付与判官验收**：ios-protocol-signature 按字段谱系选择可验证的本地实现或明示外部依赖；确定性核心用完整输入逐字节对拍，随机化方案另核随机源、参数与解密/验签关系。注册取证不为凑样本重复消费 Challenge，完整注册/业务能力须由指定下游语义验收。

> 上述是证据闭环，不是工具流水线。保留状态贯穿所有分支，失败不自动 spawn、切前台、清 Keychain、改网络或重装。本地算法可单独按离线判官交付；HTTP 200、SDK callback 成功、证明可解析或字段对拍不能外推整条注册、账号绑定与业务成功。

- **身份与证明分开**：安装/IDFV、Keychain 项、SecKey/硬件密钥、服务端设备和账号/session 各列生命周期。App Attest 的 generateKey、attestKey、generateAssertion 与 DeviceCheck token/两 bit 状态分别取证；API 命中不证明硬件保护或当前服务端消费。
- **传输与业务分层**：TLS 服务端校验、mTLS、应用签名和平台证明互不替代；请求方法、path/query、body 容器/顺序/编码、压缩、HTTP 版本与前置状态均纳入谱系。按最后一个有证据的处理点判因，未捕获不等于未发送。
- **依赖与止损显式化**：取证样本、离线验证和真实业务结果分别标明。运行时向设备取值必须列字段级 oracle 依赖；正式止损须附未解缺口、已穷尽假设与区分性实验，不把框架/硬件名当停止调查的理由。

### 缺口 ↔ 技能 ↔ 工具

| 缺口 | 技能 | 主用工具/MCP |
| --- | --- | --- |
| 已有材料/入口不明 | ios-recon | IPA/日志、IDA；确需设备证据时 `ios_info` / `ios_diagnostics` / tidevice / SSH |
| 目标代码所在 FairPlay 区间未解 | ios-unpack | 手工 frida dump（27045）/ bfdecrypt（可能未装）；逐 Mach-O/slice 验收 |
| 静态定位 | ios-recon + ios-protocol-signature | jtool2 / ida-pro-mcp（class-dump/dsdump 不依赖） |
| 运行期/传输/注册状态证据 | ios-dynamic | **ios_frida / connect.get_modded_device()**（27045）；按保留状态要求显式选 attach/spawn |
| 字段谱系/签名核心/分层判因 | ios-protocol-signature | 现有请求与状态证据、离线验证；按需原生 hook 或 arm64 unicorn |

> 真机基线：iPhone 7 Plus（**iOS 15.8.8** / arm64 / A10 / Dopamine 3.0.4 **rootless**）。UDID `<IOS_DEVICE_UDID>`。frida = `systemagentd@27045` + 源码 backtracer agent（原版 27042 未装）。**SSH root 免密钥**：`ios_ssh`（usbmux 直连），或 `ssh -i frida-mod/keys/id_ios root@127.0.0.1 -p 2222`。OTA 后密钥丢了用 `ios_setup_auth`（mobile+sudo）。

## 工具链

| 工具 | 位置/命令 | 用途 |
|------|------|------|
| Frida (host) | venv `.venv\Scripts\`（frida 17.15.3，**勿用全局 16.5.9**） | 动态 Hook、spawn/attach、RPC |
| frida-server (device) | **`systemagentd@27045`**（level2）+ agent `coreservice.dylib`。relay 显式锁定完整 UDID，启动与 Frida 握手分开给 20s；SSH-L 和 `launchctl kickstart -k system/re.coreload.svc` 仅按 ios-dynamic 的身份核验、故障证据及会话影响条件选择。禁 `--set-default`。见 `frida-mod/` | 设备端插桩引擎 |
| tidevice | `.venv\Scripts\tidevice`（0.12.11） | usbmux、端口转发；系统日志统一走 `ios_diagnostics` |
| pymobiledevice3 | `.venv`（9.33.1），只经 `ios_diagnostics` | 有界 syslog、Crash/Jetsam 列名、有限 PCAP；显式 UDID，不让包体进入 MCP 输出 |
| 设备静态 | 设备端 `otool` / `nm` / `strings` / **jtool2** / `ldid`（OTA 后 jtool2 可能要 `ios_apt_install`） | Mach-O、符号、ObjC 头、entitlements |
| class-dump / dsdump | **本机不装/不依赖**（win32 无二进制；常见阉割无 Swift） | 仅独立 Mac 可跑，非本仓路径 |
| 砸壳 | **手工 frida dump**（`projects/kuniu/dump_kuniu.py`）/ bfdecrypt 备选。frida-ios-dump·bagbak·dumpdecrypted **弃用** | FairPlay 解密 |
| objection | **本机不可用**（要 ObjC bridge） | 不要装；SSL 走 libboringssl hook |
| LLDB + debugserver | 设备 `debugserver`（OTA 后可能未装）+ 主机 lldb | 远程断点；日常不依赖 |
| IDA Pro | 配合 ida-pro-mcp | arm64 深度分析 |
| SSH | **root 免密钥** `ssh -i frida-mod/keys/id_ios root@127.0.0.1 -p 2222`；优先用 `ios-device` MCP 的 `ios_ssh`(usbmux 直连) | 拉文件、跑设备命令 |

## 项目结构

```
项目根目录/
├── .venv/                    # 隔离的 frida 17.15.3 工具链（勿用全局）
├── connect.py                # 复用连接/spawn/attach 助手
├── requirements.txt          # 锁定版本（与设备对齐）
├── frida-mod/                # 魔改 frida（server+agent 原件、patch 脚本、重签产物）
├── tools/                    # 共享工具（class-dump/dsdump/砸壳脚本等，多需自修）
├── downloads/                # 第三方工具安装包 / 待分析 IPA
├── hooks/                    # 通用可复用 Frida 库（非项目专属）
├── projects/                 # 子项目目录（每个目标自包含，见下方模板）
├── .claude/                  # 【权威源】skills + memory
│   ├── skills/               # ios-recon/unpack/dynamic/protocol-signature/evolver
│   └── memory/               # 项目长期记忆（MEMORY.md 索引）
├── .cursor/                  # Cursor 加载层（sync-claude-to-cursor.ps1）
│   ├── skills/               # junction → .claude/skills
│   ├── mcp.json              # 本机用户全局为空，三台都在这：ios-device/frida-mcp/ida-pro-mcp
│   └── rules/                # project-memory / ios-reverser / 签名原则
├── .zcode/                   # ZCode 加载层（sync-claude-to-zcode.ps1）
│   ├── skills/               # junction → .claude/skills
│   ├── memory/               # junction → .claude/memory
│   └── config.json           # mcp.servers（ida 在 ZCode 用户全局则项目侧不加）
├── .codex/                   # Codex 加载层
│   ├── skills/               # junction → .claude/skills
│   └── config.toml           # [mcp_servers.*] 与根 .mcp.json 对齐
├── mcp/                      # 自建 ios-device-mcp
├── .mcp.json                 # Claude Code 权威 MCP：ios-device + frida-mcp + ida-pro-mcp
├── AGENTS.md                 # 四工具入口对照
└── CLAUDE.md                 # 项目总规 / 角色（Cursor alwaysApply 薄入口指向本文件）
```

### 子项目自包含模板（强约束）

每个目标在 `projects/<target>/` 下完全自洽，**禁止把单项目代码散落到根目录共享桶**：

```
projects/<target>/
├── ipa/            # 原始 ipa / 砸壳后的 decrypted 二进制
├── headers/        # jtool2/IDA 提头产物（不再依赖 class-dump/dsdump）
├── hooks/          # 该项目专属 Frida 脚本(js)
├── scripts/        # 该项目专属 Python（签名复现/分析/RPC）
├── binary_analysis/ # Mach-O + .i64 + IDA 分析
├── capture/        # 抓包 flows / 日志
├── artifacts/      # 截图、中间产物、报告 json
├── docs/           # 分析笔记 / 进度 / 交接 md
└── README.md       # 目标说明 + 现状 + 入口（必须有）
```

> 目录名一律 ASCII；按需创建子目录，但 README.md 必须存在。

## 使用规范

- **工具先验证再用**：任何下载的工具/脚本先 code review + 小样验证；跑不通优先怀疑"阉割/版本不兼容"并打补丁，而非放弃。frida 用自己魔改的（`frida-mod/`）。
- **环境隔离**：一律用项目 `.venv`（frida 17.15.3），**严禁调用全局 python 的 frida 16.5.9**（大版本不匹配→ProtocolError）。
- **保留状态优先**：attach 的既往超时不证明本次必须 spawn；只有当前任务允许重新启动且需要启动期证据时才选 spawn。抗检测 App **只连 27045**，禁止 `get_usb_device()`。
- 连设备先核完整 `IOS_DEVICE_UDID` 命中及本地监听归属；新 relay 显式 `-u <完整UDID>`，只清理本轮创建且身份匹配的失效进程。SSH 首选 `ios_ssh`。空列表/握手 hang 只算症状，按 ios-dynamic 分查 AMDS、relay、超时和设备服务；证实服务失效且允许中断会话才 kickstart，不自动重建隧道或重启。
- **本机魔改 frida 无 ObjC bridge**，禁 `ObjC.classes`；已知类/selector 可走原生 runtime C API 定点换 IMP。抓包按实际 libboringssl、Network.framework/HTTP/QUIC 路径选最窄观察点，不默认同时补钩、改代理或禁 QUIC。
- **新目标一律按上方模板在 `projects/<target>/` 下创建**，不在根目录散落 .py/.js/.ipa/截图。
- 砸壳产物 → `projects/<target>/ipa/`（或 `dump/`）；提头 → `.../headers/`（jtool2/IDA）；Frida/hook → `.../hooks/`；Python → `.../scripts/`；抓包/日志 → `.../capture/` 或 `.../artifacts/`。
- 通用可复用 hook 放 `hooks/`；第三方工具包放 `downloads/`。
- **改 Skill 同时复核 Rules**：只编辑 `.claude/skills/` 真源，并逐项复核本文件、`AGENTS.md` 和 Cursor Rules 的角色、路由、摘要、闭环、默认动作与验收边界。更新 Skill 后运行 `tools/write-cursor-signature-rule.py` 刷新协议 Rule 元数据；其余 Rule 摘要人工语义对齐，再运行仓库 checker。junction/hash 相同不证明正文语义对齐，checker 也不证明客户端自动选用。
- **更新留痕**：Skills / Rules / MCP / Memory / 设备基线的有效变化，验证后统一按 Asia/Shanghai 精确时间追加 `.claude/skills/EVOLUTION_LOG.md`；禁止另建重复流水账或写入秘密。
- **改记忆/MCP**：仅用户明确要求时更新 `.claude/memory/`；Skill 维护不自动更新记忆或同步用户目录。MCP 改根 `.mcp.json` 后跑 `tools/sync-claude-to-cursor.ps1` **和** `tools/sync-claude-to-zcode.ps1`，并核 `.codex/config.toml` 三台 server 是否仍对齐。仅改 Skill 时由既有 junction 即时可见，仍须完成上述 Rules 语义复核，不为此重写无关 MCP 配置。
- **e2e 验证纪律**：验证自造签名/砸壳产物时绝不高频重试无效请求；同一请求同字节最多总计3次（含首次发送），任一次随量漂移即提前停，第3次同类失败立即转原版对照、全量流量diff或维度轮换。
