---
name: protocol-signature-reverser
description: Android App 协议、设备注册谱系、签名加密与风控判因专项。用于追踪安装标识/密钥/证明/设备令牌/账号会话的生命周期，区分传输、算法、环境与业务拒绝，交付可验证的离线实现或明示依赖的方案。触发词：Android协议逆向、设备注册、设备绑定、一机一密、Play Integrity、Key Attestation、Android风控、签名逆向、x-mini、shield、mtgsig、MTOP、Gorgon、Argus、unidbg、Unicorn、HMAC、设备令牌、会话绑定、fp_stack。
---

> ⚠️ **本机环境适配（20260920 维护注）**：本机为 macOS，`frida-orchestrator-mcp`(80工具)/`reverse-index-mcp`/`algo-lab-mcp` 已装（vendor/android_mcp，20260922）。设备操作也常用 `adb`（mac 路径，非 `android_mcp\toolchain\...adb.exe`——该 Windows 路径段按 `brew install android-platform-tools` 的 adb 替代）+ 项目 venv frida；静态索引用 `jadx` MCP（jadx-gui）+ grep 替代 reverse-index；算法对拍脚本自行落盘运行替代 algo-lab。serial 用显式参数或 `ANDROID_SERIAL`。

# Protocol Signature Reverser

## 任务边界

本 Skill 是 Android 协议/签名的判因与三级交付负责人，不预设结果一定是纯算。

- APK/API/网络栈侦察 → `android-recon`
- 脱壳取得真实 DEX/SO 段 → `android-unpack`
- Frida/SSL/native trace/RPC 采样 → `android-dynamic`
- 本 Skill 负责：字段与设备注册全链谱系、竞争假设、算法/生命周期/传输/风控分层判因、unidbg/Unicorn/frozen 实现、字节与业务验收。
- 不引入 iOS/IPA/Mach-O/越狱、Web 或通用 CTF 协议流程。

仓库内样本、两台真机（Pixel 6 `<ANDROID_SERIAL_P6>` / Pixel 4 XL `<ANDROID_SERIAL_P4XL>`）和已指定测试账号默认属于用户已授权的本地 Android 环境，不重复询问授权；目标、账号、设备或外部系统越出仓库约定时才重新确认。

## 开工门

攻坚前必须有：

1. 一句话目标能力；
2. 最终判官（字节 oracle、服务端语义或账号可见效果）；
3. 交付形态；
4. 可证伪成功标准；
5. 时间/成本/账号止损线；
6. 真实抓包和至少一组 input→output；没有样本先采集。

同时固定 App/APK/SO hash、ABI、设备 serial、账号/session、IP/代理、请求字节与时间。验证期单设备单账号；同一请求同字节总计最多 3 次（含首次及已有尝试），出现漂移更早停止；同接口同错误连续 3 次也停止同类请求并归因。预算不因换脚本、换工具或换操作者重置。

仅做本地静态梳理/取证设计时，用现有样本完成可复核部分，缺证写明；上述开工门不授权为补样本自行登录、注册、重放、清数据或重置设备。

## 三级交付

| 形态 | 条件 | 可以怎么说 |
|---|---|---|
| 解析型 | 字段谱系零空洞，算法自包含，最低 3 组任意输入与 oracle 一致，动态字段单变量实验落定 | “已还原/离线纯算” |
| 绕过型 | 利用已验证的服务端/客户端条件，不等于算法还原 | 明示条件、脆弱性和版本 |
| 止损型 | 依赖真机、原 App、RPC、在线签名或时效 token | 明示 oracle、未解字段、生命周期 |

`≥3` 是最低交付门；`100+` 只用于成熟确定性实现的增强回归，不得反过来用数量掩盖字段谱系空洞。RSA-PKCS1 随机填充等非确定性输出不能要求密文字节相同，应验证明文、key 来源、结构/长度和解密/验签结果。

## 参数谱系

每个 header/query/body/嵌套字段一行：

| 字段 | 来源 | 生成算法 | 生命周期/绑定 | 单变量验证 |
|---|---|---|---|---|
| `token` | 服务端下发/接口 | 透传 | session/TTL | 过期与刷新对照 |
| `x-sign` | 本地生成 | 精确输入与算法 | 单次/序列态 | 改一个输入后 oracle 对拍 |
| `deviceId` | 待定：本地生成或服务端下发 | 查生成/响应与持久化调用链 | 安装/设备记录等，待证 | 优先已有生命周期样本对照 |

来源只允许：静态常量、本地生成、服务端下发、由已知字段派生。抓包值若直接复用，标为“重放值+时效”；调用真机/原 App 取值，标为 oracle。字段分类先做纯算、设备态、透传/会话态，避免把上游下发值当算法硬撕。

## 设备注册与风控的按需入口

- 首启入库、设备绑定、设备 token、密钥注册或证明 → 读 [注册谱系](references/android-device-enrollment.md)，把来源/生成与身份类型分列，连通生产者、持久化、消费者和生命周期；不把安装、设备、密钥、账号、会话并成一个 ID。
- 已有失败、挑战、无业务效果，或传输与签名难以区分 → 读 [风控与传输判因](references/android-risk-transport.md)，先判断请求到达哪一层，再选最小区分实验；状态缺失和未评估不等于恶意。
- 交付设备注册梳理 → 按需复制 [谱系与实验报告模板](assets/device-enrollment-audit.md) 到目标项目 `docs/`，只填有证据的节点，未观察阶段标未知/有依据的不适用，不强制补齐假想流程。
- 维护这些能力时使用 [离线回归场景](references/enrollment-risk-cases.json)；用实际回答和产物评审，不按关键词出现次数计分。

官方文档只定义平台能力；SDK 名、API 字符串、官网宣传不证明当前 App 真调用或服务端真校验。硬件私钥、平台证明和上游令牌的依赖必须显形，不提前安排在线兜底，也不因出现这些名称立即结束调查。

## 工作流

### 1. 先定位缺口层

按成本选择能闭合当前缺口的最短路径，不做固定流水线：

- 证据表明请求未到业务网关 → 查 DNS/TLS/ALPN/QUIC/私有隧道；仅凭错误码或抓包缺失不能确定到达层；
- verbatim 原包可用，自建重签失败 → 算法输入、生命周期或序列态；
- 改 body/path 后字段不变 → 候选设备令牌，不先当每请求 HMAC；
- 原版 App 同环境也失败 → 先排环境/账号/IP/服务端；
- unidbg 能返回但与已知向量不一致 → 模拟执行不是 oracle。

“被风控”“服务器绑会话”“随机生成”“纯算完成”等终止性结论必须满足 `.zcode/memory/reverse_principles.md` 的证据牌照。

### 2. 六路证据采集（统一编号）

六路是可选证据源，不要求机械全跑；多路能验证同一缺口时可并行。

1. **SO triage**：hash/ABI/imports/exports/字符串/标准密码常量/壳与熵；工具用 rabin2/strings/llvm-readelf。
2. **IDA/static**：Java→JNI 边界、request builder、数据流、反汇编/伪代码/调用图；Ghidra GUI/headless 只作二线，GhidraMCP 当前仅 `documented`。
3. **Capture**：原版请求的 raw method/path/query/header/body、时序、前置接口和响应；二进制先保留原字节，再做 Protobuf wire 侦察。
4. **Frida/runtime**：最窄边界的入参/出参/调用栈/RPC oracle；由 `android-dynamic` 选择注入方式。
5. **Emulator**：unidbg/Unicorn/frozen blob/算子提升；先用已知向量证明执行正确，再当 oracle。
6. **References**：开源实现、论文、版本差异；记录来源/许可证，只把当前样本能验证的规则纳入结论。

私有二进制 Capture 先按方向、连接和时序重组字节流，再用多样本验证 magic/length/端序/TLV/sequence/checksum 与状态机。TCP segment、PSH 或一次 `recv()` 都不是消息边界；高熵也不是“已加密”的证据，须继续排除压缩、编码、分块和混合结构。

跨版本迁移先固定新旧 SO hash/ABI，以 export、字符串引用、常量和调用关系建立候选锚点。BinDiff/LLM 映射只能生成候选；关键函数必须用反汇编结构或同输入运行向量复核后才能沿用。

自建 MCP 主路径：

- `reverse-index-mcp`：`find_endpoint`、`find_symbol`、`list_suspicious_sign_methods`；
- `algo-lab-mcp`：样本规范化、编码/Protobuf wire、hash/HMAC 候选、复现与验证；
- `frida-orchestrator-mcp`：由 dynamic 提供 RPC oracle。

### 3. 竞争假设与区分实验

每轮最多保留 2–3 个能被下一实验区分的假设，例如：

- 标准算法及精确 key/IV/padding/canonicalization；
- 标准算法变体或分层序列化；
- 自定义变换/白盒/frozen 状态；
- 设备令牌/服务器透传；
- 会话/请求序列绑定；
- 传输指纹或私有协议。

优先实验：

1. 先比对已有原始字节、时序、响应和本地状态，保留代理漏包/QUIC/后台连接等证据盲区；
2. 如需新采样，选择已授权的原版同环境对照；一次性 challenge/token 不为对拍重复消费；
3. 对已捕获的前置接口、埋点和业务请求做全量 diff，字段未闭合不宣称“无缺块”；
4. 按当前缺口选择一个 method/path/query/body/header/time/device/session 变量；优先本地实验；
5. 线上实验须在当前范围和剩余预算内；重放实验还须证明材料可重放，一次性流程只能使用已有样本或已授权的新鲜绑定材料。改变设备/IP/账号或清数据不作为自动下一步。

连续尝试 10 个 HMAC/hash 拼接候选仍无证据提升，停止爆破，转静态/动态算子提取。假设不是交付物，每轮必须产出证据锚点或下一个区分实验。

### 4. 策略选择

| 证据 | 策略 | 验收 |
|---|---|---|
| 标准常量、输入链清楚 | 标准库重写 | canonical bytes、key/IV/padding、最低 3 组 oracle |
| 算术展开/自定义 GF | IDA/trace 提取 op list | 非样例输入逐字节一致 |
| 固定执行路径依赖大 SO 状态 | frozen blob/快照 | blob 来源、重定位、版本边界、oracle 对拍 |
| BCF/FLA/MBA、间接 `BR/BLR` 或 VM/时序反模拟 | 先分类缺口，再做局部传播/trace/快照与 Unicorn/unidbg | 反汇编边界、已知向量，再任意输入 |
| 随机混合加密 | hook 原语输入并重建结构 | 可解密/验签、字段谱系与长度 |
| 传输指纹/私有 QUIC | `projects/fp_stack/` 复刻真实档案 | 已有成功样本或已授权的新鲜请求对照；旧凭证重放失败不直接归因传输 |
| 已证实物理持有/生命周期绑定 | 止损决议后 oracle/在线兜底 | 明示依赖、TTL、并发/恢复与未解字段 |

在线兜底不能预先写进计划。只有列出已穷尽假设、完成原版/传输/字段 diff，并由证据证明纯离线缺口依赖物理状态后，才做止损决议。

### 5. unidbg/Unicorn 执行正确性

在把模拟器当 oracle 前：

- 固定目标 SO/hash/ABI、loader、JDK/NDK/系统库版本；
- 证明 JNI_OnLoad/RegisterNatives 与目标调用链真实执行；
- 标准 AES/hash 已知答案测试只作原语/工具链自检，不能据此把目标模拟执行当 oracle；
- 目标调用须另与同版本原 App/真机的已有输入输出向量核对；确定性输出逐字节比较，合法随机输出按其明文、参数和解密/验签结果验证。缺少目标对照时标为“未验证模拟结果”；
- 检查时序源、系统属性、线程、文件、随机数、网络/session 与重定位数据；
- 发现重复 keystream、全零状态、固定错误分支或只返回预期长度时，标记 invalid oracle。

补环境可以脱离 App，不自动等于脱离设备、账号或网络。对外说明初始化/session 依赖。

### 6. 验证与交付

解析型至少保存：

- 3 组非样例 input→output（成熟实现追加 100+ 随机回归）；
- 字段谱系与单变量实验；
- 真机/original-app/oracle 版本与 hash；
- 自包含代码、依赖、README、命令；
- 开工时选定判官的端到端证据：完整协议能力验服务端语义或账号可见效果；纯算法离线实现验目标原版向量或适用的解密/验签结果，不强制发送在线业务请求，并注明业务效果未验证；
- 工作条件、失效表现和字段粒度未解清单。

HTTP 200、`code=0`、长度正确、JSON/Protobuf 可解析或 framing 正确只算中间证据。最终判官必须是服务端语义、账号可见效果、解密/验签成功或与真实 oracle 的字节级一致。

## 失败模式速查

| 触发 | 含义 | 下一步 |
|---|---|---|
| 输出像 HMAC，10 个候选全败 | 算法/key/canonicalization 假设无进展 | 静态常量 + runtime 边界，不再爆破 |
| 搜不到标准常量 | 可能动态生成、混淆或展开 | trace/算子提取，不能直接排除算法 |
| verbatim 成功、重签失败 | 输入/会话/序列态候选 | 全量 diff + 单变量，未满足证据牌照不下结论 |
| 设备间不同、请求间稳定 | 设备态或服务器关联候选 | 查生产者/存储/消费者，先比对已有生命周期样本 |
| unidbg “跑通”但向量错 | 执行错误 | 补环境或废弃 oracle |
| 裸 HTTP 失败、原 App 过 | 传输、前置状态或请求字段候选 | 先到达层与完整流量 diff，再按证据查 CH/ALPN/QUIC |
| RSA 密文每次不同 | 随机填充正常候选 | 验明文、结构、解密，不追密文字节相等 |
| 只能 RPC 产值 | 止损型 | 明示设备/session/TTL，不称纯算 |

## 不要做

1. 不从 TLS 帧等最底层开始，除非上层边界已证明不可达。
2. 不把抓包长 blob、设备 token 或服务端透传字段默认当本地签名算法。
3. 不跨设备复用密钥/令牌，不批量试无效签名，不在单 IP 碰多号。
4. 不把 unidbg 返回值、Frida RPC、verbatim replay 或 HTTP 200包装成纯算。
5. 不为追求“字节一致”错误处理带随机填充的合法密码方案。
6. 不在谱系有空洞、动态字段未做单变量实验或没有真实判官时报告完成。
