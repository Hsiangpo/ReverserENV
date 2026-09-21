# Web 交付物与协议链取证

仅在目标涉及当前线上 bundle/SourceMap、SPA 异步 chunk、浏览器扩展，或 GraphQL、WebSocket/SSE、gRPC-Web、Protobuf、自定义帧与 PCAP 时读取。本文件负责定位和证据链，不授权扫描、爆破、DoS 或越权测试。

## 1. 先锚定当前交付物

不要用仓库源码、旧压缩包或历史文章替代当前服务实际下发的资产。至少记录：

- 页面 URL、采集时间、响应缓存头、script/preload/modulepreload 列表。
- bootstrap/runtime、主 bundle、lazy route chunk、worker/service worker、asset manifest、build id。
- 每个关键资产的完整 URL、内容 hash、chunk id、加载顺序和 `sourceMappingURL`。
- SourceMap 的 `sources`、`sourcesContent` 与实际执行 bundle 的对应关系；恢复出的名称必须再由运行时 initiator 或断点命中确认。

SPA 不要只下载入口 HTML 引用的 eager bundle。优先从 runtime chunk map、asset manifest、route manifest、preload 与 Network initiator 恢复异步 chunk，再搜索 API host、路径片段、operation name、persisted query id 和参数写入点。

框架产物优先按运行时证据取，不凭文件名猜版本：

| 形态 | 优先检查 | 能回答的问题 |
|---|---|---|
| webpack/CRA | runtime chunk map、`asset-manifest.json`、动态 `import()` | lazy chunk URL、模块 id、路由与 API 基址 |
| Vite | modulepreload、`manifest.json`、动态 import 映射 | 入口到 chunk/CSS/worker 的依赖图 |
| Next.js | `__NEXT_DATA__`、build id、`_buildManifest.js`、`/_next/data/`、RSC flight 与 Server Action id | 页面数据、路由、服务端/客户端边界与动作入口 |
| Nuxt | `__NUXT__`/payload、build assets、route chunks | hydration 数据、异步路由与 API 配置 |

内容 hash 轮换后旧 `.map`/chunk 返回 404，不代表能力消失。每次复核都从当前 HTML/runtime 重新解析资产 URL，并检查 status、content-type、长度、hash 与 JSON/JS 可解析性，排除 CDN soft-404 或旧版本误配。

浏览器扩展参与 Web 签名或代理逻辑时，不只看 `manifest.json`，要恢复实际数据流：

```text
page main world
  -> content script isolated world
  -> runtime.sendMessage/connect Port
  -> MV2 background page 或 MV3 service worker/offscreen document
  -> fetch/webRequest/declarativeNetRequest/storage/nativeMessaging
```

同时记录 `permissions`、`host_permissions`、`content_scripts`、`web_accessible_resources`、`externally_connectable`、`webRequest`/`declarativeNetRequest`、`nativeMessaging`，以及 MV3 service worker 被回收后的重连/状态恢复。普通网页 JS 不因此转成独立扩展流程。

## 2. 请求与代码闭环

对每个目标字段保留一条可复核链：

```text
当前资产 URL + hash
  -> chunk/module/worker
  -> initiator/调用栈/消息桥
  -> 参数写入点与入口函数
  -> 真实请求字节
  -> 响应或业务副作用
```

生成客户端、OpenAPI、GraphQL schema 和 SourceMap 只说明“声明过什么”，不证明线上 handler 一定接受。必须捕获真实请求，并用服务端语义或可见状态变化验收。

## 3. 协议载体

### GraphQL 与 RPC

记录 endpoint、HTTP method、content-type、operation name、variables、extensions、persisted query id、版本头、认证上下文和响应 errors/data。比较声明契约与真实请求时，一次只改变一个字段；隐藏或旧 operation 必须由实际 handler 结果证明。

从 bundle 中优先找 `gql` tagged template、Apollo/Relay operation registry、persisted-query manifest 与 hash 版本。分别捕获“只发 hash”和“hash miss 后补发完整 document”的请求，不能只复现其中半段。GraphQL subscription 还要确认 `graphql-transport-ws` 或旧 `graphql-ws` subprotocol，以及 `connection_init -> ack -> subscribe -> next/error/complete` 状态。

### WebSocket 与 SSE

先恢复连接生命周期，再解释业务帧：

1. handshake/setup：path、query、cookies、authorization、`Origin`、subprotocol、upgrade/stream response。
2. auth/subscribe：首帧、channel/topic、ack、服务端分配的 session 或 cursor。
3. steady state：heartbeat、业务 push/command、顺序号、压缩与编码。
4. reconnect：重连退避、last-event-id、重新认证与重新订阅条件。

keepalive、ping/pong 或一次 `101 Switching Protocols` 不是业务成功。需要把某个帧与 UI、storage 或服务端状态变化绑定。

同时保存 `Sec-WebSocket-Protocol`、`Sec-WebSocket-Extensions`、是否启用 `permessage-deflate`、浏览器看到的解压后 payload 与线上的原始帧。若是 Engine.IO/Socket.IO，先拆外层 transport packet，再拆 namespace/event/ack：例如 `40/admin,` 是 namespace connect，`42[...]` 才是 event；不能把 query 中自造的 namespace 当作已加入。SignalR、SockJS、Phoenix Channels 也先识别其协商/封装层，再解释业务 JSON 或二进制体。

### gRPC-Web 与 Protobuf

先区分 native gRPC、gRPC-Web binary、gRPC-Web text、Connect 与普通 JSON gateway。记录 HTTP/2/HTTP/1.1、content-type、grpc-encoding、grpc-status、grpc-message、trailers、metadata 和 method path。

- 数据帧：1-byte flag + 4-byte big-endian length + message；压缩位必须与 `grpc-encoding` 一起解释。
- gRPC-Web trailer frame：高位标志通常为 `0x80`，payload 是 trailer block；HTTP 200 仍可能在这里返回非零 `grpc-status`。
- `grpc-web-text`：先把整个响应作为连续 Base64 流解码，再按帧切分；不要把网络 chunk 各自当完整 Base64 或完整消息。
- Proto wire type：0=varint、1=64-bit、2=length-delimited、5=32-bit；`sint*` 还需 ZigZag。单个样本不能区分 string/bytes/embedded message、packed repeated、map 或 oneof，必须靠多样本和生成端线索。
- 无 schema 时先保留 field number、wire type、原始 bytes、重复顺序和 unknown fields，再逐步命名；重新编码能解析不等于字节等价。

反射、descriptor、生成客户端和 OpenAPI transcoding 只能作为候选契约。最终仍要以真实客户端的 method/metadata/message 与 `grpc-status=0` 或业务状态变化闭环。

### 自定义二进制帧与 PCAP

1. 先按五元组和同一会话重组 stream，标记 C->S/S->C、重传、乱序与缺包。
2. 按消息类型对齐至少 3 个样本，制作 offset×sample 差分矩阵；用单变量动作定位长度、type/opcode、sequence、时间、对象 id 与 payload 区域。
3. 对每个候选长度字段同时验证大小端、含头/不含头、字符数/字节数；对 TLV/varint 找到下一字段边界，禁止只靠一个样本猜 offset。
4. 先排除 Base64/hex、压缩和序列化，再判断加密；高熵区附近重点找 nonce/IV、tag/MAC 与版本位，并区分逐帧密钥、连接密钥和上游下发材料。
5. 区分 TCP segmentation 与应用层分帧；禁止把不同账号、连接或会话的消息拼成一条状态链。
6. 交付最小消息字典、offset/length 表、解码脚本或 dissector，以及同会话 accepted/rejected transcript 的最早分歧。

### 请求规范化差异

只有在明确授权且确有代理/gateway/backend 多跳差异时才检查 path decode、slash/dot、大小写、duplicate header、host derivation 和 body framing。保存 baseline raw request，并一次只改变一个字节或语义维度；没有后端路由或业务效果证据时，只能报告“解析差异待验证”，不能宣称绕过。生产环境不得进行 request smuggling、队列污染或 victim 影响实验。

## 4. 最小产物

- 资产索引：URL、hash、chunk/module、SourceMap/manifest、采集时间。
- 请求索引：协议、方向、operation/message type、认证载体、状态依赖。
- 字段谱系：来源、算法、生命周期/绑定、单变量实验。
- 状态图：setup/auth/subscribe/request/ack/push/reconnect/close 中实际存在的节点。
- 判官证据：字节对拍、业务响应或可复核状态变化；未闭环部分逐项显形。

## 5. 常见误判

- 打开巨型 minified bundle 前没有检查 manifest、chunk map 和 SourceMap。
- 从恢复出的函数名直接推断线上执行路径，没有 initiator 或断点证据。
- 旧 content-hash 资产 404 就判断 SourceMap/路由已消失，没有重新解析当前 build。
- 把 schema、生成客户端、`101`、grpc-status 或可解析帧当成最终能力。
- 把 gRPC-Web trailer、Socket.IO 外层 packet 或 Base64 网络 chunk 当作业务消息。
- 忽略 heartbeat、reconnect、resubscribe 或上游 token，导致离线重放只复现了格式。
- 跨版本、跨账号、跨连接混用资产或帧，破坏上下文边界。
