# Android Skills / MCP / Rules 维护手册与更新日志

> 本文是本仓库 Skills、MCP、Rules 的唯一维护手册和追加式更新时间线。只覆盖 Android 逆向，不扩展到其他平台、通用 Web、CTF 或渗透工作流。易漂移的版本、工具数和测试计数只写入带时间的记录，不作为永久现状。

## 唯一真源与发现拓扑

### 三类真源

| 内容 | 唯一编辑源 | 派生物 |
|---|---|---|
| Skills | `.claude/skills/` | `.agents/skills/` 唯一受控物理镜像 |
| MCP | 根 `.mcp.json` | `.cursor/mcp.json`、`.codex/config.toml`、`.grok/config.toml` |
| Rules | 根 `CLAUDE.md` | 根 `AGENTS.md` 仅作薄入口，不复制事实 |

`.zcode/memory/` 是独立项目记忆，不是 Rules 或更新日志。只有用户明确要求时才修改；其中历史拓扑记录不得覆盖本文和当前代码。

### Runtime 的有效 Skill 入口

| Runtime | 有效项目入口 | 约束 |
|---|---|---|
| Claude | `.claude/skills/` | 直接使用真源 |
| Codex | `.agents/skills/` | 不创建 `.codex/skills` |
| ZCode | `.agents/skills/` | 不创建 `.zcode/skills`，否则同名项会全部展示 |
| Qoder | `.agents/skills/` | 不创建 `.qoder/skills`，否则与 Agents store 重复 |
| Pi | `.agents/skills/` 自动发现 | `.pi/settings.json` 不再显式追加 `.claude/skills` |
| Cursor | `.claude/skills/` 为同名 winner | 会兼容扫描 `.agents`，但按规范化 Skill 键去重；不再创建其他 alias |
| Grok | `.agents/skills/`（同名有效来源） | 当前按名称去重；不创建 `.grok/skills`，用户级兼容合并另行审计 |

仓库允许存在的物理 Skill 根只有 `.claude/skills/` 与 `.agents/skills/`。以下路径出现即视为回归：

```text
.codex/skills
.cursor/skills
.grok/skills
.qoder/skills
.zcode/skills
```

### 为什么以前会显示双份

- ZCode 同时扫描项目 `.zcode/skills` 与 `.agents/skills`，不会按名称隐藏重复项；旧拓扑在两处都同步了相同六项。
- Qoder 把 `.qoder/skills` 与 `.agents/skills` 都当项目 store；旧拓扑也同时保存了两份。
- Pi 已自动扫描 `.agents/skills`，旧 `.pi/settings.json` 又显式加入 `.claude/skills`，形成同名 collision。
- `.codex/.cursor/.grok/skills` junction 虽不一定造成运行时重复，也会在文件树、Git 索引或兼容扫描中制造第二路径和维护歧义。
- 旧同步器默认目标是 `agents qoder zcode`，因此即使人工删除，下一次同步仍会重新生成。

本轮修复同时删除重复根、收窄同步器、增加 fail-closed 测试；只删目录而不改同步器不算修复完成。

磁盘上仍会看到 `.claude/skills` 和 `.agents/skills` 两个根，这是兼容不同发现规范所需的“一个真源 + 一个生成镜像”，不是两套可分别维护的 Skill。以后只编辑 `.claude`，`.agents` 由同步器覆盖；若某个 UI 仍把同名项列两次，先看 source path，再重启/Reload 清缓存，禁止再复制第三份。

Grok 还可能把 `.claude/commands/*.md`、用户级 Claude Skills 和自带 Skills 显示在统一列表里。这些名称与六个受控项目 Skill 不同，不属于镜像重复；2026-09-05 的脱敏 `grok inspect --json` 已确认六个受控名称各 1 个、winner 均为 `.agents/skills`。是否关闭用户级兼容扫描属于全局 Grok 配置选择，不由本项目同步脚本暗改。

## 标准更新流程

### 1. 更新前固定边界

1. 完整读取 `CLAUDE.md`、目标 `SKILL.md`、相关 `test-prompts.json`、实现和测试。
2. 记录分支、`git status --short`、目标文件 diff、行数、hash 和 BOM；脏树中只改可定位 hunk。
3. 一句话写清目标、真实判官、成功标准、止损线和是否需要真机。
4. 只吸收能改变当前 Android 决策且可由本仓库工具验证的内容；不为评分新增重复 Skill、MCP 或大段案例。

### 2. 修改真源

- Skill：只改 `.claude/skills/<name>/`。
- MCP：只改 `.mcp.json`；自建 MCP 实现只在 `android_mcp/` 修改。
- Rules：事实只改 `CLAUDE.md`；`AGENTS.md` 维持薄入口。
- 更新说明：在本文末尾追加一条带 `Asia/Shanghai` 时区的记录。
- 禁止直接编辑 `.agents/skills`、生成的 MCP 配置或历史 Memory 来制造“同步成功”。

### 3. 同步

```powershell
python .claude\scripts\sync_shared_skills.py
python .claude\scripts\sync_mcp_mirrors.py
```

旧的 `codex`、`qoder`、`zcode` Skill 参数仅为兼容别名，均写入 `.agents/skills`。`zcode --memory` 仍只在用户明确要求同步 Memory 时使用；不得加入常规维护命令。

一键包装器：

```powershell
powershell -ExecutionPolicy Bypass -File .claude\scripts\apply_optimization.ps1
```

### 4. 验证

最低验证集：

```powershell
python -m unittest discover -s android_mcp/tests -p "test_*.py" -v
python android_mcp/tests/smoke_test_mcp.py
python .claude\scripts\sync_shared_skills.py --dry-run
python .claude\scripts\sync_mcp_mirrors.py --dry-run
git diff --check
```

还必须检查：

- 六个真源 Skill 的 frontmatter、`test-prompts.json`、路径引用与 UTF-8 无 BOM 检查均通过。当前 Codex 主机可追加运行 `python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .claude\skills\<name>`；Windows 中文文件必须带 `-X utf8`，且外部校验器不存在时以仓库单测为准，不虚写结果。
- `.agents` 与真源只存在允许的运行路径替换，资源逐字节一致。
- 五个禁止的 Skill 根都不存在；每个 runtime 的项目 Skill 名称无重复。
- 根 MCP inventory 与三份项目镜像名称/参数一致，JSON/TOML 可解析且无重复键。
- Rules 只有 `CLAUDE.md` 真源与 `AGENTS.md` 薄入口，没有 vendor rule 副本。
- 修改设备控制、Root、Frida 或网络恢复实现时才重跑低风险真机回归；只改文档和发现拓扑时不拿旧真机报告冒充本轮实测。

Runtime 复核建议：

- ZCode 0.16.x：新进程运行 `node "<LOCAL_TOOL_PATH>" --cwd "<repo>" skills list --json`，只统计 `scope=project` 的名称与来源；必要时再在 Settings → Skills 或 `/skill` 核对 UI 缓存。
- Qoder：重启/Reload 后在项目 Skill inventory 中核对每个名称只有一个来源。
- Pi：重启后确认 collision 为零，来源只剩自动发现的 `.agents/skills`。
- Grok：`grok inspect --json`，只输出经脱敏的 Skill 名/来源和 MCP 名/来源，不打印 MCP 环境变量。项目 `.grok/config.toml` 只承载原生 MCP 表；1.0.x 的兼容开关来自用户级配置，额外全局项只标记为外部合并，不暗改。
- Cursor：Reload Window 后核对 Settings/Skills；运行时代码会按规范化键合并 `.claude` 与 `.agents` 同路径项。
- Codex：新任务核对项目 Skill locator 来自 `.agents/skills`。

### 5. 重载与验收边界

写入成功不等于运行时已刷新。ZCode、Qoder、Pi、Cursor、Grok、Codex 必须使用各自的 Reload、重启或新任务验证；无法 fresh-runtime 验证的项标 `未验证`，不能写成已修复。

MCP 状态使用 `implemented / adapter / declared / documented / absent / online / validated`。配置存在只算 `declared`；握手、HTTP 200、工具数或旧报告不能替代当前功能验收。

## 常见故障与处理

| 现象 | 判定 | 处理 |
|---|---|---|
| 同名 Skill 出现两次 | 先列出每项 `name + source path` | 删除多余 runtime root，运行同步器和 fresh-runtime 复核 |
| 删除后又出现 | 同步脚本或 junction 在重建 | 检查 `DEPRECATED_SKILL_ROOTS` 与 MCP 同步器，不手修镜像 |
| `.agents` 与真源漂移 | hash/允许路径替换不一致 | 从真源重新同步一次；仍失败则停止，不双边修改 |
| 中文 frontmatter 失效 | BOM 或错误代码页 | 用 UTF-8 no-BOM；禁止 `Get-Content -Raw` 参与读写 |
| MCP 名称变多 | runtime 合并了用户级或兼容配置 | 区分项目/全局来源，先做脱敏只读审计；不得暗改全局配置 |
| Rules 内容冲突 | 同时加载多个 vendor rule | 删除 vendor 副本，以 `CLAUDE.md` 为事实、`AGENTS.md` 为薄入口 |
| UI 仍显示旧项 | 缓存/旧进程 | 保存文件后 Reload 或新进程复核；不要靠再复制一份解决 |

## 回滚原则

- 先保存目标 diff；只反向应用本轮 hunk，不使用 `git reset --hard`、stash 或整树 checkout。
- `.agents` 同步失败：保留 `.claude` 真源，修复同步器后重跑；禁止以镜像覆盖真源。
- MCP 生成失败：`sync_mcp_mirrors.py` 必须整组恢复三份旧配置，再报告失败。
- runtime root 误删：先确认它是否属于本文禁止列表；只从真源重建 `.agents`，不要恢复旧多镜像拓扑。
- 真机状态变化：按测试前记录精确恢复 proxy/NAT/forward、前台 App、远端临时文件和相关进程，再停止后续动态测试。

## 更新记录模板

复制以下模板追加到本文末尾；不得覆盖旧记录：

```markdown
### YYYY-MM-DD HH:mm:ss +08:00 — 标题

- 时间（Asia/Shanghai）：YYYY-MM-DD HH:mm:ss +08:00
- 触发原因：
- 范围与真源：
- 具体变更：
- 新增/删除：
- 为什么这样改：
- 修改前后：行数、入口数或行为差异
- 验证结果：命令、通过/失败数、报告路径
- 同步与重载：各 runtime 状态
- 真机与恢复：未运行也要明确写“未运行及原因”
- 回滚方式：
- 未验证项：
- 未触碰范围：
- 决定：KEEP / REVERT / PARTIAL
```

## 历史更新记录

### 2026-06-17 — Round 1：旧 Skills 全量整理

- 对四个 Android 任务 Skill 做首轮结构整理并建立 Claude 真源到 Agents 镜像的规则。
- 当时仍保留多 runtime 物理副本，且记录混入后来排除的非 Android 材料；拓扑与评分均已被 2026-09-05 的记录取代。
- 状态：`SUPERSEDED`，仅保留日期与迁移脉络。

### 2026-08-18 — Round 2 / 2.1：Android 经验蒸馏与 MCP 对齐

- 将设备、Frida、Root 文件属主、抓包和签名失败模式归入对应现有 Skill，未新增任务入口。
- 补齐 `root_push_file` 的祖先属主继承和嵌套目录处理，并增加回归。
- 当时仍把日志和 Skill 同步到多个 runtime 根；此做法已被本手册的单镜像拓扑取代。
- 状态：部分事实保留，旧同步方式 `SUPERSEDED`。

### 2026-09-05 — Round 3：wagnganskills Android-only 蒸馏

- 只筛选 APK/DEX/ART/JNI/SO、静态分析、Frida 和 Android 协议相关内容，拒绝重复大包和非 Android 工作流；新增任务 Skill 与 MCP 均为零。
- 原记录中的旧评分、入口数、MCP 数和早期真机报告已由 Round 3.1 纠偏。
- 状态：`SUPERSEDED by Round 3.1`。

### 2026-09-05 22:59:35 +08:00 — Round 3.1：全面纠偏与当前基线

- 时间（Asia/Shanghai）：2026-09-05 22:59:35 +08:00
- 触发原因：全面梳理 Claude 真源 Skills、MCP、Rules、同步器和 Android MCP，修复假成功与权限误阻塞。
- 具体变更：收敛为四个任务 Skill 加两个维护 Skill；修复伪 DEX、未知壳误升 Frida、预检后继续、split 清单、输出覆盖、PID identity 等失败分支；项目 MCP 收敛到七个。
- 验证结果：当轮记录为 unittest 52/52、六项 quick validation、自建 MCP stdio 100 个工具零重名；真机 23/23，报告 `android_mcp/_work/test_reports/frida_orchestrator_live_20260905_221445.json`。
- 边界：独立行为评审仍为 `dry_run`；未启动四个辅助 MCP 的业务流，不称 `validated`。
- 状态：KEEP；其 Skill 镜像和 Rules 拓扑被下一条记录继续修正。

### 2026-09-06 00:01:07 +08:00 — Round 3.2：单镜像、去重与维护手册

- 时间（Asia/Shanghai）：2026-09-06 00:01:07 +08:00
- 触发原因：ZCode/Qoder/Pi 显示同名 Skill 双份，且旧日志散落在 Skill 发现根中；用户要求建立可长期追加的维护文档。
- 范围与真源：只修改 Claude Skill 真源、同步脚本、项目级 MCP/Rules 派生契约和维护文档；不修改全局配置或项目 Memory。
- 具体变更：同步器收窄到 `.agents/skills` 单镜像并对多余根 fail-closed；Grok 项目镜像保持 MCP-only，并把无法由项目配置关闭的用户级兼容来源显式列为外部合并；Pi 移除第二 Skill 路径；Rules 删除 vendor 副本；旧日志迁入本文。结合 `wagnganskills` 只把 RegisterNatives 映射、RN/Hermes/Flutter/IL2CPP 指纹、APK 内证书/SAN、BCF/FLA/MBA/间接分支/VM 分诊、私有二进制 framing 反例和跨版本 SO 锚点六类增量并入现有入口，新增 Skill/MCP 均为 0。
- 新增/删除：新增本文；删除 `.codex/.cursor/.grok/.qoder/.zcode/skills`、`.grok/commands`、三个 vendor rule shim 和旧 `EVOLUTION_LOG.md`。
- 为什么这样改：旧运行时会同时发现兼容目录，仅同步内容相同不能消除重复名称、路径歧义或缓存回归。
- 修改前后：ZCode 项目项从 12/唯一 6/重复名 6 收敛为 6/6/0；Qoder 项目物理 store 从 12/6/6 收敛为 6/6/0；Pi 两个发现根的 6 个 collision 收敛为受控项目 Skill 6/6/0。磁盘物理根从多 runtime 副本收敛为 `.claude` 真源 6 项和 `.agents` 镜像 6 项，五个禁止根均不存在。
- 正文体积：六个 `SKILL.md` 合计从 2322 行降到 865 行；分别为 recon 303→117、unpack 261→144、dynamic 334→162、protocol 647→170、evolver 291→146、Darwin 486→126。条件性实现留在既有脚本/测试中，没有复制成新的大全 Skill。
- 验证结果：`unittest discover` 62/62；维护专项 36/36；`pytest` 70/70，另有 89 个 subtests；六个 Skill 以 `python -X utf8` 运行 `quick_validate.py` 为 6/6；自建 MCP 注册 smoke 为 81+8+11=100 tools、重复名 0；修改脚本 `py_compile`、RegisterNatives 生成 JS 的 `node --check`、Skill/MCP dry-run 和 Android-only 污染扫描均通过。当前未暂存工作树的 `git diff --check` 退出 0；既有暂存区仍含已经在工作树删除/改写的旧大包及其他用户改动，`git diff --cached --check` 在 62 个 staged 文件报告 2597 条旧尾随空格，退出 2，本轮未改索引，提交前必须按当前工作树重新选择暂存内容。
- 同步与重载：Skill 与 MCP 同步器各连续运行两次；54 个受控镜像文件和 3 个 MCP 镜像的 hash/mtime 变化均为 0。ZCode 0.16.x fresh CLI 为 6/6/0，来源全是 `.agents/skills`；Pi 0.84.4 真实自动发现为受控 6/6/0，另有 `pi-mcp-adapter` 自带且不同名的 `mcp-scripting`，总计 7/7/0；Grok 1.0.13 fresh inspect 为受控 6/6/0，项目 MCP 7/7/0，另合并 4 个用户级外部 MCP。Qoder 物理项目 store 为 6/6/0，但本机无可调用 CLI，UI fresh Reload 未在本轮自动化验证；Cursor/Codex 的新窗口/新任务缓存刷新同样未冒充已验证。
- 真机与恢复：低风险 Pixel 6 套件 23/23 通过，报告 `android_mcp/_work/test_reports/frida_orchestrator_live_20260905_235826.json`。测试只执行只读查询、dry-run、非 UI 广播和 `/data/local/tmp` 临时文件写读；远端临时文件与本地输入已精确清理，未改代理、模块或持久设备配置。
- 回滚方式：只反向应用 Round 3.2 hunk；保留 `.claude` 真源并重新生成唯一 `.agents` 镜像，不恢复旧多根拓扑。
- 未验证项：Qoder/Cursor/Codex 的 fresh UI 缓存；四个辅助 MCP 的具体业务流；RegisterNatives 在真实目标 App 内的回调内容仍只有生成脚本语法和静态契约测试。`analyze_device_apks.py` 的条目上限限制扫描输出，但 Python `zipfile` 会先读取 ZIP 中央目录，因此它不是对恶意超多 entry APK 的硬内存隔离。
- 已知打包风险：`.claude/skills/darwin-skill` 与镜像当前都是无 `.gitmodules` 的嵌套 gitlink，各约 9.15 MB。它不造成运行时重名，但影响体积和 fresh-clone 可复现性；由于两边嵌套仓库都有未提交修改，本轮没有破坏性改写 Git 索引。后续应单独把它 vendoring 为最小 `SKILL.md + test-prompts.json`，或移除该通用维护入口，只保留 Android 专用 `reverse-skill-evolver`。
- 外部状态：`~/.claude.json` 存在两个仅路径大小写不同的历史项目键，旧 MCP 集合不一致；Grok 还会加载一份用户级 Claude rule。它们不是项目镜像，项目同步器只脱敏审计而不暗改真实全局配置。
- 未触碰范围：用户全局 MCP/Rules、第三方账号、设备状态、`.zcode/memory/`。
- 决定：`KEEP` 当前 Android 增量、单镜像拓扑和项目 MCP/Rules 修复；`PARTIAL` 仅指上述 fresh UI、Darwin gitlink 打包及恶意 ZIP 硬隔离未完成项，禁止把它们写成已验证。

### 2026-09-06 00:46:07 +08:00 — Round 3.3：双真机基线与设备侧工具事实同步

- 时间（Asia/Shanghai）：2026-09-06 00:46:07 +08:00
- 触发原因：用户接入第二台真机 Pixel 4 XL `<ANDROID_SERIAL_P4XL>`（Android 13，印度支付矩阵机），并完成双向工具同步（P4XL→P6 11 个工具 APK + ecapture/stackplz/okhttpfind.dex 三个设备侧二进制；P6→P4XL 一云梯客户端含订阅数据 + GPay 商户版）。Skills 与 CLAUDE.md 的"唯一真机 Pixel 6"事实已过时，用户要求更新角色定义。
- 事实来源：2026-09-06 00:00-00:45 双机 live probe（`adb devices -l`、getprop、root/模块枚举、pm list/dumpsys 版本核对、P6 ecapture v1.5.1 运行自检、P4XL 一云梯启动进程核验），全程产物在 `projects/device_survey_20260906/`。
- 修改范围：CLAUDE.md 授权段与"真机与工具链"表；`.claude/skills/` 下 android-recon、android-dynamic、android-unpack、protocol-signature-reverser 四个真源 SKILL.md。`.mcp.json` 经 grep 核对不含设备事实，零改动，故未运行 MCP 镜像同步。
- 具体变更：单设备表述改为双真机（P6 主力战场机/P4XL 印度支付矩阵机+Tricky_Store/HookVIP，两台均 APatch/LSPosed root，多设备固定唯一 serial）；android-dynamic 的 description 去掉"唯一真机"，固定工具链新增两台 `new-server` 部署差异（P6 常驻/P4XL 用前先启动）与 ecapture/stackplz 设备侧配套条目；android-recon 真机基线行改双机。
- 修改前后行数：CLAUDE.md 工具链表 2 行设备/ADB → 3 行（新增"设备侧工具"行）；recon 基线 1 行→1 行（内容扩展）；dynamic 净增 1 条工具链条目；unpack/protocol 各 1 行措辞替换。四个 SKILL.md 总行数 117+144+162+170 → 118+144+164+170。
- 验证结果：`sync_shared_skills.py` 同步 4 个 Skill 至 `.agents` 镜像；diff 核对镜像与真源仅 unpack 存在预期 runtime 路径替换（`.claude\` → `.agents\`）；`.codex/.cursor/.grok/.qoder/.zcode/skills` 五个禁止根均不存在；4 个镜像均含 `<ANDROID_SERIAL_P4XL>` 事实。judge 模式：dry-run——本轮为纯事实基线同步，不改路由/工作流/判官，无行为回归集可跑，不声称行为改善。
- 脏树边界：本轮仅追加可定位 hunk，未触碰既有未提交改动；未 stash/reset；UTF-8 无 BOM。
- 回滚方式：反向应用本轮 5 个文件的 hunk 后重跑 `sync_shared_skills.py`。
- 未验证项：P4XL 的 frida `new-server` 未做启动/握手验收（本轮只读探测），其状态仍为 `implemented(P4XL)/online(P6)` 而非双机 `validated`；ecapture 在 P4XL 侧沿用 2025-12 版本未重测。
- 未触碰范围：`.zcode/memory/`、全局配置、设备状态（一云梯验证后已 force-stop 复原）。
- 决定：`KEEP`。

### 2026-09-06 21:51:11 +08:00 — Round 3.4：Claude Android 完整自包含发布包

- 时间（Asia/Shanghai）：2026-09-06 21:51:11 +08:00
- 触发原因：用户要求生成可转交其他 Windows 电脑 Claude 使用的完整版，必须自包含本仓库 3 个自建 Android MCP、完整 Skills 与 Rules。
- 范围与真源：不改 6 个 Skill、根 MCP 真源或设备实现；只新增 `artifacts/APPCodeObjectdemo1_claude_android_full_20260906/` 派生发布目录和最终 ZIP，并更新本日志。
- 具体内容：包含 `.claude/skills/` 六项完整内容、3 个自建 MCP 的 `common/servers/tools/tests`、约 548 MB bundled ADB/Frida/算法助手/设备工具链、`CLAUDE.md`、`AGENTS.md`、`reverse_principles.md`、维护脚本和本文；排除项目样本、账号/Token/Cookie、抓包、业务产物、历史 Memory、缓存与嵌套 `.git`。
- 便携处理：根 `.mcp.json` 默认只注册随包携带的 3 个自建 MCP；`setup_self_contained.ps1` 检查 Python/工具闭包、备份配置、写入接收电脑绝对路径并运行 smoke。源工作站原始 7-MCP 配置与 Rules 保存在包内 `source_snapshot/`，不作为换机运行入口。
- 修改前后：源工作区运行拓扑不变；发布目录当前约 554.3 MB、6 个 Skill、3 个便携 MCP，无 `.agents/skills` 第二入口。外部 IDA/Reqable/Playwright/js-reverse 只保留接入说明，不打包其程序本体。
- 验证结果：发布目录 `setup_self_contained.ps1 -DryRun` 通过；MCP smoke 为 81+8+11=100 tools、重复名 0；7 个 MCP 相关安全/超时/属主/WebView/Protobuf 测试文件全部通过；bundled Frida import 为 16.5.9；Skill quick validation 6/6；缓存/嵌套 Git 扫描 0。
- 同步与重载：未运行 runtime 镜像同步，发布包面向 Claude，故只保留 `.claude/skills`。接收电脑 fresh Claude 启动仍需实际验证，不能把本机 dry-run 写成换机 `online/validated`。
- 真机与恢复：本轮未操作真机，因为只构建离线发布包；没有设备状态需要恢复。
- 回滚方式：删除本轮 `artifacts/APPCodeObjectdemo1_claude_android_full_20260906*` 派生产物并反向移除本日志条目；无需回滚 Skills/MCP/Rules 真源。
- 未验证项：不同 Windows/Python 安装组合、接收电脑 USB 驱动、fresh Claude MCP 启动及外部 4 个 MCP；这些必须在目标电脑单独验收。
- 决定：`KEEP` 完整自包含发布包；状态为离线结构与 MCP 注册 `validated`，跨电脑运行仍为 `未验证`。

### 2026-09-17 22:54:28 +0800 — Android 设备注册谱系与风控分层迭代

- 时间与时区：2026-09-17 22:54:28 +0800（Asia/Shanghai）。
- 触发与目标：用户要求将本轮 Android 设备注册、加密、传输与风控分析融入现有 Skills；以可复核的注册字段谱系、最小判因设计和职责边界为判官。仅做本地技能维护与离线评估，本轮不需要真机或业务请求。
- 真源与范围：修改 `.claude/skills/` 的 protocol-signature-reverser、android-recon、android-dynamic 及各自 test-prompts；不新增任务 Skill。扩充 `.claude/scripts/sync_shared_skills.py` 四项精确资源白名单，并在 `android_mcp/tests/test_skill_maintenance_scripts.py` 增加两项维护回归。唯一镜像由同步器生成。
- 内容与来源：protocol 按需加载 `references/android-device-enrollment.md`、`references/android-risk-transport.md`、`assets/device-enrollment-audit.md`、`references/enrollment-risk-cases.json`。覆盖安装/系统/SDK/服务器设备/密钥/证明/账号会话的分离、生产者→存储→消费者、TTL/刷新/撤销/重装等生命周期矩阵、一机一密、Play Integrity/Key Attestation 依赖、传输观察点和业务判官。依据本次已查阅 Android/Google 官方文档、Cloudflare JA3/JA4 定义与 IETF 协议说明；链接和复核日期留在 references，不把公开能力当目标采用证据。
- 分工：recon 只静态分诊和调用链锚点；dynamic 只窄边界运行证据；protocol 唯一负责整体谱系、状态与失败归因。unpack、Darwin、evolver 正文和其原有 prompts 未改，未引入其他平台能力。
- 纠正的行为：设备 ID 不预设本地生成或永久；硬件 API 命中/私钥不可导出不等于硬件证明或无法调用；未评估不等于恶意；JA4 相同不等于完整传输相同；一次性材料不为凑三组反复消费。独立内容评审发现“可重放”限制误及所有线上实验，已缩到重放实验，传输对照允许已授权的新鲜绑定材料或已有样本。
- 体积：recon SKILL 117→129 行；dynamic 163→174 行；protocol 170→181 行。条件性注册参考 116 行、风险参考 65 行、模板 82 行、补充场景 JSON 20 行。三份主 test-prompts 仍各 3 个场景，保留原有核心回归；补充注册用例单独按需加载。
- 基线与离线回归：改前 unittest 62/62、改后 64/64；新增两项覆盖资源精确同步/二次无改写与补充案例契约；脚本 py_compile 通过。六个 Skill quick_validate 6/6；MCP 注册 smoke 前后均 81+8+11=100、重复名 0。JSON/BOM/相对链接验证通过，20 个本地引用可达。
- 行为评审：judge 模式 `dry_run`。同一组 5 个请求分别由旧快照和当前 Skill 生成离线回答，去掉版本来源、打乱 A/B 后由未编写领域正文的独立 judge 评审。映射回版本：新版优先 3、持平 2、旧版优先 0；新版无必修问题。唯一必修项位于旧版回答，误把 access_token 透传当已证事实，保留原答作基线证据。这是有限离线情景的产物比较，不是现场 full-test，不报告百分制提升或真实业务成功。
- 同步与配置：同步 `.agents/skills`；23 个受控文件与真源（仅允许 SKILL 路径替换）一致。第二次同步 23 项 hash/mtime 均不变；五个禁止 Skill 根均不存在。同步器只清理其管理范围内的生成缓存，保留既有 Darwin gitlink。MCP 三镜像 dry-run 均 unchanged；只记录既有用户全局 Claude 历史键差异，未修改全局状态。
- 留存证据：`artifacts/skills_android_risk_20260917_223239/` 保存初始状态、分支、源文件快照/hash、改前后测试日志、两个实际回答集合、盲评输入/映射/结果、内容评审修正、最终 inventory 和 source_changes.patch。该目录为本地评估产物，不属于运行期 Skill。
- 脏树与未触碰：保留用户原有业务项目及嵌套仓库改动；未 stash/reset、未提交/推送；未修改 `.zcode/memory/`、全局记忆、根 Rules/MCP、设备状态或账户状态。
- 未验证：实际设备注册/平台服务/服务端风控效果、不同 Android 厂商版本矩阵、各 runtime fresh UI/新任务缓存；本轮不宣称在线能力完成。
- 回滚：先检查评估目录的 `source_changes.patch` 是否仍可反向应用；只撤本轮真源和测试 hunk，核对 `new_source_files.json` 的四个精确路径仍为本轮文件后再移除，重新运行技能同步器清理派生资源；维护记录追加回滚说明。禁止整树恢复或覆盖后续用户修改。
- 决定：`KEEP` 本轮技能与同步增量；运行期/业务能力仍以具体目标的独立证据验收。

### 2026-09-18 01:00:03 +08:00 — 重载后逻辑复核与同步路径修复

- 时间（Asia/Shanghai）：2026-09-18 01:00:03 +08:00。
- 触发与范围：用户要求重新梳理检测，重点排除逻辑错误；分别复核本项目与独立 iOS 项目，领域正文保持平台隔离。本条只记录 Android 真源和镜像变化。
- 修复内容：代理恢复按原键存在状态及完整值处理，不能固定清空为 :0；标准原语 KAT 仅作自检，目标模拟 oracle 需同版本目标原版对照；本地 SO 算法按离线判官验收，不强制发业务请求。同步器在全量预检及逐次写入/删除前检查解析边界、祖先 reparse point 和源镜像重叠，拒绝外部 junction、内部 alias 及源硬链接；保留正常 Darwin gitlink 资产。
- 涉及文件与体积：android-recon/SKILL.md 129→131 行；protocol-signature-reverser/SKILL.md 181→182 行；sync_shared_skills.py 400→482 行；test_skill_maintenance_scripts.py 625→814 行；唯一 .agents 镜像由真源同步；本维护记录追加。其他 Skill 真源、业务项目、memory 和 MCP 配置未修改。
- 验证：真实 Windows junction/hardlink 隔离夹具中，旧同步器 7 tests/9 failures，新路径专项 12/12；全量 unittest 72/72；MCP 注册 smoke 为 81+8+11=100、重复名 0（非真机调用）；6 个 Skill quick_validate 6/6。同步 23 个受控文件均与真源预期相等，第二次同步 hash/mtime 无变化，五个禁止发现根均不存在。首次全量测试因两份文档尚未同步而报镜像差异，原失败日志已保留，完成真源同步后同套全通过。
- 独立评审：跨两项目 9 组实际情景回答盲评为新版优先 1、旧版优先 1、持平 7，无必须修复项；Android 3 题为新版优先 1、持平 2。模式 dry_run，只评文本与规则决策，不报告质量百分比或现场成功率。
- 证据与同步：`artifacts/skills_logic_review_20260918_003654/` 保存 baseline/hash、问题清单、RED/GREEN、同步日志、情景回答/盲包/映射/评审、最终差异与 REPORT.md；源/镜像已物理校验，未声称各客户端 UI/调度缓存实测。
- 边界与回滚：**KEEP**；仅离线规则/代码/注册表测试，未操作设备、账号或线上业务，未改全局配置/记忆、未提交推送。只反向本轮 source_changes.patch 中的可定位 hunk，核当前文件与 final_source_manifest 后处理；保留其他脏树改动，从真源重新生成镜像。本日志只追加回滚记录。


### 2026-09-19 22:25:47 +08:00 — 退役 Skill 资源清理与客户端触发核查

- 时间（Asia/Shanghai）：2026-09-19 22:25:47 +08:00。
- 触发原因：用户要求清理更新后淘汰内容并核查自动触发，最终范围为 ZCode / Claude Code / Cursor。
- 真源与具体变更：Darwin 的结果入口统一到本文，不再消费两份不同步的 results.tsv；CLAUDE.md 明确匹配任务先读对应 Skill，区分发现、选用与实际读取。未改 Android 领域算法或设备流程。
- 删除/新增：已归档后移除 Darwin 退役辅助包真源35+镜像35，以及 unpack 缓存4，共74文件/10,627,055字节；双方 .git、当前 SKILL.md 与 test-prompts.json 保留，Git 索引未改。旧包中的过时工作流/伪证据和不同步历史有逐项依据，其余图、模板是该退役包的配套，不声称每张图均有内容错误。新增仅本轮审计产物。
- 修改前后：Darwin 126→126行，CLAUDE.md 167→169行；有效Skill仍6个。历史gitlink打包风险尚未解决。
- 验证结果：维护专项离线单测46/46；6项Skill格式通过；23个受管镜像一致。归档ZIP逐项回读哈希74/74一致，独立dry-run复核见报告；不声称模型行为评分上升。
- 同步/重载：从真源运行 sync_shared_skills.py。ZCode bundled CLI 0.16.5 在根/子目录均发现6项，最终根复验无重复、diagnostics为空；Cursor缓存有6项真源发现记录；Claude Code所查实现与配置支持发现。当前Cursor/Claude交互会话与三客户端自然语言自动选用未验证。
- 证据/回滚：artifacts/skills_cleanup_trigger_20260919_220321/ 下有 REPORT.md、baseline、diffs、退役ZIP及逐文件SHA-256、原生命令与验证产物。只反向本轮hunk；退役文件先解压到新目录核hash再选择恢复，遇不同现存文件停止覆盖。源恢复后重跑同步器，不整体回退脏树或本文。
- 范围/决定：KEEP（文档、发现、离线验证）。未改业务项目、设备、MCP配置、全局配置、项目Memory；不把旧辅助包归因成未触发的原因。Qoder按用户要求停止排查。


### 2026-09-19 23:04:58 +0800 Asia/Shanghai — Skill 更新后的 Rules 正文联动补齐

- 原因：用户纠正此前核查重点，实际问题是Skills已更新而Rules职责/流程仍旧；镜像一致不代表语义一致。
- 文件/内容：CLAUDE.md补设备注册/风控三Skill分工、密钥/证明/设备令牌/session生命周期、传输到达层、离线与业务判官、注册状态保护和累计重试预算；reverse-skill-evolver新增逐项Rules语义联动，明确同步脚本不生成Rules摘要。AGENTS薄入口无独立旧摘要，不扩写。
- 前后：CLAUDE169→173行；evolver146→148行。其他4任务Skill的当前内容保持，镜像由真源同步。
- 验证/同步：维护测试46/46，6个Skill格式通过，23个受管镜像一致。独立dry-run逐项核对6处差异闭合，无新增越域冲突；未做客户端自动调用实验。
- 证据/回滚：artifacts/skills_rules_alignment_20260919/ 含baseline、diffs、报告、哈希与日志；仅反向本轮hunk并重新同步，不覆盖脏树后续修改，本文只追加记录。
- 边界/决定：KEEP（文档语义与离线验证）。未写memory/全局配置/设备/业务项目，未把内容漂移的修复当作某次未触发的因果证明。
