# 核心补环境模板

本文件仅在需要手动补 Level 1/2、VM 加载器、WASM 或 Python 桥时读取。模板是骨架：先按 `SKILL.md` 建立 API 清单，再删除未被目标 SDK 使用的部分并校准属性、descriptor、对象身份和时序。

## 运行时与字节语义

- 先记录 SDK/hash、运行时版本、必经 API、对象身份和同步/异步调用轨迹。iv8、sdenv、Node VM 或浏览器 oracle 都是候选，家族名称和一次挂起不决定路线；复用原 SDK 必须声明依赖。
- `btoa` 消费每个 code unit 在 0–255 内的二进制字符串，不是任意 Unicode 的 UTF-8 编码。用包含 0、127、128、255 以及越界字符的离线向量验证；越界应按目标语义报错，不能静默截断、替换或宽松补 padding。`atob` 输出仍是二进制字符串。
- Node `Buffer`、TypedArray、DataView、ArrayBuffer 的转换需保留 `byteOffset/byteLength`。二进制字符串、文本、hex 和 Base64 分别标注，编码转换前确认目标 API 的输入契约。
- WASM/glue 使用同一已确认的 realm 构造对象，核对 prototype、constructor、`instanceof` 与 direct eval 的作用域。不要为了检查通过统一移除 `global` 或注入宿主 `Function/eval`；只按真实失败分支修复。出现异常大内存分配时停止该路径并保留证据。
- Python 桥显式使用项目 venv 解释器路径和参数数组，检查 timeout、退出码、stderr 与输出 schema。不能从混杂 stdout 中截出看似 JSON 的片段后宣布成功。

## Level 1：基础环境

覆盖全局对象、基础 DOM、navigator、screen、location、performance、storage、编码和 timer。SDK 若只触达其中一部分，不要整段照搬。

```javascript
// === 全局对象 ===
globalThis.window = globalThis;
globalThis.self = globalThis;
globalThis.top = globalThis;
globalThis.parent = globalThis;
globalThis.frames = globalThis;

// === document ===
const doc = {
  createElement: (tag) => ({
    tagName: tag.toUpperCase(),
    style: {},
    children: [],
    appendChild: () => {},
    removeChild: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    getAttribute: () => null,
    setAttribute: () => {},
    getBoundingClientRect: () => ({ top: 0, left: 0, width: 100, height: 100 }),
    getElementsByTagName: () => [],
    querySelectorAll: () => [],
    querySelector: () => null,
    innerHTML: '', innerText: '', textContent: '',
    offsetWidth: 100, offsetHeight: 100,
    classList: { add: () => {}, remove: () => {}, contains: () => false },
  }),
  getElementById: () => null,
  querySelector: () => null,
  querySelectorAll: () => [],
  documentElement: { style: {}, clientWidth: 1920, clientHeight: 1080 },
  body: { appendChild: () => {}, removeChild: () => {} },
  cookie: '',
  readyState: 'complete',
  title: '',
  referrer: '',
  domain: '',
  URL: 'https://www.example.com/',
  addEventListener: () => {},
  removeEventListener: () => {},
  createEvent: () => ({ initEvent: () => {} }),
  head: {},
};
globalThis.document = doc;

// === navigator ===
globalThis.navigator = {
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
  platform: 'Win32',
  language: 'zh-CN',
  languages: ['zh-CN', 'zh', 'en'],
  vendor: 'Google Inc.',
  appVersion: '5.0 (Windows NT 10.0; Win64; x64)',
  appName: 'Netscape',
  product: 'Gecko',
  productSub: '20030107',
  cookieEnabled: true,
  onLine: true,
  hardwareConcurrency: 8,
  deviceMemory: 8,
  maxTouchPoints: 0,
  plugins: { length: 0 },
  mimeTypes: { length: 0 },
  connection: { effectiveType: '4g', downlink: 10, rtt: 50 },
  userAgentData: {
    brands: [
      { brand: 'Chromium', version: '136' },
      { brand: 'Google Chrome', version: '136' },
    ],
    mobile: false,
    platform: 'Windows',
  },
};

// === screen/location ===
globalThis.screen = {
  width: 1920, height: 1080,
  availWidth: 1920, availHeight: 1040,
  colorDepth: 24, pixelDepth: 24,
};
globalThis.location = {
  href: 'https://www.example.com/',
  hostname: 'www.example.com',
  protocol: 'https:',
  pathname: '/', search: '', hash: '',
};

// === performance ===
const hostPerformance = globalThis.performance;
if (!hostPerformance || typeof hostPerformance.now !== 'function') {
  throw new Error('Host must provide monotonic performance.now');
}
globalThis.performance = {
  now: () => hostPerformance.now(),
  timeOrigin: hostPerformance.timeOrigin,
  timing: { navigationStart: hostPerformance.timeOrigin },
  getEntriesByType: () => [],
  getEntriesByName: () => [],
  mark: () => {},
  measure: () => {},
};

// === storage ===
function makeStorage() {
  const data = new Map();
  return {
    getItem(k) { return data.get(String(k)) ?? null; },
    setItem(k, v) { data.set(String(k), String(v)); },
    removeItem(k) { data.delete(String(k)); },
    clear() { data.clear(); },
    get length() { return data.size; },
    key(i) { return [...data.keys()][Number(i) >>> 0] ?? null; },
  };
}
globalThis.localStorage = makeStorage();
globalThis.sessionStorage = makeStorage();

// === encoding；宿主注入 node:buffer 的严格 atob/btoa ===
if (typeof globalThis.atob !== 'function' || typeof globalThis.btoa !== 'function') {
  throw new Error('Host must provide node:buffer atob/btoa');
}

// === timers；宿主注入可登记、清理的 timer，不压缩 SDK 请求的 delay ===
globalThis.requestAnimationFrame = (fn) => globalThis.setTimeout(() => fn(performance.now()), 16);
globalThis.cancelAnimationFrame = (id) => globalThis.clearTimeout(id);
```

注意：上面的 UA 是占位示例。应从同一真实设备快照注入 UA、UA-CH、platform、语言、时区、screen 与硬件字段，不能混搭。`btoa` 的二进制字符串契约见本文件“运行时与字节语义”；宿主注入函数及其异常属于宿主 realm，若目标检查身份则另做对应验证。Storage 仅覆盖方法接口，不覆盖属性式读写、quota 或 storage event。

## Level 2：增强环境

### Canvas 2D

```javascript
class MockCanvas2D {
  constructor(canvas) {
    this.canvas = canvas;
    this.fillStyle = '#000000';
    this.font = '10px sans-serif';
    this.textBaseline = 'alphabetic';
    this.globalCompositeOperation = 'source-over';
  }
  fillRect() {}
  fillText() {}
  measureText() { throw new Error('Text metrics fixture or renderer required'); }
  getImageData() { throw new Error('Pixel fixture or renderer required'); }
  putImageData() {}
  arc() {} beginPath() {} closePath() {} lineTo() {} moveTo() {}
  stroke() {} fill() {} save() {} restore() {} translate() {}
  rect() {} clip() {} drawImage() {}
  createLinearGradient() { return { addColorStop: () => {} }; }
}
```

这是方法骨架，不计算绘图状态。`measureText/getImageData` 缺少匹配输入的 fixture 或渲染器时明确报错，不返回常量宽度或零像素。`toDataURL()` 属于 canvas 元素，不是 2D context；高级模板见 `advanced-emulation.md`。

### WebGL

```javascript
class MockWebGL {
  getParameter(p) {
    const params = {
      37445: 'Google Inc. (NVIDIA)',
      37446: 'ANGLE (NVIDIA, GeForce GTX 1060, OpenGL 4.5)',
      7937: 'WebKit WebGL',
      7936: 'WebKit',
      7938: 'WebGL 1.0 (OpenGL ES 2.0 Chromium)',
    };
    return params[p] ?? null;
  }
  getExtension(name) {
    if (name === 'WEBGL_debug_renderer_info') {
      return { UNMASKED_VENDOR_WEBGL: 37445, UNMASKED_RENDERER_WEBGL: 37446 };
    }
    return null;
  }
  getSupportedExtensions() {
    return ['ANGLE_instanced_arrays', 'EXT_blend_minmax', 'WEBGL_debug_renderer_info'];
  }
  createBuffer() { return {}; }
  bindBuffer() {}
  bufferData() {}
}
```

### Audio 与 EventTarget

```javascript
globalThis.AudioContext = class {
  createOscillator() {
    return { connect: () => {}, start: () => {}, stop: () => {}, frequency: { value: 0 } };
  }
  createDynamicsCompressor() {
    return { connect: () => {}, threshold: { value: 0 }, knee: { value: 0 } };
  }
  createAnalyser() { return { connect: () => {}, getFloatFrequencyData: () => {} }; }
  createGain() { return { connect: () => {}, gain: { value: 0 } }; }
  get destination() { return {}; }
  close() {}
};
globalThis.OfflineAudioContext = class extends globalThis.AudioContext {
  startRendering() {
    return Promise.reject(new Error('Audio graph fixture or renderer required'));
  }
};

class MockEventTarget {
  constructor() { this._listeners = {}; }
  addEventListener(type, fn) {
    (this._listeners[type] ||= []).push(fn);
  }
  removeEventListener(type, fn) {
    if (this._listeners[type]) {
      this._listeners[type] = this._listeners[type].filter((f) => f !== fn);
    }
  }
  dispatchEvent(event) {
    (this._listeners[event.type] || []).forEach((fn) => fn(event));
    return true;
  }
}

globalThis.MutationObserver = class { observe() {} disconnect() {} };
globalThis.IntersectionObserver = class { observe() {} disconnect() {} };
globalThis.matchMedia = () => ({ matches: false, addListener: () => {}, removeListener: () => {} });
globalThis.speechSynthesis = { getVoices: () => [] };
globalThis.Notification = { permission: 'default' };
```

Audio 节点是属性骨架，不计算音频图；渲染入口默认拒绝。按 [深度模拟](advanced-emulation.md) 的渲染输入/输出契约提供兼容实现或匹配 fixture，缺失时不能返回空数组冒充渲染结果。

## 原生函数外观

维护 `WeakMap<Function, string>`，只改变登记 mock 的外观，保留未登记函数的 realm 原始语义：

```javascript
const originalToString = Function.prototype.toString;
const nativeNames = new WeakMap();

function markNative(fn, name = fn.name || '') {
  nativeNames.set(fn, name);
  return fn;
}

Function.prototype.toString = function toString() {
  if (nativeNames.has(this)) {
    const name = nativeNames.get(this);
    return `function ${name}() { [native code] }`;
  }
  return Reflect.apply(originalToString, this, []);
};

markNative(document.createElement, 'createElement');
markNative(document.querySelector, 'querySelector');
```

若 SDK 校验属性 descriptor、函数 `name/length`、Proxy 身份或 iframe realm，仅伪造字符串不够；读 `advanced-emulation.md`。WASM/glue 的同-realm 与 direct eval 约束见本文件“运行时与字节语义”。

## 固定指纹快照

```javascript
const FINGERPRINT = Object.freeze({
  canvas: 'data:image/png;base64,iVBORw0KGgo...',
  webglVendor: 'Google Inc. (NVIDIA)',
  webglRenderer: 'ANGLE (NVIDIA, GeForce GTX 1060)',
  audio: '35.770000000000003',
  fonts: ['Arial', 'Times New Roman', 'Consolas'],
  screen: '1920x1080x24',
  timezone: -480,
  platform: 'Win32',
  pluginsCount: 0,
  hardwareConcurrency: 8,
  deviceMemory: 8,
});

Object.defineProperty(navigator, 'hardwareConcurrency', {
  configurable: true,
  get: () => FINGERPRINT.hardwareConcurrency,
});
Object.defineProperty(navigator, 'deviceMemory', {
  configurable: true,
  get: () => FINGERPRINT.deviceMemory,
});
```

示例值不是 golden。实际交付要记录快照来源、版本、生命周期和相互一致性。

## VM 与 SDK 加载器

把兼容层源码作为脚本在同一 context 内执行，避免 `require('./browser.js')` 在宿主 realm 初始化后再 spread：

```javascript
const fs = require('fs');
const vm = require('vm');
const { atob, btoa } = require('node:buffer');
const { Console } = require('node:console');
const { performance } = require('node:perf_hooks');

function createSandbox() {
  const timers = new Set();
  let disposed = false;
  const clear = (id) => { clearTimeout(id); clearInterval(id); timers.delete(id); };
  const schedule = (repeat, fn, ms, ...args) => {
    if (disposed) throw new Error('Sandbox already disposed');
    if (typeof fn !== 'function') throw new TypeError('Only function timers are supported');
    if (timers.size >= 1000) throw new Error('Sandbox timer limit exceeded');
    const id = (repeat ? setInterval : setTimeout)(() => {
      if (!repeat) timers.delete(id);
      Reflect.apply(fn, undefined, args);
    }, ms, ...args);
    timers.add(id);
    return id;
  };
  const sandbox = {
    console: new Console({ stdout: process.stderr, stderr: process.stderr }),
    Buffer, atob, btoa, performance,
    setTimeout: (fn, ms, ...args) => schedule(false, fn, ms, ...args),
    setInterval: (fn, ms, ...args) => schedule(true, fn, ms, ...args),
    clearTimeout: clear,
    clearInterval: clear,
  };
  const context = vm.createContext(sandbox);
  const cleanup = () => { disposed = true; for (const id of timers) clear(id); };
  return { context, cleanup };
}

async function loadSDKAndGenerate(browserPath, sdkPath, methodName, args, timeoutMs = 10_000) {
  if (!Array.isArray(args)) throw new TypeError('SDK args must be an array');
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1) throw new RangeError('Invalid timeout');
  const { context, cleanup } = createSandbox();
  const deadline = Date.now() + timeoutMs;
  let watchdog;
  const run = (source, filename) => {
    const remaining = deadline - Date.now();
    if (remaining <= 0) throw new Error('SDK deadline exceeded');
    return new vm.Script(source, { filename }).runInContext(context, { timeout: remaining });
  };
  const expired = new Promise((_, reject) => {
    watchdog = setTimeout(() => reject(new Error('SDK deadline exceeded')), timeoutMs);
  });
  try {
    run(fs.readFileSync(browserPath, 'utf8'), browserPath);
    run(fs.readFileSync(sdkPath, 'utf8'), sdkPath);
    // JSON 参数在 SDK realm 内构造；不把宿主 Array/Object 直接传入入口。
    const result = run(`(() => {
      const method = globalThis[${JSON.stringify(methodName)}];
      if (typeof method !== 'function') throw new TypeError('SDK method missing');
      const args = JSON.parse(${JSON.stringify(JSON.stringify(args))});
      return Reflect.apply(method, globalThis, args);
    })()`, 'sdk-entry.js');
    context.__sdkResult = await Promise.race([Promise.resolve(result), expired]);
    const json = run('JSON.stringify(globalThis.__sdkResult)', 'sdk-output.js');
    if (typeof json !== 'string') throw new TypeError('SDK result is not JSON serializable');
    return json;
  } finally {
    clearTimeout(watchdog);
    delete context.__sdkResult;
    cleanup();
  }
}

if (require.main === module) {
  const [, , browserPath, sdkPath, methodName, argsJson = '[]'] = process.argv;
  loadSDKAndGenerate(browserPath, sdkPath, methodName, JSON.parse(argsJson))
    .then((value) => process.stdout.write(`${value}\n`))
    .catch((error) => {
      process.stderr.write(`${error.stack || error}\n`);
      process.exitCode = 1;
    });
}
```

该桥只接受 JSON 参数：二进制/特殊类型要另定义编码协议，再在 SDK realm 内还原。同步加载、入口和输出序列化受 VM 剩余预算约束；pending Promise 有截止时间，成功或失败后清理已登记 timer。Node timer 保留其原有 delay 转换规则，仅支持函数回调，不能据此宣称浏览器 timer 等价。

`node:vm` 不是安全隔离。timer 回调、Promise/thenable 内的死循环会阻塞宿主事件循环，宿主 watchdog 不能终止它们；此类 SDK 必须在独立 Node 进程中运行，由下方 Python 桥或等价父进程 timeout 强制终止。只在 SDK 的真实 import 需要时注入 `process` 或 allowlist `require`；不要默认暴露宿主文件系统和环境变量。

## WASM 桥接骨架

优先直接使用原生 `WebAssembly`，按 `WebAssembly.Module.imports(module)` 的真实结果构建 imports，而不是替换整个全局对象：

```javascript
const fs = require('fs');

function inspectWasm(wasmPath) {
  const module = new WebAssembly.Module(fs.readFileSync(wasmPath));
  return {
    module,
    imports: WebAssembly.Module.imports(module),
    exports: WebAssembly.Module.exports(module),
  };
}

function instantiateWasm(wasmPath, imports) {
  const inspected = inspectWasm(wasmPath);
  const instance = new WebAssembly.Instance(inspected.module, imports);
  return { ...inspected, instance };
}
```

常见 imports 骨架如下；仅保留检查表要求的项，并校准 memory/table 限制：

```javascript
const imports = {
  env: {
    memory: new WebAssembly.Memory({ initial: 256, maximum: 256 }),
    table: new WebAssembly.Table({ initial: 0, element: 'anyfunc' }),
    abort: () => { throw new Error('WASM abort'); },
    _abort: () => { throw new Error('WASM _abort'); },
    _grow: () => {},
    segfault: () => { throw new Error('WASM segfault'); },
    alignfault: () => { throw new Error('WASM alignfault'); },
    Math_sqrt: Math.sqrt,
    Math_abs: Math.abs,
    Math_floor: Math.floor,
    Math_ceil: Math.ceil,
    Math_min: Math.min,
    Math_max: Math.max,
  },
  wasi_snapshot_preview1: {
    fd_write: () => 0,
    proc_exit: () => {},
    random_get: (ptr, len) => {
      crypto.getRandomValues(new Uint8Array(imports.env.memory.buffer, ptr, len));
      return 0;
    },
  },
};
```

若 SDK 用 `fetch()` 拉 `.wasm`，让 response 的 `arrayBuffer()` 返回指定文件内容，并验证 URL 解析。实例化后必须断言当前目标 exports 的名称、类型及输入契约；同时核对本文件“运行时与字节语义”中的 realm/direct-eval 和内存边界。

## Python 调用桥

```python
import json
import subprocess
from pathlib import Path


class NodeSigner:
    def __init__(self, node_script: Path, browser_path: Path, sdk_path: Path):
        self.node_script = Path(node_script)
        self.browser_path = Path(browser_path)
        self.sdk_path = Path(sdk_path)

    def call(self, method: str, args: list | None = None) -> object:
        cmd = [
            "node",
            str(self.node_script),
            str(self.browser_path),
            str(self.sdk_path),
            method,
            json.dumps(args or [], ensure_ascii=False),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Node.js failed ({result.returncode}): {result.stderr.strip()}")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Node.js returned non-JSON stdout: {result.stdout!r}") from exc
```

在本项目执行 Python 时使用 `./venv/Scripts/python.exe`（PowerShell：`.\venv\Scripts\python.exe`），不要调用全局解释器。

此桥只验证退出码及完整 stdout 的 JSON 语法；实际交付还需按目标输出 schema 校验类型、必填字段与长度，并核对 stderr 中的 SDK 诊断。JSON 可解析不能标为 schema、向量或业务通过。

## Level 3 示例索引

这些是项目内示例，不是 Skill 的运行依赖。复用前先核实路径仍存在、SDK 版本匹配且没有站点特定动态值。

| SDK/用途 | 示例路径 | 既有规模 |
|---|---|---|
| 阿里云 AWSC | `sites/aliyun_captcha/env/browser.js` | 约 200 行 |
| 网易易盾 IR | `sites/dun_163_com/src/env/browser.js` | 1032 行 |
| 京东 jcap WASM | `sites/jd_login/node/jcap_env.js` | 完整 |
| 极验 4 | `sites/crv-captcha/env/browser.js` | 最小 |
| 同盾 fm | `sites/juneyaoair/src/fm.js` | SDK 内含 |
| B 站极验 v3 | `sites/bilibili_login/src/geetest_crypto.js` | Node.js 纯算示例 |
| 大众点评 VM | `sites/dianping/src/aS_vm.js` | aS 解释器 |

基础 VM 无额外 npm 依赖。只有判官需要真实 Canvas 渲染时才考虑 `canvas`，且依赖必须安装在目标项目本地；若需要精确物理量，优先按停止条件转真实浏览器采集。
