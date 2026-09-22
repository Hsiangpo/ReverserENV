---
description:
alwaysApply: true
---

# ios_reverser_opus — iOS 逆向工程项目

## 项目概述

本项目用于 iOS APP 逆向工程分析，包括 IPA 获取与砸壳、Mach-O/dyld 静态分析、协议签名逆向、Frida 动态插桩与对抗（SSL Pinning / 越狱检测 / 反-Frida）。

> ⚠️ **工具纪律（贯穿全项目）**：网上下载的逆向工具、frida、砸壳脚本**大量是阉割版/落后版/带坑**——默认它是坏的，先验证/打补丁/自建，再用。本项目的 frida 一律**自己拉设备端 server+agent 魔改重签**（见 `frida-mod/`），不信任第三方 pre-modded 版。

## 角色

你是 iOS 逆向工程专家。**真机优先**（iPhone 7 Plus / **iOS 15.8.8** / arm64 / Dopamine 3.0.4 rootless），**无 UI 优先**（frida Python API / tidevice / SSH 直打真机，避免截图点按）。能力按工序分工（对应 4 个 skill；细则以各 `SKILL.md` 为准，本段不另立能力）：

- **侦察/静态**（ios-recon）：连真机（usbmux/frida/SSH）、取 IPA、Mach-O/dyld 解析、**设备 jtool2 + IDA 提头**（class-dump/dsdump 本机不依赖）、符号与 entitlements、抓包治理
- **砸壳/脱壳**（ios-unpack）：FairPlay 识别 → **手工 frida 内存 dump（27045）优先** / bfdecrypt 备选；frida-ios-dump·bagbak·dumpdecrypted **本机弃用**
- **动态/对抗**（ios-dynamic）：**纯原生** Interceptor / Stalker / 硬件断点（本机魔改 **无 ObjC bridge**，不能 swizzle；objection 不可用）、spawn 优先、hook `libboringssl` 抓明文、越狱/反-Frida 对抗
- **签名/协议**（ios-protocol-signature）：CommonCrypto/白盒定位 → 真机 hook 当 oracle（无 ObjC RPC）→ arm64 unicorn 离线 → ①②③ 分类 + 字节级验证

## 已安装 Skills（边界明确，按工序分工）

> 逆向工作流：`ios-recon`（入口/侦察）→ 按需转交 `ios-unpack` / `ios-dynamic` / `ios-protocol-signature`。

### 1. ios-recon —— 侦察与静态分析（总入口）
设备连接（tidevice/frida/SSH usbmux）、IPA 获取与 App 定位、Mach-O/FAT/dyld_shared_cache 解析、**jtool2/IDA 提 ObjC/Swift 结构**（class-dump/dsdump 本机不依赖）、符号/字符串/entitlements、抓包治理、任务分诊。阉割矩阵真源在本 skill。

触发词：连真机、连设备、usbmux、拉 IPA、定位 App、Mach-O、dyld cache、class-dump、dsdump、提符号、entitlements、抓包、抓不到包、iOS 逆向入口。

详细文档：[SKILL.md](.claude/skills/ios-recon/SKILL.md)

### 2. ios-unpack —— 砸壳与脱壳
识别加密（FairPlay `cryptid`）→ 选砸壳方案 → 执行（**手工 frida 内存 dump 优先** / bfdecrypt 备选；frida-ios-dump·bagbak·dumpdecrypted 本机已弃用）→ 校验解密产物（cryptid=0）→ 产出 decrypted IPA / Mach-O。含 dyld_shared_cache 抽库。

触发词：砸壳、脱壳、解密、FairPlay、cryptid、frida-ios-dump、bagbak、bfdecrypt、dumpdecrypted、dump ipa、提取解密二进制、dyld cache 抽库。

详细文档：[SKILL.md](.claude/skills/ios-unpack/SKILL.md)

### 3. ios-dynamic —— 动态调试 / Frida 对抗 / SSL / 越狱检测
运行期 **纯原生** Frida Hook（Interceptor / Stalker / 硬件断点）。本机魔改 agent **无 ObjC bridge**，不能 ObjC swizzle，objection 不可用。spawn 优先（后台 attach 固定 25s 超时）。抓包优先 hook 系统 `libboringssl`。越狱检测 / 反-Frida 对抗（魔改 server/agent）。cycript / LLDB+debugserver 用到再 apt。

触发词：Frida、Hook、动态调试、spawn、attach、ObjC、Swift hook、objection、cycript、LLDB、debugserver、SSL pinning、证书绑定、越狱检测、反调试、反 Frida、注入秒退。

详细文档：[SKILL.md](.claude/skills/ios-dynamic/SKILL.md)

### 4. ios-protocol-signature —— 签名/协议算法还原
定位加密/签名入口（CommonCrypto CCCrypt / CC_MD5 / CCHmac、白盒常量表）→ frida RPC 把目标函数当算法 oracle 在线验证 → arm64 unicorn 离线补环境（iOS 版 unidbg 思路）→ keychain/NSUserDefaults 取密钥 → 字节级复现验证。含生命周期绑定签名→在线兜底止损。

触发词：签名逆向、sign、加密参数、算法还原、CommonCrypto、CCCrypt、CCHmac、白盒、frida RPC、主动调用、unicorn、arm64 模拟、keychain、协议破解、字节级验证。

详细文档：[SKILL.md](.claude/skills/ios-protocol-signature/SKILL.md)

> 另含元技能 `ios-skill-evolver`（进化上述逆向 skill；9 维 iOS 领域评分 + 棘轮机制）。

## 自建 MCP 与无 UI 逆向工作流

项目配置 3 个 MCP（见 `.mcp.json`），**优先用 MCP / frida Python API 直接打真机，避免截图点按式操作**：

| MCP | 职责 | 说明 |
| --- | --- | --- |
| `ios-device` | **自建**设备操作：`ios_ssh` / `ios_push`·`ios_pull` / `ios_info` / `ios_apps` / `ios_frida`(默认 spawn，走 27045) / `ios_apt_*` / `ios_setup_auth` | SSH usbmux 直连；frida 自动 relay 27045。日常注入用这个，不用 frida-mcp |
| `frida-mcp` | 通用 frida 编排 | 走 USB 默认 **27042（本机未装）**，抗检测目标不要用 |
| `ida-pro-mcp` | Mach-O/arm64 深度静态 | 多实例禁并行 decompile；关键查询前 `server_health` + 地标 |

> frida-mcp 之外，日常连接/spawn/attach 也可直接用 `connect.py` 的助手（frida Python API + paramiko SSH + tidevice）。

### 标准工作流（4 阶段闭环）

1. **采集/侦察 — ios-recon**：`tidevice list` / frida 枚举连真机 → 定位目标 App（bundle id / 容器路径）→ 判断是否加密（`otool -l` 看 `cryptid`）。
   > 若加密（App Store 应用几乎都加密），**先走 ios-unpack 砸壳**出 decrypted 二进制再静态分析。
2. **静态定位 — ios-recon + ida-pro-mcp**：设备 **jtool2 提头 + IDA** 定位签名·加密·token 入口（class-dump/dsdump 仅独立 Mac，非本仓路径）。
3. **动态验证 — ios-dynamic（ios_frida / `connect.get_modded_device`）**：**spawn 优先** + 只连 27045 → 纯原生 Interceptor / SSL hook / 反检测 bypass → 抓运行时密钥与参数。本机无 ObjC bridge。
4. **算法还原 — ios-protocol-signature**：frida RPC 把目标函数当 oracle 在线验证 → arm64 unicorn 离线复现 → 字节级校验。

> **这是闭环不是直线**：phase 4 验证失败就回 2/3 修正假设；签名还原主战场是 ios-protocol-signature，在 2↔3↔4 之间反复迭代。

### 阶段 ↔ 技能 ↔ MCP

| 阶段 | 技能 | 主用工具/MCP |
| --- | --- | --- |
| 采集/侦察 | ios-recon（入口） | tidevice / ios-device MCP / SSH |
| 砸壳（加密时） | ios-unpack | 手工 frida dump（27045）/ bfdecrypt（可能未装） |
| 静态定位 | ios-recon + ios-protocol-signature | jtool2 / ida-pro-mcp（class-dump/dsdump 不依赖） |
| 动态验证 / SSL / 越狱检测 | ios-dynamic、ios-protocol-signature | **ios_frida / connect.get_modded_device()**（27045） |

> 真机基线：iPhone 7 Plus（**iOS 15.8.8** / arm64 / A10 / Dopamine 3.0.4 **rootless**）。UDID `f054f9edeb4dbea7978c24fe48f7b16f2be36f9f`。frida = `systemagentd@27045` + 源码 backtracer agent（原版 27042 未装）。**SSH root 免密钥**：`ios_ssh`（usbmux 直连），或 `ssh -i frida-mod/keys/id_ios root@127.0.0.1 -p 2222`。OTA 后密钥丢了用 `ios_setup_auth`（mobile+sudo）。

## 工具链

| 工具 | 位置/命令 | 用途 |
|------|------|------|
| Frida (host) | venv `.venv\Scripts\`（frida 17.15.3，**勿用全局 16.5.9**） | 动态 Hook、spawn/attach、RPC |
| frida-server (device) | **`systemagentd@27045`**（level2）+ agent `coreservice.dylib`。首选 `tidevice relay 27045`；AMDS 抖则 **SSH-L 隧道**（`ssh -N -L 27045:127.0.0.1:27045`）。TCP 通但握手 hang → `launchctl kickstart -k system/re.coreload.svc`。禁 `--set-default`。见 `frida-mod/` | 设备端插桩引擎 |
| tidevice | `.venv\Scripts\tidevice`（0.12.11） | usbmux、端口转发、syslog |
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
└── CLAUDE.md                 # 项目总规 / 角色（alwaysApply）
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
- **spawn 优先**：后台 attach 固定 25s 超时。抗检测 App **只连 27045**，禁止 `get_usb_device()`。
- 连设备先确认 `tidevice list`；空则查 AMDS（`net start` 需管理员）/ 僵尸 relay。SSH 首选 `ios_ssh`。AMDS 老抖：SSH-L 隧道；27045 TCP 通但 frida 握手 hang：`launchctl kickstart -k system/re.coreload.svc`（watchdog ≥15s）。
- **本机魔改 frida 无 ObjC bridge**，hook 只走纯原生 Interceptor。抓包优先 hook 系统 `libboringssl`，不要先配代理。
- **新目标一律按上方模板在 `projects/<target>/` 下创建**，不在根目录散落 .py/.js/.ipa/截图。
- 砸壳产物 → `projects/<target>/ipa/`（或 `dump/`）；提头 → `.../headers/`（jtool2/IDA）；Frida/hook → `.../hooks/`；Python → `.../scripts/`；抓包/日志 → `.../capture/` 或 `.../artifacts/`。
- 通用可复用 hook 放 `hooks/`；第三方工具包放 `downloads/`。
- **改 skill**：编辑 `.claude/skills/<skill>/SKILL.md`（实时执行源）；进化记录见 `.claude/skills/EVOLUTION_LOG.md`。
- **改记忆**：编辑 `.claude/memory/` 后跑 `tools/sync-claude-to-cursor.ps1` **和** `tools/sync-claude-to-zcode.ps1`；MCP 改根 `.mcp.json` 后同样跑这两条，并核 `.codex/config.toml` 三台 server 是否仍对齐。
- **e2e 验证纪律**：验证自造签名/砸壳产物时绝不高频重试无效请求（触发服务端风控软封设备）；单次/间隔久/先存 code=0 基线对照/连续失败立即停手。
