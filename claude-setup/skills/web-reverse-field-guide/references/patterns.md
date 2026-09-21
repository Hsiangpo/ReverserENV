# 失败模式、正确路径与工具检查

> 以下 E/S/C 表是历史样本索引，本次未复核原始资产 hash 与部署版本。原因与修复只适用于取得相应对照证据的样本；错误码、长度、静态环境值不能替代当前因果实验。新协议状态失败模式见 [R1–R7](web-protocols.md)。

## 三、失败模式速查表

### 补环境类

| # | 现象 | 根因 | 修复 | 来源项目 |
|---|------|------|------|---------|
| E1 | Cookie生成后请求400 | 历史涉及 Canvas 返回值差异 | 同输入对照 API 语义与输出，采样值注明 fixture | 189.cn瑞数6 |
| E2 | VM沙箱 _$xx undefined | 闭包变量被VM隔离打断 | 换 eval() 全局作用域执行 | 189.cn瑞数6 |
| E3 | Maximum call stack | Proxy get trap 自引用 | 用外部对象存储，不通过Proxy访问 | 189.cn瑞数6 |
| E4 | tagName of undefined | DOM节点 parentNode 未设置 | createElement 返回时设 parentNode | 189.cn瑞数6 |
| E5 | GBK编码错误 | Windows subprocess默认GBK | 明确实际编码并严格解码；二进制保留 bytes，替换字符只能用于另存的展示副本 | 189.cn瑞数6 |
| E6 | jsdom初始化失败 | 删global.process后jsdom依赖process | jsdom初始化必须在删process前 | 189.cn瑞数6 |
| E7 | aS VM .apply崩溃 | 字节码操作数为null | 关键操作添加null容错 | 大众点评 |
| E8 | ct样本935字符，与基线不同 | 历史涉及 devcInfo/tdat_ctx | 1650字符仅是旧样本长度，需逐字节及消费者验证 | 京东jcap |
| E9 | webgl=False导致5014 | jsdom无WebGL实现 | 补全WebGL参数+状态机mock | 抖店罗盘 |

### 签名/加密类

| # | 现象 | 根因 | 修复 | 来源项目 |
|---|------|------|------|---------|
| S1 | code=38环境异常 | 旧样本缺登录态Cookie/Headers | 对照当前登录态/上下文，不复制固定 Chrome 模板 | Boss直聘 |
| S2 | SM2签名服务端拒绝 | 签名了encData而非原始data | 先签后加密（签名在加密之前） | 国家医保 |
| S3 | 三次加密误判 | Hook到的调用非目标功能 | AST反混淆→可读代码追踪 | 绎通OUC |
| S4 | X-S-Common缺失 | 旧实现未闭合新增字段 | 跟踪当前 writer/来源，按目标评估还原或明确 oracle 依赖 | rednote |
| S5 | 标准MD5输出不同 | SDK使用魔改CryptoJS | 加载原始SDK的MD5模块 | 京东H5ST |
| S6 | 5014拒绝 | 换客户端后结果变化，原因需分层 | 同上下文比较 TLS/HTTP/header 与字节，不由码定因 | 抖店罗盘 |
| S7 | 3104错误 | SO_GL的CODE值不匹配 | 提取正确SO_GL模板(CODE=114) | Air Greenland |

### 验证码类

| # | 现象 | 根因 | 修复 | 来源项目 |
|---|------|------|------|---------|
| C1 | 模拟事件被拒绝 | isTrusted=false不可伪造 | Hook WebCrypto+fetch走协议 | 涂鸦智能 |
| C2 | captchaBody无法复现 | AES-GCM在WASM中执行 | 本地AES-GCM加密器 | 抖店邮箱 |
| C3 | 反调试阻止DevTools | anti_automation.js检测 | Node.js本地加载WASM绕过 | SpiderDemo |

---

## 四、正确路径模式库

> 各场景的理想执行路径，配合 master 的路线设计方法使用。

### 模式A：框架类站点（若依/Vue/React+标准加密）

```
实际弯路：Hook反复折腾 + 3次误判 → 8小时
正确路径（30分钟）：
  1. Phase 0: 搜索"[框架名] 逆向" → 通常有现成方案
  2. Phase 1: 抓包确认1次 → 明确接口格式
  3. Phase 2: 保存JS → AST反混淆 → 直接搜 "encrypt"/"secretKey"
  4. Phase 4: 纯Python实现（AES+RSA）→ 一次通过
```

### 模式B：重防护站点（瑞数/Akamai/reese84）

```
正确路径：
  1. Phase 0: 确认防护类型（瑞数=P Cookie格式, reese84=iv8字段, Akamai=sensor_data）
  2. Phase 1: 按 D/A/C/No MCP 的当前适用条件取得同会话流量
  3. Phase 2: 用 watch() Proxy 采集 SDK 访问的环境属性清单
  4. Phase 3: 选择 env-patcher Level 2+ 模板
  5. Phase 4: 对照作用域/API/时序语义，逐 checkpoint 验证当前实现
  关键：采样值是注明来源的 fixture；既不填占位符冒充成功，也不硬编码为通用算法
```

### 模式C：签名失效/新增Header

```
正确路径：
  1. 先对比：旧请求 vs 新请求的Headers差异
  2. 新增Header简单（静态值/简单加密）→ 本地还原
  3. 新增Header复杂（需要完整SDK上下文）→ 果断切CDP桥
  决策标准：依本案目标/止损线，列明缺口和假设后再决定；CDP 产物标注 oracle 依赖
```

### 模式D：WASM加密挑战

```
正确路径：
  1. 下载 .wasm 文件 + glue JS
  2. 尝试 Node.js 原生 WebAssembly.instantiate 加载
  3. 实例化成功只证明加载；还要核对入口、真实输入输出及非样例 oracle 字节对拍
  4. 若失败（缺导入函数）→ IDA分析WASM导入表 → 逐一补全
  关键：imports、realm、状态与输出分别验证；WASM 可加载不能替代算法或业务验收
```

### 模式E：验证码纯协议

```
正确路径：
  1. 由当前资产和请求识别模块，区分无感、交互、评分或托管挑战
  2. 有图像时才识别；有行为字段时才按真实事件/单位/时序建谱系
  3. 从实际发送调用定位算法、编码与上游值，不预设 AES 或固定轨迹
  4. 分别记录前端完成、供应商内部校验、测试/容灾和业务消费
  关键：无图模式不硬套取图流程，票据出现和状态码不能作为最终接受
```

---

## 五、反模式教训榜

> 这45+项目踩过的坑，按“禁止动作→后果→正确做法”格式。

| # | 反模式 | 后果 | 正确做法 |
|---|--------|------|---------|
| 1 | 在缺公开背景或框架指纹时仍跳过检索 | 走了8小时弯路 | 只在该类缺口存在时进 Phase 0，搜索 `{站点} 逆向` 或框架指纹；已有真实流量/入口时直接进当前缺口 |
| 2 | Hook到调用就当结论 | 3次加密误判 | 必须追到调用链源头确认属于目标功能 |
| 3 | 连续猜测不回退 | ECB/CBC/PKCS7反复试 | 猜2次失败→回退到AST反混淆读源码 |
| 4 | 执行上下文与原版不同 | 闭包/realm/对象身份漂移 | 按实际入口保留同一 realm 与绑定关系，不按品牌固定全局执行 |
| 5 | Canvas指纹用占位符 | 旧样本出现400 | 对齐当前输入/输出与语义，不能由400直接证明Canvas原因 |
| 6 | 路线与目标/止损线不匹配 | 历史耗时过长 | 列明缺口后按已确认目标评估；不以固定天数证明纯算不可行 |
| 7 | 签名不对就改算法 | 实际是Cookie/Headers缺失 | 签名排查优先级最低（先查上下文） |
| 8 | Hook递归覆盖 | Maximum call stack | 保存原始引用，只Hook一次 |
| 9 | 先导航后Hook | Hook错过初始化 | 先inject_before_load再导航 |
| 10 | subprocess用默认编码 | Windows GBK解码错误 | 按实际编码严格解码；不得以 errors='replace' 静默改变协议字节 |
| 11 | jsdom referrer='' | 非法URL导致初始化失败 | 省略referrer或填合法URL |
| 12 | 删process后初始化jsdom | jsdom内部依赖process | jsdom初始化必须在删process之前 |
| 13 | AST反混淆报错就绕过 | 手动解效率极低 | 报错应立即修复（成本通常很低） |
| 14 | 不调用已有Skill | 重复造轮子 | ast-deobfuscation/captcha-solver该用就用 |
| 15 | 一次改多个变量 | 无法定位真正原因 | 一次只改一个变量 |

---

## 六、工具快查

### subprocess 编码

```powershell
# Python 必须用 venv 全路径
.\venv\Scripts\python.exe script.py

```

```python
import subprocess

# cmd 是已确认的可执行文件与参数列表；保留 stdout 原始字节
completed = subprocess.run(cmd, capture_output=True, check=True, timeout=30)
# 仅当该输出契约为 UTF-8 文本时解码；其他二进制不经过文本转换
text = completed.stdout.decode('utf-8', errors='strict')
```

### 补环境执行模式选择

```
SDK类型           → 推荐执行模式
─────────────────────────────────
瑞数6/JSVMP      → eval() 全局作用域（闭包依赖全局）
极验4/阿里AWSC    → vm.createContext（标准SDK可隔离）
京东jcap WASM    → Node.js 原生 WebAssembly（不需要浏览器）
大众点评 aS VM   → eval() + null容错（字节码解释器需要）
通用小型SDK       → vm.createContext（安全隔离）
```

### TLS 指纹对齐

```python
# 可选传输对照；是否需要由当前证据决定
from curl_cffi import requests as cffi_requests
import os
session = cffi_requests.Session(impersonate=os.environ['CASE_TLS_PROFILE'])

# 记录当前 UA/Client Hints、ClientHello、ALPN、HTTP/header 与 Cookie 上下文
# profile 名称相同不证明实发一致；换库成功也不能唯一归因为 JA3
```

---
