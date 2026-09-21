#!/usr/bin/env python3
"""
Enhanced DexDump Runner - Actual Frida-based DEX unpacking implementation
修复版本：实际执行frida-dexdump脱壳
"""

import os
import sys
import subprocess
import time
import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))
from i18n_logger import get_logger

class EnhancedDexDumpRunner:
    """Enhanced DexDump Runner - Actual implementation"""
    
    def __init__(self, verbose: bool = False, max_attempts: int = 3, deep_search: bool = False, 
                 bypass_antidebug: bool = False, language: str = 'en-US', serial: Optional[str] = None):
        """Initialize EnhancedDexDumpRunner
        
        Args:
            verbose: Enable verbose logging
            max_attempts: Maximum number of attempts
            deep_search: Enable deep search mode
            bypass_antidebug: Enable anti-debug bypass
            language: Language code (en-US, zh-CN)
        """
        self.logger = get_logger(language=language, verbose=verbose, module="enhanced_dexdump_runner")
        self.verbose = verbose
        if not 1 <= max_attempts <= 3:
            raise ValueError("max_attempts must be between 1 and 3")
        self.max_attempts = max_attempts
        self.deep_search = deep_search
        self.bypass_antidebug = bypass_antidebug
        self.output_dir = None
        self.extracted_dex_files = []
        self.language = language
        self.serial = serial or os.environ.get("ANDROID_SERIAL")
        if not self.serial or not re.fullmatch(r"[A-Za-z0-9._:-]+", self.serial):
            raise ValueError("a valid --serial or ANDROID_SERIAL is required")
        repo_root = Path(__file__).resolve().parents[4]
        self.adb_path = repo_root / "android_mcp" / "toolchain" / "bin" / "windows" / "platform-tools" / "adb.exe"
        configured_dexdump = os.environ.get("ANDROID_MCP_FRIDA_DEXDUMP")
        self.dexdump_path = Path(configured_dexdump) if configured_dexdump else Path(sys.executable).resolve().parent / "frida-dexdump.exe"

    def _adb_cmd(self, *args: str) -> List[str]:
        return [str(self.adb_path), "-s", self.serial, *args]
        
    def log(self, key: str, level: str = "INFO", **kwargs):
        """Log a message using internationalized logger"""
        self.logger.log(key, level, **kwargs)
    
    def check_environment(self) -> bool:
        """检查运行环境"""
        self.log("checking_environment")
        
        # 检查frida-dexdump
        try:
            if not self.dexdump_path.is_file():
                self.log("frida_dexdump_not_found", "ERROR")
                self.log("install_frida_dexdump", "WARNING")
                return False
            self.log("frida_dexdump_found", path=str(self.dexdump_path))
        except Exception as e:
            self.log("check_frida_dexdump_failed", "ERROR", error=str(e))
            return False
        
        # 检查ADB设备连接
        try:
            if not self.adb_path.is_file():
                self.log("adb_command_failed", "ERROR")
                return False
            result = subprocess.run(self._adb_cmd("get-state"),
                                   capture_output=True, text=True)
            if result.returncode != 0 or result.stdout.strip() != "device":
                self.log("adb_command_failed", "ERROR")
                return False

            self.log("devices_found", count=1)
            return True
            
        except Exception as e:
            self.log("check_adb_failed", "ERROR", error=str(e))
            return False
    
    def get_package_pid(self, package_name: str) -> Optional[int]:
        """获取应用进程PID（修复多PID处理）"""
        self.log("getting_package_pid", package=package_name)
        
        try:
            result = subprocess.run(
                self._adb_cmd("shell", f"pidof {package_name}"),
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pid_str = result.stdout.strip()
                # pidof可能返回多个PID（如"25886 25909"），取第一个
                if ' ' in pid_str:
                    pid_str = pid_str.split()[0]
                
                try:
                    pid = int(pid_str)
                    self.log("pid_found", "SUCCESS", pid=pid, original_output=result.stdout.strip())
                    return pid
                except ValueError:
                    self.log("pidof_invalid_output", "WARNING", output=pid_str)
                    # 尝试使用ps命令回退
                    
            # pidof失败，尝试使用ps命令
            self.log("pidof_failed_trying_ps", "WARNING")
            ps_result = subprocess.run(
                self._adb_cmd("shell", f"ps -A | grep {package_name}"),
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if ps_result.returncode == 0 and ps_result.stdout.strip():
                lines = ps_result.stdout.strip().split('\n')
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 9 and package_name in parts[-1]:
                        try:
                            pid = int(parts[1])
                            self.log("pid_found_via_ps", "SUCCESS", pid=pid)
                            return pid
                        except (ValueError, IndexError):
                            continue
            
            self.log("process_not_found", "ERROR")
            return None
                
        except Exception as e:
            self.log("pid_lookup_failed", "ERROR", error=str(e))
            return None
    
    def ensure_application_running(self, package_name: str) -> Optional[int]:
        """Return an existing PID without changing foreground/application state."""
        pid = self.get_package_pid(package_name)
        if pid:
            return pid
        self.log("application_not_running", "ERROR", package=package_name)
        return None

    def get_process_start_identity(self, pid: int) -> Optional[str]:
        """Return PID plus /proc starttime to reject a reused process id."""
        try:
            result = subprocess.run(
                self._adb_cmd("shell", f"su -c 'cat /proc/{pid}/stat'"),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None
            stat = result.stdout.strip()
            close = stat.rfind(")")
            fields_after_comm = stat[close + 2:].split() if close >= 0 else []
            if len(fields_after_comm) <= 19:
                return None
            return f"{pid}:{fields_after_comm[19]}"
        except Exception:
            return None
    
    def setup_frida_server(self) -> bool:
        """Fail closed unless the caller has already started the validated MCP server."""
        result = subprocess.run(
            self._adb_cmd("shell", "pidof new-server"),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            self.log("frida_server_setup_failed", "ERROR", error="start new-server with frida-orchestrator-mcp first")
            return False
        return True
    
    def execute_frida_dexdump(self, package_name: str, output_dir: str = None) -> bool:
        """执行frida-dexdump进行脱壳（使用历史成功策略）"""
        self.log("executing_frida_dexdump", package=package_name)
        
        # 1. 设置Frida服务器隐藏
        if not self.setup_frida_server():
            self.log("frida_server_setup_failed", "ERROR")
            return False
        
        # 2. 确保应用正在运行
        pid = self.ensure_application_running(package_name)
        if not pid:
            self.log("cannot_start_application", "ERROR")
            return False
        start_identity = self.get_process_start_identity(pid)
        if not start_identity:
            self.log("process_identity_unavailable", "ERROR", pid=pid)
            return False
        
        # 3. 准备输出目录（确保绝对路径）
        if not output_dir:
            self.log("output_directory_required", "ERROR")
            return False
        output_dir = Path(output_dir)
        
        output_dir = output_dir.resolve()  # 转换为绝对路径
        if output_dir.exists() and any(output_dir.iterdir()):
            self.log("output_directory_not_empty", "ERROR", path=str(output_dir))
            return False
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir
        
        # 4. 构建frida-dexdump命令（使用attach模式，历史成功策略）
        cmd = [str(self.dexdump_path), "-D", self.serial, "-p", str(pid), "-o", str(output_dir)]
        
        # 添加深度搜索参数（如果启用）
        if self.deep_search:
            cmd.append("-d")
            self.log("deep_search_enabled", "INFO")
        
        try:
            if self.get_process_start_identity(pid) != start_identity:
                self.log("process_identity_changed", "ERROR", expected=start_identity)
                return False
            self.log("running_frida_dexdump", "INFO", cmd=" ".join(cmd), cwd=str(output_dir))
            
            # 执行frida-dexdump，设置超时为180秒
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180
            )
            
            # 检查执行结果
            # 首先统计提取的DEX文件（无论返回码如何）
            # 使用递归查找，因为frida-dexdump可能在子目录中创建DEX文件
            dex_files = [path for path in output_dir.rglob("*.dex") if self._is_structurally_valid_dex(path)]
            dex_count = len(dex_files)
            
            # 记录查找结果
            if dex_count == 0:
                # 检查是否有子目录
                subdirs = [d for d in output_dir.iterdir() if d.is_dir()]
                self.log("searching_for_dex", "INFO", 
                       output_dir=str(output_dir), subdir_count=len(subdirs))
                for subdir in subdirs[:3]:  # 只记录前3个子目录
                    self.log("found_subdirectory", "DEBUG", path=str(subdir))
            
            if dex_count > 0:
                self.log("frida_dexdump_success_with_dex", "SUCCESS", 
                       count=dex_count, output_dir=str(output_dir), returncode=result.returncode)
                
                # 记录DEX文件信息
                self.extracted_dex_files = []
                for i, dex_file in enumerate(dex_files):
                    size_bytes = dex_file.stat().st_size
                    size_kb = size_bytes / 1024
                    size_mb = size_kb / 1024
                    
                    dex_info = {
                        'index': i + 1,
                        'name': dex_file.name,
                        'path': str(dex_file),
                        'size_bytes': size_bytes,
                        'size_kb': round(size_kb, 1),
                        'size_mb': round(size_mb, 2)
                    }
                    self.extracted_dex_files.append(dex_info)
                    
                    # 只记录前5个文件的详细信息
                    if i < 5:
                        self.log("dex_file_extracted", "INFO", 
                               index=i+1, file=dex_file.name, size=f"{size_kb:.1f}KB")
                
                if dex_count > 5:
                    self.log("more_dex_files", "INFO", extra_count=dex_count-5)
                
                return result.returncode == 0
            else:
                # 没有找到DEX文件，检查返回码
                if result.returncode == 0:
                    self.log("no_dex_files_found", "WARNING",
                           stdout_preview=result.stdout[:200] if result.stdout else '')
                    # 检查是否有其他输出
                    if result.stdout and "Successful found" in result.stdout:
                        self.log("found_dex_in_memory", "INFO", stdout_preview=result.stdout[:200])
                else:
                    self.log("frida_dexdump_failed_no_dex", "ERROR", 
                           returncode=result.returncode, 
                           stdout_preview=result.stdout[:300] if result.stdout else '',
                           stderr_preview=result.stderr[:500] if result.stderr else '')
                return False
                
        except subprocess.TimeoutExpired:
            self.log("frida_dexdump_timeout", "ERROR", timeout=180)
            return False
        except Exception as e:
            self.log("frida_dexdump_exception", "ERROR", error=str(e))
            return False
    @staticmethod
    def _is_structurally_valid_dex(path: Path) -> bool:
        try:
            size = path.stat().st_size
            with path.open("rb") as handle:
                header = handle.read(0x70)
        except OSError:
            return False
        return (
            len(header) >= 0x70
            and re.fullmatch(rb"dex\n[0-9]{3}\x00", header[:8]) is not None
            and int.from_bytes(header[0x20:0x24], "little") == size
            and int.from_bytes(header[0x24:0x28], "little") == 0x70
            and int.from_bytes(header[0x28:0x2C], "little") in {0x12345678, 0x78563412}
        )
    
    def unpack(self, package_name: str, output_dir: str = None) -> bool:
        """主脱壳函数"""
        self.log("starting_unpack_process", package=package_name)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+", package_name):
            self.log("invalid_package_name", "ERROR", package=package_name)
            return False
        if not output_dir:
            self.log("output_directory_required", "ERROR")
            return False
        if self.bypass_antidebug:
            self.log(
                "antidebug_bypass_failed",
                "ERROR",
                error="standalone anti-debug injection is not validated; use android-dynamic via frida-orchestrator-mcp",
            )
            return False
        
        # 1. 检查环境
        if not self.check_environment():
            self.log("environment_check_failed", "ERROR")
            return False
        
        # 2. 执行frida-dexdump脱壳
        success = False
        for attempt in range(1, self.max_attempts + 1):
            self.log("unpack_attempt", "INFO", attempt=attempt, max_attempts=self.max_attempts)
            
            success = self.execute_frida_dexdump(package_name, output_dir)
            if success:
                break
            else:
                if attempt < self.max_attempts:
                    self.log("retry_unpack", "WARNING", next_attempt=attempt+1)
                    time.sleep(2)  # 等待后重试
        
        # 4. 输出结果
        if success:
            self.log("unpack_success", "SUCCESS", 
                   dex_count=len(self.extracted_dex_files),
                   output_dir=str(self.output_dir))
            
            # 生成结果报告
            report = {
                "package_name": package_name,
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "dex_count": len(self.extracted_dex_files),
                "output_dir": str(self.output_dir),
                "extracted_files": self.extracted_dex_files
            }
            
            # 保存报告
            if self.output_dir:
                report_path = self.output_dir / "unpack_report.json"
                with open(report_path, 'w') as f:
                    json.dump(report, f, indent=2)
                self.log("report_saved", "INFO", path=str(report_path))
            
            return True
        else:
            self.log("unpack_failed", "ERROR", 
                   attempts=self.max_attempts, package=package_name)
            return False

def main():
    """命令行入口 - 实际执行脱壳"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Enhanced DexDump Runner - Actual Frida-based DEX unpacking'
    )
    
    parser.add_argument('--package', '-p', required=True, help='Target application package name')
    parser.add_argument('--serial', required=True, help='Unique Android device serial')
    parser.add_argument('--output', '-o', required=True, help='Fresh output directory for extracted DEX files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--language', '-l', default='en-US', choices=['en-US', 'zh-CN'], 
                       help='Language for output (en-US, zh-CN)')
    parser.add_argument('--deep-search', action='store_true', help='Enable deep search mode')
    parser.add_argument('--bypass-antidebug', action='store_true', help='Enable anti-debug bypass')
    parser.add_argument('--max-attempts', type=int, choices=range(1, 4), default=3, help='Maximum unpacking attempts (1-3)')
    
    args = parser.parse_args()
    
    runner = EnhancedDexDumpRunner(
        verbose=args.verbose,
        language=args.language,
        deep_search=args.deep_search,
        bypass_antidebug=args.bypass_antidebug,
        max_attempts=args.max_attempts,
        serial=args.serial,
    )
    
    # 执行脱壳
    success = runner.unpack(args.package, args.output)
    
    # 退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
