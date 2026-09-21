# 逆向工具链（macOS · 何老师 20260920 内部版）

Web/JS + iOS + Android 协议逆向的 agent 工具箱：**17 个 skills + 10 个 MCP + 全局逆向准则 + 一键建项目**。自包含可搬移，丢给任何 agent 说「装一下」即可。

## 一分钟装好（新机器）

前置：node 20.19+、Claude Code、Xcode CLT（缺了脚本会逐项 ❌ 提示，补齐重跑即续装）。

```bash
bash <本目录>/claude-setup/install.sh
```

装什么：17 个 skills 软链到 `~/.claude/skills`、`~/.codex/skills`、`~/.zcode/skills` 三平台 → 全局逆向准则挂载（`~/.claude/CLAUDE.md` @include + `~/.codex/AGENTS.md` 内联）→ `newrev` 进 PATH → 依赖软件（CloakBrowser/Reqable/JDK21+jadx/frida/wedecode/wabt，约 450MB；`--skip-downloads` 跳过）→ 注册 10 个 MCP（9 自动 + roxybrowser 需 API Key）。**幂等，重跑=更新。**

## 日常怎么用

**新项目**：
```bash
newrev 项目名 https://目标网址            # Web/JS
newrev --ios 项目名 com.bundle.id        # iOS
newrev --android 项目名 com.package.name # Android
```

**已有项目里接入**：cd 进项目目录，`newrev --here [--ios|--android] [URL]`

**懒得记命令**：直接跟 agent 说「看 `~/Desktop/有用/逆向`」——入口文档（CLAUDE.md / AGENTS.md）定义了标准流程：体检（缺才补）→ 判断平台 → 套模版 → 开工。

建好的项目长这样：`CLAUDE.md`（规则本体：协议优先/Phase 0-4/Phase 3 确认门槛/止损）+ `AGENTS.md`（薄壳）+ `.venv` + 目录骨架（web 用 `sites/`，移动端用 `projects/`）+ **项目级 agent 配置**：`.agents/skills/`（平台子集软链，Codex/ZCode 项目内入口）、`.zcode/`（config.json servers 保持空，memory/ 项目记忆）、`.codex/config.toml`（保持空，防分叉）。

## 更新（老师发新包时）

1. 解压新包，替换 `claude-setup/skills/` 里对应的 skill 目录（只留最新，旧的直接删）
2. 重跑 `install.sh`（三平台软链自动跟上，全局准则同步）
4. 老师包的规则/配置原版归档到 `claude-setup/_meta/<日期>/`，只作参考不照抄（含其 Windows 私人路径）

## 目录地图

```
逆向/
├── CLAUDE.md / AGENTS.md   ← agent 入口（Claude 系 / Codex 各一份）
├── README.md               ← 你在这
└── claude-setup/
    ├── install.sh          ← 一键安装/更新
    ├── bin/newrev          ← 建项目（--here 就地接入）
    ├── skills/             ← 17 个 skill 真源
    ├── rules/              ← 全局逆向准则真源（两份 .md）
    ├── templates/          ← CLAUDE.md / CLAUDE-ios / CLAUDE-android / 权限白名单
    └── _meta/20260920/     ← 老师包归档（原样留档）+ 待办-MCP到货接入指引
```

## 速查

| | |
|---|---|
| Skills | 17 个三平台全局（web 6 / 安卓 6 / iOS 5，何老师 20260920 版 + 本机适配注） |
| MCP | js-reverse / js-reverse-cloak / chrome-devtools / wiremcp / reqable / jadx / frida-agent / wedecode / roxybrowser-playwright 全局注册；roxybrowser 需 Key 且客户端要开着 |
| 健康检查 | `claude mcp list` |
| 用前要开着 | Reqable（菜单栏 R 图标）、jadx-gui（加载 apk 后 jadx MCP 才有内容） |
| 全局准则 | 每轮生效：禁词牌照 / 3 次止损 / 谱×物×证×界交付 / ①②③三分类（真源 `claude-setup/rules/`） |
