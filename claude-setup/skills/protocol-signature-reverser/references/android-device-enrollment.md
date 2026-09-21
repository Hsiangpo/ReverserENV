# Android 设备注册、身份与密钥谱系

用于首启设备入库、注册/登录绑定、设备令牌、完整性证明和一机一密分析。这里只定义可复核的分析方法；具体 App 是否使用某机制，以当前版本样本为准。静态侦察由 android-recon、运行期取证由 android-dynamic 执行。

## 先区分对象与任务

| 对象 | 典型材料 | 不可混同 |
|---|---|---|
| 安装实例 | 自建 UUID、FID、首次启动状态 | 物理设备、账号、推送 token |
| 平台/开发者范围标识 | SSAID、App Set ID、部分生态 OAID | 永久全球设备编号、可信环境证明 |
| SDK 关联记录 | SDK visitor/device ID、风险标签 | 系统 ID、真人证明；厂商“稳定”宣传不是生命周期证据 |
| 服务端设备记录 | register 响应 ID、enrollment ID | 本地生成算法；同名字段在不同接口可有不同含义 |
| 密钥身份 | alias、key_id、公钥、证书链 | 设备记录、账号凭证；alias 相同也不证明密钥相同 |
| 平台证明 | Integrity token、Key Attestation | 自定义 HMAC、可无限重放的永久凭证 |
| 设备/风险凭证 | 不透明 token、绑定 Cookie、风险状态 | access_token、Push Token；先找签发与消费方 |
| 账号与会话 | account ID、access/refresh token、session | 设备身份；同一设备可能出现多个生命周期 |

先约定成功标准：服务端接纳设备记录、绑定密钥、建立账号关系或实际业务动作，分别是什么证据。设备注册和账号注册分开验收，`code=0` 不能替代预先选定的判官。

## 还原实际状态图

以下是待查节点，不是每个 App 必须具备的固定顺序：

`安装/首次启动 → 配置与 Challenge → 密钥/证明 → 设备登记 → 凭证持久化 → 账号/会话绑定 → 业务请求`

遥测/风险上报可能在登记前、后、并行或根本不存在；另追踪刷新、过期、注销、撤销和重新登记分支。

对每条观测到的边记录：

1. 触发事件及代码锚点：启动、后台任务、登录、敏感动作或定时器；不要仅凭 `/register` 命名认定功能。
2. 生产者与消费者：方法/JNI/native offset、接口方向、响应字段流入哪个存储和下一请求。
3. 条件与时序：前置状态、成功/错误分支、重试/幂等策略、线程和连接关联。
4. 状态变化：保存、读取、更新、删除了什么；密钥身份、账号/session 是否同时变化。
5. 证据等级：已观测、代码支持未运行、假设待证、未知、有依据的不适用；不能用文档补成观测。

有后台并发时用关联 ID、单调时钟和事件顺序定位因果。时间接近不等于依赖；不能把未捕获的前置请求补画成事实。

## 字段谱系的两条轴

沿用主 Skill 的四类来源：静态常量、本地生成、服务端下发、由已知字段派生；未知时写待定和缺证，不能强填。系统 API、SDK、KeyStore 是生产者/依赖，不另冒充第五种来源。

身份类型另列：安装、平台范围标识、SDK关联、服务端设备、密钥、证明、风险凭证、账号/会话。设备态不等于“本地算法”，服务端 ID 也可能长期绑定设备。

每个 header/query/body/嵌套字段和必要本地状态至少记录：

| 列 | 应填内容 |
|---|---|
| 字段路径与身份类型 | 接口、方向、JSONPath/二进制偏移；同名跨接口不自动合并 |
| 来源与生产者 | 四类之一或待定；真实 API/方法/响应位置和版本锚点 |
| 生成/封装输入 | 原始字节、规范化、依赖字段、算法；编码/压缩/加密/签名分开 |
| 持久化与读取 | SharedPreferences/数据库/文件/Keystore alias/内存；写入与读取调用点 |
| 消费者与验证方 | 哪个请求/本地检查使用；服务端验证逻辑不可见则明确未知 |
| 生命周期与绑定 | TTL、刷新、撤销；安装/签名证书/设备/密钥/账号/session/请求绑定分别标已证或未知 |
| 实验证据 | 单变量、对照、结果、捕获边界、原始材料锚点；未做只写实验设计 |
| 复现边界 | 可本地计算、系统状态依赖、服务器透传、平台/硬件依赖、未解；不是直接宣布交付形态 |

敏感原始材料留在目标受控证据目录，报告用文件锚点、摘要和稳定脱敏标签关联；不把真实 token、私钥、账号秘密复制进 Skill、模板或维护日志。

## 生命周期矩阵

用已有前后样本优先填矩阵；“未测试”不等于“不变化”。

| 事件 | 分别观察 |
|---|---|
| 进程重启 / App 正常升级 | 内存态、安装标识、密钥、公钥、token、session |
| 凭证自然到期 / 已授权刷新 | TTL 来源、刷新接口、旧值失效、新旧绑定和并发处理 |
| 正常退出登录 / 重新登录 | 设备记录是否保留，账号关联与会话是否重新建立 |
| 清数据 / 卸载重装 / 备份恢复 | 安装 ID、密钥、公钥、服务器映射与凭证是否分别变化 |
| 签名证书变化 / 系统用户变化 | SSAID 作用域、平台证明、服务端登记关系 |
| 换设备 / 恢复出厂 / 密钥撤销 | 重新登记路径及剩余服务器状态；不能假定全部清空 |

清数据、重装、账号轮换、恢复出厂可能破坏现有会话或不可导出密钥；本地分析不授权执行。若确需验证，先确认该动作处于当前授权范围、保存可恢复状态并说明不可恢复部分；否则交付最小实验设计。已有明确授权不重复询问。

## Android 平台能力：遇到才核对

| 机制 | 会改变分析决策的事实 |
|---|---|
| Android ID / SSAID | Android 8+ 通常按签名密钥、系统用户、设备限定作用域；不能从一个样本推永久不变 |
| AAID / OAID | 广告或特定生态标识，可能重置、不可用或限域；具体实现/权限待查，不作为可信设备证明 |
| App Set ID | 检查返回 scope；开发者级与 App 级不同，存在重置条件，不假设所有安装渠道一致 |
| FID / 安装 UUID / FCM token | 安装身份与推送寻址分开；备份、删除和刷新策略影响生命周期 |
| Keystore / KeyMint | API 命中不证明 hardware-backed；读取实际安全级别和生成参数，区分软件、TEE、StrongBox |
| Key Attestation / Verified Boot | 服务端需验可信链、撤销、Challenge、应用/密钥属性及启动状态；本地可解析不等于服务端接受 |
| Play Integrity | 核对包名/签名/版本、Standard 或 Classic、Play 环境、请求绑定、时间和具体 verdict，不概括成“Google 风控通过” |
| Device Recall | 当前官方为 beta，少量设备状态 bit，可支持跨重装/重置召回；有 Play 等条件，不暴露永久设备 ID |

### Play Integrity 的关键分支

- 无 Google Play Store/services：先记支持条件缺口；不假定可用，不伪造 verdict，也不把接口失败直接归因 Root。
- Standard：记录 `requestHash` 原始输入和字节序列化，验证其与当前请求的关系；API 不自动决定关键业务字段。自动重放缓解不等于业务幂等完成。
- Classic：记录 `nonce` 的签发、请求绑定、一次性消费和服务端校验；不可将时间戳当全部重放防护。
- `PLAY_RECOGNIZED`、`LICENSED`、设备完整性属于不同声明；不推导业务账号实名、真人操作或业务授权。
- `MEETS_BASIC_INTEGRITY` 不保证 Bootloader 锁定；更强等级的要求随 Android 版本变化。不能只看标签名推导具体硬件/补丁状态。
- `UNEVALUATED`、空字段、网络/API 错误、未支持和已评估的不满足分开记录；不要统一归为恶意。
- `appAccessRiskVerdict`、Play Protect、recentDeviceActivity 是具体维度的风险信号；后者不是设备全部业务 HTTP 请求数。
- 历史样本中的 SafetyNet 与当前 Play Integrity 分开；SafetyNet Attestation 官方已在 2025-01 关闭，不能规划成当前可用服务。

### 一机一密与请求密码学

先区分共享密钥、客户端非对称密钥、平台证明支持的密钥关系；“一机”到底是安装、设备记录还是账号绑定，需要证据。

记录 alias/key_id → 公钥/证书 → 注册响应 → 后续签名消费者，并查轮换、撤销、失败恢复。不可导出私钥不等于无法请求硬件执行签名；能调用也不等于可移植为纯 Python。SDK 白盒不自动等同 TEE/StrongBox。

请求保护分开登记规范化输入、HMAC/签名、摘要、AEAD 的 key/nonce/tag/AAD、密钥协商/派生与服务器透传。APK 发布签名、业务请求签名、平台证明不互相替代；TLS 成功也不证明业务字段受应用层签名覆盖。合法随机填充/随机 nonce 不能强求密文字节一致。

## 交付

使用 [报告模板](../assets/device-enrollment-audit.md) 落到目标项目。只梳理时交付证据锚点、未知项和下一个区分实验；实现时再按主 Skill 的谱×物×证×界验收。注册某阶段通过、有效期内重放、平台服务在线依赖不能包装成完整注册纯算。

## 官方依据与复核边界

以下为 2026-09-17 核对的公开能力来源，不是任何目标 App 已采用的证据。具体版本要求、配额、beta 状态和支持矩阵应在影响决策时重新查阅。

- [标识最佳实践](https://developer.android.google.cn/identity/user-data-ids?hl=en)；[SSAID](https://developer.android.google.cn/reference/android/provider/Settings.Secure?hl=en#ANDROID_ID)；[App Set ID](https://developer.android.google.cn/identity/app-set-id?hl=en)；[Firebase 安装](https://firebase.google.cn/docs/projects/manage-installations?hl=en)。
- [Keystore](https://developer.android.google.cn/privacy-and-security/keystore?hl=en)；[Key Attestation](https://developer.android.google.cn/privacy-and-security/security-key-attestation?hl=en)；[Verified Boot](https://source.android.google.cn/docs/security/features/verifiedboot?hl=en)。
- [Integrity verdicts](https://developer.android.google.cn/google/play/integrity/verdicts?hl=en)；[Standard](https://developer.android.google.cn/google/play/integrity/standard?hl=en)；[Classic](https://developer.android.google.cn/google/play/integrity/classic?hl=en)；[Device Recall](https://developer.android.google.cn/google/play/integrity/device-recall?hl=en)；[SafetyNet 退役](https://developer.android.google.cn/privacy-and-security/safetynet/deprecation-timeline?hl=en)。
