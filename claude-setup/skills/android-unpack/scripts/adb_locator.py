"""Cross-platform adb resolution shared by the unpack scripts.

Order (mirrors android_mcp/common/adb.py so scripts and MCP pick the same binary):
1. ANDROID_MCP_ADB environment variable
2. Bundled teacher path android_mcp/toolchain/bin/windows/platform-tools/adb(.exe)
3. adb on PATH (macOS/Linux: install.sh links Google platform-tools to ~/.local/bin/adb)

If nothing is found the bundled path is returned unchanged so callers' existing
is_file() checks still fail loudly instead of silently picking a wrong device tool.
"""
import os
import shutil
from pathlib import Path


def bundled_adb_path(repo_root: Path) -> Path:
    exe = "adb.exe" if os.name == "nt" else "adb"
    return repo_root / "android_mcp" / "toolchain" / "bin" / "windows" / "platform-tools" / exe


def resolve_adb(repo_root: Path) -> Path:
    configured = os.environ.get("ANDROID_MCP_ADB")
    if configured:
        return Path(configured).expanduser()
    bundled = bundled_adb_path(repo_root)
    if bundled.is_file():
        return bundled
    found = shutil.which("adb")
    if found:
        return Path(found)
    return bundled
