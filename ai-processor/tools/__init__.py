"""
工具函數模組
提供所有可用的工具函數
"""

from .browser import browse_website_backup, browse_website_official
from .calculator import calculate
from .file_analysis import analyze_file_tool
from .file_reader import read_file
from .image_analysis import analyze_image_tool
from .time_utils import get_current_time
from .weather import get_weather

__all__ = [
    "get_weather",
    "calculate",
    "get_current_time",
    "browse_website_official",
    "browse_website_backup",
    "read_file",
    "analyze_image_tool",
    "analyze_file_tool",
]

# 工具列表
AVAILABLE_TOOLS = [
    get_weather,
    calculate,
    get_current_time,
    browse_website_official,
    browse_website_backup,
    read_file,
    analyze_image_tool,
    analyze_file_tool,
]
