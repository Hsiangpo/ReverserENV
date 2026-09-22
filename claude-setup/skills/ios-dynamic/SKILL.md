---
name: ios-dynamic
description: iOS 动态调试/Frida 对抗/SSL/越狱检测与设备注册状态取证。纯原生 Frida Hook(Interceptor/Stalker/硬件断点/ObjC runtime C API)——本机魔改 agent 无 ObjC bridge，不能用 ObjC.classes，已知类与 selector 可定点换 IMP；objection 不可用；按检测面选择 spawn 或晚 attach；抓包优先 hook libboringssl/Network.framework/QUIC 明文层。触发词：Frida、Hook、动态调试、设备注册取证、App Attest、DeviceCheck、spawn、attach、ObjC、Swift hook、objection、cycript、LLDB、debugserver、SSL pinning、越狱检测、反调试、反 Frida、注入秒退。
---

> ⚠️ **本机环境适配（20260920 维护注）**：本机为 macOS，`ios-device` MCP 老师仍未分发（0818 包只有 frida-mod 设备端与工具）；ida-pro 需付费未装。设备连接用 `frida-agent` MCP / 项目 venv 的 frida / `pymobiledevice3`；SSH 直连设备用 mac 原生工具；提头优先 mac 原生 `class-dump` / `otool`（jtool2 如未装则 brew 安装或以 class-dump 替代）。下文提及 ios-device 工具（`ios_info`/`ios_ssh` 等）的段落按此替代执行。

# iOS Dynamic —— 动态调试 / Frida 对抗 / SSL / 越狱检测

## 角色定位

运行期把目标 App 撬开：hook 看/改行为、抓明文流量、对抗反-Frida / 越狱检测。本仓库的**唯一可用 frida**是魔改 `systemagentd:27045`（level2 server + 源码 backtracer agent）。

> ⚠️ **本机硬事实（2026-08-12 至 09-03 实测）**：魔改 agent 是 QuickJS-only，**无 ObjC bridge**——`ObjC.available` 恒 false，`frida-compile` + `frida-objc-bridge` 也救不了。裸 `create_script` 另外还没有 `require` / 全局 `Frida`。这只禁止 `ObjC.classes` 等 bridge API，**不禁止原生 ObjC runtime C API**：类名/selector 已知时可用 `objc_getClass` / `sel_registerName` / `class_getInstanceMethod` / `method_setImplementation` 定点换 IMP。见 [[modded-frida-no-objc-bridge]] [[frida17-bare-inject-no-objc-bridge]]。

## 状态与证据优先级

以下优先于所有连接、spawn、抓包、bypass 模板和失败出口：仅设计/本地分析不执行设备动作。已有注册、密钥、session 或进程需保留时，先已有日志与只读证据，确需注入才选最窄 attach；失败不自动重启、切前台、删 Keychain、改网络或换账号。新动作须有当前缺口、任务范围和影响/恢复条件。

注入秒退、卡死、无流量只算症状；先排 API/ABI、地址、对象生命周期、脚本错误、watchdog 与工具链问题。工具链在已知可用目标自证，且目标异常可复现并有明确证据后，才判断反注入并按当前任务允许的方式干预。当前没有这些材料时交付缺证，不主动扩展实验。

同一业务请求同字节最多 3 次（含首次和已有尝试），漂移更早停；第三次同类失败停止同类线上实验。一次性流程不为凑样本重放，spawn 次数不能代替或重置业务请求预算。

## 连接（第一课，必记）

```
先核完整目标 UDID 命中与本地监听归属；只连设备 27045：
              .venv/Scripts/tidevice -u <IOS_DEVICE_UDID> relay 27045 27045
              d = frida.get_device_manager().add_remote_device('127.0.0.1:27045')
              或 connect.get_modded_device()（幂等起 relay）
              或 ios-device MCP 的 ios_frida（内部走 27045）

禁止：
  get_usb_device() / get_device(UDID)     → 打不存在的原版 27042，或选错其他 USB 设备
  deploy_frida.py --set-default            → 曾内核 panic / 掉越狱
  默认 frida-mcp（USB）                    → 本机原版未装；日常注入用 ios_frida / Python
```

设备端始终是 **27045**；主机 `127.0.0.1:27045` 若被其他进程占用，不杀无关进程，给 `ios-device` 配 `FRIDA_REMOTE=127.0.0.1:27146` 即可。MCP 会做 `host 27146 → device 27045`，`FRIDA_DEVICE_PORT` 保持 27045。

注入前后的系统级证据优先用 `ios_diagnostics`：`syslog` 必须给字面量过滤且最多15秒，`crash_list` 只列报告名，`pcap` 限1–100包并写入不存在的绝对本地路径。它只监听/列名，不替你启动或操作业务 App；PCAP 只返回路径、大小和 SHA-256，不把包体塞进 MCP 上下文。

Windows 冷启动 `tidevice relay` 实测可能超过 5s 才监听；MCP 必须先给 relay 独立 20s 启动窗口，再给 `add_remote_device+enumerate` 独立 20s 握手窗口。两段共用 20s 会把正常慢启动误判成死。

`tidevice list` 空或本地 TCP 通而 Frida 握手 hang，不能单凭症状认定 AMDS 自停或 relay 僵尸。分别核服务状态、监听 owner、完整命令行、目标 UDID、PID/启动身份及设备服务；只终止本轮创建且确认失效的 relay，禁止按 `*relay 27045*` 批量清理。别的任务或归属不明的监听保持不动，必要时选择空闲本地端口。恢复 AMDS 需当前任务允许和相应权限。见 [[windows-amds-flap-zombie-relay]]。

**AMDS 反复抖 / tidevice relay 老僵尸 → 改走 SSH 本地转发隧道**（SSH-over-usbmux 实测最稳，2026-08-18 酷牛回归验证）：

```
.venv/Scripts/tidevice -u <IOS_DEVICE_UDID> relay 2222 22  # 先核目标与本地端口归属
icacls frida-mod\keys\id_ios /inheritance:r; icacls frida-mod\keys\id_ios /grant:r "$($env:USERNAME):R"   # win 私钥权限，否则 ssh 忽略
ssh -i frida-mod/keys/id_ios -p 2222 -N -L 27045:127.0.0.1:27045 root@127.0.0.1     # 隧道
# 之后 frida 连 127.0.0.1:27045 走隧道到设备（systemagentd 绑 127.0.0.1:27045）
```

只有当前证据确认设备端服务失效、已排除 relay/监听/超时问题，且任务允许中断相关会话时，才用 `ssh … "launchctl kickstart -k system/re.coreload.svc"` 恢复。历史退出码 `-9` 不能单独证明当前服务卡死。历史样本中首次握手约 10s；按上文 relay 与握手各自的 20s 窗口判断，不因过短 watchdog 反复重启。

## spawn vs attach

| 条件 | 选择 | 证据/边界 |
|---|---|---|
| 已运行且需保留设备注册/密钥状态 | 先已有日志/只读证据；确需进程内证据再最窄 attach | 优先于通用 spawn 模板；不以重启、重装或删除 Keychain 补采 |
| 证据表明必须捕获 pre-main/新连接，且当前任务允许冷启动 | **spawn**，load 后 resume | 先说明会话影响；HPACK 上下文缺失本身不授权重启 |
| 运行中目标且必须 attach | 核进程身份与挂起状态，选择最窄 attach | 切前台也须当前任务允许；超时不自动转 spawn |
| 早注入本身触发检测（小红书 9.45） | App 稳定启动后 **晚 attach（实测 ≥45s）**，只装最小原生 IMP swizzle | 早 attach 约 60–90s 被杀；GOT/系统重钩会冻结 |
| 需要 spawn gating | 本机魔改服上禁作默认路线 | `enable_spawn_gating()` 后 `resume()` 仍回 Ts，见 D-20 |

以下代码仅示范已获准且确需冷启动的分支；保留当前会话时不能直接套用：

```python
from connect import get_modded_device
d = get_modded_device()
pid = d.spawn(["com.target.app"])
s = d.attach(pid)
sc = s.create_script(open("projects/<t>/hooks/hook.js", encoding="utf-8").read())
sc.on("message", lambda m, _: print(m.get("payload", m)))
sc.load()
d.resume(pid)
```

## frida 17 + 本机魔改 API 速查

**版本钉死**：主机 `.venv` frida **17.15.3**（全局 16.5.9 → ProtocolError）↔ 设备魔改 `systemagentd`(level2)@**27045**（原版 27042 未装，禁 `--set-default` 抢）。完整阉割点/替代只看 ios-recon 阉割矩阵，本表不再抄。

| 要做 | 正确写法 | 禁止 |
|---|---|---|
| 全局符号 | `Module.getGlobalExportByName("CCCrypt")` | `Module.getExportByName(null, …)`（17 不是函数） |
| 读内存 | `ptr.readByteArray(n)` / `ptr.readUtf8String()` | `Memory.readByteArray(ptr,n)`（已移除；空 catch → 抓 0 条） |
| hook C 函数 | `Interceptor.attach(addr, {onEnter,onLeave})` | `Interceptor.replace` ObjC IMP（XHS metasec abort） |
| 混淆/CFF 中段 | 硬件断点 `Thread.setHardwareBreakpoint` + `Process.setExceptionHandler` | 对 dispatcher 邻近指令 Interceptor（unable to intercept） |
| 抓栈 | HWBP + 手读 fp 链（`Backtracer.ACCURATE` 也不要依赖） | `Thread.backtrace(ctx, Backtracer.FUZZY)`（XHS **必崩**） |
| 枚举类 | IDA / 砸壳后静态；运行时勿 `objc_copyClassList` 全量 | `ObjC.classes`（本机不存在） |
| 已知 ObjC 类/selector | `objc_getClass` + `sel_registerName` + `class_getInstanceMethod` + `method_setImplementation` | bridge 式 `ObjC.classes.X["- m"].implementation` |
| 异步 ObjC completion | 保留 App 原生 block/路径，优先 hook 入参与结果 | 把 JS `NativeCallback` 手搓 block 交给系统跨线程回调（本机可崩） |
| 版本 | 不要读 `Frida.version` | 全局 `Frida` 未定义 |

硬件断点模板见 [[ios-frida17-hwbp-api]]。每线程独立槽位；后建线程用 `attachThreadObserver`。exception handler 非本断点必须 `return false`。

## Step 1：定位入口（无 ObjC 枚举）

静态（砸壳 + IDA / `otool -Iv` / strings）定符号或 RVA，再：

```javascript
const m = Process.getModuleByName("Target"); // 或 enumerateModules 找
const addr = m.base.add(0xEA5AFBC);          // RVA
Interceptor.attach(addr, {
  onEnter(args) { send({t:"in", a0: args[0].toString()}); },
  onLeave(ret)  { send({t:"out", r: ret.toString()}); }
});
```

`frida-trace` 需自己连 27045，且本机无 ObjC `-m "*[*Sign*]"` 那套。优先 Python + 纯原生脚本。

若静态已知类和 selector，可不依赖 bridge 做定点 IMP 替换；必须保存原 IMP、限定版本/类/selector，并让未知调用回原实现。小红书 9.45 的 CronetNetworkDelegator 晚 attach 路线已验证。**不要**全量枚举类，也不要把 JS block 交给系统框架异步跨线程持有。

## Step 1.1：设备注册与风险状态的窄边界取证

从现有静态锚点选一个能区分假设的位置，完整字段谱系与拒绝归因交 `ios-protocol-signature` 的[注册谱系](../ios-protocol-signature/references/ios-device-enrollment.md)和[风控/传输判因](../ios-protocol-signature/references/ios-risk-transport.md)。

- 优先观察已运行 App 的凭证读取、自然状态更新、Challenge 回调、证明/签名包装函数与实际网络提交；仅为取证不调用 `SecItemDelete/Add` 构造新状态，不默认重启、重装、换账号或改代理。
- 仅用本仓 `.venv` Frida 17.15.3 → 设备 27045；按已定位 C 符号/原生地址或 ObjC runtime C API/IMP 观察，禁止为 App Attest 引入 ObjC bridge、objection 或 JS 手搓异步 block。
- 保留原生 completion；用 task/request id、原生对象或 block 生命周期、线程/队列与输入摘要关联 Swift/ObjC 异步链，地址复用需排除；时间相近不证明回调属于同一请求。
- 将 generateKey、attestKey、generateAssertion、DeviceCheck token 与服务端登记分别留证；记录 Challenge/clientDataHash 输入、keyID、响应分支及消费状态，不为凑样本反复证明、签名或重放一次性材料。
- 区分 Keychain 数据项、SecKey 引用及硬件密钥；私钥不可导出不等于不能签名，记录用途/算法/授权条件及已有调用结果，实际硬件保护与业务验收各需证据，不采集真实私钥或账号秘密。
- 每条日志带 UDID、bundle/build/hash、PID/启动身份、session、请求关联、时间/时钟来源、module+offset 和前后状态；原始请求响应存受控证据目录，报告只用稳定脱敏标签、摘要和路径。

缺失或未触发阶段写未知/未观察；未执行的设计不能记成采样结果。Hook 命中、证明 callback 成功或 token 可解析都不等于设备登记、账号绑定或业务成功。

## Step 2：抓加密（CommonCrypto / Security）

```javascript
function exp(name) {
  return Module.getGlobalExportByName(name);
}
Interceptor.attach(exp("CCCrypt"), {
  onEnter(a) {
    const klen = a[4].toInt32();
    send({t:"CCCrypt", op:a[0].toInt32(), alg:a[1].toInt32(),
          key: a[3].readByteArray(klen)});
  }
});
// CCHmac: alg,key,keyLen,data,dataLen
// SecItemCopyMatching / SecKeyEncrypt / SecKeyDecrypt
// 酷牛：无 bridge 时用 objc_msgSend 的 description 读返回值（见 kuniu login_trace.js）
```

历史 XHS 样本中，hook `SecItemAdd` 与直接调用的检测表现不同；这不证明调用 `SecItemDelete/Add` 对凭证和注册状态安全。仅观察时不删除/新增项目；写状态必须是当前明确允许的实验并记录影响。修改 ObjC 行为也需具体证据及任务范围，不能因换成 attach/IMP 就视为无干预。

## Step 3：抓包（本 skill 主路径，优于绕 pinning + 代理）

以下网络边界来自快看 / 懂车帝 / 携程 / 酷牛历史样本；当前目标先按前述状态规则决定能否及如何注入：

1. 先核实际网络栈和已有观察缺口；已运行目标优先最窄 attach，只有确需且允许冷启动才 spawn。反检测干预不是抓包前置，须先有已证检测点与当前授权。
2. 只 hook 已识别实际承载流量的系统 `libboringssl.dylib` 或 App 内 TLS 库；扩点需解释新增覆盖，不默认全部同时装。
3. 目标模块尚未加载时做有界延迟补钩（如 `setInterval` 3s × 40），并记录模块身份。
4. `SSL_write` onEnter / `SSL_read` onLeave 用 `ptr.readByteArray`；`send(meta, ArrayBuffer)` 落盘。
5. 离线解 h2（HPACK）+ HTTP/1.1。模板：`projects/kuniu/hooks/ssl_capture.js` + `scripts/parse_flows.py`。
6. QUIC 优先另选已定位的明文提交点；历史 XHS 样本阻断 UDP 不会回落。修改 `enableQuic` 会改变传输变量，只能作为当前允许且有恢复条件的独立实验。

QUIC/h3 仍看不到业务明文时，不要在 `SSL_write` 上空等：沿 `write(UDP)` 回溯到 C++ 请求对象/发送缓冲，在加密前的协议分发点定点 hook。RVA 必须绑定 App build；小红书 9.45 的偏移只可作该版本地标，升级后重新定位。

抓 0 条先检查脚本/API 错误、当前进程与模块、网络栈及观察覆盖；再结合具体日志区分目标检测、挂起或其他失败。缺流量不证明被掐网，热进程缺 HPACK 上下文不自动转冷启动。见 [[frida-capture-fail-suspect-antidetect]] [[ios-boringssl-h2-capture-method]]。

**nw TCP 链路层（2026-08-30 心遇实测，D-17）**：Network.framework 的 TCP **完全不走**可钩的 `socket/connect(±$NOCANCEL)/connectx/setsockopt/getsockopt(SO_ERROR)`，boringssl 是内存 BIO（`SSL_get_fd` 恒 -1）。要 TCP 目的地就钩 `nw_connection_start` + `nw_connection_copy_endpoint` + `nw_endpoint_get_hostname/get_port`（逻辑 host:port 一次拿全）。UDP/QUIC（App 自建 BSD socket）仍用 sendto/recvfrom/connect 正常钩。模板：`projects/moyi/hooks/fullchain_capture.js`。

## Step 4：SSL Pinning 绕过（代理场景才需要）

```
仅当必须走 HTTP 代理时（多数目标用 Step 3 hook 明文，不必绕 pinning）：
 1. 纯原生 hook `SecTrustEvaluateWithError`（符号，不依赖 ObjC）
 2. 静态定位 TrustKit / AFNetworking / Alamofire 的 IMP 再 attach
 3. SSL Kill Switch 3（OTA 后可能未装 → `ios_apt_install`）
objection：**本机不可用**（见 ios-recon 阉割矩阵），不要当步骤 1。
```

## Step 5：反-Frida / 越狱检测（先证实再选择干预）

抓包或签名采集失败先按状态与证据规则区分工具、脚本、覆盖和目标检测。以下只是在具体检测点已被证实、当前任务允许修改时的候选手段，不是每次采样必须安装的前置。

检测面（懂车帝 metasec / 小红书 / 数美）：

| 类 | 特征 | 对抗 |
|---|---|---|
| 线程名 | gum-js-loop / gmain / frida / pool-spawner | 先确认当前检测实际读取并使用该结果，再评估是否需要局部干预 |
| 路径 | frida-server、/var/jb、Cydia… | hook stat/open/access |
| 反调试 | sysctl P_TRACED、ptrace | hook sysctl 清位 |
| 代码完整性 | Interceptor.replace、热补丁邻近 dispatcher | 改 attach / HWBP |
| 栈特征 | FUZZY backtrace | 禁止；改手读 fp |
| 枚举 | objc_copyClassList 全量 | 禁止 |
| 累计 | 重复 spawn 可触发初始化和业务请求 | 没有通用安全次数；按当前状态与请求预算执行，不循环 spawn 试错 |

level2 在 2026-08-06 的山姆/懂车帝样本曾通过相关路径，但不证明当前目标无需检查或必定存在同类检测。只有已允许冷启动且具体检测要求启动前干预时，才在挂起态设置该最小干预再 resume；新失败仍应保留 relay、脚本和目标检测等竞争原因。

越狱路径欺骗（纯原生 hook `stat`/`access`/`NSFileManager` 需先静态拿到 IMP）：

```
常见路径: /Applications/Cydia.app /usr/sbin/frida-server /bin/bash /etc/apt /var/jb
酷牛历史 stee_isJailbreak_1..7 + sysctl 样本：level2 实测未阻断 hook；新版本不默认清 P_TRACED，先核实际消费与影响
```

## Step 6：CFF / Medusa 类 VM（Interceptor 失败时）

懂车帝 `eabf0a0`：内联 hook 报 unable to intercept → **HWBP** 抓入口/离开全态；unicorn 离线 replay 必须：**代码页用文件，__DATA 用运行期已 rebase 快照**；全闭包 BFS 会杀 App（~5200 页）→ **on-demand 分页**。禁 hook VM dispatcher 热点。见 [[dongchedi-medusa-ct-vm]]。

## objection / cycript / LLDB

状态与替代只查 ios-recon 阉割矩阵。本节不列版本、不教安装 objection。日常：纯原生脚本 + `ios_frida`。cycript/debugserver 用到再 apt。

## 交接

- 抓到密钥/参数但要还原完整算法 → **ios-protocol-signature**。
- 要静态确认 hook 点 → IDA（串行 + 地标）。

## 常见坑（失败模式编码 D-xx）

> 每条格式：**编码 现象** → 原因/规则。**成本**=不知道这条会白费多少。
- **D-01 ObjC is not defined** → 本机魔改无 bridge，不是脚本写错。改纯原生。**成本**：frida-compile 半天仍 false。
- **D-02 attach 后台 25s 超时** → 先核进程/挂起/连接证据；保留状态时不改 spawn。切前台或冷启动需当前范围允许且确有必要。**成本**：把超时处理成重启，破坏会话对照。
- **D-03 hook Swift 找不到** → 无 @objc，走 exports / IDA 地址。**成本**：在 ObjC.classes 里空转（本机更是没有这个对象）。
- **D-04 SSL 绕了还抓不到** → 静态 BoringSSL / QUIC / 漏系统库。**成本**：把 pinning 方案重试一遍。
- **D-05 注入秒退 / 卡死没网** → 仅为症状；先核 API/地址/对象生命周期、watchdog、日志与工具链自证。目标检测有可复现证据后才进 Step 5，不自动 bypass 或重装。**成本**：错误归因后叠加干预，掩盖原始故障。
- **D-06 去装/升 objection** → 矩阵已弃用（无 ObjC）。改纯脚本。**成本**：卡环境半天。
- **D-07 非越狱 TrollStore attach InvalidArgumentError** → 内核硬限制，重签 get-task-allow 或完整越狱。**成本**：重签 tipa 来回数小时（已踩）。
- **D-08 Memory.readByteArray 不是函数** → 改 `ptr.readByteArray`；catch 必须 send 错误。**成本**：计数狂涨却 0 条，误判完整性还原。
- **D-09 Thread.backtrace(FUZZY)** → XHS 必崩 / token 不生成。改 HWBP+fp 链。**成本**：整条 token 来源实验作废（曾推出「非本地生成」假结论）。
- **D-10 Interceptor.attach 混淆中段失败** → HWBP。禁 hook dispatcher 热点。**成本**：script destroyed / abort。
- **D-11 --set-default 抢 27042** → 内核 panic。魔改永远旁挂 27045。**成本**：掉越狱。
- **D-12 hook NSURLSession / 加载 objc-bridge** → XHS 网络静默。只 hook SSL。**成本**：以为没流量。
- **D-13 spawn 当时模块还没有** → 延迟补钩。**成本**：W/R=0 误判网络栈。
- **D-14 高频 spawn** → 可能反复初始化并改变注册/检测状态；停止循环启动，保存实际请求与错误证据，不能仅凭启动次数下风控结论。**成本**：污染会话和尝试预算。
- **D-15 27045 TCP 通但 frida 握手永久 hang** → 核当前监听、relay、超时与设备服务证据；历史退出 -9 不足以证明当前卡死。证实设备服务失效且允许中断相关会话后才精确恢复，不自动重装或重启。**成本**：把连接症状处理成不必要的会话中断。
- **D-16 连通探测 watchdog 太短误判死** → (重)启后首次 `add_remote_device+enumerate` 约 10s。watchdog <15s 会在成功前一两秒超时。设 ≥15s。**成本**：把正常但慢的 server 判死，去瞎修（实测 11.8s 才出 procs）。
- **D-17 Network.framework TCP 在 fd 层全空** → 系统 `nw_connection_*` 可能绕过可钩的 `socket/connect/connectx`，BoringSSL 还是内存 BIO（`SSL_get_fd=-1`）。钩 `nw_connection_start` + `nw_connection_copy_endpoint` + `nw_endpoint_get_hostname/get_port`。**成本**：在 fd 层误判“无 TCP/无流量”，整条注册链漏掉。
- **D-18 `nw_connection_create` 把 a1 当 endpoint** → a0 才是 endpoint，a1 是 parameters；对 a1 调 hostname 会 `doesNotRecognizeSelector`，重钩可触发 `0x8BADF00D` 看门狗。**成本**：App 启动 19s 后被系统杀，误判反 Frida。
- **D-19 用 JS NativeCallback 手搓异步 ObjC block** → 本机魔改 agent 在系统框架跨线程回调时可页访问崩溃；保留 App 原生 completion，改 hook 入参/回参或走同步 IMP。**成本**：App Attest/系统 XPC 链路随机崩，难复现。
- **D-20 依赖 spawn gating 恢复进程** → 本机魔改服曾在 `resume()` 后仍回 Ts；先核当前进程状态，不默认再 spawn。只有任务允许冷启动且状态可重建时才选择普通 spawn；需保留现有状态则停留在证据与最窄 attach 方案。**成本**：把 gating 假暂停当业务卡死，重复污染设备状态。
- **D-21 误把“无 ObjC bridge”写成“不能 swizzle”** → 已知类/selector 可走 runtime C API 定点换 IMP；禁的是 `ObjC.classes`/objection。**成本**：放弃可用的低噪声请求层钩子，退到高风险 GOT/传输层重钩。
