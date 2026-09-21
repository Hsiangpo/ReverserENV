# 核心排错决策树与案例

## 一、排错决策树

> 先定位协议状态，再选择单变量实验。以下案例来自旧记录，本次未复核原始抓包、资产 hash 和部署版本；保留观察结果，不将当时假设提升为厂商通则。

```
请求失败/返回异常
├─ HTTP 400/401/402/403/429 或嵌套拒绝
│   ├─ 1. 响应来源/Content-Type/body/认证头 → 登录、挑战协商、付费或业务哪一层
│   ├─ 2. 记录每层 success/error；normal/fallback/test 分开（R1/R2）
│   ├─ 3. PAT 401/付费 402 需完整协商字段，不直接当登录失败（R3/R4）
│   └─ 4. 对照同会话基线，保留状态；不默认清票、换代理或重登录
│
├─ 业务码 5014/code=38/BLOCK=True/code=-2 等
│   ├─ 1. 登录态 Cookie → wt2/zp_at/session_id 等是否有效
│   ├─ 2. Headers 完整性 → sec-ch-ua/sec-fetch-*/traceparent 等12+项
│   ├─ 3. 传输 → ClientHello/ALPN/HTTP/headers 的实际差异，JA3不能唯一映射UA
│   ├─ 4. 请求依赖序 → 是否跳过了前置请求（token/config）
│   └─ 5. 签名算法 → 按首个分歧核输入串/时间戳/编码，不固定排查优先级
│
├─ 签名不一致（本地输出 ≠ 浏览器输出）
│   ├─ 1. 输入串 → 编码(UTF-8/GBK)、字段排序、空值处理
│   ├─ 2. 时间戳 → 毫秒 vs 秒、服务器时间偏差
│   ├─ 3. 自定义算法 → 标准MD5/SHA输出是否真的和浏览器一致
│   ├─ 4. 中间层 → 签名后是否还有 Base64/URL编码/XOR 等变换
│   └─ 5. 多层加密顺序 → 先签后加密 vs 先加密后签
│
├─ 补环境 SDK 崩溃
│   ├─ TypeError: xxx is not a function → 缺 API mock
│   ├─ Maximum call stack → Proxy 自引用 / Hook 递归覆盖
│   ├─ Cannot read properties of undefined → DOM 节点 parentNode 未设置
│   ├─ SDK 死循环/超时 → setInterval 未清理 / Promise 未 resolve
│   └─ VM 沙箱变量断裂 → 闭包引用失败，换全局作用域执行
│
└─ 加密方式误判
    ├─ Hook 捕获到调用但签名不对 → 确认是否属于目标功能（可能是其他模块）
    ├─ 算法确认但 Key/IV 不对 → Hook 加密函数的实际运行时参数
    ├─ 多次猜测均失败 → 停止猜测，回退到 AST 反混淆在可读代码中追踪
    └─ 没搜到加密关键词 → 可能是自定义编码（Base64变体/XOR/位运算）
```

---

## 二、实战排错案例库

> 每个案例只保留核心证据链，不重复 master 的证据链排错方法。

### 案例1：瑞数6 补环境生成 Cookie 但 400

**项目**：189.cn 瑞数6反爬  
**现象**：P Cookie 成功生成，二次请求 HTTP 400

```
Observe:
  - Cookie 字符串长度正确，格式符合预期
  - 同样的 Cookie 在浏览器中可正常使用
  - 400 仅记录响应状态，不能排除挑战拒绝或其他责任层

Hypothesize:
  "服务端校验了 Cookie 生成过程中的环境指纹，不仅看最终 Cookie 值"

Test（逐层）:
  1. Function.prototype.toString → mock函数返回源码非[native code] → 修复 → 仍400
  2. Canvas.toDataURL() → 返回'data:image/png;base64,AAAA'（固定占位符）
     → 旧记录称采集值替换后通过；需原始同条件 trace 才能确认服务端校验因果

Fix:
  1. WeakMap + markNative 标记所有API函数 → toString返回[native code]
  2. Canvas.toDataURL() 返回从真实浏览器采集的base64图像数据
  两项同时修复后 400 消失

教训：该样本提示 API 返回语义可形成差异；不能由400归因Canvas，采样重放值不是生成算法。
```

### 案例2：Boss直聘 code=38 环境异常

**项目**：Boss直聘职位列表采集  
**现象**：所有API返回 code=38 "环境异常"，签名算法已正确还原

```
Observe:
  - __zp_stoken__ 本地输出与浏览器完全一致
  - 换不同签名组合均失败
  - 换不同时间戳也失败

Hypothesize:
  "问题不在签名，在请求上下文（Cookie/Headers）"

Test:
  1. 对比完整 Headers → 缺 sec-ch-ua/sec-fetch-* 等12项 → 补全 → 仍38
  2. 检查 Cookie → 缺 wt2/zp_at/wbg 三个登录态 → 注入 → code=0 成功

Fix:
  - 根因是「缺少有效登录态」而非「签名算法错误」
  - 当时方案：cookie_config.json + Chrome 131 Headers（历史环境，不作当前默认）
  - 当时登录态样本未使用 __zp_stoken__；是否必需由当前消费者验证

教训：
  错误码不能决定根因；从同上下文请求的首个分歧检查会话、字段与传输。
  登录态重放是有状态依赖型方案，不能声称算法还原或默认复用其他会话。
```

### 案例3：抖店罗盘 5014 风控（双重指纹）

**项目**：compass.jinritemai.com 验证码  
**现象**：captcha/verify 返回 5014，补环境看似完整

```
Observe:
  - 第一轮修复补全了 screen/webgl/audio → 仍 5014
  - gen_captcha_sdenv.js 逻辑看似正确

Hypothesize:
  "存在网络层指纹校验——不仅检查运行时环境"

Test:
  1. 浏览器指纹对齐 → webgl/screen修复 → 仍5014
  2. Wireshark 抓 TLS ClientHello → requests 的 JA3 ≠ Chrome
  3. 换 curl_cffi(impersonate='chrome131') → 5014 消失

Fix: 双管齐下
  - gen_captcha_sdenv.js 补全浏览器指纹
  - requests → curl_cffi 对齐 TLS 指纹

教训：换客户端会同时改变 TLS/ALPN/HTTP/header 等因素；历史结果提示传输方向，尚不能仅凭5014唯一归因为JA3。
```

### 案例4：国家医保平台 code=-2

**项目**：fuwu.nhsa.gov.cn 国密协议  
**现象**：SM4加密正确、SM2签名本地可验，但服务端 code=-2

```
Observe:
  - SM4 加解密互逆 ✓
  - SM2 签名本地验证通过 ✓
  - 服务端返回 "查询字段名称为空"

Hypothesize:
  "签名计算的输入不对——签名了密文而非明文"

Test:
  1. 浏览器中 SM2 签名的输入 → 是原始 businessData（明文）
  2. 本地实现 → 签名了 encData（密文）
  3. 修改为先签后加密 → 仍失败
  4. signData 字段拼接需要特定排序

Fix: SM2签名必须在SM4加密之前，对原始 businessData 计算

教训：含多层加密的协议，签名/加密先后顺序是关键——「先签后加密」是常见模式。
```

### 案例5：绎通考试平台三次加密误判

**项目**：OUC 考试云平台（若依框架）  
**现象**：Hook到HmacMD5但签名不对，换AES-ECB也不对

```
Observe:
  - Hook 捕获到 HmacMD5 调用
  - 本地实现 HmacMD5 → 失败
  - 换 AES-ECB → 失败

误判链:
  ① "密码用HmacMD5加密" → 实际是其他功能在调用，密码是明文
  ② "AES密钥随机生成" → 实际是固定密钥
  ③ "AES模式是ECB" → 实际是CBC+ZeroPadding

正确路径（如果重来）:
  1. 搜索"若依 captchaImage 逆向" → 立刻知道框架特征
  2. 保存JS → AST反混淆 → 在可读代码搜 "encrypt"/"secretKey"
  3. 找到真实模块 → 确认 AES/CBC/ZeroPadding + 固定密钥 + RSA
  4. 纯Python实现 → 一次通过

教训：
  - Hook到的加密调用不一定属于目标功能——必须追踪调用链到源头
  - 连续猜测失败时，停止猜测，回退到AST反混淆在可读代码中追踪
  - 框架类站点先搜情报（"若依逆向"一搜就有答案）
```

### 案例6：瑞数6 VM沙箱变量断裂

**项目**：189.cn 瑞数6 Node.js 补环境  
**现象**：vm.createContext 执行报 `_$d9.call` is undefined

```
Observe:
  - 使用 vm.createContext + vm.runInContext 执行瑞数外链JS
  - VMP解释器中 _$d9 为 undefined
  - _$d9 在闭包中被绑定为 Math.round

Hypothesize:
  "VM沙箱创建了独立作用域，闭包变量无法正确访问sandbox对象"

Test:
  1. vm.runInContext → _$d9 undefined（闭包断裂）
  2. 换 eval(jsCode) 全局作用域执行 → 闭包变量正确解析 → 通过

Fix: 放弃 vm.createContext，改用 window=global + eval() 全局执行

教训：
  - 瑞数/JSVMP 类代码的闭包变量依赖全局作用域，VM沙箱会打断
  - 宁可污染全局作用域，也不能用VM隔离（因为VMP就是靠闭包传递状态）
```

### 案例7：大众点评 aS VM Node.js 崩溃

**项目**：大众点评 mtgsig 签名  
**现象**：aS VM 字节码解释器报 .apply/.in/typeof 访问 undefined

```
Observe:
  - VM解释器在执行字节码时多处崩溃
  - 错误都是对 undefined/null 做属性访问

Hypothesize:
  "VM字节码不保证所有操作数都有值，需要null检查保护"

Test:
  1. 为 .apply / in / typeof 操作添加 null 检查 → 不再崩溃
  2. 注入完整浏览器全局环境（webdriver/plugins/performance）
  3. VM成功运行至生成 a8 字段

Fix:
  - 字节码解释器关键操作添加 null/undefined 容错
  - 补全 navigator.webdriver=false / plugins / performance.now()

教训：VMP/VM解释器的Node.js移植，关键是 null 容错 + 环境完整性。
```

### 案例8：rednote 签名失效（服务端新增必选Header）

**项目**：rednote.com 协议逆向  
**现象**：原 Node.js 纯算 signer.js 突然失效

```
Observe:
  - X-S / X-T 签名本地生成正确
  - 请求被拒绝（非403，是业务层拒绝）
  - 对比浏览器发现新增 X-S-Common header

Hypothesize:
  "当时实现缺少新Header的生成/来源链，是否必需尚待对照"

Test:
  1. 添加空 X-S-Common → 仍失败
  2. 从浏览器复制 X-S-Common → 通过
  3. 尝试还原 X-S-Common 生成逻辑 → 过于复杂

Fix:
  - 当时停止维护该纯算 signer，未证明该字段不可计算
  - 新建 cdp_bridge.py 通过CDP调用AdsPower浏览器内真实业务函数
  - 全套签名（X-S/X-T/X-S-Common）一次性从浏览器获取

教训：
  - 按本案目标与止损线评估路线，不能将历史成本公式当默认规则
  - CDP 取值明确标为 oracle 依赖，仍需目标消费者验收
```

### 案例9：SpiderDemo WASM 挑战（绕过反调试）

**项目**：spiderdemo.cn WASM Challenge  
**现象**：页面有 anti_automation.js 反调试，DevTools无法打开

```
Observe:
  - 访问页面被重定向到 spiderbox.cn（反调试触发）
  - anti_automation.js 检测 webdriver/devtools
  - WASM模块在浏览器中执行

Hypothesize:
  "不需要在浏览器中执行WASM——直接在Node.js本地加载"

Test:
  1. 下载 wasm_anti_bg.wasm + wasm_anti.js（glue code）
  2. Node.js 22.x 原生 WebAssembly.instantiate 加载 → 成功
  3. 调用 encrypt_simple(verifyString, timestamp) → 产出正确签名

Fix:
  - 完全绕过浏览器，Node.js 本地执行 WASM
  - Python subprocess 调用 → 批量生成签名

教训：
  - 反调试保护的WASM，换个环境跑就行——不一定要在浏览器里
  - Node.js 22+ 原生支持 WebAssembly，无需额外依赖
```

### 案例10：涂鸦验证码 SDK 深度Hook

**项目**：涂鸦智能验证码  
**现象**：模拟鼠标事件被拒绝（isTrusted=false）

```
Observe:
  - dispatchEvent 触发的事件 isTrusted=false
  - SDK检测到非原生事件直接丢弃
  - 传统模拟操作方案失效

Hypothesize:
  "不模拟事件，直接Hook加密层获取明文"

Test:
  1. CDP Network.enable 拦截 getQuestion 响应 → 获取 xposition/shuffle
  2. Hook WebCrypto API (subtle.encrypt) → 捕获加密前明文
  3. Hook fetch/XHR → 捕获完整请求参数

Fix:
  - 多维度Hook：getQuestion响应 + WebCrypto + fetch
  - 不走模拟事件路线，直接走协议求解

教训：
  - isTrusted 无法伪造——遇到这种检测直接放弃模拟路线
  - WebCrypto Hook 是捕获加密明文的黄金手段
```

---
