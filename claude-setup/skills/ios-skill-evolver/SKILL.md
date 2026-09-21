---
name: ios-skill-evolver
description: iOS 逆向 Skills 维护元技能。仅在用户请求或授权维护时，用于技能评估、最小修复、回归验证及 Skill/MCP 契约对齐；不参与普通 iOS 分析的自动维护。匹配请求：进化 iOS 技能、更新砸壳矩阵、评估 iOS skill、优化技能、技能进化。
---

# iOS Skill Evolver —— iOS 逆向技能维护

## 角色定位

维护 4 个逆向 skill（**ios-recon / ios-unpack / ios-dynamic / ios-protocol-signature**，必要时含本元技能）及相关 **`.mcp.json` / `mcp/ios-device-mcp/server.py`** 契约，只保留有证据改善且属于本轮授权范围的修改。

`description` 用于客户端相关性匹配；正文的路由和维护条件不是 hooks，也不保证客户端实际加载或执行。普通 iOS 分析及其完成事件不自动修改 Skills 或记忆；仅在用户请求或授权维护时选用本技能，写记忆仍须用户明确要求。

记忆权威源是仓库 `.claude/memory/`。Claude/ZCode 用户目录只作增量来源（[[claude-zcode-memory-sync-procedure]]：md5 diff，只拷新增/更新，保留独有）。全量重审以“上次审计后新增/更新的证据簇、工具版本变化或已证伪结论”为依据，不按累计文件数启动。

**设计灵感**：达尔文.skill v2.0（棘轮机制 + 9维评分）+ 女娲知识蒸馏方法论。

```
用户请求或授权维护 → 留存基线并评估 → 找可改问题/证据簇 → 一轮只改一个决策簇
   → 独立验证（环境允许时用子 agent；否则确定性检查+相关工件回归）→ 证据改善?保留 : 回滚
```

## 核心原则

| # | 原则 | 说明 |
|---|------|------|
| 01 | 单一决策簇 | 每轮只修一个可证伪问题；可同时改主 skill、必要交叉引用和 MCP，但禁止顺手扩散无关维度 |
| 02 | 分层评估 | 结构检查 + 与改动相应的行为证据；离线/情景评审不冒充真机结果，不因评分要求扩大实验范围 |
| 03 | 棘轮机制 | 按证据判断改善与回归；默认只反向本轮 hunk。有本轮独立提交且相关文件干净时才用 `git revert`；快照恢复须当前 hash 仍等于本轮末态，否则逐项合并并保留后续改动。禁 `reset --hard` |
| 04 | 独立证据 | 环境允许时用独立子 agent；否则不伪称独立评分，改用确定性验证器、离线样本和授权范围内的 MCP 握手/单测 |
| 05 | 授权连续执行 | 在已授权维护范围内连续完成，不逐项重复 checkpoint；新增范围或必要输入缺失时再核实 |
| 06 | 权威源先行 | 只编辑 `.claude/skills` 与根 `.mcp.json`；Cursor/ZCode/Codex 派生入口靠 junction/同步与语义校验，不独立演化 |
| 07 | 外源纯度 | 外部 skill 仓只作候选证据；先做 iOS 专属、非重复、与本机实测相容三重过滤，默认不新增 skill/路由/工具链，不整段搬运混合平台内容 |

## 9 维 iOS 逆向领域评估体系（100分制）

评分只作本轮比较；未验证的维度标“未验证”，不以结构通过补足效果分。

### 结构维度（60分）

| # | 维度 | 满分 | 评估标准 |
|---|------|------|----------|
| 1 | **工具路径有效性** | 10 | venv frida 17.15.3 / tidevice / jtool2 / ldid / SSH relay 路径存在且可执行（class-dump/dsdump 本机不依赖，见阉割矩阵）|
| 2 | **砸壳/App 策略矩阵覆盖度** | 15 | 每个目标 App 的 加密(cryptid)/砸壳方案/网络栈/SSL pinning/越狱检测/签名主体方案 6 列完整 |
| 3 | **失败模式编码完整性** | 15 | R/U/D/S 各失败模式每条有：描述+案例+规则+成本(浪费时间) |
| 4 | **决策树可执行性** | 10 | 每个决策树分支有明确进入条件和执行步骤 |
| 5 | **工具阉割点/修复时效性** | 10 | 每个外部工具标注常见阉割点+修复方式+对齐版本(frida-ios-dump/dsdump/objection 等) |

### 效果维度（40分）

| # | 维度 | 满分 | 评估标准 |
|---|------|------|----------|
| 6 | **静态定位准确度** | 10 | jtool2/IDA（class-dump/dsdump 仅独立 Mac）定位签名·加密入口的手法与实际 Mach-O 匹配 |
| 7 | **抓包/pinning 绕过成功率** | 10 | 按 App pinning 强度(NSURLSession/TrustKit/BoringSSL)推荐的绕过方案可实际使用 |
| 8 | **Frida spawn/attach & 版本兼容矩阵** | 10 | 按检测面选 spawn/晚 attach；frida 17 API、bridge 可用性、原生 ObjC fallback、设备/App 版本组合准确无过时信息 |
| 9 | **实测验证通过率** | 10 | 在已授权且条件具备时，以受影响项目的真机/业务判官结果验证；未执行则标“未验证” |

## 进化循环：6 个 Phase

### Phase 1：基线评估
```
入口: 用户请求或授权 iOS Skills 维护；任务完成、指导错误或版本变化仅提供待评估证据
执行: 1.保存 SHA-256/快照并跑相关结构/MCP基线  2.环境允许时启独立子agent重评；不可委派则标“内部基线”  3.输出可改问题与证据锚点
```
### Phase 2：单维度优化
```
规则: 一轮只改一个决策簇；优先有证据的缺口；无改善证据时不继续堆改动
执行: 1.核对基线与编辑范围  2.外源先列 KEEP/REJECT 与体积基线  3.只改 `.claude` 权威源与必要 MCP  4.跑 quick_validate+仓库验证器+相关工件回归
     5.环境允许时再启独立子agent复评  6.改善→保留；不改善→按 Git/无Git路径恢复
```
### Phase 3：回归测试
```
1.按本轮改动选择相关工件关键步骤 2.优先跑离线向量/解析器；真机在线须在已授权范围内、设备健康且不越烧号线时执行
3.查是否回归 4.未做真机验证时明确“仅离线回归”，dim9 标“未验证” 5.回归→恢复本轮对应改动，保留他人修改
```
### Phase 4：跨 Skill 联动检查
```
1.查4个skill一致性(frida版本/设备基线/SSH路径/venv 统一，cross-ref有效)
2.查 ios-dynamic 失败模式在 ios-protocol-signature 有对应止损/策略
3.查 ios-unpack 的加密/网络栈是否有对应 signature 案例与 ios-dynamic 注入策略
4.逐项把本轮 Skill 的职责/触发、关键决策、状态保护和判官与 CLAUDE.md、AGENTS.md、Cursor Rules 摘要对照；更新过时摘要或记录无需修改的具体理由，junction/hash一致不替代语义核对
```
### Phase 5：知识蒸馏归档
```
1.只把已验证且与本轮相关的失败模式加入对应 Skill  2.有新App证据才更新 ios-recon 矩阵  3.有新签名证据才更新 ios-protocol-signature
4.对被推翻的旧结论加 `SUPERSEDED`/新判官锚点，禁止只追加矛盾叙事  5.仅用户明确要求更新记忆时，才写项目记忆及 MEMORY.md
6.按 Asia/Shanghai 精确时间追加 `.claude/skills/EVOLUTION_LOG.md`（原因/内容/文件/同步/验证/边界与回滚）  7.输出进化摘要
8.仅用户明确要求用户目录同步时才做增量对齐（禁止全量覆盖、禁止当权威源）；常规 Skill 维护不写用户目录
```

### Phase 6：MCP 对齐（与 skill 同期）
```
ios-device / .mcp.json 必须反映当前设备事实：
- 设备 frida 只走 27045；主机端口可避冲突，relay 必须是 `host_port→device 27045`；禁 27042 / set-default
- `IOS_DEVICE_UDID` 锁定目标，复用监听前也须 fail-closed 校验；新起 relay 显式 `-u <完整UDID>`，子进程 stdin/stdout/stderr 与 MCP stdio 隔离
- relay 冷启动与 Frida 握手分开计时，各有 ≥15s 且有限的 watchdog
- ios_setup_auth = mobile + sudo（sshd 禁 root 密码）
- ios_info 查 systemagentd/coreservice，不要查已卸载的 frida-server
- ios_frida 接口默认 spawn 是工具事实，不覆盖保留当前状态的任务要求；需 attach 时显式选择，文档写明无 ObjC/require
- ios_ssh 失败诊断指向越狱/openssh，不是 MCP 坏
- ios_diagnostics 只做有界只读 syslog / Crash-Jetsam 列名 / PCAP：显式 UDID；实时动作≤15s；PCAP≤100包、stdout丢弃、绝不覆盖已有文件
Skill 正文由现有 junction 即时可见；协议 Skill 更新后运行 tools/write-cursor-signature-rule.py 刷新 Cursor 薄入口的描述与内容指纹，其他 Rules 摘要按 Phase4 人工语义对齐，不为此重写无关配置。
实际修改 MCP/生成规则时运行对应 tools/sync-claude-to-cursor.ps1、tools/sync-claude-to-zcode.ps1 并核对镜像。
所有保留改动运行 .venv/Scripts/python.exe tools/check-ios-skills-mcp.py。
```

### Windows 验证纪律

- `quick_validate.py` 在中文 Windows 必须先设 `PYTHONUTF8=1`；项目 venv 没有 PyYAML 时可用已安装 PyYAML 的系统 Python跑它，仓库验证器本身只用标准库。
- 所有 Markdown/JSON/TOML/临时 Python 按 UTF-8 无 BOM；PowerShell 5.1 禁用默认 `Set-Content -Encoding UTF8` 写 frontmatter/脚本。
- 验证器必须检查：5 个 skill 名称/frontmatter、wiki 链接、失败码“引用即定义”、已配置 skills junction 的真实目标、根/派生 MCP 语义一致、命令路径、`server.py` 语法与16个公开工具名；另核 `CLAUDE.md` / `AGENTS.md` / Cursor Rules 的诊断边界、重试上限，以及协议 Rule 完整内容等于当前 Skill 生成结果。该检查不判断所有人工摘要的语义，也不证明客户端实际选用。
- MCP 运行验收分层：stdio initialize/list_tools 证明协议层；`ios_info`/`server_health` 证明运行层；设备离线时不得把前者写成真机成功。

## 维护请求路由
```
"评估 iOS skills"                 → Phase1 → 有证据的维度评估与报告；用户已授权检查修复时继续最小修复
"优化 <ios-recon|ios-unpack|ios-dynamic|ios-protocol-signature>" → Phase1→2→3
"更新砸壳矩阵"/"在矩阵添加新App"    → Phase1 留存相关基线 → Phase2 最小编辑 → 相关回归
"记录失败模式"/"又踩坑了"           → 先核证；仅在授权维护时更新 Skill，写项目记忆仍须明确要求
"全量进化"                        → 用户已授权批处理；按最弱证据簇→必要 skill/MCP→联动→归档，不强制机械顺序
"检索 Claude/ZCode 记忆"          → 只读检索与差异报告；不自动写记忆、同步用户目录或修改 skill/MCP
"回滚上次进化"                    → 先核本轮 diff/末态 hash；仅反向本轮 hunk，独立提交或快照恢复按原则03，不覆盖后续改动
```

## 反例黑名单 8 条（达尔文标准）
1. 同一AI自评后无确定性/真实证据就宣称涨分  2. 用 git reset --hard、无本轮独立提交的 revert 或未经末态核对的快照覆盖进行回滚
3. 为凑分堆冗余或使用无证据的涨分门槛  4. 跳过相关回归直接评分  5. 一轮混改多个无关决策簇
6. 把干跑/离线证据写成真机或服务端验证  7. 静默跳过异常  8. 忽视维度相关簇

## 评估报告模板
```markdown
## Skill: <name> — 第 N 轮进化评估
### 基线评分 (上一轮: XX)
| # | 维度 | 得分 | 评价 |
|---|------|------|------|
| 1 | 工具路径有效性 | X/10 | ... |
| ...9维... |
| **总分** | | **XX/100** | |
### 最低维度: <名> (X/10)
### 改进方案: <描述>
### 改进后: XX/100 (+X.X)
### 棘轮决策: [保留/回滚]
```

## 维护条件清单（不是自动执行 hooks）
- [ ] 完成一个新 App 的 iOS 逆向
- [ ] 发现新的检测机制(新反-Frida/新 pinning 库)
- [ ] 工具版本升级致旧策略失效(frida/iOS/objection)
- [ ] 用户反馈"按 skill 做失败了"
- [ ] 新逆向方法论(新工具/新论文)
- [ ] Claude/ZCode 用户目录与仓库 memory 再次分叉（默认只读差异；同步须用户明确要求）
- [ ] MCP 行为与 skill 文档不一致（默认端口/spawn/认证）

## 更新历史
唯一流水账为 `.claude/skills/EVOLUTION_LOG.md`。每次保留的 Skill / Rule / MCP / Memory / 设备基线变更都按文件内模板追加，必须带 Asia/Shanghai 精确时间与验证结果；不得另建并行 Changelog。
