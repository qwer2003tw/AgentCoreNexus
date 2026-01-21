"""
測試 EventBridge 整合功能
"""

import json
from unittest.mock import Mock, patch

from src.handler import detect_channel, normalize_message, publish_to_eventbridge


class TestChannelDetection:
    """測試通道檢測功能"""

    def test_detect_telegram_channel(self):
        """測試檢測 Telegram 通道"""
        event = {"path": "/telegram/webhook"}
        assert detect_channel(event) == "telegram"

    def test_detect_telegram_case_insensitive(self):
        """測試 Telegram 路徑大小寫不敏感"""
        event = {"path": "/TELEGRAM/webhook"}
        assert detect_channel(event) == "telegram"

    def test_detect_discord_channel(self):
        """測試檢測 Discord 通道"""
        event = {"path": "/discord/webhook"}
        assert detect_channel(event) == "discord"

    def test_detect_slack_channel(self):
        """測試檢測 Slack 通道"""
        event = {"path": "/slack/events"}
        assert detect_channel(event) == "slack"

    def test_detect_web_channel_default(self):
        """測試預設為 Web 通道"""
        event = {"path": "/api/message"}
        assert detect_channel(event) == "web"

    def test_detect_channel_no_path(self):
        """測試無路徑時預設為 Web"""
        event = {}
        assert detect_channel(event) == "web"


class TestMessageNormalization:
    """測試訊息標準化功能"""

    def test_normalize_telegram_text_message(self):
        """測試標準化 Telegram 文字訊息"""
        raw_data = {
            "message": {
                "message_id": 12345,
                "from": {
                    "id": 123456789,
                    "username": "testuser",
                    "first_name": "Test",
                    "last_name": "User",
                },
                "chat": {"id": 123456789, "type": "private"},
                "text": "Hello World",
            }
        }

        result = normalize_message(raw_data, "telegram", {})

        # 驗證基本結構
        assert "messageId" in result
        assert "timestamp" in result
        assert "channel" in result
        assert "user" in result
        assert "content" in result
        assert "context" in result
        assert "routing" in result

        # 驗證通道資訊
        assert result["channel"]["type"] == "telegram"
        assert result["channel"]["channelId"] == "123456789"
        assert result["channel"]["metadata"]["chat_type"] == "private"

        # 驗證用戶資訊
        assert result["user"]["id"] == "tg:123456789"
        assert result["user"]["username"] == "testuser"
        assert result["user"]["displayName"] == "Test User"

        # 驗證內容
        assert result["content"]["text"] == "Hello World"
        assert result["content"]["messageType"] == "text"
        assert result["content"]["attachments"] == []

        # 驗證上下文
        assert result["context"]["conversationId"] == "123456789"
        assert result["context"]["sessionId"] == "123456789"

    def test_normalize_telegram_photo_message(self):
        """測試標準化 Telegram 圖片訊息"""
        raw_data = {
            "message": {
                "message_id": 12345,
                "from": {"id": 123456789, "username": "testuser", "first_name": "Test"},
                "chat": {"id": 123456789, "type": "private"},
                "photo": [{"file_id": "small_file_id"}, {"file_id": "large_file_id"}],
                "caption": "Test photo",
            }
        }

        result = normalize_message(raw_data, "telegram", {})

        assert result["content"]["messageType"] == "image"
        assert result["content"]["text"] == "Test photo"
        assert len(result["content"]["attachments"]) == 1
        assert result["content"]["attachments"][0]["type"] == "photo"
        assert result["content"]["attachments"][0]["file_id"] == "large_file_id"

    def test_normalize_telegram_document_message(self):
        """測試標準化 Telegram 文件訊息"""
        raw_data = {
            "message": {
                "message_id": 12345,
                "from": {"id": 123456789, "username": "testuser", "first_name": "Test"},
                "chat": {"id": 123456789, "type": "private"},
                "document": {"file_id": "doc_file_id"},
            }
        }

        result = normalize_message(raw_data, "telegram", {})

        assert result["content"]["messageType"] == "file"
        assert len(result["content"]["attachments"]) == 1
        assert result["content"]["attachments"][0]["type"] == "document"

    def test_normalize_telegram_video_message(self):
        """測試標準化 Telegram 影片訊息"""
        raw_data = {
            "message": {
                "message_id": 12345,
                "from": {"id": 123456789, "username": "testuser", "first_name": "Test"},
                "chat": {"id": 123456789, "type": "private"},
                "video": {"file_id": "video_file_id"},
            }
        }

        result = normalize_message(raw_data, "telegram", {})

        assert result["content"]["messageType"] == "video"
        assert result["content"]["attachments"][0]["type"] == "video"

    def test_normalize_telegram_audio_message(self):
        """測試標準化 Telegram 音訊訊息"""
        raw_data = {
            "message": {
                "message_id": 12345,
                "from": {"id": 123456789, "username": "testuser", "first_name": "Test"},
                "chat": {"id": 123456789, "type": "private"},
                "audio": {"file_id": "audio_file_id"},
            }
        }

        result = normalize_message(raw_data, "telegram", {})

        assert result["content"]["messageType"] == "audio"
        assert result["content"]["attachments"][0]["type"] == "audio"

    def test_normalize_telegram_no_username(self):
        """測試標準化沒有 username 的訊息"""
        raw_data = {
            "message": {
                "message_id": 12345,
                "from": {"id": 123456789, "first_name": "Test"},
                "chat": {"id": 123456789, "type": "private"},
                "text": "Hello",
            }
        }

        result = normalize_message(raw_data, "telegram", {})

        assert result["user"]["username"] == ""
        assert result["user"]["displayName"] == "Test"

    def test_normalize_unknown_channel(self):
        """測試標準化未知通道"""
        raw_data = {"some": "data"}

        result = normalize_message(raw_data, "web", {})

        assert result["channel"]["type"] == "web"
        assert result["channel"]["channelId"] == "unknown"
        assert result["user"]["id"] == "unknown"
        assert result["content"]["text"] == ""


class TestEventBridgePublish:
    """測試 EventBridge 發布功能"""

    @patch.dict("os.environ", {"EVENT_BUS_NAME": "test-event-bus"})
    @patch("src.handler.get_eventbridge_client")
    def test_publish_success(self, mock_get_client):
        """測試成功發布到 EventBridge"""
        # Mock EventBridge 客戶端
        mock_evb = Mock()
        mock_evb.put_events.return_value = {"FailedEntryCount": 0, "Entries": []}
        mock_get_client.return_value = mock_evb

        normalized = {
            "messageId": "test-uuid",
            "timestamp": "2026-01-06T10:00:00Z",
            "channel": {"type": "telegram", "channelId": "123"},
            "user": {"id": "tg:123"},
            "content": {"text": "test"},
            "context": {},
            "routing": {},
            "raw": {"original": "data"},
        }

        result = publish_to_eventbridge(normalized)

        assert result is True
        mock_evb.put_events.assert_called_once()

        # 驗證呼叫參數
        call_args = mock_evb.put_events.call_args[1]
        entries = call_args["Entries"]
        assert len(entries) == 1
        assert entries[0]["Source"] == "universal-adapter"
        assert entries[0]["DetailType"] == "message.received"
        assert entries[0]["EventBusName"] == "test-event-bus"

        # 驗證 raw 被移除
        detail = json.loads(entries[0]["Detail"])
        assert "raw" not in detail

    @patch.dict("os.environ", {}, clear=True)
    def test_publish_no_event_bus_configured(self):
        """測試未配置 EventBus 時跳過發布"""
        normalized = {"messageId": "test"}

        result = publish_to_eventbridge(normalized)

        assert result is False

    @patch.dict("os.environ", {"EVENT_BUS_NAME": "test-event-bus"})
    @patch("src.handler.get_eventbridge_client")
    def test_publish_failed_entry(self, mock_get_client):
        """測試 EventBridge 返回失敗"""
        mock_evb = Mock()
        mock_evb.put_events.return_value = {
            "FailedEntryCount": 1,
            "Entries": [{"ErrorCode": "InternalError"}],
        }
        mock_get_client.return_value = mock_evb

        normalized = {
            "messageId": "test-uuid",
            "channel": {"type": "telegram"},
            "user": {},
            "content": {},
            "context": {},
            "routing": {},
        }

        result = publish_to_eventbridge(normalized)

        assert result is False

    @patch.dict("os.environ", {"EVENT_BUS_NAME": "test-event-bus"})
    @patch("src.handler.get_eventbridge_client")
    def test_publish_exception(self, mock_get_client):
        """測試 EventBridge 拋出異常"""
        mock_evb = Mock()
        mock_evb.put_events.side_effect = Exception("Network error")
        mock_get_client.return_value = mock_evb

        normalized = {
            "messageId": "test-uuid",
            "channel": {"type": "telegram"},
            "user": {},
            "content": {},
            "context": {},
            "routing": {},
        }

        result = publish_to_eventbridge(normalized)

        assert result is False


class TestIntegration:
    """測試整合場景"""

    @patch.dict("os.environ", {"EVENT_BUS_NAME": "test-event-bus"})
    @patch("src.handler.get_eventbridge_client")
    def test_full_normalization_and_publish_flow(self, mock_get_client):
        """測試完整的標準化和發布流程"""
        # Mock EventBridge
        mock_evb = Mock()
        mock_evb.put_events.return_value = {"FailedEntryCount": 0}
        mock_get_client.return_value = mock_evb

        # Telegram 原始訊息
        raw_data = {
            "message": {
                "message_id": 12345,
                "from": {
                    "id": 123456789,
                    "username": "testuser",
                    "first_name": "Test",
                    "last_name": "User",
                },
                "chat": {"id": 123456789, "type": "private"},
                "text": "Integration test message",
            }
        }

        # 步驟 1: 標準化
        normalized = normalize_message(raw_data, "telegram", {})
        assert normalized["content"]["text"] == "Integration test message"
        assert normalized["channel"]["type"] == "telegram"

        # 步驟 2: 發布
        result = publish_to_eventbridge(normalized)
        assert result is True

        # 驗證發布的訊息
        call_args = mock_evb.put_events.call_args[1]
        detail = json.loads(call_args["Entries"][0]["Detail"])

        # 確認標準化結構保持完整
        assert detail["messageId"] == normalized["messageId"]
        assert detail["channel"]["type"] == "telegram"
        assert detail["user"]["username"] == "testuser"
        assert detail["content"]["text"] == "Integration test message"

        # 確認 raw 資料被移除
        assert "raw" not in detail
