"""MSA Base 版打包脚本

职责：
- install_deps: MaaFramework 二进制 → install/runtimes/{tag}/native/
- install_resource: OCR 模型 + resource + interface.json（写入版本号）
- install_chores: README, LICENSE, requirements.txt
- install_agent: agent/ 目录 + 设置 child_exec 路径
- patch_interface_for_base: mouse → "Seize", keyboard → "Seize"

使用 jsonc 读取源 interface.json（含注释），用 json 写入（去除注释）。
"""

import json
import shutil
import sys
from pathlib import Path

try:
    import jsonc
except ModuleNotFoundError as e:
    raise ImportError(
        "缺少依赖 'json-with-comments' (imported as 'jsonc').\n"
        f"安装方式:\n  {sys.executable} -m pip install json-with-comments\n"
    ) from e

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INSTALL_PATH = PROJECT_ROOT / "install"


# ─── 平台标签 ───────────────────────────────────────────────

PLATFORM_MAP = {
    "win-x64": ("win", "x86_64"),
    "win-arm64": ("win", "aarch64"),
    "osx-x64": ("macos", "x86_64"),
    "osx-arm64": ("macos", "aarch64"),
    "linux-x64": ("linux", "x86_64"),
    "linux-arm64": ("linux", "aarch64"),
}


def parse_args():
    """解析命令行参数: version platform_tag"""
    if len(sys.argv) < 3:
        print("Usage: python install.py <version> <platform_tag>")
        print("Example: python install.py v0.5.0 win-x64")
        print(f"可用平台标签: {', '.join(PLATFORM_MAP.keys())}")
        sys.exit(1)

    version = sys.argv[1]
    platform_tag = sys.argv[2]

    if platform_tag not in PLATFORM_MAP:
        print(f"不支持的平台标签: {platform_tag}")
        print(f"可用标签: {', '.join(PLATFORM_MAP.keys())}")
        sys.exit(1)

    return version, platform_tag


def get_os_arch(platform_tag: str) -> tuple[str, str]:
    """从平台标签获取 os_name 和 arch"""
    return PLATFORM_MAP[platform_tag]


# ─── 安装函数 ───────────────────────────────────────────────

def install_deps(platform_tag: str):
    """安装 MaaFramework 二进制依赖"""
    deps_bin = PROJECT_ROOT / "deps" / "bin"
    if not deps_bin.exists():
        print('请先下载 MaaFramework 到 "deps" 目录。')
        sys.exit(1)

    os_name, _ = get_os_arch(platform_tag)

    if os_name == "android":
        shutil.copytree(deps_bin, INSTALL_PATH, dirs_exist_ok=True)
    else:
        shutil.copytree(
            deps_bin,
            INSTALL_PATH / "runtimes" / platform_tag / "native",
            ignore=shutil.ignore_patterns(
                "*MaaDbgControlUnit*",
                "*MaaThriftControlUnit*",
                "*MaaRpc*",
                "*MaaHttp*",
            ),
            dirs_exist_ok=True,
        )

    shutil.copytree(
        PROJECT_ROOT / "deps" / "share" / "MaaAgentBinary",
        INSTALL_PATH / "MaaAgentBinary",
        dirs_exist_ok=True,
    )
    print("MaaFramework 依赖安装完成")


def configure_ocr_model():
    """配置 OCR 模型"""
    assets_dir = PROJECT_ROOT / "assets"
    assets_ocr_dir = assets_dir / "MaaCommonAssets" / "OCR"
    if not assets_ocr_dir.exists():
        print(f"未找到 OCR 资源: {assets_ocr_dir}")
        sys.exit(1)

    ocr_dir = assets_dir / "resource" / "model" / "ocr"
    if not ocr_dir.exists():
        shutil.copytree(
            assets_ocr_dir / "ppocr_v5" / "zh_cn",
            ocr_dir,
            dirs_exist_ok=True,
        )
        print("OCR 模型配置完成")
    else:
        print("已存在 OCR 目录，跳过默认模型导入")


def install_resource(version: str, platform_tag: str):
    """安装资源文件和 interface.json"""
    configure_ocr_model()

    shutil.copytree(
        PROJECT_ROOT / "assets" / "resource",
        INSTALL_PATH / "resource",
        dirs_exist_ok=True,
    )

    # 使用 jsonc 读取（支持注释），用标准 json 写入（去除注释）
    src_interface = PROJECT_ROOT / "assets" / "interface.json"
    with open(src_interface, "r", encoding="utf-8") as f:
        interface = jsonc.load(f)

    interface["version"] = version

    # 非 Windows 平台修改 child_exec
    os_name, _ = get_os_arch(platform_tag)
    if os_name != "win":
        if "agent" in interface:
            interface["agent"]["child_exec"] = "python3"

    dst_interface = INSTALL_PATH / "interface.json"
    with open(dst_interface, "w", encoding="utf-8") as f:
        json.dump(interface, f, ensure_ascii=False, indent=4)

    print("资源文件安装完成")


def install_chores():
    """安装杂项文件"""
    for filename in ("README.md", "LICENSE"):
        src = PROJECT_ROOT / filename
        if src.exists():
            shutil.copy2(src, INSTALL_PATH)

    # 复制 requirements.txt 供 Agent 运行时依赖安装使用
    req_src = PROJECT_ROOT / "requirements.txt"
    if req_src.exists():
        shutil.copy2(req_src, INSTALL_PATH)

    print("杂项文件安装完成")


def install_agent(platform_tag: str):
    """安装 Python Agent"""
    shutil.copytree(
        PROJECT_ROOT / "agent",
        INSTALL_PATH / "agent",
        dirs_exist_ok=True,
    )

    # 设置 child_exec 路径（已在 install_resource 中处理 interface.json）
    print("Agent 安装完成")


def patch_interface_for_base():
    """Base 版补丁：将鼠标和键盘控制方式改为 Seize（前台独占）"""
    interface_path = INSTALL_PATH / "interface.json"
    if not interface_path.exists():
        print("警告：interface.json 不存在，跳过 Base 版补丁")
        return

    with open(interface_path, "r", encoding="utf-8") as f:
        interface = json.load(f)

    for controller in interface.get("controller", []):
        win32 = controller.get("win32", {})
        if win32:
            win32["mouse"] = "Seize"
            win32["keyboard"] = "Seize"

    with open(interface_path, "w", encoding="utf-8") as f:
        json.dump(interface, f, ensure_ascii=False, indent=4)

    print("Base 版补丁应用完成: mouse=Seize, keyboard=Seize")


# ─── 主流程 ─────────────────────────────────────────────────

if __name__ == "__main__":
    version, platform_tag = parse_args()

    install_deps(platform_tag)
    install_resource(version, platform_tag)
    install_chores()
    install_agent(platform_tag)
    patch_interface_for_base()

    print(f"\nBase 版打包完成: {INSTALL_PATH}")
