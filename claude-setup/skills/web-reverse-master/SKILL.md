---
name: web-reverse-master
description: >
  对已授权的 Web/JS 目标执行完整协议逆向及路线设计、样本复现和证据排错：从当前线上 bundle、SourceMap、HTTP/GraphQL/WebSocket/gRPC-Web 流量定位动态字段，经 Hook、源码、WASM 或环境取证后交付可复现实现。涉及两个以上专业域时由本 Skill 统筹；单一已知缺口使用对应专业 Skill。
---

> ⚠️ **本机环境适配（20260920 维护注）**：本机为 macOS，无 AdsPower / ida-pro-mcp / sequential-thinking，js-reverse-mcp 已换老师私改版（vendor/teacher-mcp，25 工具，含 `inject_before_load`/`trace_function`/`trace_dispatcher`/`get_dispatcher_trace`，20260922 起全局注册）。路线 A/C（AdsPower）↔ 本机路线 3（RoxyBrowser：`roxybrowser` 管 profile/代理，`roxybrowser-playwright` 管页面）；wasm 用 wabt（`wasm2wat`）。`../../../.claude/mcp.md` 本机不存在；`tools/reverse-chromium/` 文档在 `~/.claude/tools/reverse-chromium/`（内核补丁是 Windows 向，mac 路线 2 用 js-reverse-cloak 代替）。指纹/商业指纹墙场景优先 RoxyBrowser。AdsPower/RoxyBrowser 指纹深度采集实现在 `~/.claude/tools/reverse-chromium/fp_*`（fp_probe_adspower_cdp.py 对 RoxyBrowser 同样适用，传其 CDP 端口即可，见同目录 FP_SCRIPTS-README.md）。

# Web Reverse Master

负责未知或跨阶段的 Web/JS 协议逆向。目标是得到可复核的字段谱系、实现和业务证据，不是让浏览器长期代替协议客户端。

## 适用与边界

- 用于完整链路、算法尚未定位、跨流量/源码/Hook/WASM/环境层的问题。
- 仅处理用户有权测试的系统、自有应用、公开学习目标或防御性研究。
- 不协助账号滥用、凭据窃取、绕过访问控制、批量隐蔽采集或攻击生产反滥用系统。
- 仅需一种明确能力时直接使用 `captcha-solver`、`param-encryptor`、`env-patcher` 或 `ast-deobfuscation`。
- 查询既有失败模式时使用 `web-reverse-field-guide`；命中后仍由本 Skill 或专业 Skill 实施。

## 开工门槛

开始攻坚前写清六项：目标能力、最终判官、交付形态、可证伪成功标准、止损线、真实样本。没有真实请求与 input→output 对时，先采集，禁止空手猜算法。

下列结论必须有可复核证据：算法类型、字段来源、生命周期/绑定、风控、会话绑定、反调试、纯算完成。HTTP 200、可解析响应或长度正确都不等于业务成功。

需要完整协议交付或跨请求追踪字段时，按 [项目谱系契约](references/16-lineage-contract.md) 建立站点级记录：实际请求字段清单、生产者/依赖/消费者、状态变化、证据与未解项使用稳定 ID 关联。已有记录就继续更新，不每轮重建一份叙事。轻量问答、独立 AST 变换或单函数分析不强制生成完整站点记录，也不得为通过检查器伪造 HAR。

## 工具与路线契约

- 只能调用当前会话实际暴露的工具；文档中的 MCP 名称只是条件化示例。
- 浏览器动作前声明一条路线，并在同一轮保持一致：
  - **D（默认）**：Cloak + `js-reverse-mcp` attach 9222。
  - **A**：AdsPower 商业指纹/真实登录，只需轻量 Hook。
  - **C**：AdsPower + 深度调试，优先 MCP 原生连接，CDP 桥仅 fallback。
  - **No MCP**：DevTools、HAR 与本地脚本。
- 不假设不同浏览器进程共享 Cookie、存储、断点或流量；切换路线必须显式导出/导入现场。
- 路线 D 启动、attach 缓存和工具层级见 [`../../../.claude/mcp.md`](../../../.claude/mcp.md) 与 [`references/08-tool-reference.md`](references/08-tool-reference.md)。
- Cloak 的 C++ ResourceLoader 抓包、内核级 `webdriver=false`、`CLOAK_NO_DEBUGGER` 和 VM trace 能力见 [`../../../tools/reverse-chromium/CAPABILITIES.md`](../../../tools/reverse-chromium/CAPABILITIES.md)；构建与边界分别见同目录 `BUILD_NOTES.md`、`LIMITATIONS.md`。

## 核心流程

这些是按缺口选用的工作面，不是必须逐级通关的流水线：

1. **Observe**：识别当前实际加载的框架、bundle/chunk、协议载体、防护入口与所需浏览器能力。
2. **Capture**：保存关键请求的 URL、method、headers、cookies、query/body、response、initiator、调用现场与触发动作。
3. **Locate**：从参数写入点回溯调用链；按需使用 SourceMap、源码搜索、断点、Hook、AST、WASM trace 或环境对比。
4. **Plan**：区分已证实事实与待验证假设，列出产物、实验、风险和失败回退。涉及实现或实质性外部动作时先获得用户确认。
5. **Rebuild**：先写样本校验，再实现最小 signer/decrypter/request client，逐层比对输入、中间态、编码和最终字节。
6. **Judge**：由真实下游判官验收，记录业务响应、版本、工作条件、失效表现与未解析字段。

路线设计、计划模板、逐步执行、样本驱动复现和系统排错的合并方法见 [`references/10-staged-method.md`](references/10-staged-method.md)。需要完整 Phase 0–4 操作细节时再读 [`references/01-workflow.md`](references/01-workflow.md)。

## 专业能力路由

| 缺口 | 使用 |
|---|---|
| 验证码识别、轨迹、验证码内置加密与提交 | `captcha-solver` |
| 已确认算法的签名、加密、编码或参数组装 | `param-encryptor` |
| 让原始 SDK 在 Node.js/VM 中运行 | `env-patcher` |
| `_0x`、字符串表、dispatcher、控制流平坦化 | `ast-deobfuscation` |
| 已知错误码、失败模式或历史案例索引 | `web-reverse-field-guide` |

未知算法仍由本 Skill 先定位；不要把上游透传值误当成本地算法，也不要用补环境掩盖字段谱系空洞。
Turnstile、reCAPTCHA、hCaptcha 等先区分无交互、交互、评分和托管挑战模式。客户端计算、环境信号与服务端验证/签发分别建谱系；需要外部服务或浏览器时明示依赖，不把前端完成、容灾放行或测试模式成功计为正常验证通过。

遇到风控相关失败，先区分产生结果的组件及验证、策略、业务三个层次；协议与状态证据按需读下方 14，厂商/版本线索按需读 15。历史配方是候选实验，不能凭品牌、状态码或 Cookie 片段直接判因。

## 证据与停止条件

- 动态字段逐项记录来源、生成算法、生命周期/绑定和单变量实验。
- 请求清单中的常量、嵌套字段与间接 key/token 也纳入谱系；发现未知项先保留缺口和下一项区分实验。分派给专业 Skill 时传递原字段 ID、样本/资产版本和待证问题，结果回填同一记录。
- 用 `scripts/check_lineage.py` 检查支持的 HAR 请求覆盖、引用与证据完整性；按本次声明选择记录、算法或协议门槛。记录合法不等于分析完成，脚本不能证明人工填写的来源和业务解释属实。未覆盖的协议载荷保留人工验收，不由 HTTP 外层检查替代。
- 评估复现结果时分别报告格式/解析、逐字节对拍与业务判官的证据；未提供或未执行的层级标为未知/未验证，不能用一个匹配 fixture 补全整条链路。
- 完成声明至少需要 3 组非样例输入与 oracle 对拍一致；随机性和动态字段必须固定、抽离或解释。
- 同一请求同字节最多总计 3 次（含首次发送）；任一次出现漂移或随量降级就立即停止同字节重发并转维度归因，3 次均恒拒也只能说明当前请求未见随量漂移。
- 失败时一次只改变一个变量。达到线上停止条件后改做原版对照、全量流量 diff 或离线分析，不继续堆请求。
- Hook 无效时换到源码、调用栈、request writer、iframe/worker/WASM 或本地反混淆，不重复同一动作。
- 计划假设被证据推翻时更新计划并重新确认，不在执行阶段偷偷换路线。

## 交付

至少交付一个可运行产物和一条独立验证路径：协议请求脚本、signer/decrypter、Hook/trace、环境补丁或一次性取证报告。README/文档应说明入口、依赖、参数谱系、版本锚点、工作条件、失效表现和未逆清单。

启用项目谱系的任务，以 `lineage.json` 为记录真源，报告从该文件生成；收尾逐项列出已定位、已对拍、业务已验收和未验证的证据，不能用一个总进度替代。资产或证据 hash 改变后，先确定影响范围并重新取证，不仅更新 hash 来维持旧的“通过”。

## 按需参考

- [`references/02-recipes-signature.md`](references/02-recipes-signature.md)：签名、加密、编码、协议与密钥交换配方。
- [`references/03-recipes-captcha.md`](references/03-recipes-captcha.md)：验证码研究和交互取证。
- [`references/04-deobfuscation.md`](references/04-deobfuscation.md)：AST 与 JSVMP 分析。
- [`references/05-env-patching.md`](references/05-env-patching.md)：环境差异、浏览器 API 与补丁布局。
- [`references/06-project-cases.md`](references/06-project-cases.md)：历史项目模式；路径仅作案例，先确认当前仓库存在。
- [`references/07-anti-patterns.md`](references/07-anti-patterns.md)：卡住时的反模式检查。
- [`references/08-tool-reference.md`](references/08-tool-reference.md)：当前工具存在时的操作说明。
- [`references/09-external-tools.md`](references/09-external-tools.md)：外部依赖及替代路线。
- [`references/11-web-artifacts-and-protocols.md`](references/11-web-artifacts-and-protocols.md)：当前线上 bundle/SourceMap、SPA chunk、浏览器扩展、GraphQL、WebSocket、gRPC-Web 与 PCAP 协议链。
- [`references/12-evidence-hygiene.md`](references/12-evidence-hygiene.md)：HAR、HTTP、Hook、截图和对拍证据的最小化、脱敏、哈希与控制组要求。
- [`references/13-runtime-observation-and-rebuild.md`](references/13-runtime-observation-and-rebuild.md)：从 request writer、异步调用链和跨 realm 消息定位入口，并用 first divergence 驱动本地复现。
- [`references/14-risk-protocol-and-state.md`](references/14-risk-protocol-and-state.md)：多层风控归因、TLS/HTTP 传输证据、UA-CH/存储分区、票据状态、评分方向、Web Bot Auth 与 PAT；仅在相应缺口出现时读取。
- [`references/15-vendor-capability-reference.md`](references/15-vendor-capability-reference.md)：厂商模块、公开来源、版本/开放条件与目标待证项；识别产品或核对机制时读取，不作为自动执行配方。
- [`references/16-lineage-contract.md`](references/16-lineage-contract.md)：项目级字段、请求、状态与证据记录；从真实 HAR 初始化、检查漏项/失效证据、生成报告及完成声明的门槛。

## 自带脚本与验证

优先复用本 Skill 自带的 `.claude/skills/web-reverse-master/scripts/`：`verify_crypto.py`、`compare_env.py`、`env_diff.js`、`deobfuscate_strings.py`、`cdp_bridge.py`，以及 `scripts/hooks/network.js`、`scripts/hooks/cookie_header.js`、`scripts/hooks/cryptojs.js`。站点目录应按已确认任务的实际产物最小创建，不从 Skill 生成带假算法、空测试或固定 Phase 的通用脚手架。Babel AST 变换统一交给 `ast-deobfuscation`，避免两套脚本和依赖漂移。执行前验证依赖存在；新增或安装外部依赖必须先获得用户同意；Python 必须使用项目虚拟环境。

交付或修改本 Skill 后运行：

```powershell
.\venv\Scripts\python.exe .claude\skills\web-reverse-master\scripts\selftest.py
```
