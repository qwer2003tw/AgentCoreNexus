"""
Allowlist Module - DynamoDB 允許名單驗證
"""

import os

import boto3
from botocore.exceptions import ClientError

from utils.logger import get_logger

logger = get_logger(__name__)

# 初始化 DynamoDB 客戶端
dynamodb = boto3.resource("dynamodb")
table_name = os.environ.get("ALLOWLIST_TABLE_NAME", "telegram-allowlist")
table = dynamodb.Table(table_name)


def check_allowed(chat_id: int, username: str = "") -> bool:
    """
    檢查用戶是否在允許名單中

    Args:
        chat_id: Telegram chat ID
        username: Telegram username (可選)

    Returns:
        bool: True 如果允許，False 如果拒絕
    """
    try:
        # 查詢 DynamoDB
        response = table.get_item(Key={"chat_id": chat_id})

        # 檢查是否存在記錄
        if "Item" not in response:
            logger.info(
                "Chat ID not found in allowlist",
                extra={"chat_id": chat_id, "username": username, "event_type": "allowlist_miss"},
            )
            return False

        item = response["Item"]

        # 檢查 enabled 狀態
        if not item.get("enabled", False):
            logger.warning(
                "Chat ID is disabled",
                extra={
                    "chat_id": chat_id,
                    "username": username,
                    "event_type": "allowlist_disabled",
                },
            )
            return False

        # 如果提供了 username，進行額外驗證
        stored_username = item.get("username", "")
        if username and stored_username and username != stored_username:
            logger.warning(
                "Username mismatch",
                extra={
                    "chat_id": chat_id,
                    "provided_username": username,
                    "stored_username": stored_username,
                    "event_type": "username_mismatch",
                },
            )
            return False

        logger.info(
            "Access granted",
            extra={"chat_id": chat_id, "username": username, "event_type": "allowlist_hit"},
        )
        return True

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(
            f"DynamoDB error: {error_code}",
            extra={"chat_id": chat_id, "error": str(e), "event_type": "dynamodb_error"},
            exc_info=True,
        )
        # 發生錯誤時預設拒絕訪問
        return False

    except Exception as e:
        logger.error(
            f"Unexpected error in allowlist check: {str(e)}",
            extra={"chat_id": chat_id, "event_type": "allowlist_error"},
            exc_info=True,
        )
        return False


def add_to_allowlist(chat_id: int, username: str, enabled: bool = True) -> bool:
    """
    新增用戶到允許名單 (輔助函數，非 Lambda 主流程使用)

    Args:
        chat_id: Telegram chat ID
        username: Telegram username
        enabled: 是否啟用

    Returns:
        bool: True 如果成功
    """
    try:
        table.put_item(Item={"chat_id": chat_id, "username": username, "enabled": enabled})
        logger.info(
            "Added to allowlist",
            extra={
                "chat_id": chat_id,
                "username": username,
                "enabled": enabled,
                "event_type": "allowlist_add",
            },
        )
        return True

    except ClientError as e:
        logger.error(f"Failed to add to allowlist: {str(e)}", exc_info=True)
        return False


def remove_from_allowlist(chat_id: int) -> bool:
    """
    從允許名單中移除用戶 (輔助函數)

    Args:
        chat_id: Telegram chat ID

    Returns:
        bool: True 如果成功
    """
    try:
        table.delete_item(Key={"chat_id": chat_id})
        logger.info(
            "Removed from allowlist", extra={"chat_id": chat_id, "event_type": "allowlist_remove"}
        )
        return True

    except ClientError as e:
        logger.error(f"Failed to remove from allowlist: {str(e)}", exc_info=True)
        return False


def get_user_info(chat_id: int) -> dict | None:
    """
    獲取用戶詳細信息

    Args:
        chat_id: Telegram chat ID

    Returns:
        dict: 用戶信息，或 None 如果不存在
    """
    try:
        response = table.get_item(Key={"chat_id": chat_id})
        return response.get("Item")
    except ClientError as e:
        logger.error(f"Failed to get user info: {str(e)}", exc_info=True)
        return None


def list_all_users(limit: int = 50) -> list:
    """
    列出所有用戶

    Args:
        limit: 最大返回數量

    Returns:
        list: 用戶列表
    """
    try:
        response = table.scan(Limit=limit)
        items = response.get("Items", [])

        # 按 chat_id 排序（群組在前，負數）
        items.sort(key=lambda x: x.get("chat_id", 0))

        return items
    except ClientError as e:
        logger.error(f"Failed to list users: {str(e)}", exc_info=True)
        return []


def update_user_enabled(chat_id: int, enabled: bool) -> bool:
    """
    啟用/禁用用戶

    Args:
        chat_id: Telegram chat ID
        enabled: True 啟用，False 禁用

    Returns:
        bool: True 如果成功
    """
    try:
        table.update_item(
            Key={"chat_id": chat_id},
            UpdateExpression="SET enabled = :enabled",
            ExpressionAttributeValues={":enabled": enabled},
        )
        logger.info(
            f"User {'enabled' if enabled else 'disabled'}",
            extra={"chat_id": chat_id, "enabled": enabled, "event_type": "user_status_updated"},
        )
        return True
    except ClientError as e:
        logger.error(f"Failed to update user status: {str(e)}", exc_info=True)
        return False


def update_user_role(chat_id: int, role: str) -> bool:
    """
    更新用戶角色

    Args:
        chat_id: Telegram chat ID
        role: 新角色 ('admin' 或 'user')

    Returns:
        bool: True 如果成功
    """
    try:
        table.update_item(
            Key={"chat_id": chat_id},
            UpdateExpression="SET #role = :role",
            ExpressionAttributeNames={"#role": "role"},
            ExpressionAttributeValues={":role": role},
        )
        logger.info(
            f"User role updated to {role}",
            extra={"chat_id": chat_id, "role": role, "event_type": "user_role_updated"},
        )
        return True
    except ClientError as e:
        logger.error(f"Failed to update user role: {str(e)}", exc_info=True)
        return False


def get_stats() -> dict:
    """
    獲取統計信息

    Returns:
        dict: 統計數據
    """
    try:
        # 掃描整個表（注意：大表可能需要分頁）
        response = table.scan()
        items = response.get("Items", [])

        total_users = len(items)
        enabled_users = sum(1 for item in items if item.get("enabled", False))
        admin_count = sum(1 for item in items if item.get("role") == "admin")
        group_count = sum(1 for item in items if item.get("chat_id", 0) < 0)
        private_count = total_users - group_count

        return {
            "total_users": total_users,
            "enabled_users": enabled_users,
            "disabled_users": total_users - enabled_users,
            "admin_count": admin_count,
            "user_count": total_users - admin_count,
            "group_count": group_count,
            "private_count": private_count,
        }
    except ClientError as e:
        logger.error(f"Failed to get stats: {str(e)}", exc_info=True)
        return {}


def check_file_permission(chat_id: int) -> bool:
    """
    檢查用戶是否有檔案讀取權限

    Args:
        chat_id: Telegram chat ID

    Returns:
        bool: True 如果有權限
    """
    try:
        response = table.get_item(Key={"chat_id": chat_id})

        if "Item" not in response:
            logger.info(
                "User not in allowlist, no file permission",
                extra={"chat_id": chat_id, "event_type": "file_permission_denied_not_in_allowlist"},
            )
            return False

        item = response["Item"]

        # 檢查是否啟用
        if not item.get("enabled", False):
            logger.info(
                "User disabled, no file permission",
                extra={"chat_id": chat_id, "event_type": "file_permission_denied_disabled"},
            )
            return False

        # 檢查權限（如果 permissions 欄位不存在，預設為 False）
        permissions = item.get("permissions", {})
        has_permission = permissions.get("file_reader", False)

        logger.info(
            f"File permission check: {has_permission}",
            extra={
                "chat_id": chat_id,
                "has_permission": has_permission,
                "event_type": "file_permission_check",
            },
        )

        return has_permission

    except ClientError as e:
        logger.error(
            f"DynamoDB error during permission check: {str(e)}",
            extra={"chat_id": chat_id, "event_type": "file_permission_check_error"},
            exc_info=True,
        )
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error in permission check: {str(e)}",
            extra={"chat_id": chat_id, "event_type": "file_permission_check_error"},
            exc_info=True,
        )
        return False


def update_file_permission(chat_id: int, enabled: bool) -> bool:
    """
    更新用戶的檔案讀取權限（管理員指令使用）

    Args:
        chat_id: Telegram chat ID
        enabled: True 啟用，False 禁用

    Returns:
        bool: True 如果成功
    """
    try:
        table.update_item(
            Key={"chat_id": chat_id},
            UpdateExpression="SET permissions.file_reader = :enabled",
            ExpressionAttributeValues={":enabled": enabled},
        )
        logger.info(
            "File permission updated",
            extra={"chat_id": chat_id, "enabled": enabled, "event_type": "file_permission_updated"},
        )
        return True
    except ClientError as e:
        logger.error(
            f"Failed to update file permission: {str(e)}",
            extra={"chat_id": chat_id, "event_type": "file_permission_update_failed"},
            exc_info=True,
        )
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error updating file permission: {str(e)}",
            extra={"chat_id": chat_id, "event_type": "file_permission_update_failed"},
            exc_info=True,
        )
        return False
