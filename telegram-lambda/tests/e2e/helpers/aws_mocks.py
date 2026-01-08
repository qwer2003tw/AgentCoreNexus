"""
AWS 服務 Mock 工具
提供測試環境的 AWS 服務模擬
"""

from typing import Any
from unittest.mock import MagicMock, Mock


class MockSecretsManager:
    """Mock Secrets Manager"""

    @staticmethod
    def setup_secrets():
        """設置測試用的 secrets"""
        return {
            "bot_token": "test_bot_token_12345",
            "webhook_secret_token": "test_secret",
        }


class MockEventBridge:
    """Mock EventBridge 客戶端"""

    def __init__(self):
        self.events = []

    def put_events(self, **kwargs) -> dict[str, Any]:
        """記錄發送的事件"""
        entries = kwargs.get("Entries", [])
        self.events.extend(entries)
        return {"FailedEntryCount": 0, "Entries": [{"EventId": f"event-{i}"} for i in entries]}

    def get_events(self):
        """取得所有記錄的事件"""
        return self.events

    def clear(self):
        """清除記錄的事件"""
        self.events = []


class MockTelegramAPI:
    """Mock Telegram API 調用"""

    def __init__(self):
        self.sent_messages = []
        self.sent_photos = []
        self.sent_documents = []

    def send_message(self, chat_id: int, text: str, **kwargs) -> dict[str, Any]:
        """記錄發送的訊息"""
        message = {"chat_id": chat_id, "text": text, **kwargs}
        self.sent_messages.append(message)
        return {"ok": True, "result": {"message_id": len(self.sent_messages)}}

    def send_photo(self, chat_id: int, photo: str, **kwargs) -> dict[str, Any]:
        """記錄發送的圖片"""
        photo_data = {"chat_id": chat_id, "photo": photo, **kwargs}
        self.sent_photos.append(photo_data)
        return {"ok": True, "result": {"message_id": len(self.sent_photos)}}

    def get_sent_messages(self):
        """取得所有發送的訊息"""
        return self.sent_messages

    def get_last_message(self):
        """取得最後發送的訊息"""
        return self.sent_messages[-1] if self.sent_messages else None

    def clear(self):
        """清除記錄"""
        self.sent_messages = []
        self.sent_photos = []
        self.sent_documents = []


class MockDynamoDB:
    """Mock DynamoDB allowlist"""

    def __init__(self):
        # 預設的 allowlist 用戶
        self.allowed_users = {
            316743844: {"chat_id": 316743844, "username": "qwer2003tw"},
        }

    def check_allowed(self, chat_id: int, username: str) -> bool:
        """檢查用戶是否在 allowlist"""
        return chat_id in self.allowed_users

    def add_user(self, chat_id: int, username: str):
        """添加用戶到 allowlist"""
        self.allowed_users[chat_id] = {"chat_id": chat_id, "username": username}

    def remove_user(self, chat_id: int):
        """從 allowlist 移除用戶"""
        self.allowed_users.pop(chat_id, None)


def create_mock_context() -> Mock:
    """
    創建 Mock Lambda Context

    Returns:
        Mock Lambda context 物件
    """
    context = Mock()
    context.function_name = "telegram-lambda-receiver"
    context.function_version = "$LATEST"
    context.invoked_function_arn = "arn:aws:lambda:us-west-2:123456789:function:test"
    context.memory_limit_in_mb = 256
    context.aws_request_id = "test-request-id-12345"
    context.log_group_name = "/aws/lambda/telegram-lambda-receiver"
    context.log_stream_name = "2026/01/07/[$LATEST]test"

    # 添加 get_remaining_time_in_millis 方法
    context.get_remaining_time_in_millis = MagicMock(return_value=30000)

    return context
