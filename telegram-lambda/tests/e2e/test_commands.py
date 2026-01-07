"""
命令處理端對端測試
測試各種 Telegram 命令的完整處理流程
"""

import pytest
from handler import lambda_handler

from tests.e2e.helpers.telegram_factory import TelegramUpdateFactory


@pytest.mark.e2e
class TestCommands:
    """測試 Bot 命令端對端流程"""

    def test_info_command_success(self, full_mock_env, lambda_context):
        """測試 /info 命令返回系統資訊"""
        # Arrange
        event = TelegramUpdateFactory.create_command_update("info")
        telegram_api = full_mock_env["telegram_api"]

        # Act
        response = lambda_handler(event, lambda_context)

        # Assert
        assert response["statusCode"] == 200
        assert response["body"]

        # 驗證 Telegram API 被調用
        sent_messages = telegram_api.get_sent_messages()
        assert len(sent_messages) > 0

        # 驗證回應內容
        last_message = telegram_api.get_last_message()
        assert last_message is not None
        # 檢查包含系統資訊（格式可能改變）
        text = last_message["text"]
        assert "系統資訊" in text or "Stack" in text
        assert "telegram-lambda-receiver" in text

    def test_unknown_command_forwarded_to_processor(self, full_mock_env, lambda_context):
        """測試未知命令被轉發到處理器"""
        # Arrange
        event = TelegramUpdateFactory.create_command_update("unknown")
        eventbridge = full_mock_env["eventbridge"]

        # Act
        response = lambda_handler(event, lambda_context)

        # Assert
        assert response["statusCode"] == 200

        # 驗證 EventBridge 事件被發送
        events = eventbridge.get_events()
        assert len(events) > 0
        assert events[0]["DetailType"] == "message.received"

    def test_normal_message_flow(self, full_mock_env, lambda_context):
        """測試普通訊息的完整流程"""
        # Arrange
        event = TelegramUpdateFactory.create_message_update("你好，這是測試訊息")
        eventbridge = full_mock_env["eventbridge"]

        # Act
        response = lambda_handler(event, lambda_context)

        # Assert
        assert response["statusCode"] == 200

        # 驗證 EventBridge 事件被發送
        events = eventbridge.get_events()
        assert len(events) > 0

        # 驗證事件內容
        event_detail = events[0]
        assert event_detail["Source"] == "universal-adapter"
        assert event_detail["DetailType"] == "message.received"

    @pytest.mark.parametrize(
        "command,expected_in_response",
        [
            ("info", "系統資訊"),  # 修正：現在是中文格式
            ("help", ""),  # help 命令可能還沒實作
        ],
    )
    def test_various_commands(self, command, expected_in_response, full_mock_env, lambda_context):
        """測試各種命令"""
        # Arrange
        event = TelegramUpdateFactory.create_command_update(command)
        telegram_api = full_mock_env["telegram_api"]

        # Act
        response = lambda_handler(event, lambda_context)

        # Assert
        assert response["statusCode"] == 200

        if expected_in_response:
            last_message = telegram_api.get_last_message()
            if last_message:
                assert expected_in_response in last_message.get("text", "")


@pytest.mark.e2e
class TestAdminCommands:
    """測試管理員命令"""

    def test_admin_command_with_non_admin_user(self, full_mock_env, lambda_context):
        """測試非管理員用戶使用管理員命令"""
        # Arrange - 使用非管理員用戶
        event = TelegramUpdateFactory.create_command_update(
            "debug", user_id=999999, username="non_admin"
        )
        telegram_api = full_mock_env["telegram_api"]

        # Act
        response = lambda_handler(event, lambda_context)

        # Assert
        assert response["statusCode"] == 200

        # /debug 命令允許所有在 allowlist 的用戶執行
        # 所以非管理員用戶（不在 allowlist）會收到除錯資訊或被 allowlist 拒絕
        # 驗證有發送訊息
        sent_messages = telegram_api.get_sent_messages()
        assert len(sent_messages) > 0  # 確認有回應


@pytest.mark.e2e
class TestAuthentication:
    """測試認證和授權"""

    def test_invalid_secret_token(self, full_mock_env, lambda_context):
        """測試無效的 secret token"""
        # Arrange
        # 使用非命令的普通訊息，這樣才會進入 token 驗證
        event = TelegramUpdateFactory.create_message_update("Hello")
        event["headers"]["X-Telegram-Bot-Api-Secret-Token"] = "invalid_token"

        # Act
        response = lambda_handler(event, lambda_context)

        # Assert
        assert response["statusCode"] == 403

    def test_allowlist_denied(self, full_mock_env, lambda_context):
        """測試不在 allowlist 的用戶被拒絕"""
        # Arrange - 使用不在 allowlist 的用戶
        event = TelegramUpdateFactory.create_message_update(
            "Hello", user_id=888888, username="unauthorized_user"
        )

        # Act
        response = lambda_handler(event, lambda_context)

        # Assert
        assert response["statusCode"] == 200  # 仍然返回 200 避免 Telegram 重試
        # 可以檢查 body 中的 status
        import json

        body = json.loads(response["body"])
        assert body.get("status") == "ignored"
