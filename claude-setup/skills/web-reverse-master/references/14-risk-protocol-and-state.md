# Web 风控：协议证据与状态机

仅在需要区分传输、客户端采集、挑战、会话或业务决策时读取。当前厂商资料见 [能力参考](15-vendor-capability-reference.md)，验证码服务端验证见 [验证与降级](../../captcha-solver/references/verification-and-fallback.md)。不因厂商名称直接选择实现或默认执行外部动作。

## 1. 先定位产生结果的组件

同一站点可同时部署 CDN/WAF、Bot 检测、独立验证码、设备识别和业务风控。保留 request id、时间、响应内容、规则/检测 ID（可得时）、重定向链和发起上下文，分别记录：

| 层 | 观察对象 | 不能据此单独得出的结论 |
|---|---|---|
| 网络与协议 | TLS/ALPN、HTTP 版本、代理、连接与请求 | 某个客户端库或 UA 保证通过 |
| 客户端采集 | 实际加载资产、模块、输入输出、执行 realm | 看到 Canvas API 就确定某厂商或确定被该字段拒绝 |
| 挑战/验证 | challenge 类型、服务端校验、票据消费 | 前端成功、token 非空就是业务接受 |
| 评分与策略 | 字段语义、规则版本、命中动作、未知值 | 一个分数等于最终授权 |
| 会话/账户 | Cookie/storage、连续事件、账户上下文 | Cookie 有效期内一定保持放行 |
| 业务 | 登录/查询/写入的约定结果与服务端日志 | HTTP 200、响应大小或页面标题就是完成 |

固定域名、Cookie 名、脚本名只作线索。第一方代理、自定义路径和多厂商组合会改变外观；必须由当前资产、请求链或部署配置补证。识别未知时记录候选及冲突证据。

## 2. 分开维护公开知识与目标实证

每条可复用结论注明 `官方机制 / 当前实测 / 历史案例 / 待验证`。历史样本缺 hash 或原始证据时写“版本未核实”，不得补造。

建议在既有 notes 中记录以下信息，不要求为每项创建文件：

| 信息 | 内容 |
|---|---|
| 目标锚点 | 站点、入口、资产 URL/hash、SDK/runtime 版本、采样时间 |
| 产品条件 | 产品模块、API/schema/规则组版本、区域/套餐、Beta/Preview/GA 或未知 |
| 来源 | 官方 URL、取得日期、原文适用范围；发布日期和页面修订日期分别记 |
| 决策证据 | 被观测组件、输入、输出、日志关联、控制组、第一处差异 |
| 结论边界 | 已解释字段、未知字段、外部签发或浏览器依赖、下一项区分实验 |

产品宣传、文档示例和版本发布记录不能证明目标已启用。日期已过也不能证明 rollout 完成。入口规则保留方法，易变的厂商能力留在按需 reference。

## 3. 传输证据，不从配置名推定线上字节

只有证据指向传输差异时才展开本节；不把全部网络参数列成每次开工的强制检查。

| 工作面 | 对照记录 |
|---|---|
| TLS | 客户端/runtime 版本、握手位置、ALPN、ClientHello 可见字段、是否会话恢复、JA3/JA4 的计算方法与缺失条件 |
| HTTP/1.1 | 实际 request line、header 字节/大小写/顺序、重复 header、正文编码 |
| HTTP/2 | 协商结果、SETTINGS、伪头部和常规字段、流复用及流控；按证据查看 HPACK/帧，而非套 HTTP/1.1 模板 |
| HTTP/3/QUIC | 仅在实际协商时记录 QUIC/HTTP 版本、可见传输参数、回退及重连；不从 URL 推定协议 |
| 网络路径 | 代理类型、TLS 在何处终止、出口、连接复用；分清浏览器到代理和代理到服务端 |

DevTools 展示顺序、Python 字典顺序、库的 impersonation 名称都不能证明线上 header/握手字节。优先用可控服务端、合适的解密抓包或已验证覆盖面的网络日志；HAR/CDP 未包含的数据标为未知。Python 3.10+ 的 dict 保持插入顺序，但库和协议层仍可能改写最终请求。

JA3/JA4 是客户端连接特征，不是设备唯一身份；一个指纹可对应多名用户。同类客户端也可能因版本、扩展顺序策略或网络路径产生差异。GREASE、会话恢复、ECH 等只在当前采样和解析器支持时解释，不能据缺字段直接判定伪装。

保持对照实验只改变一个可控变量；切换 HTTP 库往往同时改变 TLS、HTTP 版本和 header，不算已隔离单一原因。选择 requests、curl_cffi 或其他已授权依赖应由所需协议能力与当前版本决定，不固定浏览器版本或唯一库。

## 4. 浏览器身份与存储上下文

从真实调用建立环境差异，沿用 [运行时 checkpoint](13-runtime-observation-and-rebuild.md)，不批量制造“真实指纹”。

- UA 与 UA-CH：区分低熵/高熵信息、Accept-CH/权限、品牌列表和平台。`Sec-CH-UA` 中的非真实品牌是协议允许的行为，不能单独判为自动化。
- realm：顶层页、iframe、Worker/service worker 的 origin、对象身份和存储访问不同。主页面 Hook 没命中不能证明采集不存在。
- Cookie：记录 Domain/host-only、Path、Secure、HttpOnly、SameSite、expiry，以及浏览器实际接受/拒绝原因。
- 分区状态：CHIPS 的 partition key 包含顶层站点上下文。复制 name/value 不能完整描述同一个 Cookie；跨顶层站点或 iframe 的存储失败先查分区与权限。
- 环境观测：Canvas/WebGL/Audio/字体/媒体能力只记录实际调用和消费者；并非所有厂商模块都会采集全部信号。数据变化要与相同版本原浏览器对照，不能给所有机器固定一组值。

浏览器存储限制、CSP、资源加载错误、网络故障和业务拒绝分别留痕；不能把 SDK 未加载统一记为“设备风险”。

## 5. 挑战、票据与业务是不同状态

以下是可裁剪的分析模型，不是所有厂商固定执行顺序。被动评分可以没有交互挑战，非验证码请求可以没有票据。

```text
加载/初始化 -> 信号采集 -> 分类或挑战选择
                         -> 无交互 / 交互 / 仅评分
                         -> 票据签发（若有）-> 服务端验证/消费（若有）
                         -> 边缘策略 -> 业务决策
任一阶段可出现：网络失败、过期、重复消费、测试模式、配置的容灾分支
会话可能持续采样、重新评分、撤回 clearance 或再次挑战
```

对一次尝试分别保存：

| 结果轴 | 示例含义 |
|---|---|
| transport | 请求是否成功到达、响应是否可解析 |
| client | 脚本执行或交互是否完成 |
| vendor verification | 厂商后端验证结果、原因、是否消耗票据；未取得时写未知 |
| decision provenance | 正常验证、测试模式、降级/容灾、未知；从配置和日志确认，不凭前缀泛化 |
| edge policy | allow/block/challenge/rate limit/其他动作及对应规则 |
| business | 预先约定的业务结果、错误码、返回对象或状态变更 |

外层 `success` 可能只表示 API 调用成功，必须读取文档规定的内部结果。容灾放行可以产生真实业务接受，但不证明正常验证机制已通过；成功率按上述来源分别统计。

状态码只定位现象：401 可能是预期的 PAT 获取失败，402 可能是内容付费策略，403/429 可能由不同组件产生。先保存原响应及现场，再决定实验；不得自动清票、换 IP 或丢弃关键失败证据。

### 票据谱系

每个 token/Cookie 单独记录签发者、消费端、传递位置、格式版本、app/sitekey/scene/action、签发时间、TTL、一次性语义、scope/partition、刷新路径。IP/UA/账户/设备绑定要分“官方支持”和“本目标已验证”，未知写未知。

固定格式可解析不等于可本地生成；本地计算的采集载荷与服务端签发票据可能共存。字段谱系沿用 param-encryptor 的本地计算、环境采集和上游透传分类。不要用不透明 token 的长度推定算法。

## 6. 分数、身份、授权分别解释

对每个评分字段登记范围、方向、未知/缺省值、模块、版本、来源、规则阈值及依据。不同厂商的“高分”含义可能相反，设备识别 confidence 也不等于欺诈概率。

浏览器执行成功、challenge 完成、Bot Score、身份认证和业务授权是独立观察值。例如 JSD 通过仍可能因其他信号得到低 Bot Score；认证过的 Agent 仍受访问策略约束。

### HTTP Message Signatures / Web Bot Auth

遇到实际签名头时，记录所用 profile、`Signature-Input`/`Signature`、covered components、signature base、密钥来源/轮换、算法、`created`/`expires` 及 nonce/replay 策略。RFC 9421 提供机制，厂商 profile 另有约束；出现 `nonce` 不代表验证端实际去重，也不能据签名有效推导业务授权。

签名的完整性结论只覆盖已签名且实际验证的组件；没有覆盖 method、目标或正文摘要时，不得宣称这些部分受该签名保护。正文完整性还需确认正文摘要参与签名且验证端核对了摘要与实际正文。

### Privacy Pass / PAT

分清 challenge、attestation/issuance 和 redemption，以及 issuer/attester/origin 各自角色。RFC 9577 定义 HTTP 认证方案；特定 PAT 产品有自身实现条件。由签发服务产生的凭证不是浏览器可独立纯算字段。

Cloudflare 公开说明 PAT 不能自动完成整个挑战，获取 PAT 的 401 可走标准挑战分支。分析时继续关联最终挑战与业务结果，不把可选优化失败当根因。

## 7. 可复现验收

先使用本地 fixture、隔离服务端或授权测试租户验证字段解释和状态转换。正常成功、拒绝、过期、重复消费、网络异常、测试/降级状态按当前系统存在的分支选择；不要为填表自动访问生产接口。

算法字节验证固定时间和随机源，比较真正函数入口到最终 writer 的第一处差异。对象的执行后快照、长度相同或段数相同不能替代加密入口的逐字节证据。HTTP/业务验证单独报告，不由算法对拍结果代替。

本地分析记录与实际请求 schema 分离：不向线上 payload 加入自创的会话年龄、人格、置信分数或调度参数。日志避免保存活凭据，遵守 [证据卫生](12-evidence-hygiene.md)。

## 8. 公开资料锚点

下列资料于 2026-09-19 核对；标准是协议依据，MDN 是平台行为参考，厂商页只证明公开机制，均不替代目标实证。

- [RFC 9421 HTTP Message Signatures](https://www.rfc-editor.org/rfc/rfc9421)：2024-02，Standards Track。
- [RFC 9577 Privacy Pass HTTP Authentication Scheme](https://www.rfc-editor.org/rfc/rfc9577)：2024-06，Standards Track；[RFC 9576 架构](https://www.rfc-editor.org/rfc/rfc9576)为 Informational。
- [MDN CHIPS](https://developer.mozilla.org/en-US/docs/Web/Privacy/Guides/Privacy_sandbox/Partitioned_cookies)：分区 Cookie 与顶层站点。
- [MDN Sec-CH-UA](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-CH-UA)：品牌列表、低熵提示及兼容性。
- [Cloudflare JA3/JA4](https://developers.cloudflare.com/bots/additional-configurations/ja3-ja4-fingerprint/)：可用条件和缺失字段。
- [Cloudflare JSD](https://developers.cloudflare.com/cloudflare-challenges/challenge-types/javascript-detections/)：执行、评分与策略的区别。
- [Cloudflare Clearance](https://developers.cloudflare.com/cloudflare-challenges/concepts/clearance/)：Challenge/Precursor 会话状态；[PAT](https://developers.cloudflare.com/cloudflare-challenges/reference/private-access-tokens/)：401 与挑战流程。
