# Web 交付物与协议失败模式

本索引只用于把现象映射到证据缺口和下一项实验。需要实际抓包、Hook、复现或修复时转 `web-reverse-master`。

风控/挑战完整状态机见 [master 协议参考](../../web-reverse-master/references/14-risk-protocol-and-state.md)，厂商日期与版本条件见 [厂商参考](../../web-reverse-master/references/15-vendor-capability-reference.md)。R1–R7 是本索引编号，与 E/S/C 历史案例编号分开。

## R1：外层 success，内层判定失败

**现象**：HTTP 200、RPC envelope `success:true` 或上传接受，但嵌套风险结果、挑战验证或业务响应拒绝。

**证据门槛**：原始响应结构、各层字段路径/消费者、request ID 与后续动作；明确哪个字段仅表示接收/解析成功。

**下一项实验**：沿同一请求 ID 跟踪外层处理、内层判分、凭证签发和业务消费，找到首个拒绝状态。不能把一个 `success` 字段汇总成端到端成功。

## R2：fallback/test 与正常路径混算

**现象**：测试 key、fallback、降级服务或 fail-open 返回了可解析 token/允许结果，被计入正常通过率。

**证据门槛**：key/模式类型、配置、响应中的模式/降级原因、原始 SDK 分支及下游处理；不在日志中暴露活密钥。

**下一项实验**：按 normal/test/fallback 分别统计并检验消费者语义。若无法确认模式就标未知，不通过清状态或换 key 强行重走；任何正常模式对照须在已确认范围内。

## R3：PAT / Privacy Pass 的 401 被误判为登录过期

**现象**：资源或验证接口返回 401，响应可能包含 `WWW-Authenticate: PrivateToken`，随后有 attestation/issuance/redemption 流程。

**证据门槛**：完整认证头、challenge 内容、客户端支持情况和后续 token redemption；仅有 401 不足以确认 PAT。

**下一项实验**：按 [RFC 9577](https://www.rfc-editor.org/rfc/rfc9577) 区分挑战下发、token 获取、提交和验证，结合浏览器日志确定停止阶段。正常协商分支不触发自动清 Cookie 或重登录。

Cloudflare 的 PAT 获取 401 可以是客户端不支持或无法取得 PAT 的正常分支，后续仍可完成标准挑战；见 [PAT 官方说明](https://developers.cloudflare.com/cloudflare-challenges/reference/private-access-tokens/)。这不意味着任意 401 都属于 PAT，仍需关联具体请求阶段与最终业务结果。

## R4：HTTP 402 是付费访问分支

**现象**：AI crawler/agent 访问收到 402，携带定价、支付网络或付款授权说明。

**证据门槛**：实际响应、厂商配置/文档版本、资源范围和价格/支付字段；402 本身不证明具体协议，也不证明 Bot 判负。

**下一项实验**：仅解析已取得的挑战与付款条件，记录业务仍未授权。付款、钱包签名、发送支付凭证不属于普通协议取证授权。

## R5：同长度被当成同字节

**现象**：body/token/ciphertext 长度相同，或都可解码，被声称算法对拍通过。

**证据门槛**：同输入/同状态下每个 checkpoint 的 type、encoding、length、raw bytes/hash，必要时解码压缩后的原始字节。

**下一项实验**：逐点比较 canonical bytes、加密输入输出及最终编码，定位 first divergence；随机量明确固定或由相同 oracle 输入控制。长度相等只用于排查结构，不能替代逐字节一致。

## R6：CHIPS / Cookie 分区上下文在迁移中丢失

**现象**：Cookie name/value 相同，浏览器可用而 HTTP 客户端、另一 iframe 或顶层页面失效。

**证据门槛**：Set-Cookie 与实际发送 Cookie、domain/path、Secure/HttpOnly/SameSite、Partitioned、top-level site、frame origin、partition key、browser context 与生命周期。

**下一项实验**：先离线比较存储/发送条件及 CookieJar 表达能力。普通 name/value 导出不能证明保存了 CHIPS 上下文，不能因此断言 TLS/IP 绑定；保留原 profile，不默认清票。

## R7：身份认证成功被当成访问授权

**现象**：WBA 签名验证、verified bot 标签或挑战凭证验证成功，但资源访问仍拒绝或要求付费。

**证据门槛**：签名覆盖字段、key/profile、验证结果，及后续 ACL/策略/付费/业务判定；认证与业务结果分别记录。

**下一项实验**：按实际策略优先级定位拒绝发生点；在自有日志中区分“身份已验证”和“该资源获准”。不因签名有效推断可以跳过授权，不把策略拒绝回写成签名算法错误。

## 当前 bundle 与恢复源码不一致

**现象**：从源码仓库或 SourceMap 找到函数，但断点不命中，线上参数也对不上。

**证据门槛**：当前页面 script/preload/manifest、bundle URL/hash、chunk id、SourceMap 对应关系和 runtime initiator。

**下一项实验**：从当前 runtime/asset manifest 恢复 lazy chunk，按 Network initiator 定位实际执行 module；不要继续在旧源码上补丁。

## 旧 SourceMap/Chunk 404，被误判为已经消失

**现象**：历史 `.map` 或 content-hash chunk 返回 404，但当前页面仍有同类逻辑。

**证据门槛**：当前 HTML/runtime 的 build id、资产 URL、status、content-type、长度、hash，以及响应是否为 CDN soft-404。

**下一项实验**：从当前 build 重新解析 chunk/map URL 后再验证；不要拿旧 hash 的 404 证明功能已移除。

## SPA 只找到入口接口，隐藏路由缺失

**现象**：HTML 与 main bundle 里接口很少，但页面操作时持续出现未知 API。

**证据门槛**：runtime chunk map、route manifest、异步 chunk 请求和对应 initiator。

**下一项实验**：枚举当前版本 lazy chunk，搜索 API host、路径片段、operation name 与参数 writer；禁止用历史 bundle 补齐当前链路。

## GraphQL/OpenAPI 契约与线上行为漂移

**现象**：schema、生成客户端或 OpenAPI 声明某字段/operation，但真实请求拒绝或走另一 handler。

**证据门槛**：契约版本、真实 method/path/operation/variables/版本头、认证上下文和服务端业务响应。

**下一项实验**：以真实成功请求为 baseline，一次只替换 operation、persisted query id 或版本维度之一，定位差异发生在客户端组装、gateway 还是 backend handler。

## WebSocket/SSE 只有连接成功，没有业务结果

**现象**：拿到 `101`、SSE stream 或持续 heartbeat，却无法复现订阅和业务 push。

**证据门槛**：handshake/setup、auth/subscribe、ack、业务帧、heartbeat、reconnect/resubscribe 与最终 UI/服务端状态的同会话链。

**下一项实验**：从一次真实成功会话切出最小状态机，逐项验证首帧 token、channel/topic、sequence 和重连 cursor；不要把 ping/pong 当业务协议。

## gRPC/gRPC-Web 可解析但业务不闭合

**现象**：能识别 5-byte frame、descriptor 或 grpc-status，但调用没有预期语义。

**证据门槛**：transport 类型、method path、content-type、压缩标志、消息/尾帧边界、metadata/auth 和业务响应。

**下一项实验**：对照真实客户端的同 method 同消息，先确认 message schema 与 metadata，再做字段级 byte diff；descriptor 不能替代线上接受证据。

## PCAP/自定义帧重放不稳定

**现象**：单帧看似解码正确，拼接或重放后服务端拒绝。

**证据门槛**：同一五元组/连接、stream 重组、方向、sequence、重传、握手、checksum/MAC、nonce 与上游状态。

**下一项实验**：排除 TCP segmentation 与跨会话混帧，按 accepted/rejected transcript 找最早分歧；先闭合 framing 和状态依赖，再讨论加密。

## 浏览器有输出，本地复现无异常但字节不一致

**现象**：入口在 Node.js/VM 中可以运行，结果结构也正确，但最终 sign/body/frame 与浏览器不同。

**证据门槛**：同一输入下两端的入口参数、上下文来源、序列化前对象、canonical bytes、加密输入输出和最终编码；每个 checkpoint 同时记录 type、length、hex/hash。

**下一项实验**：按 checkpoint 顺序找 first divergence，只修第一个分歧的来源、时序或环境语义，再用原样本和新样本回归；不要从最终密文反向盲猜。

## 代理与后端解析不一致

**现象**：路径、重复 header 或 body framing 在不同观察点呈现不同结果。

**证据门槛**：baseline raw request、单一差异请求、各 hop 的解析/路由证据与最终业务效果。

**下一项实验**：只在明确授权的隔离环境改变一个规范化维度，定位 front proxy、gateway 或 backend 的首个分歧。没有最终 effect 时只能记录解析差异；不得在生产环境做 smuggling 或 victim 影响实验。

## 证据含活凭据或跨上下文拼接

**现象**：HAR/日志含 Cookie、JWT、PII，或成功链混用了不同版本、账号、会话和连接。

**证据门槛**：原件 hash、脱敏副本 hash、占位符映射、采集上下文和 baseline/variant/same-run/judge。

**下一项实验**：保留受控原件，生成结构化脱敏副本；重新采集同一上下文控制组，不能用跨上下文材料证明字段因果。
