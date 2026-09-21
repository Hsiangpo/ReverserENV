# 外部工具选择与隔离

仅当项目内 Skill、脚本和已注册 MCP 无法闭合当前证据缺口时读取本文件。这里是候选索引，
不是默认依赖清单，也不授权安装、联网下载、扫描、重放或修改目标。

## 依赖卫生

- Python 包只装入项目 `./venv`，按当前任务最小选择；在站点交付目录记录已验证版本或 lock。
- Node.js 工具只使用项目本地、已固定且进入 lockfile 的版本；禁止全局安装和临时解析 latest。
- 下载的二进制或仓库固定版本/commit/hash，先在任务目录离线验证，再决定是否进入长期工具链。
- 外部工具的“执行成功”只证明该工具运行过，不能替代调用栈、字节对拍或服务端业务语义。
- 任何主动扫描、请求重放、handler、Intruder、代理改写或凭据使用仍按具体动作单独授权。

安装依赖属于配置修改：先给出包名、固定版本、用途和卸载方式，获得用户确认后，才可通过
`./venv` 或项目 lock 安装。不得依赖当前机器碰巧已有的全局包或根 `node_modules`。

## 候选索引

| 缺口 | 候选 | 适用边界 |
|---|---|---|
| obfuscator.io / webpack 解包 | [webcrack](https://github.com/j4k0xb/webcrack) | 先用 `ast-deobfuscation`；只有已知模式更适合 webcrack 时才引入固定版本 |
| 纯格式化 | [js-beautify](https://github.com/beautifier/js-beautify) | 只做可读性变换，不作为语义还原证据 |
| HTTPS 代理与脚本化分析 | [mitmproxy](https://github.com/mitmproxy/mitmproxy) | 本仓默认已有 Reqable/Cloak 取证面；WireMCP 当前为隔离候选，代理改写和重放需单独授权 |
| 桌面抓包/综合分析 | [Yakit](https://github.com/yaklang/yakit)、[whistle](https://github.com/avwo/whistle) | 不默认注册为 MCP，不替代原始流量留存 |
| 手动数据变换 | [CyberChef](https://github.com/gchq/CyberChef) | 记录完整 recipe；不能以“可解码”代替字段来源证明 |
| 国密算法 | [gmssl](https://github.com/duanhongyi/gmssl) | 算法、输入与编码已实证后，由 `param-encryptor` 最小引入 |
| ECDSA | [python-ecdsa](https://github.com/tlsfuzzer/python-ecdsa) | 先确认曲线、DER/raw 格式、nonce 与哈希输入 |
| 未知 Protobuf schema | [blackboxprotobuf](https://github.com/nccgroup/blackboxprotobuf) | 推断结果必须用多样本和真实消息语义复核 |
| 本地验证码 OCR | [ddddocr](https://github.com/sml2h3/ddddocr) | 只在 `captcha-solver` 的具体识别缺口需要时安装 |

## 浏览器与采集框架边界

DrissionPage、pydoll、nodriver、Crawlee、Scrapy、Colly 等可作为外部研究对象，但不进入本项目
默认依赖。本项目禁止用 Selenium、Playwright、Puppeteer 或同类页面自动化完成生产采集；
若短时 CDP/真实浏览器取证确有必要，仍须沿 `web-reverse-master` 选定的单一路线执行，产物
必须显式标注 browser/oracle 依赖。

线上签名服务、云端“开箱即用” signer 和来源不明的爬虫合集不得作为交付依赖：它们无法提供
输入谱系、版本锚点和可复核的本地实现，还可能外发 Cookie、token 或待分析样本。

## 采用检查

采用任一候选前记录：

1. 当前内置工具缺少的具体能力，以及为什么不能通过已有 Skill/MCP 完成。
2. 固定版本、上游 URL、license、hash/commit、运行入口和最小依赖。
3. 是否联网、读取凭据、修改流量、写用户目录或启动长期进程。
4. 离线 smoke test、真实样本判官、卸载/回退步骤和仍未闭合的字段。

未满足以上条件时，只能把该工具列为候选，不得写入项目 MCP、Skill 运行路径或长期配置。
