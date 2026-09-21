# 补环境证据链排错

仅在 SDK 加载失败、入口挂起、输出漂移或被判“环境异常”时读取。目标是设计能区分根因的实验，不是继续堆 API。

## 先保存失败快照

每轮至少记录：SDK hash、runtime/Level、入口和输入、完整异常与 stack、最后一个已知调用点、进程是否有 pending timer/Promise、输出及下游判官。修改一项后用同一输入重跑；不要同时更换 runtime、指纹和业务参数。

## 症状速查

| 症状 | 首要假设 | 区分实验 | 一线修复 | 仍失败时 |
|---|---|---|---|---|
| `window is not defined` | 全局别名缺失 | 在 SDK 首行前断言 `window===self===globalThis` | 补 Level 1 和别名关系 | 查是否访问独立 iframe/worker realm |
| `canvas.getContext is not a function` | canvas 元素类型不对 | 记录 tag、context type、返回值消费点 | 补目标 `2d`/`webgl` context | 查状态机或真实像素输出 |
| `AudioContext not defined` | Audio API 缺失 | 记录构造参数、属性与 `startRendering` 消费方式 | 补已证实的 Audio API | 按 advanced-emulation 的渲染契约验证真实输出 |
| SDK 加载超时 | 死循环、Promise 不推进或 timer 未清理 | 分别记录同步执行截止点、pending jobs/timers | 同步 VM 预算与异步独立进程 timeout 分开；修已定位的事件语义 | 比较运行时能力，不能用空 Promise 掩盖缺口 |
| `Function.toString` 检测失败 | mock 身份暴露 | 在原检查点比较 name/length/descriptor/toString | WeakMap 登记或 Proxy 包装 | 查 bind/realm/stack/constructor 身份 |
| `navigator.userAgentData` 缺失 | Chrome 90+ UA-CH 探测 | 捕获读取字段和 `getHighEntropyValues` 参数 | 补消费字段 | 统一 UA、brands、platform 与移动标志 |
| Cookie 操作异常 | getter/setter 或作用域语义缺失 | 记录赋值串、读取时点、domain/path | 实现可见 Cookie jar | `HttpOnly` 不可由页面 JS 模拟；查上游响应 |
| `WebAssembly.instantiate` 失败 | import 名称/类型/内存限制不匹配 | 输出 `Module.imports/exports` 与实际 imports | 逐项补真实 import | 用二进制工具核对签名及 core-templates 的 realm 语义 |
| Proxy/iframe 检测 | 对象身份或子 realm 不真实 | 在检测点打印 prototype/descriptor/关系 | 补 `contentWindow` 与 prototype | 创建独立 context 或转真实浏览器 |
| 时区/语言异常 | 指纹字段混搭 | 一次打印 UA、UA-CH、Intl、Date、language、screen | 注入同一快照 | 换用真实浏览器整套快照 |
| 输出为空但无异常 | 资源回调/Promise/输入信号未发生 | 对每个 async task 记录 start/settle | 修已定位的 `onload`/事件语义 | 看 advanced-emulation 的执行阶段与状态延续 |
| 输出长度或字节不一致 | 输入构造、序列化、熵源或隐式状态差异，尚待定位 | 在实际加密入口和返回点复制字节，固定同一输入与熵源逐字节比较 | 按首个差异修复已证实的构造或状态缺口 | 看 advanced-emulation 的加密边界捕获；timer 对象不等于加密输入，等长不等于对拍通过 |

## “检测到非浏览器”排查顺序

只有错误信息模糊时使用此顺序；一旦找到具体失败调用点，立即回到该点做单变量实验。

1. 对目标真正调用的 mock 检查 `Function.prototype.toString`、`name`、`length`、descriptor 和 prototype。
2. 检查 UA 中 Chrome 版本与 `userAgentData.brands`、platform、mobile 是否一致。
3. 若读取 `navigator.plugins/mimeTypes`，校准长度、索引、named access 与 prototype；未读取则不补。
4. 检查 iframe 的 `contentWindow/contentDocument`、父子 window 关系与 realm。
5. 检查 Proxy/包装函数是否改变身份、异常栈或同步返回；核验插桩前后的原版输出。
6. 统一 `Date.getTimezoneOffset()`、`Intl` 时区与 `navigator.language/languages`。
7. 统一 screen/viewport/devicePixelRatio/colorDepth 的合理组合。
8. 对 Canvas/WebGL/Audio 做同 session 重复调用，确认结果稳定且来源一致。
9. 若 SDK 真正使用 WebSocket/Worker/MessageChannel，再按其事件顺序补；不要仅为枚举存在而造空对象。
10. 若 SDK 测 storage 配额，按调用语义补估算值；基础 get/set 通过不代表 quota 通过。

全部通过仍失败时，不要整文件重写。回到 SDK 判定分支，记录该分支的直接输入；无法获得分支证据时转 `web-reverse-master` 做 `watch()`/`env_diff`。

## 挂起与异步诊断

将“同步没返回”和“Promise 未 settle”分开：

- `vm.Script.runInContext()` 超时：先查同步循环、自校验、OOM/wasm2js 炸弹。
- SDK 函数已返回 Promise 但不 settle：查 MessageChannel、Worker、queueMicrotask、timer 和资源 load。
- timer 回调或 Promise/thenable 内部死循环会阻塞宿主 watchdog；由独立父进程 timeout 终止，不能把 `runInContext` 的同步 timeout 当作异步硬上限。
- Promise settle 但 Node 不退出：枚举未清理 interval、socket、listener；在正式加载器提供 cleanup。
- callback 在错误时点触发：对浏览器原版采集事件顺序，保持同步/微任务/宏任务层级。
- 已修已知 API 但 async 仍不推进：先定位首个未触发的事件或宿主回调，再比较运行时能力，不能按产品名称直接换环境。

## 指纹一致性诊断

用一张快照表比较 mock 与原版：

| 域 | 至少核对 |
|---|---|
| UA | userAgent、UA-CH brands/fullVersion/platform/mobile |
| 地域 | language(s)、timezone、locale、Date/Intl 输出 |
| 显示 | screen、viewport、devicePixelRatio、colorDepth |
| 硬件 | platform、cores、memory、touch、plugins |
| 图形 | Canvas 数据、WebGL vendor/renderer/extensions/limits |
| 音频 | sampleRate、channel 属性、是否消费真实浮点 buffer |
| DOM | prototype/descriptor、layout、iframe realm、事件顺序 |

同 session 内不应随机漂移。跨 session 是否轮换由目标真实行为决定；没有样本时保持固定并声明未知，不能宣称“模拟真实随机”。

## WASM 诊断

1. 先用 `WebAssembly.Module.imports()` 列出 module/name/kind，逐项核对 function/global/memory/table 类型。
2. 核对 memory initial/maximum、table element type 及共享属性。
3. 实例化后断言目标 exports 存在且类型正确，再调用 SDK glue。
4. wasm-bindgen 若检查 `global`、`self instanceof Window`、Location/HTMLElement 或 direct eval，按 [核心模板](core-templates.md) 的同-realm 约束核对当前分支。
5. 出现巨型 ArrayBuffer/OOM 或 panic 时立即终止；不要运行 wasm2js fallback 试错。

## 按证据缺口读取

| 缺口 | 读取 |
|---|---|
| btoa/二进制编码、运行时选择、WASM/glue 与 Python 桥 | [核心模板](core-templates.md) |
| currentScript、XHR/Promise/continuation、realm、渲染与加密快照 | [深度模拟](advanced-emulation.md) |
| SDK 输出已验证，票据或业务状态仍未知 | [协议与状态指南](../../web-reverse-master/references/14-risk-protocol-and-state.md) |

浏览器启动运维交给 master；本 Skill 不维护浏览器启动副本或历史配方编号路由。

## 反模式与停止线

| 不要做 | 原因 | 替代 |
|---|---|---|
| 一次补全所有 API | 扩大检测面且无法归因 | 从必经调用开始，单项递增 |
| 把通用 jsdom 当万能答案 | 依赖重、语义仍不等于浏览器 | 仅用已验证的 sdenv 路线，或手动最小 mock |
| 全局改写 `Function.prototype.toString` 却不登记 | 掩盖真实函数并破坏身份 | WeakMap 登记目标 mock，必要时 Proxy |
| 每次随机生成 Canvas/WebGL/硬件值 | 同 session 漂移直接暴露 | 注入同设备固定快照 |
| 在宿主 realm 直接执行 SDK | 污染全局且对象身份错误 | Node 内置 `vm` context |
| 不设 timeout 或不清理 timer | 死循环、活锁、进程不退出 | 同步 VM 预算 + 父进程 timeout + cleanup |
| 用空 stub 吞掉所有属性/异常 | 改变控制流并制造假成功 | 保留目标消费的类型、异常和时序 |
| 以“加载无报错”宣称完成 | 未经真实入口/判官验证 | 明确区分加载通过、能力通过、oracle |

同一错误连续三次必须停止叠加补丁并改变实验维度。若已定位字体/Audio/Canvas 输出差异，比较输入、引擎及依赖版本后选择兼容实现或显式 oracle。CF VM 或其他 SDK 在已知补丁后仍失败时，保存首个输出/事件差异及原版对照，由 master 查状态、序列化与传输；不根据 400 自动改走 Cookie 复用。
