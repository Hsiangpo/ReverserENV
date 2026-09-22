---
name: ios-protocol-signature
description: iOS 设备注册谱系、签名加密与风控分层判因。追踪 IDFV、Keychain、密钥、App Attest/DeviceCheck、设备凭证及账号会话，区分传输、平台证明与业务结果；按证据选择 CommonCrypto/白盒、原生 Frida 或 arm64 unicorn 验证，诚实标明外部依赖。触发词：iOS设备注册、设备绑定、一机一密、App Attest、DeviceCheck、Secure Enclave、iOS风控、签名逆向、CommonCrypto、CCCrypt、CCHmac、白盒、frida RPC、unicorn、keychain、字节级验证。
---

> ⚠️ **本机环境适配（20260920 维护注）**：本机为 macOS，`ios-device` MCP 老师仍未分发（0818 包只有 frida-mod 设备端与工具）；ida-pro 需付费未装。设备连接用 `frida-agent` MCP / 项目 venv 的 frida / `pymobiledevice3`；SSH 直连设备用 mac 原生工具；提头优先 mac 原生 `class-dump` / `otool`（jtool2 如未装则 brew 安装或以 class-dump 替代）。下文提及 ios-device 工具（`ios_info`/`ios_ssh` 等）的段落按此替代执行。

# iOS Protocol Signature —— 签名/协议算法还原

## 角色定位

把 iOS App 请求里的加密/签名参数还原成**诚实分型、可验证**的生成链。优先产出纯离线 Python；若正式止损后仍含设备/在线依赖，交付必须明确标成混合或 oracle 形态，不能伪装成纯协议。

> 📌 **先套全局心法**（`.claude/memory/reverse-signature-principles.md` + `reverse-principles-v2.md`）：每个动态参数先区分① 客户端计算、② 设备/安装状态、③ 上游下发值；硬件密钥与平台证明另登记依赖，不能因属于②就假定可复制。上游下发也不自动证明客户端原样透传。开工前定死「什么叫找到」；交付要有字段谱系，禁止把没找到的写成已还原。

## 开工检查（攻坚任务，缺一禁开工）

- [ ] 目标能力一句话（可验证，如「登记的设备记录被指定下游识别」；不能只写 HTTP/code 成功）
- [ ] 判官：服务端语义 / 与真机 oracle 逐字节 / 下游接口
- [ ] 交付形态：纯算脚本 / 混合 oracle / 一次性取证 / 持续批量
- [ ] “找到”的可证伪标准：哪个实验结果等于成功，哪个只证明解析/收包
- [ ] 样本在手：真实抓包 + input→output 对。没有 → 先采集（ios-recon/dynamic），**禁止空手逆向**
- [ ] 止损：时间 / 烧号红线（高频无效签名会软封整机）
- [ ] 字段先分类 ①②③，再开撕

仅本地梳理/评审时用现有 IPA、日志和代码完成可复核部分，缺证写未知与最小实验；开工检查不授权为补样本自行注册、登录、重放、删 Keychain 或重装。

## 设备注册与风控的按需入口

- 首启登记、设备绑定、密钥或凭证生命周期 → 读 [iOS 注册谱系](references/ios-device-enrollment.md)，区分安装、Vendor 标识、Keychain 项、密钥、公钥登记、平台证明、服务端设备、账号/会话；将生产者→存储→消费者连成有证据的状态图。
- 失败/挑战/无业务效果、网络与签名难区分 → 读 [iOS 风控与传输判因](references/ios-risk-transport.md)，先确认到达层与观察盲区，再做最小区分实验。
- 交付注册分析 → 使用 [设备注册审计模板](assets/device-enrollment-audit.md)，只填已观察节点和有依据的不适用；未测 TTL、绑定、服务端验证明确保留未知。
- 技能维护用 `test-prompts.json` 与 [边界回归场景](references/enrollment-risk-cases.json) 作离线情景评审；文本检查不替代实际业务验收。

参考文档负责通用决策；下方历史 App 案例仅在版本与原始证据匹配时复用。官方 API/SDK 字符串只说明候选能力，不能代替当前调用、服务端验收或用户行为证据。

## 本仓 iOS 算法边界

- 代码主体是 ObjC/Swift、CommonCrypto 或 App 自带 dylib；部分 SDK 静态链接 OpenSSL（如同盾 1.0.2）。
- 离线执行只在依赖可控时用 unicorn 跑 arm64 裸函数；系统依赖缺证时先查已有静态/运行材料，确需新样本且当前任务允许才转原生 hook 取证。取证 oracle 与交付运行依赖分开，后者仍须正式止损决议。
- 本机魔改 Frida 无 ObjC bridge：主动验证优先 hook C/导出符号，或静态还原后做字节级对拍。

## 决策树

```
定位到签名/加密函数后:
   │
   ├─ 是标准算法(CCHmac/AES/MD5/SHA/RSA)?
   │     → 先查已有 key/iv/输入证据；确需且允许才定点 hook → Python 复现 → 按确定性/随机化方案验收
   │
   ├─ 是自定义纯算 / CFF-VM（无硬件墙）?
   │     → 抠函数 + unicorn；Interceptor 失败改 HWBP 抓态
   │     → 超大 OLLVM：Hex-Rays/d810 会 too big → FlowChart CFG，不是墙
   │
   ├─ 依赖设备/安装状态(②)? → 分清 IDFV 作用域、Keychain 状态、硬件密钥与平台证明，再查生命周期
   │
   ├─ 依赖服务器下发值(③ token/nonce/salt/shield)?
   │     → 追签发/缓存/变换/消费者与时效；需要新样本时才在当前授权范围内采集
   │
   ├─ 字段都齐但仍拒绝?
   │     → 先核 body 容器形态/顺序/编码/Content-Type/HTTP 版本与前置链，禁止直接归因签名
   │
   └─ 「离线失败」其实是传输通道指纹?
         → 将静态 OpenSSL / 私有头作为样本候选；与请求字段、前置状态并列核对，不凭失败先定传输原因
```

## ①②③ 分类的分发边界

原工作区此处是含真实设备、会话与目标进度的历史个案表，未随便携包分发。字段分类方法、注册谱系、风控/传输参考和审计模板仍完整保留。新目标必须取得自己的输入输出与消费证据；不能继承旧项目的通过率或业务结论。

## Step 1：定位签名入口

```
1. 从已有抓包与调用链定位签名候选；确需新样本时按当前范围交 ios-dynamic 选最窄观察点
2. 静态：IDA / strings / 类名 *sign* *hmac* *crypt*；注意 ida-pro-mcp 多实例漂移
3. 动态：纯原生 Interceptor 对拍输出 == 抓包值
   本机无 ObjC RPC 模板时，用 hook onLeave 当 oracle，不要写 ObjC.classes.SignManager
```

## Step 2：真机当 oracle（受 ObjC 限制）

```javascript
// 可行：hook 已定位的 C/导出符号，send 入参+出参
// 不可行：rpc.exports 里调 ObjC.classes.xxx（本机 ObjC 不存在）
rpc.exports = {
  ping: function() { return "pong"; }
};
```

能静态还原的不要长期挂真机 oracle（风控 + 设备绑定）。懂车帝 follow 写路径曾用设备 `getFeatureHash` 混合通，纯主机 CT 仍 OPEN——混合要在谱系里标明 oracle 依赖，禁止宣称纯协议。

## Step 3：unicorn 离线（CFF-VM / 白盒）

```
已验证的工程坑（懂车帝 CT replay；**不等于 CT 已升①**）：
- 代码页永远用文件（frida module.size 只到 __TEXT，别把 __DATA 当堆 overlay 覆盖代码）
- __DATA 必须是运行期已 rebase 的值，否则指针图全废
- 全对象图 BFS 会杀 App（~5200 页）→ 断点处只抓 per-request，其余 on-demand rpc readpage
- libSystem 要 shim（malloc/objc_msgSend 返 nil/锁 noop）；别 let-run 全部 objc
- 验证用「内容交集」不是地址；**高熵 100% 匹配可能是 P-无关密钥调度缓冲**（clock-diff 恒 100% = 假密文）
- 超大 OLLVM：d810 阉割/硬限制见 ios-recon 矩阵 + [[d810-ollvm-unflattening-recipe]]；不要在本节再抄激活步骤
- e2e 未过（懂车帝 follow 4001）前禁止把 VM replay 标成 ①
```

依赖系统库过多时，先定位具体缺失输入与语义；需要且允许新运行证据时再使用最窄 hook 取证，不能直接把交付改成长期 oracle。VMP/重混淆本身不证明不可还原；按用户选定目标、现有证据与止损条件继续。

## Step 4：取密钥 / 伪造纪律

```
- 运行时 key：CCCrypt/CCHmac hook
- keychain：先已有材料或限定项目的只读查询；SecItemAdd/Delete 会改变凭证状态，不是采样默认动作。动态观察需按当前范围和具体检测证据选择
- 硬编码盐/S盒：砸壳后 strings / IDA
- 指纹伪造：每台独立 env（机型↔芯片配对）；禁复用真机模板（聚类会连累真机）
- 测试禁用真机指纹（山姆）
- 共享 XXID / 共享 box 头 = 批量被聚类的病根
```

## Step 5：字节级复现 + 谱系交付

```python
for sample in samples:  # ≥3 组非样例
    assert my_offline_sign(sample.input) == sample.real
```

以上逐字节要求用于固定完整输入后的确定性运算。AEAD 在 key、nonce、明文、AAD 均固定时仍应逐字节对拍，不能因 nonce 原本随机生成就免除密码核心验证；不同 nonce/随机填充的独立运行不要求相同密文。随机化方案要核生成来源、精确参数和解密/验签关系，并以至少三组独立输入验证可复现部分。状态型 assertion 单列硬件/服务依赖；注册取证不为凑三组重复消费 Challenge/证明或破坏现有状态。纯本地算法按该算法的离线判官验收，不能强制追加无关线上业务。

交付必须有**参数谱系表**（每字段一行：来源 / 算法 / 生命周期 / 单变量验证）。来源四选一：静态常量 / 本地生成 / 服务端下发 / 派生。谱系还必须覆盖请求方法、path/query 规范化、body **容器类型与顺序**（dict / KV 列表 / form / protobuf）、字符编码、压缩层、Content-Type 与传输版本；字段值正确但序列化形态错误仍是缺口。硬编码抓包值必须标「重放+时效」。脚本内部若向真机取值 → 标明 oracle，禁止写「纯协议」。

**禁词牌照**（无证据不准结案）：
- 「被风控了」= 原版同环境也挂 +（维度轮换或冷却自愈）
- 「已还原」= 声明范围内谱系零空洞 + ≥3 组任意输入验证（确定性逐字节，随机化按上文等价关系）+ 动态字段单变量落定；本地核心通过不等于含外部依赖的整条注册纯算
- 「随机生成」= 有随机源/PRNG 及其输入、调用与消费关系证据；≥3 组同显式输入的不同输出只提示随机或隐藏状态，不能排除时间/计数器就结案（const_hex93 的 arc4random 锚点是正例）

## 止损线 & 风控红线

- 止损决议前，计划中不得出现“先用在线兜底”；决议必须附已穷尽假设与区分性实验。
- 硬件证明/SE 签名 API 命中只是依赖候选；须证实当前接口消费与请求绑定，并列已穷尽假设，才能作字段级止损决议。不可导出不等于不能调用，也不等于可以移植私钥到 Python。
- **通道指纹 ≠ 算法墙**：同盾离线失败根因可以是 ClientHello/前置头，不是 box 算错。
- **星座/双闸**：历史样本的 box、设备凭证与服务端关联应分阶段验收；不能把该模型套所有 App。先做既有材料差分，不自动换号/IP 或等待后宣称冷却自愈。
- **profile `000` 是「接受上报」不是「过闸」**。
- **e2e 不批量发送无效签名**。同一请求同字节最多总计3次（含首次和已有尝试）；漂移更早停，预算不随换脚本/工具重置。第3次同类失败停止同类线上实验，先离线差分，再设计当前范围内的原版对照；一次性流程的旧材料不可重放时，用已有样本或已授权的新鲜绑定材料。
- **白盒/CFF ≠ 止损**。随机字段按证据还原生成规则和消费关系，不能因样本值不同就宣称不可还原，也不要求复现某次随机字节。

## 已完成签名矩阵（摘要）

| App | 主体 | 状态 |
|---|---|---|
| 快看 | app_secret_sign | ① 完全还原 |
| 小红书 | x-mini / shield / d / App Attest | x-mini 全链+d ①；shield ③；App Attest=硬件/oracle，端点依赖逐接口证明 |
| 懂车帝 | Gorgon+Helios+Medusa | 首页纯主机；**CT 不声称①**（e2e 4001）；写路径混合 |
| 山姆 | st + QIMEI + 同盾 + Turing | 三件套可本地；commit 另有星座/集群闸 |
| 携程 | XPS | 首页软校验 e2e |
| 酷牛 | 登录 RSA + 直播 URL | 登录/转播纯协议 |
| 心遇 | CSJM 请求/响应 | CC20P1305+zstd 纯算；主 API e2e |
| nice | nice-sign-v1 + nuid | 签名① 18/18；nuid ③；首页 e2e，写接口未测 |

## 交接

- 需要动态抓 key / 绕检测拿样本 → **ios-dynamic**。
- 需要砸壳静态定位 → **ios-unpack** → **ios-recon**。

## 常见坑（失败模式编码 S-xx）

> 每条格式：**编码 现象** → 原因/规则。**成本**=不知道这条会白费多少。
- **S-01 把 ③ 当算法硬撕** → 先分类。**成本**：数天到永远（shield）。
- **S-02 寻找不存在的整机级离线模拟器** → 本仓只有符号 hook/RPC oracle 与 arm64 unicorn 裸函数两条路。**成本**：调研空转半天。
- **S-03 unicorn 跑到系统库就崩** → 依赖多则退 oracle；或按 CT 经验 shim。**成本**：补桩 1 天。
- **S-04 CCHmac 参数读错** → alg,key,keyLen,data,dataLen。**成本**：当算法错重撕。
- **S-05 算法对但签名不对** → 漏 ③ / 编码顺序；更危险的是高频 e2e 软封设备。**成本**：封号/封机。
- **S-06 反检测导致假「非本地」** → hook 把流程掐死（SETTOK=0）。先换安全 hook 再下结论。**成本**：整条 token 来源推倒重来。
- **S-07 复用真机指纹模板** → 聚类连累真机。每台独立 forge。**成本**：真号被限。
- **S-08 profile 000 当过闸** → 只是接受上报。**成本**：批量「成功」上线后全灭。
- **S-09 算法对、通道错** → 静态 OpenSSL/私有头/旧 ClientHello。先复现传输。**成本**：无限改 box。
- **S-10 单闸过了还有星座** → box ↔ device-id/token 双检；集群记忆冷却。**成本**：同一伪造配方刷到封。
- **S-11 软校验 e2e 当还原完成** → 首页放过 ≠ 写接口硬校验。按牌照升级 ①/②。
- **S-12 字段值对但 body 容器错** → dict 与有序 KV 列表不是一回事；把容器类型、重复键、顺序和编码纳入谱系并单变量。**成本**：在签名/会话层空转数轮，实际网关只是不认序列化形态。
- **S-13 把旧错误码归因当永久结论** → 先核最新成功对照与 `SUPERSEDED`/时间线；同一错误可由缺参数、HTTP 版本、配额或环境态触发。**成本**：把已被简单参数实验推翻的“硬件墙”写进交付。
- **S-14 把 Apple Attest 同形伪造标成纯算** → 结构可解析、result=0 或证书字段同形都不等于 Apple 链通过；只有真硬件 oracle 或服务端明确不校验才可交付。**成本**：伪造器看似完备但挑战/业务状态不闭环，批量上线全灭。
