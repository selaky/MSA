"""MSA Background 版打包脚本

在 Base 版基础上额外执行：
- install_hook_dlls: 重命名原版 DLL → 复制代理 DLL + Hook DLL
- 不调用 patch_interface_for_base()，保持 mouse="SendMessage"
"""

import json
import shutil
import sys
from pathlib import Path

# 导入 Base 版的公共函数
sys.path.insert(0, str(Path(__file__).parent))
from install import (
    PROJECT_ROOT,
    INSTALL_PATH,
    parse_args,
    get_os_arch,
    install_deps,
    install_resource,
    install_chores,
    install_agent,
)


def install_hook_dlls(platform_tag: str):
    """安装后台点击 Hook 相关 DLL

    处理逻辑：
    1. 将原版 MaaWin32ControlUnit.dll 重命名为 MaaWin32ControlUnit_original.dll
    2. 将 Proxy DLL (MaaWin32ControlUnit.dll) 复制到安装目录
    3. 复制 msa_hook.dll 到安装目录
    """
    os_name, _ = get_os_arch(platform_tag)
    if os_name != "win":
        print("后台点击功能仅支持 Windows，跳过 Hook DLL 安装")
        return

    native_dir = INSTALL_PATH / "runtimes" / platform_tag / "native"
    hook_build_dir = PROJECT_ROOT / "hook" / "build" / "bin" / "Release"

    proxy_dll = hook_build_dir / "MaaWin32ControlUnit.dll"
    hook_dll = hook_build_dir / "msa_hook.dll"

    if not proxy_dll.exists():
        print(f"警告：Proxy DLL 未找到: {proxy_dll}")
        print("跳过 Hook DLL 安装，请先执行 CMake 构建")
        return

    # 1. 重命名原版 DLL
    original_dll = native_dir / "MaaWin32ControlUnit.dll"
    renamed_dll = native_dir / "MaaWin32ControlUnit_original.dll"

    if original_dll.exists() and not renamed_dll.exists():
        print("重命名原版 MaaWin32ControlUnit.dll → MaaWin32ControlUnit_original.dll")
        shutil.move(str(original_dll), str(renamed_dll))
    elif not renamed_dll.exists():
        print("警告：原版 MaaWin32ControlUnit.dll 未找到")

    # 2. 复制 Proxy DLL
    print(f"安装 Proxy DLL: {proxy_dll.name}")
    shutil.copy2(proxy_dll, native_dir / "MaaWin32ControlUnit.dll")

    # 3. 复制 Hook DLL
    if hook_dll.exists():
        print(f"安装 Hook DLL: {hook_dll.name}")
        shutil.copy2(hook_dll, native_dir / "msa_hook.dll")
    else:
        print(f"警告：Hook DLL 未找到: {hook_dll}")

    print("Hook DLL 安装完成")


# ─── 主流程 ─────────────────────────────────────────────────

if __name__ == "__main__":
    version, platform_tag = parse_args()

    install_deps(platform_tag)
    install_resource(version, platform_tag)
    install_chores()
    install_agent(platform_tag)
    install_hook_dlls(platform_tag)
    # 注意：Background 版不调用 patch_interface_for_base()
    # 保持 mouse="SendMessage" 以支持后台点击

    print(f"\nBackground 版打包完成: {INSTALL_PATH}")
