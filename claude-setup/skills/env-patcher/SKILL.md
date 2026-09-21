---
name: env-patcher
description: >-
  仅限已授权目标。为 Node.js VM、iv8 或 sdenv 生成浏览器环境补丁，使依赖 DOM、Canvas、WebGL、Audio、WASM 或指纹 API 的 JS SDK 稳定运行。适用于“补环境/browser env/mock browser”；负责运行时选择、最小 API 补齐、指纹一致性和加载验证，不负责未知算法、验证码协议或浏览器差异取证。
---

# Env Patcher

让目标 SDK 在明确、最小、可复核的浏览器兼容层中运行。成功必须由目标 SDK 的真实入口和下游结果证明，不能用“脚本无异常”代替。

仅处理已获授权的目标；不用于账号滥用、凭据窃取、绕过访问控制、批量隐蔽采集或攻击生产反滥用系统。

## 能力边界

- 输入至少包括目标 SDK 源码或可执行文件、入口函数、期望输出；有失败时同时提供完整错误和最小复现。
- 本 Skill 负责运行时选择、缺失 API 补齐、对象身份/时序/指纹一致性、SDK 加载器和 Python 调用桥。
- 未知加密逻辑定位、`watch()`/`env_diff` 浏览器差异取证及完整协议编排交给 `web-reverse-master`。
- 已知算法的纯算实现交给 `param-encryptor`；验证码识别与提交交给 `captcha-solver`；结构性混淆先交给 `ast-deobfuscation`。
- 本 Skill 默认生成本地文件，不直接操作 MCP 或生产接口；需要从真实浏览器取值时，明确标注 oracle 依赖及其版本、会话和生命周期。

## 按需读取

只读当前问题需要的材料，避免一次加载所有模板：

| 场景 | 读取 |
|---|---|
| 运行时选择、字节语义、Level 1/2、VM/SDK/WASM/Python 桥 | [references/core-templates.md](references/core-templates.md) |
| 图形/音频、异步/currentScript/continuation、realm 与加密边界快照 | [references/advanced-emulation.md](references/advanced-emulation.md) |
| 报错、无明确异常但被判环境异常、连续失败 | [references/troubleshooting.md](references/troubleshooting.md) |
| SDK 采样、挑战票据与服务端状态的分工 | [协议与状态指南](../web-reverse-master/references/14-risk-protocol-and-state.md) |
| 厂商常驻脚本、按需挑战与公开能力边界 | [厂商参考](../web-reverse-master/references/15-vendor-capability-reference.md) |

## 工作流

### 1. 固定判官与样本

先写清楚：SDK 版本/hash、入口、输入、预期输出、当前错误，以及什么结果算通过。没有真实 input→output 或可调用入口时，只能做需求盘点，不能宣称补环境完成。

### 2. 建立 API 与执行语义清单

从源码和运行错误同时取证，至少记录：

- `window/self/globalThis/top/parent/frames` 的引用关系；`document/navigator/screen/location/storage` 的属性与 descriptor。
- DOM 创建、查询、事件、资源 `src/onload`、iframe `contentWindow`、Cookie 与 CSSOM。
- Canvas/WebGL/Audio、字体/layout、时区、语言、UA/UA-CH、plugins 等指纹面。
- Promise、microtask、timer、RAF、Worker/MessageChannel 等异步推进方式。
- `WebAssembly` 加载方式、imports、exports、memory/table，以及 `instanceof`/realm/direct-eval 要求。
- 每项标为“必经调用 / 条件分支 / 探测项”，并注明返回类型、对象身份、同步或异步。

API 清单完成后再选运行方案。不能仅凭首个 `ReferenceError` 就开始堆 mock。

### 诊断记录

编码前保留一份紧凑记录，后续每个补丁都应能回指其中一行：

| 项 | 必填内容 |
|---|---|
| 判官 | 哪个入口、输出或服务端语义决定成功 |
| 版本 | SDK 路径、版本/hash、Node/iv8/sdenv 版本 |
| 失败点 | 异常 stack 或具体环境判定分支 |
| API | 调用点、返回语义、时序、对象身份、必经/条件 |
| 路线 | 所选 Level、选择证据、明确排除的更低成本路线 |
| oracle | 采集来源、绑定维度、生命周期和可替换性 |

这份记录可以放入既有 notes 或最终 manifest，不要求额外创建项目文件。

### 3. 选择最低可行 Level

按必经 API、对象身份和事件推进能力选择运行时；兼容性与字节边界见 [核心模板](references/core-templates.md)，不按 SDK 家族机械选 Level。

| Level | 选择条件 | 做法 |
|---|---|---|
| 0 / iv8 | VMP/强混淆但核心同步 | 跑原版；只修 iv8 兼容点 |
| 0 / sdenv | async 采集、需较真实 DOM | 跑原版；处理事件循环和 no-layout 差异 |
| 0 / 真实浏览器取值 | 已确认当前运行时缺少目标消费的精确渲染或托管状态 | 建立输入→输出对照；采集或保留 CDP oracle 时明示依赖 |
| 1 | 仅基础全局、DOM、navigator、storage、timer | 使用最小基础模板 |
| 2 | 还需要 Canvas/WebGL/Audio/Event/CSSOM | 在 Level 1 上按调用清单增量补齐 |
| 3 | 已有 SDK 专用模板、WASM/webpack/复杂状态机 | 复用专用实现，不另造一份 |

不要把通用 `jsdom` 当成万能补丁；已验证的 sdenv Level 0 是例外。选定 Level 后记录理由和未覆盖项。

### 4. 实现最小兼容层

先读对应 reference，只实现必经调用和已证实探测项。每增加一项都记录触发证据、返回语义与验证方法；不要凭 API 名批量补全。

必须保持：

- 使用 Node 内置 `vm`，禁止 `vm2`；同步加载、入口和输出序列化设 10 秒预算。异步死循环需独立进程及父进程 timeout，不能把 context 或宿主 watchdog 当作硬隔离。
- `window/self/globalThis/top/parent`、prototype、realm 与 `instanceof` 关系符合目标检查。
- mock 的类型、property descriptor、异常行为和同步/异步时序与消费方一致。
- SDK 检查到的 mock 函数保持原生外观；优先包装或 Proxy，不直接改写会被 `toString()` 校验的函数。
- 同一 session 的 Canvas/WebGL/Audio、UA/UA-CH、语言/时区、screen 等值稳定且相互一致；真实物理量不得用随机值冒充。
- WASM 依据真实 imports 逐项实现，并验证所需 exports；检测到 OOM 炸弹时不运行 wasm2js fallback。
- 定时器有上限且可清理；不得用会饿死 timer 的递归 microtask stub。

### 5. 用真实入口闭环

按同一输入依次记录：SDK 加载、入口调用、输出结构/长度/关键字段及下游判官结果。修改前后做单变量对照；需要字节一致时保存 golden 并逐字节比较。

结果分级：

- **加载通过**：SDK 与入口可执行，但尚无业务判官；只能这样表述。
- **向量通过**：预定输入与 oracle 逐字节一致；结构/长度检查只能标为结构通过。
- **业务通过**：下游服务按预定义语义接受目标请求；与向量通过分别记录。
- **oracle 方案**：依赖真实浏览器采集；必须显式说明依赖和失效条件，不能称纯算。

## 门控与停止条件

- API 清单未覆盖必经调用、返回类型未知或没有真实入口：停止编码，补证据。
- `browser.js` 生成后先逐项对照 API 清单；缺项或语义不明不得进入加载验证。
- 同一错误连续三次：停止补丁叠加，读 `references/troubleshooting.md`，回到调用点、对象身份、异步时序或运行路线做区分实验。
- 发现精确字体、Audio/Canvas 渲染差异时，停止用近似常量冒充实测值；比较调用输入、渲染引擎和依赖版本，再选择兼容实现或明确的 oracle。出现渲染 API 本身不能证明不可复现。
- CF VM 或其他 SDK 的已知补丁应用后仍失败：保存首个输出/时序差异与响应，由 master 重新定位状态、序列化或传输缺口；不根据 400 自动选择 Cookie 复用。
- 仅 HTTP 200、脚本无异常或字段非空都不是补环境完成；以预先定义的 SDK/协议判官为准。

## 交付

按任务需要交付，不机械生成空文件：

- `browser.js`：最小环境补丁，按领域分段并标注每项来源。
- `call_sdk.js`：固定 SDK 加载、入口、超时、参数和 JSON 输出协议。
- Python 桥：仅当主流程需要，使用项目 venv 调用 Node，检查退出码、stderr、timeout 和 JSON schema。
- `env-manifest.md` 或等价说明：SDK 版本/hash、运行 Level、API→来源→语义→验证、固定指纹来源、oracle 依赖、未补项与失效表现。
- 验证证据：至少一组真实 input→output；若宣称稳定或一致，按目标要求提供多组 golden、重复运行或服务端语义结果。

完成前确认：文件可独立运行、依赖最小、没有隐藏浏览器调用、没有把抓包动态值硬编码成算法、临时诊断代码已与正式补丁分离。
