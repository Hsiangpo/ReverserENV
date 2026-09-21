# iOS Skills + Rules

当前 5 个 Skill：ios-recon、ios-unpack、ios-dynamic、ios-protocol-signature、ios-skill-evolver。
前四个执行 iOS 任务，最后一个用于明确请求的维护。

先读 PORTABLE.md。把本目录放到最终使用位置，作为独立的 iOS 项目根；迁移到已有项目时先备份并合并规则，不覆盖不相干配置。

Windows 安装 Python 3.12 或更高版本，在本目录执行：

    python -X utf8 prepare_skills.py
    python -X utf8 prepare_skills.py --check

脚本为 .cursor/.zcode/.codex/.pi 创建指向当前 .claude/skills 的本地 junction，并为 .zcode/memory 创建指向当前 .claude/memory 的 junction。ZIP 不携带旧机器 junction。
若目标位置已有不相符的文件夹或联接，脚本会停止，不覆盖或删除；应人工核对并合并原有内容。

Claude Code 使用 .claude/skills；Cursor 同时使用 .cursor/rules；ZCode 按源项目拓扑使用 .zcode/skills。在客户端中打开完整平台项目根，实际自动选用仍需在所用版本中验证。

移动已经初始化的目录后，不要继续使用指向旧位置的 junction。保留原目录数据，优先从 ZIP 在新位置重新解压并初始化。

Skill 更新后再次运行 prepare_skills.py 可刷新协议 Rule 的正文指纹；其他 Rules 摘要仍须人工语义核对。不要运行源仓库的 MCP 同步命令代替本轻包初始化。
