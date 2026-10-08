#!/usr/bin/env python3
"""
Unpack Orchestrator - 智能解包策略协调器
根据加固分析结果自动选择最佳解包策略
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 导入i18n_logger（处理相对导入）
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))
try:
    from i18n_logger import get_logger
    from adb_locator import resolve_adb
except ImportError:
    # 如果直接导入失败，尝试使用绝对导入
    from scripts.i18n_logger import get_logger
    from scripts.adb_locator import resolve_adb

class UnpackOrchestrator:
    """解包策略协调器 - 根据加固类型自动选择最佳策略"""
    
    def __init__(self, verbose: bool = True, language: str = 'en-US', serial: Optional[str] = None):
        """Initialize UnpackOrchestrator
        
        Args:
            verbose: Enable verbose logging
            language: Language code (en-US, zh-CN)
        """
        self.logger = get_logger(language=language, verbose=verbose, module="unpack_orchestrator")
        self.verbose = verbose
        self.script_dir = Path(__file__).parent
        # laohe: device commands must stay pinned to one explicit adb (ANDROID_MCP_ADB > bundled > PATH).
        self.adb_path = resolve_adb(self.script_dir.parents[3])
        self.serial = serial or os.environ.get("ANDROID_SERIAL")
        if self.serial and not re.fullmatch(r"[A-Za-z0-9._:-]+", self.serial):
            raise ValueError("serial contains unsupported characters")
        self.strategy_decision_tree = {
            # 加固类型 -> 推荐策略
            "none": "recon",          # 无壳 -> 返回静态分析，不注入
            "unknown": "root",         # 未知 -> 优先零注入 Root 取证
            "ijiami": "root",          # 爱加密 -> Root内存提取
            "bangcle": "root",         # 梆梆 -> Root内存提取
            "360": "root",             # 360加固 -> Root内存提取
            "tencent": "root",         # 腾讯加固 -> Root内存提取
            "baidu": "root",           # 商业壳默认避免进程内注入
            "ali": "root",             # 商业壳默认避免进程内注入
            "naga": "root",           # 娜迦加固 -> Root内存提取
            "dingxiang": "root",      # 顶象加固 -> Root内存提取
            "netease": "root",        # 网易易盾 -> Root内存提取
            "kiwivm": "root",         # 几维安全 -> Root内存提取
        }
        self.last_apk_inventory: List[Dict[str, object]] = []

    def _adb_cmd(self, *args: str) -> List[str]:
        """Build a command for the bundled ADB and one explicitly selected device."""
        if not self.adb_path.is_file():
            raise FileNotFoundError(f"ADB not found (set ANDROID_MCP_ADB or put adb on PATH): {self.adb_path}")
        if not self.serial:
            raise RuntimeError("device operation requires --serial or ANDROID_SERIAL")
        return [str(self.adb_path), "-s", self.serial, *args]

    def extract_apks_from_device(self, package_name: str) -> Optional[List[str]]:
        """Pull base plus every split APK and retain a device/local inventory."""
        self.log("extracting_apk_from_device", package=package_name)
        
        try:
            # 获取APK路径
            cmd = self._adb_cmd("shell", "pm", "path", package_name)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0 or not result.stdout.strip():
                self.log("failed_to_get_apk_path", "ERROR", error=result.stderr)
                return None
            
            # Split APK packages return one package: line per base/split APK.
            device_apk_paths = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                if not line.startswith("package:"):
                    self.log("invalid_apk_path_format", "ERROR", path=line)
                    return None
                remote = line[len("package:"):].strip()
                if not remote.startswith("/") or "\x00" in remote:
                    self.log("invalid_apk_path_format", "ERROR", path=remote)
                    return None
                device_apk_paths.append(remote)
            if not device_apk_paths:
                self.log("invalid_apk_path_format", "ERROR", path=result.stdout.strip())
                return None
            
            # 创建临时目录保存APK
            temp_dir = tempfile.mkdtemp(prefix=f"apk_{package_name}_")
            local_paths = []
            inventory = []
            used_names = set()
            for index, device_apk_path in enumerate(device_apk_paths):
                name = Path(device_apk_path).name or f"split_{index}.apk"
                if name in used_names:
                    name = f"{index}_{name}"
                used_names.add(name)
                local_apk_path = os.path.join(temp_dir, name)
                self.log("pulling_apk_from_device", device_path=device_apk_path, local_path=local_apk_path)
                cmd = self._adb_cmd("pull", device_apk_path, local_apk_path)
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode != 0 or not os.path.isfile(local_apk_path) or os.path.getsize(local_apk_path) == 0:
                    self.log("failed_to_pull_apk", "ERROR", error=result.stderr)
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None
                local_paths.append(local_apk_path)
                inventory.append(
                    {
                        "device_path": device_apk_path,
                        "name": name,
                        "size": os.path.getsize(local_apk_path),
                    }
                )

            self.last_apk_inventory = inventory
            self.log("apk_extraction_success", "SUCCESS", count=len(local_paths))
            return local_paths
            
        except subprocess.TimeoutExpired:
            self.log("apk_extraction_timeout", "ERROR")
            return None
        except Exception as e:
            self.log("apk_extraction_exception", "ERROR", error=str(e))
            return None
    
    def analyze_installed_app(self, package_name: str) -> Optional[Dict]:
        """Analyze base and splits, then return the strongest supported result."""
        self.log("analyzing_installed_app", package=package_name)
        
        # 1. 提取APK
        apk_paths = self.extract_apks_from_device(package_name)
        if not apk_paths:
            self.log("failed_to_extract_apk", "ERROR")
            return None

        # 2. Analyze every split because shell/business code need not live in base.apk.
        analyses = []
        for apk_path in apk_paths:
            result = self.analyze_apk_protection(apk_path)
            if result:
                analyses.append((apk_path, result))

        analysis_result = None
        if analyses:
            _, analysis_result = max(
                analyses,
                key=lambda item: float(item[1].get("confidence_score", 0) or 0),
            )
            analysis_result = dict(analysis_result)
            analysis_result["apk_inventory"] = list(self.last_apk_inventory)
            analysis_result["split_analyses"] = [
                {
                    "name": Path(path).name,
                    "protection_type": result.get("protection_type", "unknown"),
                    "protection_level": result.get("protection_level", "unknown"),
                    "confidence_score": result.get("confidence_score", 0),
                }
                for path, result in analyses
            ]
        
        # 3. 清理临时文件
        try:
            temp_dir = os.path.dirname(apk_paths[0])
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                self.log("cleaned_temp_files", "DEBUG", path=temp_dir)
        except Exception as e:
            self.log("temp_cleanup_failed", "WARNING", error=str(e))
        
        return analysis_result

    def save_apk_inventory(self, analysis_result: Dict, output_dir: str) -> bool:
        """Persist base/split evidence beside, not inside, the fresh extraction dir."""
        inventory = analysis_result.get("apk_inventory")
        if not inventory:
            return True
        output = Path(output_dir).resolve()
        report = output.parent / f"{output.name}_apk_inventory.json"
        if report.exists():
            self.log("apk_inventory_exists", "ERROR", path=str(report))
            return False
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            json.dumps(
                {
                    "apk_inventory": inventory,
                    "split_analyses": analysis_result.get("split_analyses", []),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.log("apk_inventory_saved", "INFO", path=str(report))
        return True
    
    def validate_dex_files(self, output_dir: str) -> Dict:
        """验证提取的DEX文件，返回准确的统计信息"""
        self.log("validating_dex_files", directory=output_dir)
        
        if not os.path.exists(output_dir):
            self.log("output_directory_not_found", "ERROR", path=output_dir)
            return {"valid_count": 0, "total_files": 0, "details": []}
        
        valid_dex_files = []
        all_files = []
        
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                all_files.append(file_path)
                if os.path.splitext(file)[1].lower() != ".dex":
                    continue
                try:
                    file_size = os.path.getsize(file_path)
                    with open(file_path, "rb") as f:
                        header = f.read(0x70)
                    magic_ok = len(header) >= 8 and re.fullmatch(rb"dex\n[0-9]{3}\x00", header[:8]) is not None
                    size_ok = len(header) >= 0x70 and int.from_bytes(header[0x20:0x24], "little") == file_size
                    header_ok = len(header) >= 0x70 and int.from_bytes(header[0x24:0x28], "little") == 0x70
                    endian_ok = len(header) >= 0x70 and int.from_bytes(header[0x28:0x2C], "little") in {0x12345678, 0x78563412}
                    if magic_ok and size_ok and header_ok and endian_ok:
                        valid_dex_files.append({
                            "path": file_path,
                            "size": file_size,
                            "valid": True,
                            "type": "standard_dex"
                        })
                    else:
                        valid_dex_files.append({
                            "path": file_path,
                            "size": file_size,
                            "valid": False,
                            "type": "unknown",
                            "note": "DEX header/size/endian validation failed"
                        })
                except Exception as e:
                    self.log("file_validation_error", "WARNING", file=file_path, error=str(e))
        
        result = {
            "valid_count": len([f for f in valid_dex_files if f["valid"]]),
            "total_files": len(all_files),
            "suspicious_count": len([f for f in valid_dex_files if not f["valid"]]),
            "details": valid_dex_files
        }
        
        self.log("dex_validation_complete", "INFO", 
                valid=result["valid_count"], total=result["total_files"], suspicious=result["suspicious_count"])
        
        return result

    def validate_with_jadx(self, dex_paths: List[str], output_dir: str) -> Dict[str, object]:
        """Require JADX to accept every extracted DEX before reporting success."""
        jadx = self.script_dir.parents[3] / "tools" / "jadx" / "bin" / "jadx.bat"
        if not jadx.is_file() or not dex_paths:
            return {"ok": False, "error": "jadx or validated DEX input missing"}
        verify_dir = Path(output_dir).resolve() / "jadx_verify"
        if verify_dir.exists():
            return {"ok": False, "error": f"fresh jadx_verify directory required: {verify_dir}"}
        env = os.environ.copy()
        env["JADX_OPTS"] = "-Xmx4g"
        cmd = [str(jadx), "--no-res", "--show-bad-code", "-d", str(verify_dir), *dex_paths]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "jadx validation timed out"}
        sources = list((verify_dir / "sources").rglob("*.java")) if verify_dir.is_dir() else []
        ok = result.returncode == 0 and bool(sources)
        return {
            "ok": ok,
            "returncode": result.returncode,
            "source_files": len(sources),
            "stderr_excerpt": result.stderr[-1000:],
        }
    
    def log(self, key: str, level: str = "INFO", **kwargs):
        """Log a message using internationalized logger"""
        self.logger.log(key, level, **kwargs)
    def analyze_apk_protection(self, apk_path: str) -> Optional[Dict]:
        """分析APK加固类型"""
        self.log(f"分析APK加固类型: {os.path.basename(apk_path)}")
        
        if not os.path.exists(apk_path):
            self.log(f"APK文件不存在: {apk_path}", "ERROR")
            return None
        
        analyzer_script = self.script_dir / "apk_protection_analyzer.py"
        if not analyzer_script.exists():
            self.log(f"加固分析脚本不存在: {analyzer_script}", "ERROR")
            return None
        
        try:
            # 运行分析器，强制使用JSON输出
            cmd = [sys.executable, str(analyzer_script), "--apk", apk_path, "--json"]
            if self.verbose:
                cmd.append("--verbose")
            
            self.log(f"执行命令: {' '.join(cmd)}", "DEBUG")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                self.log(f"加固分析失败: {result.stderr[:200]}", "ERROR")
                return None
            
            # 解析JSON输出
            try:
                analysis_result = json.loads(result.stdout.strip())
                self.log(f"✅ 加固分析完成", "SUCCESS")
                self.log(f"   加固类型: {analysis_result.get('protection_type', 'unknown')}")
                self.log(f"   加固级别: {analysis_result.get('protection_level', 'unknown')}")
                self.log(f"   置信度: {analysis_result.get('confidence_score', 0)*100:.1f}%")
                
                return analysis_result
            except json.JSONDecodeError as e:
                self.log(f"❌ 无法解析加固分析结果: {e}", "ERROR")
                self.log(f"原始输出: {result.stdout[:500]}", "DEBUG")
                return None
                
        except subprocess.TimeoutExpired:
            self.log("加固分析超时（60秒）", "ERROR")
            return None
        except Exception as e:
            self.log(f"加固分析异常: {e}", "ERROR")
            return None
    
    def select_strategy(self, analysis_result: Dict) -> Tuple[str, str]:
        """根据加固分析结果选择解包策略"""
        protection_type = analysis_result.get("protection_type", "unknown")
        protection_level = analysis_result.get("protection_level", "basic")
        confidence = analysis_result.get("confidence_score", 0)
        
        # 默认策略
        default_strategy = "root"
        reason = "未知壳默认使用零注入 Root 取证"
        
        # 检查加固类型
        if protection_type in self.strategy_decision_tree:
            selected_strategy = self.strategy_decision_tree[protection_type]
            reason = f"加固类型 '{protection_type}' 推荐使用 {selected_strategy} 策略"
            
            # lao_1_he: low-confidence shell classification must not escalate
            # to a more invasive process-injection path.
            if confidence < 0.3:
                self.log(f"⚠️  加固检测置信度低 ({confidence*100:.1f}%)，可能误判", "WARNING")
                selected_strategy = "root"
                reason = "加固置信度低，保持零注入 Root 取证"
        else:
            # 未知加固类型，根据级别决定
            if protection_level in ["enterprise", "commercial"]:
                selected_strategy = "root"
                reason = f"商业/企业级加固，使用Root内存提取"
            else:
                selected_strategy = default_strategy
                reason = f"未知加固类型，使用默认策略"
        
        # 考虑加固级别的影响
        if protection_level == "enterprise" and selected_strategy == "frida":
            selected_strategy = "root"
            reason = f"企业级加固，强制使用Root内存提取"
        
        return selected_strategy, reason
    
    def execute_frida_strategy(self, package_name: str, output_dir: str = None, 
                              deep_search: bool = False, bypass_antidebug: bool = False) -> bool:
        """执行Frida动态解包策略"""
        self.log("executing_frida_strategy", package=package_name)
        
        script_path = self.script_dir / "enhanced_dexdump_runner.py"
        if not script_path.exists():
            self.log(f"Frida解包脚本不存在: {script_path}", "ERROR")
            return False
        
        try:
            cmd = [sys.executable, str(script_path), "--package", package_name]
            if self.serial:
                cmd.extend(["--serial", self.serial])
            
            if output_dir:
                cmd.extend(["--output", output_dir])
            
            if deep_search:
                cmd.append("--deep-search")
            
            if bypass_antidebug:
                cmd.append("--bypass-antidebug")
            
            if self.verbose:
                cmd.append("--verbose")
            
            self.log(f"执行命令: {' '.join(cmd)}", "DEBUG")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                self.log("frida_extraction_process_completed", "INFO")
                return True
            else:
                self.log(f"❌ Frida动态解包失败", "ERROR")
                self.log(f"错误输出: {result.stderr[:500]}", "DEBUG")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("Frida解包超时（5分钟）", "ERROR")
            return False
        except Exception as e:
            self.log(f"Frida解包异常: {e}", "ERROR")
            return False
    
    def execute_root_strategy(self, package_name: str, output_dir: str = None) -> bool:
        """执行Root内存提取策略"""
        self.log("executing_root_strategy", package=package_name)
        
        script_path = self.script_dir / "root_memory_extractor.py"
        if not script_path.exists():
            self.log(f"Root内存提取脚本不存在: {script_path}", "ERROR")
            return False
        
        try:
            cmd = [sys.executable, str(script_path), "--package", package_name]
            if self.serial:
                cmd.extend(["--serial", self.serial])
            
            if output_dir:
                cmd.extend(["--output", output_dir])
            
            if self.verbose:
                cmd.append("--verbose")
            
            self.log(f"执行命令: {' '.join(cmd)}", "DEBUG")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时（Root提取可能较慢）
            )
            
            if result.returncode == 0:
                self.log("root_extraction_process_completed", "INFO")
                return True
            else:
                self.log(f"❌ Root内存提取失败", "ERROR")
                self.log(f"错误输出: {result.stderr[:500]}", "DEBUG")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("Root内存提取超时（10分钟）", "ERROR")
            return False
        except Exception as e:
            self.log(f"Root内存提取异常: {e}", "ERROR")
            return False
    
    def execute_snapshot_strategy(self, package_name: str, output_dir: str = None) -> bool:
        """Fail closed until the snapshot helper has serial and artifact gates."""
        self.log(
            "snapshot_strategy_not_validated; use android-dynamic for acquisition "
            "and rerun this orchestrator on extracted DEX artifacts",
            "ERROR",
        )
        return False
    
    def unpack_with_auto_strategy(self, package_name: str, apk_path: str = None,
                                 output_dir: str = None, **kwargs) -> bool:
        """使用自动策略解包应用"""
        self.log("=" * 60)
        self.log("🎯 智能解包协调器 - 自动策略选择")
        self.log(f"目标应用: {package_name}")
        self.log("=" * 60)
        
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+", package_name):
            self.log("invalid_package_name", "ERROR", package=package_name)
            return False
        if not output_dir:
            self.log("output_directory_required", "ERROR")
            return False
        output_dir = str(Path(output_dir).resolve())
        if Path(output_dir).exists() and any(Path(output_dir).iterdir()):
            self.log("output_directory_not_empty", "ERROR", path=output_dir)
            return False

        # 1. 分析加固类型（优先使用提供的APK，否则从设备提取）
        analysis_result = None
        if apk_path:
            self.log("using_provided_apk", "INFO", apk=os.path.basename(apk_path))
            analysis_result = self.analyze_apk_protection(apk_path)
        else:
            self.log("no_apk_provided", "INFO")
            self.log("attempting_to_extract_apk_from_device", "INFO")
            
            # 尝试从设备提取APK进行分析
            analysis_result = self.analyze_installed_app(package_name)
            
            if analysis_result:
                self.log("apk_analysis_successful", "SUCCESS")
                protection_type = analysis_result.get("protection_type", "unknown")
                confidence = analysis_result.get("confidence_score", 0)
                self.log(f"   检测到的加固: {protection_type} (置信度: {confidence*100:.1f}%)")
            else:
                self.log("failed_to_analyze_app", "WARNING")
                self.log("   壳分析失败，保持零注入 Root 取证", "WARNING")
        
        # 2. 选择策略
        if analysis_result:
            strategy, reason = self.select_strategy(analysis_result)
            self.log("strategy_selected", strategy=strategy.upper())
            self.log("selection_reason", reason=reason)
        else:
            strategy = "root"
            self.log(f"🧠 策略选择: {strategy.upper()} (分析失败，零注入默认)")

        if analysis_result and not self.save_apk_inventory(analysis_result, output_dir):
            return False
        if strategy == "recon":
            self.log("no_shell_detected_return_to_recon", "ERROR")
            return False
        
        # 3. 执行策略
        self.log("")
        self.log("starting_unpack_strategy")
        
        success = False
        if strategy == "frida":
            success = self.execute_frida_strategy(
                package_name, output_dir,
                deep_search=kwargs.get("deep_search", False),
                bypass_antidebug=kwargs.get("bypass_antidebug", False)
            )
        elif strategy == "root":
            success = self.execute_root_strategy(package_name, output_dir)
        else:
            self.log(f"❌ 未知策略: {strategy}", "ERROR")
            return False
        
        # 4. 结果汇总与验证
        self.log("")
        self.log("=" * 60)
        if success:
            # A child exit code only means extraction ran. Success is gated on
            # structural DEX checks plus a fresh JADX decompile.
            if output_dir and os.path.exists(output_dir):
                validation_result = self.validate_dex_files(output_dir)
                
                self.log("validation_results", "INFO")
                self.log(f"   总文件数: {validation_result['total_files']}")
                self.log(f"   有效DEX文件: {validation_result['valid_count']}")
                self.log(f"   可疑/加密文件: {validation_result['suspicious_count']}")
                
                valid_paths = [item["path"] for item in validation_result["details"] if item["valid"]]
                if validation_result['valid_count'] > 0:
                    self.log("   有效DEX文件列表:", "INFO")
                    for i, dex_info in enumerate(validation_result['details'][:10]):  # 只显示前10个
                        if dex_info["valid"]:
                            size_mb = dex_info["size"] / (1024*1024)
                            self.log(f"     {i+1}. {os.path.basename(dex_info['path'])} ({size_mb:.2f} MB)")
                
                if not valid_paths:
                    self.log("no_structurally_valid_dex", "ERROR")
                    return False
                jadx_result = self.validate_with_jadx(valid_paths, output_dir)
                if not jadx_result.get("ok"):
                    self.log("jadx_validation_failed", "ERROR", result=jadx_result)
                    return False

                self.log("unpack_success", "SUCCESS")
                self.log(f"   使用的策略: {strategy.upper()}")

                # 警告如果有大量可疑文件（可能是加密的）
                if validation_result['suspicious_count'] > validation_result['valid_count']:
                    self.log("many_encrypted_files_warning", "WARNING")
                    self.log(f"   检测到大量可疑/加密文件 ({validation_result['suspicious_count']}个)")
                    self.log(f"   这可能表明加固使用了内存加密技术")
                    
                    # 针对梆梆加固的特殊建议
                    if analysis_result and analysis_result.get("protection_type") == "bangcle":
                        self.log("bangcle_encryption_warning", "WARNING")
                        self.log(f"   梆梆加固商业版使用内存加密技术")
                        self.log(f"   提取的DEX文件可能无法直接反编译")
                        self.log(f"   建议尝试：")
                        self.log(f"   1. 运行时内存dump (Frida脚本)")
                        self.log(f"   2. 动态调试获取解密后的DEX")
                        self.log(f"   3. 分析加密算法尝试解密")
                    
            elif output_dir:
                self.log("output_directory_not_found", "ERROR", path=output_dir)
                return False
        else:
            self.log("unpack_failed", "ERROR")
            self.log(f"   尝试的策略: {strategy.upper()}")
            
            # 如果Frida失败，建议尝试Root策略
            if strategy == "frida" and analysis_result:
                protection_type = analysis_result.get("protection_type", "")
                if protection_type in ["ijiami", "bangcle", "360", "tencent"]:
                    self.log("commercial_reinforcement_suggestion", "WARNING")
                    self.log("   建议使用Root策略重新尝试: --strategy root")
        
        return success
    
    def unpack_with_specified_strategy(self, package_name: str, strategy: str,
                                      output_dir: str = None, **kwargs) -> bool:
        """使用指定策略解包应用"""
        self.log(f"使用指定策略解包: {strategy.upper()}")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+", package_name):
            self.log("invalid_package_name", "ERROR", package=package_name)
            return False
        if not output_dir:
            self.log("output_directory_required", "ERROR")
            return False
        resolved_output = Path(output_dir).resolve()
        if resolved_output.exists() and any(resolved_output.iterdir()):
            self.log("output_directory_not_empty", "ERROR", path=str(resolved_output))
            return False

        success = False
        if strategy == "frida":
            success = self.execute_frida_strategy(
                package_name, str(resolved_output),
                deep_search=kwargs.get("deep_search", False),
                bypass_antidebug=kwargs.get("bypass_antidebug", False)
            )
        elif strategy == "root":
            success = self.execute_root_strategy(package_name, str(resolved_output))
        elif strategy == "auto":
            return self.unpack_with_auto_strategy(
                package_name, kwargs.get("apk_path"), str(resolved_output), **kwargs
            )
        else:
            self.log(f"❌ 未知策略: {strategy}", "ERROR")
            return False

        if not success or not resolved_output.is_dir():
            return False
        validation = self.validate_dex_files(str(resolved_output))
        valid_paths = [item["path"] for item in validation["details"] if item["valid"]]
        if not valid_paths:
            self.log("no_structurally_valid_dex", "ERROR")
            return False
        jadx_result = self.validate_with_jadx(valid_paths, str(resolved_output))
        if not jadx_result.get("ok"):
            self.log("jadx_validation_failed", "ERROR", result=jadx_result)
            return False
        self.log("unpack_success", "SUCCESS")
        return True

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='智能解包协调器 - 根据加固类型自动选择最佳解包策略'
    )
    
    parser.add_argument('--package', '-p', required=True, help='目标应用包名')
    parser.add_argument('--serial', required=True, help='唯一 Android 设备 serial')
    parser.add_argument('--apk', '-a', help='APK文件路径（用于自动策略分析）')
    parser.add_argument('--output', '-o', required=True, help='全新输出目录')
    parser.add_argument('--strategy', '-s', default='auto',
                       choices=['auto', 'frida', 'root'],
                       help='解包策略: auto(自动), frida(Frida动态), root(Root内存)')
    parser.add_argument('--deep-search', action='store_true', help='深度搜索模式（仅Frida策略）')
    parser.add_argument('--bypass-antidebug', action='store_true', help='绕过反调试（仅Frida策略）')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    orchestrator = UnpackOrchestrator(verbose=args.verbose, serial=args.serial)
    
    if args.strategy == "auto":
        success = orchestrator.unpack_with_auto_strategy(
            args.package, args.apk, args.output,
            deep_search=args.deep_search,
            bypass_antidebug=args.bypass_antidebug
        )
    else:
        success = orchestrator.unpack_with_specified_strategy(
            args.package, args.strategy, args.output,
            deep_search=args.deep_search,
            bypass_antidebug=args.bypass_antidebug,
            apk_path=args.apk
        )
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
