"""
Debug Command Handler - 除錯指令處理器
"""

import telegram_client
from commands.base import CommandHandler
from telegram import Update

from utils.logger import get_logger

logger = get_logger(__name__)


class DebugCommandHandler(CommandHandler):
    """
    除錯指令處理器

    處理 /debug 指令，發送當前請求的除錯資訊

    權限：無需權限（全部開放）
    """

    def can_handle(self, text: str) -> bool:
        """
        判斷是否為 /debug 指令

        Args:
            text: 訊息文字內容

        Returns:
            bool: True 如果是 /debug 或 /debug 開頭的指令
        """
        if not text:
            return False

        stripped = text.strip()
        return stripped == "/debug" or stripped.startswith("/debug ")

    def handle(self, update: Update, event: dict) -> bool:
        """
        處理 /debug 指令

        Args:
            update: Telegram Update 物件
            event: API Gateway event（完整的請求資料）

        Returns:
            bool: True 如果成功發送除錯資訊
        """
        message = update.message or update.edited_message
        if not message:
            logger.warning(
                "No message in update for debug command", extra={"event_type": "debug_no_message"}
            )
            return False

        chat_id = message.chat_id
        username = message.from_user.username if message.from_user else None
        command_text = message.text or message.caption or ""

        logger.info(
            "Processing debug command",
            extra={
                "chat_id": chat_id,
                "username": username,
                "command": command_text.strip(),
                "event_type": "debug_command",
            },
        )

        # 發送除錯資訊
        debug_sent = telegram_client.send_debug_info(chat_id, event)

        if debug_sent:
            logger.info(
                "Debug info sent successfully",
                extra={"chat_id": chat_id, "event_type": "debug_sent"},
            )
            return True
        else:
            logger.warning(
                "Failed to send debug info",
                extra={"chat_id": chat_id, "event_type": "debug_send_failed"},
            )
            return False

    def get_command_name(self) -> str:
        """取得指令名稱"""
        return "DebugCommand"

    def get_description(self) -> str:
        """取得指令描述"""
        return "顯示當前請求的除錯資訊（包含 webhook payload）"
