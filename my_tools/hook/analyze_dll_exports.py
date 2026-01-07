#!/usr/bin/env python3
"""
DLL 导出函数分析工具

分析 Windows DLL 文件的导出函数、架构信息等。

使用方法:
    python my_tools/hook/analyze_dll_exports.py <dll_path> [options]

选项:
    -e, --expect <func1,func2,...>  验证指定函数是否存在
    -f, --filter <keyword>          只显示包含关键字的导出
    -j, --json                      以 JSON 格式输出
    -q, --quiet                     静默模式，只输出导出函数名
    -h, --help                      显示帮助信息

示例:
    python my_tools/hook/analyze_dll_exports.py deps/bin/MaaWin32ControlUnit.dll
    python my_tools/hook/analyze_dll_exports.py some.dll -e "Create,Destroy,GetVersion"
    python my_tools/hook/analyze_dll_exports.py some.dll -f "Control"
    python my_tools/hook/analyze_dll_exports.py some.dll -j > exports.json
"""

import sys
import os
import struct
import subprocess
import argparse
import json
from pathlib import Path
from typing import Optional


class DllAnalyzer:
    """DLL 分析器"""

    def __init__(self, dll_path: str):
        self.dll_path = Path(dll_path)
        self.result = {
            "file": str(self.dll_path),
            "exists": self.dll_path.exists(),
            "method": None,
            "machine": None,
            "characteristics": [],
            "exports": [],
            "error": None
        }

    def analyze(self) -> dict:
        """执行分析，返回结果字典"""
        if not self.result["exists"]:
            self.result["error"] = f"File not found: {self.dll_path}"
            return self.result

        # 尝试多种分析方法
        methods = [
            ("pefile", self._analyze_with_pefile),
            ("manual_pe", self._analyze_pe_manually),
            ("dumpbin", self._analyze_with_dumpbin),
        ]

        for method_name, method_func in methods:
            try:
                if method_func():
                    self.result["method"] = method_name
                    break
            except Exception as e:
                continue

        if not self.result["method"]:
            self.result["error"] = "All analysis methods failed"

        return self.result

    def _analyze_with_pefile(self) -> bool:
        """使用 pefile 库分析"""
        try:
            import pefile
        except ImportError:
            return False

        try:
            pe = pefile.PE(str(self.dll_path))
        except Exception:
            return False

        # 架构信息
        machine_types = {
            0x14c: "x86 (32-bit)",
            0x8664: "x64 (64-bit)",
            0xaa64: "ARM64"
        }
        self.result["machine"] = machine_types.get(
            pe.FILE_HEADER.Machine,
            f"Unknown (0x{pe.FILE_HEADER.Machine:x})"
        )

        # DLL 特性
        if pe.FILE_HEADER.Characteristics & 0x2000:
            self.result["characteristics"].append("DLL")
        if pe.FILE_HEADER.Characteristics & 0x0020:
            self.result["characteristics"].append("Large Address Aware")

        # 导出函数
        if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
            for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                self.result["exports"].append({
                    "ordinal": exp.ordinal,
                    "name": exp.name.decode('utf-8') if exp.name else None,
                    "rva": hex(exp.address) if exp.address else None,
                    "forwarder": exp.forwarder.decode('utf-8') if exp.forwarder else None
                })

        pe.close()
        return True

    def _analyze_pe_manually(self) -> bool:
        """手动解析 PE 文件"""
        try:
            with open(self.dll_path, 'rb') as f:
                # DOS 头
                dos_header = f.read(64)
                if dos_header[:2] != b'MZ':
                    return False

                pe_offset = struct.unpack('<I', dos_header[60:64])[0]

                # PE 签名
                f.seek(pe_offset)
                if f.read(4) != b'PE\x00\x00':
                    return False

                # COFF 头
                coff_header = f.read(20)
                machine = struct.unpack('<H', coff_header[0:2])[0]
                num_sections = struct.unpack('<H', coff_header[2:4])[0]
                optional_header_size = struct.unpack('<H', coff_header[16:18])[0]

                machine_types = {
                    0x14c: "x86 (32-bit)",
                    0x8664: "x64 (64-bit)",
                    0xaa64: "ARM64"
                }
                self.result["machine"] = machine_types.get(machine, f"Unknown (0x{machine:x})")

                # 可选头
                optional_header = f.read(optional_header_size)
                magic = struct.unpack('<H', optional_header[0:2])[0]

                if magic == 0x10b:  # PE32
                    export_rva = struct.unpack('<I', optional_header[96:100])[0]
                elif magic == 0x20b:  # PE32+
                    export_rva = struct.unpack('<I', optional_header[112:116])[0]
                else:
                    return False

                if export_rva == 0:
                    return True  # 没有导出表也算成功

                # 节表
                sections = []
                for _ in range(num_sections):
                    section = f.read(40)
                    sections.append({
                        'virtual_addr': struct.unpack('<I', section[12:16])[0],
                        'virtual_size': struct.unpack('<I', section[8:12])[0],
                        'raw_ptr': struct.unpack('<I', section[20:24])[0],
                    })

                def rva_to_offset(rva):
                    for sec in sections:
                        if sec['virtual_addr'] <= rva < sec['virtual_addr'] + sec['virtual_size']:
                            return rva - sec['virtual_addr'] + sec['raw_ptr']
                    return None

                # 导出目录
                export_offset = rva_to_offset(export_rva)
                if export_offset is None:
                    return True

                f.seek(export_offset)
                export_dir = f.read(40)

                num_names = struct.unpack('<I', export_dir[24:28])[0]
                name_ptr_rva = struct.unpack('<I', export_dir[32:36])[0]
                ordinal_table_rva = struct.unpack('<I', export_dir[36:40])[0]
                addr_table_rva = struct.unpack('<I', export_dir[28:32])[0]
                ordinal_base = struct.unpack('<I', export_dir[16:20])[0]
                num_functions = struct.unpack('<I', export_dir[20:24])[0]

                name_ptr_offset = rva_to_offset(name_ptr_rva)
                if not name_ptr_offset:
                    return True

                f.seek(name_ptr_offset)
                name_ptrs = struct.unpack(f'<{num_names}I', f.read(4 * num_names))

                ordinal_offset = rva_to_offset(ordinal_table_rva)
                f.seek(ordinal_offset)
                ordinals = struct.unpack(f'<{num_names}H', f.read(2 * num_names))

                addr_offset = rva_to_offset(addr_table_rva)
                f.seek(addr_offset)
                addresses = struct.unpack(f'<{num_functions}I', f.read(4 * num_functions))

                for i in range(num_names):
                    name_offset = rva_to_offset(name_ptrs[i])
                    if name_offset:
                        f.seek(name_offset)
                        name_bytes = b''
                        while True:
                            b = f.read(1)
                            if b == b'\x00' or not b:
                                break
                            name_bytes += b

                        ordinal = ordinals[i]
                        self.result["exports"].append({
                            "ordinal": ordinal + ordinal_base,
                            "name": name_bytes.decode('utf-8', errors='ignore'),
                            "rva": hex(addresses[ordinal]) if ordinal < len(addresses) else None
                        })

                return True

        except Exception:
            return False

    def _analyze_with_dumpbin(self) -> bool:
        """使用 dumpbin 工具分析"""
        import glob

        dumpbin_patterns = [
            r"C:\Program Files\Microsoft Visual Studio\2022\*\VC\Tools\MSVC\*\bin\Hostx64\x64\dumpbin.exe",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2019\*\VC\Tools\MSVC\*\bin\Hostx64\x64\dumpbin.exe",
        ]

        dumpbin_exe = None
        for pattern in dumpbin_patterns:
            matches = glob.glob(pattern)
            if matches:
                dumpbin_exe = matches[0]
                break

        if not dumpbin_exe:
            try:
                subprocess.run(["dumpbin", "/?"], capture_output=True, check=True)
                dumpbin_exe = "dumpbin"
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False

        try:
            proc = subprocess.run(
                [dumpbin_exe, "/exports", str(self.dll_path)],
                capture_output=True,
                text=True,
                timeout=30
            )

            in_exports = False
            for line in proc.stdout.split('\n'):
                line = line.strip()
                if "ordinal" in line.lower() and "hint" in line.lower():
                    in_exports = True
                    continue
                if in_exports and line:
                    parts = line.split()
                    if len(parts) >= 4 and parts[0].isdigit():
                        self.result["exports"].append({
                            "ordinal": int(parts[0]),
                            "name": parts[3] if len(parts) > 3 else None,
                            "rva": parts[2]
                        })
                    elif not line or line.startswith("Summary"):
                        in_exports = False

            return True

        except Exception:
            return False


def format_table_output(result: dict, filter_keyword: str = None) -> str:
    """格式化表格输出"""
    lines = []
    lines.append("=" * 70)
    lines.append(f"DLL Analysis: {result['file']}")
    lines.append("=" * 70)

    if result.get("error"):
        lines.append(f"\n[ERROR] {result['error']}")
        return "\n".join(lines)

    lines.append(f"\nAnalysis Method: {result.get('method', 'unknown')}")

    if result.get("machine"):
        lines.append(f"Architecture: {result['machine']}")

    if result.get("characteristics"):
        lines.append(f"Characteristics: {', '.join(result['characteristics'])}")

    exports = result.get("exports", [])

    # 应用过滤
    if filter_keyword:
        exports = [e for e in exports if e.get("name") and filter_keyword.lower() in e["name"].lower()]
        lines.append(f"\nFilter: '{filter_keyword}'")

    lines.append(f"Export Count: {len(exports)}")

    if exports:
        lines.append(f"\n{'Ordinal':<10} {'Name':<50} {'RVA'}")
        lines.append("-" * 70)
        for exp in sorted(exports, key=lambda x: x.get('ordinal', 0) or 0):
            ordinal = exp.get('ordinal', '-')
            name = exp.get('name', '<unnamed>')
            rva = exp.get('rva', '-')
            forwarder = exp.get('forwarder')

            line = f"{ordinal:<10} {name:<50} {rva}"
            if forwarder:
                line += f" -> {forwarder}"
            lines.append(line)

    return "\n".join(lines)


def format_quiet_output(result: dict, filter_keyword: str = None) -> str:
    """静默模式输出，只输出函数名"""
    exports = result.get("exports", [])
    if filter_keyword:
        exports = [e for e in exports if e.get("name") and filter_keyword.lower() in e["name"].lower()]

    names = [e.get("name") for e in exports if e.get("name")]
    return "\n".join(sorted(names))


def verify_expected_functions(result: dict, expected: list) -> dict:
    """验证期望的函数是否存在"""
    export_names = {e.get("name") for e in result.get("exports", []) if e.get("name")}

    found = []
    missing = []

    for func in expected:
        if func in export_names:
            found.append(func)
        else:
            missing.append(func)

    return {
        "expected": expected,
        "found": found,
        "missing": missing,
        "all_found": len(missing) == 0
    }


def format_verification_output(verify_result: dict) -> str:
    """格式化验证结果输出"""
    lines = []
    lines.append("\n" + "=" * 70)
    lines.append("Function Verification")
    lines.append("=" * 70)

    if verify_result["found"]:
        lines.append("\n[FOUND]")
        for func in verify_result["found"]:
            lines.append(f"   + {func}")

    if verify_result["missing"]:
        lines.append("\n[MISSING]")
        for func in verify_result["missing"]:
            lines.append(f"   - {func}")

    lines.append("\n" + "-" * 70)
    if verify_result["all_found"]:
        lines.append("Result: ALL expected functions found")
    else:
        lines.append(f"Result: {len(verify_result['found'])}/{len(verify_result['expected'])} functions found")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze DLL export functions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s MaaWin32ControlUnit.dll
  %(prog)s some.dll -e "Create,Destroy,GetVersion"
  %(prog)s some.dll -f "Control"
  %(prog)s some.dll -j > exports.json
        """
    )

    parser.add_argument("dll_path", help="Path to the DLL file")
    parser.add_argument("-e", "--expect", help="Comma-separated list of expected function names")
    parser.add_argument("-f", "--filter", help="Filter exports by keyword")
    parser.add_argument("-j", "--json", action="store_true", help="Output as JSON")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode, only output function names")

    args = parser.parse_args()

    # 分析 DLL
    analyzer = DllAnalyzer(args.dll_path)
    result = analyzer.analyze()

    # 验证期望的函数
    verify_result = None
    if args.expect:
        expected_funcs = [f.strip() for f in args.expect.split(",")]
        verify_result = verify_expected_functions(result, expected_funcs)

    # 输出结果
    if args.json:
        output = {
            "analysis": result,
        }
        if verify_result:
            output["verification"] = verify_result
        print(json.dumps(output, indent=2, ensure_ascii=False))

    elif args.quiet:
        print(format_quiet_output(result, args.filter))

    else:
        print(format_table_output(result, args.filter))
        if verify_result:
            print(format_verification_output(verify_result))

    # 返回码
    if result.get("error"):
        sys.exit(1)
    if verify_result and not verify_result["all_found"]:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
