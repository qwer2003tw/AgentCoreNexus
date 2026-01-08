"""
E2E 測試 Fixtures
提供測試環境設置和 Mock 服務
"""

import os
from unittest.mock import Mock, patch

import pytest

from tests.e2e.helpers.aws_mocks import (
    MockDynamoDB,
    MockEventBridge,
    MockTelegramAPI,
    create_mock_context,
)


@pytest.fixture(scope="function")
def mock_env():
    """設置測試環境變數"""
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_SECRETS_ARN": "arn:aws:secretsmanager:us-west-2:123456789:secret:test",
            "EVENT_BUS_NAME": "telegram-lambda-receiver-events",
            "ALLOWLIST_TABLE_NAME": "telegram-allowlist",
            "STACK_NAME": "telegram-lambda-receiver",
            "AWS_REGION": "us-west-2",
            "SQS_QUEUE_URL": "https://sqs.us-west-2.amazonaws.com/123456789/test-queue",
        },
    ):
        yield


@pytest.fixture(scope="function")
def mock_secrets():
    """Mock Secrets Manager"""
    # Mock get_telegram_bot_token 和 get_telegram_secret_token 直接返回值
    with (
        patch("secrets_manager.get_telegram_bot_token", return_value="test_bot_token"),
        patch("secrets_manager.get_telegram_secret_token", return_value="test_secret"),
        patch(
            "secrets_manager.get_telegram_secrets",
            return_value={"bot_token": "test_bot_token", "webhook_secret_token": "test_secret"},
        ),
    ):
        yield


@pytest.fixture(scope="function")
def mock_eventbridge():
    """Mock EventBridge 客戶端"""
    mock_evb = MockEventBridge()
    with patch("handler.get_eventbridge_client", return_value=mock_evb):
        yield mock_evb


@pytest.fixture(scope="function")
def mock_telegram_api():
    """Mock Telegram API 調用"""
    mock_api = MockTelegramAPI()

    async def mock_send_message(self, chat_id, text, **kwargs):
        """Mock Bot.send_message"""
        mock_api.send_message(chat_id, text, **kwargs)
        # 返回一個 Mock Message 對象
        message = Mock()
        message.message_id = len(mock_api.sent_messages)
        message.chat = Mock()
        message.chat.id = chat_id
        return message

    with patch("telegram_client.Bot.send_message", new=mock_send_message):
        yield mock_api


@pytest.fixture(scope="function")
def mock_allowlist():
    """Mock DynamoDB allowlist"""
    mock_db = MockDynamoDB()

    def mock_check(chat_id, username):
        return mock_db.check_allowed(chat_id, username)

    def mock_file_permission(chat_id):
        # 預設允許檔案權限（避免錯誤）
        return True

    with (
        patch("handler.check_allowed", side_effect=mock_check),
        patch("handler.check_file_permission", side_effect=mock_file_permission),
    ):
        yield mock_db


@pytest.fixture(scope="function")
def lambda_context():
    """創建 Mock Lambda Context"""
    return create_mock_context()


@pytest.fixture(scope="function")
def mock_sqs():
    """Mock SQS 客戶端"""

    def mock_send(body):
        # 總是返回成功
        return True

    with patch("handler.send_to_queue", side_effect=mock_send):
        yield


@pytest.fixture(scope="function")
def full_mock_env(
    mock_env, mock_secrets, mock_eventbridge, mock_telegram_api, mock_allowlist, mock_sqs
):
    """
    完整的測試環境
    包含所有必要的 mocks
    """
    return {
        "eventbridge": mock_eventbridge,
        "telegram_api": mock_telegram_api,
        "allowlist": mock_allowlist,
    }
