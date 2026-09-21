---
name: ast-deobfuscation
description: >
  仅限已授权目标。使用 Babel AST 分层、可回退地还原 JavaScript 混淆结构。适用于 `_0x` 字符串表、dispatcher、虚假分支、控制流平坦化、opcode 分发及 reese84/顶象/极验等家族适配；不负责加密算法、补环境或验证码求解。
---

# AST 反混淆

优先使用分层入口，而不是继续把站点特有逻辑堆进通用脚本。

## 角色规则

**此 Skill 激活后，以 JS 代码还原专家身份工作。**

仅处理已获授权的目标；不用于账号滥用、凭据窃取、绕过访问控制、批量隐蔽采集或攻击生产反滥用系统。

- 每一步改写必须可回退（保留原文件 + 中间产物）
- 结构性改写后必须重新 parse 验证语法正确性
- 禁止一次性执行所有变换层，必须逐层验证
- 反混淆的最终目标是让加密函数可读、可定位，不是追求 100% 还原

## 工作流

> 使用本 Skill 自带的 `.claude/skills/ast-deobfuscation/scripts/`；它与仓库根 `scripts/` 不是同一份，命令必须写显式 Skill 路径。首次运行或 lockfile 更新后先执行 `node .claude/skills/ast-deobfuscation/scripts/install-dependencies.js`。依赖按本 Skill 的 lockfile 安装到 ignored 的 `.claude/skills-next/dependency-cache/ast-deobfuscation/`，运行脚本只从该缓存加载，不依赖仓库根的传递 Babel 包，也不把 `node_modules` 带进 Skill 发现树。

### Step 1: 家族路由与症状基线

先记录当前资产 URL、内容 hash、采样时间、加载 realm 与已知版本；文件名/厂商品牌只作候选线索。旧家族特征不匹配时保留未知，不向当前样本硬套旧字母表、字段数或 opcode。

```bash
node .claude/skills/ast-deobfuscation/scripts/detect-patterns.js <input.js> [hint]
```

`detect-patterns.js` 输出候选家族、评分和命中依据，用于选择专用适配器；它不是完整的结构症状扫描。随后运行：

```bash
node .claude/skills/ast-deobfuscation/scripts/collect-residue-metrics.js <input.js>
```

以 `splitPipeCount`、`loopSwitchCount`、`opcodeIfChainCount`、`dispatcherWrapperCount` 和 `hexIdentifierCount` 建立变换前症状基线。

### Step 2: 选择流水线

只读取命中的站点或混淆家族规则文档，不要一次加载所有。

### Step 3: 执行流水线

```bash
node .claude/skills/ast-deobfuscation/scripts/run-pipeline.js <input.js> <output-dir> [hint]
```

执行选中的变换步骤，记录每步耗时。

### Step 4: 验证产出

- `node --check <output.js>` 语法检查
- 对照参考产物或原始混淆症状，判断是否还需要新增专用适配脚本
- 使用 `.claude/skills/ast-deobfuscation/scripts/collect-residue-metrics.js` 统计剩余混淆特征
- 对修改到的目标入口固定同一输入、时钟与随机源，比较变换前后输出、关键副作用和异常；跨异步链时保留时序证据。没有可运行 oracle 时只能报告结构变换，不能宣称语义保持或算法已还原。
- 发现输出、副作用或异常不等价时，停止交付该产物，定位首个引入差异的变换并回退到上一验证点；修复后再对原样本回归。

🔴 **CHECKPOINT**：每层记录语法、可读性与已完成的语义验证；parse 通过、残留减少和业务成功分别报告。VM 调度 trace、厂商所称 Proof of Execution 与算法逐字节还原也是不同证据。

## 支持的混淆类型

| 混淆类型 | 症状 | 处理方式 |
|---------|------|---------|
| `_0x` 标识符 | 变量名全是 `_0x1a2b3c` | 标识符重命名（基于引用分析） |
| 字符串表 | 大型数组 + 解码函数 + 自执行包装 | 字符串数组内联 + 解码函数求值 |
| dispatcher | 对象方法分发 `_0xabc['call'](...)` | dispatcher 内联 |
| 虚假分支 | `if (constant === value)` 永真/永假 | 常量折叠 + 死代码消除 |
| 控制流平坦化 | `while/for + switch` 状态机 | 控制流拍平还原 |
| opcode 分发 | `if (literal === opcode)` 的 `else if` 链 | 严格比较链改写；独立连续 `if` 保留 |
| 逗号表达式 | `(a=1, b=2, c=3)` | 序列化拆分 |
| IIFE 包装 | 自执行函数包裹 | 通用层保留调用/作用域边界；专用改写须单独验证 |
| 语句提升 | 变量/函数声明提前 | 语句顺序还原 |

## 支持的混淆家族

| 家族 | 站点 | 规则文档 |
|------|------|---------|
| reese84 | — | `references/patterns/reese84.md` |
| 顶象 Verify5 | dingxiang | `references/patterns/dingxiang.md` |
| 极验4 | geetest | `references/patterns/geetest4.md` |
| 同花顺 | tonghuashun | `references/patterns/tonghuashun.md` |
| 网易易盾 | yidun | `references/patterns/yidun.md` |
| 小红书 | xiaohongshu | `references/patterns/xiaohongshu.md` |
| OB 变种 (cn-bidding) | — | `references/patterns/cn-bidding-ob.md` |
| OB 变种 (mps) | — | `references/patterns/mps-ob.md` |
| PerimeterX basE91 多态表 | walmart 历史样本 | 字母表与解码器按当前资产配对，往返字节验证见 [参数组装参考](../param-encryptor/references/assemblers.md) |
| 数美 captcha-sdk OB | ishumei 历史样本 | 曾观察到 2602 元素及 `arr[idx-400]`；当前资产核对后才应用 |
| CF Turnstile dispatcher | 1yunti 历史样本 | 可按缺口用 `trace_dispatcher` + mask 快照；trace 不等于还原完成 |

## 设计规则

- 通用脚本只保留低风险、可复用的改写，例如结构标准化、虚假分支清理、dispatcher 内联、控制流拍平和 `if -> switch`。
- 一旦某个模式明显是站点特有的，就同时补齐四部分：规则文档、检测器命中项、专用适配脚本、流水线配置项。
- 对于高开销步骤，优先按家族跳过或重排，不要强行要求所有样本走同一套顺序。像 `reese84` 这种大样本，如果太晚执行 `inline-literals`，很容易卡住。
- 专用适配脚本应当保持窄而准。如果某条规则没有在多个无关样本中复用，不要急着回灌到通用脚本。
- 结构性改写后要重新 parse，并保证每一阶段都可以独立运行和排查。

## 反混淆后的下游路由

局部结构恢复并定位到目标后，按实际缺口转交；尚未定位的函数和 VM handler 明确列为未解：

| 反混淆后发现 | 转交 Skill | 示例 |
|-------------|-----------|------|
| 加密/签名函数（MD5/AES/RSA/自定义） | `param-encryptor` | `CryptoJS.AES.encrypt(data, key)` |
| 验证码计算逻辑 | `captcha-solver` | 滑块距离计算 + 轨迹生成 |
| 浏览器环境检测代码 | `env-patcher` | `navigator.webdriver` 检测 |
| VM 字节码（非 AST 可处理） | `web-reverse-master` + `trace_dispatcher` | JSVMP / CF orchestrate / Kasada ips.js |

## 入口脚本

> 以下脚本随本 Skill 提供；如果提示 dependency cache 缺失、陈旧或版本漂移，先运行上述依赖安装入口。不要手工把 `node_modules` 放进 `.claude/skills/` 或 `.agents/skills/`。

- `scripts/detect-patterns.js`
  根据显式 hint、文件名/路径和源码中的家族标记选择最可能的站点或混淆家族；结构残留由 `collect-residue-metrics.js` 单独统计。
- `scripts/run-pipeline.js`
  把样本复制到测试目录，执行选中的步骤，记录耗时并输出流水线报告。
- `scripts/collect-residue-metrics.js`
  统计仍未解开的症状，例如 `split('|')`、直接 `loop/switch` 平坦化、opcode `if` 链、dispatcher wrapper 和 `_0x` 标识符。
- `scripts/compare-with-reference.js`
  将最新流水线输出与 `decode.js` 对比，汇总剩余差距。

## 参考文档

> 以下参考文档位于本 Skill 的 `references/` 子目录中。如不存在，核心工作流仍可执行，但缺少特定混淆家族的适配细节。

- 新增或调整适配器时，先读 `references/pattern-layering.md`。
- 任何逻辑想放进通用脚本前，先读 `references/safe-rewrite-rules.md`。
- 处理字符串表、解码 stub、最小运行时求值时，读 `references/string-array-and-minimal-eval.md`。
- 处理控制流平坦化、opcode 分发器和 VM 类 handler 时，读 `references/control-flow-and-opcode-patterns.md`。
- 处理逗号表达式、IIFE、语句提升时，读 `references/sequence-normalization.md`。
- 厂商样本版本、服务端票据或执行证明边界不清时，读 [协议与状态证据](../web-reverse-master/references/14-risk-protocol-and-state.md)，不要从混淆家族推出产品验证结果。
- 检测器命中后，只读取对应的**一份**站点规则文档。文件路径见上方「支持的混淆家族」表的「规则文档」列（此处不再重列，避免两份清单漂移）。

## 校验

- 每个新增或改过的 JavaScript 辅助脚本，在接入流水线前都要至少过一次 `node --check` 或等价的加载校验。
- 测试案例时，把中间产物、检测结果、对比结果和流水线耗时都保留在案例目录里，方便定位慢步骤和失败步骤。
- 修改作用域、比较链或数组内联时，运行 `node .claude/skills-next/evals/ast-semantic-regression.js`。它以真实变换脚本对照离线 fixture 的运行结果，不写文件或请求网络；通过不等于所有变换或目标算法已验证。

## Phase Mapping

本 Skill 主要在 CLAUDE.md Phase 2（定位加密）作为前置步骤：

| Phase | 本 Skill 的角色 | 与专业 Skill 的协作 |
|-------|----------------|-------------------|
| Phase 2 定位加密 | 按需恢复妨碍定位的局部结构；已有 writer/调用栈可直接取证 | 算法已定位时转交 `param-encryptor` |
| Phase 3 方案制定 | 🟡 按需：Plan 中如涉及混淆处理方案 | — |
| Phase 4 代码还原 | 🟡 按需：最终 signer.js 可能需要局部反混淆 | — |

**典型调用链：**
```
web-reverse-master Phase 2 发现目标 JS 被混淆
  → ast-deobfuscation Step 1-4 还原代码
  → 还原后发现 CryptoJS.MD5 调用
  → param-encryptor 配方1 匹配 + 本地对照
  → Phase 4 代码还原
```

## Related Skills

| Skill | 职责 | 何时调用 |
|-------|------|---------|
| `web-reverse-master` | 全流程编排 | 需要完整逆向分析流程 |
| `captcha-solver` | 验证码求解 | 反混淆后发现验证码计算逻辑 |
| `param-encryptor` | 加密参数生成 | 反混淆后发现加密/签名函数 |
| `env-patcher` | 补环境 | 反混淆后发现环境检测代码 |
