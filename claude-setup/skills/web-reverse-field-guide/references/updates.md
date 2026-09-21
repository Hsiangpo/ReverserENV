# 历史现象与当前检查入口

仅按现象查表；E/S/C 编号保留用于兼容既有检索，不是可直接执行的厂商配方。旧案例缺少当前资产 hash、原始 trace 或部署版本时，历史原因不能替代本次证据。确认问题后交专业 Skill 实施。

## 环境与运行时：E10–E18

| 编号 | 历史检索词 / 现象 | 当前证据门槛与下一项检查 |
|---|---|---|
| E10 | async SDK、strData=-6、iv8 | 比较未决 Promise、MessageChannel、timer 与网络回调；缺哪个语义再修哪个，不按返回值固定切运行时。 |
| E11 | btoa、Latin-1、128–255 | 用相同二进制字节比较 Base64；区分 Latin-1 字节与 UTF-8 文本，超出单字节范围不得静默截断。 |
| E12 | 字体、Audio、渲染差异 | 固定调用输入及浏览器/引擎版本，比较原始输出；采样 fixture 与可生成模型分别报告。 |
| E13 | SBSD、currentScript、空 URL | 记录脚本执行上下文、currentScript 读取时刻和 URL writer；只在当前样本确有差异时补 shim。 |
| E14 | CF FO 400、payload mutation | 在真实加密入口/返回点保存不可变字节快照，逐 checkpoint 比较；长度差不证明拒绝原因。 |
| E15 | Cloak 启动但无目标页 | 核对真实 CommandLine、目标页及本轮日志；由工具入口定位参数传递，不修改业务算法。 |
| E16 | MCP fetch failed、死 ws | 浏览器存活与 MCP 缓存分别检查；按 MCP 文档处理重载，不能靠重复工具调用恢复死连接。 |
| E17 | Hook 后同步循环、toString | 对比 Hook 前后函数身份、descriptor、调用次数和副作用；包装方式必须按样本验证。 |
| E18 | VM await 不返回、ShadowDOM | 找首个未兑现异步依赖及消费者；不能从品牌或卡住现象推定缺 ShadowDOM 或纯算不可行。 |

运行时语义见 env-patcher 的 [基础环境](../../env-patcher/references/core-templates.md)、[进阶仿真](../../env-patcher/references/advanced-emulation.md) 与 [排错](../../env-patcher/references/troubleshooting.md)。
E15/E16 转 [master 工具参考](../../web-reverse-master/references/08-tool-reference.md)；跨 realm、writer、mutation 取证转 [运行时观察](../../web-reverse-master/references/13-runtime-observation-and-rebuild.md)。

## 字段、协议与签发：S8–S17

| 编号 | 历史检索词 / 现象 | 当前证据门槛与下一项检查 |
|---|---|---|
| S8 | Akamai、_abck 后缀 | 从当前入口追采集、签发和业务消费；Cookie 后缀不能作成功判官。 |
| S9 | CF、cf_clearance 未取得 | 分开 widget token、challenge、clearance 与业务 session；逐阶段核对，TTL/绑定缺证保持未知。 |
| S10 | 更换 HTTP 客户端后接受变化 | 固定可控变量，对照真实 TLS/ALPN/HTTP/header 字节；换库本身不能隔离 TLS。 |
| S11 | VMP、长时间未还原 | 对照当前字段缺口、资产版本、oracle 与成本；运行原 SDK 和独立算法还原分别交付。 |
| S12 | Kasada、DONE、ct | 先追字段首次出现于响应还是本地 writer，建立发行者/消费者/刷新链，不能把上游值猜为客户端加密。 |
| S13 | PX、sensor 编码 | 先分编码、压缩和密码学；使用当前字母表、输入与原始 payload 做往返字节验证。 |
| S14 | 京东联盟、h5st 不匹配 | 按当前 appId/SDK 追输入 DAG、padding、salt 与 token 来源，不复用搜索版或旧站点常量。 |
| S15 | cnipa、T、中间接口 | 通过当前全量请求与 writer 证明本地生成或上游下发；未见 XHR 不等于不存在异步/Worker 来源。 |
| S16 | PayPal、403/429 | 记录响应阶段、Retry-After、会话与业务结果；状态码不能证明废票或要求清票重登录。 |
| S17 | 广电、WASM/fallback glue | 固定实际加载的 WASM/glue 资产与 realm，核 imports/exports 及原始分支；转换成功不能替代入口输出对拍。 |

字段计算交 param-encryptor 的 [字节与算法](../../param-encryptor/references/crypto-primitives.md) / [参数组装](../../param-encryptor/references/assemblers.md)。
多层结果与传输对照见 [协议状态机](../../web-reverse-master/references/14-risk-protocol-and-state.md)；厂商公开条件见 [能力参考](../../web-reverse-master/references/15-vendor-capability-reference.md)。

## 验证码：C4–C12

| 编号 | 历史检索词 / 现象 | 当前证据门槛与下一项检查 |
|---|---|---|
| C4 | 顶象、4012、ac | 对齐当前版本的原始响应、输入字节、二次校验及业务消费者；单码不证明位置、算法或环境错误。 |
| C5 | rmc、5014、captchaBody | 关联真实 encrypt 调用序号、输入输出和最终提交体，逐字节定位首次差异。 |
| C6 | rmc、5011、空 id | 对照本次初始化响应、id 生命周期、加密输入与请求体；不凭旧映射修改环境字段。 |
| C7 | CaptchaFox、403、cs | 分开采集、传输、挑战和验证结果，按当前 schema 逐项核实字段，不套固定项数。 |
| C8 | PayPal、hCaptcha、40010 | 沿同一链关联挑战选择、前端结果与业务返回；旧错误码不构成跳过挑战的依据。 |
| C9 | rmc、VerifyErr、轨迹速度 | 对照题目、坐标尺度、时间单位及真实样本轨迹；不预置通用匀速/过冲参数。 |
| C10 | 数美、register.k、code 1100 | 区分会话下发值与本地派生字段；历史采样相同不能证明跨设备常量。 |
| C11 | 天御、ec51/ec0、六宫格 | 图像答案、编码、传输及票据消费分别验收；换库/状态码不能替代传输因果证据。 |
| C12 | 飞邻、deviceToken 恒定 | 从真实事件与请求 writer 追生成时刻，核任务是否消费该字段；不按品牌强制模拟交互。 |

协议状态与后端判官见 [二次校验与容灾](../../captcha-solver/references/verification-and-fallback.md)。
加密/编码见 [协议参数](../../captcha-solver/references/encryption-and-providers.md)，图像与轨迹见 [识别参考](../../captcha-solver/references/recognition-and-trajectories.md)。

上述均是下一项取证入口；历史成功率、算法常量和旧实现模板已退出运行时索引。没有当前证据时报告未验证，不从本表自动发请求。
