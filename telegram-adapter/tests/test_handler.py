"""
Unit tests for handler.py
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from src.handler import lambda_handler


class TestLambdaHandler:
    """測試 Lambda Handler 功能"""

    @pytest.fixture(autouse=True)
    def reset_command_router(self):
        """在每個測試前重置全域 command router"""
        import src.handler

        src.handler._command_router = None
        yield
        # 測試後也重置
        src.handler._command_router = None

    @pytest.fixture
    def valid_telegram_event(self):
        """有效的 Telegram webhook event"""
        return {
            "headers": {},
            "body": json.dumps(
                {
                    "message": {
                        "message_id": 123,
                        "chat": {"id": 123456789, "type": "private"},
                        "from": {"id": 123456789, "username": "test_user", "first_name": "Test"},
                        "text": "Hello, bot!",
                    }
                }
            ),
        }

    @pytest.fixture
    def mock_context(self):
        """Mock Lambda context"""
        context = MagicMock()
        context.function_name = "telegram-lambda-receiver"
        context.aws_request_id = "test-request-id"
        return context

    @patch("src.handler.send_to_queue")
    @patch("src.handler.check_allowed_with_session")
    def test_valid_user_message(
        self, mock_check_allowed_with_session, mock_send_to_queue, valid_telegram_event, mock_context
    ):
        """測試有效用戶訊息處理"""
        # 設定 mock 返回值（三元組）
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")
        mock_send_to_queue.return_value = True

        # 執行 handler
        response = lambda_handler(valid_telegram_event, mock_context)

        # 驗證
        assert response["statusCode"] == 200
        assert "body" in response
        body = json.loads(response["body"])
        assert body["status"] == "ok"

        # 驗證函數被正確調用
        mock_check_allowed_with_session.assert_called_once_with(123456789, "test_user")
        mock_send_to_queue.assert_called_once()

    @patch("src.handler.check_allowed_with_session")
    def test_unauthorized_user(self, mock_check_allowed_with_session, valid_telegram_event, mock_context):
        """測試未授權用戶訪問"""
        # 設定 mock 返回值（三元組，allowed=False）
        mock_check_allowed_with_session.return_value = (False, "test_user", "123456789")

        # 執行 handler
        response = lambda_handler(valid_telegram_event, mock_context)

        # 驗證：現在統一回應 200 OK
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ignored"

        # 驗證 check_allowed_with_session 被調用
        mock_check_allowed_with_session.assert_called_once_with(123456789, "test_user")

    def test_malformed_payload(self, mock_context):
        """測試格式錯誤的 payload"""
        event = {"body": "invalid json"}

        # 執行 handler
        response = lambda_handler(event, mock_context)

        # 驗證
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Invalid JSON"

    def test_missing_chat_id(self, mock_context):
        """測試缺少 chat_id 的訊息"""
        event = {"body": json.dumps({"message": {"text": "Hello"}})}

        # 執行 handler
        response = lambda_handler(event, mock_context)

        # 驗證
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Invalid webhook payload"

    @patch("src.handler.send_to_queue")
    @patch("src.handler.check_allowed_with_session")
    def test_sqs_send_failure(
        self, mock_check_allowed_with_session, mock_send_to_queue, valid_telegram_event, mock_context
    ):
        """測試 SQS 發送失敗"""
        # 設定 mock 返回值
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")
        mock_send_to_queue.return_value = False

        # 執行 handler
        response = lambda_handler(valid_telegram_event, mock_context)

        # 驗證：現在統一回應 200 OK
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "sqs_failed"

    @patch("src.handler.check_allowed_with_session")
    def test_check_allowed_exception(self, mock_check_allowed_with_session, valid_telegram_event, mock_context):
        """測試 check_allowed_with_session 拋出異常"""
        # 設定 mock 拋出異常
        mock_check_allowed_with_session.side_effect = Exception("Database error")

        # 執行 handler
        response = lambda_handler(valid_telegram_event, mock_context)

        # 驗證：現在統一回應 200 OK
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "error"

    @patch.dict(os.environ, {"TELEGRAM_SECRET_TOKEN": "test_secret_token_abc123"})
    @patch("src.handler.send_to_queue")
    @patch("src.handler.check_allowed_with_session")
    def test_valid_secret_token(
        self, mock_check_allowed_with_session, mock_send_to_queue, valid_telegram_event, mock_context
    ):
        """測試有效的 secret token"""
        # 設定 event 包含正確的 token
        valid_telegram_event["headers"] = {
            "X-Telegram-Bot-Api-Secret-Token": "test_secret_token_abc123"
        }

        # 設定 mock 返回值
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")
        mock_send_to_queue.return_value = True

        # 執行 handler
        response = lambda_handler(valid_telegram_event, mock_context)

        # 驗證通過
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ok"

    @patch.dict(os.environ, {"TELEGRAM_SECRET_TOKEN": "test_secret_token_abc123"})
    @patch("src.handler.check_allowed_with_session")
    def test_invalid_secret_token(self, mock_check_allowed_with_session, valid_telegram_event, mock_context):
        """測試無效的 secret token"""
        # 設定 event 包含錯誤的 token
        valid_telegram_event["headers"] = {"X-Telegram-Bot-Api-Secret-Token": "wrong_token"}

        # Mock check_allowed_with_session 以避免實際檢查
        mock_check_allowed_with_session.return_value = (False, "test_user", "123456789")

        # 執行 handler
        response = lambda_handler(valid_telegram_event, mock_context)

        # 驗證：現在統一回應 200 OK
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ignored"

    @patch.dict(os.environ, {"TELEGRAM_SECRET_TOKEN": "test_secret_token_abc123"})
    @patch("src.handler.check_allowed_with_session")
    def test_missing_secret_token(self, mock_check_allowed_with_session, valid_telegram_event, mock_context):
        """測試缺少 secret token"""
        # event 不包含 token header
        valid_telegram_event["headers"] = {}

        # Mock check_allowed_with_session 以避免實際檢查
        mock_check_allowed_with_session.return_value = (False, "test_user", "123456789")

        # 執行 handler
        response = lambda_handler(valid_telegram_event, mock_context)

        # 驗證：現在統一回應 200 OK
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ignored"

    @patch.dict(os.environ, {"TELEGRAM_SECRET_TOKEN": "test_secret_token_abc123"})
    @patch("src.handler.send_to_queue")
    @patch("src.handler.check_allowed_with_session")
    def test_lowercase_secret_token_header(
        self, mock_check_allowed_with_session, mock_send_to_queue, valid_telegram_event, mock_context
    ):
        """測試小寫的 secret token header"""
        # 設定 event 包含小寫 header key 的正確 token
        valid_telegram_event["headers"] = {
            "x-telegram-bot-api-secret-token": "test_secret_token_abc123"
        }

        # 設定 mock 返回值
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")
        mock_send_to_queue.return_value = True

        # 執行 handler
        response = lambda_handler(valid_telegram_event, mock_context)

        # 驗證通過（支援小寫 header）
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ok"

    @patch.dict(os.environ, {"TELEGRAM_SECRET_TOKEN": ""})
    @patch("src.handler.send_to_queue")
    @patch("src.handler.check_allowed_with_session")
    def test_no_secret_token_configured(
        self, mock_check_allowed_with_session, mock_send_to_queue, valid_telegram_event, mock_context
    ):
        """測試未設定 secret token 時（向後相容）"""
        # 沒有設定 token header
        valid_telegram_event["headers"] = {}

        # 設定 mock 返回值
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")
        mock_send_to_queue.return_value = True

        # 執行 handler
        response = lambda_handler(valid_telegram_event, mock_context)

        # 驗證通過（跳過 token 驗證）
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ok"

    @patch("src.handler.check_allowed_with_session")
    @patch("src.commands.handlers.debug_handler.telegram_client.send_debug_info")
    def test_debug_command(self, mock_send_debug, mock_check_allowed_with_session, mock_context):
        """測試 /debug test 指令（通過指令路由器）"""
        # 創建 debug 指令的 event
        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "update_id": 123456,
                    "message": {
                        "message_id": 123,
                        "date": 1234567890,
                        "chat": {"id": 123456789, "type": "private"},
                        "from": {
                            "id": 123456789,
                            "username": "test_user",
                            "first_name": "Test",
                            "is_bot": False,
                        },
                        "text": "/debug test",
                    },
                }
            ),
        }

        # 設定 mock 返回值
        mock_send_debug.return_value = True
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")

        # 執行 handler
        response = lambda_handler(event, mock_context)

        # 驗證
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "command_handled"

        # 驗證 send_debug_info 被正確調用
        mock_send_debug.assert_called_once_with(123456789, event)

    @patch("src.handler.check_allowed_with_session")
    @patch("src.commands.handlers.debug_handler.telegram_client.send_debug_info")
    def test_debug_command_alone(self, mock_send_debug, mock_check_allowed_with_session, mock_context):
        """測試單獨的 /debug 指令"""
        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "update_id": 123456,
                    "message": {
                        "message_id": 123,
                        "date": 1234567890,
                        "chat": {"id": 123456789, "type": "private"},
                        "from": {
                            "id": 123456789,
                            "username": "test_user",
                            "first_name": "Test",
                            "is_bot": False,
                        },
                        "text": "/debug",
                    },
                }
            ),
        }

        mock_send_debug.return_value = True
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")
        response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "command_handled"
        mock_send_debug.assert_called_once()

    @patch("src.handler.check_allowed_with_session")
    @patch("src.commands.handlers.debug_handler.telegram_client.send_debug_info")
    def test_debug_command_with_number(self, mock_send_debug, mock_check_allowed_with_session, mock_context):
        """測試 /debug 123 指令"""
        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "update_id": 123456,
                    "message": {
                        "message_id": 123,
                        "date": 1234567890,
                        "chat": {"id": 123456789, "type": "private"},
                        "from": {
                            "id": 123456789,
                            "username": "test_user",
                            "first_name": "Test",
                            "is_bot": False,
                        },
                        "text": "/debug 123",
                    },
                }
            ),
        }

        mock_send_debug.return_value = True
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")
        response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "command_handled"

    @patch("src.handler.check_allowed_with_session")
    @patch("src.commands.handlers.debug_handler.telegram_client.send_debug_info")
    def test_debug_command_with_multiple_words(
        self, mock_send_debug, mock_check_allowed_with_session, mock_context
    ):
        """測試 /debug any string 指令"""
        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "update_id": 123456,
                    "message": {
                        "message_id": 123,
                        "date": 1234567890,
                        "chat": {"id": 123456789, "type": "private"},
                        "from": {
                            "id": 123456789,
                            "username": "test_user",
                            "first_name": "Test",
                            "is_bot": False,
                        },
                        "text": "/debug hello world",
                    },
                }
            ),
        }

        mock_send_debug.return_value = True
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")
        response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "command_handled"

    @patch("src.handler.send_to_queue")
    @patch("src.handler.check_allowed_with_session")
    def test_debug_without_space_should_not_trigger(
        self, mock_check_allowed_with_session, mock_send_to_queue, mock_context
    ):
        """測試 /debugtest 不應該觸發除錯功能"""
        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "message": {
                        "chat": {"id": 123456789},
                        "from": {"username": "test_user"},
                        "text": "/debugtest",
                    }
                }
            ),
        }

        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")
        mock_send_to_queue.return_value = True

        response = lambda_handler(event, mock_context)

        # 應該走正常流程，不是除錯流程
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ok"
        mock_check_allowed_with_session.assert_called_once()
        mock_send_to_queue.assert_called_once()

    @patch("src.handler.check_allowed_with_session")
    @patch("src.commands.handlers.debug_handler.telegram_client.send_debug_info")
    def test_debug_command_with_spaces(self, mock_send_debug, mock_check_allowed_with_session, mock_context):
        """測試 /debug test 指令（帶空格）"""
        # 創建帶空格的 debug 指令
        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "update_id": 123456,
                    "message": {
                        "message_id": 123,
                        "date": 1234567890,
                        "chat": {"id": 123456789, "type": "private"},
                        "from": {
                            "id": 123456789,
                            "username": "test_user",
                            "first_name": "Test",
                            "is_bot": False,
                        },
                        "text": "  /debug test  ",  # 前後有空格
                    },
                }
            ),
        }

        # 設定 mock
        mock_send_debug.return_value = True
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")

        # 執行
        response = lambda_handler(event, mock_context)

        # 驗證
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "command_handled"

    @patch("src.handler.send_to_queue")
    @patch("src.handler.check_allowed_with_session")
    @patch("src.commands.handlers.debug_handler.telegram_client.send_debug_info")
    def test_debug_command_send_failure(
        self, mock_send_debug, mock_check_allowed_with_session, mock_send_to_queue, mock_context
    ):
        """測試 debug 指令發送失敗"""
        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "update_id": 123456,
                    "message": {
                        "message_id": 123,
                        "date": 1234567890,
                        "chat": {"id": 123456789, "type": "private"},
                        "from": {
                            "id": 123456789,
                            "username": "test_user",
                            "first_name": "Test",
                            "is_bot": False,
                        },
                        "text": "/debug test",
                    },
                }
            ),
        }

        # 設定 mock 返回失敗
        mock_send_debug.return_value = False
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")
        mock_send_to_queue.return_value = False  # SQS 也失敗

        # 執行
        response = lambda_handler(event, mock_context)

        # 驗證：當 debug 發送失敗，會繼續正常流程，如果 SQS 也失敗則返回 sqs_failed
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "sqs_failed"

    @patch("src.handler.send_to_queue")
    @patch("src.handler.check_allowed_with_session")
    def test_non_debug_command(self, mock_check_allowed_with_session, mock_send_to_queue, mock_context):
        """測試非 debug 指令的正常處理"""
        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "message": {
                        "chat": {"id": 123456789},
                        "from": {"username": "test_user"},
                        "text": "/help",  # 其他指令，不是 /debug
                    }
                }
            ),
        }

        # 設定 mock
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")
        mock_send_to_queue.return_value = True

        # 執行
        response = lambda_handler(event, mock_context)

        # 驗證：應該走正常流程而不是 debug 流程
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ok"
        mock_check_allowed_with_session.assert_called_once()
        mock_send_to_queue.assert_called_once()

    @patch("src.telegram_client.send_debug_info")
    def test_debug_command_missing_chat_id(self, mock_send_debug, mock_context):
        """測試 debug 指令但缺少 chat_id"""
        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "message": {
                        "text": "/debug test"
                        # 缺少 chat 欄位
                    }
                }
            ),
        }

        # 執行
        response = lambda_handler(event, mock_context)

        # 驗證：應該回傳錯誤而不是呼叫 send_debug_info
        assert response["statusCode"] == 400
        mock_send_debug.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "STACK_NAME": "test-stack",
            "AWS_REGION": "us-west-2",
            "AWS_LAMBDA_FUNCTION_NAME": "test-function",
        },
    )
    @patch("src.handler.check_allowed_with_session")
    @patch("src.commands.handlers.info_handler.telegram_client.send_message")
    @patch("src.commands.handlers.info_handler.boto3.client")
    def test_info_command(
        self, mock_boto_client, mock_send_message, mock_check_allowed_with_session, mock_context
    ):
        """測試 /info 指令（通過指令路由器）"""
        from datetime import datetime

        # 創建 info 指令的 event
        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "update_id": 123456,
                    "message": {
                        "message_id": 123,
                        "date": 1234567890,
                        "chat": {"id": 123456789, "type": "private"},
                        "from": {
                            "id": 123456789,
                            "username": "test_user",
                            "first_name": "Test",
                            "is_bot": False,
                        },
                        "text": "/info",
                    },
                }
            ),
        }

        # Mock CloudFormation client
        mock_cfn = MagicMock()
        mock_boto_client.return_value = mock_cfn

        # Mock CloudFormation response
        mock_cfn.describe_stacks.return_value = {
            "Stacks": [
                {
                    "StackName": "test-stack",
                    "StackStatus": "UPDATE_COMPLETE",
                    "CreationTime": datetime(2025, 1, 1, 10, 0, 0),
                    "LastUpdatedTime": datetime(2025, 1, 5, 11, 0, 23),
                }
            ]
        }

        # 設定 mock 返回值
        mock_send_message.return_value = True
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")

        # 執行 handler
        response = lambda_handler(event, mock_context)

        # 驗證
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "command_handled"

        # 驗證 send_message 被正確調用
        mock_send_message.assert_called_once()
        call_args = mock_send_message.call_args
        assert call_args[0][0] == 123456789  # chat_id
        info_text = call_args[0][1]
        assert "📊 系統資訊" in info_text
        assert "2025-01-05 11:00:23 UTC" in info_text
        assert "test-stack" in info_text
        assert "UPDATE_COMPLETE" in info_text

    @patch.dict(os.environ, {"STACK_NAME": "test-stack", "AWS_REGION": "us-west-2"})
    @patch("src.handler.check_allowed_with_session")
    @patch("src.commands.handlers.info_handler.telegram_client.send_message")
    @patch("src.commands.handlers.info_handler.boto3.client")
    def test_info_command_with_text(
        self, mock_boto_client, mock_send_message, mock_check_allowed_with_session, mock_context
    ):
        """測試 /info test 指令（帶額外文字）"""
        from datetime import datetime

        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "update_id": 123456,
                    "message": {
                        "message_id": 123,
                        "date": 1234567890,
                        "chat": {"id": 123456789, "type": "private"},
                        "from": {
                            "id": 123456789,
                            "username": "test_user",
                            "first_name": "Test",
                            "is_bot": False,
                        },
                        "text": "/info test",
                    },
                }
            ),
        }

        # Mock CloudFormation
        mock_cfn = MagicMock()
        mock_boto_client.return_value = mock_cfn
        mock_cfn.describe_stacks.return_value = {
            "Stacks": [
                {
                    "StackName": "test-stack",
                    "StackStatus": "CREATE_COMPLETE",
                    "CreationTime": datetime(2025, 1, 1, 10, 0, 0),
                }
            ]
        }

        mock_send_message.return_value = True
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")

        response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "command_handled"
        mock_send_message.assert_called_once()

    @patch.dict(os.environ, {"STACK_NAME": "test-stack", "AWS_REGION": "us-west-2"})
    @patch("src.handler.check_allowed_with_session")
    @patch("src.commands.handlers.info_handler.telegram_client.send_message")
    @patch("src.commands.handlers.info_handler.boto3.client")
    def test_info_command_cloudformation_access_denied(
        self, mock_boto_client, mock_send_message, mock_check_allowed_with_session, mock_context
    ):
        """測試 /info 指令遇到權限不足錯誤"""
        from botocore.exceptions import ClientError

        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "update_id": 123456,
                    "message": {
                        "message_id": 123,
                        "date": 1234567890,
                        "chat": {"id": 123456789, "type": "private"},
                        "from": {
                            "id": 123456789,
                            "username": "test_user",
                            "first_name": "Test",
                            "is_bot": False,
                        },
                        "text": "/info",
                    },
                }
            ),
        }

        # Mock CloudFormation client 拋出 AccessDenied 錯誤
        mock_cfn = MagicMock()
        mock_boto_client.return_value = mock_cfn
        mock_cfn.describe_stacks.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "DescribeStacks"
        )
        mock_cfn.exceptions.ClientError = ClientError

        mock_send_message.return_value = True
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")

        response = lambda_handler(event, mock_context)

        # 驗證：應該返回成功但發送錯誤訊息
        assert response["statusCode"] == 200
        mock_send_message.assert_called_once()
        call_args = mock_send_message.call_args[0][1]
        assert "權限不足" in call_args

    @patch.dict(os.environ, {"STACK_NAME": "non-existent-stack", "AWS_REGION": "us-west-2"})
    @patch("src.handler.check_allowed_with_session")
    @patch("src.commands.handlers.info_handler.telegram_client.send_message")
    @patch("src.commands.handlers.info_handler.boto3.client")
    def test_info_command_stack_not_found(
        self, mock_boto_client, mock_send_message, mock_check_allowed_with_session, mock_context
    ):
        """測試 /info 指令找不到 Stack"""
        from botocore.exceptions import ClientError

        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "update_id": 123456,
                    "message": {
                        "message_id": 123,
                        "date": 1234567890,
                        "chat": {"id": 123456789, "type": "private"},
                        "from": {
                            "id": 123456789,
                            "username": "test_user",
                            "first_name": "Test",
                            "is_bot": False,
                        },
                        "text": "/info",
                    },
                }
            ),
        }

        # Mock CloudFormation client 拋出 ValidationError
        mock_cfn = MagicMock()
        mock_boto_client.return_value = mock_cfn
        mock_cfn.describe_stacks.side_effect = ClientError(
            {"Error": {"Code": "ValidationError", "Message": "Stack does not exist"}},
            "DescribeStacks",
        )
        mock_cfn.exceptions.ClientError = ClientError

        mock_send_message.return_value = True
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")

        response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 200
        mock_send_message.assert_called_once()
        call_args = mock_send_message.call_args[0][1]
        assert "找不到 Stack" in call_args

    @patch.dict(os.environ, {"STACK_NAME": "test-stack", "AWS_REGION": "us-west-2"})
    @patch("src.handler.check_allowed_with_session")
    @patch("src.commands.handlers.info_handler.telegram_client.send_message")
    @patch("src.commands.handlers.info_handler.boto3.client")
    def test_info_command_api_error(
        self, mock_boto_client, mock_send_message, mock_check_allowed_with_session, mock_context
    ):
        """測試 /info 指令遇到一般 API 錯誤"""
        from botocore.exceptions import ClientError

        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "update_id": 123456,
                    "message": {
                        "message_id": 123,
                        "date": 1234567890,
                        "chat": {"id": 123456789, "type": "private"},
                        "from": {
                            "id": 123456789,
                            "username": "test_user",
                            "first_name": "Test",
                            "is_bot": False,
                        },
                        "text": "/info",
                    },
                }
            ),
        }

        # Mock CloudFormation client 拋出一般錯誤
        mock_cfn = MagicMock()
        mock_boto_client.return_value = mock_cfn
        mock_cfn.describe_stacks.side_effect = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}}, "DescribeStacks"
        )
        mock_cfn.exceptions.ClientError = ClientError

        mock_send_message.return_value = True
        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")

        response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 200
        mock_send_message.assert_called_once()
        call_args = mock_send_message.call_args[0][1]
        assert "API 錯誤" in call_args

    @patch("src.handler.send_to_queue")
    @patch("src.handler.check_allowed_with_session")
    def test_info_without_space_should_not_trigger(
        self, mock_check_allowed_with_session, mock_send_to_queue, mock_context
    ):
        """測試 /infotest 不應該觸發 info 指令"""
        event = {
            "headers": {},
            "body": json.dumps(
                {
                    "message": {
                        "chat": {"id": 123456789},
                        "from": {"username": "test_user"},
                        "text": "/infotest",
                    }
                }
            ),
        }

        mock_check_allowed_with_session.return_value = (True, "test_user", "123456789")
        mock_send_to_queue.return_value = True

        response = lambda_handler(event, mock_context)

        # 應該走正常流程，不是 info 流程
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ok"
        mock_check_allowed_with_session.assert_called_once()
        mock_send_to_queue.assert_called_once()