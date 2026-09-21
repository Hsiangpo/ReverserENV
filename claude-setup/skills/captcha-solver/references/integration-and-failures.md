# 集成、失败模式与依赖

> 从 `SKILL.md` 按需加载：需要 Phase/MCP 协作、排错表、反模式、依赖或相邻 Skill 边界时读取。

## Phase 映射

本 Skill 在 CLAUDE.md Phase 0-4 工作流中的定位：

| Phase | 本 Skill 的角色 | 与其他 Skill 的协作 |
|-------|----------------|-------------------|
| Phase 0 情报收集 | 🟡 辅助：识别验证码服务商特征 | web-reverse-master 搜索目标站点的验证码方案 |
| Phase 1 流量分析 | ✅ 核心参与：捕获验证码初始化/提交接口 | web-reverse-master 通过 js-reverse-mcp 或 CDP 桥抓流量 |
| Phase 2 定位加密 | ✅ 核心参与：定位验证码提交的加密参数 | web-reverse-master 用 js-reverse-mcp 搜 encrypt/sign 关键词 |
| Phase 3 方案制定 | ✅ 核心参与：选择配方 + 确认轨迹+加密方案 | 配合 env-patcher（验证码 SDK 需补环境） |
| Phase 4 代码还原 | ✅ 核心参与：生成验证码求解脚本 | Python 主脚本集成验证码模块 |

**典型调用链：**
```
web-reverse-master Phase 1 发现验证码接口 c.dun.163.com
  → captcha-solver 固定 SDK/协议版本和当前验证分支
  → 有图片/轨迹才做识别和协议行为数据处理
  → 提交 + 供应商二次校验 + 区分测试/容灾
  → Python 主脚本携带 ticket 调用业务接口
```

**MCP 工具使用：**
- 本 Skill 纯协议求解，不直接调用浏览器 MCP 工具
- 如需动态调试验证码加密逻辑，使用 `web-reverse-master` → `js-reverse-mcp`（默认路线 D）
- 如需在指纹浏览器中抓验证码流量，使用 `web-reverse-master` → `adspower-browser`（路线A/C）
- 如需反混淆验证码 JS，使用 `ast-deobfuscation`

---


## 失败模式编码

错误码只有在对应产品、版本和接口内才有意义；下列是排查分支，不是单码根因映射。

| 症状 | 待区分因素 | 下一项证据 |
|------|------|---------|
| OpenCV 置信低 | 像素恢复、格式、模板、尺寸、题型不匹配 | 查看可验证像素与坐标元数据，先本地复核 |
| verify 返回 -1/VerifyErr 等 | 当前版本错误语义、会话、行为、参数、策略 | 保存内部响应，与同版本成功样本差分；不自动加抖动 |
| 参数错误 | 字段缺失、编码、来源、版本、初始化状态 | 对比真实字段谱系及原字节，再决定是否查 Key/IV/Mode |
| 识别服务超时 | 服务调用或网络异常，不等于验证码失败 | 停止盲重试，保留当前图片有效性证据后选择已授权识别器 |
| WASM 输出空像素 | 输入、内存、解码或导入函数缺口 | 固定输入离线复现，交 master 定位，不能默认环境不完整 |
| ticket 立即失效 | 过期、先被消费、应用/场景不匹配、降级 token | 依生命周期表区分，不能默认时间戳偏差 |
| SDK true 但无业务接受 | 容错、测试模式、内层校验或业务自身拒绝 | 查看 [verification-and-fallback.md](verification-and-fallback.md) |

---

## 反模式黑名单

| # | 不要做 | 替代 |
|---|--------|------|
| 1 | 用Selenium/Playwright过验证码 | 纯协议请求 |
| 2 | 猜测加密密钥 | 动态调试Hook实证 |
| 3 | 无样本就添加过冲、回拉、抖动 | 按当前协议和真实事件验证，不设默认人类轨迹 |
| 4 | 将固定或随机采样当通用解法 | 确认当前 SDK 采样与时间单位 |
| 5 | 见验证码就强加指纹字段 | 先确认是否启用指纹及其发行、采集与消费路径 |
| 6 | 一家验证码服务商方案通吃 | 每家有独立加密逻辑 |
| 7 | 将所有 session 设为 30–120s | 按字段与版本核实寿命、绑定和一次性规则 |
| 8 | 外层 success/容灾/测试 key 算正常通过 | 供应商二次校验与业务消费分别留证 |

---

## 依赖清单

按当前缺口最小安装，禁止调用全局 `pip` 或一次装齐无关依赖。安装动作仍需用户确认：

```powershell
# 内置 mmcaptcha 云端引擎；版本由随包 requirements 固定
.\venv\Scripts\python.exe -m pip install -r .claude\skills\captcha-solver\scripts\mmcaptcha\requirements.txt

# 仅在对应本地识别/验证码加密任务需要时安装
.\venv\Scripts\python.exe -m pip install opencv-python ddddocr pycryptodome
```

`mmcaptcha` 的解析、坐标换算和离线 selftest 只用标准库；Doubao/GLM 引擎才读取上述
`requirements.txt`。第三方 API token 只放环境变量（例如 `YUNMA_TOKEN`），不得写入 Skill、
站点源码、样例或日志。

---

## Related Skills

| Skill | 职责 | 何时调用 |
|-------|------|---------|
| `web-reverse-master` | 全流程编排 | 需要分析验证码加密逻辑但尚未确认算法类型 |
| `param-encryptor` | 加密参数生成 | 验证码之外的非验证码加密参数场景 |
| `env-patcher` | 补环境生成 | 验证码 SDK 需要在 Node.js 中运行时 |
| `ast-deobfuscation` | JS 反混淆 | 验证码 JS 混淆严重需先反混淆 |

---
