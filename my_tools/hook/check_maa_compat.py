#!/usr/bin/env python3
"""
MAA Framework 兼容性检测工具

检测 MAA Framework 更新后是否与 MSA Hook 方案兼容。

使用方法:
    python my_tools/hook/check_maa_compat.py              # 执行兼容性检测
    python my_tools/hook/check_maa_compat.py --init       # 从当前框架生成基线（首次使用或确认兼容后）
    python my_tools/hook/check_maa_compat.py --verbose    # 显示详细信息
    python my_tools/hook/check_maa_compat.py --json       # JSON 格式输出

检测项目:
    1. DLL 导出函数 - 检测 MaaWin32ControlUnit.dll 的导出函数是否变化
    2. 关键枚举值 - 检测 MaaWin32InputMethod_SendMessage 等关键定义
    3. 虚函数表 - 检测 ControlUnitAPI 类的虚函数是否变化（最关键）
"""

import sys
import os
import re
import json
import hashlib
import argparse
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

# 添加当前目录到路径，以便导入 analyze_dll_exports
sys.path.insert(0, str(Path(__file__).parent))
from analyze_dll_exports import DllAnalyzer


# ========== 配置 ==========

SCRIPT_DIR = Path(__file__).parent
BASELINE_DIR = SCRIPT_DIR / "maa_baseline"
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # my_tools/hook/ -> my_tools/ -> 项目根目录

# 框架文件路径（相对于项目根目录）
FRAMEWORK_PATHS = {
    "dll": "deps/bin/MaaWin32ControlUnit.dll",
    "dll_original": "deps/bin/MaaWin32ControlUnit_original.dll",
    "maa_def_h": "deps/include/MaaFramework/MaaDef.h",
    "control_unit_h": "hook/proxy/control_unit.h",
}

# 基线文件
BASELINE_FILES = {
    "exports": BASELINE_DIR / "exports.json",
    "maa_def": BASELINE_DIR / "maa_def.json",
    "control_unit_api": BASELINE_DIR / "control_unit_api.json",
}


# ========== 数据结构 ==========

@dataclass
class CheckResult:
    """单项检测结果"""
    name: str
    status: str  # "ok", "warn", "error"
    message: str
    details: list = field(default_factory=list)


@dataclass
class CompatReport:
    """兼容性报告"""
    compatible: bool
    results: list  # List[CheckResult]
    framework_version: str = "unknown"


# ========== 检测函数 ==========

def check_dll_exports(verbose: bool = False) -> CheckResult:
    """检测 DLL 导出函数"""
    # 优先使用原版 DLL（如果存在）
    dll_path = PROJECT_ROOT / FRAMEWORK_PATHS["dll_original"]
    if not dll_path.exists():
        dll_path = PROJECT_ROOT / FRAMEWORK_PATHS["dll"]

    if not dll_path.exists():
        return CheckResult(
            name="DLL 导出函数",
            status="error",
            message=f"DLL 文件不存在: {dll_path}"
        )

    # 加载基线
    baseline_path = BASELINE_FILES["exports"]
    if not baseline_path.exists():
        return CheckResult(
            name="DLL 导出函数",
            status="warn",
            message="基线文件不存在，请先运行 --init 生成基线"
        )

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    # 分析当前 DLL
    analyzer = DllAnalyzer(str(dll_path))
    result = analyzer.analyze()

    if result.get("error"):
        return CheckResult(
            name="DLL 导出函数",
            status="error",
            message=f"DLL 分析失败: {result['error']}"
        )

    # 对比导出函数
    current_exports = {e["name"] for e in result.get("exports", []) if e.get("name")}
    expected_exports = {e["name"] for e in baseline.get("exports", [])}

    missing = expected_exports - current_exports
    extra = current_exports - expected_exports

    details = []
    if missing:
        details.append(f"缺失的函数: {', '.join(sorted(missing))}")
    if extra and verbose:
        details.append(f"新增的函数: {', '.join(sorted(extra))}")

    if missing:
        return CheckResult(
            name="DLL 导出函数",
            status="error",
            message=f"缺失 {len(missing)} 个关键导出函数",
            details=details
        )
    elif extra:
        return CheckResult(
            name="DLL 导出函数",
            status="ok",
            message=f"导出函数完整（新增 {len(extra)} 个）",
            details=details
        )
    else:
        return CheckResult(
            name="DLL 导出函数",
            status="ok",
            message="导出函数完全匹配"
        )


def check_maa_def(verbose: bool = False) -> CheckResult:
    """检测 MaaDef.h 中的关键定义"""
    header_path = PROJECT_ROOT / FRAMEWORK_PATHS["maa_def_h"]

    if not header_path.exists():
        return CheckResult(
            name="关键枚举定义",
            status="error",
            message=f"头文件不存在: {header_path}"
        )

    # 加载基线
    baseline_path = BASELINE_FILES["maa_def"]
    if not baseline_path.exists():
        return CheckResult(
            name="关键枚举定义",
            status="warn",
            message="基线文件不存在，请先运行 --init 生成基线"
        )

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    # 读取头文件
    with open(header_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 检测关键定义
    critical_defines = baseline.get("critical_defines", {})
    issues = []
    details = []

    for name, info in critical_defines.items():
        expected_value = info.get("value", "")
        # 构建正则表达式匹配 #define
        pattern = rf"#define\s+{re.escape(name)}\s+(.+)"
        match = re.search(pattern, content)

        if not match:
            issues.append(f"{name} 未找到")
        else:
            actual_value = match.group(1).strip()
            if actual_value != expected_value:
                issues.append(f"{name} 值变化: {expected_value} -> {actual_value}")
            elif verbose:
                details.append(f"{name} = {actual_value}")

    if issues:
        return CheckResult(
            name="关键枚举定义",
            status="error",
            message=f"发现 {len(issues)} 个定义变化",
            details=issues
        )
    else:
        return CheckResult(
            name="关键枚举定义",
            status="ok",
            message="关键定义无变化",
            details=details
        )


def check_vtable(verbose: bool = False) -> CheckResult:
    """检测虚函数表定义"""
    header_path = PROJECT_ROOT / FRAMEWORK_PATHS["control_unit_h"]

    if not header_path.exists():
        return CheckResult(
            name="虚函数表",
            status="error",
            message=f"头文件不存在: {header_path}"
        )

    # 加载基线
    baseline_path = BASELINE_FILES["control_unit_api"]
    if not baseline_path.exists():
        return CheckResult(
            name="虚函数表",
            status="warn",
            message="基线文件不存在，请先运行 --init 生成基线"
        )

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    # 读取头文件
    with open(header_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取 ControlUnitAPI 类的定义（关键类）
    # 匹配 class ControlUnitAPI { ... };
    class_pattern = r"class\s+ControlUnitAPI\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}"
    class_match = re.search(class_pattern, content, re.DOTALL)

    if not class_match:
        return CheckResult(
            name="虚函数表",
            status="error",
            message="未找到 ControlUnitAPI 类定义"
        )

    class_body = class_match.group(1)

    # 从类体中提取虚函数
    current_vtable = extract_vtable_from_class(class_body)

    # 从基线获取期望的虚函数表
    expected_vtable = [v["name"] for v in baseline.get("vtable", [])]

    # 对比
    issues = []
    details = []

    # 检查数量
    if len(current_vtable) != len(expected_vtable):
        issues.append(f"虚函数数量变化: {len(expected_vtable)} -> {len(current_vtable)}")

    # 检查顺序和名称
    for i, (expected, current) in enumerate(zip(expected_vtable, current_vtable)):
        if expected != current:
            issues.append(f"索引 {i}: {expected} -> {current}")
        elif verbose:
            details.append(f"[{i}] {current}")

    # 检查新增的虚函数
    if len(current_vtable) > len(expected_vtable):
        extra = current_vtable[len(expected_vtable):]
        issues.append(f"新增虚函数: {', '.join(extra)}")

    # 检查缺失的虚函数
    if len(current_vtable) < len(expected_vtable):
        missing = expected_vtable[len(current_vtable):]
        issues.append(f"缺失虚函数: {', '.join(missing)}")

    if issues:
        return CheckResult(
            name="虚函数表",
            status="error",
            message=f"虚函数表发生变化（ABI 不兼容）",
            details=issues
        )
    else:
        return CheckResult(
            name="虚函数表",
            status="ok",
            message=f"虚函数表匹配（{len(current_vtable)} 个虚函数）",
            details=details
        )


def extract_vtable_from_class(class_body: str) -> list:
    """从类体中提取虚函数列表"""
    vtable = []
    seen = set()

    # 匹配析构函数: virtual ~ClassName()
    destructor_pattern = r"virtual\s+(~\w+)\s*\([^)]*\)"
    for match in re.finditer(destructor_pattern, class_body):
        name = match.group(1)
        if name not in seen:
            vtable.append(name)
            seen.add(name)

    # 匹配普通虚函数: virtual ReturnType name(...)
    # 按出现顺序提取
    virtual_pattern = r"virtual\s+(?:\w+[\w\s\*&<>:]*)\s+(\w+)\s*\([^)]*\)"
    for match in re.finditer(virtual_pattern, class_body):
        name = match.group(1)
        if name not in seen:
            vtable.append(name)
            seen.add(name)

    return vtable


def check_header_hash(verbose: bool = False) -> CheckResult:
    """检测关键头文件的哈希值（辅助检测）"""
    header_path = PROJECT_ROOT / FRAMEWORK_PATHS["control_unit_h"]

    if not header_path.exists():
        return CheckResult(
            name="头文件哈希",
            status="warn",
            message="头文件不存在"
        )

    with open(header_path, "rb") as f:
        content = f.read()

    current_hash = hashlib.sha256(content).hexdigest()[:16]

    # 这个检测主要是辅助性的，提醒用户头文件有变化
    return CheckResult(
        name="头文件哈希",
        status="ok",
        message=f"control_unit.h SHA256: {current_hash}",
        details=[f"完整哈希: {hashlib.sha256(content).hexdigest()}"] if verbose else []
    )


# ========== 基线生成 ==========

def init_baseline() -> bool:
    """从当前框架生成基线"""
    print("=" * 60)
    print("生成 MAA Framework 兼容性基线")
    print("=" * 60)

    # 确保基线目录存在
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    success = True

    # 1. 生成导出函数基线
    print("\n[1/3] 生成导出函数基线...")
    dll_path = PROJECT_ROOT / FRAMEWORK_PATHS["dll_original"]
    if not dll_path.exists():
        dll_path = PROJECT_ROOT / FRAMEWORK_PATHS["dll"]

    if dll_path.exists():
        analyzer = DllAnalyzer(str(dll_path))
        result = analyzer.analyze()

        if not result.get("error"):
            exports_baseline = {
                "_comment": "MAA Framework MaaWin32ControlUnit.dll 导出函数基线",
                "_version": "1.0",
                "_created": "auto-generated",
                "_framework_version": "unknown",
                "exports": [
                    {"name": e["name"], "critical": True}
                    for e in result.get("exports", [])
                    if e.get("name")
                ]
            }
            with open(BASELINE_FILES["exports"], "w", encoding="utf-8") as f:
                json.dump(exports_baseline, f, indent=4, ensure_ascii=False)
            print(f"   已保存: {BASELINE_FILES['exports']}")
            print(f"   导出函数数量: {len(exports_baseline['exports'])}")
        else:
            print(f"   错误: {result['error']}")
            success = False
    else:
        print(f"   跳过: DLL 文件不存在")

    # 2. 生成 MaaDef.h 基线
    print("\n[2/3] 生成 MaaDef.h 基线...")
    maa_def_path = PROJECT_ROOT / FRAMEWORK_PATHS["maa_def_h"]

    if maa_def_path.exists():
        with open(maa_def_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取关键定义
        critical_names = [
            "MaaWin32InputMethod_SendMessage",
            "MaaWin32InputMethod_Seize",
            "MaaWin32InputMethod_PostMessage",
            "MaaWin32InputMethod_SendMessageWithCursorPos",
        ]

        critical_defines = {}
        for name in critical_names:
            pattern = rf"#define\s+{re.escape(name)}\s+(.+)"
            match = re.search(pattern, content)
            if match:
                value = match.group(1).strip()
                critical_defines[name] = {"value": value}

        maa_def_baseline = {
            "_comment": "MAA Framework MaaDef.h 关键定义基线",
            "_version": "1.0",
            "_created": "auto-generated",
            "_source": str(FRAMEWORK_PATHS["maa_def_h"]),
            "critical_defines": critical_defines
        }

        with open(BASELINE_FILES["maa_def"], "w", encoding="utf-8") as f:
            json.dump(maa_def_baseline, f, indent=4, ensure_ascii=False)
        print(f"   已保存: {BASELINE_FILES['maa_def']}")
        print(f"   关键定义数量: {len(critical_defines)}")
    else:
        print(f"   跳过: 头文件不存在")

    # 3. 生成虚函数表基线
    print("\n[3/3] 生成虚函数表基线...")
    control_unit_path = PROJECT_ROOT / FRAMEWORK_PATHS["control_unit_h"]

    if control_unit_path.exists():
        with open(control_unit_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取 ControlUnitAPI 类的定义
        class_pattern = r"class\s+ControlUnitAPI\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}"
        class_match = re.search(class_pattern, content, re.DOTALL)

        if class_match:
            class_body = class_match.group(1)

            # 提取虚函数（包含完整签名）
            vtable = []
            seen = set()

            # 析构函数
            destructor_pattern = r"virtual\s+(~\w+)\s*\([^)]*\)"
            for match in re.finditer(destructor_pattern, class_body):
                name = match.group(1)
                full_sig = match.group(0).strip()
                if name not in seen:
                    vtable.append({
                        "index": len(vtable),
                        "name": name,
                        "signature": full_sig
                    })
                    seen.add(name)

            # 普通虚函数
            virtual_pattern = r"virtual\s+((?:\w+[\w\s\*&<>:]*)\s+(\w+)\s*\([^)]*\))"
            for match in re.finditer(virtual_pattern, class_body):
                full_sig = "virtual " + match.group(1).strip()
                name = match.group(2)
                if name not in seen:
                    vtable.append({
                        "index": len(vtable),
                        "name": name,
                        "signature": full_sig
                    })
                    seen.add(name)

            vtable_baseline = {
                "_comment": "MAA Framework Win32ControlUnitAPI 虚函数表基线",
                "_version": "1.0",
                "_created": "auto-generated",
                "_note": "虚函数顺序至关重要，任何变化都会破坏 ABI 兼容性",
                "class_name": "ControlUnitAPI",
                "vtable": vtable,
                "vtable_count": len(vtable)
            }

            with open(BASELINE_FILES["control_unit_api"], "w", encoding="utf-8") as f:
                json.dump(vtable_baseline, f, indent=4, ensure_ascii=False)
            print(f"   已保存: {BASELINE_FILES['control_unit_api']}")
            print(f"   虚函数数量: {len(vtable)}")
        else:
            print(f"   错误: 未找到 ControlUnitAPI 类定义")
            success = False
    else:
        print(f"   跳过: 头文件不存在")

    print("\n" + "=" * 60)
    if success:
        print("基线生成完成！")
    else:
        print("基线生成完成（部分失败）")

    return success


# ========== 输出格式化 ==========

def format_report(report: CompatReport, verbose: bool = False) -> str:
    """格式化报告输出"""
    lines = []
    lines.append("=" * 60)
    lines.append("MAA Framework 兼容性检测报告")
    lines.append("=" * 60)

    # 状态图标
    icons = {"ok": "[OK]", "warn": "[!!]", "error": "[XX]"}

    for result in report.results:
        icon = icons.get(result.status, "[??]")
        lines.append(f"\n{icon} {result.name}")
        lines.append(f"    {result.message}")

        if result.details:
            for detail in result.details:
                lines.append(f"      - {detail}")

    lines.append("\n" + "=" * 60)

    if report.compatible:
        lines.append("结论: 兼容 - Hook 方案应该可以正常工作")
    else:
        lines.append("结论: 不兼容 - 需要检查并适配框架变化")
        lines.append("")
        lines.append("建议操作:")
        lines.append("  1. 检查 MAA Framework 更新日志")
        lines.append("  2. 对比 ControlUnitAPI 类的变化")
        lines.append("  3. 更新 hook/proxy/control_unit.h")
        lines.append("  4. 重新编译并测试")
        lines.append("  5. 确认兼容后运行 --init 更新基线")

    return "\n".join(lines)


def format_json(report: CompatReport) -> str:
    """JSON 格式输出"""
    data = {
        "compatible": report.compatible,
        "framework_version": report.framework_version,
        "results": [
            {
                "name": r.name,
                "status": r.status,
                "message": r.message,
                "details": r.details
            }
            for r in report.results
        ]
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


# ========== 主函数 ==========

def main():
    parser = argparse.ArgumentParser(
        description="MAA Framework 兼容性检测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s              # 执行兼容性检测
  %(prog)s --init       # 生成基线（首次使用或确认兼容后）
  %(prog)s --verbose    # 显示详细信息
  %(prog)s --json       # JSON 格式输出

检测项目:
  - DLL 导出函数: 检测关键导出函数是否存在
  - 关键枚举定义: 检测 MaaWin32InputMethod_SendMessage 等值
  - 虚函数表: 检测 ControlUnitAPI 类的虚函数顺序（最关键）
        """
    )

    parser.add_argument("--init", action="store_true",
                        help="从当前框架生成基线")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="显示详细信息")
    parser.add_argument("-j", "--json", action="store_true",
                        help="JSON 格式输出")

    args = parser.parse_args()

    # 生成基线模式
    if args.init:
        success = init_baseline()
        sys.exit(0 if success else 1)

    # 检测模式
    results = []

    # 执行各项检测
    results.append(check_dll_exports(args.verbose))
    results.append(check_maa_def(args.verbose))
    results.append(check_vtable(args.verbose))
    results.append(check_header_hash(args.verbose))

    # 判断整体兼容性
    has_error = any(r.status == "error" for r in results)
    compatible = not has_error

    # 生成报告
    report = CompatReport(
        compatible=compatible,
        results=results
    )

    # 输出
    if args.json:
        print(format_json(report))
    else:
        print(format_report(report, args.verbose))

    # 返回码
    sys.exit(0 if compatible else 1)


if __name__ == "__main__":
    main()
