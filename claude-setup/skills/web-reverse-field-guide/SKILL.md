---
name: web-reverse-field-guide
description: >
  仅限已授权目标，且仅在用户明确要求查询历史案例、错误码映射，或 bundle/SourceMap、GraphQL/WebSocket/gRPC-Web/PCAP 等失败模式索引时使用。按现象给出证据门槛与下一项实验；要求定位、修复、实现或交付时转交 web-reverse-master 或对应专业 Skill。
---

# Web 逆向实战经验索引

本 Skill 只负责“现象 → 已知模式 → 证据门槛 → 下一步实验”的检索。不要把历史案例直接套成当前结论，也不要在这里生成代码或调用 MCP。

仅处理已获授权的目标；不用于账号滥用、凭据窃取、绕过访问控制、批量隐蔽采集或攻击生产反滥用系统。

## 使用流程

1. 原样记录错误码、外层/内层响应、normal/fallback/test 分支、失败阶段、输入字节是否相同、会话/分区上下文和重试次数。
2. 按下表只读取与当前现象相关的 reference；优先搜索精确错误码和 E/S/C 编号。
3. 对照案例的前置条件与证据，不满足时只能标为待验证假设。
4. 输出一个有证据锚点的根因结论，或一个能区分剩余假设的实验。
5. 将实施动作交给 `web-reverse-master` 或对应专业 Skill。

## Reference 路由

| 当前问题 | 读取 |
|---|---|
| 400/403/5014、Hook/环境/签名/验证码的基础案例 | [`references/cases.md`](references/cases.md) |
| E/S/C 失败表、正确路径、反模式、TLS/工具检查 | [`references/patterns.md`](references/patterns.md) |
| E10–E18、S8–S17、C4–C12 历史现象对应的证据检查入口 | [`references/updates.md`](references/updates.md) |
| bundle/SourceMap、GraphQL/RPC、WebSocket/SSE、PCAP 或请求规范化误判 | [`references/web-protocols.md`](references/web-protocols.md) |
| 外层成功内层失败、PAT 401、付费 402、同长不同字节、CHIPS 或身份与授权混淆 | [`references/web-protocols.md`](references/web-protocols.md) 的 R1–R7 |
| 当前挑战/签发/验证/业务状态机；厂商版本与适用条件 | 按需读 master 的 [协议状态机](../web-reverse-master/references/14-risk-protocol-and-state.md) / [厂商参考](../web-reverse-master/references/15-vendor-capability-reference.md) |

只读需要的一份；若精确编号或案例标题已确定，直接在对应文件内定位，不必加载其他案例。

## 归因纪律

- “被风控”：需要原版同环境对照也失败，并由维度轮换或冷却自愈定位。
- “反调试/反插桩”：需要浏览器调试与 Hook 工具链在已知无防护页面上自证正常，并在目标页面上稳定复现失败。
- “服务器校验/绑会话”：需要全量流量无缺块，且同输入重构请求仍被拒绝。
- “随机生成”：需要至少 3 个同输入样本仍无稳定关系。
- “已还原/纯算完成”：需要字段谱系零空洞、至少 3 组任意输入 oracle 对拍一致，并落定动态字段。

HTTP 200、响应可解析、固定长度或一次成功都不能替代业务判官。

历史案例没有当前资产 hash/原始 trace 时明确标注“未复核”；不能凭 Cookie 名、后缀、错误码或换库结果推导全产品规则。不自动清票、轮换代理、换号、重登录或付款，实验动作服从已确认范围。

## 转交规则

| 根因/任务 | 转交 |
|---|---|
| 未知或跨阶段，需要抓包、Hook、源码/WASM 定位 | `web-reverse-master` |
| 已确认算法的签名、加密和参数组装 | `param-encryptor` |
| Node.js/VM 浏览器 API 与指纹行为 | `env-patcher` |
| 验证码识别、轨迹和验证码内置加密 | `captcha-solver` |
| `_0x`、字符串表、控制流或 dispatcher | `ast-deobfuscation` |

命中案例不等于完成修复。转交时携带：现象原文、命中编号、相同点、不同点、证据缺口和建议实验。

## 输出格式

```text
现象：
命中：E/S/C/R 编号或案例标题
已满足证据：
尚缺证据：
当前结论：
下一项区分性实验：
转交：
```

如果没有匹配案例，明确写“未命中”，再交给 `web-reverse-master` 做新证据链；禁止创造不存在的编号或历史结论。
