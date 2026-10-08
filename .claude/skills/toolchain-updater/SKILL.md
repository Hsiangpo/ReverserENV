---
name: toolchain-updater
description: >-
  维护本逆向工具链仓库（真源 → live → 三平台软链）的全套操作：何老师发新版 skills/规则时的更新替换、新 Mac 安装、三平台同步与终验。触发词：老师发包了、更新工具链、更新逆向文件夹、装到新机器、维护逆向仓库。
---

# 逆向工具链维护（本仓库唯一更新入口）

本仓库是何老师逆向工具链的**唯一真源**。同步链路：

```
claude-setup/（源，改这里）
  → ~/.claude/reverse-toolchain/（live 实体，install.sh 复制）
    → 项目 .claude/skills（newrev 挂载，默认）／ 或 --global-skills 时 ~/.claude|~/.codex|~/.zcode/skills 三平台软链（指向 live）
```

铁律：**一切改动从源开始向下同步；任何时刻 `diff -rq 源/skills live/skills` 必须零差异**；老师 Windows 环境的路径/工具/设备信息永不照抄（见维护注）。

## 任务路由

| 用户说 | 任务 | 文档 |
|---|---|---|
| 「老师发包了」「更新工具链/逆向文件夹」 | **A. 版本更新**（解压→diff→替换→维护注→删旧→归档→文档→提交） | [references/update-sop.md](references/update-sop.md) |
| 「装到新 Mac」 | **B. 机器安装**（install.sh 一条命令） | [references/machine-install.md](references/machine-install.md) |
| 「建个项目」 | **C. 项目接入**（newrev 四种模式，产物含项目级 agent 配置） | 一般由用户在目标项目里做；本仓库只保证 `bin/newrev` 可用 |

## 任务 A 速览（细节必须读 update-sop.md）

微信文件在 `~/Library/Containers/com.tencent.xinWeChat/.../temp/drag/`；**GBK 包用 `ditto -x -k` 解压**（unzip 会报 Illegal byte sequence）。替换 = 源 + live 双写 → 重打维护注（模板在 update-sop.md）→ 老师已合并的旧 skill 连软链一起删 → 原包归档 `_meta/<日期>/` → 文档口径（6 处）同步 → `git commit`。

## 终验（每次更新必跑）

```bash
bash <仓库>/.claude/skills/toolchain-updater/scripts/verify.sh
```

脚本覆盖：源=live 零差异、三平台软链计数、install.sh/newrev 语法、bash 3.2 全角贴变量扫描、newrev 四模式干跑。

## 红线

- 只留何老师最新版；新版已合并的旧 skill 即删（源/live/三平台软链三处一起）。
- `_meta/` 只归档不安装不照抄；rules/ 是全局逆向准则真源（改动需同步 `~/.claude/` 与 `~/.codex/AGENTS.md`）。
- 动手前先看 [references/pitfalls.md](references/pitfalls.md)（zsh 不分词 / bash 3.2 全角坑 / install.sh 自毁史等血泪清单）。
