# 已知坑清单（血泪，动手前必读）

## 脚本类

1. **zsh 不做变量分词**：`for s in $LIST` / `RS="rsync -a"; $RS ...` 在 zsh 里把整串当一个词——循环静默不执行、命令 not found。修法：显式列表、或包一层 `ssh host 'bash -s'` / `bash -c`。
2. **bash 3.2 全角贴变量**：`$var）`、`$var（`（变量名后紧跟全角字符）报 `unbound variable` 崩溃（macOS 自带 bash 3.2 特有）。一律写 `${var}`。扫描命令：
   ```bash
   grep -nE '\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7F 0-9A-Za-z_"\/\)\}\.\,\;\:\=\+\-\*\\\|\&\<\>\x27]' <脚本>
   ```
3. **install.sh 自毁史**：旧版「先 rm -rf 目标再 cp 源」在 live 目录里运行时（源=目标）把 skills 删了才退出。已修复（源=目标跳过复制 + `.new` 原子替换），但**改过 install.sh 必须两处同步**：仓库源、`~/.claude/reverse-toolchain/install.sh`。
4. **别用 `| head` 截断 install.sh 输出**：SIGPIPE 会把脚本杀在半路（实测把两个平台的 skills 软链削到 11/17）。要看输出重定向到文件再 tail；跑完必跑 verify.sh。
5. **newrev 项目名注入**：曾允许任意字符，`a&b` 污染 sed、`$()` 会被 venv 包装脚本执行。已加白名单 `[A-Za-z0-9._-]`，别删。

## 解压/文件类

6. **GBK zip**：老师 Windows 打的包含中文目录名，`unzip` 报 `Illegal byte sequence` 落一堆空目录——必须 `ditto -x -k 包.zip 目标/`。
7. **微信临时目录**：drag 下的文件随时被清，收到即归档进 `_meta/`。

## 环境语义类

8. **老师环境 ≠ 本机**：其 SKILL.md / .mcp.json / CLAUDE.md 里的 `E:\`、`C:\Users`、AdsPower、`ios-device`/`frida-orchestrator`/`reverse-index`/`algo-lab`（自建 MCP，从未随包分发）、设备 UDID/serial、27045 端口、`inject_before_load`/`trace_function`（其私改 js-reverse-mcp 的工具，npm 版没有）——一律按维护注替代方案执行；配置文件永不照抄。
9. **老师包不带 MCP**：包内 EXTERNAL_DEPENDENCIES.md 明说自建 MCP 未分发。到货后按 `_meta/20260920/待办-老师MCP到货接入指引.md` 接。
10. **路径迁移**：仓库已从 `~/Desktop/逆向` 挪到 `~/Desktop/有用/逆向`（用户手动挪的）——文档/脚本里引用路径时以 `claude-setup` 相对结构为准，别写死上层路径（skill 内部用 `<仓库>` 占位）。

11. **CloakBrowser 桌面图标**：Mac 上 `~/Desktop/Cloak浏览器.app`（osacompile 做的 AppleScript，9223 专用端口，9222 被 js-reverse MCP 常占）。重装系统要重做。

12. **老师 android_mcp 是 Windows 包**：`common/paths.py` 写死 `toolchain/bin/windows/platform-tools`，包里只有 `adb.exe`，`device/frida/` 是空目录。mac 上表现为所有 agent 的 frida-orchestrator-mcp 同时报 `No such file or directory: 'adb'`——不是某个 agent 配错。修法见 machine-install.md「安卓三件套 / adb」；老师发新版时 android-unpack 的 `scripts/adb_locator.py` 适配要保留（三个脚本经它解析 adb）。
