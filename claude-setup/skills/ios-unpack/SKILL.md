---
name: ios-unpack
description: iOS 砸壳与脱壳。识别 FairPlay 加密(cryptid)→选砸壳方案→执行(手工 frida 内存 dump 优先/bfdecrypt 备选；frida-ios-dump·bagbak·dumpdecrypted 本机已弃用)→校验原加密区间字节、Mach-O 结构和反汇编→产出可静态分析的 decrypted IPA/Mach-O。cryptid=0 不能单独验收。含 dyld_shared_cache 抽取系统库。触发词：砸壳、脱壳、解密、FairPlay、cryptid、frida-ios-dump、bagbak、bfdecrypt、dumpdecrypted、dump ipa、dyld cache 抽库。
---

> ⚠️ **本机环境适配（20260920 维护注）**：本机为 macOS，`ios-device` MCP 老师仍未分发（0818 包只有 frida-mod 设备端与工具）；ida-pro 需付费未装。设备连接用 `frida-agent` MCP / 项目 venv 的 frida / `pymobiledevice3`；SSH 直连设备用 mac 原生工具；提头优先 mac 原生 `class-dump` / `otool`（jtool2 如未装则 brew 安装或以 class-dump 替代）。下文提及 ios-device 工具（`ios_info`/`ios_ssh` 等）的段落按此替代执行。

# iOS Unpack —— 砸壳与脱壳

## 角色定位

把 **FairPlay 加密的 App Store 二进制**解密成明文，让 ios-recon / ios-protocol-signature 能静态分析。这里的“砸壳”处理 **Apple 官方 FairPlay DRM**：指定文件区间在进程加载时解密到内存，再将对应明文字节回写副本；cryptid 不判断其他混淆或运行期变换。

来源渠道只作先验，不作判官：App Store、TestFlight、enterprise、ad-hoc 或自签件都按当前 build、每个 Mach-O/slice 的 `LC_ENCRYPTION_INFO(_64).cryptid` 决定是否砸壳；原始、解密、重签产物分开保存并各记 SHA-256。

**范围与状态优先于后文模板**：先核已有文件和加密区间。仅本地分析/设计不连接设备；确需内存字节且当前任务允许时，优先利用正在运行的目标进程并固定身份。attach 失败不自动 spawn；需保留注册/session 时不得为砸壳重启、重装或删状态，缺失内容按区间留待补证。冷启动、安装 tweak 和 respring 各自需要当前范围允许及影响/恢复说明。

> ⚠️ **工具纪律**：阉割点/版本/弃用替代 **只查 ios-recon「工具阉割矩阵」**，本节不重复。本机 `tools/frida-ios-dump` 是 AloneMonkey **未补丁**原版 → **不要跑**。砸壳默认方案 A。

## 砸壳原理

```
App Store 二进制:  LC_ENCRYPTION_INFO(_64).cryptid = 1
                   [cryptoff, cryptoff+cryptsize] 被 FairPlay 加密
                   ⚠ cryptsize 可能远小于 __TEXT（酷牛=4096，只加密一小段）
                   ↓ 进程启动，内核把这段解密进内存
砸壳:  运行 App → 从内存读 [cryptoff, cryptsize] → 覆写文件对应偏移
       → cryptid 改成 0 → 明文 Mach-O
```

## 决策树（选砸壳方案）

```
目标加密(cryptid=1)?
   │
   ├─ 越狱机(本项目基线) ── 首选顺序:
   │     1. 手工 frida 内存 dump（纯原生，走 27045）→ 最可控，适配部分加密
   │     2. bfdecrypt（OTA 后可能没装：ios_apt_search/install）
   │     3. bfdecrypt 仍没有、又不能手工 dump 时 → 停，回矩阵找替代；**不要**启用未补丁的 frida-ios-dump/bagbak
   │
   └─ 非越狱机 ──
         本机实测：TrollStore 骗过 CoreTrust 也拿不到任意进程 task port
         → 只能重签目标进 get-task-allow 或塞 gadget；要无限制 dump = 完整越狱
```

## 方案 A：手工 frida 内存 dump（首选，已在酷牛验证）

走魔改 27045 + 纯原生 JS（无 ObjC）。读 Mach-O header 找 `LC_ENCRYPTION_INFO_64`（cmd=0x2C）的 cryptoff/cryptsize，再找**覆盖该文件区间的 segment**。运行时地址不是无条件 `base+cryptoff`：

```
runtime = module.base + (segment.vmaddr - __TEXT.vmaddr) + (cryptoff - segment.fileoff)
```

只有目标位于 `__TEXT(fileoff=0)` 时才退化成常见的 `module.base+cryptoff`。从 `runtime` 读 `cryptsize`；薄 Mach-O 在主机文件的 `cryptoff` 覆写，FAT 则在 `slice_file_base + cryptoff` 覆写，并在同一 slice 对应 load command 的 cryptid 字段改 0。

```python
# 骨架：核目标 UDID/进程身份 → 已运行进程最窄 attach → LC/segment 映射 → 读 runtime
# 仅在证据表明必须冷启动且当前任务允许时选择 spawn；本地设计不执行连接。
# 参考 projects/kuniu/dump_kuniu.py（部分加密只 dump 4096B 那一段）
```

要点：
- **按 LC 里的 cryptoff/cryptsize dump，不要假设整段 __TEXT**。
- **按 segment 做 fileoff→vmaddr 映射**；仅在 `__TEXT.fileoff=0` 且覆盖 cryptoff 时允许 `base+cryptoff` 快路径。
- 模块尚未映射时做有界等待，核当前进程/模块身份；不能因读取失败自动重启目标。
- `Memory.readByteArray` 已移除，必须 `ptr.readByteArray(len)`。
- 主二进制砸完还要扫 `PlugIns/*.appex`、`Frameworks/*.framework`（各有自己的 cryptid）。懂车帝：主二进制+12 个 framework 已砸，3 个 appex 仍加密（可暂缓）。

## 方案 B：bfdecrypt（设备 tweak，OTA 后先确认）

```bash
# 先看还在不在
ios_apt_list("bfdecrypt")
# 没有：ios_apt_search("bfdecrypt") → ios_apt_install(...) → respring
plutil -p /var/mobile/Library/Preferences/com.level3tjg.bfdecrypt.plist
# 前台启动目标 → 默认 /var/mobile/Documents/<App>.ipa
ios_pull("/var/mobile/Documents/Target.ipa", "projects/<target>/ipa/Target.ipa")
```

## 方案 C / D（frida-ios-dump · bagbak · dumpdecrypted）— 本机弃用

见 ios-recon 矩阵：`tools/frida-ios-dump` 仍 USB+alpine+ObjC；bagbak/dumpdecrypted **仓库无可用产物**、已弃用。再 clone、对未补丁副本打补丁、或临时编 dylib 都算开环——**统一回方案 A 手工 dump**（`projects/kuniu/dump_kuniu.py`）。

## 校验解密产物（必做）

```bash
otool -l Target.decrypted | grep -A5 LC_ENCRYPTION_INFO   # 当前 slice 的 cryptid 必须 = 0
# 如当前任务允许设备只读，可用现有设备端 jtool2；不为本地验收自动补装或启动 App
jtool2 -d objc Target.decrypted | head
# strings/可读类名只作辅助，不能证明 cryptoff/cryptsize 区间已经解密
```
cryptid=0 仅表示文件头已标记，不证明密文字节被替换；符号缺失/类名不可读也不能单独判失败。部分加密可能仅有 4096B，其余明文里的类名和 URL 不能替该区间验收。至少完成以下核对：

1. 原文件与运行期模块的 build、UUID、架构及 segment 映射一致；核 cryptoff/cryptsize、slice 和目标文件边界，读取完整长度，保留来源与缓冲区 hash。
2. 输出对应区间与实际读取的明文缓冲区逐字节一致；除这些区间与记录过的 cryptid 字段外，差异必须逐项解释。仅修改 cryptid、读错模块或短读不能通过。
3. 在新打开的静态分析结果中验证**原加密区间本身**的指令/数据结构、目标函数边界与引用一致性，结合运行期来源证据判断；不能用其他区间 strings 或工具退出码代替。无法验证的范围标未解。
4. 每个目标 Mach-O/slice 单列结果；未采到的另一架构或扩展不能随主程序一并标成功。静态分析交付不要求重签安装或启动验证。

校验还要记录 App build、原文件 SHA-256、输出 SHA-256、slice 架构、slice_file_base、cryptoff/cryptsize 和修改后的 cryptid 偏移。FAT Mach-O 必须逐 slice 解析，宿主文件写入点是 `slice_file_base + cryptoff`，不能拿旧版本或另一架构的 offset 套当前文件。

## dyld_shared_cache 抽取

```bash
ls /System/Library/Caches/com.apple.dyld/    # 或 /var/db/dyld/
ipsw dyld extract dyld_shared_cache_arm64 /usr/lib/libcommonCrypto.dylib
```

## 交接给下游

- 解密二进制 → 回 **ios-recon** 提头 / **ios-protocol-signature** 定位算法。
- 要 hook 运行时（而非静态）→ **ios-dynamic**。

## 常见坑（失败模式编码 U-xx）

> 每条格式：**编码 现象** → 原因/规则。**成本**=不知道这条会白费多少。
- **U-01 去跑 tools/frida-ios-dump 或再 clone 一份** → 原版未补，矩阵已弃用。走方案 A。**成本**：卡在 USB/ObjC/alpine 数小时。
- **U-02 attach 目标失败** → 挂起只是候选，先核进程与连接证据；需保留状态时停止升级侵入度。只有确需且当前范围允许冷启动才 spawn。**成本**：把采集失败变成会话重置。
- **U-03 dump 出来 cryptid 还是 1** → 核当前 slice 的标记偏移及实际字节来源；改成 0 仍须通过原加密区间的独立验收。**成本**：只改头的假解密文件进入后续分析。
- **U-04 去装 bagbak** → 矩阵：不装。**成本**：折腾 node 半天。
- **U-05 只砸了主二进制，漏了 PlugIns/Frameworks** → 各自检查加密状态并单列已解/未解，不从主程序外推。**成本**：关键逻辑在未验收组件，反复回头补证。
- **U-06 想用 dumpdecrypted（网上多为 armv7）** → 已弃用（见矩阵），别为它编 arm64。走方案 A。**成本**：注入不生效查半天。
- **U-07 OTA 后 bfdecrypt/jtool2 不存在** → `/var/jb` 已空。先 `ios_apt_list` 再装，别改脚本。**成本**：当砸壳方案失效。
- **U-08 整段 __TEXT dump 但 cryptsize 只有 4K** → 部分加密。按 LC 字段 dump。**成本**：传几百 MB、对不齐偏移。
- **U-09 用依赖 ObjC 的 dump 脚本打 27045** → 本机魔改无 ObjC。改纯原生读 header。**成本**：脚本 load 即报 ObjC is not defined。
- **U-10 把旧 build 的 cryptoff/RVA 套新 IPA** → 每个版本、主二进制、appex、framework 都独立解析 LC 与 hash；升级后旧偏移只作地标。**成本**：覆写错段仍可能得到可打开的假产物，后续静态结论全部漂移。
- **U-11 无条件用 `module.base+cryptoff`** → cryptoff 是文件偏移，先按所属 segment 映射到 vmaddr；只在 `__TEXT.fileoff=0` 快路径成立。**成本**：非典型布局/framework 读错内存并把密文或别段写回。
