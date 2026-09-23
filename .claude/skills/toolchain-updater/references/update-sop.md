# 任务 A：版本更新 SOP（何老师发新包）

## 0. 取件

微信拖来的文件落在（临时目录，用完会被清，及时归档）：
```
~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_ukegs6mqjhx422_ec66/temp/drag/
```

## 1. 解压

```bash
cd /tmp && rm -rf upd && mkdir upd && cd upd
cp ~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/*/temp/drag/<包>.zip .   # 先拷出来（drag 是临时目录）
unzip -q <包>.zip -d web/          # 普通包
ditto -x -k <GBK包>.zip pkg/       # 老师 Windows 打的包（unzip 报 Illegal byte sequence 时必用 ditto）
find . -maxdepth 4 -type d         # 看结构，定位真正 skills 目录（.claude/skills/ 或裸 skills/）
```

## 2. diff 摸底（先给用户看再动手）

逐 skill `diff -r 新包 <live>`，输出三类清单：更新（N 处不同）/ 新增（本地无）/ 相同。特别注意老师 CLAUDE.md 里宣布「已合并/已清理」的旧 skill——那是要删的信号。

## 3. 替换（源 + live 双写）

**zsh 不分词**：`for s in $LIST` 会把整串当一个名字。用显式列表：

```bash
SRC="<仓库>/claude-setup/skills"
LIVE="$HOME/.claude/reverse-toolchain/skills"
for s in skill1 skill2; do
  rm -rf "$SRC/$s" "$LIVE/$s"
  /bin/cp -R "/tmp/upd/新包/$s" "$SRC/$s"
  /bin/cp -R "/tmp/upd/新包/$s" "$LIVE/$s"
done
```

新增 skill 另需补三平台软链：`for d in ~/.claude/skills ~/.codex/skills ~/.zcode/skills; do ln -sfn "$LIVE/<名>" "$d/<名>"; done`

## 4. 重打维护注（替换会冲掉旧注）

对含老师私有环境引用的 skill，在 frontmatter 第二个 `---` 之后插入对应模板（日期换成当天）：

**WEB**（web-reverse-master 等）：
```markdown
> ⚠️ **本机环境适配（<日期> 维护注）**：本机为 macOS，无 AdsPower / ida-pro-mcp / sequential-thinking，js-reverse-mcp 用 npm 版（**无** `inject_before_load` / `trace_function`，注入=先 `evaluate_script` 再 `navigate_page` 或注入后刷新；函数追踪=`set_breakpoint_on_text`+`get_paused_info`+`step`）。路线 A/C（AdsPower）↔ 本机路线 3（RoxyBrowser：`roxybrowser` 管 profile/代理，`roxybrowser-playwright` 管页面）；wasm 用 wabt（`wasm2wat`）。`../../../.claude/mcp.md` 本机不存在；`tools/reverse-chromium/` 文档在 `~/.claude/tools/reverse-chromium/`（内核补丁是 Windows 向，mac 路线 2 用 js-reverse-cloak 代替）。指纹/商业指纹墙场景优先 RoxyBrowser。
```

**IOS**：
```markdown
> ⚠️ **本机环境适配（<日期> 维护注）**：本机为 macOS，**无** `ios-device` MCP（老师自建未随包分发）、无 ida-pro-mcp。设备连接用 `frida-agent` MCP / 项目 venv frida / `pymobiledevice3`；SSH 直连设备用 mac 原生工具；提头优先 mac 原生 `class-dump` / `otool`。下文提及 ios-device 工具（`ios_info`/`ios_ssh` 等）的段落按此替代执行。
```

**ANDROID**：
```markdown
> ⚠️ **本机环境适配（<日期> 维护注）**：本机为 macOS，**无** `frida-orchestrator` / `reverse-index` / `algo-lab` MCP（老师自建未随包分发）。设备操作用 `adb`（mac 路径，非 `android_mcp\toolchain\...adb.exe`——该 Windows 路径段按 `brew install android-platform-tools` 的 adb 替代）+ 项目 venv frida；静态索引用 `jadx` MCP（jadx-gui）+ grep 替代 reverse-index；算法对拍脚本自行落盘运行替代 algo-lab。serial 用显式参数或 `ANDROID_SERIAL`。
```

判断该打哪种注：grep 新 SKILL.md 是否含 `AdsPower|tools/reverse-chromium`（WEB）、`ios-device`（IOS）、`frida-orchestrator|adb.exe`（ANDROID）。

## 5. 删旧（只留最新）

老师新版已合并的旧 skill：源 + live + 三平台软链三处一起删。历史先例：20260920 版把 trace + 6 个 web-reverse-* 工作流 skill 并入 master 的 `references/10-staged-method.md` 后删除，最终 17 个。

## 6. 归档

老师包原样存 `claude-setup/_meta/<日期>/`（分 web/android/ios 子目录放规则与配置原版），仅参考不安装。同时把有用的新规则提炼进 `claude-setup/rules/`（全局准则真源）并同步 `~/.claude/` + `~/.codex/AGENTS.md`。

## 7. 文档口径（6 处，数字/表格/用法变了才改）

根 `CLAUDE.md`、`AGENTS.md`、`README.md`、`claude-setup/README.md`、`claude-setup/install.sh` 头注、`templates/CLAUDE.md` §6。检查口径：skill 数量、技能表行、两种用法句。


## 7.5 项目级副本同步（本机策略：全局不挂载，项目按需）

本机 20260922 起 skills 全局卸载、按项目挂载。老师更新 web 六件套后，同步两个工作项目的副本：

```bash
for p in ~/Develop/Masterpiece/System/GPTEAM ~/Develop/Masterpiece/System/AutoSubcribe; do
  for s in web-reverse-master param-encryptor captcha-solver env-patcher ast-deobfuscation web-reverse-field-guide; do
    rm -rf "$p/skills/$s"; cp -R "$LIVE/$s" "$p/skills/$s"
  done
done
```
（项目侧 `.claude/.agents/.zcode` 的 skills 目录用相对软链 `../../skills/<名>`，随项目 git 走；若项目需要安卓/iOS 技能，同法加对应 skill 名。）

## 8. 终验 + 提交

```bash
bash <仓库>/.claude/skills/toolchain-updater/scripts/verify.sh
cd <仓库> && git add -A && git commit -m "更新至何老师<日期>版"   # 有远端则 push
```
