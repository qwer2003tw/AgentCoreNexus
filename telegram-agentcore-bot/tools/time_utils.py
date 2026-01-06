"""
時間相關工具
提供時間查詢和格式化功能
"""
from datetime import datetime
from strands import tool
from utils.logger import get_logger

logger = get_logger(__name__)

@tool
def get_current_time() -> str:
    """
    取得目前台北時間
    
    Returns:
        格式化的時間字串
    """
    logger.info("查詢目前時間")
    
    try:
        # 嘗試使用 pytz 取得準確的時區時間
        import pytz
        tz = pytz.timezone('Asia/Taipei')
        current_time = datetime.now(tz)
        time_str = current_time.strftime("目前時間: %Y-%m-%d %H:%M:%S (台北時間)")
        logger.info(f"時間查詢成功: {time_str}")
        return time_str
        
    except ImportError:
        # 如果沒有安裝 pytz，使用系統時間
        logger.warning("pytz 未安裝，使用系統時間")
        current_time = datetime.now()
        time_str = current_time.strftime("目前時間: %Y-%m-%d %H:%M:%S")
        return time_str
        
    except Exception as e:
        logger.error(f"取得時間失敗: {str(e)}", exc_info=True)
        return f"無法取得目前時間: {str(e)}"

def format_timestamp(timestamp: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化時間戳記
    
    Args:
        timestamp: datetime 物件
        format_str: 格式化字串
    
    Returns:
        格式化後的時間字串
    """
    try:
        return timestamp.strftime(format_str)
    except Exception as e:
        logger.error(f"時間格式化失敗: {str(e)}")
        return str(timestamp)
