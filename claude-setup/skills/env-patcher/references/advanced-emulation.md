# 深度环境模拟

只在调用栈已证明简单 stub 不足时使用。本文件处理 WebGL 状态、Canvas 稳定性、RAF/CSSOM、iframe realm 和资源异步；未知环境差异先由 `web-reverse-master` 做 `watch()`/`env_diff` 取证。

## WebGL 状态机

有些 SDK 不只读取 vendor/renderer，还检查 `bindTexture → texParameter → drawArrays`、shader compile、program link 与 `getError()` 的状态一致性。按真实调用链保留状态，不要为未触达的 WebGL API造全量实现。

```javascript
class MockWebGLStateMachine {
  constructor() {
    this._textures = new Map();
    this._buffers = new Map();
    this._programs = new Map();
    this._currentTexture = null;
    this._currentProgram = null;
    this._viewport = { x: 0, y: 0, w: 300, h: 150 };
    this._error = 0;
    this.drawingBufferWidth = 300;
    this.drawingBufferHeight = 150;
  }

  createTexture() {
    const id = { _id: Math.random() };
    this._textures.set(id, {});
    return id;
  }
  bindTexture(target, texture) { this._currentTexture = texture; }
  texParameteri() {}
  texImage2D() {}

  createShader(type) { return { _type: type, _source: '', _compiled: false }; }
  shaderSource(shader, source) { shader._source = source; }
  compileShader(shader) { shader._compiled = true; }
  getShaderParameter(shader, pname) {
    if (pname === 0x8B81) return Boolean(shader._compiled); // COMPILE_STATUS
    return null;
  }

  createProgram() {
    const program = { _shaders: [], _linked: false };
    this._programs.set(program, program);
    return program;
  }
  attachShader(program, shader) { program._shaders.push(shader); }
  linkProgram(program) { program._linked = true; }
  getProgramParameter(program, pname) {
    if (pname === 0x8B82) return Boolean(program._linked); // LINK_STATUS
    return null;
  }
  useProgram(program) { this._currentProgram = program; }

  getError() {
    const error = this._error;
    this._error = 0;
    return error;
  }
  viewport(x, y, w, h) { this._viewport = { x, y, w, h }; }
}
```

`Math.random()` 生成对象 id 只用于内部身份，不得进入对外指纹输出。若 SDK 读取更多 enum、precision、extensions 或像素结果，从真实浏览器采集一套相互一致的快照。

## Canvas 哈希稳定性

同一 session 内，相同绘制序列的 `toDataURL()`/`toBlob()` 必须稳定。固定值应来自与其余指纹字段一致的真实浏览器，而不是示例占位串。

```javascript
class StableCanvas {
  constructor(fixedDataUrl) {
    if (typeof fixedDataUrl !== 'string' || !/^data:image\/png;base64,[A-Za-z0-9+/]+={0,2}$/.test(fixedDataUrl)) {
      throw new TypeError('Expected a verified PNG data URL fixture');
    }
    this._fixedDataUrl = fixedDataUrl;
    this._callCount = 0;
  }

  toDataURL() {
    this._callCount += 1;
    return this._fixedDataUrl;
  }

  toBlob(callback, type = 'image/png') {
    if (typeof callback !== 'function') throw new TypeError('Callback required');
    if (String(type).toLowerCase() !== 'image/png') {
      throw new Error('Only the supplied PNG fixture is supported');
    }
    const bytes = Buffer.from(this._fixedDataUrl.split(',')[1], 'base64');
    const blob = new Blob([bytes], { type: 'image/png' });
    setTimeout(() => callback(blob), 0);
  }
}
```

此骨架只接受已核验的单个 PNG fixture，并依赖宿主注入 `Buffer`、`Blob` 和可清理的 `setTimeout`；格式检查不证明字节是有效 PNG。请求其他 MIME 时明确拒绝，不能把 PNG 字节标成 JPEG。若 SDK 把绘制命令作为输入，不能对所有输入返回同一 hash；需要按输入→输出保存 golden，或转真实 Canvas 引擎/浏览器 oracle。

## requestAnimationFrame 时序

只在 SDK 明确检查帧间隔时使用轻微抖动；测试需用范围与顺序断言，不能期待逐次时间戳相同。

```javascript
let rafId = 0;
const rafCallbacks = new Map();

globalThis.requestAnimationFrame = (callback) => {
  const id = ++rafId;
  const delay = 16 + Math.random() * 4 - 2;
  const timer = setTimeout(() => {
    callback(performance.now());
    rafCallbacks.delete(id);
  }, delay);
  rafCallbacks.set(id, timer);
  return id;
};

globalThis.cancelAnimationFrame = (id) => {
  const timer = rafCallbacks.get(id);
  if (timer !== undefined) {
    clearTimeout(timer);
    rafCallbacks.delete(id);
  }
};
```

不要用无界递归 `Promise.then()` 模拟 `queueMicrotask`：它可能饿死 timer。诊断 pending jobs 与原版事件顺序后再修复，不把所有 microtask 统一改成 timer。

## CSSOM 与 layout

```javascript
const COMPUTED_STYLE_DEFAULTS = Object.freeze({
  display: 'block',
  position: 'static',
  visibility: 'visible',
  opacity: '1',
  overflow: 'visible',
  zIndex: 'auto',
  width: '100px',
  height: '100px',
  margin: '0px',
  padding: '0px',
  fontFamily: 'Arial, sans-serif',
  fontSize: '16px',
  color: 'rgb(0, 0, 0)',
  backgroundColor: 'rgba(0, 0, 0, 0)',
  border: '0px none rgb(0, 0, 0)',
});

globalThis.getComputedStyle = () => new Proxy({}, {
  get(_target, prop) {
    if (prop === 'getPropertyValue') {
      return (name) => COMPUTED_STYLE_DEFAULTS[name] || '';
    }
    return COMPUTED_STYLE_DEFAULTS[prop] || '';
  },
});
globalThis.document.styleSheets = [];
```

这是 no-layout 占位语义，不能用于精确渲染验收。SDK 若消费字体、Canvas/Audio 的精确输出，按下文“渲染输入与输出契约”比较调用输入和引擎版本，再评估兼容实现或明确的浏览器 oracle。近似失败不证明本地复现不可行。

## iframe、prototype 与 realm

`contentWindow` 不能只是 `{}`：SDK 常检查 `iframe.contentWindow.window === iframe.contentWindow`、constructor/prototype、`instanceof Window` 以及父子 realm 函数身份。

```javascript
function Window() {}
function HTMLElement() {}

function makeWindow(parentWindow) {
  const win = Object.create(Window.prototype);
  Object.assign(win, {
    Window,
    window: win,
    self: win,
    globalThis: win,
    top: parentWindow ? parentWindow.top : win,
    parent: parentWindow || win,
  });
  return win;
}

const rootWindow = makeWindow(null);

function makeIframe() {
  const iframe = Object.create(HTMLElement.prototype);
  const childWindow = makeWindow(rootWindow);
  const childDocument = {
    defaultView: childWindow,
    documentElement: Object.create(HTMLElement.prototype),
  };
  childWindow.document = childDocument;
  Object.defineProperty(iframe, 'contentWindow', { get: () => childWindow });
  Object.defineProperty(iframe, 'contentDocument', { get: () => childDocument });
  return iframe;
}
```

真正的跨 realm `Function.prototype.toString`、constructor 身份和异常栈可能仍无法靠对象拼装复现。先定位具体检查，再决定创建独立 `vm` context 或显式浏览器 oracle；WASM/glue 约束见 [核心模板](core-templates.md)“运行时与字节语义”。

## 资源加载异步

`Image/script/link` 等元素设置 `src` 后，回调顺序通常是异步的，同时要兼容属性 handler 与 `addEventListener`：

```javascript
class MockImage {
  constructor() {
    this.width = 1;
    this.height = 1;
    this.complete = false;
    this.onload = null;
    this.onerror = null;
    this._src = '';
    this._listeners = {};
  }

  set src(value) {
    this._src = String(value);
    this.complete = true;
    setTimeout(() => {
      this.naturalWidth = this.width = 300;
      this.naturalHeight = this.height = 150;
      const event = { type: 'load', target: this, currentTarget: this };
      if (typeof this.onload === 'function') this.onload(event);
      for (const listener of this._listeners.load || []) listener(event);
    }, 1);
  }

  get src() { return this._src; }
  addEventListener(type, listener) {
    (this._listeners[type] ||= []).push(listener);
  }
  removeEventListener(type, listener) {
    this._listeners[type] = (this._listeners[type] || []).filter((fn) => fn !== listener);
  }
}
```

若入口依赖 webpack chunk runtime，确认注册/加载/缓存顺序与目标 exports，不能只执行模块源码。资源成功与失败事件、重复赋值后的取消行为均以原版调用轨迹为准；不注入虚构行为信号来掩盖挂起。

## 执行阶段与状态延续

- `document.currentScript` 的值取决于脚本类型和当前执行阶段；模块脚本及异步回调中的 null 可能正常。仅当原调用点确需同步 script 元素时修补其身份、src/baseURI 和 descriptor，保留真实 query，执行后恢复。
- 记录 `XHR.open` 的 async 参数、send 返回、readyState 与回调/microtask 顺序。同步请求才用同步桥；异步请求不得为了立即读到响应而强制阻塞。
- Promise 不推进时跟踪 MessageChannel/Worker、宿主回调和 timer 的注册/settle；只有确认存在原版降级分支，才评估禁用某 API，不能统一设 undefined 或返回空 Promise。
- VM 的 continuation、闭包和寄存器别名关系按原轨迹保留。只有原解码 mask 是快照而本地误用了可变引用时才复制；在首个不同 opcode/状态验证，禁止用通用 null-safe Proxy 吞掉所有失败。
- Proxy/断点/包装 Hook 都可能改变身份、toString、异常栈或时序；先核验插桩前后原输出。仅凭返回常量或挂起不能断定缺少某类用户事件。

## 渲染输入与输出契约

记录绘制/音频图、尺寸、字体、采样率、声道、节点参数、引擎及依赖版本；先确认 SDK 消费的是属性还是实际像素/浮点数据。近似实现与原版不一致时比较第一个被消费的值，不凭 API 名宣称不可复现。

固定 fixture 必须绑定同一输入图及环境，匹配类型、长度、采样率与声道；缺失或不匹配时拒绝输出，不能回退零值、截断或把旧 buffer 用于任意输入。返回副本避免调用者修改后续样本；多输入 golden 或兼容引擎输出另行对拍。浏览器采集须声明 oracle、生命周期与未覆盖输入。

## 加密边界捕获与逐字节比较

在实际 encrypt/serialize 入口消费数据前复制输入字节，在返回点立即复制输出；异步入口在对应 promise 完成点采集。timer 注册/执行前后的对象并不等于加密输入。

对象入口同时记录类型与原序列化器实际输出。不要用 `JSON.parse(JSON.stringify(...))` 复制任意值；它会丢失 undefined 或改变二进制等信息。TypedArray/DataView 快照应保留 offset/length 并复制底层字节，例如 Node 诊断器使用 `Buffer.from(new Uint8Array(view.buffer, view.byteOffset, view.byteLength))`，避免共享原 buffer。

固定输入、时钟、熵源和会话依赖，对至少三组非样例输入逐字节比较中间值及最终输出。长度/段数相同只是结构观察；before/after 无 mutation 也可能正常。算法一致但服务端拒绝时保留完整响应并交 master 查状态机，不以 400 自动切换 Cookie 路线。

## 深度模拟验收

每项高级补丁都要保存一个能区分修复前后的测试：

- WebGL：调用顺序、状态字段、compile/link status、error reset 与对外 fingerprint。
- Canvas：同输入多次稳定，不同输入若被消费则有可解释差异。
- RAF/资源：回调异步、顺序正确、可取消，进程无残留 timer。
- CSSOM/layout：仅声明已覆盖的属性；精确字体/物理渲染不得以近似值冒充。
- iframe/realm：对象关系、prototype、`instanceof`、descriptor 和函数身份通过目标 SDK 的原检查点。
