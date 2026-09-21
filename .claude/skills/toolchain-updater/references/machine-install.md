# 任务 B：新 Mac / 重装

## 新 Mac / 重装

```bash
bash <仓库>/claude-setup/install.sh
```
幂等，重跑=更新。装完跑 `claude mcp list` 体检（roxybrowser 需 API Key + 客户端开着才 Connected，属正常）。

前置：node 20.19+、Claude Code、Xcode CLT。缺依赖时脚本会给 ❌ 和补装提示，装完重跑即续装。


## ZCode CLI（Linux）

`npm i -g zcode-app-cli`（非官方终端客户端，含官方 runtime）。配置：`~/.zcode/cli/setting.json`、provider 在 `~/.zcode/v2/provider_config.json`。OAuth 只支持 macOS，其他平台配 API key。
