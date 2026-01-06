"""
工具函數模組
提供所有可用的工具函數
"""
from .weather import get_weather
from .calculator import calculate
from .user_info import get_user_info
from .time_utils import get_current_time
from .browser import browse_website_official, browse_website_backup

__all__ = [
    'get_weather',
    'calculate', 
    'get_user_info',
    'get_current_time',
    'browse_website_official',
    'browse_website_backup'
]

# 工具列表
AVAILABLE_TOOLS = [
    get_weather,
    calculate,
    get_user_info,
    get_current_time,
    browse_website_official,
    browse_website_backup
]
