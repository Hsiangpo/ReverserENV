# 未随包提供的运行依赖

- ios-device、frida-mcp、ida-pro-mcp 及 .mcp.json/客户端 MCP 配置。
- connect.py、frida-mod、设备端 agent/server、SSH 私钥、Python venv、tidevice、系统服务和 IDA。
- projects/kuniu/dump_kuniu.py、projects/moyi 等历史业务脚本和 Hook；文中路径仅说明原工作区调用关系，新项目需要自己的等效实现。
- IOS_DEVICE_UDID 必须按当前设备显式配置；不复制原设备 UDID。SSH 认证由接收方配置；frida-mod/keys/id_ios 仅是路径示例，本包没有密钥。
- 27045、27042、无 ObjC bridge、指定机型/系统和 Frida 版本都是原环境契约，不是新机器已经安装或经过验证的事实。
- tools/check-ios-skills-mcp.py 和原 Cursor/ZCode MCP 同步器不在本包；它们依赖完整仓库，不能用于本轻包验收。

历史 wiki 入口在 .claude/memory 中仅指向当前 Skills 并说明原文未附带，不构成真实历史证据。
