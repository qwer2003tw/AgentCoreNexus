"""
MyBindings Command Handler - 查看綁定身份命令處理器
顯示用戶當前綁定的所有身份
"""

import os
import sys
from datetime import datetime

import telegram_client
from commands.base import CommandHandler
from telegram import Update

from utils.logger import get_logger

logger = get_logger(__name__)

# 動態導入 IdentityService（從 Lambda Layer）
sys.path.insert(0, "/opt/python")
from identity_service import IdentityService  # noqa: E402


class MyBindingsCommandHandler(CommandHandler):
    """
    /mybindings 命令處理器

    功能：查看當前綁定的身份列表
    權限：所有用戶可用（不需要管理員）

    使用方式：
        用戶: /mybindings
        Bot: 顯示已綁定的身份列表
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
        """判斷是否為 /mybindings 命令"""
        if not text:
            return False
        return text.strip() == "/mybindings"

    def handle(self, update: Update, event: dict) -> bool:
        """處理 /mybindings 命令"""
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
            "MyBindings command received",
            extra={
                "chat_id": chat_id,
                "user_id": user_id,
                "username": username,
                "event_type": "mybindings_command",
            },
        )

        # 獲取 IdentityService
        identity_service = self._get_identity_service()
        if not identity_service:
            error_msg = "❌ 綁定功能暫時不可用\n\n請稍後再試"
            return telegram_client.send_message(chat_id, error_msg, parse_mode=None)

        try:
            # 查詢綁定狀態
            telegram_identity_id = f"tg:{user_id}"
            bindings = identity_service.get_bindings(telegram_identity_id)

            if not bindings:
                # 沒有綁定
                message_text = """🔗 我的身份綁定

目前沒有綁定其他身份

💡 想要綁定 Web 帳號？
使用 /bind 命令生成綁定碼"""

                return telegram_client.send_message(chat_id, message_text, parse_mode=None)

            # 有綁定，格式化顯示
            unified_id = bindings.get("unified_conversation_id", "N/A")
            bound_identities = bindings.get("bound_identities", [])

            lines = [
                "🔗 我的身份綁定\n",
                f"📱 Telegram ID: {user_id}",
                f"🌐 統一對話 ID: {unified_id}\n",
            ]

            if bound_identities:
                lines.append("已綁定的身份：")

                for identity in bound_identities:
                    platform = identity.get("platform", "unknown")
                    identity_user_id = identity.get("user_id", "unknown")
                    bound_at = identity.get("bound_at")

                    # 平台圖標
                    platform_icon = {
                        "web": "🖥️",
                        "telegram": "📱",
                        "discord": "💬",
                        "slack": "💼",
                    }.get(platform, "❓")

                    # 格式化綁定時間
                    if bound_at:
                        try:
                            dt = datetime.fromtimestamp(bound_at)
                            time_str = dt.strftime("%Y-%m-%d %H:%M")
                        except:
                            time_str = "Unknown"
                    else:
                        time_str = "Unknown"

                    lines.append(f"  • {platform_icon} {platform.capitalize()}: {identity_user_id}")
                    lines.append(f"    綁定時間: {time_str}")

                lines.append(f"\n（共 {len(bound_identities) + 1} 個身份綁定）\n")
                lines.append("💡 提示：綁定後的對話在所有通道同步")

            message_text = "\n".join(lines)

            success = telegram_client.send_message(chat_id, message_text, parse_mode=None)

            if success:
                logger.info(
                    "Bindings info sent",
                    extra={
                        "user_id": user_id,
                        "unified_id": unified_id,
                        "bound_count": len(bound_identities),
                        "event_type": "mybindings_success",
                    },
                )

            return success

        except Exception as e:
            logger.error(
                f"Failed to get bindings: {str(e)}",
                extra={"user_id": user_id, "event_type": "mybindings_error"},
                exc_info=True,
            )

            error_msg = "❌ 查詢綁定狀態失敗\n\n請稍後再試或聯繫管理員"
            return telegram_client.send_message(chat_id, error_msg, parse_mode=None)

    def get_command_name(self) -> str:
        """取得指令名稱"""
        return "MyBindingsCommand"

    def get_description(self) -> str:
        """取得指令描述"""
        return "查看當前綁定的身份列表"
