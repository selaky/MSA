import sys
import os
import json
import subprocess

# 将脚本所在目录添加到模块搜索路径，确保能找到同目录下的模块
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils.logger import logger


# ─── 版本与模式检测 ──────────────────────────────────────────

def read_interface_version() -> str:
    """读取 interface.json 中的版本号，判断是否为开发模式

    - ./interface.json 存在 → 读取其 version 字段
    - ./interface.json 不存在但 ./assets/interface.json 存在 → 返回 "DEBUG"（开发模式）
    - 都不存在 → 返回 "UNKNOWN"
    """
    interface_path = os.path.join(os.getcwd(), "interface.json")
    assets_interface_path = os.path.join(os.getcwd(), "assets", "interface.json")

    if os.path.exists(interface_path):
        try:
            with open(interface_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("version", "UNKNOWN")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"读取 interface.json 失败: {e}")
            return "UNKNOWN"
    elif os.path.exists(assets_interface_path):
        return "DEBUG"
    else:
        return "UNKNOWN"


# ─── 配置读取 ────────────────────────────────────────────────

def read_config(config_name: str, defaults: dict) -> dict:
    """通用配置读取，首次运行自动创建默认配置

    Args:
        config_name: 配置文件名（不含路径），如 "pip_config.json"
        defaults: 默认配置字典

    Returns:
        配置字典
    """
    config_dir = os.path.join(os.getcwd(), "config")
    config_path = os.path.join(config_dir, config_name)

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"读取配置 {config_name} 失败: {e}，使用默认值")
            return defaults

    # 首次运行，创建默认配置
    os.makedirs(config_dir, exist_ok=True)
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(defaults, f, ensure_ascii=False, indent=4)
        logger.info(f"已创建默认配置: {config_path}")
    except OSError as e:
        logger.warning(f"创建默认配置失败: {e}")

    return defaults


# ─── 虚拟环境管理 ─────────────────────────────────────────────

def ensure_venv_and_relaunch_if_needed():
    """Linux/开发模式：创建 .venv 并在 venv 内重启自身

    仅在以下条件同时满足时执行：
    1. 当前不在虚拟环境中
    2. 系统不是 Windows（Windows 使用嵌入式 Python）
    """
    # Windows 使用嵌入式 Python，不需要 venv
    if sys.platform == "win32":
        return

    # 已在虚拟环境中
    if sys.prefix != sys.base_prefix:
        return

    venv_dir = os.path.join(os.getcwd(), ".venv")
    venv_python = os.path.join(venv_dir, "bin", "python3")

    if not os.path.exists(venv_dir):
        logger.info("正在创建虚拟环境...")
        subprocess.run(
            [sys.executable, "-m", "venv", venv_dir],
            check=True,
        )

    if os.path.exists(venv_python):
        logger.info("在虚拟环境中重新启动...")
        os.execv(venv_python, [venv_python] + sys.argv)


# ─── 依赖安装 ─────────────────────────────────────────────────

def check_and_install_dependencies():
    """三级回退依赖安装

    1. 检查 deps/*.whl 是否存在 → pip install --find-links deps/ --no-index
    2. 失败 → 读取 pip_config.json 获取镜像源 → pip install -i <主源> --extra-index-url <备源>
    3. 失败 → pip install -r requirements.txt（使用系统 pip 配置）
    """
    requirements_file = os.path.join(os.getcwd(), "requirements.txt")
    if not os.path.exists(requirements_file):
        logger.debug("未找到 requirements.txt，跳过依赖检查")
        return

    # 快速检查：尝试导入关键依赖
    try:
        import maa  # noqa: F401
        import numpy  # noqa: F401
        logger.debug("核心依赖已就绪")
        return
    except ImportError:
        logger.info("检测到缺失依赖，开始安装...")

    pip_config = read_config("pip_config.json", {
        "enable_pip_install": True,
        "mirror": "https://pypi.tuna.tsinghua.edu.cn/simple",
        "backup_mirror": "https://mirrors.ustc.edu.cn/pypi/simple",
    })

    if not pip_config.get("enable_pip_install", True):
        logger.warning("pip 安装已被禁用（pip_config.json），跳过依赖安装")
        return

    # 策略1：从本地 whl 安装
    deps_dir = os.path.join(os.getcwd(), "deps")
    if os.path.isdir(deps_dir) and any(
        f.endswith(".whl") for f in os.listdir(deps_dir)
    ):
        logger.info("尝试从本地 whl 安装依赖...")
        result = subprocess.run(
            [
                sys.executable, "-m", "pip", "install",
                "--find-links", deps_dir,
                "--no-index",
                "-r", requirements_file,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            logger.info("从本地 whl 安装依赖成功")
            return
        logger.warning(f"本地 whl 安装失败: {result.stderr.strip()}")

    # 策略2：使用镜像源安装
    mirror = pip_config.get("mirror", "")
    backup_mirror = pip_config.get("backup_mirror", "")
    if mirror:
        logger.info(f"尝试使用镜像源安装依赖: {mirror}")
        cmd = [
            sys.executable, "-m", "pip", "install",
            "-i", mirror,
            "-r", requirements_file,
        ]
        if backup_mirror:
            cmd.extend(["--extra-index-url", backup_mirror])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("使用镜像源安装依赖成功")
            return
        logger.warning(f"镜像源安装失败: {result.stderr.strip()}")

    # 策略3：使用系统 pip 配置
    logger.info("尝试使用系统 pip 配置安装依赖...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", requirements_file],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        logger.info("使用系统 pip 安装依赖成功")
        return

    logger.error(f"所有依赖安装策略均失败: {result.stderr.strip()}")
    logger.error("请手动安装依赖: pip install -r requirements.txt")


# ─── Agent 启动 ────────────────────────────────────────────────

def agent(is_dev_mode: bool):
    """启动 Agent 服务

    Args:
        is_dev_mode: 是否为开发模式
    """
    if not is_dev_mode:
        # 预留：版本检查
        try:
            from utils.version_checker import check_resource_version
            check_resource_version(read_interface_version())
        except Exception as e:
            logger.debug(f"版本检查跳过: {e}")

        # 预留：热更新
        try:
            hot_update_config = read_config("hot_update.json", {
                "enable_hot_update": True,
            })
            if hot_update_config.get("enable_hot_update", True):
                from utils.resource_updater import hot_update
                hot_update()
        except Exception as e:
            logger.debug(f"热更新跳过: {e}")

    # 延迟导入所有业务模块
    from maa.agent.agent_server import AgentServer
    from maa.toolkit import Toolkit

    from recover import recover_action  # noqa: F401
    from recover import recover_reco  # noqa: F401
    from arena import arena_action  # noqa: F401
    from arena import arena_reco  # noqa: F401
    from boss import boss_action  # noqa: F401
    from boss import boss_reco  # noqa: F401
    from utils import common_action  # noqa: F401
    from utils import common_reco  # noqa: F401
    from battle import battle_action, battle_reco  # noqa: F401
    from lab import lab_action, lab_reco  # noqa: F401

    Toolkit.init_option("./")

    if len(sys.argv) < 2:
        print("Usage: python main.py <socket_id>")
        print("socket_id is provided by AgentIdentifier.")
        sys.exit(1)

    socket_id = sys.argv[-1]

    AgentServer.start_up(socket_id)
    AgentServer.join()
    AgentServer.shut_down()


# ─── 主入口 ──────────────────────────────────────────────────

def main():
    version = read_interface_version()
    is_dev_mode = version == "DEBUG"

    if is_dev_mode:
        logger.info("开发模式启动")
    else:
        logger.info(f"MSA Agent v{version}")

    ensure_venv_and_relaunch_if_needed()
    check_and_install_dependencies()
    agent(is_dev_mode)


if __name__ == "__main__":
    main()
