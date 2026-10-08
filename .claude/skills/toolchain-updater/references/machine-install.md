# 任务 B：新 Mac / 重装

## 新 Mac / 重装

```bash
bash <仓库>/claude-setup/install.sh
```
幂等，重跑=更新。装完跑 `claude mcp list` 体检（roxybrowser 需 API Key + 客户端开着才 Connected，属正常）。

前置：node 20.19+、Claude Code、Xcode CLT。缺依赖时脚本会给 ❌ 和补装提示，装完重跑即续装。


## ZCode CLI（Linux）

`npm i -g zcode-app-cli`（非官方终端客户端，含官方 runtime）。配置：`~/.zcode/cli/setting.json`、provider 在 `~/.zcode/v2/provider_config.json`。OAuth 只支持 macOS，其他平台配 API key。

## 安卓三件套 / adb（换机器必看）

- 老师原包在 `claude-setup/mcps/`（**gitignore，不随 git 走**）。新机器 `git clone` 后要把 `mcps/安卓/android_mcp.zip` 手动拷进同一位置，再跑 install.sh：自动解压到 `vendor/android_mcp`、建 venv（frida 16.5.9 + mcp<2）、注册三件套。
- adb：install.sh 下载 Google 官方 platform-tools 到 `vendor/platform-tools`，软链 `~/.local/bin/adb`。老师包只有 Windows `adb.exe`，mac 上永远用不上。
- 注册 frida-orchestrator-mcp 时带 `ANDROID_MCP_ADB=<本机 adb 绝对路径>`——GUI 启动的 agent（Antigravity / Codex App 等）PATH 里常没有 `~/.local/bin`。镜像到其他 agent 配置时同样带上；这个绝对路径只写进本机配置，**不写进本仓库**。
- 魔改 frida-server `new-server-arm64-16.5.8-dev.11` 不在老师包里（`toolchain/device/frida/` 是空目录）。拿到后放进 `vendor/android_mcp/toolchain/device/frida/`，再用 `bootstrap_device_toolchain` / `push_patched_frida_server`。
- 体检：`frida-orchestrator-mcp` 的 `toolchain_status` 里 `adb.exists` 为 true、`device.error` 为空（未接设备时 devices 为空列表属正常）。
