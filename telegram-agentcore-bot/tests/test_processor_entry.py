"""
測試 EventBridge Processor Entry Point
"""

import json
import os
import sys
from unittest.mock import Mock, patch

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestProcessorHandler:
    """測試 Processor 主處理函數"""

    @patch("processor_entry.process_eventbridge_event")
    def test_handler_with_eventbridge_event(self, mock_process_eb):
        """測試處理 EventBridge 事件"""
        from processor_entry import handler

        event = {
            "source": "universal-adapter",
            "detail-type": "message.received",
            "detail": {"messageId": "test-uuid", "channel": {"type": "telegram"}},
        }
        context = Mock()

        mock_process_eb.return_value = {"statusCode": 200}

        result = handler(event, context)

        mock_process_eb.assert_called_once_with(event, context)
        assert result["statusCode"] == 200

    @patch("processor_entry.process_sqs_event")
    def test_handler_with_sqs_event(self, mock_process_sqs):
        """測試處理 SQS 事件（向後兼容）"""
        from processor_entry import handler

        event = {"Records": [{"body": json.dumps({"message": {"text": "test"}})}]}
        context = Mock()

        mock_process_sqs.return_value = {"statusCode": 200}

        result = handler(event, context)

        mock_process_sqs.assert_called_once_with(event, context)
        assert result["statusCode"] == 200

    def test_handler_with_unknown_event(self):
        """測試未知事件格式"""
        from processor_entry import handler

        event = {"unknown": "format"}
        context = Mock()

        result = handler(event, context)

        assert result["statusCode"] == 400
        assert "error" in json.loads(result["body"])

    @patch("processor_entry.process_eventbridge_event")
    def test_handler_exception(self, mock_process_eb):
        """測試處理函數異常"""
        from processor_entry import handler

        event = {"detail": {}}
        context = Mock()

        mock_process_eb.side_effect = Exception("Test error")

        result = handler(event, context)

        assert result["statusCode"] == 500
        assert "error" in json.loads(result["body"])


class TestEventBridgeEventProcessing:
    """測試 EventBridge 事件處理"""

    @patch("processor_entry.publish_completion_event")
    @patch("processor_entry.process_normalized_message")
    def test_process_eventbridge_success(self, mock_process, mock_publish):
        """測試成功處理 EventBridge 事件"""
        from processor_entry import process_eventbridge_event

        event = {
            "detail-type": "message.received",
            "detail": {
                "messageId": "test-uuid",
                "channel": {"type": "telegram", "channelId": "123"},
                "user": {"id": "tg:123"},
                "content": {"text": "Hello", "messageType": "text"},
                "context": {},
                "routing": {},
            },
        }
        context = Mock()

        mock_process.return_value = {
            "success": True,
            "response": "Test response",
            "user_id": "tg:123",
        }
        mock_publish.return_value = True

        result = process_eventbridge_event(event, context)

        assert result["statusCode"] == 200
        mock_process.assert_called_once()
        mock_publish.assert_called_once()

    @patch("processor_entry.publish_failure_event")
    @patch("processor_entry.process_normalized_message")
    def test_process_eventbridge_failure(self, mock_process, mock_publish):
        """測試處理失敗的 EventBridge 事件"""
        from processor_entry import process_eventbridge_event

        event = {
            "detail-type": "message.received",
            "detail": {"messageId": "test-uuid", "channel": {"type": "telegram"}},
        }
        context = Mock()

        mock_process.return_value = {"success": False, "error": "Processing failed"}
        mock_publish.return_value = True

        result = process_eventbridge_event(event, context)

        assert result["statusCode"] == 200
        mock_publish.assert_called_once()

    def test_process_eventbridge_wrong_detail_type(self):
        """測試不支援的 detail-type"""
        from processor_entry import process_eventbridge_event

        event = {"detail-type": "unsupported.type", "detail": {}}
        context = Mock()

        result = process_eventbridge_event(event, context)

        assert result["statusCode"] == 200
        assert result["body"] == "Event ignored"


class TestSQSEventProcessing:
    """測試 SQS 事件處理（向後兼容）"""

    @patch("processor_entry.conversation_agent")
    def test_process_sqs_event_success(self, mock_agent):
        """測試成功處理 SQS 事件"""
        from processor_entry import process_sqs_event

        event = {
            "Records": [
                {
                    "body": json.dumps(
                        {"message": {"from": {"id": 123456789}, "text": "Test message"}}
                    )
                }
            ]
        }
        context = Mock()

        mock_agent.process_message.return_value = "Response"

        result = process_sqs_event(event, context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["processed"] == 1
        mock_agent.process_message.assert_called_once_with("Test message")

    @patch("processor_entry.conversation_agent")
    def test_process_sqs_event_no_text(self, mock_agent):
        """測試處理無文字的 SQS 事件"""
        from processor_entry import process_sqs_event

        event = {"Records": [{"body": json.dumps({"message": {"from": {"id": 123456789}}})}]}
        context = Mock()

        result = process_sqs_event(event, context)

        assert result["statusCode"] == 200
        mock_agent.process_message.assert_not_called()


class TestNormalizedMessageProcessing:
    """測試標準化訊息處理"""

    @patch("processor_entry.conversation_agent")
    def test_process_text_message_success(self, mock_agent):
        """測試成功處理文字訊息"""
        from processor_entry import process_normalized_message

        normalized = {
            "messageId": "test-uuid",
            "channel": {"type": "telegram"},
            "user": {"id": "tg:123", "displayName": "Test User"},
            "content": {"text": "Hello AI", "messageType": "text"},
            "context": {"sessionId": "session-123"},
        }

        mock_agent.process_message.return_value = "AI response"

        result = process_normalized_message(normalized)

        assert result["success"] is True
        assert result["response"] == "AI response"
        assert result["user_id"] == "tg:123"
        assert result["session_id"] == "session-123"
        mock_agent.process_message.assert_called_once_with("Hello AI")

    @patch("processor_entry.conversation_agent")
    def test_process_unsupported_message_type(self, mock_agent):
        """測試不支援的訊息類型"""
        from processor_entry import process_normalized_message

        normalized = {
            "channel": {"type": "telegram"},
            "user": {"id": "tg:123", "displayName": "Test"},
            "content": {"messageType": "sticker"},
            "context": {},
        }

        result = process_normalized_message(normalized)

        assert result["success"] is False
        assert "Unsupported message type" in result["error"]
        mock_agent.process_message.assert_not_called()

    @patch("processor_entry.conversation_agent")
    def test_process_message_exception(self, mock_agent):
        """測試處理訊息時發生異常"""
        from processor_entry import process_normalized_message

        normalized = {
            "channel": {"type": "telegram"},
            "user": {"id": "tg:123", "displayName": "Test"},
            "content": {"text": "Test", "messageType": "text"},
            "context": {},
        }

        mock_agent.process_message.side_effect = Exception("Agent error")

        result = process_normalized_message(normalized)

        assert result["success"] is False
        assert "Agent error" in result["error"]


class TestEventPublishing:
    """測試事件發布功能"""

    @patch.dict("os.environ", {"EVENT_BUS_NAME": "test-bus"})
    @patch("processor_entry.get_eventbridge_client")
    def test_publish_completion_event_success(self, mock_get_client):
        """測試成功發布完成事件"""
        from processor_entry import publish_completion_event

        mock_evb = Mock()
        mock_evb.put_events.return_value = {"FailedEntryCount": 0}
        mock_get_client.return_value = mock_evb

        original = {"messageId": "test-uuid", "channel": {"type": "telegram"}}
        result_data = {"response": "AI response", "user_id": "tg:123", "session_id": "session-123"}

        success = publish_completion_event(original, result_data)

        assert success is True
        mock_evb.put_events.assert_called_once()

        # 驗證事件內容
        call_args = mock_evb.put_events.call_args[1]
        entry = call_args["Entries"][0]
        assert entry["Source"] == "agent-processor"
        assert entry["DetailType"] == "message.completed"

    @patch.dict("os.environ", {}, clear=True)
    def test_publish_completion_no_bus_configured(self):
        """測試未配置 EventBus 時跳過發布"""
        from processor_entry import publish_completion_event

        success = publish_completion_event({}, {})

        assert success is False

    @patch.dict("os.environ", {"EVENT_BUS_NAME": "test-bus"})
    @patch("processor_entry.get_eventbridge_client")
    def test_publish_failure_event_success(self, mock_get_client):
        """測試成功發布失敗事件"""
        from processor_entry import publish_failure_event

        mock_evb = Mock()
        mock_evb.put_events.return_value = {"FailedEntryCount": 0}
        mock_get_client.return_value = mock_evb

        original = {"messageId": "test-uuid", "channel": {"type": "telegram"}}
        result_data = {"error": "Processing failed", "user_id": "tg:123"}

        success = publish_failure_event(original, result_data)

        assert success is True

        # 驗證事件內容
        call_args = mock_evb.put_events.call_args[1]
        entry = call_args["Entries"][0]
        assert entry["Source"] == "agent-processor"
        assert entry["DetailType"] == "message.failed"

        detail = json.loads(entry["Detail"])
        assert detail["error"] == "Processing failed"
