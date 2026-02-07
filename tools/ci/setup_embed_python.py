"""嵌入式 Python 环境配置脚本

职责：
- Windows：下载官方 embed zip → 解压 → 修改 ._pth → 安装 pip
- macOS：下载 python-build-standalone → 解压 → 设置执行权限 → 安装 pip
- 输出到 install/python/
"""

import os
import sys
import platform
import urllib.request
import zipfile
import tarfile
import subprocess
from pathlib import Path

PYTHON_VERSION = "3.12.8"
PYTHON_STANDALONE_TAG = "20241219"


def get_install_dir():
    """获取安装目录"""
    return Path(__file__).resolve().parent.parent.parent / "install" / "python"


def setup_windows_embed(arch: str = "amd64"):
    """配置 Windows 嵌入式 Python

    Args:
        arch: 架构，amd64 或 arm64
    """
    install_dir = get_install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)

    url = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-{arch}.zip"
    zip_path = install_dir.parent / "python-embed.zip"

    print(f"正在下载 Windows 嵌入式 Python: {url}")
    urllib.request.urlretrieve(url, zip_path)

    print(f"正在解压到: {install_dir}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(install_dir)
    zip_path.unlink()

    # 修改 ._pth 文件
    pth_files = list(install_dir.glob("python*._pth"))
    if not pth_files:
        print("错误：未找到 ._pth 文件")
        sys.exit(1)

    pth_file = pth_files[0]
    pth_name = pth_file.stem  # e.g. python312
    print(f"正在配置 {pth_file.name}")

    pth_file.write_text(
        f"{pth_name}.zip\n"
        ".\n"
        "Lib\n"
        "Lib\\site-packages\n"
        "DLLs\n"
        "\n"
        "import site\n",
        encoding="utf-8",
    )

    # 安装 pip
    print("正在安装 pip...")
    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
    get_pip_path = install_dir / "get-pip.py"
    urllib.request.urlretrieve(get_pip_url, get_pip_path)

    python_exe = install_dir / "python.exe"
    subprocess.run(
        [str(python_exe), str(get_pip_path), "--no-warn-script-location"],
        check=True,
    )
    get_pip_path.unlink()

    print("Windows 嵌入式 Python 配置完成")


def setup_macos_standalone(arch: str = "x86_64"):
    """配置 macOS python-build-standalone

    Args:
        arch: 架构，x86_64 或 aarch64
    """
    install_dir = get_install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)

    url = (
        f"https://github.com/indygreg/python-build-standalone/releases/download/"
        f"{PYTHON_STANDALONE_TAG}/cpython-{PYTHON_VERSION}+{PYTHON_STANDALONE_TAG}-"
        f"{arch}-apple-darwin-install_only.tar.gz"
    )
    tar_path = install_dir.parent / "python-standalone.tar.gz"

    print(f"正在下载 macOS Python: {url}")
    urllib.request.urlretrieve(url, tar_path)

    print(f"正在解压到: {install_dir}")
    with tarfile.open(tar_path, "r:gz") as tf:
        tf.extractall(install_dir.parent)
    tar_path.unlink()

    # python-build-standalone 解压后目录名为 python
    extracted = install_dir.parent / "python"
    if extracted.exists() and extracted != install_dir:
        if install_dir.exists():
            import shutil
            shutil.rmtree(install_dir)
        extracted.rename(install_dir)

    # 设置执行权限
    python_bin = install_dir / "bin" / "python3"
    if python_bin.exists():
        os.chmod(python_bin, 0o755)

    # 安装 pip
    print("正在安装 pip...")
    python_exe = install_dir / "bin" / "python3"
    subprocess.run(
        [str(python_exe), "-m", "ensurepip", "--upgrade"],
        check=True,
    )

    print("macOS Python 配置完成")


def main():
    current_os = platform.system().lower()

    # 支持通过命令行参数指定架构
    arch = None
    if len(sys.argv) > 1:
        arch = sys.argv[1]

    if current_os == "windows":
        if arch is None:
            machine = platform.machine().lower()
            arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
        setup_windows_embed(arch)
    elif current_os == "darwin":
        if arch is None:
            machine = platform.machine().lower()
            arch = "aarch64" if machine == "arm64" else "x86_64"
        setup_macos_standalone(arch)
    else:
        print(f"不支持的操作系统: {current_os}")
        print("Linux 平台请使用系统 Python")
        sys.exit(1)


if __name__ == "__main__":
    main()
