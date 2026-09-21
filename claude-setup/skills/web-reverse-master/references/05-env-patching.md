# 浏览器补环境完整方法

## 原则

**不要试图补全一整个浏览器。只补目标代码实际用到的API。**

优先级：
1. 补 `undefined` 导致主流程中断的
2. 补 `Illegal invocation` 错误的
3. 补原型链和描述符不一致的
4. 补 native `toString` 暴露的
5. 补指纹异常的

---

## 标准补环境模板

> 完整的三级补环境模板（Level 1 基础环境 / Level 2 增强环境 / Level 3 SDK专用）参见 `env-patcher` Skill。
>
> env-patcher 提供：
> - Level 1: window/document/navigator/screen/location/storage/performance — 所有项目必补
> - Level 2: Canvas 2D/WebGL/AudioContext/MutationObserver/IntersectionObserver — 风控严格站点
> - Level 3: SDK专用模板索引（阿里云AWSC/网易易盾IR/京东jcap WASM/极验4/同盾fm）
> - WASM 桥接模板（含 wasi_snapshot_preview1）
> - Python NodeSigner 桥接类
> - Function.prototype.toString 修复
> - 5步执行工作流 + 失败模式编码表

---

## 快速诊断

### 方法A：简单Proxy收集
```javascript
// MCP: js-reverse-mcp → evaluate_script
const handler = {
    get(target, prop) {
        if (!(prop in target)) {
            console.log('[MISSING]', prop);
            target[prop] = undefined;
        }
        return target[prop];
    }
};
window = new Proxy(window, handler);
```

### 方法B：watch() 全Proxy监控（推荐）

```javascript
// 强大的环境监控工具——递归Proxy所有对象
// 能够：
// 1. 精确追踪代码实际访问了哪些属性
// 2. 记录属性的get/set/in/delete操作
// 3. 发现运行时才赋值的属性（不要补那些）

function watch(obj, name, visited = new WeakSet()) {
    if (obj === null || typeof obj !== 'object' || visited.has(obj)) {
        return obj;
    }
    visited.add(obj);

    return new Proxy(obj, {
        get: function (target, property, receiver) {
            try {
                if (typeof property === 'symbol' || 
                    property === 'constructor' || 
                    property === '__proto__') {
                    return Reflect.get(target, property, receiver);
                }
                const value = Reflect.get(target, property, receiver);
                if (typeof value === 'object' && value !== null) {
                    const nestedName = `${name}.${String(property)}`;
                    return watch(value, nestedName, visited);
                }
                if (value === undefined) {
                    console.log(`对象 => ${name}, 读取属性: ${String(property)}, 值为: undefined`);
                }
            } catch (e) {}
            return Reflect.get(target, property, receiver);
        },
        set: (target, property, newValue, receiver) => {
            try {
                console.log(`对象 => ${name}, 设置属性: ${String(property)}, 值: ${typeof newValue === 'function' ? 'function' : newValue}`);
            } catch (e) {}
            return Reflect.set(target, property, newValue, receiver);
        },
        has: function(target, property) {
            console.log(`对象 => ${name}, in运算符检测: ${String(property)}`);
            return Reflect.has(target, property);
        },
        deleteProperty: function(target, property) {
            console.log(`对象 => ${name}, 删除属性: ${String(property)}`);
            return Reflect.deleteProperty(target, property);
        },
        ownKeys: function(target) {
            console.log(`对象 => ${name}, 获取自身键(Object.keys)`);
            return Reflect.ownKeys(target);
        },
        defineProperty: function(target, property, descriptor) {
            console.log(`对象 => ${name}, 定义属性: ${String(property)}`);
            return Reflect.defineProperty(target, property, descriptor);
        },
        setPrototypeOf: function(target, prototype) {
            console.log(`检测: setPrototypeOf 被调用 (对象: ${name})`);
            return Reflect.setPrototypeOf(target, prototype);
        },
        getPrototypeOf: function(target) {
            console.log(`检测: getPrototypeOf 被调用 (对象: ${name})`);
            return Reflect.getPrototypeOf(target);
        }
    });
}

// 使用方式
document = watch(document, 'document');
navigator = watch(navigator, 'navigator');
window = watch(window, 'window');
```

**watch() 使用建议**：
- 在浏览器Console中先运行一次 → 获得目标代码**实际**访问了哪些属性
- 只补 `undefined` 的那些，不补运行时赋值的
- 补完立即验证，不要等到"全补完"

---

## 特殊对象处理

### document.all

`document.all` 是 V8 的特殊对象，纯 JS 无法完全模拟。如果被检测到：

```javascript
// 最低限度模拟
context.document.all = {
    0: context.document.documentElement,
    length: 1,
    item: (i) => i === 0 ? context.document.documentElement : null,
    namedItem: () => null,
};
// 使其 typeof 返回 undefined（HTMLAllCollection 特征）
// 纯JS做不到，需要 C++ addon
```

---

## navigator.plugins 与 mimeTypes 的环境契约

不要使用固定 PDF/Native Client 插件列表冒充当前浏览器。空列表、PDF 内建插件及其命名会随浏览器、版本和设置变化，不能单独判异常。

- 从当前授权基线采集属性描述符、原型、索引访问、`item`/`namedItem`、枚举行为，以及 plugin 与 mimeType 的关联。
- 先定位 SDK 实际读取的属性，再以最小实现匹配该语义；函数是否返回 `[native code]` 不是充分判据。
- 采集值记录 browser/device/asset hash 和来源。复制到本地的值标为 fixture 或 oracle 依赖，不能宣称是任意输入生成算法。
- Canvas/WebGL/Audio 同样需要输入、调用序列和输出对拍；不能把一个截图哈希或音频常量当成“真实指纹”。

---

## 补环境决策矩阵

| 情况 | 方案 | 成本 |
|------|------|------|
| 只用到 navigator/document 基础属性 | 最小补环境（模板就够） | 10分钟 |
| 用到 Canvas/WebGL 指纹 | 对齐当前输入/调用/渲染输出；采样重放值标明依赖 | 按缺口评估 |
| 用到 AudioContext 指纹 | 对照异步生命周期与输出；stub 只证明流程可跑 | 按缺口评估 |
| 用到 plugins/mimeTypes | 按当前基线的属性/原型/关联补齐（见上方） | 按缺口评估 |
| 用到 WebRTC/Service Worker | 考虑切换到CDP桥 | — |
| 代码已收缩成纯函数 | 不要补环境，直接扣函数 | 5分钟 |
| 需要 document.all typeof | 无法完美模拟，用CDP桥 | — |
| 需要多个模块组合 | 使用模块化 EnvPatcher 加载器（见下方） | 按模块叠加 |
| 达到本案止损线 | 列明未解字段与假设，再按已确认目标选择后续路线 | — |

---

## 切换策略

当补环境成本过高时，切换到浏览器内执行：

```python
# 方案1: CDP桥 → 在AdsPower浏览器内执行（参考 .claude/skills/web-reverse-master/scripts/cdp_bridge.py）
# 方案2: Node.js子进程 + JsRpc → 通过WebSocket通信
```

---

## 模块化补环境架构

将大型单体模板拆分为可插拔模块，按需加载：

```javascript
// env_loader.js — 模块化补环境加载器
const vm = require('vm');
const fs = require('fs');

class EnvPatcher {
    constructor() {
        this.context = {
            window: {},
            self: {},
            globalThis: {},
            console: console,
            setTimeout: setTimeout,
            setInterval: setInterval,
        };
        // 循环引用
        this.context.window.window = this.context.window;
        this.context.self = this.context.window;
        this.context.globalThis = this.context.window;
        
        this.modules = {};
    }
    
    load(moduleName, config = {}) {
        const module = require(`./modules/${moduleName}`);
        this.context = module.patch(this.context, config);
        this.modules[moduleName] = true;
        console.log(`[Env] Loaded: ${moduleName}`);
        return this;
    }
    
    loadIfMissing(propertyPath, moduleName, config = {}) {
        const parts = propertyPath.split('.');
        let current = this.context;
        for (const p of parts) {
            if (current[p] === undefined) {
                return this.load(moduleName, config);
            }
            current = current[p];
        }
        console.log(`[Env] Skip: ${moduleName} (${propertyPath} already exists)`);
        return this;
    }
    
    run(code) {
        vm.createContext(this.context);
        return vm.runInContext(code, this.context);
    }
    
    get() {
        return this.context;
    }
}

// === 使用示例 ===
const env = new EnvPatcher();

env.load('navigator', { ua: 'Mozilla/5.0 ...', platform: 'Win32' })
   .load('document', { url: 'https://target.com/' })
   .load('location', { href: 'https://target.com/' })
   .load('storage')
   .load('crypto')
   .loadIfMissing('window.screen', 'screen')
   .loadIfMissing('window.AudioContext', 'audio')
   .loadIfMissing('window.HTMLCanvasElement', 'canvas');

const targetCode = fs.readFileSync('target.js', 'utf-8');
env.run(targetCode);
```

### 模块目录结构

```
modules/
├── navigator.js    ← navigator 对象
├── document.js     ← document 对象（含 createElement）
├── location.js     ← location 对象
├── storage.js      ← localStorage + sessionStorage
├── crypto.js       ← crypto.getRandomValues
├── screen.js       ← screen 属性
├── history.js      ← history 对象
├── canvas.js       ← HTMLCanvasElement + WebGL
├── audio.js        ← AudioContext
├── webworker.js    ← Worker 最小 stub
├── webrtc.js       ← RTCPeerConnection 最小 stub
├── plugins.js      ← navigator.plugins + mimeTypes
├── prototypes.js   ← 原型链保护（toString/descriptors）
└── utils.js        ← watch() / obj_toString 等工具
```

---

## 自动诊断脚本

快速检测补环境与真实浏览器的差异：

```javascript
// env_diff.js — 补环境差异诊断工具
// 在真实浏览器 Console 中运行，然后对比补环境输出
// 完整脚本见 .claude/skills/web-reverse-master/scripts/env_diff.js
```

```python
# compare_env.py — 对比浏览器环境与补环境的差异
# 完整脚本见 .claude/skills/web-reverse-master/scripts/compare_env.py
# 用法: .\venv\Scripts\python.exe .claude\skills\web-reverse-master\scripts\compare_env.py browser_env.json patched_env.json
```
