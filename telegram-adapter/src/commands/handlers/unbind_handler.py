"""
Unbind Command Handler - 解除綁定命令處理器
解除用戶的跨通道身份綁定
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


class UnbindCommandHandler(CommandHandler):
    """
    /unbind 命令處理器

    功能：解除身份綁定（需要二次確認）
    權限：所有用戶可用（不需要管理員）

    使用方式：
        用戶: /unbind
        Bot: 顯示確認訊息和已綁定身份

        用戶: /unbind confirm
        Bot: 執行解綁並確認
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
        """判斷是否為 /unbind 命令"""
        if not text:
            return False
        stripped = text.strip()
        return stripped == "/unbind" or stripped == "/unbind confirm"

    def handle(self, update: Update, event: dict) -> bool:
        """處理 /unbind 命令"""
        message = update.message or update.edited_message
        if not message:
            return False

        chat_id = message.chat_id
        user = message.from_user
        if not user:
            return False

        user_id = str(user.id)
        username = user.username or "Unknown"
        command_text = (message.text or "").strip()

        logger.info(
            "Unbind command received",
            extra={
                "chat_id": chat_id,
                "user_id": user_id,
                "username": username,
                "command": command_text,
                "event_type": "unbind_command",
            },
        )

        # 獲取 IdentityService
        identity_service = self._get_identity_service()
        if not identity_service:
            error_msg = "❌ 綁定功能暫時不可用\n\n請稍後再試"
            return telegram_client.send_message(chat_id, error_msg, parse_mode=None)

        # 判斷是初次請求還是確認
        is_confirm = command_text == "/unbind confirm"

        if not is_confirm:
            # 第一次：顯示確認訊息
            return self._show_confirmation(chat_id, user_id, identity_service)
        else:
            # 第二次：執行解綁
            return self._execute_unbind(chat_id, user_id, identity_service)

    def _show_confirmation(self, chat_id: int, user_id: str, identity_service) -> bool:
        """顯示解綁確認訊息"""
        try:
            # 查詢當前綁定
            telegram_identity_id = f"tg:{user_id}"
            bindings = identity_service.get_bindings(telegram_identity_id)

            if not bindings:
                message_text = """🔗 解除綁定

您目前沒有綁定其他身份，無需解綁

💡 使用 /bind 命令可以生成綁定碼"""
                return telegram_client.send_message(chat_id, message_text, parse_mode=None)

            # 格式化已綁定的身份列表
            bound_identities = bindings.get("bound_identities", [])

            lines = ["⚠️ 確認解除身份綁定\n", "您目前綁定的身份："]

            for identity in bound_identities:
                platform = identity.get("platform", "unknown")
                identity_user_id = identity.get("user_id", "unknown")

                platform_icon = {"web": "🖥️", "telegram": "📱", "discord": "💬", "slack": "💼"}.get(
                    platform, "❓"
                )

                lines.append(f"  • {platform_icon} {platform.capitalize()}: {identity_user_id}")

            lines.extend(
                [
                    "\n解除綁定後：",
                    "✓ 對話歷史保留（不會刪除）",
                    "✗ 各通道恢復獨立對話",
                    "✗ 無法跨通道同步新訊息\n",
                    "確認解除請輸入：",
                    "/unbind confirm",
                ]
            )

            message_text = "\n".join(lines)
            return telegram_client.send_message(chat_id, message_text, parse_mode=None)

        except Exception as e:
            logger.error(
                f"Failed to show unbind confirmation: {str(e)}",
                extra={"user_id": user_id, "event_type": "unbind_confirm_error"},
                exc_info=True,
            )

            error_msg = "❌ 查詢綁定狀態失敗\n\n請稍後再試"
            return telegram_client.send_message(chat_id, error_msg, parse_mode=None)

    def _execute_unbind(self, chat_id: int, user_id: str, identity_service) -> bool:
        """執行解綁操作"""
        try:
            # 再次檢查是否有綁定（防止重複解綁）
            telegram_identity_id = f"tg:{user_id}"
            bindings = identity_service.get_bindings(telegram_identity_id)

            if not bindings:
                message_text = "ℹ️ 您目前沒有綁定其他身份"
                return telegram_client.send_message(chat_id, message_text, parse_mode=None)

            # 執行解綁
            success = identity_service.unbind(telegram_identity_id)

            if success:
                message_text = f"""✅ 已解除身份綁定

您的身份已恢復為獨立：
📱 Telegram ID: {user_id}

💡 對話歷史已保留
💡 隨時可以使用 /bind 重新綁定"""

                logger.info(
                    "Identity unbound successfully",
                    extra={"user_id": user_id, "event_type": "unbind_success"},
                )

                return telegram_client.send_message(chat_id, message_text, parse_mode=None)
            else:
                # unbind 返回 False 表示身份不存在（理論上不應該發生）
                message_text = "ℹ️ 解綁失敗：找不到綁定記錄"
                return telegram_client.send_message(chat_id, message_text, parse_mode=None)

        except Exception as e:
            logger.error(
                f"Failed to unbind identity: {str(e)}",
                extra={"user_id": user_id, "event_type": "unbind_error"},
                exc_info=True,
            )

            error_msg = "❌ 解除綁定失敗\n\n請稍後再試或聯繫管理員"
            return telegram_client.send_message(chat_id, error_msg, parse_mode=None)

    def get_command_name(self) -> str:
        """取得指令名稱"""
        return "UnbindCommand"

    def get_description(self) -> str:
        """取得指令描述"""
        return "解除跨通道身份綁定（需要確認）"
