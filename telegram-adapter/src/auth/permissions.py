"""
Permissions Module - 權限等級定義和檢查邏輯
"""

from enum import IntEnum

from allowlist import check_allowed

from utils.logger import get_logger

logger = get_logger(__name__)


class Permission(IntEnum):
    """
    權限等級定義
    數值越大權限越高，高權限包含低權限
    """

    NONE = 0  # 無需驗證
    ALLOWLIST = 1  # 需要在 allowlist
    ADMIN = 2  # 需要 admin 權限


class UserRole:
    """用戶角色常數"""

    USER = "user"  # 一般用戶
    ADMIN = "admin"  # 管理員


def check_permission(chat_id: int, username: str, required: Permission) -> bool:
    """
    檢查用戶權限

    Args:
        chat_id: Telegram chat ID
        username: Telegram username
        required: 需要的權限等級

    Returns:
        bool: True 如果權限足夠
    """
    if required == Permission.NONE:
        logger.debug(
            "Permission check: NONE - always granted",
            extra={
                "chat_id": chat_id,
                "username": username,
                "required_permission": "NONE",
                "event_type": "permission_check",
            },
        )
        return True

    # 檢查 admin 權限（admin 包含所有權限）
    from auth.admin_list import is_admin

    if is_admin(chat_id, username):
        logger.info(
            "Permission check: granted (admin)",
            extra={
                "chat_id": chat_id,
                "username": username,
                "required_permission": required.name,
                "actual_role": "admin",
                "event_type": "permission_granted",
            },
        )
        return True

    # 檢查 allowlist 權限
    if required == Permission.ALLOWLIST:
        allowed = check_allowed(chat_id, username)

        if allowed:
            logger.info(
                "Permission check: granted (allowlist)",
                extra={
                    "chat_id": chat_id,
                    "username": username,
                    "required_permission": "ALLOWLIST",
                    "actual_role": "user",
                    "event_type": "permission_granted",
                },
            )
        else:
            logger.warning(
                "Permission check: denied (not in allowlist)",
                extra={
                    "chat_id": chat_id,
                    "username": username,
                    "required_permission": "ALLOWLIST",
                    "event_type": "permission_denied",
                },
            )

        return allowed

    # 需要 admin 但不是 admin
    logger.warning(
        "Permission check: denied (requires admin)",
        extra={
            "chat_id": chat_id,
            "username": username,
            "required_permission": "ADMIN",
            "event_type": "permission_denied",
        },
    )
    return False


def get_permission_level(role: str) -> Permission:
    """
    根據角色取得權限等級

    Args:
        role: 用戶角色 ('user' 或 'admin')

    Returns:
        Permission: 對應的權限等級
    """
    if role == UserRole.ADMIN:
        return Permission.ADMIN
    elif role == UserRole.USER:
        return Permission.ALLOWLIST
    else:
        return Permission.NONE
