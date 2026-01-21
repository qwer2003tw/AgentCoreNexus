"""
Unit tests for telegram_client.py (using python-telegram-bot)
"""

from unittest.mock import patch

from src.telegram_client import (
    MAX_MESSAGE_LENGTH,
    _split_message,
    send_debug_info,
    send_long_message,
    send_message,
)


class TestTelegramClient:
    """測試 Telegram Client 功能"""

    @patch("src.telegram_client.get_bot_token")
    @patch("src.telegram_client.asyncio.run")
    def test_send_message_success(self, mock_run, mock_get_token):
        """測試成功發送訊息"""
        # 設定 mock
        mock_get_token.return_value = "test_bot_token"
        mock_run.return_value = True

        # 執行
        result = send_message(12345, "Test message")

        # 驗證
        assert result is True
        mock_run.assert_called_once()

    @patch("src.telegram_client.get_bot_token")
    def test_send_message_no_token(self, mock_get_token):
        """測試沒有 Bot Token 的情況"""
        # 設定 mock
        mock_get_token.return_value = ""

        # 執行
        result = send_message(12345, "Test message")

        # 驗證
        assert result is False

    @patch("src.telegram_client.get_bot_token")
    @patch("src.telegram_client.asyncio.run")
    def test_send_message_exception(self, mock_run, mock_get_token):
        """測試發送時發生異常"""
        # 設定 mock
        mock_get_token.return_value = "test_bot_token"
        mock_run.side_effect = Exception("Unexpected error")

        # 執行
        result = send_message(12345, "Test message")

        # 驗證
        assert result is False

    def test_split_message_short(self):
        """測試短訊息不需要分割"""
        text = "Short message"
        result = _split_message(text, MAX_MESSAGE_LENGTH)

        assert len(result) == 1
        assert result[0] == text

    def test_split_message_long(self):
        """測試長訊息分割"""
        # 創建一個超過限制的長文字
        text = "A" * (MAX_MESSAGE_LENGTH + 100)
        result = _split_message(text, MAX_MESSAGE_LENGTH)

        # 驗證
        assert len(result) == 2
        assert len(result[0]) <= MAX_MESSAGE_LENGTH
        assert len(result[1]) <= MAX_MESSAGE_LENGTH
        assert "".join(result) == text

    def test_split_message_with_newlines(self):
        """測試在換行符處分割"""
        # 創建帶換行符的長文字
        part1 = "A" * (MAX_MESSAGE_LENGTH - 100)
        part2 = "B" * 200
        text = part1 + "\n" + part2

        result = _split_message(text, MAX_MESSAGE_LENGTH)

        # 驗證在換行符處分割
        assert len(result) == 2
        assert result[0].endswith("\n")

    @patch("src.telegram_client.get_bot_token")
    @patch("src.telegram_client.asyncio.run")
    def test_send_long_message_success(self, mock_run, mock_get_token):
        """測試發送長訊息"""
        # 設定 mock
        mock_get_token.return_value = "test_bot_token"
        mock_run.return_value = True

        # 創建長文字
        text = "A" * (MAX_MESSAGE_LENGTH + 100)

        # 執行
        result = send_long_message(12345, text)

        # 驗證
        assert result is True
        mock_run.assert_called_once()

    @patch("src.telegram_client.get_bot_token")
    def test_send_long_message_no_token(self, mock_get_token):
        """測試發送長訊息但沒有 token"""
        # 設定 mock
        mock_get_token.return_value = ""

        # 創建長文字
        text = "A" * (MAX_MESSAGE_LENGTH + 100)

        # 執行
        result = send_long_message(12345, text)

        # 驗證
        assert result is False

    @patch("src.telegram_client.get_bot_token")
    @patch("src.telegram_client.asyncio.run")
    def test_send_long_message_exception(self, mock_run, mock_get_token):
        """測試發送長訊息時發生異常"""
        # 設定 mock
        mock_get_token.return_value = "test_bot_token"
        mock_run.side_effect = Exception("Unexpected error")

        # 創建長文字
        text = "A" * (MAX_MESSAGE_LENGTH + 100)

        # 執行
        result = send_long_message(12345, text)

        # 驗證
        assert result is False

    @patch("src.telegram_client.send_message")
    def test_send_debug_info_success(self, mock_send):
        """測試發送除錯資訊"""
        # 設定 mock
        mock_send.return_value = True

        # 創建測試 event
        event = {
            "headers": {"Content-Type": "application/json"},
            "body": '{"message": {"text": "/debug test"}}',
        }

        # 執行
        result = send_debug_info(12345, event)

        # 驗證
        assert result is True
        mock_send.assert_called_once()

        # 檢查發送的內容包含 JSON
        call_args = mock_send.call_args
        assert call_args[0][0] == 12345  # chat_id
        assert "```json" in call_args[0][1]  # text 包含 JSON 標記
        assert '"headers"' in call_args[0][1]  # 包含 event 內容

    @patch("src.telegram_client.send_message")
    def test_send_debug_info_failure(self, mock_send):
        """測試發送除錯資訊失敗"""
        # 設定 mock
        mock_send.return_value = False

        event = {"test": "data"}

        # 執行
        result = send_debug_info(12345, event)

        # 驗證
        assert result is False

    @patch("src.telegram_client.send_message")
    def test_send_debug_info_exception(self, mock_send):
        """測試發送除錯資訊時發生異常"""
        # 設定 mock 拋出異常
        mock_send.side_effect = Exception("Unexpected error")

        event = {"test": "data"}

        # 執行
        result = send_debug_info(12345, event)

        # 驗證
        assert result is False
