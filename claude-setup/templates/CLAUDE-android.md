# {{PROJECT_NAME}} — Android 逆向项目

> 本文件是项目模版（源自 20260906 老师 Android 规则的 macOS 适配版）。`newrev` 或手动复制到 Android 逆向项目根目录后，按目标设备与工具链实际情况编辑。Skills 在全局 `~/.claude/skills/`，无需项目内安装。

## 1. 范围与授权

本仓库只做 Android APK/DEX/ART/JNI/SO、Android 网络协议和真机运行期分析，不引入 iOS/PE/通用 Web 工作流（Web 部分用主模版 `CLAUDE.md`）。

仓库内样本、工具、项目目录、测试设备及用户指定测试账号默认属于**用户已授权的本地环境**。对既定对象做静态分析、低风险真机验证时，不重复询问授权，不用泛化免责声明阻塞工作。以下情况重新确认：

- 目标/设备/账号扩展到约定之外
- 要写真实全局配置、联系第三方或产生明显外部影响
- 高风险设备动作（恢复出厂、刷机、改系统分区）

**授权默认不取消工程护栏**：唯一 serial、写前备份、写后验证、止损纪律仍强制执行。

## 2. Skills 拓扑（4 个工序 Skill，按需路由）

1. **`android-recon`**：设备/样本预检、APK 拉取、加壳初判、jadx/apktool 反编译、网络栈识别、API/调用链索引、抓包治理。**总入口**。
2. **`android-unpack`**：真实 DEX/VDEX 或运行期解密 SO 段提取，**通过 DEX/ELF 结构检查 + fresh JADX 反汇编验收**（退出码和文件名不算成功）。
3. **`android-dynamic`**：Frida/trace/RPC、反注入判因、SSL/native 网络、运行期快照。用最窄 Hook 面。
4. **`protocol-signature-reverser`**：字段谱系、传输/算法/设备态/会话态判因、unidbg/Unicorn/纯算三级交付。

`reverse-skill-evolver` 只维护上述 Skill 的进化，不参与任务路由。

## 3. 真机与工具链

| 项 | 规则 |
|---|---|
| 设备 | 连接先 `adb devices` 确认；**多设备在线时固定唯一 serial**（`adb -s <serial>`），防误操作 |
| ADB | `adb` / `aapt` / `apksigner`（Android SDK 或 brew）；每个写/进程操作绑定唯一 serial |
| frida | 项目 venv（`./.venv`）安装 frida，client/server 版本必须匹配；设备端 frida-server 只监听 loopback，宿主 `adb forward` 临时转发，**结束精确删除** |
| 静态 | `jadx` MCP（jadx-gui 已加载 APK）为主；apktool 解资源；native SO 用 IDA（如有）/ Ghidra |
| 抓包 | `reqable` / `wiremcp`；先识别网络栈（OkHttp/Cronet/QUIC/自研）再选方案 |

**停止进程前核对 package/PID/start identity，禁止 `pkill -f` 式误杀。**

## 4. 标准闭环（缺口驱动，不要求顺序通关）

1. `android-recon`：固定 APK/version/hash、包名、serial/ABI 和可证伪目标；拉 base/splits，反编译到新目录，识别网络栈
2. 有壳则 `android-unpack`：取得真实 DEX/SO 段并通过结构验收
3. 静态索引：jadx MCP 闭合 request/API/JNI 调用链，建立字段谱系
4. `protocol-signature-reverser`：区分传输、算法、设备态、会话态四类成因；竞争假设逐个排除
5. 需要运行证据时 `android-dynamic`：最窄 Hook/trace/RPC；**验证失败回到静态/假设层，不机械升级侵入度**
6. 以「谱系×产物×证据×边界」交付；HTTP 200、可解析、Hook 命中都不是最终业务判官

## 5. 设备写入与恢复

设备/系统动作前：

- 确认唯一 serial、包名、PID/ABI、目标路径
- **保存现状**：代理/forward 设置、前台 App、frida/LSPosed 状态
- Root 文件写入前保存旧内容、owner/mode/SELinux context
- 明确恢复命令

**写后读取验证；失败立即恢复并复核。**配置读取失败不得退化为空配置覆盖。

## 6. 证据与止损

- 同接口同错误**连续 3 次即停止**同类请求，保存证据并归因
- 验证期单设备单账号；单 IP 不碰多号，不批量发送无效签名
- 确定性纯算最低 3 组任意输入对拍；100+ 组只作增强回归
- 解析型/绕过型/止损型结论分开；真机/RPC/replay/oracle 依赖显式列出
- 含活凭据的抓包先脱敏再归档；保留资产 hash 索引

## 7. 项目结构（每个目标自包含）

```text
projects/<target>/          # 目录名一律 ASCII，README.md 必须有
├── apk/                    # 原始 apk / splits / 脱壳产物
├── decompiled/            # jadx/apktool 输出
├── hooks/                  # 该项目专属 Frida 脚本(.js)
├── scripts/                # 该项目专属 Python（复现/分析）
├── so_analysis/            # native SO 分析
├── capture/                # 抓包 flows / 日志
├── artifacts/              # 截图、中间产物
├── docs/                   # 分析笔记 / 进度
└── README.md               # 目标说明 + 现状 + 入口
```

通用 Hook 放项目根 `hooks/`；第三方工具放 `downloads/`；不在仓库根散落单项目文件。

## 8. 沟通要求

- 回复用中文，技术术语保留英文
- 涉及设备写入、外部动作先给 Plan，确认后实施；纯只读分析不重复走形式关卡
- 不创建多余的项目或文件
