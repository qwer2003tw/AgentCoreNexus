"""
安全工具模組
提供 Actor ID 雜湊和其他安全功能
"""

import hashlib
import hmac
import os

from utils.logger import get_logger

logger = get_logger(__name__)


def get_secret_key() -> str:
    """
    取得 Actor ID 雜湊用的密鑰

    Returns:
        密鑰字串
    """
    key = os.getenv("MEMORY_ACTOR_SECRET")

    if not key:
        logger.warning(
            "⚠️ MEMORY_ACTOR_SECRET not set, using default (NOT SECURE for production)",
            extra={"event_type": "security_warning"},
        )
        # 預設值（僅用於開發，不應在生產環境使用）
        key = "default-secret-change-me-in-production"

    return key


def secure_actor_id(user_id: str) -> str:
    """
    生成安全的 actor_id（使用 HMAC-SHA256）

    這個函數將原始 user_id 轉換為不可逆的雜湊值，
    防止 actor_id 被猜測，增強用戶隔離安全性。

    Args:
        user_id: 原始用戶 ID (例如: "tg:316743844")

    Returns:
        雜湊後的 actor_id (例如: "actor-f3a8b2c1d4e5f6g7")

    Examples:
        >>> secure_actor_id("tg:316743844")
        "actor-f3a8b2c1d4e5f6g7"

        >>> secure_actor_id("tg:999888777")
        "actor-a1b2c3d4e5f6g7h8"

    Note:
        - 使用 HMAC-SHA256 確保安全性
        - 相同的 user_id 總是產生相同的 actor_id（確定性）
        - 不同的 SECRET_KEY 會產生不同的結果
        - 雜湊值不可逆，無法從 actor_id 還原 user_id
    """
    secret_key = get_secret_key()

    # 使用 HMAC-SHA256 生成雜湊
    hmac_hash = hmac.new(
        secret_key.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    # 取前 16 位，添加 "actor-" 前綴
    # 格式：actor-XXXXXXXXXXXXXXXX
    secure_id = f"actor-{hmac_hash[:16]}"

    logger.debug(
        "Generated secure actor_id",
        extra={
            "original_id_hash": hashlib.sha256(user_id.encode()).hexdigest()[:8],
            "secure_id": secure_id,
            "event_type": "actor_id_generated",
        },
    )

    return secure_id


def hash_sensitive_data(data: str, length: int = 8) -> str:
    """
    雜湊敏感資料（用於日誌記錄）

    Args:
        data: 要雜湊的資料
        length: 雜湊值長度（預設 8）

    Returns:
        雜湊值的前 N 位

    Example:
        >>> hash_sensitive_data("user@example.com")
        "a1b2c3d4"
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:length]


def validate_user_id(user_id: str) -> bool:
    """
    驗證 user_id 格式是否有效

    Args:
        user_id: 用戶 ID

    Returns:
        是否有效
    """
    if not user_id or user_id == "unknown":
        return False

    # 檢查格式（應該是 "tg:數字" 或 "數字"）
    if user_id.startswith("tg:"):
        try:
            int(user_id[3:])
            return True
        except ValueError:
            return False

    try:
        int(user_id)
        return True
    except ValueError:
        return False
