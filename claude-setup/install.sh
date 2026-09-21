#!/usr/bin/env bash
# 一条命令装齐逆向工具链：17 个 skill + newrev + 10 个 MCP + 它们依赖的免费软件。幂等，重跑 = 更新。
#
# 用法（本文件放哪都行，路径不写死）：
#   bash <本目录>/install.sh                      全部装
#   bash <本目录>/install.sh --no-global-skills   skills 不进全局，由 newrev 按项目软链
#   bash <本目录>/install.sh --skip-downloads     跳过大文件（CloakBrowser 150MB / JDK 200MB / jadx 70MB / Reqable 33MB）
#   bash <本目录>/install.sh --core-only          只装 Web 逆向核心（js-reverse×2 / Roxy×2 / chrome-devtools / wiremcp），跳过 App/小程序那些扩展 MCP
#   ROXY_API_KEY=xxx bash install.sh             顺带把 RoxyBrowser 的 Key 配进去
#
# 装完后本目录可以搬走/删掉：所有东西都在 ~/.claude/reverse-toolchain/ 和 ~/.local/
set -euo pipefail

GLOBAL_SKILLS=1; SKIP_DOWNLOADS=0; CORE_ONLY=0
for a in "$@"; do
  case "$a" in
    --no-global-skills) GLOBAL_SKILLS=0 ;;
    --skip-downloads)   SKIP_DOWNLOADS=1 ;;
    --core-only)        CORE_ONLY=1 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "未知参数: ${a}（用 --help 看用法）"; exit 1 ;;
  esac
done

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DST="$HOME/.claude/reverse-toolchain"
VENDOR="$DST/vendor"
SKILLS_DST="$HOME/.claude/skills"
BIN_DST="$HOME/.local/bin"
export PATH="$BIN_DST:$PATH"
# Node 的 fetch 默认不认 HTTP(S)_PROXY，开着系统代理的机器会直连超时；这个变量让它走代理，没代理时无副作用
export NODE_USE_ENV_PROXY=1
ARCH=$(uname -m)   # arm64 / x86_64

echo "==> 源目录: $SRC"
echo "==> 安装到: $DST"

# ---------- 1. 环境检查 ----------
echo; echo "==> 检查依赖"
missing=0
check() {
  if command -v "$1" >/dev/null 2>&1; then printf "  ✅ %-8s %s\n" "$1" "$($2 2>/dev/null | head -1)"
  else printf "  ❌ %-8s 未安装 — %s\n" "$1" "$3"; missing=1; fi
}
check node   "node -v"          "https://nodejs.org 装 20.19+"
check npx    "npx -v"           "随 node 一起装"
check claude "claude --version" "npm i -g @anthropic-ai/claude-code"
check git    "git --version"    "xcode-select --install"
if ! command -v uv >/dev/null 2>&1; then
  echo "  ⚙️  uv 未装，现在装（frida / reqable / jadx 的 MCP 都要它）"
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1 && echo "  ✅ uv $(uv --version 2>/dev/null)" || { echo "  ❌ uv 装失败"; missing=1; }
else printf "  ✅ %-8s %s\n" "uv" "$(uv --version)"; fi
PYBIN=""
for c in python3.13 python3.12 python3.11; do command -v "$c" >/dev/null 2>&1 && { PYBIN="$c"; break; }; done
if [ -n "$PYBIN" ]; then printf "  ✅ %-8s %s\n" "python" "$($PYBIN -V)"
else echo "  ⚠️  只有系统自带 $(python3 -V 2>/dev/null)（已 EOL）。uv 会自己下 3.12 给 MCP 用；你写脚本建议装个新的"; fi
TSHARK=""
for t in "$(command -v tshark 2>/dev/null || true)" /Applications/Wireshark.app/Contents/MacOS/tshark /opt/homebrew/bin/tshark /usr/local/bin/tshark; do
  [ -n "$t" ] && [ -x "$t" ] && { TSHARK="$t"; break; }
done
[ -n "$TSHARK" ] && printf "  ✅ %-8s %s\n" "tshark" "$("$TSHARK" -v 2>/dev/null | head -1)" \
                 || echo "  ⚠️  tshark 未装 — 想要 wiremcp 就装 Wireshark：https://www.wireshark.org/download.html（勾 ChmodBPF）"
[ "$missing" -eq 1 ] && echo "  ⚠️  上面 ❌ 的装完再跑一次。"

# 通用下载函数：dl <url> <目标文件>；已存在且非空就跳过
dl() {
  [ -s "$2" ] && { echo "  ✔︎ 已有 $(basename "$2")，跳过下载"; return 0; }
  echo "  ⬇︎ $(basename "$2") ..."
  curl -sL --retry 3 --max-time 1800 -o "$2.part" "$1" && mv "$2.part" "$2" || { rm -f "$2.part"; return 1; }
}
gh_latest_asset() {   # gh_latest_asset <owner/repo> <名字里含的字符串> → 打印下载 URL
  ( curl -sL --max-time 30 "https://api.github.com/repos/$1/releases/latest" \
    | python3 -c "import sys,json; a=[x['browser_download_url'] for x in json.load(sys.stdin).get('assets',[]) if '$2' in x['name']]; print(a[0] if a else '')" 2>/dev/null ) || true
}

# ---------- 2. 复制到安装目录（原子替换：先拷 .new 再换，防源=目标时自毁） ----------
for d in skills templates bin; do
  [ -d "$SRC/$d" ] || { echo "❌ 源目录不完整：缺 ${SRC}/${d}（本文件夹必须整体拷贝，不能只拷 install.sh）"; exit 1; }
done
if [ "$SRC" = "$DST" ]; then
  echo; echo "==> 直接运行于安装目录（${DST}），无需复制"
else
  echo; echo "==> 复制 skills / templates / bin → $DST"
  mkdir -p "$DST" "$VENDOR"
  for d in skills templates bin; do
    rm -rf "$DST/$d.new"
    cp -R "$SRC/$d" "$DST/$d.new" || { echo "❌ 复制 ${d} 失败"; exit 1; }
    rm -rf "$DST/$d"
    mv "$DST/$d.new" "$DST/$d"
  done
  echo "  ✅ 已复制（重跑本脚本即更新）"
fi
chmod +x "$DST/bin/newrev"

# ---------- 3. skills（Claude Code / ZCode / Codex 三平台软链，都指向同一份实体）----------
if [ "$GLOBAL_SKILLS" -eq 0 ]; then
  echo; echo "==> 跳过全局 skills（--no-global-skills），newrev 会按项目软链"
else
  for SKILLS_DST in "$HOME/.claude/skills" "$HOME/.zcode/skills" "$HOME/.codex/skills"; do
    echo; echo "==> skills → $SKILLS_DST"
    mkdir -p "$SKILLS_DST"; count=0
    for d in "$DST"/skills/*/; do
      name=$(basename "$d"); [ -f "$d/SKILL.md" ] || continue
      if [ -e "$SKILLS_DST/$name" ] && [ ! -L "$SKILLS_DST/$name" ]; then
        mv "$SKILLS_DST/$name" "$SKILLS_DST/$name.bak-$(date +%Y%m%d-%H%M%S)"; echo "  ↪︎ 已有同名目录，已备份"
      fi
      rm -f "$SKILLS_DST/$name"; ln -s "$d" "$SKILLS_DST/$name"; count=$((count+1))
    done
    echo "  ✅ ${count} 个 skill → ${SKILLS_DST}（常驻 context ≈ 2.4k tokens；~/.codex/skills/.system 为 Codex 官方内置，不动）"
  done
fi

# ---------- 4. newrev ----------
echo; echo "==> newrev → $BIN_DST/newrev"
mkdir -p "$BIN_DST"; ln -sf "$DST/bin/newrev" "$BIN_DST/newrev"; echo "  ✅ newrev"
case ":$PATH:" in *":$BIN_DST:"*) ;; *)
  echo "  ⚠️  $BIN_DST 不在 PATH 里，执行："
  echo "      echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc" ;;
esac

# ---------- 4.5 全局逆向准则（何老师内部版） ----------
echo; echo "==> 全局逆向准则（~/.claude/CLAUDE.md @include + ~/.codex/AGENTS.md 内联）"
RR="$DST/rules"
[ -d "$RR" ] || RR="$SRC/rules"
if [ -d "$RR" ] && [ -f "$RR/reverse_principles.md" ]; then
  cp "$RR/reverse_principles.md" "$RR/reverse_signature_principles.md" "$HOME/.claude/"
  CL="$HOME/.claude/CLAUDE.md"
  if ! grep -q "@reverse_principles.md" "$CL" 2>/dev/null; then
    [ -f "$CL" ] || printf '# Claude Code 全局指令\n' > "$CL"
    printf '\n## 逆向准则（何老师内部版，全局生效）\n\n@reverse_principles.md\n\n@reverse_signature_principles.md\n\n<!-- cloak_kernel_sync.md：老师明确不要配置（其 Windows 内核同步规则，不适用本机）；仅归档于 _meta/20260920/参考/ -->\n' >> "$CL"
    echo "  ✅ ~/.claude/CLAUDE.md 已挂载 @include"
  else echo "  ✔︎ 已有"; fi
  AG="$HOME/.codex/AGENTS.md"
  if ! grep -q "逆向准则（何老师内部版" "$AG" 2>/dev/null; then
    [ -f "$AG" ] || printf '# 全局指令\n' > "$AG"
    { echo; echo "## 逆向准则（何老师内部版；真源 claude-setup/rules/，更新后重新同步本文件）"; echo; cat "$RR/reverse_principles.md"; echo; cat "$RR/reverse_signature_principles.md"; } >> "$AG"
    echo "  ✅ ~/.codex/AGENTS.md 已内联"
  else echo "  ✔︎ 已有"; fi
else echo "  ⚠️ 无 rules 目录，跳过"; fi

# ---------- 5. WireMCP（Wireshark 抓包，没上 npm）----------
echo; echo "==> WireMCP"
WIRE_DIR="$VENDOR/WireMCP"
if [ -z "$TSHARK" ]; then echo "  ⚠️  没有 tshark，跳过"
else
  if [ -f "$WIRE_DIR/index.js" ]; then echo "  ✔︎ 已有"
  else git clone --depth 1 -q https://github.com/0xKoda/WireMCP.git "$WIRE_DIR" && rm -rf "$WIRE_DIR/.git" && echo "  ✅ 已下载" || echo "  ❌ 下载失败"; fi
  [ -f "$WIRE_DIR/index.js" ] && [ ! -d "$WIRE_DIR/node_modules" ] && (cd "$WIRE_DIR" && npm install --omit=dev --silent >/dev/null 2>&1) && echo "  ✅ 依赖已装"
  id -Gn | tr ' ' '\n' | grep -qx access_bpf || echo "  ⚠️  当前用户不在 access_bpf 组，抓不了包：sudo dseditgroup -o edit -a \"$USER\" -t user access_bpf（然后注销重登）"
fi

# ---------- 6. CloakBrowser 二进制（js-reverse-cloak 用）----------
echo; echo "==> CloakBrowser 二进制（约 150MB）"
if [ "$SKIP_DOWNLOADS" -eq 1 ]; then echo "  ↪︎ --skip-downloads，跳过。以后：NODE_USE_ENV_PROXY=1 npx -y cloakbrowser install"
else
  npx -y cloakbrowser install >/dev/null 2>&1 &
  CB_PID=$!; CB_I=0
  while kill -0 "$CB_PID" 2>/dev/null && [ "$CB_I" -lt 60 ]; do sleep 10; CB_I=$((CB_I+1)); done
  if kill -0 "$CB_PID" 2>/dev/null; then
    kill "$CB_PID" 2>/dev/null; echo "  ⚠️  下载超时（10 分钟）终止。以后手动：NODE_USE_ENV_PROXY=1 npx -y cloakbrowser install"
  elif wait "$CB_PID"; then echo "  ✅ 已就绪"
  else echo "  ⚠️  下载失败。以后手动：NODE_USE_ENV_PROXY=1 npx -y cloakbrowser install"; fi
fi

# ---------- 7. wabt（wasm 反汇编，IDA 的免费替代）----------
echo; echo "==> wabt（wasm2wat / wasm-decompile）"
if command -v wasm2wat >/dev/null 2>&1; then echo "  ✔︎ 已有 $(wasm2wat --version 2>/dev/null)"
else npm i -g wabt --silent >/dev/null 2>&1 && echo "  ✅ wabt $(wasm2wat --version 2>/dev/null)" || echo "  ❌ npm i -g wabt 失败"; fi

if [ "$CORE_ONLY" -eq 1 ]; then
  echo; echo "==> --core-only：跳过 Reqable / jadx / frida / wedecode"
else
# ---------- 8. Reqable（免费版抓包客户端 + MCP）----------
echo; echo "==> Reqable"
if [ -d /Applications/Reqable.app ]; then echo "  ✔︎ /Applications/Reqable.app 已有"
elif [ "$SKIP_DOWNLOADS" -eq 1 ]; then echo "  ↪︎ --skip-downloads，跳过。手动下：https://github.com/reqable/reqable-app/releases"
else
  URL=$(gh_latest_asset reqable/reqable-app "macos-$( [ "$ARCH" = arm64 ] && echo arm64 || echo x86_64 ).dmg" || true)
  if [ -n "$URL" ] && dl "$URL" "$VENDOR/reqable.dmg"; then
    MNT=$( (hdiutil attach -nobrowse "$VENDOR/reqable.dmg" 2>/dev/null | grep -o '/Volumes/.*' | tail -1) || true)
    if [ -n "$MNT" ] && [ -d "$MNT/Reqable.app" ]; then
      if cp -R "$MNT/Reqable.app" /Applications/ 2>/dev/null; then
        xattr -dr com.apple.quarantine /Applications/Reqable.app 2>/dev/null; hdiutil detach "$MNT" -quiet
        echo "  ✅ 已装到 /Applications/Reqable.app"; rm -f "$VENDOR/reqable.dmg"
      else
        hdiutil detach "$MNT" -quiet 2>/dev/null; echo "  ❌ 复制到 /Applications 失败（磁盘满/无权限），dmg 保留在 $VENDOR/reqable.dmg"
      fi
    else echo "  ❌ dmg 挂载失败"; fi
  else echo "  ❌ 下载失败"; fi
fi

# ---------- 9. jadx + JDK + jadx-ai-mcp 插件 + python server ----------
echo; echo "==> jadx（安卓 APK 反编译）"
JDK_HOME="$VENDOR/jdk-21/Contents/Home"
if [ "$SKIP_DOWNLOADS" -eq 1 ] && [ ! -x "$JDK_HOME/bin/java" ]; then echo "  ↪︎ --skip-downloads，跳过 JDK/jadx"
else
  if [ -x "$JDK_HOME/bin/java" ]; then echo "  ✔︎ JDK 已有：$("$JDK_HOME/bin/java" -version 2>&1 | head -1)"
  else
    JARCH=$( [ "$ARCH" = arm64 ] && echo aarch64 || echo x64 )
    dl "https://api.adoptium.net/v3/binary/latest/21/ga/mac/$JARCH/jdk/hotspot/normal/eclipse" "$VENDOR/jdk21.tar.gz" \
      && mkdir -p "$VENDOR/jdk-21" && tar xzf "$VENDOR/jdk21.tar.gz" -C "$VENDOR/jdk-21" --strip-components=1 && rm -f "$VENDOR/jdk21.tar.gz" \
      && echo "  ✅ JDK $("$JDK_HOME/bin/java" -version 2>&1 | head -1)" || echo "  ❌ JDK 下载失败"
  fi
  if [ -x "$JDK_HOME/bin/java" ]; then
    if [ -x "$VENDOR/jadx/bin/jadx" ]; then echo "  ✔︎ jadx 已有"
    else
      URL=$( (curl -sL --max-time 30 https://api.github.com/repos/skylot/jadx/releases/latest | python3 -c "import sys,json,re; a=[x['browser_download_url'] for x in json.load(sys.stdin)['assets'] if re.fullmatch(r'jadx-[\d.]+\.zip', x['name'])]; print(a[0] if a else '')") || true)
      dl "$URL" "$VENDOR/jadx.zip" && rm -rf "$VENDOR/jadx" && mkdir "$VENDOR/jadx" && unzip -q "$VENDOR/jadx.zip" -d "$VENDOR/jadx" && rm -f "$VENDOR/jadx.zip" && echo "  ✅ jadx" || echo "  ❌ jadx 下载失败"
    fi
    # 启动包装：带上自带 JDK
    for b in jadx jadx-gui; do
      printf '#!/usr/bin/env bash\nexport JAVA_HOME="%s"\nexec "%s/jadx/bin/%s" "$@"\n' "$JDK_HOME" "$VENDOR" "$b" > "$BIN_DST/$b"; chmod +x "$BIN_DST/$b"
    done
    # jadx-ai-mcp 插件 + python server
    if [ -x "$VENDOR/jadx/bin/jadx" ]; then
      if JAVA_HOME="$JDK_HOME" "$VENDOR/jadx/bin/jadx" plugins --list 2>/dev/null | grep -q jadx-ai-mcp; then echo "  ✔︎ jadx-ai-mcp 插件已有"
      else
        URL=$(gh_latest_asset zinja-coder/jadx-ai-mcp ".jar" || true)
        dl "$URL" "$VENDOR/jadx-ai-mcp.jar" && JAVA_HOME="$JDK_HOME" "$VENDOR/jadx/bin/jadx" plugins --install-jar "$VENDOR/jadx-ai-mcp.jar" >/dev/null 2>&1 && echo "  ✅ jadx-ai-mcp 插件" || echo "  ❌ 插件安装失败"
      fi
      if [ -f "$VENDOR/jadx-mcp-server/jadx_mcp_server.py" ]; then echo "  ✔︎ jadx-mcp-server 已有"
      else
        URL=$(gh_latest_asset zinja-coder/jadx-ai-mcp "jadx-mcp-server" || true)
        dl "$URL" "$VENDOR/jadx-mcp-server.zip" && rm -rf "$VENDOR/_jmcp" && mkdir "$VENDOR/_jmcp" && unzip -q "$VENDOR/jadx-mcp-server.zip" -d "$VENDOR/_jmcp" \
          && D=$(find "$VENDOR/_jmcp" -name jadx_mcp_server.py -exec dirname {} \; | head -1) && rm -rf "$VENDOR/jadx-mcp-server" && mv "$D" "$VENDOR/jadx-mcp-server" && rm -rf "$VENDOR/_jmcp" "$VENDOR/jadx-mcp-server.zip" \
          && echo "  ✅ jadx-mcp-server" || echo "  ❌ jadx-mcp-server 下载失败"
      fi
    fi
  fi
fi

# ---------- 10. frida ----------
echo; echo "==> frida（手机动态插桩）"
# frida-mcp 还在用 mcp 1.x 的 FastMCP API，必须钉 mcp<2，否则起不来
if [ -x "$BIN_DST/frida-mcp" ] && "$BIN_DST/frida-mcp" --help >/dev/null 2>&1; then echo "  ✔︎ frida-mcp 已有"
else uv tool install --python 3.12 --force --with 'mcp<2' frida-mcp >/dev/null 2>&1 && echo "  ✅ frida-mcp" || echo "  ❌ frida-mcp 装失败"; fi
command -v frida >/dev/null 2>&1 && echo "  ✔︎ frida-tools $(frida --version 2>/dev/null)" \
  || { uv tool install --python 3.12 frida-tools >/dev/null 2>&1 && echo "  ✅ frida-tools $(frida --version 2>/dev/null)" || echo "  ❌ frida-tools 装失败"; }

# ---------- 11. wedecode（微信小程序反编译）----------
echo; echo "==> wedecode"
WD="$VENDOR/wedecode"
if [ -f "$WD/dist/mcp/wedecode-mcp.js" ]; then echo "  ✔︎ 已有"
else
  T=$(mktemp -d) && git clone --depth 1 -q https://github.com/d-rn/MCP-WEDECODEMCP.git "$T/w" \
    && (cd "$T/w" && npm install --silent --no-audit --no-fund >/dev/null 2>&1 && npm run build >/dev/null 2>&1) \
    && rm -rf "$WD" && mkdir -p "$WD" && cp -R "$T/w/dist" "$T/w/package.json" "$T/w/node_modules" "$WD/" && rm -rf "$T" \
    && echo "  ✅ 已构建到 $WD" || echo "  ❌ 构建失败"
fi
fi  # CORE_ONLY

# ---------- 12. 注册 MCP（全局 user scope，幂等）----------
echo; echo "==> 注册 MCP（全局 ~/.claude.json）"
if ! command -v claude >/dev/null 2>&1; then echo "  ❌ 没有 claude 命令，跳过。装好后重跑本脚本。"
else
  has_mcp() { claude mcp get "$1" >/dev/null 2>&1; }
  add_mcp() {   # add_mcp <name> <说明> -- <command...>
    local name="$1" desc="$2"; shift 2
    if has_mcp "$name"; then echo "  ✔︎ ${name} 已有（${desc}）"
    else claude mcp add --scope user "$name" "$@" >/dev/null 2>&1 && echo "  ✅ ${name}（${desc}）" || echo "  ❌ ${name} 添加失败：claude mcp add --scope user $name $*"; fi
  }
  UV="$(command -v uv || true)"
  add_mcp js-reverse             "路线1 默认浏览器调试"          -- npx -y js-reverse-mcp
  add_mcp js-reverse-cloak       "路线2 CloakBrowser 隐身内核"    -- npx -y js-reverse-mcp --cloak
  add_mcp roxybrowser-playwright "路线3 接管 Roxy 窗做页面操作"    -- npx -y @roxybrowser/playwright-mcp@latest
  add_mcp chrome-devtools        "接管 9222 端口 Chrome"          -- npx -y chrome-devtools-mcp@latest --browserUrl http://127.0.0.1:9222
  if [ -f "$WIRE_DIR/index.js" ] && [ -d "$WIRE_DIR/node_modules" ]; then add_mcp wiremcp "Wireshark 系统级抓包" -- node "$WIRE_DIR/index.js"
  else echo "  ⚠️  wiremcp 未就绪（WireMCP 没装好），本次不注册；装好后重跑"; fi
  if [ "$CORE_ONLY" -eq 0 ]; then
    # Reqable 3.2+ 自带官方 MCP server（stdio，Dart 写的），装在 .app 里；不用社区的 reqable-mcp，也不用配 Report Server
    RQ_MCP=/Applications/Reqable.app/Contents/Helpers/mcp-server
    if [ -x "$RQ_MCP" ]; then add_mcp reqable "Reqable 官方 MCP（抓包/改包/断点/脚本）" -- "$RQ_MCP" --scope all
    else add_mcp reqable "Reqable 官方 MCP（npx 版，App 没装时的兜底）" -- npx -y reqable-mcp-server --scope all; fi
    if [ -f "$VENDOR/jadx-mcp-server/jadx_mcp_server.py" ]; then add_mcp jadx "安卓 APK 反编译（需先开 jadx-gui）" -- "$UV" --directory "$VENDOR/jadx-mcp-server" run --python 3.12 jadx_mcp_server.py
    else echo "  ⚠️  jadx MCP 未就绪（jadx-mcp-server 没构建好），本次不注册"; fi
    if [ -x "$BIN_DST/frida-mcp" ]; then add_mcp frida-agent "手机动态插桩" -- "$BIN_DST/frida-mcp"
    else echo "  ⚠️  frida-agent MCP 未就绪（frida-mcp 没构建好），本次不注册"; fi
    if [ -f "$WD/dist/mcp/wedecode-mcp.js" ]; then add_mcp wedecode "微信小程序反编译" -- node "$WD/dist/mcp/wedecode-mcp.js"
    else echo "  ⚠️  wedecode MCP 未就绪（没构建好），本次不注册"; fi
  fi
  if has_mcp roxybrowser; then echo "  ✔︎ roxybrowser 已有（路线3 profile/代理/账号管理）"
  elif [ -n "${ROXY_API_KEY:-}" ]; then
    claude mcp add --scope user roxybrowser -e "ROXY_API_KEY=$ROXY_API_KEY" -e "ROXY_API_HOST=${ROXY_API_HOST:-http://127.0.0.1:50007}" -e "ROXY_TIMEOUT=30000" -- npx -y @roxybrowser/openapi >/dev/null 2>&1 \
      && echo "  ✅ roxybrowser" || echo "  ❌ roxybrowser 添加失败"
  else
    echo "  ⚠️  roxybrowser 没装：需要 API Key。RoxyBrowser 客户端 → API → 启用 → 复制 Key，然后："
    echo "      ROXY_API_KEY=你的Key bash $SRC/install.sh   （端口不是 50007 就再加 ROXY_API_HOST=http://127.0.0.1:端口）"
  fi
fi

if [ "$missing" -eq 1 ]; then
  cat <<'PART'

==> ⚠️ 有依赖缺失（见上方 ❌ 行）。补齐后【重跑本脚本】即自动续装（幂等）：
    · node 20.19+   → https://nodejs.org
    · Claude Code   → npm i -g @anthropic-ai/claude-code
    · git/Xcode CLT → xcode-select --install
PART
else
cat <<'DONE'

==> 装好了。本目录现在可以搬走或删掉。

  用法：在任何目录开 Claude Code，直接说「帮我逆向 xxx」。
  想要整齐的项目结构：newrev 项目名 https://目标网址

  用之前要开着的软件：
    · reqable MCP：Reqable 要在运行（菜单栏有 R 图标即可）。首次用 Reqable 会引导装根证书（点两下，要输一次系统密码）
    · jadx MCP：先开着 jadx-gui（终端敲 jadx-gui）并加载一个 apk

  健康检查：claude mcp list
  重跑本脚本 = 更新。
DONE
fi
