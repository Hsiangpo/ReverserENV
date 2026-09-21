# 基础密码与编码配方

按已实证的算法类型读取本文件。代码是复现骨架，目标的 Key、IV、Mode、Padding、AAD、字符表和输出格式仍须由样本确认。

## 哈希签名

### 配方1: hash-md5（标准MD5）

```python
import hashlib

def md5_sign(data: str) -> str:
    """标准MD5签名"""
    return hashlib.md5(data.encode()).hexdigest()

# 典型用法：
# 工信部 authKey = MD5("testtest" + str(timestamp_ms))
# 饿了么 MTOP sign = MD5(token + "&" + t + "&" + appKey + "&" + data)
# Spider Demo sign = MD5(f"{timestamp}{page}" + salt)
```

### 配方2: hash-md5-custom（京东自定义MD5）

```python
# 京东H5ST SDK魔改MD5
# 特征：SDK MD5("hello") != 标准 MD5("hello")
# 处理：直接加载原始SDK的CryptoJS模块
# 参考：sites/jd_search/assets/js/js_security_v3_0.1.6.js（参考实现）
```

**重要**：遇到标准 MD5 输入但输出与 `hashlib.md5()` 不一致，先核对输入类型与编码；确认是自定义 MD5 后加载原始 SDK 或复现其 padding/盐。

### 配方3: hash-sm3（国密SM3）

```python
from gmssl import sm3  # 依赖 gmssl；只装入项目 venv

def sm3_hash(data: str) -> str:
    """UTF-8 文本的标准 SM3，返回 64 个 hex 字符。"""
    # gmssl 会就地 append padding，必须传可变字节列表。
    return sm3.sm3_hash(list(data.encode('utf-8')))
```

### 配方4: hash-murmur3（MurmurHash3 x64 128）

```python
# 顶象Verify5设备指纹哈希
# 纯Python实现，与fingerprintjs v2对齐
def murmur_hash_128(key: str, seed: int = 0) -> str:
    """MurmurHash3 x64_128"""
    # 完整实现参考 sites/verify5/core/crypto.py（参考实现）
```

## 对称加密

### 配方5: aes-cbc（AES-128-CBC）

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

def aes_cbc_encrypt(data: str, key: bytes, iv: bytes) -> str:
    """AES-CBC + PKCS7 + Base64；key/IV 必须由当前样本显式传入。"""
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(data.encode(), 16))
    return base64.b64encode(encrypted).decode()

# 变体：
# 历史版本出现过 ASCII '0' IV、ECB、指纹派生 key/IV 等变体；
# 当前模式、key/IV 来源和编码必须重新确认，不能沿用旧固定值。
```

### 配方6: aes-ctr（AES-256-CTR）

```python
# 顶象Verify5专用
from Crypto.Cipher import AES
from Crypto.Util import Counter

def aes_ctr_encrypt(data: bytes, key: bytes, nonce: bytes) -> bytes:
    ctr = Counter.new(128, initial_value=int.from_bytes(nonce, 'big'))
    cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
    return cipher.encrypt(data)
```

### 配方7: aes-gcm（AES-GCM）

```python
# 京东jcap / 字节rmc-captcha专用
# 通常在WASM内部完成，需通过Node.js桥接
```

### 配方8: des-ecb（DES-ECB·数美专用）

验证码场景交 `captcha-solver` 确认当前协议与参数；这里仅保留算法层示例。DES key、模式、padding 和字段编码必须由当前目标版本与输入输出证明，不再依赖旧固定密钥字典。

```python
# DES key 为8字节；文本、hex或其他来源先按实际契约解码，不套旧字典
# 零填充（非PKCS7）；整块输入是否追加一块由当前样本明确选择
from Crypto.Cipher import DES
import base64

def des_ecb_encrypt(data: str, key: bytes, *, append_full_block: bool) -> str:
    data_bytes = data.encode('utf-8')
    pad_len = (-len(data_bytes)) % 8
    if append_full_block and pad_len == 0:
        pad_len = 8
    data_bytes += b'\x00' * pad_len
    cipher = DES.new(key, DES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(data_bytes)).decode()
```

### 配方9: rc4（RC4·抖音专用）

```python
def rc4_encrypt(plaintext: bytes, key: bytes) -> bytes:
    """标准 RC4 字节变换；编码和 key 来源由调用方按当前入口确认。"""
    if not isinstance(plaintext, bytes) or not isinstance(key, bytes):
        raise TypeError("plaintext and key must be bytes")
    if not 1 <= len(key) <= 256:
        raise ValueError("RC4 key must contain 1..256 bytes")
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) % 256
        S[i], S[j] = S[j], S[i]
    result = bytearray()
    i = j = 0
    for k in range(len(plaintext)):
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        result.append(S[(S[i] + S[j]) % 256] ^ plaintext[k])
    return bytes(result)
```

## 非对称加密

### 配方10: rsa-pkcs1（RSA PKCS1v1.5）

```python
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64

def rsa_encrypt(data: str, public_key_b64: str) -> str:
    """RSA PKCS1v1.5 加密 + Base64
    典型用途：密码加密（B站/京东/丰巢）、AES密钥传输（极验）
    """
    der_key = base64.b64decode(public_key_b64)
    key = RSA.import_key(der_key)
    cipher = PKCS1_v1_5.new(key)
    encrypted = cipher.encrypt(data.encode())
    return base64.b64encode(encrypted).decode()

# 变体：
# B站密码：plaintext = hash_salt + raw_password
# 极验w后缀：RSA(AES密钥).hex()（注意输出hex非base64）
# 极验固定公钥N和E=65537
```

## 自定义编码

### 配方11: base64-custom-douyin（抖音自定义Base64）

```python
# 5套字符表 s0-s4
S1 = "Dkdpgh4ZKsQB80/Mfvw36XI1R25+WUAlEi7NLboqYTOPuzmFjJnryx9HVGcaStCe="
S2 = "Dkdpgh4ZKsQB80/Mfvw36XI1R25-WUAlEi7NLboqYTOPuzmFjJnryx9HVGcaStCe="
S4 = "Dkdpgh2ZmsQB80/MfvV36XI1R45-WUAlEixNLwoqYTOPuzKFjJnry79HbGcaStCe"
```

### 配方12: base64-custom-geetest（极验自定义Base64）

```python
# 字符集替换：+→(, /→)
# 位掩码：[7274496, 9483264, 19220, 235]
# 完整实现参考 sites/bilibili_login/src/geetest_crypto.js（参考实现）
```

### 配方13: xor-encode（XOR编码）

```python
# 字节级循环 XOR；token 的文本/hex/Base64 解码按当前入口确认
def xor_encode(token: bytes, data: bytes) -> bytes:
    if not isinstance(token, bytes) or not isinstance(data, bytes):
        raise TypeError("token and data must be bytes")
    if not token:
        raise ValueError("XOR token must not be empty")
    return bytes(value ^ token[i % len(token)] for i, value in enumerate(data))
```

## 字节编码与随机信封的不变量

- 文本字符串、二进制字符串、TypedArray、hex 与 Base64 分开记录。UTF-8、Latin-1、整数端序、位宽、符号位和截断位置都需入口证据；二进制值不能默认 UTF-8，也不能用 `errors='replace'` 吞掉越界字符。
- 自定义字符表需验证映射可逆、字符唯一性和 padding 规则；固定熵源后做 `encode(decode(payload)) == payload` 的精确往返，再用非样例 oracle 对拍，不能宽松补齐后只比较长度。
- 信封分别记录版本、key ID、公钥来源/轮换、长度字段的端序、封装密钥、nonce/IV、AAD、tag、ciphertext 的确切位置。顺序与长度来自当前协议，不套固定版本号或旧偏移。
- AES-GCM 校验 AAD 的原始字节、nonce、tag 长度和位置；对同一个 key 不得重复使用 nonce。旧客户端出现固定 nonce 时必须追踪 key 是否每次重新生成，不能把该组合当通用加密模板。
- SealedBox、RSA padding 或其他随机封装不能只凭两份密文不同断言错误；使用独立解密/认证检查，或在可控测试中固定全部熵源后逐字节比较。自解密成功仍不能替代服务器业务验收。
- SM4 核对 key 为实际16字节、模式、padding 与派生链；hex 字符串截取与原始字节截取不同，必须保存每步字节。SM2 核对 user ID/ZA、公钥、预哈希与签名编码，是否启用库的 hash 选项取决于其 API 契约，不能默认重复哈希。

## 诊断速查

| 症状 | 优先核对 | 仍失败时 |
|---|---|---|
| 签名与 oracle 不匹配 | 原始字节、字段顺序、盐与自定义算法 | 在浏览器内调用入口并导出第一处差异 |
| Python MD5 != SDK MD5 | 输入类型、UTF-8/Latin-1、padding | 复现 SDK 变体或最小加载原模块 |
| AES 输出不同或解密乱码 | Key、IV/nonce、Mode、Padding、AAD、tag 顺序 | 对比每层密文长度和输出编码 |
| RSA 被拒 | 公钥版本、PKCS1v1.5/OAEP、分段、hex/Base64 | 对拍信封布局和明文拼接 |
| 自定义 Base64 解码失败 | 字符表、位掩码、padding 规则 | 从原函数导出字符表逐字符验证 |

Python 常用依赖为 `pycryptodome`、`gmssl`；只安装实际需要的包到项目 venv。
