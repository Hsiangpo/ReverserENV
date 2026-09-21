# 厂商公开能力与目标待证清单

> 读取条件：识别产品模块、选择分析分支、避免旧品牌/旧协议/单码归因；不是可直接执行的逆向 recipe。
> 本轮官方资料核对日：**2026-09-19**。正文读取属于 `DOC` 证据，不是目标站点的 `LIVE` 实验。
> 文档更新时间不等于产品发布日期；产品介绍不证明目标启用、租户授权、地区覆盖或全量上线。

## 使用方法

1. 先划分网络/客户端信号、Bot 判定、challenge、账户/交易策略、AI Agent 身份与权限模块。
2. 记录目标真实资产 URL/hash、SDK/API/schema 版本、租户配置、区域、模式和实际响应。
3. 每项公开能力补一列目标证据：`未观察 / 仅发现脚本 / 信号已采集 / 判定已返回 / 规则已执行 / 业务已接受`。
4. 字段若由上游返回、密封载荷或服务端状态派生，不因字符串可解析就写成本地生成。
5. 缺内部实现时只定位实际入口与输入输出；不从产品名推断 VM、opcode、密钥、全部指纹项或判定权重。

验证码校验细节见 [二次校验与容灾](../../captcha-solver/references/verification-and-fallback.md)。
厂商分数不共享方向：Bot 风险、Agent trust、identity strength、设备识别 confidence 是不同语义。

## 1. Akamai

- **模块**：Bot Manager 配置、TLS/信誉相关配置，以及 Application Security 的 JA4 设置。
- **公开证据**：[导出配置](https://techdocs.akamai.com/application-security/reference/get-export-config-version.md)
  展示 Bot/TLS/Reputation 等配置结构；[JA4 设置](https://techdocs.akamai.com/application-security/reference/get-ja4-fingerprint-settings.md)
  将 JA4 说明为 TLS 指纹，接口标有 Beta，涉及 WAP/Kona。
- **日期/状态**：本轮读取的是 API 文档和示例；产品正文访问受限，未据宣传页补写当前 sensor 内部能力。
- **目标待证/路由**：先看实际配置和流量再确认 Bot Manager、JA4 或某策略是否启用。主交 master；
  `_abck` 等历史字段名称不证明当前编码、传感器版本或业务判定。

## 2. DataDome

- **模块**：JavaScript Tag、Device Check、CAPTCHA、Bot Protect、Agentic Trust 与意图策略。
- **公开证据**：[JS Tag](https://docs.datadome.co/docs/javascript-tag) 与
  [Device Check](https://docs.datadome.co/docs/device-check) 的采集描述不同：不能把 Tag 的“无 Canvas”推广到整个产品；
  Device Check 文档列 Canvas/执行特征且说明不使用行为模型；[CAPTCHA](https://docs.datadome.co/docs/datadome-captcha) 使用行为信息。
  [Agentic Trust](https://docs.datadome.co/docs/agentic-trust-getting-started) 基于 Bot Protect；
  [Agent Trust Score](https://docs.datadome.co/docs/agent-trust-score) 是按客户环境计算的 0–100 Agent 信任分，
  与 identity strength 分开；另有 [Intent-based protection](https://docs.datadome.co/docs/intent-based-protection)。
- **日期/状态**：上述为本轮当前文档，不证明所有站点或套餐启用所有模块。
- **目标待证/路由**：识别当前请求落在哪个模块，分别追踪采集、挑战、信任分、身份与执行策略；
  不把一段 sensor 的结果当整个业务风控。跨模块交 master，有真实挑战协议才交 captcha-solver。

## 3. Cloudflare

- **模块**：Bot Management、JS Detections、Challenge/clearance、Turnstile、AI Bot 管理各有边界。
- **公开证据**：[Bot score](https://developers.cloudflare.com/bots/concepts/bot-score/) 说明 heuristics、ML、JSD，
  Bot score 为 1–99，越高越倾向人类；0 表示未计算，不能按最低风险或最高风险处理。
  `__cf_bm` 参与会话处理，旧 Anomaly Detection 已停止新客户接入并处于弃用过程；
  [JA3/JA4](https://developers.cloudflare.com/bots/additional-configurations/ja3-ja4-fingerprint/) 是另一个信号面。
  [JSD](https://developers.cloudflare.com/cloudflare-challenges/challenge-types/javascript-detections/)
  通过仍可能得到很低 Bot score；[clearance](https://developers.cloudflare.com/cloudflare-challenges/concepts/clearance/)
  描述 Challenge 与 Precursor 的动态处理和可撤回条件。
- **日期/状态**：[Block AI Bots](https://developers.cloudflare.com/bots/additional-configurations/block-ai-bots/)
  本轮页面仍含 rollout 预告；页面出现 9 月 15 日相关计划不能当全量部署证明。
- **目标待证/路由**：分别看 JSD、Bot score、规则动作、challenge token/clearance 和业务状态；
  JSD pass、cookie 出现或静态资源可访问均不等于登录或业务授权。实际版本、套餐与规则另证。

## 4. HUMAN

- **模块**：Bot Defender、Account Defender、Credential Intelligence，以及整合后的 Sightline Cyberfraud Defense / AgenticTrust。
- **公开证据**：[检测说明](https://docs.humansecurity.com/applications/bd-detection-overview.md)
  区分 Sensor、云 Detector、cookie 风险结果与 Enforcer；列行为、浏览器/设备/网络指标、ML 和历史画像。
  [Sightline 迁移](https://docs.humansecurity.com/applications/whats-different-in-sightline-cyberfraud-defense.md)
  对照旧三产品界面，并列 AgenticTrust 的 Agent 观察和权限控制。
  [Account Defender](https://docs.humansecurity.com/applications/getting-started-with-account-defender.md)
  需要用户 ID 等账户上下文。
- **日期/状态**：本轮读到迁移文档；不推定每个旧 Bot Defender 租户均已迁移。PerimeterX/`px` 可作为历史检索线索。
- **目标待证/路由**：Sensor 采集与 Enforcer 拦截分别证明；账户画像与 Bot score 不能混同。
  跨信号、模型与执行器由 master 梳理；Press & Hold 等 UI 不是全部检测能力。

## 5. Imperva / Thales

- **模块**：Advanced Bot Protection（ABP）；账户盗用保护、WAF、DDoS 为不同能力面。
- **公开证据**：[ABP](https://www.imperva.com/products/advanced-bot-protection/)
  描述客户端 interrogation、行为、ML、连接特征、威胁情报与可调策略；
  [公司说明](https://www.imperva.com/company/) 明确 Imperva 已属 Thales。
- **日期/状态**：本轮产品文档；“700+ 维度”等属于厂商披露，不作效果测评或目标采集项清单。
- **目标待证/路由**：确认 ABP 还是 WAF/账户规则返回；旧 Incapsula 名称不决定当前模块或协议。
  用 master 拆分网络、客户端和业务执行证据，不凭拦截页样式归因。

## 6. F5 / Shape

- **模块**：F5 Distributed Cloud Bot Defense，覆盖 Web、移动 App、API，并突出 Agent-aware classification。
- **公开证据**：[当前产品](https://www.f5.com/products/distributed-cloud-services/bot-defense)
  描述实时行为、客户端遥测、平台信号、持续调整和 allow/block/rate-limit/step-up；
  [收购公告](https://www.f5.com/company/news/press-releases/f5-completes-acquisition-of-shape-security)
  记录 2020-01-24 完成 Shape 收购。
- **日期/状态**：收购日期只解释品牌沿革；当前产品文案不证明旧 Shape 部署已更新或具备全部功能。
- **目标待证/路由**：确认实际部署、SDK 与受保护登录/结账等流程；Bot 检测、业务逻辑保护与完整支付风控分开。

## 7. AWS WAF

- **模块**：Bot Control Common/Targeted；Fraud Control ATP/ACFP；WBA 与 AI 流量管理。
- **公开证据**：[Bot Control](https://docs.aws.amazon.com/waf/latest/developerguide/waf-bot-control.html)
  Common 识别/验证常见 Bot 和标签，Targeted 增加浏览器 interrogation、指纹、行为与可选 ML；
  当前文档包含 WBA 与 CloudFront 限定的 Monetize/HTTP 402。
  [ATP](https://docs.aws.amazon.com/waf/latest/developerguide/waf-atp.html)
  检查登录与泄露凭据，CloudFront 可检查响应成功/失败；不能等同 Bot Control。
- **日期/版本**：[规则变更记录](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-changelog.html)
  记录 2025-11-20 v4 的 WBA、2026-05-22 v6 的 Regional 扩展、2026-07-24 v6.1。
  静态版本、默认版本、区域/资源与功能条件分别核查，不能只写“4.0+ 所有资源通用”。
- **目标待证/路由**：读取实际托管规则版本、标签、动作、资源及 SDK；WBA 的身份验证不等于业务权限，
  HTTP 402 是收费策略结果，不按 challenge 失败处理。

## 8. Google reCAPTCHA / Google Cloud Fraud Defense

- **模块**：reCAPTCHA 是 Google Cloud Fraud Defense 的组成部分，涉及 Bot、账户、交易保护。
- **公开证据**：[概述](https://cloud.google.com/recaptcha/docs/overview)
  描述客户端采集→token→后端 `assessments.create`→0–1 分数和 reason→商户决策；
  该 reCAPTCHA 分数越高越倾向合法交互，不能套用腾讯风险 Score 的方向。
  [旧术语映射](https://cloud.google.com/recaptcha/docs/reconcile-legacy-terminology)
  对照 v2/v3 与 Website score/checkbox/policy-based challenge。
- **日期/状态**：[Release notes](https://docs.cloud.google.com/recaptcha/docs/release-notes)
  2026-04-22 说明纳入套件且现有功能不变；2026-07-24 Policy Engine 为 Preview。
  2026-09-18 的页面更新不是新协议发布日期；不能据套件名称替换全部 reCAPTCHA API。
- **目标待证/路由**：区分旧 SiteVerify、新 Assessment、key 类型、action、reason 和规则；
  不是 Security Command Center 的同名功能。Preview 是否在目标开启另证。

## 9. Kasada

- **模块**：Bot Defense、客户端执行验证、服务端检测、AI Agent Trust Management。
- **公开证据**：[Bot Defense](https://www.kasada.io/bot-defense)
  公开描述 Invisible signal collection、Client Validation、混淆 VM / Proof of Execution 和服务端检测。
  [AI Agent Trust](https://www.kasada.io/ai-agent-trust-management)
  描述 WBA 身份强度和 HTTP method 权限。
- **日期/状态**：本轮产品文案；endpoint-level 权限仍标 coming soon。效果数字不作独立验证结果。
- **目标待证/路由**：VM 的存在只支持进入 master/AST/运行时取证，不证明 opcode、证明格式或可纯算；
  不将 Agent 身份强度与 endpoint 授权混为一项，也不把预告写成已部署。

## 10. Arkose Labs

- **模块**：Bot Manager 的风险信号、adaptive challenges 与 Global Intelligence；产品页还涉及 Titan / Agent Trust Manager。
- **公开证据**：[Bot Manager](https://www.arkoselabs.com/arkose-bot-manager/)
  支持上述产品/能力关系；本轮未核实其内部挑战算法、模型或私有参数生成。
- **日期/状态**：本轮产品文档，不作全部客户的迁移、挑战形态或新版本发布日期证明。
- **目标待证/路由**：先确认风险判定与挑战之间的升级关系，再分析实际返回题型和 token 消费；
  不能将 FunCaptcha 历史名称或某一题目等同整个 Bot Manager。

## 11. hCaptcha

- **模块**：可见/Invisible/Passive challenge、Enterprise risk score、服务端验证。
- **公开证据**：[接入](https://docs.hcaptcha.com/) 要求后端 form-urlencoded `/siteverify`，
  一次性 token、短有效期、预期 sitekey；hostname 不应用于身份认证。
  [模式](https://docs.hcaptcha.com/invisible/) 区分 Invisible（无 checkbox，可出题）与 Passive（无可见挑战）。
- **日期/状态**：本轮文档；score/Passive 等存在档位条件，测试 key 无反 Bot 保护。
- **目标待证/路由**：captcha-solver 先分支，二次校验和业务消费分别留证；不把旧 hsj/hsw recipe 当当前通用协议。

## 12. GeeTest 极验

- **模块**：行为验证第四代、风险融合、交互形态及商户二次校验；其他风控产品不自动纳入。
- **公开证据**：[服务端](https://docs.geetest.com/gt4/deploy/server) 列 `lot_number/captcha_output/pass_token/gen_time`
  和商户 `sign_token`；外层 status 与内层 result 分开，示例含请求异常放行。
  [Web API](https://docs.geetest.com/gt4/apirefer/api/web) 列 riskType/offlineCb。
- **日期/状态**：第四代接口文档，不代表第四代只有 slide 或只有某一种 w 算法。
- **目标待证/路由**：商户 HMAC 与客户端输出分开谱系；captcha-solver 检查正常校验、离线/异常分支与业务结果。

## 13. 顶象 Dingxiang

- **模块**：智能无感验证/第五代验证码、可组合的设备指纹；Dinsight 业务决策不能等同验证码。
- **公开证据**：[官方文档](https://www.dingxiang-inc.com/docs/detail/captcha)
  列设备/行为/频率/地理信号、`passByServer`、`sl` 降级 token、后端 `/api/tokenVerify`、
  一次性 2 分钟 token、可选 IP 一致性；SDK 网络容错时必须区分 `SERVER_SUCCESS`。
- **日期/状态**：当前 Web 示例引用 captcha-ui/v5；是否为目标资产和是否集成指纹模块仍待证。
- **目标待证/路由**：captcha-solver 分无交互、交互、前端降级与服务端容错；master 追踪实际 apiServer/应用与策略。

## 14. 腾讯验证码

- **模块**：有交互/无感验证码、服务端票据验证及结果中的风险字段。
- **公开证据**：[DescribeCaptchaResult](https://cloud.tencent.com/document/product/1110/36926)
  以 `CaptchaCode=1` 为通过；票据有效期 5 分钟且不可重复；code 21 中的 trerror 容灾与其他风险返回需区分。
  Score 为 0–100，越高风险越大；EvilLevel 适用无感模式。
- **日期/状态**：页面 2026-09-18 更新是文档时间，不是 API 版本更名；所列 API Version 为 2019-07-22。
- **目标待证/路由**：内外层状态、模式与 AppId/票据/Randstr/IP 逐项核对；不能因旧 TDC/PoW 样本存在就推广到所有验证形态。

## 15. 阿里云验证码

- **模块**：验证码 2.0 的无痕、一点即过、滑块、拼图、图像复原；不是阿里全部 WAF/Bot 功能。
- **公开证据**：[产品概述](https://help.aliyun.com/zh/captcha/captcha2-0/product-overview/what-is-alibaba-cloud-captcha-2)
  列设备、行为和推理形态；[服务端](https://help.aliyun.com/zh/captcha/captcha2-0/user-guide/server-integration)
  要求原样透传 CaptchaVerifyParam，区分 Success 与 Result.VerifyResult，以及 T001 真校验和 T005 测试模式。
- **日期/版本**：产品 2.0 中有客户端 V2/V3 架构，参数和 F018/F019/F020 等规则不同；
  F025 公开提到 Qwen 分析，不能据此猜模型内部实现。容灾建议不是正常验证结果。
- **目标待证/路由**：固定产品代际、客户端架构、区域、SceneId/User/CertifyID 及初始化→行为→验签状态。
  不把旧 NVC/Baxia/飞邻配方推广到当前版本。

## 16. Fingerprint

- **模块**：浏览器/设备识别、Smart Signals、服务端关联与业务规则；visitor ID 不等于登录身份。
- **公开证据**：[当前接入](https://dev.fingerprint.com/docs) 使用 v4 `event_id/visitor_id` 与 `/v4/events`；
  Smart Signals 通过服务端 API、Webhook 或 Sealed Results 取得。
  [防篡改/重放](https://docs.fingerprint.com/docs/protecting-from-client-side-tampering.md)
  要求新鲜度、一致性与消费检查，并区分业务端 event 重放和采集 payload 重放。
  [confidence](https://docs.fingerprint.com/docs/identification-accuracy-and-confidence.md)
  是识别混淆的置信，不是 Bot/欺诈分；新设备也可能为 1.0。
- **日期/版本**：本轮是 v4 文档；旧 requestId/visitorId 名称不能直接套到 v4 schema。
- **目标待证/路由**：master 分开身份、设备识别、Bot 与业务风险；密封载荷是上游结果，不能因本地可解密就称检测算法已还原。

## 未取得正文的范围

本轮瑞数官网返回 HTTP 412，未继续探测；因此不写其当前 VM、算法、型号或客户端参数结论。
阿里 WAF Bot 管理未取得可用对应正文，验证码资料不能替代其能力证据。
后续只有需要这些家族且取得公开正文/实际资产时才补分支，不用第三方印象填空。
