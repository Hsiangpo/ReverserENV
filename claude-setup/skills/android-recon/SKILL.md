---
name: android-recon
description: Android APK 逆向侦察与静态分析入口。用于设备与工具链预检、APK 拉取、malformation/加壳初判、jadx/apktool 反编译、网络栈识别、API/调用链索引、设备注册与风控 SDK 分诊和抓包通路治理；发现壳、运行期 Hook 或签名算法问题时路由到对应专项。触发词：Android逆向、APK反编译、jadx、apktool、提取API、调用链、设备注册入口、风控SDK识别、连真机、证书、抓包、QUIC、Cronet、ANet、malformation。
---

> ⚠️ **本机环境适配（20260920 维护注）**：本机为 macOS，`frida-orchestrator-mcp`(80工具)/`reverse-index-mcp`/`algo-lab-mcp` 已装（vendor/android_mcp，20260922）。设备操作也常用 `adb`（mac 路径，非 `android_mcp\toolchain\...adb.exe`——该 Windows 路径段由 install.sh 装的 Google platform-tools 替代：`~/.local/bin/adb`；MCP 与 android-unpack 脚本统一按 `ANDROID_MCP_ADB` > 包内路径 > PATH 解析）+ 项目 venv frida；静态索引用 `jadx` MCP（jadx-gui）+ grep 替代 reverse-index；算法对拍脚本自行落盘运行替代 algo-lab。serial 用显式参数或 `ANDROID_SERIAL`。

# Android Recon

## 任务边界

本 Skill 只负责 Android 的第一阶段：样本/设备就绪、静态证据、网络栈与抓包通路、专项分诊。

- 空壳 DEX、VDEX、运行期解密 DEX/SO → `android-unpack`
- Frida、反检测、SSL 强绕过、native 运行期 trace → `android-dynamic`
- 签名/加密判因、unidbg/Unicorn、纯算或 oracle 交付 → `protocol-signature-reverser`
- 不引入 iOS/IPA/Mach-O/越狱、PE 或通用 CTF 流程。

本仓库中的样本、工具和两台真机（Pixel 6 / Pixel 4 XL）默认属于用户已授权的本地 Android 环境，不重复询问授权。只有目标、设备、账号或系统扩展到仓库约定之外时，才重新确认范围。

## 固定事实

- 权威规则：仓库根 `CLAUDE.md`；逆向验收：`.zcode/memory/reverse_principles.md`。
- ADB：`android_mcp\toolchain\bin\windows\platform-tools\adb.exe`，所有设备命令固定唯一 serial；MuMu 只作显式 fallback。
- 真机基线：Pixel 6 `<ANDROID_SERIAL_P6>` / Android 14（主力战场机）；Pixel 4 XL `<ANDROID_SERIAL_P4XL>` / Android 13（印度支付矩阵机，含 Tricky_Store/HookVIP）。两台均 arm64 root；多设备在线时所有命令显式 `-s <serial>`。开始动态或写设备前以当前探测结果为准，不凭文档假定在线。
- 输出必须进入 `projects/<target>/` 的 `apk/`、`decompiled/`、`capture/`、`artifacts/`、`docs/`；目录只用 ASCII，已有非空输出不覆盖。
- 优先使用自建 MCP：`frida-orchestrator-mcp`（设备/拉包/代理）、`reverse-index-mcp`（静态索引）。

## 工作流

### 1. 锁定目标与基线

轻量问题先写一句可验证目标；需要产物或设备操作时补齐目标能力、判官、交付形态、成功标准、止损线和真实样本。

记录：

- APK 路径、版本、SHA-256、包名；
- 当前 serial/state/ABI；
- jadx/apktool 版本；
- 新输出目录；
- 若将修改网络：当前 `http_proxy`、NAT 规则、CA hash 和恢复命令。

设备有多个、offline、包名不确定、恢复基线缺失或输出目录会被覆盖时，停止写操作。

### 2. 获取 APK 并区分工具故障、malformation 与壳

优先用 `pull_package_apk`，保留 base 与 split APK 清单。外部 APK 先计算 hash。

```powershell
tools\jadx\bin\jadx.bat --deobf --show-bad-code -d projects\<target>\decompiled\jadx <apk>
tools\apktool.bat d <apk> -o projects\<target>\decompiled\apktool_<timestamp>
```

- jadx 报错：用新 apktool 目录复现，并记录错误；不能直接判加固。
- 仅有 Stub/极少类：以壳特征复核后转 `android-unpack`。
- Java 可读：jadx 追调用链；需精确 Manifest/resources/smali 时再用 apktool，不要求所有任务双跑。
- ZIP 库存同时识别运行时组合：`index.android.bundle`/`.hbc`/`libhermes.so`（React Native/Hermes）、`libflutter.so`+`libapp.so`+`flutter_assets`（Flutter）、`libil2cpp.so`+`global-metadata.dat`（Unity IL2CPP）；单一文件只算候选。
- 离线枚举 APK 内 `.cer/.der/.pem/.crt` 与 `network_security_config.xml`；可解析证书只记录 subject/issuer/有效期/SAN DNS。SAN 只是候选 host，不据此做网络探测或扩域。
- 记录反编译 warnings/failed methods；反编译成功不等于运行期逻辑已证实。

### 3. 先识别网络栈，再选抓包或 Hook 路径

| 静态锚点 | 判定 | 后续 |
|---|---|---|
| `okhttp3` / Retrofit | 标准 Java HTTP 栈 | 常规代理；需要 Hook 转 dynamic |
| Cronet / `libcronet` / TTNet | Chromium/native 栈 | 不继续堆 OkHttp Hook；转 dynamic/eCapture |
| ANet / `libtnet` / `libxquic` / MTOP | 阿里 native/QUIC | 在 recon 只记录栈与入口；实际 Hook 转 dynamic，签名转 protocol |
| Shark / NV / 私有隧道 | 美团系私有传输 | 保存真实流量形状；转 dynamic 或 `projects/fp_stack/` |
| `dart:io` / `libflutter` / `libapp.so` | Flutter native 网络 | 转 dynamic 的 native 边界 |

不要把某个 App 的入口或策略泛化为全局规则。网络栈结论要附字符串、类、导入符号或 maps 证据。

### 4. 建索引并闭合调用链

对 `projects/<target>/decompiled/` 使用：

1. `index_project`
2. `find_endpoint` / `find_symbol` / `search_strings`
3. `list_suspicious_sign_methods`
4. 从外部输入或 request builder 反向追到仓库层、JNI、签名器或网络 sink

API 记录至少包含 method/path、源文件与行号、参数/headers/body、调用链和未解动态字段。关键词命中、导出组件或 WebView API 只算候选；没有 source→sink 或运行证据时不能升级为结论。

### 4.1 设备注册与风控分诊

涉及首次启动、设备入库或账号设备绑定时，沿真实调用链标注：

- 安装 ID、系统标识、SDK 标识与服务端设备 ID 的读取/生成/回填位置，区分作用域，不按 `device_id` 字段名合并。
- Challenge 下发 → 密钥生成/alias → 公钥注册 → attestation 提交 → 设备凭证落盘；未知步骤明确留空，静态链路不证明服务端已经验证。
- 凭证刷新、轮换、过期、注销和账号/会话绑定入口，以及遥测上报与业务请求的依赖；缓存读取不自动等于本地算法。
- Java → JNI → serializer/signer → 网络提交点；标明实际网络库、TLS/HTTP/QUIC 路径、pinning/mTLS 配置证据与观察位置。
- SDK 类名、SO、字符串或厂商指纹仅用于产生候选，不能直接认定采集能力、启用策略或失败原因。

完整字段谱系与状态机交 `protocol-signature-reverser`，按需读[设备注册谱系](../protocol-signature-reverser/references/android-device-enrollment.md)、[风控与传输判因](../protocol-signature-reverser/references/android-risk-transport.md)；需要实际输入输出或状态读写证据再转 `android-dynamic`。本阶段只交付来源锚点、候选调用链和未解项，不为补齐静态空洞触发注册或重置设备。

### 5. 抓包治理

写代理前先确认真实监听端口和 PC 可达地址；Reqable/Charles 使用 OneLite 时，上游链为 `127.0.0.1:7892`。先保存 `http_proxy` 键是否存在及完整原值；读取失败时停止写入，不按“无代理”处理：

```powershell
android_mcp\toolchain\bin\windows\platform-tools\adb.exe -s <serial> shell settings list global
android_mcp\toolchain\bin\windows\platform-tools\adb.exe -s <serial> shell settings get global http_proxy
```

抓包结束仍通过同一 bundled ADB 和 serial 恢复：原先存在该键时，用 `settings put global http_proxy <保存的原值>` 回写（保留空值并正确引用）；原先不存在时，用 `settings delete global http_proxy` 删除本轮新增键。不能只凭 `get` 输出的 `null` 判断键不存在，也不无条件写 `:0`。恢复后重新核对键的存在状态与值均匹配基线。

- “ping/DNS 正常但 App 没网”：先查残留 `http_proxy`、NAT、`ip rule` 和死端口，不先归因为风控。
- Android 14 系统 CA 使用 Conscrypt APEX 路径；写入前备份，写后核对 hash/owner/mode，失败恢复。
- 强 pinning、代理检测、native TLS 或 QUIC 的实际绕过转 `android-dynamic`。
- WebView 只用 `webview_devtools` 发现当前设备 socket；临时 forward 必须 `--no-rebind`，结束按返回端口精确 remove。

## 失败分支

| 触发 | 一线处理 | 仍失败 |
|---|---|---|
| jadx 类残缺 | `--show-bad-code`、增加堆、核对 split APK | apktool/smali；若是空壳转 unpack |
| URL/接口搜不到 | 搜字符串拼接、Base64、解密器、request builder | 转 dynamic 捕获运行期参数 |
| 关键逻辑进入 JNI/SO | 保存 Java→JNI 边界、so hash/ABI | 转 dynamic/protocol，不在 Java 层死磕 |
| 抓不到核心包 | 复核监听端口、CA、目标网络栈 | native/QUIC 转 dynamic；传输指纹转 fp_stack |
| 原版 App 与自建请求表现不同 | 先做同环境、同流量形状与传输指纹对照 | 再交 protocol 判定签名/会话缺口 |

## 交付门

交付 `projects/<target>/README.md` 或 `docs/` 记录：样本与工具版本、组件/API/调用链证据、网络栈、抓包状态、路由决定、恢复状态和未解项。HTTP 200、JSON 可解析、索引命中或 jadx 能打开都不能单独充当业务成功。

## 不要做

1. 不用 PATH 中不明版本的 adb/frida 替代 bundled 工具链。
2. 不在多设备歧义下猜 serial，不覆盖已有反编译/抓包目录。
3. 不因 jadx 失败就报“有壳”，不因 OkHttp 未命中就报“没有流量”。
4. 不在 recon 中执行 libxquic/Frida 业务 Hook 或实现签名算法。
5. 不留下代理、iptables、forward、CA 或前台 App 状态变化。
6. 不把静态关键词、HTTP 状态码或格式正确当成最终判官。
