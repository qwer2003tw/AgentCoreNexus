"""
Unit tests for sqs_client.py
"""

from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from src.sqs_client import get_queue_attributes, send_to_queue


class TestSQSClient:
    """測試 SQS 客戶端功能"""

    @pytest.fixture
    def sample_message(self):
        """範例 Telegram 訊息"""
        return {
            "message": {
                "message_id": 123,
                "chat": {"id": 123456789},
                "from": {"username": "test_user"},
                "text": "Hello, bot!",
            }
        }

    @patch(
        "src.sqs_client.queue_url", "https://sqs.us-east-1.amazonaws.com/123456789/telegram-inbound"
    )
    @patch("src.sqs_client.sqs")
    def test_send_message_success(self, mock_sqs, sample_message):
        """測試成功發送訊息到 SQS"""
        # 設定 mock 返回值
        mock_sqs.send_message.return_value = {"MessageId": "test-message-id-123"}

        # 執行測試
        result = send_to_queue(sample_message)

        # 驗證
        assert result is True
        mock_sqs.send_message.assert_called_once()

        # 驗證呼叫參數
        call_args = mock_sqs.send_message.call_args
        assert (
            call_args[1]["QueueUrl"]
            == "https://sqs.us-east-1.amazonaws.com/123456789/telegram-inbound"
        )
        assert "MessageBody" in call_args[1]
        assert "MessageAttributes" in call_args[1]

    @patch("src.sqs_client.queue_url", "")
    def test_send_message_no_queue_url(self, sample_message):
        """測試缺少 QUEUE_URL 環境變數"""
        # 執行測試
        result = send_to_queue(sample_message)

        # 驗證
        assert result is False

    @patch(
        "src.sqs_client.queue_url", "https://sqs.us-east-1.amazonaws.com/123456789/telegram-inbound"
    )
    @patch("src.sqs_client.sqs")
    def test_send_message_retry_success(self, mock_sqs, sample_message):
        """測試重試機制成功"""
        # 設定 mock：第一次失敗，第二次成功
        error_response = {"Error": {"Code": "ServiceUnavailable"}}
        mock_sqs.send_message.side_effect = [
            ClientError(error_response, "SendMessage"),
            {"MessageId": "test-message-id-123"},
        ]

        # 執行測試
        result = send_to_queue(sample_message, retry_count=3)

        # 驗證
        assert result is True
        assert mock_sqs.send_message.call_count == 2

    @patch(
        "src.sqs_client.queue_url", "https://sqs.us-east-1.amazonaws.com/123456789/telegram-inbound"
    )
    @patch("src.sqs_client.sqs")
    def test_send_message_retry_exhausted(self, mock_sqs, sample_message):
        """測試重試次數耗盡"""
        # 設定 mock：持續失敗
        error_response = {"Error": {"Code": "ServiceUnavailable"}}
        mock_sqs.send_message.side_effect = ClientError(error_response, "SendMessage")

        # 執行測試
        result = send_to_queue(sample_message, retry_count=3)

        # 驗證
        assert result is False
        assert mock_sqs.send_message.call_count == 3

    @patch(
        "src.sqs_client.queue_url", "https://sqs.us-east-1.amazonaws.com/123456789/telegram-inbound"
    )
    @patch("src.sqs_client.sqs")
    def test_send_message_unexpected_error(self, mock_sqs, sample_message):
        """測試未預期的錯誤"""
        # 設定 mock：拋出一般異常
        mock_sqs.send_message.side_effect = Exception("Unexpected error")

        # 執行測試
        result = send_to_queue(sample_message, retry_count=2)

        # 驗證
        assert result is False
        assert mock_sqs.send_message.call_count == 2

    @patch(
        "src.sqs_client.queue_url", "https://sqs.us-east-1.amazonaws.com/123456789/telegram-inbound"
    )
    @patch("src.sqs_client.sqs")
    def test_get_queue_attributes_success(self, mock_sqs):
        """測試成功取得 Queue 屬性"""
        # 設定 mock 返回值
        mock_sqs.get_queue_attributes.return_value = {
            "Attributes": {
                "ApproximateNumberOfMessages": "5",
                "ApproximateNumberOfMessagesNotVisible": "2",
            }
        }

        # 執行測試
        result = get_queue_attributes()

        # 驗證
        assert "ApproximateNumberOfMessages" in result
        assert result["ApproximateNumberOfMessages"] == "5"
        assert result["ApproximateNumberOfMessagesNotVisible"] == "2"

    @patch(
        "src.sqs_client.queue_url", "https://sqs.us-east-1.amazonaws.com/123456789/telegram-inbound"
    )
    @patch("src.sqs_client.sqs")
    def test_get_queue_attributes_failure(self, mock_sqs):
        """測試取得 Queue 屬性失敗"""
        # 設定 mock 拋出異常
        error_response = {"Error": {"Code": "QueueDoesNotExist"}}
        mock_sqs.get_queue_attributes.side_effect = ClientError(
            error_response, "GetQueueAttributes"
        )

        # 執行測試
        result = get_queue_attributes()

        # 驗證
        assert result == {}
