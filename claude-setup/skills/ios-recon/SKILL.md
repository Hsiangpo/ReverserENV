---
name: ios-recon
description: iOS 逆向侦察与静态分析总入口。连真机、定位 IPA/App、判定 FairPlay，检查 Mach-O/ObjC/Swift、Info.plist/entitlements/ATS/deeplink，梳理设备注册与风险信号入口，再分诊到砸壳、动态验证或协议签名。触发词：连真机、连设备、usbmux、拉 IPA、定位 App、Mach-O、dyld cache、class-dump、dsdump、entitlements、设备注册入口、App Attest、DeviceCheck、URL Scheme、Universal Link、抓包、iOS 逆向入口。
---

> ⚠️ **本机环境适配（20260920 维护注）**：本机为 macOS，`ios-device` MCP 老师仍未分发（0818 包只有 frida-mod 设备端与工具）；ida-pro 需付费未装。设备连接用 `frida-agent` MCP / 项目 venv 的 frida / `pymobiledevice3`；SSH 直连设备用 mac 原生工具；提头优先 mac 原生 `class-dump` / `otool`（jtool2 如未装则 brew 安装或以 class-dump 替代）。下文提及 ios-device 工具（`ios_info`/`ios_ssh` 等）的段落按此替代执行。

# iOS Recon —— 侦察与静态分析（总入口）

## 角色定位

你是 iOS 逆向的**侦察兵和分诊台**。先用已有 IPA、二进制和日志固定样本、判断加密范围、提取可读结构，再按缺口**分诊**到 ios-unpack（要砸壳）/ ios-dynamic（要运行证据）/ ios-protocol-signature（要还原算法）。仅本地分析或设计不连接设备；实际需要设备取证时再核当前任务范围与目标身份。

**优先级覆盖后文所有模板和失败出口**：已有注册/密钥/session 或运行中进程须保留时，先已有材料和只读证据；不能因抓包不全、HPACK 缺上下文或 attach 失败自动 spawn、切前台、删状态、改网络或重建隧道。需要改变状态时必须有具体缺口、当前授权和影响/恢复说明；旧项目经验只生成候选。

> ⚠️ **工具纪律**：外部工具默认当坏的。**阉割矩阵只在本节**（真源）；ios-unpack / ios-dynamic 禁止再抄一份补丁清单，只写执行步骤并回指本表。原则见 [[tools-often-crippled-need-repair]]。

## 工具阉割矩阵（dim5 真源，2026-08-18）

每行必须闭环：`本仓状态 → 阉割点 → 修法或弃用替代 → 归属`。修不了就**弃用并指向已验证替代**，禁止「再 git clone 一份网上原版」。

| 工具 | 本仓状态 | 阉割点（实测） | 闭环（修法 / 弃用替代） | 归属 |
|---|---|---|---|---|
| frida 主机 | `.venv` **17.15.3** | 全局 16.5.9 → ProtocolError | 只用 `.venv`；禁全局 | 全 skill |
| frida 设备 | `systemagentd@27045` + `coreservice.dylib`（自编译 level2+backtracer） | 网上 pre-modded / `build.rida.re` 特征不干净；源码 server SIGKILL | **只连 27045**；禁 `--set-default` 27042；原版未装 | ios-dynamic |
| `ios_frida` / 裸 `create_script` | MCP 默认 spawn、设备端走 27045 | frida17 无全局 `ObjC`/`require`/`Frida`；本机魔改 **compile 也无 bridge** | C 导出 + `Interceptor`/HWBP；已知类/selector 可用 ObjC runtime C API 定点换 IMP；`ptr.readByteArray` | ios-dynamic |
| frida-ios-dump | `tools/frida-ios-dump/` = **AloneMonkey 原版未补**（`get_usb_iphone`、`Password=alpine`、`dump.js` 用 `ObjC.classes`） | 打 27042；依赖 ObjC；SSH 密码 alpine | **弃用**。不要再 clone、不要在本副本上打补丁当可用。砸壳走 **手工 dump**（`projects/kuniu/dump_kuniu.py`） | ios-unpack |
| bagbak | **仓库无** | node/frida 版本墙，跟不上 17.15.3 + 无 ObjC | **不装**。同手工 dump | ios-unpack |
| dumpdecrypted | **仓库无 arm64 产物** | 网上常是 armv7；rootless 无 `/bin/sh` | **弃用**。砸壳走手工 dump（`projects/kuniu/dump_kuniu.py`）；不为它编 dylib | ios-unpack |
| bfdecrypt | OTA 后 **/var/jb 已空** | 当「设备已装」会空转 | `ios_apt_list` → 没有再 `ios_apt_install` → respring；仍优先手工 dump | ios-unpack |
| class-dump | **win32 仓库无二进制**（macOS-only） | 网上旧版不认新 Mach-O | **本机不装/不依赖**。提头：设备 `jtool2 -d objc`（先 apt）或 IDA。仅当另有独立 Mac 才可跑，非本仓基线 | ios-recon |
| dsdump | **仓库无** | 常见阉割=无 Swift metadata，输出不全却像成功 | **不下载/不依赖**。ObjC 头 → jtool2；Swift → IDA / `enumerateExports`（砸壳后静态；运行时无 ObjC.classes） | ios-recon |
| jtool2 | OTA 后可能未装（`/var/jb/usr/bin`） | 当「已 apt 装」会失败 | `ios_apt_list('jtool2')` → `ios_apt_install`；ldid 已装可先 `ldid -e` | ios-recon |
| objection | **本机不可用** | 要 frida 17 + **ObjC bridge**；老版 API 也不对 | **弃用**。SSL 走系统 `libboringssl` hook；越狱路径走纯原生 `stat`/`sysctl` | ios-dynamic |
| cycript / debugserver | OTA 清空 | 当已装会找不到 | 用到再 `ios_apt_install`；日常不依赖 | ios-dynamic |
| ida-pro-mcp | IDA 9.3sp1 portable；plugin **可能未装** | `select_instance` 不粘；并行 decompile 漂实例 | 先确认 plugin；串行 + `server_health` + 地标。路径见 [[ida-path]] | ios-recon |
| d810 | IDA 插件已有 recipes | 超大函数 Hex-Rays `too big` → hook 不触发 | 先显式 import optimizer；救不了就 FlowChart CFG。见 [[d810-ollvm-unflattening-recipe]] | ios-protocol-signature |
| frida-mcp | `.venv` 的 exe | USB 默认 **27042（未装）**，且可能选错其他 USB 设备 | **日常不用**。注入走 `ios_frida` / `get_modded_device`；主机 27045 冲突时改 `FRIDA_REMOTE` 本地端口，设备端仍 27045 | ios-dynamic |
| pymobiledevice3 | `.venv` **9.33.1** | CLI 默认取第一台；`syslog` 可无限跑；`pcap --out` 仍向 stdout 打包体 | 只经 `ios_diagnostics`：显式 UDID、1–15s/行字节/1–100包上限、PCAP stdout 丢弃且禁止覆盖 | ios-recon / ios-dynamic |

**禁止开环**：为某个工具再去 GitHub 拉「最新阉割版」当修法。替代链路必须是本仓已验证脚本或 MCP/`ios_apt_*`。

## 设备基线（真机优先，2026-08-11 后）

| 项 | 值 |
|---|---|
| 机型/系统 | iPhone 7 Plus / **iOS 15.8.8** / arm64（A10 T8010，checkm8）|
| 越狱 | **Dopamine 3.0.4 rootless**（`/var/jb`）半不完美：重启后在 Dopamine App 内点 Jailbreak（不用电脑）|
| frida | **只连魔改**：`systemagentd@27045` + 源码 backtracer agent `coreservice.dylib`。原版 27042 **未装** |
| 连法 | 优先 `connect.get_modded_device()` / `ios_frida`，配置完整目标 `IOS_DEVICE_UDID` 并校验命中；手工 relay 同样显式 `tidevice -u <完整UDID> relay ...`，既有本地监听先核归属。主机端口冲突可用 `27146→设备27045`；**禁** `get_usb_device()` / `get_device(UDID)`（可能打 27042 或选错设备）|
| SSH | **root 密钥免密**：私钥 `frida-mod/keys/id_ios`。sshd **禁 root 密码**。恢复：`ios_setup_auth`（mobile + sudo 推公钥），见 [[frida-root-shell-bypass]] |
| UDID | `<IOS_DEVICE_UDID>` |
| 设备端工具 | 已装：openssh / ldid / Sileo / level3 frida。**OTA 清空待装**：ellekit / bfdecrypt / Shadow / jtool2 / odcctools / debugserver / cycript → `ios_apt_install` |
| 首选连法 | **`ios-device` MCP**：`ios_info` / `ios_diagnostics` / `ios_ssh` / `ios_frida`(默认走 27045) / `ios_push`·`ios_pull` / `ios_apt_*` / `ios_setup_auth`。`frida-mcp` 走 USB 默认，本机基本不可用 |

**红线**：禁止 `deploy_frida.py --set-default` 抢 27042（曾内核 panic / 掉越狱）。设备改动只做加法+隔离。见 [[device-reboot-risk-jailbreak-loss]] [[modded-frida-deployed]]。

## 决策树（入口分诊）

```
先检查已有材料与当前范围；确需设备且任务允许时核唯一 UDID（未命中即停）
   → 定位目标 App → otool -l 看 cryptid
   │
   ├─ cryptid=1（加密，App Store 几乎都是）
   │      → 转 ios-unpack 砸壳 → 拿 decrypted 二进制回来静态分析
   │
   ├─ cryptid=0（已解密 / 自签 / 砸过壳）
   │      → 设备 jtool2 提头 + IDA 静态定位（class-dump/dsdump 本机不依赖，见阉割矩阵）
   │
   ├─ 目标是"抓协议样本 / 看接口"
   │      → 首选 BoringSSL/h2 hook（见 Step 6），不要先配代理
   │
   └─ 目标是"还原某签名/加密参数"
          → 静态提头定位入口 → 转 ios-protocol-signature（配 ios-dynamic 动态验证）
```

## Step 1：连接设备（无 UI 优先）

```bash
# 项目 venv（勿用全局 frida）
cd .
.venv/Scripts/tidevice list                    # 有 UDID 行 = usbmux 通
# 空但 USB 设备 Status=OK → Windows "Apple Mobile Device Service" 自停
#   sc query "Apple Mobile Device Service" → STOPPED 则 net start
#   relay 无响应先核监听 owner、完整命令行、目标 UDID 和进程启动身份；只清理本轮创建且确认失效的进程。
#   未知或其他任务的 relay 不杀；换空闲本地端口或记录阻塞。见 [[windows-amds-flap-zombie-relay]]

# frida：必须先 relay 27045，再 add_remote_device（connect.py get_modded_device 会幂等起 relay）
.venv/Scripts/python.exe connect.py --modded
# 若主机 27045 被其他进程占用：给 ios-device 设 FRIDA_REMOTE=127.0.0.1:27146；
# MCP 会 relay 27146 -> 设备固定 27045。每次复用/新起本地 relay 前都先校验 IOS_DEVICE_UDID，
# 新进程显式 `tidevice -u <完整UDID> relay ...`；未命中就失败，禁止猜第一台或继承 MCP stdio。
# Windows 冷启动 relay 实测可超过 5s；relay 启动与 Frida 握手必须分开计时，各留 20s，不能共用一个总 watchdog。

# SSH：首选 ios-device MCP（usbmux 直连 22，免 relay）
#   系统级取证先用 ios_diagnostics(syslog/crash_list/pcap)：有界只读，不启动或操作业务 App
#   ios_ssh("uname -a; ls /var/jb; sw_vers")
#   ios_ssh 失败先区分连接、鉴权、越狱状态和 openssh；单次错误不能直接定因。
#   只有证实对应缺口且当前任务允许恢复，才选择重越狱、补装 openssh 或 ios_setup_auth；不依次全做。
# 备用手动 SSH：
.venv/Scripts/tidevice -u <IOS_DEVICE_UDID> relay 2222 22
ssh -i frida-mod/keys/id_ios root@127.0.0.1 -p 2222
```

确认当前工具确实缺失且本轮允许安装后，才用 `ios_apt_update` → `ios_apt_search` / `ios_apt_install`（走 `IOS_APT_PROXY`）。需要 respring 的安装会影响运行中 App 与会话；未纳入当前任务范围时保持状态并记录依赖，不自动重启 SpringBoard。

frida 枚举（**只走 27045**）：
```python
from connect import get_modded_device
# 前提：已允许设备读取，完整 IOS_DEVICE_UDID 命中；既有监听归属已核对。
d = get_modded_device()
for a in d.enumerate_applications():
    print(a.pid, a.identifier, a.name)
```

> 坑：`frida-ls-devices` / `frida` CLI 的 TUI 在 Git-Bash 里崩 → 用 Python API。`add_remote_device` hang 只算连接症状；分别核监听归属、relay、AMDS、设备服务及超时边界，不能直接认定僵尸 relay。清理只限已核验身份的本轮失效进程。

## Step 2：定位目标 App 与容器

```bash
# 首选 ios_apps(filter="kuaikan") 或 SSH
find /var/containers/Bundle/Application -maxdepth 3 -name "*.app" 2>/dev/null
plutil -p "/path/Target.app/Info.plist" | grep -Ei "CFBundleIdentifier|CFBundleExecutable"
find /var/mobile/Containers/Data/Application -maxdepth 2 -name "*.plist" 2>/dev/null | head
```

## Step 3：判断加密（cryptid）

```bash
otool -l Target | grep -A5 LC_ENCRYPTION_INFO      # cryptid 1=加密 0=明文
# 注意 FairPlay「部分加密」：cryptsize 可能只有 4096（酷牛），不是整段 __TEXT
```
目标代码位于 `cryptid=1` 标记的加密区间 → 将该缺口交 **ios-unpack**。区间外可读 load commands、entitlements、字符串和元数据仍可做本地侦察；不能把它们的可读性当成加密代码已经解密，也不因 cryptid=1 放弃全部静态证据。

分发渠道只作先验：App Store / TestFlight / enterprise / ad-hoc / 自签件都逐个读取当前 Mach-O 的 `cryptid`，同时记录渠道、build 与 SHA-256；禁止按文件名或来源直接判定“要砸/不用砸”。

## Step 4：提取 ObjC/Swift 结构

本机基线 win32 无 Mac，**默认走设备 jtool2 + IDA**（class-dump/dsdump 不依赖，理由见阉割矩阵）：

```bash
# ObjC 头/方法（对 decrypted 二进制；设备端，OTA 后 jtool2 可能要先 ios_apt_install）
jtool2 -d objc Target
otool -Iv Target | head          # 导出/导入符号
otool -L Target                  # 依赖库
# Swift-only（无 @objc）：jtool2 看不到 → IDA，或 exports 兜底
strings -a Target | grep -E "^_\$s"     # Swift mangled 符号
# 运行时枚举类走不通：本机魔改 frida 无 ObjC bridge，别用 ios_frida 扫 ObjC.classes
```

静态定位只加两个锚：ObjC 从 `__objc_methname` selector 交叉引用到 `objc_msgSend`/实现；Swift 从 `__swift5_types`、`__swift5_proto` 与 `$s...` 符号交叉确认，再进反编译，不能只凭单个字符串命名函数。

> 只有另备**独立 Mac** 时才可跑 `class-dump -H` / `dsdump --objc --swift`（非本仓路径，且注意阉割版无 Swift）。
> 超大 OLLVM 函数：Hex-Rays / d810 会 `too big` → 走 IDA FlowChart CFG，见 [[d810-ollvm-unflattening-recipe]]。

## Step 5：iOS bundle 信任面 / 签名信息 / IDA

```bash
ldid -e Target
otool -l Target | grep -A3 LC_CODE_SIGNATURE
plutil -p Info.plist
```

| 静态面 | 查什么 | 结论边界 |
|---|---|---|
| ATS | `NSAppTransportSecurity`、全局/域名/WebContent 例外 | 配置只算线索；必须关联真实 HTTP/TLS 流量，不能把键存在写成漏洞或协议完成 |
| Deeplink | `CFBundleURLTypes`、`com.apple.developer.associated-domains`、AASA | 继续定位 handler 与数据流；scheme/域名声明本身不证明可利用 |
| 共享状态 | `keychain-access-groups`、`com.apple.security.application-groups`、plist/SQLite 路径 | 标注访问组、容器、生命周期；entitlement 不等于已经拿到 secret |
| 嵌入代码 | `Frameworks/`、`PlugIns/*.appex`、provisioning 信息 | 每个 Mach-O 独立记 build/hash/cryptid，不把主程序结论外推到扩展 |

原始 IPA、解包目录、decrypted 与 re-signed 产物必须分路径保存并各记 SHA-256；动态日志只绑定产生它的那一份工件，禁止混证据。

**IDA（ida-pro-mcp）纪律**（[[ida-mcp-parallel-instance-drift]] [[ida-path]]）：
1. `list_instances` → `select_instance(port)` 后，**每次关键查询前**再看 `server_health` 的 `idb_path`，确认在目标二进制。
2. 用目标独有字符串做地标（如 discover 的 `x-mini-mua`、山姆的 `SCClassContentCell`）。
3. **禁止并行** `decompile` / `analyze_batch`（会漂回 active 实例，张冠李戴）。
4. 反编译里出现另一个 App 的符号 = 漂了，立刻停，别顺着假数据分析。
5. 恢复 MCP 前先认 `13337` 的 owner；端口仍监听但 RPC 超时先按 **busy** 处理，不等于 dead。`ida.exe` 占用时只能等待或切换目标实例，严禁结束 GUI 或使用 `taskkill /T`。

## Step 5.1：设备注册与风控入口分诊

仅做本地梳理时，沿现有 IPA/解密 Mach-O/日志取证，不为补样本连接设备或触发注册。先标出候选节点，再用交叉引用闭合实际数据流：

- 固定 bundle/build/hash、签名与 `application-identifier` 前缀、Team ID、entitlements；主 App 与 extension 各自核对，不默认前缀、Team ID 和 vendor 范围等价。
- 区分安装 UUID、IDFV、IDFA/ATT 授权状态、SDK 标识与服务端设备 ID；标出生成/读取/回填点，字段名或一次重装后未变不证明永久身份。
- 区分 Keychain `keychain-access-groups`、可访问性/同步属性与 App Group 容器；追 `SecItem*`、NSUserDefaults/文件读写，entitlement 不证明实际共享或跨重装保留。
- `DCAppAttestService` 的支持检查、generateKey/attestKey/generateAssertion 分开定位；`DCDevice.generateToken` 及服务端两 bit 状态属于 DeviceCheck，不能视为同一证明或固定设备编号。
- 追 keyID/公钥或密钥引用 → 登记请求 → 设备凭证存储 → 后续消费者，并查刷新、轮换、解绑、撤销与账号/session 绑定；Keychain 中的数据项不自动等于 Secure Enclave 私钥。
- 关联 Challenge/请求摘要、遥测事件与 URLSession、Network.framework、WKWebView 或 native 请求提交点；API/SDK 名、域名及 ATS 配置只生成候选，不证明实际执行、服务端校验或业务成功。

完整谱系与判因交 `ios-protocol-signature` 的[设备注册谱系](../ios-protocol-signature/references/ios-device-enrollment.md)和[风控/传输判因](../ios-protocol-signature/references/ios-risk-transport.md)；本 Skill 交付来源锚点、候选上下游与未知项，需要运行证据再转 `ios-dynamic`。

## Step 6：抓包治理（首选 hook，代理兜底）

先复用已有捕获。确需且当前范围允许动态取证时，按实际网络栈和需要保留的状态选最窄观察点，交 ios-dynamic 执行；以下是历史路线候选，不要求全装或逐级通关。禁止默认 spawn、装 bypass 或改 QUIC/代理来填补捕获缺口。

```
优先级（越狱机已验证）：
 1. 纯原生 hook 系统 /usr/lib/libboringssl.dylib 的 SSL_read/SSL_write
    + 同时 hook App 模块名匹配 boringssl|openssl|libssl 的 SSL_*
    + 延迟补钩（spawn 后 dyld 未完，setInterval 数分钟）
    + 离线 HPACK 解 h2；HTTP/1.1 按 content-length/chunked 重组
    模板：projects/ctrip|kuniu|kuaikan 的 ssl_capture.js + parse_h2/parse_flows
 2. QUIC/TQUIC：先选已定位的请求对象/加密前提交点
    （历史 XHS 样本阻断 UDP 不会回落；修改 enableQuic 是改变协议变量的独立实验，需当前范围允许）
 3. Network.framework：TCP 目的地钩 nw_connection_start/copy_endpoint；内存 BIO 的 SSL_get_fd=-1 属正常
 4. HTTP:80 明文或 QUIC 前明文：钩 nw_connection_send/receive，或从 UDP write 回溯请求对象/发送缓冲
 5. 代理 + CA + pinning 绕过：仅当前面走不通（或必须用代理聚合流量）时
    本仓 iOS mitm 固定用 8889（projects/ios-capture）
```

抓不到包先核目标/连接身份、脚本异常、实际网络栈和观察覆盖；若是热进程 HPACK 上下文缺失，标明盲区或转更上层已定位请求边界，不自动冷启动。只有工具链自证和目标可复现证据成立时才将反注入列为已证原因；需要 spawn 或改协议时重新检查当前任务允许的动作与状态影响。

## 已完成目标策略矩阵

| App | bundle | cryptid/砸壳 | 网络栈 | 检测 | 签名主体 | 抓包 |
|---|---|---|---|---|---|---|
| 快看 | com.kuaikan.comic | 已砸，无加固 | 业务系统 h2；广告 TQUIC | 弱 | app_secret_sign = MD5 双时间戳 ① | SSL hook |
| 小红书 | com.xingin.discover | 9.38 已砸；9.44 拉取件仍 cryptid=1；9.45 静态未取证 | cronet/quiche QUIC；部分链可 h2 | metasec：早 attach/GOT 重钩会杀；晚 attach+最小原生 IMP 可用 | x-mini 全链①；shield=③；d=AES/X25519 ①；App Attest 非① | QUIC 前请求对象/晚 attach swizzle；SSL 仅覆盖非 QUIC |
| 懂车帝 | com.ss.ios.auto | 主二进制已砸；3 appex 仍加密 | boringssl h2 | metasec/isecgm + Medusa CFF-VM | Gorgon/Helios ①；Medusa 帧①；**CT 不声称①** | **冷启动 spawn** |
| 山姆 | cn.samsclub.iphone | 已砸 | 业务系统 TLS；同盾=静态 OpenSSL1.0.2+TLV | 同盾通道指纹 | st ①；QIMEI/Turing/同盾三件套 | 通道≠系统 TLS |
| 携程 | ctrip.com | — | boringssl | 弱 | XPS（首页软校验） | SSL 四件套 |
| 酷牛 | net.kuniu | 部分加密 cryptsize=4096 | h2+h1 | 数美越狱检测（level2 不拦 hook） | 登录 RSA-1024 ① | SSL 四件套+延迟补钩 |
| 心遇 | com.netease.moyi | 已砸(160MB) | 业务全 nw h2(易盾h1)+CSJM加密；广告GDT QUIC | 易盾+数美+火山mssdk | 主API=CSJM=CC20P1305+zstd **①纯算e2e已闭环**(密钥成对,caesar.framework,h1直连200) | SSL+`nw_connection_start`+`EVP_AEAD_CTX_seal` oracle |
| nice | com.KKGOO.kk | 本轮未做静态 cryptid 取证（动态路线） | 系统 BoringSSL + Network.framework h2；数美/日志走 HTTP:80 | 重 hook 可触发 `0x8BADF00D` | nice-sign-v1 ①（18/18 对拍；首页 listTabBody e2e） | `fullchain_lite.js`：DNS+nw+BoringSSL，禁重钩 |

细则见 `.claude/memory/` 对应条。新目标按这 6 列补一行，再分诊。

## 交接给下游

| 现象 | 转交 |
|---|---|
| cryptid=1，要静态分析 | **ios-unpack** |
| 要 hook / 绕 SSL / 绕越狱检测 / 反 Frida | **ios-dynamic** |
| 要还原某签名/加密参数 | **ios-protocol-signature** |
| 二进制深度分析（arm64） | IDA + `ida-pro-mcp`（串行 + 地标） |

## 常见坑（失败模式编码 R-xx）

> 每条格式：**编码 现象** → 原因/规则。**成本**=不知道这条会白费多少。
- **R-01 拿全局 frida 连设备** → ProtocolError（16.5.9 vs 17.15.3）。永远用 `.venv`。**成本**：误当设备坏了去重装,~0.5 天。
- **R-02 attach 后台 App 超时 25s** → 挂起是候选，先核进程身份/状态与连接证据。需保留会话时不转 spawn；切前台或冷启动只在当前任务允许且确有必要时选择。**成本**：把超时当重启指令，污染当前会话。
- **R-03 对加密二进制提头** → 先划定 cryptoff/cryptsize；区间外元数据可读不代表区间内代码可分析。不得用未解密区域建立已证调用链。**成本**：用明文字符串替密文代码背书，生成假调用图。
- **R-04 jtool2 看不到 Swift 类** → 无 @objc，走 IDA / `enumerateExports`（**别下 dsdump**，矩阵已弃用）。**成本**：漏掉整条 Swift 业务。
- **R-05 想下 dsdump/class-dump 补 Swift** → 阉割版无 metadata。矩阵已弃用，改 jtool2/IDA。**成本**：以为提全了，后续全歪。
- **R-06 ios_ssh 失败当 MCP 坏** → 越狱未激活或 OTA 清空 openssh。先 Dopamine 重越 / `ios_apt_install`+`ios_setup_auth`。**成本**：重写 MCP、重启 Cursor，方向全错。
- **R-07 get_usb_device / 打 27042** → 本机原版未装，且可能选错其他设备。只走 27045。**成本**：枚举空/连错设备，半天。
- **R-08 tidevice list 空 / add_remote hang** → AMDS、relay、设备服务和监听归属分别核实，不凭症状定因。查服务状态后，只清理本轮创建、身份匹配且确认失效的 relay；禁止按端口字符串批量杀进程。`net start`/`Start-Service` 需管理员及当前恢复范围，不反复重试拒绝；SSH-L 只在需要且允许时使用，固定 UDID 和本地端口归属。见 [[windows-amds-flap-zombie-relay]] + ios-dynamic 连接节。**成本**：误杀其他任务连接或在错误设备上恢复。
- **R-09 IDA 并行查询张冠李戴** → `select_instance` 不粘。串行 + server_health + 地标。**成本**：整轮分析建在别的 App 上（小红书会话实测）。
- **R-10 OTA 后仍按旧工具清单** → `/var/jb` 已空，bfdecrypt/jtool2/ElleKit 没了。先 `ios_apt_list` 再装。**成本**：砸壳/提头全失败却查脚本。
- **R-11 抓包先配代理** → pinning + QUIC 漏。先 SSL hook。**成本**：证书/代理/绕 pinning 大半天，其实 hook 半小时能出接口。
- **R-12 目标 UDID 不在却退回第一台设备** → MCP 必须由 `IOS_DEVICE_UDID` fail-closed；为空、未命中或前缀多匹配都停，复用本地监听也不能绕过校验；新起 relay 显式传 `tidevice -u <完整UDID>`，不猜设备。**成本**：把取证/安装/清理打到另一台 iPhone，证据与设备态全部污染。
- **R-13 主机 27045 被其他进程占用** → 不杀无关进程；改 `FRIDA_REMOTE=127.0.0.1:27146`，relay 主机 27146 到设备 27045。**成本**：把别的 socket 当 iOS relay，出现 connection closed 后反复重装 frida。
- **R-14 relay 固定等 5s 就判失败** → Windows 冷启动 `tidevice relay` 可在 5s 后才监听；给 relay 独立 20s 启动窗口，再另给 Frida 握手 20s。超时只终止本轮新起的 relay。**成本**：设备和 systemagentd 都正常却被假阴性拦住，手工 relay 反而成功。
- **R-15 把 ATS/deeplink/entitlement 声明直接写成漏洞或能力** → 静态键只生成待验证分支；必须补 handler/数据流/真实请求或访问证据。**成本**：报告出现不可复核的假阳性，后续路线被错误优先级带偏。
