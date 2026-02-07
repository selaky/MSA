"""版本检查模块（骨架）

预留版本检查功能，mirrorchyan 未开通时返回占位结果。
"""

from utils.logger import logger


def check_resource_version(current_version: str) -> dict | None:
    """检查资源版本是否有更新

    Args:
        current_version: 当前版本号

    Returns:
        更新信息字典，无更新时返回 None
    """
    # TODO: mirrorchyan 开通后实现版本检查
    logger.debug(f"版本检查（预留）: 当前版本 {current_version}")
    return None
