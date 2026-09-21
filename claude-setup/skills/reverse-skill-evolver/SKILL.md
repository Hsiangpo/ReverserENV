---
name: reverse-skill-evolver
description: 维护和验证本仓库 Android 逆向 Skills、Rules 与 MCP 契约。用于全量或单项技能优化、失败模式沉淀、路由去重、镜像同步、跨 Skill/MCP 一致性和独立行为评审。触发词：优化逆向skills、进化技能、skill评估、更新策略矩阵、记录失败模式、同步skills、MCP规则一致性。
---

# Reverse Skill Evolver

## 范围

只维护：

- 4 个 Android 任务 Skill：`android-recon`、`android-unpack`、`android-dynamic`、`protocol-signature-reverser`；
- 本 Android 演进 Skill；
- `darwin-skill` 作为通用维护框架，不进入 Android 任务路由；
- 根 `.mcp.json` 与 3 个自建 Android MCP 的契约；
- `CLAUDE.md` 权威 Rules 及各 runtime 薄 shim。

不吸收 iOS/IPA/Mach-O/越狱、Web/PE/通用 CTF 技能或 Kali 渗透 MCP。本地仓库维护默认已授权；只有写真实全局配置、扩展到仓库外目标或改变第三方系统时才重新确认。

## 真源与脏树纪律

- Skills：只编辑 `.claude/skills/<skill>/`。
- MCP：只编辑根 `.mcp.json` 和 `android_mcp/` 实现。
- Rules：事实只写 `CLAUDE.md`；只保留根 `AGENTS.md` 作为非 Claude runtime shim，不创建 vendor rules 副本或 `AGENTS.override.md`。
- Memory：`.zcode/memory/` 是独立真源；只有用户明确要求更新记忆时才写，不把技能优化自动扩展成记忆修改。
- 修改前记录 `git status --short` 和目标文件 diff。禁止 stash、reset、checkout 丢弃、整树覆盖或独立修镜像。
- UTF-8 中文使用无 BOM；禁止 `Get-Content -Raw` 参与读写同步。

## 七态事实词

MCP/工具结论只使用：

`implemented` / `adapter` / `declared` / `documented` / `absent` / `online` / `validated`

配置存在、握手成功、工具数量、HTTP 200 或文档声称都不能替代功能验收。

## 9 维评估（按相关性评分）

| # | 维度 | 核心问题 |
|---|---|---|
| 1 | 发现与边界 | description 是否准确触发且排除非 Android 扩域 |
| 2 | 路由/职责 | 与其余 3 个任务 Skill 是否重叠或断档 |
| 3 | 工作流 | 输入、输出、判官和决策点是否可执行 |
| 4 | 失败编码 | 是否有“触发→一线→仍失败”且能区分假设 |
| 5 | 工具契约 | 路径、版本、serial、超时、MCP 状态是否有代码/测试证据 |
| 6 | 状态恢复 | 备份、写后验证、清理、防 PID 复用是否覆盖风险动作 |
| 7 | 交付诚实度 | 是否区分静态命中、在线 oracle、绕过和纯算 |
| 8 | 行为实测 | test prompt 与真实回归是否优于 baseline 且无副作用 |
| 9 | 精简与黑名单 | 是否去重、渐进披露，并保留关键反例 |

并非每个 Skill 都应有 APP 矩阵、SO 策略、抓包方案或 Frida 版本表。不可适用项按职责评估，不以“缺少别的 Skill 内容”扣分；否则会诱导横向复制和文件膨胀。

## 进化流程

### 1. 建立基线

1. 读 `CLAUDE.md`、目标 Skill、现有 `test-prompts.json` 和相关实现/测试；
2. 固定分支、脏树边界、文件 hash/行数/BOM；
3. 扫描路径、缺失引用、runtime 钉死、iOS/非 Android 污染和重复职责；
4. 运行改前测试；无法运行的维度标 `dry_run`，不能补造分数；
5. 由独立 judge 盲评；复杂/高风险改动至少一名 judge，不把同一上下文自评当证据。

若用户已明确批准“全量优化并继续推进”，视为本轮批量人审检查点；仍需逐项记录 diff 与回归，不反复停问。

### 2. 最小改进

按证据选择一个可归因改进块：

- 路由重叠 → 把执行职责留在唯一 Skill，其他只分诊；
- 工具/版本漂移 → 以代码、配置和 live probe 为准；
- 假成功 → 先补失败回归，再把实现改为 fail-closed；
- 文档过大 → 删除宣传、重复案例和无决策价值清单；条件性细节放已有 reference；
- 外部知识 → 记录来源，只吸收当前 Android 样本/工具能验证且改变决策的规则；
- 权限误阻塞 → 说明仓库内默认授权，同时保留范围扩展门和工程恢复护栏。

目标文件有用户未提交改动时，只应用可定位 hunk；若与无法区分的用户改动重叠，停止该文件并报告，不覆盖。

### 3. 验证棘轮

1. 重跑改前同一测试集；
2. 新/改脚本加语法、契约和假成功回归；
3. 独立 judge 用相同 prompt 做 with-skill/baseline 行为对比；
4. 检查文件体积、重复、越域和镜像漂移；
5. 只有测试不退步、职责更清晰且行为证据改善时保留。

分数只是摘要。没有 full-test 时只能报告 dry-run；不能根据措辞匹配、标题数量或自己刚改完的直觉声称质量提升。

### 4. 跨域联动检查

- recon 只侦察/静态/抓包治理；native Hook 必须在 dynamic；
- unpack 只交付真实 DEX/SO 解密段；退出码/文件名不算成功；
- dynamic 只交付 Hook/trace/RPC/运行证据；Unicorn/纯算在 protocol；
- protocol 负责字段谱系和三级交付；oracle/重放不能称纯算；
- 所有设备操作使用 bundled ADB + 唯一 serial；
- Python Frida 以专用 venv 16.5.9 为事实，不假定 CLI；
- GhidraMCP 若未注册/未验收，只能是 `documented`；
- 3 个自建 MCP 工具数由 server 注册测试得出，不手填猜测。

### 5. 同步

先做 Rules 语义联动：逐项对照本轮 Skill 的职责/触发、关键决策、状态保护和交付判官，更新 `CLAUDE.md` 的 Skills 拓扑、标准闭环及相关约束；`AGENTS.md` 只核真源引用，不复制全文。报告每项对应的源段落及更新结果；无需修改也要写具体理由。下面的 Skill 镜像脚本不生成这些摘要，哈希一致或结构测试通过不能替代这项核对。

```powershell
python .claude\scripts\sync_shared_skills.py
python .claude\scripts\sync_mcp_mirrors.py
```

同步后验证：

- `.claude` 与唯一 `.agents` 镜像的内容只存在预期 runtime 路径替换；
- `.codex/.cursor/.grok/.qoder/.zcode/skills` 均不存在，各 runtime 实际项目 Skill 名无重复；
- Cursor/Codex/Grok MCP 与根 `.mcp.json` 一致，Codex 非 MCP 配置保留；
- 任一组写入失败，所有 MCP 镜像恢复旧内容；
- ZCode/Qoder 用户目录配置只核对并报告，不因项目同步脚本暗改。

### 6. 报告

记录到 `docs/SKILLS_MCP_RULES_MAINTENANCE.md`。每条必须带北京时间和时区，并包含：

- 触发原因、修改范围和来源；
- 具体文件、修改前后、删除/新增内容和原因；
- 改前/改后行数；
- 静态、离线、行为和真机测试分别的结果；
- runtime 同步/重载结果、judge 模式（full-test/dry-run）；
- 保留/回滚决定、可执行回滚办法与未验证项。

维护文档不属于 Skill 发现根，不复制到镜像；易漂移的工具数、版本和测试计数只写进带日期记录，不写成永久现状。

除非用户明确要求，不生成成果卡片，不自动写记忆，不提交或推送。

## 失败恢复

| 触发 | 一线 | 仍失败 |
|---|---|---|
| 目标 hunk 与用户改动重叠 | 缩小补丁并保存前后 diff | 停该文件，交用户决定 |
| judge 超时/结果不完整 | 相同输入重跑一次 | 标 dry-run，本轮不报分数提升 |
| 镜像 hash/路径漂移 | 从真源重新同步一次 | 停止，禁止手修镜像 |
| MCP 配置存在但实现不消费 | 补离线契约测试 | 保持 declared/implemented，不标 validated |
| live 测试改变设备状态 | 立即按基线精确恢复并复核 | 停止后续动态测试，报告残留 |

## 不要做

1. 不从 `wagnganskills` 整包复制，也不引入它的 iOS/CTF/Kali/通用移动路由。
2. 不为评分堆章节、案例、成功率或绝对化经验。
3. 不跳过 baseline、test prompt、回归或独立评审。
4. 不把 4 个任务 Skill 横向抄成相同大全。
5. 不用 `git reset --hard`、stash 或整目录 junction 修复脏树。
6. 不自动修改记忆、全局 MCP、设备高风险配置或第三方系统。
