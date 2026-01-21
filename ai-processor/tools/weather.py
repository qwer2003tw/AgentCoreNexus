"""
天氣查詢工具
"""

from strands import tool

from utils.logger import get_logger

logger = get_logger(__name__)


@tool
def get_weather(city: str) -> str:
    """
    取得城市天氣資訊

    Args:
        city: 城市名稱

    Returns:
        天氣資訊字串
    """
    logger.info(f"查詢天氣: {city}")

    # 模擬天氣資料（實際應用中應連接真實的天氣 API）
    weather_data = {
        "台北": "晴天，溫度 25°C",
        "台中": "多雲，溫度 23°C",
        "高雄": "晴天，溫度 28°C",
        "新北": "陰天，溫度 24°C",
        "桃園": "晴天，溫度 24°C",
        "台南": "晴天，溫度 27°C",
    }

    # 取得天氣資訊或返回預設訊息
    weather_info = weather_data.get(city, f"{city} 的天氣資訊尚未提供")

    logger.info(f"天氣結果: {weather_info}")
    return weather_info
