from pathlib import Path

import shutil
import sys

try:
    import jsonc
except ModuleNotFoundError as e:
    raise ImportError(
        "Missing dependency 'json-with-comments' (imported as 'jsonc').\n"
        f"Install it with:\n  {sys.executable} -m pip install json-with-comments\n"
        "Or add it to your project's requirements."
    ) from e

from configure import configure_ocr_model


working_dir = Path(__file__).parent.parent.resolve()
install_path = working_dir / Path("install")
version = len(sys.argv) > 1 and sys.argv[1] or "v0.0.1"

# the first parameter is self name
if sys.argv.__len__() < 4:
    print("Usage: python install.py <version> <os> <arch>")
    print("Example: python install.py v1.0.0 win x86_64")
    sys.exit(1)

os_name = sys.argv[2]
arch = sys.argv[3]


def get_dotnet_platform_tag():
    """自动检测当前平台并返回对应的dotnet平台标签"""
    if os_name == "win" and arch == "x86_64":
        platform_tag = "win-x64"
    elif os_name == "win" and arch == "aarch64":
        platform_tag = "win-arm64"
    elif os_name == "macos" and arch == "x86_64":
        platform_tag = "osx-x64"
    elif os_name == "macos" and arch == "aarch64":
        platform_tag = "osx-arm64"
    elif os_name == "linux" and arch == "x86_64":
        platform_tag = "linux-x64"
    elif os_name == "linux" and arch == "aarch64":
        platform_tag = "linux-arm64"
    else:
        print("Unsupported OS or architecture.")
        print("available parameters:")
        print("version: e.g., v1.0.0")
        print("os: [win, macos, linux, android]")
        print("arch: [aarch64, x86_64]")
        sys.exit(1)

    return platform_tag


def install_deps():
    if not (working_dir / "deps" / "bin").exists():
        print('Please download the MaaFramework to "deps" first.')
        print('请先下载 MaaFramework 到 "deps"。')
        sys.exit(1)

    if os_name == "android":
        shutil.copytree(
            working_dir / "deps" / "bin",
            install_path,
            dirs_exist_ok=True,
        )
    else:
        shutil.copytree(
            working_dir / "deps" / "bin",
            install_path / "runtimes" / get_dotnet_platform_tag() / "native",
            ignore=shutil.ignore_patterns(
                "*MaaDbgControlUnit*",
                "*MaaThriftControlUnit*",
                "*MaaRpc*",
                "*MaaHttp*",
            ),
            dirs_exist_ok=True,
        )

    shutil.copytree(
        working_dir / "deps" / "share" / "MaaAgentBinary",
        install_path / "MaaAgentBinary",
        dirs_exist_ok=True,
    )


def install_hook_dlls():
    """安装后台点击 Hook 相关 DLL

    处理逻辑：
    1. 将原版 MaaWin32ControlUnit.dll 重命名为 MaaWin32ControlUnit_original.dll
    2. 将 Proxy DLL (MaaWin32ControlUnit.dll) 复制到安装目录
    3. 复制 msa_hook.dll 到安装目录
    """
    if os_name != "win":
        # 后台点击功能仅支持 Windows
        return

    native_dir = install_path / "runtimes" / get_dotnet_platform_tag() / "native"
    hook_build_dir = working_dir / "hook" / "build" / "bin" / "Release"

    # 检查构建产物是否存在
    proxy_dll = hook_build_dir / "MaaWin32ControlUnit.dll"
    hook_dll = hook_build_dir / "msa_hook.dll"

    if not proxy_dll.exists():
        print(f"Warning: Proxy DLL not found at {proxy_dll}")
        print("Skipping hook DLL installation. Run CMake build first.")
        return

    # 1. 重命名原版 DLL（如果尚未重命名）
    original_dll = native_dir / "MaaWin32ControlUnit.dll"
    renamed_dll = native_dir / "MaaWin32ControlUnit_original.dll"

    if original_dll.exists() and not renamed_dll.exists():
        print("Renaming original MaaWin32ControlUnit.dll to MaaWin32ControlUnit_original.dll")
        shutil.move(str(original_dll), str(renamed_dll))
    elif not renamed_dll.exists():
        print("Warning: Original MaaWin32ControlUnit.dll not found")

    # 2. 复制 Proxy DLL
    print(f"Installing Proxy DLL: {proxy_dll.name}")
    shutil.copy2(proxy_dll, native_dir / "MaaWin32ControlUnit.dll")

    # 3. 复制 Hook DLL
    if hook_dll.exists():
        print(f"Installing Hook DLL: {hook_dll.name}")
        shutil.copy2(hook_dll, native_dir / "msa_hook.dll")
    else:
        print(f"Warning: Hook DLL not found at {hook_dll}")

    print("Hook DLLs installed successfully.")


def install_resource():

    configure_ocr_model()

    shutil.copytree(
        working_dir / "assets" / "resource",
        install_path / "resource",
        dirs_exist_ok=True,
    )
    shutil.copy2(
        working_dir / "assets" / "interface.json",
        install_path,
    )

    with open(install_path / "interface.json", "r", encoding="utf-8") as f:
        interface = jsonc.load(f)

    interface["version"] = version

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        jsonc.dump(interface, f, ensure_ascii=False, indent=4)


def install_chores():
    shutil.copy2(
        working_dir / "README.md",
        install_path,
    )
    shutil.copy2(
        working_dir / "LICENSE",
        install_path,
    )


def install_agent():
    shutil.copytree(
        working_dir / "agent",
        install_path / "agent",
        dirs_exist_ok=True,
    )


if __name__ == "__main__":
    install_deps()
    install_resource()
    install_chores()
    install_agent()
    install_hook_dlls()

    print(f"Install to {install_path} successfully.")
