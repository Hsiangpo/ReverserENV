# 未随包提供的运行依赖

- 三个自建 Android MCP 及 IDA、Reqable 等外部集成；未附 .mcp.json 和任何用户配置。
- Android SDK/ADB、JADX、apktool、Frida client/server、Root 设备与驱动。
- 随 Skill 提供的脱壳 Python 脚本仍按相对路径寻找 android_mcp/toolchain/bin/windows/platform-tools/adb.exe。缺失时应停止并按当前环境配置，不得调用错误设备。
- enhanced_dexdump_runner 需要对应 Python 环境中的 frida-dexdump.exe，或 ANDROID_MCP_FRIDA_DEXDUMP 指定入口。
- serial 使用显式参数或 ANDROID_SERIAL；文档中的设备占位符必须用当前唯一目标替换。
- 维护文档中的全仓测试、MCP 同步器、用户目录验证器和历史报告未随包提供；这些命令不是轻包验收步骤。

本包验收仅覆盖文件、Rules/Skill 结构、镜像和引用，不证明设备或外部工具可用。
