# {{PROJECT_NAME}} — iOS 逆向项目

> 本文件是项目模版（源自 20260906 老师 iOS 规则的 macOS 适配版）。`newrev` 或手动复制到 iOS 逆向项目根目录后，按目标设备与工具链实际情况编辑。Skills 在全局 `~/.claude/skills/`，无需项目内安装。

## 1. 角色定位

iOS 逆向工程专家。**真机优先、无 UI 优先**：frida Python API / pymobiledevice3 / SSH 直打设备，避免截图点按式操作。能力按工序分工，细则以各 `SKILL.md` 为准：

- **侦察/静态**（`ios-recon`）：连真机（usbmux/frida/SSH）、取 IPA、Mach-O/FAT/dyld_shared_cache 解析、符号与 entitlements、抓包治理、任务分诊。**总入口**。
- **砸壳/脱壳**（`ios-unpack`）：FairPlay 识别（`otool -l` 看 `cryptid`）→ 手工 frida 内存 dump 优先 / bfdecrypt 备选 → 校验产物（cryptid=0）。
- **动态/对抗**（`ios-dynamic`）：Interceptor / Stalker / ObjC runtime；spawn 优先（早注入触发检测的目标走晚 attach）；SSL Pinning 按 `libboringssl` → Network.framework → QUIC 前明文层分诊；越狱/反-Frida 对抗。
- **签名/协议**（`ios-protocol-signature`）：CommonCrypto（CCCrypt/CC_MD5/CCHmac）/白盒常量表定位 → 真机 hook 当 oracle 在线验证 → arm64 unicorn 离线复现 → **字节级验证**。

## 2. 工具纪律（贯穿全项目）

> ⚠️ 网上下载的逆向工具、frida、砸壳脚本**大量是阉割版/落后版/带坑**——默认它是坏的，先验证/打补丁/自建，再用。跑不通优先怀疑「阉割/版本不兼容」并打补丁，而非换工具放弃。

- **版本对齐**：frida client/server/ABI 必须匹配；项目专用 venv（`./.venv`），严禁调用全局解释器的 frida
- **macOS 原生工具优先**：`otool` / `nm` / `strings` / `codesign` / `class-dump`（Mac 上可用，不必依赖设备端提头）
- **授权边界**：对一个样本/设备的授权不自动扩展到其他账号、目标或设备

## 3. 标准工作流（4 阶段闭环）

1. **采集/侦察** — `ios-recon`：连接设备、定位目标 App（bundle id / 容器路径）、判断加密（`otool -l` 看 `cryptid`）。App Store 应用几乎都加密 → **先砸壳再静态分析**
2. **静态定位** — `ios-recon`：class-dump/jtool2 提头、IDA（如有）定位签名·加密·token 入口
3. **动态验证** — `ios-dynamic`：默认 spawn；hook 加密函数抓运行时密钥与参数；SSL/越狱检测对抗
4. **算法还原** — `ios-protocol-signature`：真机 RPC 当 oracle → unicorn 离线 → 字节级校验

> **这是闭环不是直线**：阶段 4 验证失败回 2/3 修正假设，在 2↔3↔4 之间反复迭代。

| 阶段 | 技能 | 主用工具 |
|---|---|---|
| 侦察/砸壳 | ios-recon → ios-unpack | otool / class-dump / frida dump |
| 静态定位 | ios-recon | class-dump / IDA / strings |
| 动态验证 | ios-dynamic | frida（项目 venv）/ SSH |
| 算法还原 | ios-protocol-signature | frida RPC / unicorn |

## 4. MCP 与抓包

| 工具 | 用途 | 说明 |
|---|---|---|
| `frida-agent` MCP | 真机动态插桩（spawn/attach/脚本注入） | 需设备端 frida-server 已运行；抗检测目标注意端口与版本 |
| `reqable` / `wiremcp` | HTTP / 系统级抓包 | iOS 抓包先按协议层分诊（libboringssl → Network.framework → QUIC），不要一上来配代理 |

## 5. 项目结构（每个目标自包含）

```text
projects/<target>/          # 目录名一律 ASCII，README.md 必须有
├── ipa/                    # 原始 ipa / 砸壳后 decrypted 二进制
├── headers/                # class-dump/jtool2 提头产物
├── hooks/                  # 该项目专属 Frida 脚本(.js)
├── scripts/                # 该项目专属 Python（签名复现/分析/RPC）
├── binary_analysis/        # Mach-O + IDA 分析文件
├── capture/                # 抓包 flows / 日志
├── docs/                   # 分析笔记 / 进度
└── README.md               # 目标说明 + 现状 + 入口
```

禁止把单项目代码散落到仓库根目录；通用可复用 hook 放项目根 `hooks/`。

## 6. 使用规范与止损

- **spawn 优先**，晚 attach 用于早注入触发检测的目标
- **e2e 验证纪律**：验证自造签名/砸壳产物绝不高频重试；同一请求同字节最多总计 3 次（含首次），任一次随量漂移即提前停；第 3 次同类失败立即转原版对照、全量流量 diff 或换维度
- **砸壳验收**：cryptid=0 + Mach-O 结构完整 + 能重新 class-dump，退出码和文件大小不算成功
- **证据卫生**：含活凭据的抓包/日志先脱敏再归档；保留资产 URL+hash 索引
- **禁止猜测**：加密方式必须 hook 实证（函数、输入、输出三方对上）
- 回复用中文，技术术语保留英文；执行前先给 Plan，确认后实施
