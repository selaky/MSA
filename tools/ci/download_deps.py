"""Python 依赖下载脚本

职责：
- 自动检测平台标签（win_amd64 等）
- 读取项目根目录 requirements.txt
- pip download --platform <tag> --only-binary=:all: 下载 whl 到指定目录
- 平台特定下载失败时回退到通用策略
"""

import argparse
import subprocess
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_platform_tag(platform_tag: str) -> tuple[str, str]:
    """将 dotnet 风格的平台标签转换为 pip 平台标签和 Python 版本

    Args:
        platform_tag: 如 win-x64, win-arm64, osx-x64, osx-arm64, linux-x64, linux-arm64

    Returns:
        (pip_platform, python_version) 元组
    """
    tag_map = {
        "win-x64": "win_amd64",
        "win-arm64": "win_arm64",
        "osx-x64": "macosx_12_0_x86_64",
        "osx-arm64": "macosx_12_0_arm64",
        "linux-x64": "manylinux2014_x86_64",
        "linux-arm64": "manylinux2014_aarch64",
    }

    pip_platform = tag_map.get(platform_tag)
    if not pip_platform:
        print(f"不支持的平台标签: {platform_tag}")
        print(f"可用标签: {', '.join(tag_map.keys())}")
        sys.exit(1)

    return pip_platform, "312"


def download_deps(platform_tag: str, deps_dir: str):
    """下载依赖到指定目录

    Args:
        platform_tag: dotnet 风格平台标签
        deps_dir: 输出目录
    """
    deps_path = Path(deps_dir)
    deps_path.mkdir(parents=True, exist_ok=True)

    requirements_file = PROJECT_ROOT / "requirements.txt"
    if not requirements_file.exists():
        print(f"错误：未找到 {requirements_file}")
        sys.exit(1)

    pip_platform, python_version = get_platform_tag(platform_tag)

    # 读取依赖列表，区分纯 Python 包和平台特定包
    with open(requirements_file, "r", encoding="utf-8") as f:
        all_deps = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

    # 已知的纯 Python 包（不包含 native 代码）
    pure_python_packages = {"strenum", "MaaAgentBinary"}
    platform_packages = []
    pure_packages = []

    for dep in all_deps:
        dep_name = dep.split("==")[0].split(">=")[0].split("<=")[0].strip()
        if dep_name in pure_python_packages:
            pure_packages.append(dep)
        else:
            platform_packages.append(dep)

    # 下载纯 Python 包
    if pure_packages:
        print(f"正在下载纯 Python 包: {', '.join(pure_packages)}")
        cmd = [
            sys.executable, "-m", "pip", "download",
            "--no-deps",
            "-d", str(deps_path),
        ] + pure_packages
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print("警告：纯 Python 包下载失败，尝试通用策略")

    # 下载平台特定包
    if platform_packages:
        print(f"正在下载平台特定包 ({pip_platform}): {', '.join(platform_packages)}")
        cmd = [
            sys.executable, "-m", "pip", "download",
            "--no-deps",
            "--only-binary=:all:",
            "--platform", pip_platform,
            "--python-version", python_version,
            "-d", str(deps_path),
        ] + platform_packages
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print("平台特定下载失败，回退到通用策略...")
            cmd_fallback = [
                sys.executable, "-m", "pip", "download",
                "--no-deps",
                "-d", str(deps_path),
            ] + platform_packages
            subprocess.run(cmd_fallback, check=True)

    print(f"依赖下载完成: {deps_path}")
    # 列出下载的文件
    for f in sorted(deps_path.iterdir()):
        print(f"  {f.name}")


def main():
    parser = argparse.ArgumentParser(description="下载 Python 依赖")
    parser.add_argument(
        "platform_tag",
        help="平台标签，如 win-x64, osx-arm64, linux-x64",
    )
    parser.add_argument(
        "--deps-dir",
        default="install/deps",
        help="依赖输出目录（默认: install/deps）",
    )
    args = parser.parse_args()

    download_deps(args.platform_tag, args.deps_dir)


if __name__ == "__main__":
    main()
