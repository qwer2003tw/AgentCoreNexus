"""
Command Decorators - 指令裝飾器
"""

from functools import wraps

from auth.permissions import Permission, check_permission
from telegram import Update
from telegram_client import send_permission_denied

from utils.logger import get_logger

logger = get_logger(__name__)


def require_permission(required: Permission):
    """
    權限檢查裝飾器工廠

    Args:
        required: 需要的權限等級

    Returns:
        裝飾器函數

    Example:
        @require_permission(Permission.ADMIN)
        class AdminCommandHandler(CommandHandler):
            ...
    """

    def decorator(handler_class: type) -> type:
        """
        類裝飾器 - 包裝 CommandHandler 的 handle 方法

        Args:
            handler_class: CommandHandler 子類別

        Returns:
            包裝後的類別
        """
        # 保存原始的 handle 方法
        original_handle = handler_class.handle

        @wraps(original_handle)
        def wrapped_handle(self, update: Update, event: dict) -> bool:
            """
            包裝後的 handle 方法 - 加入權限檢查

            Args:
                self: CommandHandler 實例
                update: Telegram Update 物件
                event: API Gateway event

            Returns:
                bool: True 如果成功處理，False 如果權限不足或處理失敗
            """
            # 取得用戶資訊
            message = update.message or update.edited_message
            if not message:
                logger.warning("No message in update", extra={"event_type": "decorator_no_message"})
                return False

            chat_id = message.chat_id
            username = message.from_user.username if message.from_user else None

            # 檢查權限
            logger.info(
                f"Checking permission for handler: {self.get_command_name()}",
                extra={
                    "handler_name": self.get_command_name(),
                    "chat_id": chat_id,
                    "username": username,
                    "required_permission": required.name,
                    "event_type": "permission_check_start",
                },
            )

            if not check_permission(chat_id, username or "", required):
                # 權限不足，發送通知訊息
                logger.warning(
                    f"Permission denied for handler: {self.get_command_name()}",
                    extra={
                        "handler_name": self.get_command_name(),
                        "chat_id": chat_id,
                        "username": username,
                        "required_permission": required.name,
                        "event_type": "permission_denied",
                    },
                )

                # 發送權限不足訊息
                send_permission_denied(chat_id, required.name)
                return False

            # 權限足夠，執行原始的 handle 方法
            logger.info(
                f"Permission granted for handler: {self.get_command_name()}",
                extra={
                    "handler_name": self.get_command_name(),
                    "chat_id": chat_id,
                    "username": username,
                    "required_permission": required.name,
                    "event_type": "permission_granted",
                },
            )

            return original_handle(self, update, event)

        # 替換 handle 方法
        handler_class.handle = wrapped_handle

        # 標記此類別已被裝飾（用於除錯和測試）
        handler_class._permission_required = required

        return handler_class

    return decorator


def require_admin(handler_class: type) -> type:
    """
    需要管理員權限的裝飾器

    Args:
        handler_class: CommandHandler 子類別

    Returns:
        包裝後的類別

    Example:
        @require_admin
        class AdminCommandHandler(CommandHandler):
            def can_handle(self, text: str) -> bool:
                return text.startswith('/admin')

            def handle(self, update: Update, event: dict) -> bool:
                # 此方法只會在權限檢查通過後執行
                ...
    """
    return require_permission(Permission.ADMIN)(handler_class)


def require_allowlist(handler_class: type) -> type:
    """
    需要在 allowlist 的裝飾器

    Args:
        handler_class: CommandHandler 子類別

    Returns:
        包裝後的類別

    Example:
        @require_allowlist
        class PrivateCommandHandler(CommandHandler):
            def can_handle(self, text: str) -> bool:
                return text.startswith('/private')

            def handle(self, update: Update, event: dict) -> bool:
                # 此方法只會在權限檢查通過後執行
                ...
    """
    return require_permission(Permission.ALLOWLIST)(handler_class)
