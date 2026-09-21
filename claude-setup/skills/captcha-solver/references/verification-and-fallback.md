# 二次校验、token 生命周期与容灾

> 读取条件：无感或评分模式、前端显示通过但业务拒绝、token 失效、后端二次校验、SDK 容错或测试模式。
> 官方资料核对日：2026-09-19。下列是公开接口约定，不代表某个目标已启用这些能力，也不是本次线上业务测试。

## 四层证据与单独的策略状态

| 层级 | 需要记录 | 不能据此推出 |
|---|---|---|
| 前端 challenge | 模式、回调、token 发行响应、初始化/行为时间 | 商户后端已完成验证 |
| 供应商 API | HTTP、外层请求状态、内部验证结果、reason/score | 业务已接受或账户合法 |
| 商户验证策略 | 二次校验、预期 sitekey/scene/action、过期/重放检查、测试和容灾分支 | challenge 正常通过，除非验证证据也成立 |
| 业务消费 | 具体接口的业务语义、消费时间、失败原因 | 其他账号、会话、接口同样可用 |

每轮分别标 `NORMAL_VERIFIED`、`TEST_MODE`、`FALLBACK_ALLOWED`、`REJECTED`、`UNKNOWN` 中适用状态，
并单独记录 `business_accepted`。这些是报告状态，不是建议修改服务端的决策逻辑。
供应商 API 不可见时保留 `UNKNOWN`；只见 UI 或业务放行不能补填正常验证成功。
容灾、测试、缓存命中和正常验证的成功率不能混算。

## 最小生命周期记录

每个动态字段一行：字段名、来源/发行者、输入依赖、原始编码、消费者、版本、作用域、产生时间、
校验时间、消费时间、有效期证据、一次性规则、绑定条件、刷新路径、脱敏证据锚点。

- sitekey、AppId、scene、action、账户、IP、UA、会话、设备之间的关系逐项记录。
- “官方支持 IP 检查”不等于“当前目标启用 IP 检查”；是否启用必须看真实配置或获授权的单变量验证。
- 前端 SDK 回传、供应商下发和商户后端签名分开；透传值不列成本地纯算。
- 过期、重复使用、缺初始化、缺行为验证、场景不匹配是不同状态；不统一解释成签名错误。
- 不固定所有 token 的寿命为 120 秒；不向浏览器或日志暴露商户 secret、云 AccessKey。
- 需要后端凭据但未获提供时，交付接口契约与已证层级，列出缺少的判官，不能虚构二次校验。

## 已核实的家族分支

### hCaptcha

- [Developer Guide](https://docs.hcaptcha.com/)：后端 `POST https://api.hcaptcha.com/siteverify`，
  `application/x-www-form-urlencoded`；必需 `secret`、`response`，推荐 `remoteip` 和预期 `sitekey`。
  不发送 JSON；以内部 `success` 与错误码为准。
- token 一次性；当前文档 `expired-input-response` 默认 120 秒，`already-seen-response` 为已验证。
  `hostname` 来自用户浏览器，官方明确不能用于身份认证；跨 sitekey 约束用其验证参数与实际配置确认。
- [Invisible 与 Passive](https://docs.hcaptcha.com/invisible/)：Invisible 隐藏 checkbox 但可能出题；
  Passive 不显示可见题目且依赖 Enterprise risk score；不能将两个词当同义词。
- 测试 sitekey/token 仅证明测试集成可运行。Enterprise 的 score 字段、解释和策略单独记录，不能套其他厂商的方向。

### GeeTest 极验 v4

- [服务端部署](https://docs.geetest.com/gt4/deploy/server)：浏览器输出
  `lot_number/captcha_output/pass_token/gen_time`，商户后端附 `captcha_id/sign_token` 去 `/validate`。
  服务端签名公开为 `HMAC-SHA256(captcha_key, lot_number)`；这只解释商户签名，不解释客户端验证码输出。
- `status:"success"` 只表示请求状态，可能同时 `result:"fail"`；正常通过判据看 `result`。
- 当前官方示例在请求异常时填 `result:"success"`、`reason:"request geetest api fail"`。
  这是容灾示例，不能复制成研究验收标准，更不能将该分支算作正常验证通过。
- [Web API](https://docs.geetest.com/gt4/apirefer/api/web) 的 `riskType`、`offlineCb`、交互样式分别记录；
  第四代不等于固定 slide/固定加密算法，不从历史样本推断全部形态。

### 顶象

- [智能无感验证文档](https://www.dingxiang-inc.com/docs/detail/captcha)：当前 Web 入口示例为
  captcha-ui v5 的 index.js；实际资产仍须按当前目标记录 URL/hash。
- `passByServer` 是服务端判定无需交互的前端事件；`sl` 前缀 token 是前端网络异常降级标识。
  二者都不能替代后端 `/api/tokenVerify` 的证据。
- 当前文档 token 一次性、2 分钟有效；可选 IP 参数用于比较 token 发行与业务提交来源，是否启用另证。
- SDK 可能因网络容错返回 `result=true`；官方要求查看 `SERVER_SUCCESS`。
  分别留存真实服务端成功、SDK 容错、前端降级及业务结果。
- 设备指纹是可组合能力；是否实际集成指纹 SDK、等待采集及哪些字段缺失须单独确定。

### 腾讯验证码

- [DescribeCaptchaResult](https://cloud.tencent.com/document/product/1110/36926)：后端使用
  `Ticket/Randstr/UserIp/CaptchaAppId/AppSecretKey` 核查。`CaptchaCode=1` 才是该接口的验证通过。
- code 8：票据过期，文档有效期 5 分钟；9：重复使用；16：AppId 与票据不匹配。
  `retcode=0`、HTTP 200 或 SDK 调用成功都不替代 `CaptchaCode`。
- code 21 不能单码归因：文档将 `trerror` 前缀票据解释为前端容灾，非该前缀则说明为安全风险。
  只记录供应商返回原因，不仅凭此归因具体设备、算法或环境。
- `Score` 当前定义为 0–100，越高风险越大；无感模式另有 `EvilLevel`。
  记录模式、字段是否存在和商户策略，不能因 score 缺失填 0。

### 阿里云验证码 2.0

- [产品概述](https://help.aliyun.com/zh/captcha/captcha2-0/product-overview/what-is-alibaba-cloud-captcha-2)
  区分无痕、一点即过、滑块、拼图、图像复原；无痕不进入取图流程。
- [服务端接入](https://help.aliyun.com/zh/captcha/captcha2-0/user-guide/server-integration)：
  `VerifyIntelligentCaptcha` 接收原样 `CaptchaVerifyParam`。产品 2.0 下还有客户端 V2/V3 架构；
  文档示例前者是 JSON、后者是编码字符串，不能按营销版本推定参数格式。
- `Success` 表示请求成功；看 `Result.VerifyResult/VerifyCode`。T001 是服务端校验通过，
  T005 是控制台测试模式通过，二者不可混同。
- 服务端 `SceneId` 与前端场景一致，区域与 endpoint 匹配。参数不可任意解码重组后再提交。
- V3 F018：重复使用；F019：行为验证到业务验签超过 90 秒或未行为验证；
  F020：与场景/用户不匹配。V2 初始化记录期限、错误码等不能套到 V3。
- 官方针对网络、超时、服务不可用建议容灾放行，但明确不适用于正常返回 `VerifyResult=false`。
  本 Skill 不默认采用该策略；记录目标实际策略，并将容灾结果与正常验证分开。

### 托管挑战与评分产品

- Turnstile token、Cloudflare clearance、Google reCAPTCHA assessment、Bot 产品的会话 cookie
  不是同一类凭证；先确定发行者、消费者与验证 API，不能统一填 `ticket`。
- score 是产品字段，不是统一概率。记录范围、方向、reason、缺失值、档位和阈值的来源。
- 设备识别 confidence 也不是风险分数。Fingerprint 的识别置信可能在新设备上等于 1.0，
  不能由此推出用户可信、无 Bot 或交易安全。
- 当前厂商边界、版本与官方链接见
  [厂商能力参考](../../web-reverse-master/references/15-vendor-capability-reference.md)。

## 失败时的下一项实验

| 已观察现象 | 先核对 | 合法结论范围 |
|---|---|---|
| UI 通过、业务失败 | token 是否传入；后端内部结果；业务自身鉴权 | 两个层级结果不同，尚不能确定根因 |
| API 外层成功、内层失败 | 当前版本字段含义、reason、时间与绑定；沿同一请求 ID 关联本次初始化、客户端输出、二次验证参数与业务消费，比较脱敏字段摘要而非记录活凭据 | 验证未通过，不是 transport 成功即可交付 |
| SDK 成功但无供应商响应 | 异常日志、fallback 标志、测试 key/模式 | 可能策略放行，不能计正常成功 |
| 新 token 立即过期/已使用 | 校验是否先被前端、代理、日志测试消费；时间来源 | 按实际原因拆分，不能固定归因时钟偏移 |
| 评分和验证码结果冲突 | 评分域、方向、action、阈值与执行规则 | 身份、Bot、挑战和业务决策可不同 |

实验必须改变一个能区分假设的变量；先离线对照，不因本表自动重试、换账号、换 IP 或制造失败。
任何线上实验遵守当前授权和同字节最多 3 次的总上限；上限不是目标次数。
