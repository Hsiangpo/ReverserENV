#!/usr/bin/env bash
# 逆向工具链终验：源=live 一致性 / 三平台软链 / 脚本语法 / 全角贴变量 / newrev 三模式干跑
# 用法: bash <仓库>/.claude/skills/toolchain-updater/scripts/verify.sh [--quick]
set -uo pipefail   # 不用 -e：单项失败要继续跑完出全报告

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
SRC="$REPO/claude-setup"
LIVE="$HOME/.claude/reverse-toolchain"
QUICK=0
[ "${1:-}" = "--quick" ] && QUICK=1
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "  ✅ ${1}"; }
bad()  { FAIL=$((FAIL+1)); echo "  ❌ ${1}"; }

echo "═══ 1. 源 = live（skills / rules / bin / templates） ═══"
for d in skills rules bin templates; do
  if diff -rq "$SRC/$d" "$LIVE/$d" >/dev/null 2>&1; then ok "$d 零差异"; else bad "${d} 有差异（diff -rq ${SRC}/${d} ${LIVE}/${d}）"; fi
done

echo "═══ 2. 三平台 skills 软链（自适应：项目级 或 --global-skills 全局） ═══"
# 只数本工具链自己的 skill 名；全局目录里 superpowers 等插件 skill 与本仓库无关
NAMES=$(ls "$SRC/skills")
EXPECT=$(echo "$NAMES" | wc -l | tr -d ' ')
count_ours() {
  local n=0 s
  for s in $NAMES; do [ -f "$1/$s/SKILL.md" ] && n=$((n+1)); done
  echo "$n"
}
GLOBAL_N=0
for pdir in "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.zcode/skills"; do
  GLOBAL_N=$((GLOBAL_N + $(count_ours "$pdir")))
done
if [ "$GLOBAL_N" -eq 0 ]; then
  ok "项目级模式（全局无本工具链 skill；实体在 live+源，newrev 按项目挂载）"
else
  for pdir in "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.zcode/skills"; do
    n=$(count_ours "$pdir")
    if [ "$n" = "$EXPECT" ]; then ok "${pdir}（${n}/${EXPECT}）"; else bad "${pdir} 半挂载（${n}/${EXPECT}）：重跑 install.sh --global-skills 补齐，或删掉残留软链回到项目级"; fi
  done
fi

echo "═══ 3. 脚本语法（bash 3.2） ═══"
for f in "$SRC/install.sh" "$SRC/bin/newrev"; do
  /bin/bash -n "$f" && ok "$(basename "$f")" || bad "$(basename "$f") 语法错误"
done

echo "═══ 4. 全角贴变量扫描（bash 3.2 unbound 坑） ═══"
for f in "$SRC/install.sh" "$SRC/bin/newrev"; do
  m=$(grep -nE '\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7F 0-9A-Za-z_"\/\)\}\.\,\;\:\=\+\-\*\\\|\&\<\>\x27]' "$f" |grep -nE '\$[A-Za-z_][A-Za-z0-9_]*[^ -~]' "$f" | head -3)
  if [ -n "$m" ]; then
    bad "$(basename "$f") 存在 \$var+全角: $(echo "$m" | head -1 | cut -c1-80)"
  else ok "$(basename "$f") 干净"; fi
done

echo "═══ 5. 逆向准则挂载（Claude：项目级相对导入 或 --global-rules；Codex：内联） ═══"
if grep -q "^@claude-setup/rules/reverse_principles.md" "$REPO/CLAUDE.md" 2>/dev/null \
   && grep -q "^@claude-setup/rules/reverse_signature_principles.md" "$REPO/CLAUDE.md" 2>/dev/null; then
  ok "Claude 项目级：仓库 CLAUDE.md 相对导入两份准则"
elif grep -q "^@reverse_principles.md" "$HOME/.claude/CLAUDE.md" 2>/dev/null && [ -f "$HOME/.claude/reverse_principles.md" ]; then
  ok "Claude 全局：~/.claude/CLAUDE.md @include + 附件"
else bad "Claude 准则未挂载（仓库 CLAUDE.md 缺相对导入，全局也没有）"; fi
if grep -q "逆向准则" "$HOME/.codex/AGENTS.md" 2>/dev/null; then ok "~/.codex/AGENTS.md 内联"; else bad "~/.codex/AGENTS.md 缺准则"; fi

echo "═══ 5.5 可移植性：仓库内无本机绝对路径 ═══"
# _meta/参考 是原样留存的外部提示词（含 /home/claude 等非本机路径），排除；老师环境 E:\ 等描述性文字不算
LEAK=$(cd "$REPO" && git grep -n -I -E "/Users/[A-Za-z0-9_.-]+/|/home/[a-z][a-z0-9_-]*/" -- . ':!claude-setup/_meta' 2>/dev/null | head -3)
if [ -z "$LEAK" ]; then ok "无 /Users/<名>/ 或 /home/<名>/ 绝对路径"
else bad "发现绝对路径：$(echo "$LEAK" | head -1 | cut -c1-100)"; fi

echo "═══ 5.6 安卓三件套 / adb（未装只警告，不计失败） ═══"
AMCP="$LIVE/vendor/android_mcp"
if command -v adb >/dev/null 2>&1 || [ -x "$HOME/.local/bin/adb" ]; then ok "adb 可用"
else echo "  ⚠️  没有 adb（install.sh 非 --skip-downloads 会自动装）"; fi
if [ -x "$AMCP/.venv/bin/python" ]; then
  "$AMCP/.venv/bin/python" -c "import frida, mcp" >/dev/null 2>&1 && ok "android_mcp venv 可导入 frida/mcp" || bad "android_mcp venv 缺 frida/mcp"
  [ -n "$(ls -A "$AMCP/toolchain/device/frida" 2>/dev/null)" ] || echo "  ⚠️  魔改 frida-server 缺失（老师包未附带，已知状态）"
else echo "  ⚠️  android_mcp 未装（mcps/安卓/android_mcp.zip 不随 git，需手动拷入后跑 install.sh）"; fi

if [ "$QUICK" -eq 1 ]; then
  echo; echo "── quick 模式，跳过 newrev 干跑 ──"
else
  echo "═══ 6. newrev 四模式干跑（/tmp） ═══"
  T=$(mktemp -d)
  N="$LIVE/bin/newrev"
  ( cd "$T" && "$N" vt1 https://a.com        >/dev/null 2>&1 && [ -f vt1/CLAUDE.md ] && [ -d vt1/.agents/skills ] ) && ok "web"      || bad "web"
  ( cd "$T" && "$N" --ios vt2 com.a.b        >/dev/null 2>&1 && [ -f vt2/CLAUDE.md ] )                                        && ok "ios"      || bad "ios"
  ( cd "$T" && "$N" --android vt3 com.c.d    >/dev/null 2>&1 && [ -f vt3/CLAUDE.md ] )                                        && ok "android"  || bad "android"
  ( mkdir -p "$T/vt4" && cd "$T/vt4" && "$N" --here https://x.com >/dev/null 2>&1 && [ -f CLAUDE.md ] )                       && ok "--here"   || bad "--here"
  rm -rf "$T"
fi

echo; echo "════════ 结果：${PASS} 通过 / ${FAIL} 失败 ════════"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
