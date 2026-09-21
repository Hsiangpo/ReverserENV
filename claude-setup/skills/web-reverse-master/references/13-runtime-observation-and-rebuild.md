# 浏览器运行时定位与本地复现

仅在请求入口未知、代码跨 iframe/Worker/service worker/扩展、异步链难追，或浏览器与 Node.js 输出不一致时读取。目标是从最终 request writer 反向建立可对拍的 checkpoint 链，而不是先对整份 bundle 做全量清洗。

## 1. 从最终写入点反向定位

先锁定真实触发动作与 request id，再从最靠近网络的写入点往上回溯：

- HTTP：`fetch`、`XMLHttpRequest.send/setRequestHeader`、`sendBeacon`、表单提交。
- WebSocket：构造 URL/subprotocol、首个 auth/setup frame、`WebSocket.send`。
- Worker/iframe/扩展：`postMessage`、`MessagePort`、runtime message、background/service-worker fetch。
- WASM：JS glue 的输入视图、export 调用、memory 写入区和返回视图。

优先读取 Network initiator、async call stack 和暂停现场；只有调用栈断裂或代码自修改时，才在窄范围包装函数或改写源码。先找到“谁写入最终字段”，再决定是否需要 AST/JSVMP 去混淆。

## 2. 建立 checkpoint 链

每个样本使用稳定 id 记录这些真实值；不存在的层可以省略，但不能用推断补值：

| checkpoint | 至少记录 |
|---|---|
| trigger | 用户动作、入口参数、调用次数、request id |
| context | time/random/cookie/storage/token/UA/指纹等实际读取值 |
| object | 序列化前对象、字段存在性、类型与 key 顺序 |
| canonical | `JSON.stringify`/query/canonical string 前后的 bytes |
| crypto | algorithm 参数、key 来源/标识、IV/nonce、输入输出 bytes |
| encoding | TextEncoder/Base64/hex/URL encoding 前后长度与 bytes |
| writer | 最终 headers/query/body/frame 和发送顺序 |
| judge | response、ack、业务状态或 oracle 输出 |

二进制值统一保存 length + hex/base64 + hash，不依赖 Console 对 `ArrayBuffer`、TypedArray 或对象的延迟渲染。对象要保留“字段缺失”和“字段值为 null/undefined”的区别。

## 3. Hook 的升级顺序

按当前缺口选择最窄观察面：

1. SourceMap/源码搜索 + Network initiator。
2. XHR/fetch/event listener breakpoint，暂停后读取参数、局部变量和 async stack。
3. 只包装一个已定位函数，使用 `Reflect.apply` 保持 `this`、返回值、异常和 Promise 语义。
4. 调用链仍断裂时才做局部源码插桩、AST 变换或 VM trace。

常见观察点：

- 组装：`JSON.stringify`、`URLSearchParams`、header setter、protobuf encoder。
- 字节：`TextEncoder/TextDecoder`、`atob/btoa`、TypedArray/DataView。
- 随机与时钟：`crypto.getRandomValues`、`Date.now`、`performance.now`。
- WebCrypto：`subtle.importKey/deriveBits/digest/sign/encrypt/decrypt`；记录 algorithm、key type/usages/extractable 和输入输出 bytes，不假设 `CryptoKey` 可导出。
- 跨 realm：`Worker`、`SharedWorker`、`MessageChannel/postMessage`、iframe、service worker、扩展 runtime port。

包装前保存原 descriptor；结束后恢复。Hook 导致调用次数、时序、对象身份、stack 或序列化结果变化时，该样本无效，改用 breakpoint 或更低侵入度观察。

## 4. 异步与跨 realm

页面、iframe、dedicated/shared worker、service worker、worklet 和扩展 service worker 是不同 execution context。每条消息至少记录 source realm、target realm、channel/type、transfer list、payload bytes、message id 与对应网络请求。

遇到 Promise 或事件链时区分：

- 函数尚未返回；
- 返回 Promise 但未 settle；
- Promise 已 settle，但 request writer 尚未触发；
- request 已发送，回调/ack/状态更新尚未发生。

不要在页面 main world 的 Hook 没命中后就断言函数不存在；先检查 worker target、iframe、isolated world、service worker 和扩展 background。

## 5. 用 first divergence 驱动复现

浏览器与本地对同一固定输入输出同名 checkpoint，按顺序比较：

```text
browser checkpoint stream
local   checkpoint stream
        -> 找到第一个 type/length/bytes/order 不同的位置
        -> 只修该位置之前的一个来源、时序或环境语义
        -> 重跑原样本和至少一个新样本
```

- 前序 checkpoint 一致、crypto 输入开始不同：先修 canonicalization/动态字段，不换算法。
- crypto 输入一致、输出不同：核对算法参数、key/IV、padding、数据类型和库语义。
- crypto 输出一致、最终请求不同：核对 Base64/URL 编码、字段顺序、header/body writer。
- 所有本地 bytes 一致但下游拒绝：检查会话、生命周期、状态机、TLS/transport 与漏掉的前置请求。
- checkpoint 在本地更早消失：检查控制流、异步推进、realm、资源回调或 Hook 自身副作用。

“不报错”“字段非空”“长度相同”都不能替代 first-divergence 对拍。

## 6. 最小交付

- request id 到 script/module/realm/function 的定位链。
- 可重复采集的 checkpoint schema 和至少一组浏览器原始记录。
- 本地复现器及 browser/local diff；明确第一个仍未闭合的 checkpoint。
- 时间、随机、storage、cookie、服务端透传、浏览器 oracle 的来源和生命周期。
- 下游业务判官及当前是格式闭合、字节闭合还是业务闭合。
