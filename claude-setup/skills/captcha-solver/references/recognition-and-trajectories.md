# 图像识别、坐标与行为数据记录

> 从 `SKILL.md` 按需加载：当前链路确有交互题目，需要图像处理、坐标转换或行为事件记录时读取。
> 坐标系数、事件、采样和时间单位均按当前样本确认；无感、评分和托管挑战见 [verification-and-fallback.md](verification-and-fallback.md)。

## 通用自研验证码分析流程（服务商识别无匹配时）

```
1. 固定初始化/提交样本、版本、状态机和消费者；确认当前确有图片/交互
2. 保存并核对图片、坐标系与题型；选择匹配的本地识别或已授权识别器
3. 分析提交字段来源；未知算法交 master 定位真实入口，不按外观猜 AES/DES/XOR
4. 用真实输入输出确认算法、编码与行为数据序列化
5. 只在协议要求时处理真实样本支持的行为数据与序列化
6. 提交、供应商二次校验、测试/容灾分类、业务消费逐层留证
```

---

## 识别与坐标边界

产品模块与版本参考 [厂商能力索引](../../web-reverse-master/references/15-vendor-capability-reference.md)。
域名、前缀、图片样式和错误码只是线索，不能单独证明某个加密算法或完整防护模块。

- 先从当前初始化/提交确定题型；无感与评分分支不进入下面的图像流程。
- 区分原图像素、重排后的图像、CSS 显示尺寸、滑块初始偏移、提交坐标及归一化坐标；
  比例、四舍五入顺序与边界裁剪由当前样本确认，不固定 300/400、0.94 或 10000。
- RGBA 提示图先确认背景合成方式；滑块 alpha mask、打乱块索引和碰撞处理均需像素级验证。
- 语义/宫格/语序可用 `scripts/mmcaptcha/`；当前 `grid_select/text_grid_select` 的选格依赖模型，
  未实现独立集合逻辑判定器。需要确定性“和/或/不含”时，先获得逐格标签再由调用方做集合运算；
  把识别不支持、图像不清与服务端拒绝分开，不以某个旧成功率宣称当前题型可解。
- `mmcaptcha.to_pixels` 只把本包的 0–1000 归一化结果转为图像内像素索引，1000 映射到最后一个像素；
  这不是任何厂商的提交坐标契约。提交前另行验证缩放、偏移与舍入。
- `mmcaptcha.slider_gap` 当前提示词要求“完整背景 + 带缺口背景”两张同尺寸图；不能把滑块裁片当第二张背景。

---

## 识别示例

### slider-opencv（滑块本地识别）

```python
# 优先级：首选
# 适用：已确认图片和模板条件满足当前方法的几何滑块
# 依赖：opencv-python
import cv2
import math
import numpy as np

def detect_gap_slider(bg_bytes: bytes, slider_bytes: bytes, *, min_confidence: float) -> int:
    """OpenCV Canny + matchTemplate 滑块缺口检测
    返回：模板在背景中的左上角 x 坐标（像素），不自动扣除模板内透明/空白边距。
    min_confidence 须用当前题型标注样本校准；无有效像素或低分时拒绝返回坐标。
    """
    if not math.isfinite(min_confidence) or not 0 < min_confidence <= 1:
        raise ValueError("min_confidence must be in (0, 1]")
    if not bg_bytes or not slider_bytes:
        raise ValueError("image bytes must not be empty")
    bg = cv2.imdecode(np.frombuffer(bg_bytes, np.uint8), cv2.IMREAD_COLOR)
    slider = cv2.imdecode(np.frombuffer(slider_bytes, np.uint8), cv2.IMREAD_COLOR)
    if bg is None or slider is None:
        raise ValueError("image decoding failed")
    if slider.shape[0] > bg.shape[0] or slider.shape[1] > bg.shape[1]:
        raise ValueError("template must fit inside the background")
    
    # 策略1：Canny边缘检测 + 模板匹配
    bg_gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
    slider_gray = cv2.cvtColor(slider, cv2.COLOR_BGR2GRAY)
    bg_edge = cv2.Canny(bg_gray, 100, 200)
    slider_edge = cv2.Canny(slider_gray, 100, 200)
    if not np.any(bg_edge) or not np.any(slider_edge):
        raise ValueError("background/template has no usable edges")
    
    result = cv2.matchTemplate(bg_edge, slider_edge, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    
    if not math.isfinite(max_val) or max_val < min_confidence:
        raise ValueError(f"template confidence below calibrated threshold: {max_val:.4f}")
    return max_loc[0]

# 需要alpha mask、重排或坐标缩放时，按当前图片与提交样本单独验证
```

**失败分支**：低置信度先检查图片恢复、模板与坐标；阈值由本地标注样本校准，不按通用常量直接提交或切换线上服务。

### slider-yunma（云码API滑块识别）

```python
# 优先级：OpenCV后的兜底方案
# 依赖：requests
import requests, base64, os

def recognize_slider_yunma(bg_b64: str, slider_b64: str, token: str = None) -> int:
    """云码API双图滑块识别
    返回：缺口 x 坐标
    """
    url = "http://api.jfbym.com/api/YmServer/customApi"
    key = token or os.environ.get("YUNMA_TOKEN")
    if not key:
        raise ValueError("missing YUNMA_TOKEN")
    resp = requests.post(url, data={
        "token": key,
        "type": "20111",  # 滑块类型
        "image": bg_b64,  # 背景图base64
        "extra_image": slider_b64,  # 滑块图base64（如有双图接口）
    }, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") == 10000:
        value = data["data"]["data"]
        if isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit():
            raise ValueError("invalid slider coordinate")
        return int(value)
    raise ValueError(f"云码识别失败，code={data.get('code')}")
```

**失败分支**：API 超时先保留错误并停止盲重试；图片和授权范围仍有效时再选择匹配识别器。算术 OCR 不替代滑块定位。

### click-yunma（点选识别）

```python
# type=30103 点选验证码
# type=30008 九宫格（阿里Baxia）
import os
import requests

def recognize_click_yunma(img_b64: str, extra: str = "click", token: str = None):
    """返回已解析的服务响应；坐标 schema 和业务消费另按当前版本验证。"""
    url = "http://api.jfbym.com/api/YmServer/customApi"
    key = token or os.environ.get("YUNMA_TOKEN")
    if not key:
        raise ValueError("missing YUNMA_TOKEN")
    resp = requests.post(url, data={
        "token": key,
        "type": "30103",  # 或 "30008"
        "image": img_b64,
        "extra": extra,
    }, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != 10000:
        raise ValueError(f"云码识别失败，code={payload.get('code')}")
    return payload
```

以上云码 endpoint、类型和响应路径是既有示例契约，当前服务未在线验证；使用前核对当前文档与真实样本。
离线 mock 只能证明请求组装和响应分支，不证明 API 可用、图片识别正确或验证码通过。

### arithmetic-ddddocr（算术验证码）

```python
# 依赖：ddddocr
import ddddocr
import operator
import re
def solve_arithmetic(img_bytes: bytes) -> str:
    ocr = ddddocr.DdddOcr(show_ad=False)
    expr = ocr.classification(img_bytes)
    # 本例仅支持两个整数的加、减、乘；其他题型明确拒绝，不执行OCR文本
    expr = expr.replace("x", "*").replace("×", "*")
    match = re.fullmatch(r"\s*(\d{1,6})\s*([+*\-])\s*(\d{1,6})\s*(?:=\s*\??)?\s*", expr)
    if not match:
        raise ValueError("算术题超出本地白名单或OCR结果不可信")
    operations = {"+": operator.add, "-": operator.sub, "*": operator.mul}
    return str(operations[match[2]](int(match[1]), int(match[3])))
```

---

## 行为数据记录

- 仅在当前协议消费行为事件时处理；记录事件类型、目标元素、触发顺序和真实采样，不生成默认“人类轨迹”。
- 区分原图/CSS 像素、归一化坐标、绝对坐标与位移；记录转换公式、原点、边界、舍入顺序。
- 明确时间戳/相对耗时、秒/毫秒/微秒、墙钟/单调时钟、起算事件；不随意混用或随机改写。
- 事件顺序与采样间隔按真实样本和 SDK 序列化确认；不预设观察时长、固定速度、过冲回拉或高斯点击。
- 比较输入事件、SDK 收集结果、编码结果和实际发送载荷；异步完成用已观察事件/返回值确认，不用固定延迟代替。
- 既有回归夹具若为合成，明确标注 `SYNTHETIC`、生成目的和预期结构；只验证解析/坐标/序列化，不能作为行为真实性或供应商通过证据。
- 缺少事件或时间字段来源时标为未闭合，转 `web-reverse-master` 补证据；不靠补一套随机模板填空。
