# 反模式全库：20条实战教训

> 每一条都来自真实项目踩坑经历。

## 反模式 1：猜测性编码 ⚠️ 最常见

**表现**：未实证确认加密方式就编写加密/签名代码。

**案例**：ouc_exam项目3次误判（密码HmacMD5→实际明文、AES随机密钥→实际固定、ECB→实际CBC）

**纠正**：加密参数必须从源码实证确认。只能基于已知推进。

---

## 反模式 2：跳过Phase 3直接编码

**表现**：找到加密函数后直接写代码，不等用户确认。

**案例**：多个项目中Phase 2完成 → 不产Plan → 直接写代码 → 方向错误 → 全部推倒

**纠正**：Phase 3是强制准入门槛，Plan必须用户确认。

---

## 反模式 3：Hook捕获 ≠ 目标功能

**表现**：Hook到加密调用就想当然认为是目标功能。

**案例**：ouc_exam Hook到HmacMD5 → 以为登录用HmacMD5 → 实际是其他功能在用

**纠正**：必须追踪完整调用链，确认调用栈到达目标请求发送点。

---

## 反模式 4：线索不追到底

**表现**：拿到接口地址却不直接用requests验证。

**纠正**：Performance API拿到接口 → 直接用requests调 → 最快验证路径。

---

## 反模式 5：Hook时机错误

**表现**：页面加载后才注入Hook → 框架闭包已创建 → Hook无效。

**纠正**：用 `inject_before_load` 或 `Page.addScriptToEvaluateOnNewDocument`。

---

## 反模式 6：绕过反混淆工具报错

**表现**：工具报错选择绕过，手动解混淆效率极低。

**纠正**：工具报错立即修复（通常只需几行try-catch），不要绕过。

---

## 反模式 7：不调用已有工具

**表现**：有AST反混淆工具不用，手动写简易替代品。

**纠正**：优先使用项目已有的工具和脚本。

---

## 反模式 8：浏览器内反复折腾

**表现**：在浏览器中反复搜索/Hook/执行——效率极低。

**纠正**：保存JS → 本地反混淆 → 搜索。效率提升5-10倍。

---

## 反模式 9：重复失败Hook

**表现**：Hook失败 → 同一种方式重试多次。

**纠正**：失败一次就换方法（AST反混淆 / breakpoint / Proxy / Performance API）。

---

## 反模式 10：加密参数想当然

| 常见错误假设 | 实际可能 |
|-------------|---------|
| AES密钥随机生成 | 固定密钥 |
| ECB+PKCS7 | CBC+ZeroPadding |
| 密码加密传输 | 密码明文，整体JSON加密 |
| IV随机 | IV = Key |

**纠正**：每个参数从源码实证确认。

---

## 反模式 11：把问题升级

**表现**：简单方案不用，非要走最复杂的路线。

**案例**：
- zhipin → 有登录态Cookie不用 → 花大量时间补环境161个API → 仍然code=38
- 本质：用最复杂的方案试图解决简单问题

**纠正**：按目标能力和当前缺口选择最小实验。Cookie 重放、浏览器 oracle 与独立算法的交付边界不同，不能用历史耗时替代本案止损线。

---

## 反模式 12：PowerShell语法

```powershell
# 错误
# 全局 pip + Bash 的 &&，随后调用全局 Python
# 用 python -c 承载多行代码

# 正确
.\venv\Scripts\python.exe -m pip install xxx
.\venv\Scripts\python.exe main.py
# 多行代码写.py文件再执行
```

---

## 反模式 13：CDP桥时机太晚 ⚠️ 高效陷阱

**表现**：签名频繁升级后还坚持纯算路线，浪费大量时间。

**案例**：rednote签名方案 — 纯算signer.js用curl_cffi发请求，X-S-Common升级后失效。
历史记录称 CDP 桥取得所需字段；本次未复核原始资产 hash。浏览器路径仍依赖版本、会话和业务上下文，不能保证后续改动自动兼容。

**教训**：列明未解析字段、已排除假设和实际成本，按已确认目标决定继续还原还是交付依赖型方案；升级频率不构成“纯算不可行”的证明。

---

## 反模式 14：忽略框架特征

**表现**：没做Phase 0情报收集就硬逆，不知道目标用的是什么框架。

**案例**：ouc_exam — 若依框架（RuoYi）有固定加密模式（AES/CBC/ZeroPadding + IV=Key + RSA公钥加密AES密钥），搜一下"若依 captchaImage 逆向"就能知道答案，却花了大量时间从头逆向。

**纠正**：当前缺公开背景、产品或框架指纹时，进入 Phase 0，搜索"站点名 + 逆向/加密/cookie"或识别框架特征（若依/captchaImage、Vue/__vue__、React/__REACT_DEVTOOLS_GLOBAL_HOOK__）。若已有真实流量或函数入口，则直接进入当前证据缺口，不为形式补做 Phase 0。

---

## 反模式 15：未确认题型就固定识别工具

**表现**：未确认协议是否有图像、题型和输入格式，就固定使用某个识别服务或本地模型。

**案例**：fcbox滑块验证码 — 先用OpenCV TM_CCOEFF_NORMED做缺口检测，效果一般；切换到云打码API后大幅提升成功率。

**纠正**：先分无感、评分和图像交互模式，再按真实样本、识别能力与任务范围选择工具。图像向外部服务传递及费用须已有授权；某个历史样本的效果不能形成通用优先级。

---

## 反模式 16：盲目补环境

**表现**：看到JS用navigator/document就决定补环境，补了一堆API才发现代码实际只用了3个属性。

**案例**：zhipin补环境 — 逐个补了161个API和属性哈希，最终仍然code=38。事后分析，实际需要的环境属性可能只有10个。

**纠正**：
1. 先在浏览器Hook，精确确定代码**实际**访问了哪些属性
2. 只补它实际用到的，不补"可能用到"的
3. 补完立即验证，不等到"全部补完"再测试
4. 如果补环境成本 > 2小时，评估CDP桥方案

---

## 反模式 17：不验证签名对齐

**表现**：写完纯算代码后直接调接口验证，不先用已知输入对比输出。

**案例**：多次项目中写完算法 → 直接用接口测试 → code!=0 → 不知道是算法错了还是环境/参数/网络问题 → 反复回退排查。

**纠正**：
1. Hook 捕获一组"输入+输出"样本（至少3组不同输入）
2. 本地用相同输入计算 → 逐字节对比输出
3. 所有样本对齐后才能用接口验证
4. 推荐工具：`.\venv\Scripts\python.exe .claude\skills\web-reverse-master\scripts\verify_crypto.py --browser-output <file> --local-output <file>`

---

## 反模式 18：TLS指纹忽略

**表现**：加密参数全部逆向成功，用 `requests` 发请求仍然被拦截（403/412）。

**案例**：Boss 直聘 `__zp_stoken__` 生成完全正确，用原生 `requests` 发请求 → code=35 限流 → 排查数小时才发现是 TLS 指纹暴露。切换到 `curl_cffi` + `impersonate="chrome131"` 后立即通过。

**纠正**：
1. 将算法对拍与请求接受分开，先定位业务/挑战/会话/传输哪个观察点首先分歧
2. 需要传输对照时可使用项目 `./venv` 中的 `curl_cffi`；换库会同时改变多项行为，不能唯一归因为 TLS
3. profile 按当前基线和已安装库支持选择，记录实发 ClientHello、ALPN、HTTP 版本及 headers；不固定“最新 Chrome”
4. 注意：`curl_cffi` 不是 `curl-cffi`！

---

## 反模式 19：请求头残缺

**表现**：只配了 User-Agent 和 Cookie，忽略了现代浏览器的 `sec-ch-ua`、`sec-fetch-*` 等安全头。

**案例**：拼多多 `anti_content` 签名正确，但缺少 `sec-fetch-dest`/`sec-fetch-mode`/`sec-fetch-site` → 服务端直接返回空数据（无错误码，难以排查）。

**纠正**：
1. 从浏览器 Network 面板**完整复制**请求头（不只是 Cookie 和 UA）
2. 特别关注：`sec-ch-ua`、`sec-ch-ua-mobile`、`sec-ch-ua-platform`、`sec-fetch-*`
3. 结合 UA-CH 品牌列表、GREASE 与实际浏览器版本解释字段，不要求所有品牌版本号都与 User-Agent 相同
4. 参考 [协议与状态证据](14-risk-protocol-and-state.md) 比较当前传输和上下文；不再引用已删除的通用 `build_headers()` 模板

---

## 反模式 20：过度Hook导致递归/性能崩溃

**表现**：一次性 Hook 多个原型方法（如同时 Hook `fetch` + `XMLHttpRequest.send` + `JSON.stringify` + `Function.prototype.apply`），导致递归调用栈溢出或页面卡死。

**案例**：
- Hook `CryptoJS.AES.encrypt` → 内部调用 `toString` → 触发另一个 Hook → 递归溢出
- 同时 Hook 5 个方法 → 每次请求触发 200+ 条日志 → 浏览器卡死

**纠正**：
1. 每次只 Hook 1-2 个目标方法，用完即卸载
2. Hook 函数内部用 `if (logging)` flag 控制日志输出，避免递归
3. 对递归敏感的 Hook 加 `__hooked` 标记防止重复：
```javascript
const orig = CryptoJS.AES.encrypt;
CryptoJS.AES.encrypt = function(msg, key, cfg) {
    if (this.__hooked) return orig.call(this, msg, key, cfg);
    this.__hooked = true;
    console.log('[Hook] AES.encrypt input:', msg);
    const result = orig.call(this, msg, key, cfg);
    this.__hooked = false;
    return result;
};
```
4. 抓关键点：先 Hook 请求发送点（fetch/XHR.send），确认参数来源后再 Hook 加密函数
5. 如果需要广撒网，用 `watch()` Proxy 监控代替多个 Hook
