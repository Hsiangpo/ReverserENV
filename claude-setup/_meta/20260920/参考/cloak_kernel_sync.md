# 魔改浏览器(Cloak)内核同步铁律(全局,所有项目)

魔改 Chromium(逆向显微镜)有**两份**:主构建 `E:\cr\src\out\Default`(编译输出)+ 便携版 `E:\Cloak-portable`(可分发子集)。二者**极易脱节**——改了内核只重编译到 `E:\cr`,忘了同步到 portable,导致 portable 缺新特性(如 `CLOAK_VM_VARDUMP`)。

## 规则

1. **每次内核重编译后,必须同步到 `E:\Cloak-portable` 并记录**。触发时机:任何 `E:/cr/src` 下改 `runtime-trace.cc`/hook/tracer 源码后 `ninja -C out/Default chrome` 重编译完。

2. **同步文件**(内核改动主要在 chrome.dll,但保持构建一致同步这5个):
   ```bash
   SRC="E:/cr/src/out/Default"; DST="E:/Cloak-portable"
   cp -f "$DST/chrome.dll" "$DST/chrome.dll.bak"   # 先备份可回滚
   for f in chrome.dll chrome.exe resources.pak snapshot_blob.bin v8_context_snapshot.bin; do
     cp -f "$SRC/$f" "$DST/$f"; done
   ```

3. **同步前检查**:确认无 `E:\Cloak-portable` 的 chrome 进程占用(锁文件)——用 `Get-CimInstance Win32_Process -Filter "name='chrome.exe'" | Where ExecutablePath -like '*Cloak-portable*'`。**绝不全局 kill chrome**(会误杀别项目,见多项目隔离)。

4. **验证**:`grep -c CLOAK_VM_VARDUMP "E:/Cloak-portable/chrome.dll"` 应为 1;比对 `E:/cr` 与 portable 的 chrome.dll 大小一致。

5. **记录更新日志**:每次同步在 **`E:\Cloak-portable\UPDATE_LOG.md`** 顶部追加一条(**US 时间 PDT** + 同步文件 + 新增/改的内核特性 + 用途场景 + 回滚备份名)。日志已有模板,照抄填。

## CLOAK_* 内核特性(env-gated,默认关)

`CLOAK_VM_VARDUMP`(数组length取证)· `CLOAK_VM_DEVIRT`(去虚拟化op流)· `CLOAK_VM_TRACE`(VM字节码trace)· `CLOAK_NO_DEBUGGER`(反调试中和)· `CLOAK_HOOK_LOG`(hook全家桶)。改内核加新特性时,同步 + 日志两步都要做。

> 便携版比主构建旧 = 用 portable 跑会缺特性、复现不出实证。**改内核 → 同步 portable → 写 UPDATE_LOG,三步一体,缺一不可。**
