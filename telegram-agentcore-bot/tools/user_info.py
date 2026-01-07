"""
用戶資訊工具
查詢和管理用戶相關資訊
"""

import json
from datetime import date, datetime

from strands import tool

from utils.logger import get_logger

logger = get_logger(__name__)


@tool
def get_user_info(user_id: str) -> str:
    """
    取得用戶資訊

    Args:
        user_id: 用戶 ID

    Returns:
        用戶資訊的 JSON 字串
    """
    logger.info(f"查詢用戶資訊: {user_id}")

    try:
        # 建立用戶資訊（實際應用中應從資料庫或 API 取得）
        user_info = {
            "user_id": user_id,
            "status": "active",
            "joined_date": str(date.today()),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "preferences": {"language": "zh-TW", "timezone": "Asia/Taipei"},
        }

        # 返回 JSON 格式的用戶資訊
        result = json.dumps(user_info, ensure_ascii=False, indent=2)
        logger.info(f"成功取得用戶資訊: {user_id}")
        return result

    except Exception as e:
        logger.error(f"取得用戶資訊失敗: {str(e)}", exc_info=True)
        return json.dumps(
            {"error": f"無法取得用戶資訊: {str(e)}", "user_id": user_id}, ensure_ascii=False
        )
