"""
Tests for Identity Binding Commands
測試 /bind, /mybindings, /unbind 命令
"""

import sys
from unittest.mock import Mock, patch

import pytest
from telegram import Chat, Message, Update, User

# Mock identity_service before importing handlers
mock_identity_service_module = Mock()
sys.modules["identity_service"] = mock_identity_service_module

from commands.handlers.bind_handler import BindCommandHandler  # noqa: E402
from commands.handlers.mybindings_handler import MyBindingsCommandHandler  # noqa: E402
from commands.handlers.unbind_handler import UnbindCommandHandler  # noqa: E402


@pytest.fixture
def mock_identity_service():
    """創建 mock IdentityService"""
    service = Mock()
    service.generate_binding_code.return_value = {
        "code": "123456",
        "expires_at": 1234567890,
        "expires_in_minutes": 10,
    }
    service.get_bindings.return_value = None
    service.unbind.return_value = True
    return service


@pytest.fixture
def mock_update():
    """創建 mock Telegram Update"""
    user = User(id=316743844, first_name="Test", is_bot=False, username="testuser")
    chat = Chat(id=316743844, type="private")
    message = Message(message_id=1, date=None, chat=chat, from_user=user, text="/bind")
    update = Update(update_id=1, message=message)
    return update


class TestBindCommandHandler:
    """測試 /bind 命令處理器"""

    def test_can_handle_bind_command(self):
        """測試能識別 /bind 命令"""
        handler = BindCommandHandler()
        assert handler.can_handle("/bind")
        assert handler.can_handle("/bind ")
        assert handler.can_handle(" /bind")
        assert not handler.can_handle("/mybindings")
        assert not handler.can_handle("hello")

    @patch("commands.handlers.bind_handler.telegram_client")
    @patch("commands.handlers.bind_handler.os.getenv")
    def test_handle_bind_success(
        self, mock_getenv, mock_telegram_client, mock_identity_service, mock_update
    ):
        """測試成功生成綁定碼"""
        # Setup
        mock_getenv.side_effect = lambda k: {
            "BINDING_CODES_TABLE": "test-binding-codes",
            "IDENTITY_MAP_TABLE": "test-identity-map",
        }.get(k)

        mock_telegram_client.send_message.return_value = True

        handler = BindCommandHandler()
        handler._identity_service = mock_identity_service

        # Execute
        result = handler.handle(mock_update, {})

        # Verify
        assert result
        mock_identity_service.generate_binding_code.assert_called_once_with("316743844")
        mock_telegram_client.send_message.assert_called_once()

        # 驗證訊息內容包含綁定碼
        call_args = mock_telegram_client.send_message.call_args
        assert "123456" in call_args[0][1]  # 綁定碼在訊息中
        assert "10 分鐘" in call_args[0][1]  # 有效期限在訊息中

    @patch("commands.handlers.bind_handler.telegram_client")
    @patch("commands.handlers.bind_handler.os.getenv")
    def test_handle_bind_service_unavailable(self, mock_getenv, mock_telegram_client, mock_update):
        """測試服務不可用時的處理"""
        # Setup - 沒有配置表名稱
        mock_getenv.return_value = None
        mock_telegram_client.send_message.return_value = True

        handler = BindCommandHandler()

        # Execute
        result = handler.handle(mock_update, {})

        # Verify
        assert result
        call_args = mock_telegram_client.send_message.call_args
        assert "暫時不可用" in call_args[0][1]

    @patch("commands.handlers.bind_handler.telegram_client")
    @patch("commands.handlers.bind_handler.os.getenv")
    def test_handle_bind_generation_error(
        self, mock_getenv, mock_telegram_client, mock_identity_service, mock_update
    ):
        """測試綁定碼生成失敗"""
        # Setup
        mock_getenv.side_effect = lambda k: {
            "BINDING_CODES_TABLE": "test-binding-codes",
            "IDENTITY_MAP_TABLE": "test-identity-map",
        }.get(k)

        mock_identity_service.generate_binding_code.side_effect = Exception("DynamoDB error")
        mock_telegram_client.send_message.return_value = True

        handler = BindCommandHandler()
        handler._identity_service = mock_identity_service

        # Execute
        result = handler.handle(mock_update, {})

        # Verify
        assert result
        call_args = mock_telegram_client.send_message.call_args
        assert "失敗" in call_args[0][1]


class TestMyBindingsCommandHandler:
    """測試 /mybindings 命令處理器"""

    def test_can_handle_mybindings_command(self):
        """測試能識別 /mybindings 命令"""
        handler = MyBindingsCommandHandler()
        assert handler.can_handle("/mybindings")
        assert handler.can_handle("/mybindings ")
        assert not handler.can_handle("/bind")

    @patch("commands.handlers.mybindings_handler.telegram_client")
    @patch("commands.handlers.mybindings_handler.os.getenv")
    def test_handle_mybindings_no_bindings(
        self, mock_getenv, mock_telegram_client, mock_identity_service, mock_update
    ):
        """測試沒有綁定時的回應"""
        # Setup
        mock_getenv.side_effect = lambda k: {
            "BINDING_CODES_TABLE": "test-binding-codes",
            "IDENTITY_MAP_TABLE": "test-identity-map",
        }.get(k)

        mock_identity_service.get_bindings.return_value = None
        mock_telegram_client.send_message.return_value = True

        handler = MyBindingsCommandHandler()
        handler._identity_service = mock_identity_service

        # Execute
        result = handler.handle(mock_update, {})

        # Verify
        assert result
        mock_identity_service.get_bindings.assert_called_once_with("tg:316743844")

        call_args = mock_telegram_client.send_message.call_args
        assert "沒有綁定" in call_args[0][1]
        assert "/bind" in call_args[0][1]

    @patch("commands.handlers.mybindings_handler.telegram_client")
    @patch("commands.handlers.mybindings_handler.os.getenv")
    def test_handle_mybindings_with_bindings(
        self, mock_getenv, mock_telegram_client, mock_identity_service, mock_update
    ):
        """測試有綁定時的回應"""
        # Setup
        mock_getenv.side_effect = lambda k: {
            "BINDING_CODES_TABLE": "test-binding-codes",
            "IDENTITY_MAP_TABLE": "test-identity-map",
        }.get(k)

        mock_identity_service.get_bindings.return_value = {
            "identity_id": "tg:316743844",
            "unified_conversation_id": "unified:abc-123-def",
            "bound_identities": [{"platform": "web", "user_id": "user123", "bound_at": 1737765600}],
            "metadata": {},
        }
        mock_telegram_client.send_message.return_value = True

        handler = MyBindingsCommandHandler()
        handler._identity_service = mock_identity_service

        # Execute
        result = handler.handle(mock_update, {})

        # Verify
        assert result
        call_args = mock_telegram_client.send_message.call_args
        assert "unified:abc-123-def" in call_args[0][1]
        assert "user123" in call_args[0][1]
        assert "🖥️" in call_args[0][1]  # Web 圖標


class TestUnbindCommandHandler:
    """測試 /unbind 命令處理器"""

    def test_can_handle_unbind_commands(self):
        """測試能識別 /unbind 相關命令"""
        handler = UnbindCommandHandler()
        assert handler.can_handle("/unbind")
        assert handler.can_handle("/unbind confirm")
        assert handler.can_handle("/unbind ")
        assert not handler.can_handle("/bind")

    @patch("commands.handlers.unbind_handler.telegram_client")
    @patch("commands.handlers.unbind_handler.os.getenv")
    def test_handle_unbind_no_bindings(
        self, mock_getenv, mock_telegram_client, mock_identity_service
    ):
        """測試沒有綁定時的 unbind"""
        # Setup
        mock_getenv.side_effect = lambda k: {
            "BINDING_CODES_TABLE": "test-binding-codes",
            "IDENTITY_MAP_TABLE": "test-identity-map",
        }.get(k)

        mock_identity_service.get_bindings.return_value = None
        mock_telegram_client.send_message.return_value = True

        user = User(id=316743844, first_name="Test", is_bot=False, username="testuser")
        chat = Chat(id=316743844, type="private")
        message = Message(message_id=1, date=None, chat=chat, from_user=user, text="/unbind")
        update = Update(update_id=1, message=message)

        handler = UnbindCommandHandler()
        handler._identity_service = mock_identity_service

        # Execute
        result = handler.handle(update, {})

        # Verify
        assert result
        call_args = mock_telegram_client.send_message.call_args
        assert "沒有綁定" in call_args[0][1]

    @patch("commands.handlers.unbind_handler.telegram_client")
    @patch("commands.handlers.unbind_handler.os.getenv")
    def test_handle_unbind_confirmation_step(
        self, mock_getenv, mock_telegram_client, mock_identity_service
    ):
        """測試 unbind 確認步驟"""
        # Setup
        mock_getenv.side_effect = lambda k: {
            "BINDING_CODES_TABLE": "test-binding-codes",
            "IDENTITY_MAP_TABLE": "test-identity-map",
        }.get(k)

        mock_identity_service.get_bindings.return_value = {
            "identity_id": "tg:316743844",
            "unified_conversation_id": "unified:abc-123",
            "bound_identities": [{"platform": "web", "user_id": "user123"}],
            "metadata": {},
        }
        mock_telegram_client.send_message.return_value = True

        user = User(id=316743844, first_name="Test", is_bot=False, username="testuser")
        chat = Chat(id=316743844, type="private")
        message = Message(message_id=1, date=None, chat=chat, from_user=user, text="/unbind")
        update = Update(update_id=1, message=message)

        handler = UnbindCommandHandler()
        handler._identity_service = mock_identity_service

        # Execute
        result = handler.handle(update, {})

        # Verify - 應該顯示確認訊息
        assert result
        call_args = mock_telegram_client.send_message.call_args
        assert "確認" in call_args[0][1]
        assert "/unbind confirm" in call_args[0][1]
        assert "user123" in call_args[0][1]

    @patch("commands.handlers.unbind_handler.telegram_client")
    @patch("commands.handlers.unbind_handler.os.getenv")
    def test_handle_unbind_confirm_success(
        self, mock_getenv, mock_telegram_client, mock_identity_service
    ):
        """測試 unbind confirm 執行解綁"""
        # Setup
        mock_getenv.side_effect = lambda k: {
            "BINDING_CODES_TABLE": "test-binding-codes",
            "IDENTITY_MAP_TABLE": "test-identity-map",
        }.get(k)

        mock_identity_service.get_bindings.return_value = {
            "identity_id": "tg:316743844",
            "unified_conversation_id": "unified:abc-123",
            "bound_identities": [{"platform": "web", "user_id": "user123"}],
            "metadata": {},
        }
        mock_identity_service.unbind.return_value = True
        mock_telegram_client.send_message.return_value = True

        user = User(id=316743844, first_name="Test", is_bot=False, username="testuser")
        chat = Chat(id=316743844, type="private")
        message = Message(
            message_id=1, date=None, chat=chat, from_user=user, text="/unbind confirm"
        )
        update = Update(update_id=1, message=message)

        handler = UnbindCommandHandler()
        handler._identity_service = mock_identity_service

        # Execute
        result = handler.handle(update, {})

        # Verify
        assert result
        mock_identity_service.unbind.assert_called_once_with("tg:316743844")

        call_args = mock_telegram_client.send_message.call_args
        assert "已解除" in call_args[0][1]
        assert "316743844" in call_args[0][1]


class TestCommandIntegration:
    """整合測試：命令處理器協作"""

    @patch("commands.handlers.bind_handler.telegram_client")
    @patch("commands.handlers.mybindings_handler.telegram_client")
    @patch("commands.handlers.bind_handler.os.getenv")
    @patch("commands.handlers.mybindings_handler.os.getenv")
    def test_bind_then_check_flow(
        self,
        mock_getenv_mybindings,
        mock_getenv_bind,
        mock_telegram_mybindings,
        mock_telegram_bind,
        mock_identity_service,
    ):
        """測試完整流程：bind → mybindings"""
        # Setup environment
        mock_getenv_bind.side_effect = lambda k: {
            "BINDING_CODES_TABLE": "test-binding-codes",
            "IDENTITY_MAP_TABLE": "test-identity-map",
        }.get(k)
        mock_getenv_mybindings.side_effect = mock_getenv_bind.side_effect

        mock_telegram_bind.send_message.return_value = True
        mock_telegram_mybindings.send_message.return_value = True

        # Step 1: /bind
        bind_handler = BindCommandHandler()
        bind_handler._identity_service = mock_identity_service

        user = User(id=316743844, first_name="Test", is_bot=False, username="testuser")
        chat = Chat(id=316743844, type="private")
        bind_message = Message(message_id=1, date=None, chat=chat, from_user=user, text="/bind")
        bind_update = Update(update_id=1, message=bind_message)

        bind_result = bind_handler.handle(bind_update, {})
        assert bind_result

        # Step 2: 模擬綁定後，查詢 /mybindings
        mock_identity_service.get_bindings.return_value = {
            "identity_id": "tg:316743844",
            "unified_conversation_id": "unified:test-123",
            "bound_identities": [{"platform": "web", "user_id": "web_user"}],
            "metadata": {},
        }

        mybindings_handler = MyBindingsCommandHandler()
        mybindings_handler._identity_service = mock_identity_service

        mybindings_message = Message(
            message_id=2, date=None, chat=chat, from_user=user, text="/mybindings"
        )
        mybindings_update = Update(update_id=2, message=mybindings_message)

        mybindings_result = mybindings_handler.handle(mybindings_update, {})
        assert mybindings_result

        # 驗證 mybindings 回應包含綁定資訊
        call_args = mock_telegram_mybindings.send_message.call_args
        assert "unified:test-123" in call_args[0][1]
        assert "web_user" in call_args[0][1]
