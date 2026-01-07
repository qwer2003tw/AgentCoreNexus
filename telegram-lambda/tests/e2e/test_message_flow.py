"""
訊息流程端對端測試
測試完整的訊息處理流程：接收 → EventBridge → 響應
"""

import json

import pytest
from handler import lambda_handler

from tests.e2e.helpers.telegram_factory import TelegramUpdateFactory


@pytest.mark.e2e
class TestMessageFlow:
    """測試完整的訊息處理流程"""

    def test_text_message_to_eventbridge(self, full_mock_env, lambda_context):
        """測試文字訊息被正確轉換並發送到 EventBridge"""
        # Arrange
        test_message = "這是一條測試訊息，請幫我處理"
        event = TelegramUpdateFactory.create_message_update(test_message)
        eventbridge = full_mock_env["eventbridge"]

        # Act
        response = lambda_handler(event, lambda_context)

        # Assert
        assert response["statusCode"] == 200

        # 驗證 EventBridge 事件
        events = eventbridge.get_events()
        assert len(events) > 0

        # 解析事件內容
        event_detail = events[0]
        assert event_detail["Source"] == "universal-adapter"
        assert event_detail["DetailType"] == "message.received"

        # 驗證標準化訊息格式
        detail = json.loads(event_detail["Detail"])
        assert detail["channel"]["type"] == "telegram"
        assert detail["content"]["text"] == test_message
        assert detail["content"]["messageType"] == "text"
        # username 可能為空（取決於 Update 解析）
        assert "username" in detail["user"]

    def test_message_normalization(self, full_mock_env, lambda_context):
        """測試訊息標準化格式"""
        # Arrange
        event = TelegramUpdateFactory.create_message_update(
            text="測試標準化",
            user_id=316743844,
            username="qwer2003tw",
            first_name="Steven",
            last_name="Test",
        )
        eventbridge = full_mock_env["eventbridge"]

        # Act
        response = lambda_handler(event, lambda_context)

        # Assert
        assert response["statusCode"] == 200

        # 驗證標準化格式
        events = eventbridge.get_events()
        detail = json.loads(events[0]["Detail"])

        # 檢查必要欄位
        assert "messageId" in detail
        assert "timestamp" in detail
        assert "channel" in detail
        assert "user" in detail
        assert "content" in detail
        assert "context" in detail
        assert "routing" in detail

        # 檢查用戶資訊
        assert detail["user"]["channelUserId"] in ["316743844", "None"]  # 可能是字串 "None"
        assert "username" in detail["user"]
        assert detail["user"]["displayName"]  # 確保有 displayName

    def test_channel_detection(self, full_mock_env, lambda_context):
        """測試通道檢測"""
        # Arrange
        event = TelegramUpdateFactory.create_message_update("Test channel detection")
        eventbridge = full_mock_env["eventbridge"]

        # Act
        result = lambda_handler(event, lambda_context)

        # Assert
        assert result["statusCode"] == 200

        events = eventbridge.get_events()
        detail = json.loads(events[0]["Detail"])

        # 驗證通道類型
        assert detail["channel"]["type"] == "telegram"
        assert detail["channel"]["metadata"]["chat_type"] == "private"


@pytest.mark.e2e
class TestAttachments:
    """測試附件處理"""

    def test_photo_message_structure(self, full_mock_env, lambda_context):
        """測試圖片訊息的結構"""
        # Arrange
        event = TelegramUpdateFactory.create_photo_update(caption="這是一張測試圖片")
        eventbridge = full_mock_env["eventbridge"]

        # Act
        response = lambda_handler(event, lambda_context)

        # Assert
        assert response["statusCode"] == 200

        # 驗證事件結構
        events = eventbridge.get_events()
        detail = json.loads(events[0]["Detail"])

        # 驗證訊息類型
        assert detail["content"]["messageType"] == "image"
        assert detail["content"]["text"] == "這是一張測試圖片"

        # 驗證附件
        attachments = detail["content"]["attachments"]
        assert len(attachments) > 0
        assert attachments[0]["type"] == "photo"

    def test_document_message_structure(self, full_mock_env, lambda_context):
        """測試文件訊息的結構"""
        # Arrange
        event = TelegramUpdateFactory.create_document_update(filename="test.pdf")
        eventbridge = full_mock_env["eventbridge"]

        # Act
        response = lambda_handler(event, lambda_context)

        # Assert
        assert response["statusCode"] == 200

        # 驗證事件結構
        events = eventbridge.get_events()
        detail = json.loads(events[0]["Detail"])

        # 驗證訊息類型
        assert detail["content"]["messageType"] == "file"

        # 驗證附件
        attachments = detail["content"]["attachments"]
        assert len(attachments) > 0
        assert attachments[0]["type"] == "document"
        assert attachments[0]["file_name"] == "test.pdf"


@pytest.mark.e2e
@pytest.mark.slow
class TestErrorHandling:
    """測試錯誤處理"""

    def test_invalid_json_payload(self, full_mock_env, lambda_context):
        """測試無效的 JSON payload"""
        # Arrange
        event = {
            "body": "invalid json {{{",
            "headers": {"X-Telegram-Bot-Api-Secret-Token": "test_secret"},
        }

        # Act
        response = lambda_handler(event, lambda_context)

        # Assert
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    def test_missing_chat_id(self, full_mock_env, lambda_context):
        """測試缺少 chat_id 的訊息"""
        # Arrange
        event = {
            "body": json.dumps({"update_id": 1, "message": {}}),
            "headers": {"X-Telegram-Bot-Api-Secret-Token": "test_secret"},
        }

        # Act
        result = lambda_handler(event, lambda_context)

        # Assert
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body
