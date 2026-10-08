---
name: android-dynamic
description: Android 运行期动态分析专项。用于真机（Pixel 6 主力 / Pixel 4 XL 印度支付矩阵机）上的 Frida Hook/RPC、反注入判因、Java/JNI/native 最窄边界观察、设备注册与风控状态取证、SSL Pinning 与 native 网络栈绕过、Stalker/运行期快照和 Root 检测验证。触发词：Android Frida、Hook、动态调试、设备注册取证、风控状态、attach、spawn、反Frida、SSL pinning、Cronet、ANet、libxquic、Stalker、native trace、RPC oracle、eCapture。
---

> ⚠️ **本机环境适配（20260920 维护注）**：本机为 macOS，`frida-orchestrator-mcp`(80工具)/`reverse-index-mcp`/`algo-lab-mcp` 已装（vendor/android_mcp，20260922）。设备操作也常用 `adb`（mac 路径，非 `android_mcp\toolchain\...adb.exe`——该 Windows 路径段由 install.sh 装的 Google platform-tools 替代：`~/.local/bin/adb`；MCP 与 android-unpack 脚本统一按 `ANDROID_MCP_ADB` > 包内路径 > PATH 解析）+ 项目 venv frida；静态索引用 `jadx` MCP（jadx-gui）+ grep 替代 reverse-index；算法对拍脚本自行落盘运行替代 algo-lab。serial 用显式参数或 `ANDROID_SERIAL`。

# Android Dynamic

## 任务边界

本 Skill 负责 Android 运行期证据：Hook、trace、RPC、SSL/native 网络观察和反注入判因。

- APK/组件/API 静态侦察与抓包配置治理 → `android-recon`
- 真实 DEX、VDEX、内存 SO 段提取 → `android-unpack`
- Unicorn/unidbg、frozen blob、算子提升和离线协议实现 → `protocol-signature-reverser`
- 不引入 iOS/IPA/Mach-O/越狱或通用 CTF 动态流程。

仓库内样本与两台真机（Pixel 6 `<ANDROID_SERIAL_P6>` / Pixel 4 XL `<ANDROID_SERIAL_P4XL>`）默认属于用户已授权的本地 Android 环境，不重复询问授权；目标、设备、账号或外部系统越出仓库约定时才重新确认。多设备在线时 Hook/RPC 命令固定唯一 serial。

## 固定工具链与不变量

- ADB：`android_mcp\toolchain\bin\windows\platform-tools\adb.exe`，每次固定唯一 serial。
- 主路径：`frida-orchestrator-mcp`；先 `toolchain_status`、`device_health`、`patched_frida_status`、`frida_ps`。
- 主客户端：专用 venv Python `frida==16.5.9`；主 server：`/data/local/tmp/new-server` 16.5.8-dev.11。不要回落到 PATH 中的 Frida CLI。两台真机均部署 `new-server`：P6 常驻，P4XL 默认未运行、用前先 `patched_frida_status` 探测并启动。
- 设备侧配套：两台 `/data/local/tmp/` 均有 `ecapture`（无注入抓 TLS 明文）与 `stackplz`（native trace）、`okhttpfind.dex`；P4XL 另有 frida-gadget×2。Cronet/QUIC 强 pinning 优先考虑 ecapture 零注入路径。
- server 仅监听设备 loopback；宿主只建 `--no-rebind` 的临时 ADB forward，结束精确删除。
- 每次注入会话使用唯一 session id，记录 package/PID/start identity；停止或清理前重新核对 PID，防 PID 复用误杀。
- 输出落 `projects/<target>/hooks/` 与 `artifacts/`，保留脚本、日志、时间、版本、PID、模块基址和清理结果。

## 证据门

“有反 Frida/反调试”必须同时具备：

1. 同一 serial、ABI、client/server 和 transport 能对已知无防护 App 完成相同 attach/spawn；
2. 目标失败可稳定复现，并有 logcat/tombstone/进程或 server 状态证据。

没有两证时只报告工具链症状，不升级结论。注入、代理或进程连续出现三次同类失败时停止同类尝试，进入归因或零注入路径。

## 工作流

### 1. 定义最窄运行边界

从静态调用链选择离信任变化最近且侵入最小的位置：

1. request builder / signer 的输入输出；
2. Java↔JNI marshaling；
3. crypto 原语入参；
4. native 网络明文入口；
5. 只有上层不可达时才 trace 更底层代码。

不要先做广域 Hook。记录“为什么这个点能区分当前两个假设”，先观察，再决定是否修改返回值。

### 2. 设备与状态预检

写入/注入前记录：

- serial/state/ABI、包名、PID 和前台 App；
- server/client 版本与监听地址；
- Zygisk/LSPosed/AlgorithmAide/HMA 当前状态；
- 全局 proxy、NAT、ADB forward；
- 对应恢复命令。

设备歧义、offline、ABI/版本不配、包名不合法、前一次注入残留或恢复路径不明确时停止。动态工作结束后，前台 App、proxy/NAT、forward 和模块配置应恢复到基线。

### 3. 选择注入方式

侵入度按缺口选择，不按固定流水线升级：

| 已有证据 | 入口 | 失败后 |
|---|---|---|
| 不需进程内证据 | eCapture/Root 读取/原版流量 | 保持零注入 |
| 目标已运行且 attach 可用 | 精确 PID attach | 核对 tombstone/server，再决定是否 spawn |
| 必须捕获冷启动初始化 | spawn | 启动期 watchdog 则停止重复 spawn |
| 已证实 ptrace/启动期检测且在线 Hook 必需 | 评估 Zygisk/Gadget | 系统/zygote 异常立即恢复并降为零注入 |
| ART 完整性或进程级反注入 | 不做 Java/进程内 Hook | Root dump/eCapture/纯协议 |

已知局部经验只能作为候选：商业 ART-hook 检测目标优先 native；部分美团系使用运行中 PID attach；抽取壳的冷启动/执行覆盖由 `android-unpack` 决定。每个新版本必须重新用证据确认。

### 4. Hook 与 RPC

优先 `start_frida_hook` 或 `generate_frida_rpc_template` + `frida_rpc_call`。脚本以当前 16.5.x runtime 可解析的 API 为准：

```javascript
Java.perform(function () {
  var Target = Java.use("com.example.Target");
  Target.sign.implementation = function (input) {
    var out = this.sign(input);
    send({kind: "sign", input: String(input), output: String(out)});
    return out;
  };
});

var libc = Process.findModuleByName("libc.so");
var fopen = libc ? libc.findExportByName("fopen") : null;
if (fopen) {
  Interceptor.attach(fopen, {
    onEnter: function (args) { send({kind: "fopen", path: args[0].readUtf8String()}); }
  });
}
```

- 二进制大数据分块 `send()` 或写临时文件后 `root_pull_file`；每块带 offset/total/hash。
- 模块后加载时监听加载事件后 re-arm；不能只在 spawn 时查一次基址。
- 动态注册 JNI 用 `register_natives` 模板逐项记录 method name、JNI signature、function pointer、module+offset；表数量必须有上限，空指针/坏指针逐项报错，不能因一项不可读中断整次映射。
- Native 地址一律记录 module hash、base 与 relative offset，不只保存绝对 VA。
- RPC 是 oracle 依赖；交付必须明示设备/进程/session 条件。

### 4.1 设备注册与风控的最窄取证

先接收静态来源锚点与待区分假设，完整状态机、字段谱系和拒绝归因交 `protocol-signature-reverser` 的[设备注册谱系](../protocol-signature-reverser/references/android-device-enrollment.md)与[风控/传输判因](../protocol-signature-reverser/references/android-risk-transport.md)。本 Skill 只补运行证据：

- 观察 Challenge 获取、密钥 alias/公钥登记、attestation 请求、凭证读写/刷新/注销与遥测提交的实际输入输出；按同一 request id 关联 Java/JNI/native/network，异步调用另记关联依据。
- 每条证据带原始请求与响应锚点、时间/时钟来源、serial、App 版本、session/PID、账号脱敏标识及前后状态；缺失或未触发的阶段显式标注。
- 先读现有状态；不把清数据、重装、刷机、改代理或切换账号当采样前置，不为“冷启动”主动破坏当前注册关系。
- 一次性 Challenge/token 记录有效期、消费位置与已用状态；不为凑样本反复调用或重放，不把新 Challenge 的输出差异直接归因为随机数。
- 密钥不可导出不等于不能调用；观察 alias、算法/参数、授权要求与签名结果，实际调用和硬件保护级别需各自证据，不采集私钥或账号秘密。
- 共享模板和报告只保留脱敏且可关联的标识、摘要与本地证据路径；原始抓包沿既有敏感证据边界保存，不把凭证值复制进模板。

### 5. Java/ART 与 native 网络栈

| 现象 | 处理 |
|---|---|
| Java Hook 装上但业务静默降级 | 先撤 Hook 做原版对照；若证实 ART-hook 检测，改 JNI/native 边界 |
| Cronet/TTNet | 不继续堆 OkHttp Hook；定位 native request/crypto/TLS 边界 |
| ANet/libtnet/libxquic | Hook 实际 header/body 提交点；模块后加载需 re-arm |
| Flutter/libflutter | 从 native TLS/serializer/JNI 边界观察 |
| Shark/NV/私有隧道 | 先确认隧道入口和传输层；签名归因转 protocol |

Hook 命中只证明代码执行；必须把输入、输出、调用栈或服务端分支与同一会话对应起来。

### 6. SSL/抓包选择

按最低侵入度选择：

- 标准信任链/弱 pinning：Reqable/Charles + 正确 Android 14 CA；
- 标准 Java pinning：在当前 App 范围内观察/绕过 TrustManager/OkHttp；
- native TLS、代理检测或 App 配代理即断网：eCapture 或目标 native 明文入口；
- QUIC/私有传输：定位 header/body 提交点，传输指纹问题交 `projects/fp_stack/`；
- 透明代理/iptables 只在需要时使用，写前保存规则，结束精确恢复。

是否抓到包不等于签名通过；HTTP 200 不等于业务成功。

### 7. SO 运行期分析

静态地址与函数范围先由 IDA/rabin2/Ghidra headless 确认。GhidraMCP 当前仅 `documented`，未注册、未 validated。

- 代码页 Hook 导致完整性失败：停止改页，使用 Stalker、硬件/Root 取证或运行期快照；
- trace 地址必须换算为 module+offset，并与静态反汇编核对；
- 检查 `RDTSC/RDTSCP/CNTVCT_EL0/gettimeofday/clock_gettime` 等时序源；
- 快照保存映射、重定位后只读段、堆依赖、输入输出与版本锚点；
- 需要 Unicorn/unidbg/frozen blob 或纯算时转 `protocol-signature-reverser`。

## 失败分支

| 触发 | 一线处理 | 仍失败 |
|---|---|---|
| `frida_ps` 空/TransportError | 核 server、loopback forward、client/server 版本 | 重启 MCP/server，不切 PATH CLI |
| attach 报 closed/server 崩 | 核 PID、root、tombstone 与无防护对照 | 需要冷启动才试一次 spawn；否则零注入 |
| spawn 启动期 SIGKILL | 保存 logcat/tombstone，判 watchdog | 不循环换版本；Root dump/eCapture |
| Java Hook 成功但业务失效 | 撤 Hook 做原版同环境对照 | 改 JNI/native，保留判因证据 |
| native Hook 一装就崩 | 核地址/ABI/模块 hash/代码完整性 | Stalker/快照/零注入 |
| RPC 输出可得但自建请求失败 | 固定同一会话做传输/字段 diff | 转 protocol 做签名/生命周期判因 |

## 交付门

保存脚本/hash、设备与 App 版本、session/PID、模块 offset、原版对照、清理结果和未解项。确定性算法对拍至少 3 组非样例输入→输出；设备注册等有状态取证按已发生的阶段留证，不为满足数量消耗一次性凭证。若只实现 RPC/oracle，明确标为止损型或在线依赖，不得称离线纯算。

## 不要做

1. 不把 Zygisk、spawn 或广域 Hook 当默认第一步。
2. 不混用 arm64 真机与 x86_64 模拟器二进制，不混用 16.5.x server 与 PATH 17.x 客户端。
3. 不按包名盲杀、不复用旧 PID、不用 `pkill -f` 代替身份核验。
4. 不在未自证工具链时宣称“目标有反 Frida”。
5. 不把 Hook 安装成功、日志出现、HTTP 200 或可解析输出当最终验收。
6. 不在本 Skill 中把 trace/快照包装成离线算法完成。
