"""
New Session Command Handler
處理 /new 指令，開始新的對話 session
"""

import json
import os
import uuid
from datetime import datetime

import boto3
import telegram_client
from commands.base import CommandHandler
from telegram import Update

from utils.logger import get_logger

logger = get_logger(__name__)

# EventBridge client for sending session.clear events
_eventbridge_client = None


def get_eventbridge_client():
    """Get EventBridge client singleton"""
    global _eventbridge_client
    if _eventbridge_client is None:
        _eventbridge_client = boto3.client("events")
    return _eventbridge_client


class NewCommandHandler(CommandHandler):
    """處理 /new 指令的處理器"""

    def can_handle(self, message: str) -> bool:
        """
        判斷是否可以處理此訊息

        Args:
            message: 訊息文字

        Returns:
            如果訊息以 /new 開頭則返回 True
        """
        return message.strip().startswith("/new")

    def handle(self, update: Update, event: dict) -> bool:
        """
        處理 /new 指令

        Args:
            update: Telegram Update 物件
            event: Lambda event 物件

        Returns:
            True 如果成功處理，False 如果處理失敗
        """
        try:
            # 從 Update 物件取得資訊
            chat_id = update.effective_message.chat_id
            user_id = update.effective_message.from_user.id
            username = update.effective_message.from_user.username or "Unknown"

            if not chat_id:
                logger.warning("New command: missing chat_id")
                return False

            # 生成新的 session ID
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            random_suffix = str(uuid.uuid4())[:8]
            new_session_id = f"session-{timestamp}-{random_suffix}"

            logger.info(
                f"Creating new session for user {user_id}",
                extra={"user_id": user_id, "username": username, "new_session_id": new_session_id},
            )

            # 發送 session.clear 事件到 EventBridge（讓 Processor 清除 Memory）
            clear_success = send_session_clear_event(user_id, str(chat_id), new_session_id)
            if not clear_success:
                logger.warning(f"Failed to send session clear event for user {user_id}")

            # 構建回應訊息
            message_lines = [
                "✅ 已開始新的對話 session！",
                "",
                "🆔 Session ID:",
                f"`{new_session_id[:28]}...`",
                "",
                "📌 說明：",
                "• 💾 你的長期記憶（姓名、偏好等）仍然保留",
                "• 🆕 當前對話的短期記憶已清空",
                "• 🔄 下一則訊息將使用新的 session",
                "",
                "💡 提示：",
                "你可以隨時使用 /new 開始新的對話主題，",
                "而不會影響系統對你的長期記憶。",
            ]

            response_text = "\n".join(message_lines)

            # 發送回覆（包含 session_id 供下次使用）
            # 注意：這裡需要將 new_session_id 儲存起來，讓下一次訊息使用
            # 目前先簡單實現，未來可以用 DynamoDB 儲存
            telegram_client.send_message(chat_id, response_text)

            logger.info(
                "New session created successfully",
                extra={"user_id": user_id, "session_id": new_session_id},
            )

            return True

        except Exception as e:
            logger.error(f"Error processing /new command: {str(e)}", exc_info=True)

            # 嘗試發送錯誤訊息給用戶
            try:
                chat_id = update.effective_message.chat_id
                if chat_id:
                    error_msg = "❌ 無法創建新 session，請稍後再試。"
                    telegram_client.send_message(chat_id, error_msg)
            except:
                pass

            return False

    def get_command_name(self) -> str:
        """取得指令名稱"""
        return "/new"

    def get_description(self) -> str:
        """取得指令描述"""
        return "開始新的對話 session（清空短期記憶，保留長期記憶）"


def send_session_clear_event(user_id: int, chat_id: str, new_session_id: str) -> bool:
    """
    發送 session.clear 事件到 EventBridge

    Args:
        user_id: Telegram user ID
        chat_id: Telegram chat ID
        new_session_id: 新的 session ID

    Returns:
        True if successful
    """
    event_bus_name = os.getenv("EVENT_BUS_NAME")
    if not event_bus_name:
        logger.warning("EVENT_BUS_NAME not configured, cannot clear session")
        return False

    try:
        evb = get_eventbridge_client()

        event_detail = {
            "user_id": str(user_id),
            "chat_id": chat_id,
            "new_session_id": new_session_id,
            "timestamp": datetime.now().isoformat(),
        }

        response = evb.put_events(
            Entries=[
                {
                    "Source": "telegram-adapter",
                    "DetailType": "session.clear",
                    "Detail": json.dumps(event_detail),
                    "EventBusName": event_bus_name,
                }
            ]
        )

        if response.get("FailedEntryCount", 0) > 0:
            logger.error(f"Failed to send session.clear event: {response}")
            return False

        logger.info(
            "Session clear event sent", extra={"user_id": user_id, "new_session_id": new_session_id}
        )
        return True

    except Exception as e:
        logger.error(f"Error sending session clear event: {e}", exc_info=True)
        return False
