# 项目级 Web 谱系契约

用于完整 HTTP 协议交付、跨请求字段依赖或持续维护的 Web 目标。目标是让每次工作都能回答：哪些字段有来源，依赖到哪里，什么实验支持结论，还缺什么。

本文件定义本项目的记录与验收约定，不是厂商协议规范。轻量问答、独立 AST 变换、单函数算法分析只使用相关字段卡和证据要求，不为运行检查器伪造请求、抓包或业务结果。

## 1. 一个记录真源，按任务确定范围

- 站点使用一个 `docs/lineage.json` 关联请求、字段、内部依赖、资产和证据。Markdown 报告从该记录生成；不得手工维护两份不同状态。
- 初始化的请求范围必须与本次目标一致。只分析一个接口时选中该接口及必要前置；未选请求不计入覆盖率，也不因检查通过变成已分析。
- 当前自动库存来自本地 HAR 的 HTTP 请求。JSON 嵌套字段、重复参数和空容器都需要保留身份；签名覆盖的 canonical bytes 另存为证据，不能从脱敏值重新拼造。
- HAR 的 WebSocket 升级请求不包含完整帧谱系；gRPC-Web/Protobuf、SSE、二进制和无法解释的载荷须继续按 [协议参考](11-web-artifacts-and-protocols.md) 建立帧/字节证据。当前检查器不证明这些载荷的内部字段覆盖，opaque 项不能直接关闭。
- 不把实际未发送或不在目标范围内的参数写进请求来凑表。内部 key、时钟、熵源、存储项作为内部依赖节点，不能伪装成已捕获的线上字段。

## 2. 每个字段必须交代的内容

| 内容 | 填写要求 |
|---|---|
| 身份 | 请求 ID、精确位置/路径；同名不同位置、重复出现与不同会话实例分别登记 |
| 来源 | 常量提取处、本地函数、环境/存储读取点、服务端下发接口或派生关系；抓包是观察位置，不能替代生产者 |
| 代码锚点 | 实际加载的资产 ID/hash、函数/行号、realm、调用或消息链；仅引用旧仓库源码不足以确认线上版本 |
| 依赖 | 精确输入节点，包含 key/IV/nonce、时间、随机源和上游 token；依赖递归追到可复核来源或明确的外部边界 |
| 变换 | 字段存在性与类型、排序、序列化、压缩、编码、算法参数和中间字节；没有变换要说明直接传递 |
| 保存与消费 | 写入位置、读取方、最终 request writer；跨 iframe/Worker 时记录消息关联 |
| 生命周期与绑定 | 产生、更新、消费、过期、刷新和作用域；未知写未知，不从相同值推导永久有效或不绑定 |
| 实现 | 对应实现文件与函数，说明纯算、原 SDK、环境采集、上游协议或 oracle 依赖 |
| 证据 | 本轮样本、资产和实验的稳定 ID；来源定位、字节对拍、生命周期及业务证据分开引用 |
| 缺口 | 尚未解释的事实，以及下一项能区分原因的实验；不能仅写“继续研究”或把猜测填成结论 |

服务端签发的不透明 token 可以在已证实的发行、保存、消费和刷新边界结束追溯，不要求推造签发服务的内部算法。来源类别只能说明实现边界，不能替代来源证据。

输入、中间串、crypto、encoding、writer 的逐层证据仍按 [checkpoint 链](13-runtime-observation-and-rebuild.md) 采集，作为本记录的证据文件关联。检查器不会自动从 bundle 推导依赖，也不会凭最终字节一致补出缺失的中间链。

## 3. 请求与状态必须对应同一次尝试

为每个请求登记触发条件、前置请求和状态变化。把请求响应中的字段写入存储，再被下一请求读取的过程落到字段依赖；不能只给一张按时间排列的 URL 清单。

- 区分 page/iframe/Worker、账号/会话/连接与资产版本；跨上下文对比必须明示差异，不能拼接成一条成功链。
- 刷新、重复挑战与重试使用新的请求/字段实例，记录依赖上一实例的关系；不把同一节点连回自身来掩盖不同生命周期。
- 仅初始化、前端产票、厂商验证、策略放行、业务消费是不同结果。验证码仍按 [二次校验与容灾](../../captcha-solver/references/verification-and-fallback.md) 分别验收，通用业务记录不能替代厂商正常验证证据。
- 生产前置与失败分支由已授权样本支持；不因表格缺项自动在线制造过期、重复消费或异常流量。

## 4. 从真实记录初始化，再逐项补证

使用项目 venv，从仓库根执行。下面 `sites/example_com` 只是命令占位，须换成当前目标的既有目录；命令不会采集网络请求。

```powershell
.\venv\Scripts\python.exe .claude\skills\web-reverse-master\scripts\check_lineage.py init --project-root sites/example_com --har assets/har/session.har --output docs/lineage.json --entries 0,2
.\venv\Scripts\python.exe .claude\skills\web-reverse-master\scripts\check_lineage.py check --project-root sites/example_com --lineage docs/lineage.json --require record
```

`--entries` 使用 HAR 的零基索引；范围应由人工确认，省略时检查工具支持的全部条目。初始化只生成观察清单与未知项，不会推断算法、key、TTL、绑定或成功。已有记录不覆盖；继续编辑原 JSON，不能反复初始化抹掉旧缺口。

所有记录内路径以及 `--har/--output/--lineage/--report` 都相对 `--project-root`。证据、资产和实现必须在该目录边界内；引用检查不会执行这些文件。原始 HAR 可能含活凭据，应遵守 [证据卫生](12-evidence-hygiene.md)，受控保存原件与脱敏映射；生成器不复制捕获值不是完整脱敏审计。

专业 Skill 接手时接收原字段 ID、固定样本/版本与待证问题；完成后更新同一记录的实现、证据与缺口。不要交回一份没有字段关联的“算法已完成”。

## 5. JSON v1 的填写位置

初始化命令生成所选请求及字段的实际结构，先使用该结果，再增加内部依赖和证据；不要从旧站点复制“全部已验证”的记录。顶层 `version` 为 `1`。

| 顶层集合 | 内容与关联 |
|---|---|
| `capture` | `artifact` 指向 HAR 的 artifact ID；`entries` 是本次选择的零基索引 |
| `artifacts` | 每项 `id/path/sha256/provenance/kind`；sha256 为小写十六进制。provenance 为 `unknown/target/fixture`，kind 为 `capture/code/evidence`。正文、源码、输入、oracle 与本地输出均用文件锚定 |
| `runs` | `id/kind`；kind 为 `unknown/target/fixture`，表示实际采样来源，不能为通过门禁任意改标签 |
| `sessions` | `id/run_id/kind/initial_state`；kind 为 `new/existing`。会话标签仍须证据支持，不是工具创建了真实新会话 |
| `requests` | `id/entry_index/predecessors/state_before/state_after/epoch/trigger/realm/session_id/evidence_ids`；ID 如 `r0` 对应已选 HAR 条目，前置关系和状态必须可追溯 |
| `nodes` | 实际发送字段与内部依赖，结构见下表；节点的 dependencies 使用节点 ID |
| `evidence` | 样本/实验记录及上下文，见下方；其 artifact 指向实际证据文件 |
| `algorithms` | 本次声明已复现的算法及对拍材料；没有算法声明时保留空数组，不填假对拍 |
| `business_targets` | 本次业务目标、判断条件和对应请求/会话/证据；没有业务结果时不编造目标验收 |

字段与内部节点使用以下结构：

| 键 | 填写方式 |
|---|---|
| `id/node_type` | 唯一 ID；node_type 为 `field` 或 `internal` |
| `request_id/location` | field 保留初始化给出的请求 ID 和 HAR 内 JSON Pointer，例如 `/headers/0/value`；internal 两者为空。不要擅自改路径来隐藏漏项 |
| `source` | `kind/producer/artifact/anchor/realm`；kind 为 `UNKNOWN/constant/local/server/derived/device`。device 包括环境读取；具体来源写入 producer、anchor 和证据 |
| `dependencies` | 输入节点 ID 列表；时间、随机、上游 key 以及必要的派生输入分别登记 |
| `transformations` | 按真实顺序列出 `{name,evidence_ids}`；不需要变换时为 `[]`，有变换时不能只写“加密处理” |
| `encoding/storage/consumer` | 说明精确字节契约、保存位置与读取/写入方；确实不适用时明确说明，不用空字符串冒充已确认 |
| `lifecycle/binding` | 各自包含 `status/description/evidence_ids`；status 为 `unknown/verified/na`。`na` 需要解释适用边界，动态票据不能仅改标签回避实验 |
| `implementation` | 未实现为 `null`；已实现为 `{artifact,symbol}`，artifact 指向当前实现文件 |
| `evidence_ids` | 与本字段相关的来源/实验记录 ID，不是随便选一个存在的文件 |
| `gaps` | `[{detail,next_experiment}]`；发现新缺口立即登记，关闭时先补相应证据 |

本地/派生字段的 source 应指向实际代码 artifact 和入口 anchor，implementation 指向复现实现。服务端下发字段的 producer 使用发行请求 ID，anchor 指向真实 HAR 条目的 `/response/...` 路径；该请求必须在消费请求的前置链中。响应路径存在只证明有该位置，字段透传或绑定关系还要对应实验。

每项 evidence 包含 `id/kind/artifact/run_id/session_id/asset_ids/asset_hashes/request_ids/details`。kind 为 `source/lifecycle/oracle/business/state`。`asset_ids` 记录该证据所依据的代码/版本，request_ids 与 session/run 记录来源；不要把不同资产、会话的结果拼成同一条验证。details 保存实验条件与结果说明，不能放活 token/key。

`asset_hashes` 是采证时的 `{artifact_id: sha256}` 快照，键覆盖本项 evidence 的 `artifact` 和全部 `asset_ids`。检查时与当前文件清单核对，所以仅修改清单 hash 不能使旧证据恢复有效。需要重新采证时增加新记录，不通过同时改写旧快照掩盖版本变化。

算法项包含：

- `id/fields`：本次明确声明已复现的输出节点。
- `conditions.random/clock`：随机、时间及其他动态条件的控制方法；不消费这些输入时明确写不适用及依据。
- `comparisons`：每组包含 `input_artifact/oracle_artifact/local_artifact/non_sample/evidence_ids`。检查器实际读取 oracle 与 local 文件比较字节，并按输入内容区分样本；`non_sample` 的真实性仍需人工复核。oracle evidence 的 `details.algorithm_id` 对应算法 ID，asset_ids 包含本组输入/oracle/local，以及声明字段及其递归依赖的全部来源和实现资产，不能给三组数据贴同一个不相关的日志。

业务项包含 `id/request_ids/criteria/evidence_ids/session_ids`。相关 business evidence 的 details 使用 `target_id/judge/accepted/observation`，judge 为 `business-semantic`；observation 应描述实际业务对象或状态变化。HTTP 状态、外层 success 或人为填入 `accepted: true` 不能自行证明真实验收。

请求的 state evidence 绑定当前 capture；无前置请求时 state_before 与 session.initial_state 对应，有前置时保持同一 session 并与前置 state_after 衔接。business evidence 的资产快照同时覆盖 capture、目标请求字段及递归依赖的来源/实现资产。

## 6. 分开验收记录、算法和协议

| 检查门槛 | 含义 | 不代表 |
|---|---|---|
| `record` | 记录格式、HAR 字段覆盖、ID/依赖/证据引用及 hash 合法；未知项仍列为 gap | 所有来源已查明或目标协议已可用 |
| `algorithm` | 明确的算法目标有闭合依赖；至少 3 组不同输入、非样例的 oracle 对拍材料，实际输出字节一致 | 业务接口接受、新会话可用、或人工标注的 oracle 来源已由机器认证 |
| `protocol` | 范围内谱系、请求状态及指定业务目标满足记录条件，具有新会话和业务语义证据 | 任意频率/账号/版本持续可用，或测试/容灾放行等同正常验证 |

输出按 `origin/byte/business/state` 四轴报告；它们分别表示相应证据的声明条件是否满足。algorithm 门槛只覆盖明确声明的字段及其依赖，其他字段仍可能 origin 未闭合。protocol 要求范围内整体闭合，且所有 local/derived 节点都被算法声明或其依赖覆盖；纯透传、确无客户端计算时允许 byte 为 `not_applicable`，不用伪造三组算法样本。

```powershell
.\venv\Scripts\python.exe .claude\skills\web-reverse-master\scripts\check_lineage.py check --project-root sites/example_com --lineage docs/lineage.json --require algorithm
.\venv\Scripts\python.exe .claude\skills\web-reverse-master\scripts\check_lineage.py check --project-root sites/example_com --lineage docs/lineage.json --require protocol --report docs/lineage-review.md
```

报告是派生产物，输出目标必须是尚不存在的新文件。保留 record 检查时的未解列表；不要把退出码 0 改写成“全部还原”。每个结论仍需人工复核对应证据及控制条件。

时间、随机和上游状态需要显式记录控制方式，不能反复给同一个输入编号冒充独立样本。真实 oracle 样本可在离线回归中使用；人为合成 fixture 可以验证检查器，却不能升级成真实目标验收证据。哈希只证明文件完整性，不证明数据来源、非样例标注和业务解释属实。

## 7. 变更和缺口如何收尾

- 检查时重新读取 HAR 字段集合，并校验证据与资产 hash；漏字段、断引用或旧证据漂移必须修正，不能从表里删掉对应行来得到通过。
- bundle、WASM、实现或上游状态变化后，沿关联字段和依赖重验；旧样本只保留为旧版本结果。更新 hash 本身不是重验。
- 工作中可以明确保留未知项；交付声明只能覆盖已证范围。分析报告或有外部依赖的阶段产物仍可交付，但不能贴上更高等级的完成标签。
- 每轮交接从同一记录生成：新增证据、仍未闭合的字段/请求、下一项区分实验、已证范围和外部依赖。缺证时给具体实验，不补想象中的值。

本工具不发网络请求、不判断厂商内部算法，也不能证明人为填写的语义结论真实。其作用是阻止遗漏、断链、证据失效和不满足记录条件的完成声明。
