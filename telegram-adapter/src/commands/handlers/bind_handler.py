"""
Bind Command Handler - 身份綁定命令處理器
生成綁定碼供用戶在 Web 介面使用
"""

import os
import sys

import telegram_client
from commands.base import CommandHandler
from telegram import Update

from utils.logger import get_logger

logger = get_logger(__name__)

# 動態導入 IdentityService（從 Lambda Layer）
sys.path.insert(0, "/opt/python")
from identity_service import IdentityService  # noqa: E402


class BindCommandHandler(CommandHandler):
    """
    /bind 命令處理器

    功能：為 Telegram 用戶生成綁定碼
    權限：所有用戶可用（不需要管理員）

    使用方式：
        用戶: /bind
        Bot: 顯示 6 位數字綁定碼和使用說明
    """

    def __init__(self):
        """初始化處理器"""
        self._identity_service = None

    def _get_identity_service(self):
        """取得 IdentityService 單例"""
        if self._identity_service is None:
            binding_codes_table = os.getenv("BINDING_CODES_TABLE")
            identity_map_table = os.getenv("IDENTITY_MAP_TABLE")

            if not binding_codes_table or not identity_map_table:
                logger.error("Identity binding tables not configured")
                return None

            self._identity_service = IdentityService(
                binding_codes_table_name=binding_codes_table,
                identity_map_table_name=identity_map_table,
            )
            logger.info("IdentityService initialized")

        return self._identity_service

    def can_handle(self, text: str) -> bool:
        """判斷是否為 /bind 命令"""
        if not text:
            return False
        return text.strip() == "/bind"

    def handle(self, update: Update, event: dict) -> bool:
        """處理 /bind 命令"""
        message = update.message or update.edited_message
        if not message:
            return False

        chat_id = message.chat_id
        user = message.from_user
        if not user:
            return False

        user_id = str(user.id)
        username = user.username or "Unknown"

        logger.info(
            "Bind command received",
            extra={
                "chat_id": chat_id,
                "user_id": user_id,
                "username": username,
                "event_type": "bind_command",
            },
        )

        # 獲取 IdentityService
        identity_service = self._get_identity_service()
        if not identity_service:
            error_msg = "❌ 綁定功能暫時不可用\n\n請稍後再試"
            return telegram_client.send_message(chat_id, error_msg, parse_mode=None)

        try:
            # 生成綁定碼
            result = identity_service.generate_binding_code(user_id)
            code = result["code"]
            expires_in = result["expires_in_minutes"]

            # 格式化回應訊息
            message_text = f"""🔗 身份綁定碼

您的綁定碼：{code}
⏰ 有效期限：{expires_in} 分鐘

請在 Web 介面的「綁定」選單輸入此綁定碼

⚠️ 注意：
• 此綁定碼只能使用一次
• 綁定後將共享跨通道對話歷史
• 綁定碼將在 {expires_in} 分鐘後自動失效"""

            success = telegram_client.send_message(chat_id, message_text, parse_mode=None)

            if success:
                logger.info(
                    f"Binding code generated and sent: {code}",
                    extra={
                        "user_id": user_id,
                        "code": code,
                        "expires_in_minutes": expires_in,
                        "event_type": "bind_code_generated",
                    },
                )

            return success

        except Exception as e:
            logger.error(
                f"Failed to generate binding code: {str(e)}",
                extra={"user_id": user_id, "event_type": "bind_error"},
                exc_info=True,
            )

            error_msg = "❌ 生成綁定碼失敗\n\n請稍後再試或聯繫管理員"
            return telegram_client.send_message(chat_id, error_msg, parse_mode=None)

    def get_command_name(self) -> str:
        """取得指令名稱"""
        return "BindCommand"

    def get_description(self) -> str:
        """取得指令描述"""
        return "生成身份綁定碼（用於 Web 綁定）"
