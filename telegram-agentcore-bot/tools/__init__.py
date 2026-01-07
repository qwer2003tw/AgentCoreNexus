"""
工具函數模組
提供所有可用的工具函數
"""

from .browser import browse_website_backup, browse_website_official
from .calculator import calculate
from .file_reader import read_file
from .time_utils import get_current_time
from .user_info import get_user_info
from .weather import get_weather

__all__ = [
    "get_weather",
    "calculate",
    "get_user_info",
    "get_current_time",
    "browse_website_official",
    "browse_website_backup",
    "read_file",
]

# 工具列表
AVAILABLE_TOOLS = [
    get_weather,
    calculate,
    get_user_info,
    get_current_time,
    browse_website_official,
    browse_website_backup,
    read_file,
]
