# 参数组装器配方

组装器的每一段都应保存中间值并单独对拍。下列结构来自既有实战版本，使用前重新确认 SDK 版本、输入顺序、生命周期与输出格式。

## 配方14: h5st-assembler（既有目标的 H5ST 10 段示意）

下列 10 段只描述所引既有实现，当前目标/SDK 版本尚未在本参考中实测；不是京东全平台统一格式。
其他资料里的 8 段示意不能与这里拼接或互相补字段，当前段数、版本和时间编码以实际发送值及入口为准。

```text
格式：datetime;fp;appId;token;signHash;version;timestamp;expandParams;bodyHash;eidHash

生成流程：
1. _$cps: 参数排序为key-value数组
2. _$pam: 校验token/fingerprint
3. _$clt: 生成随机fp + 指纹数据
4. _$gdk: 密钥派生（token→自定义哈希链）
5. _$gs: 生成signHash（自定义MD5）
6. _$gsd: 生成bodyHash（自定义MD5）
7. _$gsp: 组装h5st字符串

历史版本线索：该 SDK 使用自定义 CryptoJS，标准 MD5/SHA256 不能直接替换
     → 先核对当前 SDK 与中间字节；可复现变体或最小加载对应版本原模块

实现参考：sites/jd_search/src/signer.js（参考实现）, sites/h5st533商详/h5st5_3_3.js（参考实现）
```

同名签名在不同业务与版本上可能使用不同 padding、盐、派生链和输入类型。先逐段记录当前入口与中间字节，不能套用其他站点的 appId 或旧 SDK 常量。

## 配方15: abogus-assembler（抖音A-Bogus生成器）

```text
格式：前缀(random) + Base64(RC4(SM3(params)))

生成流程：
1. URL参数 + "cus" → SM3哈希 → params_array
2. HTTP方法 + "cus" → SM3哈希 → method_array
3. 浏览器信息 → charCode数组
4. 时间戳相关参数
5. 组合 → RC4加密(key="y") → 自定义Base64编码(s1/s2/s4字符表)
6. 加上随机前缀

运行耗时需在当前输入、实现和机器上实测，不沿用历史性能数字。
参考：sites/douyin_abogus/abogus_local.py（参考实现）
```

二进制字符串与 Latin-1/UTF-8 转换按 [密码与编码](crypto-primitives.md) 的字节不变量核验；当前常量和业务结果从目标证据提取。

## 配方16: mtgsig-assembler（大众点评mtgsig）

```text
格式：HTTP Header mtgsig: JSON{a1,a2,a3,a5,a6,a8,a9,a10,x0,d1}

生成流程：
1. aS VM加载字节码 → 计算a8/a5/a6
2. 纯算修复a9/d1
3. a1=签名版本, a2=时间戳, a3=随机UUID
4. x0=设备指纹数据
5. d1 = MD5(concat) XOR temp_array

历史记录：VM可产出签名，但服务器端验证403；该记录不代表当前版本状态。
失败出口：先对比字段与中间字节，再核对上游状态和请求上下文；a9/d1 与 `hybrid_signer` 仅是该历史样本线索，单个403不能定位根因。未闭环前禁止宣称已还原。
参考：sites/dianping/src/hybrid_signer.js（参考实现） + aS_vm.js（参考实现）
```

## 配方17: mtop-signer（饿了么MTOP签名）

```python
def mtop_sign(token: str, t: str, app_key: str, data: str) -> str:
    """MTOP签名 = MD5(token + "&" + t + "&" + appKey + "&" + data)"""
    import hashlib
    raw = f"{token}&{t}&{app_key}&{data}"
    return hashlib.md5(raw.encode()).hexdigest()

# token: Cookie _m_h5_tk 的 "_" 前缀部分
# t: 13位毫秒时间戳
# appKey: 固定 "12574478"
# data: POST body中data字段的原始JSON字符串
```

## 派生字段与透传状态

- 把每个字段及嵌套 key/IV 的来源、输入类型、序列化、生命周期与消费位置写入谱系；多层哈希或 token 驱动的派生图逐节点保存中间值，不从名字推断算法。
- 原始对象、规范化签名串、密文与最终封装分别捕获。签明文还是密文、先签还是先加密、重复包装层级均以实际调用为准；生成一个新对象不要意外修改待签对象。
- 本地 sensor/编码器输出与服务器签发 Cookie/token 分别验收。回传值的存在和格式不证明挑战或业务接受；状态/TTL/刷新与未知绑定交 [协议与状态指南](../../web-reverse-master/references/14-risk-protocol-and-state.md) 处理。
- 复用原 SDK/WASM 时声明运行依赖。固定时间、随机源及上游值后对至少三组非样例输入逐字节比较；原始 body 的空格、顺序与编码不能被请求库二次序列化改变。

## 组装器选择

```text
标准算法
├─ MD5/SHA → Python hashlib
├─ AES-CBC/ECB → pycryptodome
├─ RSA → pycryptodome PKCS1_v1_5
└─ RC4/XOR → 经过样本验证的最小实现

自定义变体
├─ 自定义Base64 → 导出字符表并手写编解码
├─ 自定义MD5 → 复现 padding/盐，或最小加载原始SDK模块
└─ 自定义哈希链 → 提取密钥派生 DAG 并保存中间值

复杂执行体
├─ JS SDK → Node.js subprocess 最小加载
├─ WASM → Node.js 真 WASM 桥接或静态分析
└─ VM字节码 → 先完成 dispatcher/handler 证据链
```

不要因为配方名称相同就跨 SDK 版本复用。若最终字段一致但业务拒绝，冻结 assembler 输出，转查上游 token、设备态、序列化和请求上下文。
