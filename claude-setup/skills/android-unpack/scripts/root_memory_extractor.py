#!/usr/bin/env python3
"""Extract structurally valid in-memory DEX files from one rooted Android device."""

import os
import sys
import re
import struct
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))
from i18n_logger import get_logger
from adb_locator import resolve_adb

class RootMemoryExtractor:
    """Root Memory Extractor - Static memory analysis solution that completely bypasses application-layer detection"""

    def __init__(self, verbose: bool = True, language: str = 'en-US', serial: Optional[str] = None):
        """Initialize RootMemoryExtractor

        Args:
            verbose: Enable verbose logging
            language: Language code (en-US, zh-CN)
        """
        self.logger = get_logger(language=language, verbose=verbose, module="root_memory_extractor")
        self.verbose = verbose
        self.package_name = ""
        self.pid = None
        self.process_start_identity = None
        self.output_dir = None
        self.dex_regions = []  # Found DEX memory regions
        self.extracted_dex_files = []
        self.serial = serial or os.environ.get("ANDROID_SERIAL")
        if not self.serial or not re.fullmatch(r"[A-Za-z0-9._:-]+", self.serial):
            raise ValueError("a valid --serial or ANDROID_SERIAL is required")
        self.adb_path = resolve_adb(Path(__file__).resolve().parents[4])
        if not self.adb_path.is_file():
            raise FileNotFoundError(f"ADB not found (set ANDROID_MCP_ADB or put adb on PATH): {self.adb_path}")

    def _adb_cmd(self, *args: str) -> List[str]:
        return [str(self.adb_path), "-s", self.serial, *args]

    def log(self, key: str, level: str = "INFO", **kwargs):
        """Log a message using internationalized logger"""
        self.logger.log(key, level, **kwargs)

    def check_root(self) -> bool:
        """检查设备是否有root权限"""
        self.log("checking_root_permission")

        try:
            # 使用su命令测试root权限
            result = subprocess.run(
                self._adb_cmd("shell", "su -c 'echo root_ok'"),
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and "root_ok" in result.stdout:
                self.log("device_has_root", "SUCCESS")
                return True
            else:
                self.log("no_root_permission", "ERROR",
                       stdout=result.stdout[:100], stderr=result.stderr[:100])
                return False

        except Exception as e:
            self.log("check_root_failed", "ERROR", error=str(e))
            return False

    def get_package_pid(self, package_name: str) -> Optional[int]:
        """获取进程PID(增强版:pidof失败时使用ps回退)"""
        self.log("getting_process_pid", package=package_name)

        try:
            # 策略1:使用pidof获取PID(最快)
            result = subprocess.run(
                self._adb_cmd("shell", f"pidof {package_name}"),
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                pid_str = result.stdout.strip()
                # pidof可能返回多个PID，取第一个
                if ' ' in pid_str:
                    pid_str = pid_str.split()[0]
                try:
                    pid = int(pid_str)
                    self.log("pid_found", "SUCCESS", pid=pid)
                    return pid
                except ValueError:
                    self.log("pidof_invalid_output", "WARNING", output=pid_str)
                    # 继续尝试其他策略

            # 策略2:pidof失败,使用ps -A | grep(兼容多进程/进程名隐藏)
            self.log("pidof_failed_trying_ps", "WARN")
            ps_result = subprocess.run(
                self._adb_cmd("shell", f"ps -A | grep {package_name}"),
                capture_output=True,
                text=True,
                timeout=10
            )

            if ps_result.returncode == 0 and ps_result.stdout.strip():
                # 解析ps输出,格式如:USER PID PPID VSZ RSS WCHAN ADDR S NAME
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

            # 策略3:使用ps -A | grep -v grep(更精确)
            ps_result2 = subprocess.run(
                self._adb_cmd("shell", f"ps -A | grep -v grep | grep {package_name}"),
                capture_output=True,
                text=True,
                timeout=10
            )

            if ps_result2.returncode == 0 and ps_result2.stdout.strip():
                lines = ps_result2.stdout.strip().split('\n')
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 9:
                        try:
                            pid = int(parts[1])
                            self.log("pid_found_via_ps_grep", "SUCCESS", pid=pid)
                            return pid
                        except (ValueError, IndexError):
                            continue

            self.log("process_not_found", "ERROR")
            return None

        except Exception as e:
            self.log("pid_lookup_failed", "ERROR", error=str(e))
            return None

    def get_process_start_identity(self, pid: int) -> Optional[str]:
        """Return PID plus Linux /proc starttime so a reused PID is rejected."""
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
            if close < 0:
                return None
            fields_after_comm = stat[close + 2:].split()
            if len(fields_after_comm) <= 19:
                return None
            return f"{pid}:{fields_after_comm[19]}"
        except Exception:
            return None

    def read_process_maps(self, pid: int) -> List[Dict]:
        """读取进程的内存映射信息"""
        self.log("reading_process_maps", pid=pid)

        try:
            # 通过root权限读取/proc/pid/maps
            cmd = self._adb_cmd("shell", f"su -c 'cat /proc/{pid}/maps'")
            result = subprocess.run(cmd, capture_output=True, timeout=15)  # text=False for binary output

            if result.returncode != 0:
                self.log("read_maps_failed", "ERROR", stderr=result.stderr[:200] if result.stderr else '')
                return []

            memory_regions = []
            # 解码二进制输出，忽略编码错误
            stdout_text = result.stdout.decode('utf-8', errors='ignore')
            lines = stdout_text.strip().split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 解析maps行格式: start-end perms offset dev inode pathname
                parts = line.split()
                if len(parts) < 5:
                    continue

                # 解析地址范围
                addr_range = parts[0]
                perms = parts[1]

                if '-' in addr_range:
                    start_str, end_str = addr_range.split('-')
                    try:
                        start = int(start_str, 16)
                        end = int(end_str, 16)
                        size = end - start

                        # 只关注可读区域
                        if 'r' in perms and size > 0:
                            region_info = {
                                'start': start,
                                'end': end,
                                'size': size,
                                'perms': perms,
                                'offset': parts[2] if len(parts) > 2 else '',
                                'device': parts[3] if len(parts) > 3 else '',
                                'inode': parts[4] if len(parts) > 4 else '',
                                'pathname': ' '.join(parts[5:]) if len(parts) > 5 else '',
                                'line': line
                            }

                            # 特别标记可能的DEX区域
                            if 'anon:dalvik' in region_info['pathname'] or 'dalvik' in region_info['pathname']:
                                region_info['likely_dex'] = True
                                self.log("potential_dex_region", "INFO",
                                       start=f"0x{start:x}", size=size)

                            memory_regions.append(region_info)
                    except ValueError:
                        continue

            self.log("memory_regions_found", count=len(memory_regions))
            return memory_regions

        except Exception as e:
            self.log("read_maps_exception", "ERROR", error=str(e))
            return []

    def extract_memory_region(
        self, pid: int, start: int, size: int, expected_start_identity: Optional[str] = None
    ) -> Optional[bytes]:
        """提取指定内存区域的数据"""
        self.log("extracting_memory_region", pid=pid, start=f"0x{start:x}", size=size)

        try:
            if expected_start_identity:
                current_identity = self.get_process_start_identity(pid)
                if current_identity != expected_start_identity:
                    self.log(
                        "process_identity_changed",
                        "ERROR",
                        expected=expected_start_identity,
                        current=current_identity,
                    )
                    return None
            # 使用dd命令通过root权限读取内存
            # 注意:需要将地址转换为十进制
            start_dec = start
            count = size

            # 构建dd命令
            dd_cmd = f"dd if=/proc/{pid}/mem bs=4096 skip={start_dec//4096} count={count//4096 + 1} 2>/dev/null"
            cmd = self._adb_cmd("shell", f"su -c '{dd_cmd}'")

            self.log("executing_dd_command", command=" ".join(cmd))

            result = subprocess.run(cmd, capture_output=True, timeout=30)

            if result.returncode == 0:
                data = result.stdout
                actual_size = len(data)

                # 裁剪到实际需要的尺寸
                if actual_size > size:
                    data = data[:size]

                self.log("memory_extraction_success", "SUCCESS",
                       expected_size=size, actual_size=len(data))
                return data
            else:
                self.log("memory_extraction_failed", "ERROR",
                       returncode=result.returncode, stderr=result.stderr[:200])
                return None

        except Exception as e:
            self.log("memory_extraction_exception", "ERROR", error=str(e))
            return None

    def search_dex_in_memory(self, data: bytes, region_info: Dict) -> List[Dict]:
        """Return only candidates with a complete, internally consistent DEX header."""
        self.log("searching_dex_in_memory", data_size=len(data))

        dex_files = []
        search_limit = min(len(data), 100 * 1024 * 1024)  # 最多搜索前100MB
        offset = data.find(b"dex\n", 0, search_limit)
        while offset >= 0:
            self.log("standard_dex_signature_found", offset=offset)
            dex_info = self._parse_dex_header(data, offset, region_info)
            if dex_info:
                dex_files.append(dex_info)
            offset = data.find(b"dex\n", offset + 1, search_limit)

        self.log("dex_search_complete", found=len(dex_files))
        return dex_files

    def _parse_dex_header(self, data: bytes, offset: int, region_info: Dict) -> Optional[Dict]:
        """解析DEX头部信息"""
        if offset < 0 or offset + 0x70 > len(data):
            return None
        header_data = data[offset:offset + 0x70]
        try:
            file_size = struct.unpack("<I", header_data[0x20:0x24])[0]
            magic_ok = re.fullmatch(rb"dex\n[0-9]{3}\x00", header_data[:8]) is not None
            size_ok = 0x70 <= file_size <= min(100 * 1024 * 1024, len(data) - offset)
            header_ok = struct.unpack("<I", header_data[0x24:0x28])[0] == 0x70
            endian_ok = struct.unpack("<I", header_data[0x28:0x2C])[0] in {0x12345678, 0x78563412}
            if magic_ok and size_ok and header_ok and endian_ok:
                dex_info = {
                    "offset": offset,
                    "file_size": file_size,
                    "start_addr": region_info["start"] + offset,
                    "header_checksum": header_data[8:12].hex(),
                    "signature": header_data[12:32].hex()[:16] + "...",
                    "region_info": region_info,
                    "encrypted": False,
                    "confidence": 1.0,
                }
                self.log("valid_dex_found", "INFO", offset=offset, file_size=file_size)
                return dex_info
        except (KeyError, struct.error, ValueError) as exc:
            self.log("dex_header_parse_error", "WARNING", error=str(exc))
        return None

    def extract_dex_file(self, data: bytes, dex_info: Dict, output_dir: Path) -> Optional[str]:
        """提取并保存DEX文件"""
        try:
            offset = dex_info['offset']
            file_size = dex_info['file_size']

            # 检查是否有足够的数据
            if offset + file_size > len(data):
                self.log("insufficient_data_for_dex", "WARNING",
                       offset=offset, file_size=file_size, available=len(data)-offset)
                return None

            # 提取DEX数据
            dex_data = data[offset:offset+file_size]

            reparsed = self._parse_dex_header(data, offset, dex_info.get("region_info", {"start": 0}))
            if not reparsed or reparsed["file_size"] != file_size or len(dex_data) != file_size:
                self.log("invalid_dex_structure", "ERROR")
                return None
            dex_hash = hashlib.sha256(dex_data).hexdigest()[:12]
            filename = f"dex_{dex_info['start_addr']:08x}_{dex_hash}.dex"
            
            filepath = output_dir / filename

            # 保存文件
            with open(filepath, 'wb') as f:
                f.write(dex_data)

            self.log("dex_file_saved", "SUCCESS",
                   filename=filename, size=len(dex_data), path=str(filepath), encrypted=False)

            return str(filepath)

        except Exception as e:
            self.log("dex_extraction_failed", "ERROR", error=str(e))
            return None

    def extract(self, package_name: str, output_dir: str = None) -> bool:
        """主提取函数"""
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+", package_name):
            self.log("invalid_package_name", "ERROR", package=package_name)
            return False
        self.log("starting_root_extraction", package=package_name)
        self.package_name = package_name

        # 1. 检查root权限
        if not self.check_root():
            self.log("root_required", "ERROR")
            return False

        # 2. Require an already running process. The operator controls the
        # execution point; this extractor must not force-stop/start apps.
        pid = self.get_package_pid(package_name)
        if not pid:
            self.log("process_not_running", "ERROR", package=package_name)
            return False

        self.pid = pid
        self.process_start_identity = self.get_process_start_identity(pid)
        if not self.process_start_identity:
            self.log("process_identity_unavailable", "ERROR", pid=pid)
            return False

        # 3. 准备输出目录
        if not output_dir:
            self.log("output_directory_required", "ERROR")
            return False
        output_dir = Path(output_dir)

        if output_dir.exists() and any(output_dir.iterdir()):
            self.log("output_directory_not_empty", "ERROR", path=str(output_dir))
            return False
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir

        self.log("output_directory_ready", "INFO", path=str(output_dir))

        # 4. 读取内存映射
        memory_regions = self.read_process_maps(pid)
        if not memory_regions:
            self.log("no_memory_regions_found", "ERROR")
            return False

        # 5. 提取和分析内存区域
        all_extracted_dex = []
        total_regions = len(memory_regions)

        for i, region in enumerate(memory_regions[:50]):  # 最多处理50个区域
            self.log("processing_region", region_num=i+1, total=total_regions,
                   start=f"0x{region['start']:x}", size=region['size'])

            # 跳过太大的区域(>500MB)
            if region['size'] > 500 * 1024 * 1024:
                self.log("region_too_large", "WARNING", size=region['size'])
                continue

            # 提取内存数据
            data = self.extract_memory_region(
                pid,
                region['start'],
                region['size'],
                expected_start_identity=self.process_start_identity,
            )
            if not data:
                continue

            # 在数据中搜索DEX文件
            dex_files = self.search_dex_in_memory(data, region)

            # 提取找到的DEX文件
            for dex_info in dex_files:
                dex_path = self.extract_dex_file(data, dex_info, output_dir)
                if dex_path:
                    dex_info['saved_path'] = dex_path
                    dex_info['region_index'] = i
                    all_extracted_dex.append(dex_info)

        # 6. 生成报告
        report = {
            "package_name": package_name,
            "pid": pid,
            "process_start_identity": self.process_start_identity,
            "timestamp": datetime.now().isoformat(),
            "memory_regions_analyzed": len(memory_regions),
            "dex_files_found": len(all_extracted_dex),
            "output_directory": str(output_dir),
            "extracted_dex_files": all_extracted_dex
        }

        report_path = output_dir / "extraction_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.log("extraction_report_saved", "INFO", path=str(report_path))

        # 7. 结果总结
        if all_extracted_dex:
            self.log("root_extraction_success", "SUCCESS",
                   dex_count=len(all_extracted_dex), output_dir=str(output_dir))

            # 列出提取的DEX文件
            for i, dex in enumerate(all_extracted_dex[:5]):
                self.log("extracted_dex_summary", "INFO",
                       index=i+1,
                       addr=f"0x{dex['start_addr']:x}",
                       size=dex['file_size'],
                       path=dex.get('saved_path', 'unknown'))

            if len(all_extracted_dex) > 5:
                self.log("more_dex_files_extracted", "INFO", extra_count=len(all_extracted_dex)-5)

            return True
        else:
            self.log("no_dex_files_extracted", "ERROR")
            return False

def main():
    """Main function for command line usage"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Root Memory Extractor - Extract DEX files from process memory via root permissions'
    )

    parser.add_argument('--package', '-p', required=True, help='Target application package name')
    parser.add_argument('--serial', required=True, help='Unique Android device serial')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--language', '-l', default='en-US', choices=['en-US', 'zh-CN'],
                       help='Language for output (en-US, zh-CN)')
    parser.add_argument('--output', '-o', required=True, help='Fresh output directory for extracted DEX files')

    args = parser.parse_args()

    extractor = RootMemoryExtractor(verbose=args.verbose, language=args.language, serial=args.serial)

    # 执行提取
    success = extractor.extract(args.package, args.output)

    # 退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
