---
name: android-unpack
description: Android APK 脱壳与运行期解密产物提取专项。用于壳识别、整体壳/抽取壳区分、Root 零注入内存提取、受控 Frida DEX dump、VDEX 与运行期 SO 代码段恢复，并以结构校验和 fresh JADX 结果验收。触发词：Android脱壳、加固、DEX提取、空壳、抽取壳、FART、Youpk、VDEX、360加固、梆梆、爱加密、SO脱密、Root内存dump。
---

> ⚠️ **本机环境适配（20260920 维护注）**：本机为 macOS，`frida-orchestrator-mcp`(80工具)/`reverse-index-mcp`/`algo-lab-mcp` 已装（vendor/android_mcp，20260922）。设备操作也常用 `adb`（mac 路径，非 `android_mcp\toolchain\...adb.exe`——该 Windows 路径段由 install.sh 装的 Google platform-tools 替代：`~/.local/bin/adb`；MCP 与 android-unpack 脚本统一按 `ANDROID_MCP_ADB` > 包内路径 > PATH 解析）+ 项目 venv frida；静态索引用 `jadx` MCP（jadx-gui）+ grep 替代 reverse-index；算法对拍脚本自行落盘运行替代 algo-lab。serial 用显式参数或 `ANDROID_SERIAL`。

# Android Unpack

## 任务边界

目标只有一个：从 Android 加固样本取得真实 DEX，或取得运行期已解密的 SO 代码段，并证明产物可用。

- APK/组件/API 静态分析 → `android-recon`
- 为业务逻辑做 Frida Hook、trace、SSL 绕过 → `android-dynamic`
- 签名/加密算法还原与 unidbg/Unicorn → `protocol-signature-reverser`
- 不引入 iOS/IPA/Mach-O/越狱或通用 CTF 脱壳流程。

本仓库与两台指定真机（Pixel 6 `<ANDROID_SERIAL_P6>` / Pixel 4 XL `<ANDROID_SERIAL_P4XL>`）默认处于用户已授权的本地 Android 范围，不重复询问授权；目标或设备扩展到仓库约定之外时才重新确认。

## 不变量

- ADB 只用 `android_mcp\toolchain\bin\windows\platform-tools\adb.exe`，每个脚本显式传唯一 `--serial`。
- 输出显式传 `--output projects/<target>/apk/<fresh-dir>`；目录已非空则停止，不覆盖。
- 先记录 APK/version/hash、包名、ABI、设备状态、Root/Frida/Zygisk 状态和恢复命令。
- 侵入度从低到高：静态识别 → Root 零注入 → attach/spawn → Zygisk/重打包。若低侵入路径已足够，不升级。
- 脱壳脚本的退出码、文件名含 `dex_`、DEX magic 或文件非空都不能单独判成功。

## 已验证入口

| 入口 | 用途 | 成功含义 |
|---|---|---|
| `apk_protection_analyzer.py` | 静态壳候选与策略提示 | 只算识别候选，不算已脱壳 |
| `unpack_orchestrator.py` | 拉 base/splits、执行受支持策略、校验 DEX、fresh JADX | 只有有效 DEX 且 JADX 产出 Java 才成功 |
| `root_memory_extractor.py` | 唯一设备上的 Root 零注入 DEX 提取 | 至少一个结构有效 DEX；仍需 fresh JADX |
| `enhanced_dexdump_runner.py` | 已通过 dynamic 预检后的受控 Frida dump | Frida rc=0 且结构有效 DEX；仍需 fresh JADX |

运行目录只保留上表 4 个入口及其直接依赖。历史 anti-debug、snapshot、梆梆 runner 和裸内存脚本未达到当前验收门，已从 active Skill 移除；需要对应能力时先在目标项目中建立可复现测试，再决定是否实现。

## 工作流

### 1. 识别壳形态

```powershell
python .claude\skills\android-unpack\scripts\apk_protection_analyzer.py --apk <apk> --json --output projects\<target>\artifacts\protection.json
```

结合 APK 内容、Application/Stub、native 库、类数量与方法体判断：

| 形态 | 证据 | 首选 |
|---|---|---|
| 无壳/工具 malformation | 业务类与方法体完整，或仅解析器报错 | 回 recon；不要脱壳 |
| 整体壳 | 磁盘 DEX 仅 Stub，真实 DEX 运行期出现 | Root 零注入；防护低时可 Frida |
| 抽取壳 | 类结构在，关键 CodeItem 为 nop/return | 执行覆盖 + CodeItem repair |
| VDEX/OAT | 运行期代码主要在 VDEX/OAT | Root 提取后按版本转换并验 DEX |
| native 自解密 | 磁盘 `.text` 高熵，运行期出现可执行解密段 | Root dump 段并重建 ELF |

壳厂商只帮助选择候选策略；不能用厂商名代替当前版本的实验。

### 2. 设备与输出检查

```powershell
$ADB = "android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
& $ADB -s <serial> get-state
& $ADB -s <serial> shell getprop ro.product.cpu.abi
```

多设备、offline、ABI 不匹配、包名不合法、Root 状态不明、输出目录非空或上次注入残留影响系统时，停止。进程级反注入或系统异常目标只走零注入路径。

### 3. 执行策略

优先使用一键编排：

```powershell
python .claude\skills\android-unpack\scripts\unpack_orchestrator.py --package <pkg> --serial <serial> --apk <apk> --output projects\<target>\apk\unpacked_<timestamp> --strategy auto --verbose
```

明确选择 Root：

```powershell
python .claude\skills\android-unpack\scripts\root_memory_extractor.py --package <pkg> --serial <serial> --output projects\<target>\apk\root_<timestamp> --verbose
```

只有 `android-dynamic` 已证明当前 server/client/ABI 与注入方式可用时，才单独使用：

```powershell
python .claude\skills\android-unpack\scripts\enhanced_dexdump_runner.py --package <pkg> --serial <serial> --output projects\<target>\apk\frida_<timestamp> --deep-search --verbose
```

该 runner 不再从 PATH 选择 Frida；只接受当前 Python 环境旁或 `ANDROID_MCP_FRIDA_DEXDUMP` 指定的可验证入口。standalone `--bypass-antidebug` 当前不受支持时必须失败，改走 `android-dynamic + frida-orchestrator-mcp`。

### 4. 抽取壳

反射枚举、`getDeclaredMethods()` 或 class resolve 只算候选触发，不能证明方法体已回填。完成条件必须同时包括：

1. 覆盖真实业务入口，实际执行目标方法；或使用 FART/Youpk 等记录运行期 CodeItem；
2. 保存 method→CodeItem/offset 映射；
3. 将运行期方法体 patch-back 到目标 DEX；
4. fresh JADX 能反编译关键类，关键方法不再是 nop/return；
5. 至少一条真实调用链能从入口走到修复后的方法。

做不到 patch-back/JADX 验收时，只能报告“已触发/已采集候选”，不得报告脱壳完成。

### 5. 360 VIP 抹 magic 与 SO 解密段

- 搜不到 `dex\n` 但 maps 有大匿名可读/可执行段：先保存 maps 与范围，再以 DEX header_size/endian 等多字段候选扫描；切片后重建 magic、SHA-1、Adler32，并走完整 DEX 验收。
- dump 高 VA 地址时，offset/skip 在 PC 端用 64 位计算后传给设备；不在 Android shell 里做可能溢出的地址算术。
- native 解密段：同时保存磁盘 SO hash、maps、内存段、基址/权限/offset；用 ELF program headers 和反编译/反汇编验证重建结果。
- 设备文件优先通过 `frida-orchestrator-mcp` 的 `root_pull_file` 拉取，不用 Git Bash 直接传 `/data` 路径。

## 验收

DEX 最低结构检查：`dex\n` 版本、header size、file size、endian tag 与实际长度一致。随后必须在全新目录运行：

```powershell
tools\jadx\bin\jadx.bat --show-bad-code -d projects\<target>\decompiled\unpacked_verify_<timestamp> <dex-or-apk>
```

通过条件：

- JADX rc=0 或可解释的非致命 warning；
- 产出 Java 源码；
- 目标业务类与关键方法体存在，不是 Stub/nop/return；
- base/split/多 DEX 清单完整；
- 记录版本/hash、命令、日志、失败方法和未修复项。

SO 产物必须能由 IDA/rabin2/Ghidra headless 解析 program headers/代码段，并与运行期地址映射对应。GhidraMCP 当前仅 `documented`、未注册、未 validated，不能作为已通过证据。

## 失败分支

| 触发 | 一线处理 | 仍失败 |
|---|---|---|
| 注入崩 App/server | 清理并恢复；改 Root 零注入 | 系统也受影响则停止所有注入 |
| Root dump 没 DEX | 核对触发时机、maps、split/VDEX、抽取壳形态 | 保存取证并转执行覆盖/CodeItem repair |
| 只有 magic 或文件名像 DEX | 结构校验 + fresh JADX | 失败即丢弃候选，不报成功 |
| 抽取壳仍是空方法 | 增加真实执行覆盖并 patch-back | FART/Youpk；仍无结果则列未解方法 |
| native 段重建后不可反汇编 | 复核基址、页边界、ELF offset/权限 | 保留原始 dump 和映射，不伪造修复 |

## 不要做

1. 不凭退出码、日志“success”、文件数量、magic 或预估成功率报完成。
2. 不推荐未验收的 anti-debug、snapshot 或梆梆 runner。
3. 不在 x86_64 模拟器死磕只含 arm64/反模拟路径的壳。
4. 不用 `pkill -f` 清理与当前 shell 命令同名的服务；先核 PID 与进程身份。
5. 不覆盖用户 APK、输出或设备配置；任何写入先备份、写后验证、失败恢复。
6. 不把抽取壳的反射 resolve 当真实执行覆盖。
