# iOS 设备注册、密钥与证明谱系

用于 App 首启设备入库、登录后绑定、风险凭证及敏感请求分析。静态入口交 ios-recon，运行期证据交 ios-dynamic；这里负责全链谱系、生命周期与交付边界。只吸收当前样本能证明的节点，不套固定注册流水线。

## 对象先拆开

| 对象 | 常见材料 | 作用域与限制 |
|---|---|---|
| 安装实例 | App 自建 UUID、首次启动标记 | 生命周期依保存/备份策略；不是物理设备或账号身份 |
| Vendor 关联 | `identifierForVendor` / IDFV | 同设备同 Vendor 关联；删除该 Vendor 全部 App 后重装可变，单 App 重装样本不能证明永久不变 |
| 广告标识 | IDFA / ATT 状态 | 受授权及平台规则约束；全零/不可用不等于设备异常，不能作为必需的通用设备注册主键 |
| 本地凭据/状态 | Keychain item、UserDefaults、App Group 文件 | 不同访问组/容器/同步与可访问策略，不能只按键名或值相同合并 |
| 密钥身份 | SecKey 引用、tag、App Attest key identifier、公钥 | key ID 只是索引；保留字符串不证明底层密钥仍有效 |
| 平台证明 | App Attest attestation/assertion、DeviceCheck token | 各自用途与信任链不同，不是普通自定义签名或永久设备号 |
| 服务端设备记录 | register 返回 device/enrollment ID | 服务器分配的关系对象；值不变不证明底层设备或安装没变 |
| 风险/设备凭证 | SDK blob、token、Cookie | 先找签发与消费点；TTL、账号/设备/请求绑定未知就留空 |
| 账号与会话 | account ID、access/refresh token、session | 与设备登记分开验收；服务端下发不自动等于客户端不变透传 |
| 推送寻址 | APNs device token | App/环境相关推送材料，可变化；字段叫 device_token 不足以确定含义 |

①②③ 是粗分；正式谱系仍用来源四类：静态常量、本地生成、服务端下发、由已知字段派生。不确定时填待定和已知 API/响应锚点。身份类型、来源、运行依赖分列，不能用“设备态”掩盖生成缺口。

## 重建实际注册状态图

待查节点包括安装/首次启动、配置与 Challenge、密钥生成、平台证明、公钥/设备登记、凭证保存、账号绑定、遥测、业务请求、刷新、过期、解绑/撤销和重新登记。顺序、并行和缺省以实际证据为准。

每条边写：触发事件 → ObjC/Swift/C 实际调用 → 请求/响应 → 本地写入/读取 → 下一消费者。记录 bundle ID、Team/App ID、Mach-O UUID/hash、相对地址、版本和签名/entitlements。只有静态引用时标“代码支持未运行”；字符串、时间相邻和相同 token 外观都不能填成已证因果。

对异步 completion handler、delegate、Swift task 和后台 URLSession，用可验证的 task/request/key ID、回调关联与单调时钟交叉定位。只靠日志时间近不能确定哪次 Challenge 对应哪次证明。

## 字段与存储谱系

每个相关 header/query/body/嵌套字段及必要本地状态一行：

| 列 | 需要留下的证据 |
|---|---|
| 字段路径 / 身份类型 | 接口与方向、JSONPath/二进制偏移；安装、密钥、证明、设备记录、账号/会话分别列 |
| 来源 / 生产者 | 四类之一或待定；具体 API、响应位置、生成函数与版本 |
| 生成 / 封装输入 | method/path/query、容器/顺序/编码、压缩、摘要/签名/密文依赖分别追踪 |
| 存储 / 读取 | SecItem 查询属性、UserDefaults suite、数据库/文件或内存；写入与读取锚点 |
| 消费者 / 验证方 | 请求构建或本地校验点；服务端验证不可见则明确未知 |
| 生命周期 / 绑定 | TTL、刷新、撤销；安装、Vendor、密钥、账号/session、请求绑定分别标状态 |
| 对照 / 复现边界 | 单变量与原始证据；可本地计算、系统/硬件/平台服务/上游依赖及未解部分 |

从上游响应拿到 token，只能证明签发来源；需要闭合响应值→读取→消费才能断言透传，途中也可能派生或再次封装。原始敏感材料留在目标受控证据目录，报告只用摘要/稳定脱敏标签和文件锚点，不把可用凭证或私钥粘进 Skill。

## Keychain、App Group 与生命周期

- `keychain-access-groups` 管 Keychain 共享权限；`com.apple.security.application-groups` 管 App Group 共享容器等能力。名字相似不证明二者相同，也不证明数据必然跨 App/扩展共享。
- 检查 `kSecClass`、service/account/tag、access group、`kSecAttrAccessible`、`kSecAttrSynchronizable` 与实际读写条件；不要为盘点把整个 Keychain 值导出。
- `ThisDeviceOnly` 影响向其他设备迁移；可访问级别、同步与备份各有条件。Keychain 不等于永久设备 ID，也不能统一断言卸载即清空或永远保留。
- Secure Enclave 私钥保护与普通 Keychain 数据不同。`SecKey`/`SecItem` API 出现不证明硬件级别；检查实际生成属性与使用路径。不能把不可导出的私钥当普通字节缓存读取。
- Face ID/Touch ID、用户在场或口令可约束密钥使用；本地验证成功不直接证明服务器业务账号真实身份。

生命周期矩阵优先填已有样本：进程重启、正常升级、凭证到期/刷新、退出/重新登录、卸载重装、备份恢复/设备迁移、Vendor 全部 App 移除、密钥撤销。每种事件分别观察安装 ID、IDFV、Keychain 项、key ID/公钥、服务端设备 ID、风险 token 和 session。

重装、删除 Keychain、恢复设备可能破坏不可恢复密钥或会话。本地梳理只设计实验；新动作先核当前授权、影响和恢复条件，已有授权不重复询问。不要把“新安装”默认实现成清空全设备状态。

## App Attest：首次证明与后续 assertion

1. 核对 `DCAppAttestService.isSupported`、环境及实际错误；不能仅凭系统版本或机型宣称可用。
2. 追踪 `generateKey` 返回的 key identifier 与保存位置。公钥/私钥关系和业务账号绑定分别记录，不能把 key ID 当可导出私钥或永久物理设备号。
3. 初次 `attestKey`：服务端 Challenge 与 `clientDataHash` 关联；服务端按 Apple 协议验证链、nonce、App ID / `rpIdHash`、key identifier/公钥关系、环境等，再登记可信公钥。
4. 后续 `generateAssertion`：用已建立的密钥关系保护所选请求数据；不是每个业务请求都重新向 Apple 申请 attestation。
5. 服务端核验 assertion 签名、请求数据摘要、App ID、Challenge/新鲜度及 counter。并发、乱序、重试和业务幂等需要专门状态设计；不能一概放宽计数，也不能机械按接收时间推定生成顺序。

`clientDataHash` 具体包含什么必须追实际序列化。单独签 Challenge 不自动覆盖 method/path/body/账号上下文；CBOR 可解析、证书字段同形、SDK 回调成功都不能替代服务器完整验证与业务结果。

App Attest key 可以跨正常升级保留，但不跨卸载重装、设备迁移或备份恢复；Keychain 里剩下旧 key ID 不改变这一点。不得为采样批量新建 key 或重复消费 attestation/Challenge。

App Attest 不能确定性识别全部受损系统，也不证明真人或正常业务意图。Fraud Risk Metric 是与 attested keys 数量有关的辅助估计，需记录 receipt 生命周期和查询语义；不是完整设备历史或固定封禁结论。

## DeviceCheck：少量设备状态，独立于 App Attest

- `DCDevice.generateToken` 返回临时 token；业务服务端用它和开发者鉴权材料向 Apple 查询/更新两个 bit。开发者的服务端 JWT 与设备 token 是不同凭据。
- 两个 bit 只有四种组合，可记业务标记；不是无限设备画像、UDID 或账号实名证明。
- 记录业务方给 bit 的实际含义、更新者、修改时间和状态清理策略。App 重装不等于服务端状态自然清空；也不能把 DeviceCheck token 当稳定设备主键。
- 没有服务端日志时，看到 token 调用不证明查询/更新已经发生；不要为“确认”自行写 bit 或触发权益流程。

## 硬件密钥与受管设备边界

一机一密可能指 App 实例、公钥登记或账号设备关系，按字段说明。硬件私钥不可导出，不排除受控进程请求它签名；能调用不代表私钥已纯算还原。自行创建 Secure Enclave key 也不自动得到 Apple 远程证明。

Managed Device Attestation 属于 MDM/ACME 等受管场景，需要对应系统、硬件及管理条件；不能作为任意消费 App 的通用设备身份 API。仓库记录的旧设备基线不证明支持这项能力，不为引入它升级/擦除或注册管理配置。

请求保护仍区分摘要、HMAC、数字签名、AEAD 的 key/nonce/tag/AAD、密钥派生、序列化和上游透传。TLS 服务端校验、mTLS 客户端凭证、应用签名和平台证明互不替代。

## 隐私与平台能力边界

设备风险信号、IDFV 关联、广告跟踪及通过信号派生唯一设备身份是不同用途。Apple 对设备 fingerprinting 有独立限制；特定反欺诈用途的 ATT 例外不等于无限采集或跨域识别许可。厂商宣称“稳定设备 ID”不能证明当前 iOS 版本获取了永久硬件标识。

## 交付与官方来源

用 [报告模板](../assets/device-enrollment-audit.md) 分开设备登记、密钥登记、账号绑定与业务效果。已解析本地算法可以单独交付；外部证明/签发依赖列到字段级，不能从某字段依赖平台直接终止整条本地分析，也不提前安排 oracle 兜底。

以下公开说明于 2026-09-17 核对；仅定义平台能力，具体 App 调用、支持情况与服务端消费需当前样本验证：

- [IDFV](https://developer.apple.com/documentation/uikit/uidevice/identifierforvendor)、[IDFA](https://developer.apple.com/documentation/adsupport/asidentifiermanager/advertisingidentifier)、[用户隐私与数据使用](https://developer.apple.com/app-store/user-privacy-and-data-use/)。
- [App Attest 建立完整性](https://developer.apple.com/documentation/devicecheck/establishing-your-app-s-integrity)、[服务端验证](https://developer.apple.com/documentation/devicecheck/validating-apps-that-connect-to-your-server)、[Fraud Risk Metric](https://developer.apple.com/documentation/devicecheck/assessing-fraud-risk)。
- [DeviceCheck 设备状态](https://developer.apple.com/documentation/devicecheck/accessing-and-modifying-per-device-data)、[Secure Enclave 密钥](https://developer.apple.com/documentation/security/protecting-keys-with-the-secure-enclave)、[Keychain 可访问属性](https://developer.apple.com/documentation/security/ksecattraccessiblewhenpasscodesetthisdeviceonly)。
- [Managed Device Attestation](https://support.apple.com/guide/deployment/managed-device-attestation-dep28afbde6a/web)。
