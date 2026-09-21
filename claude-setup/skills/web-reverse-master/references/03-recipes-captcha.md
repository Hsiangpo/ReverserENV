# 验证码取证、CDP 诊断与字体分析

当前缺口跨初始化、源码、环境、参数或业务验证时由 master 定位；协议和入口已明确时交 captcha-solver。按模式选择需要的工作面，无感/评分模式不强制获取图片或生成轨迹。

## 证据工作面

| 工作面 | 记录与当前参考 |
|---|---|
| 初始化 | 当前资产 URL/hash、产品/客户端架构、场景、初始化响应与会话字段 |
| 图像和事件（若有） | 首次图片原件、尺寸/alpha、CSS 坐标与时间单位；见 [识别与行为数据](../../captcha-solver/references/recognition-and-trajectories.md) |
| 参数与编码 | 实际发送调用的输入输出、序列化与编码顺序、上游 key；见 [验证码参数](../../captcha-solver/references/encryption-and-providers.md) |
| 环境与异步 | realm、调用时刻、资源与异步完成状态；见 [运行时取证](13-runtime-observation-and-rebuild.md) |
| 验证与业务 | 厂商内部结果、容灾/测试分支、票据消费和业务对象；见 [二次校验与容灾](../../captcha-solver/references/verification-and-fallback.md) |

只从当前调用链确认 AES/RSA/自定义编码，不按厂商名、长度或旧样本常量选择算法。票据生成不是最终验收，厂商验证和业务消费分别记录。

## 图像与行为

- 图片可能一次性消费，优先保留首次响应供本地识别，不能反复获取造成材料失效。
- 滑块、点选、宫格与旋转使用当前题型、图片和坐标约定；模板匹配需阈值和误差样本，不能低置信也返回距离。
- 协议确实消费事件时，追踪真实事件序列、相对/绝对坐标、时间源和单位；不预置“真人速度”、过冲或随机等待。
- 算术 OCR 的文字是不可信输入。仅解析题型允许的操作符和有界整数；用 captcha-solver 的白名单解析器，不执行 OCR 文本。
- 外部识别服务的接口、数据传递和费用须在任务范围内；本地库与服务按实际能力选，不固定通用优先级。

## CDP 仅作短时取证

路线 D/C 的适用条件、启动与重载见 [工具参考](08-tool-reference.md)。浏览器端执行用于定位输入输出或建立 oracle，不能把浏览器内 axios 请求桥包装成生产协议客户端。

使用自带 [cdp_bridge.py](../scripts/cdp_bridge.py)，不维护第二套 WebSocket 接收器。先从当前已授权页面确定 page WebSocket URL；端口发现结果必须与目标页核对，不能把第一个 target 当作本案页面。

命令形态（将占位 URL 换成已确认的本案 page endpoint）：

```powershell
& .\venv\Scripts\python.exe .claude\skills\web-reverse-master\scripts\cdp_bridge.py --ws-url 'ws://127.0.0.1:9222/devtools/page/<page-id>' --expr 'document.title'
```

Python API 的契约是 `CDPBridge(ws_url=...)` → `connect()` → `evaluate(...)`，并在 `finally` 中 `close()`。已有离线 transport 可直接注入，不需要浏览器。
`evaluate` 返回完整 CDP 响应 envelope；先判断 `error` / `result.exceptionDetails`，再按 RemoteObject 的 type/value/unserializableValue 读取结果，不能假设每次都有 `value`。
自带桥按请求 id 关联响应并收集插入事件；事件、错误与目标值不得混为一次成功输出。跨页/iframe 的执行上下文需单独确认。

## 字体映射分析

字体混淆属于内容还原，不必进入验证码协议。先固定字体文件 hash、文本 codepoint 与页面实际字体选择，再分析本地字形：

- 区分 TrueType `glyf`、CFF/CFF2；cmap 只给 codepoint→glyph name，不直接给业务字符含义。
- TrueType 字形使用已计算的 `xMin/xMax/yMin/yMax` 边界，几何宽高取差值；不要读取不存在的 `glyph.width/glyph.height`。advance width 属于 `hmtx`，与轮廓宽度分开。
- 空字形和复合字形独立处理；必要时通过 glyph set/BoundsPen 求实际边界，不假定每个 glyph 都有简单轮廓字段。
- 几何指纹可能碰撞，需已知文本或渲染对照确定映射；字体版本变化后重新核验，不能从“形状相似”推导逐字符正确。

交付证据应包含原字体/文本锚点、映射来源、已确认字符和未知字符；解码可显示不等于业务接口验收。
