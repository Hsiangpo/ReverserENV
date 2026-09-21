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

echo "═══ 2. 三平台 skills 软链 ═══"
EXPECT=$(ls "$SRC/skills" | wc -l | tr -d ' ')
for pdir in "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.zcode/skills"; do
  n=0
  for l in "$pdir"/*/; do
    s=$(basename "$l"); [ "$s" = ".system" ] && continue
    [ -f "$l/SKILL.md" ] && n=$((n+1))
  done
  if [ "$n" = "$EXPECT" ]; then ok "${pdir}（${n}/${EXPECT}）"; else bad "${pdir} 计数不符（${n}/${EXPECT}）"; fi
done

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

echo "═══ 5. 全局准则挂载 ═══"
if grep -q "@reverse_principles.md" "$HOME/.claude/CLAUDE.md" 2>/dev/null && [ -f "$HOME/.claude/reverse_principles.md" ]; then
  ok "~/.claude/CLAUDE.md @include + 附件"
else bad "~/.claude/CLAUDE.md 准则未挂载或附件缺失"; fi
if grep -q "逆向准则" "$HOME/.codex/AGENTS.md" 2>/dev/null; then ok "~/.codex/AGENTS.md 内联"; else bad "~/.codex/AGENTS.md 缺准则"; fi

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
