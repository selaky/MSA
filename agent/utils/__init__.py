# 通用工具模块

from .logger import logger

try:
    from .version_checker import check_resource_version
except ImportError:
    pass
