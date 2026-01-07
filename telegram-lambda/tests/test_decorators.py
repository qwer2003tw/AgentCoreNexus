"""
Tests for Command Decorators - 指令裝飾器測試
"""

from unittest.mock import Mock, patch

import pytest
from auth.permissions import Permission
from commands.base import CommandHandler
from commands.decorators import require_admin, require_allowlist, require_permission
from telegram import Chat, Message, Update, User


class BaseTestHandler(CommandHandler):
    """測試用的基礎處理器"""

    def __init__(self):
        self.handle_called = False
        self.handle_result = True

    def can_handle(self, text: str) -> bool:
        return True

    def handle(self, update: Update, event: dict) -> bool:
        self.handle_called = True
        return self.handle_result


@pytest.fixture
def mock_update():
    """創建 Mock Update 物件"""
    update = Mock(spec=Update)
    message = Mock(spec=Message)
    user = Mock(spec=User)
    chat = Mock(spec=Chat)

    user.username = "testuser"
    chat.id = 12345
    message.text = "/test"
    message.from_user = user
    message.chat = chat
    message.chat_id = 12345

    update.message = message
    update.edited_message = None

    return update


@pytest.fixture
def mock_event():
    """創建 Mock event 字典"""
    return {"body": "test"}


class TestRequireAdmin:
    """測試 @require_admin 裝飾器"""

    @patch("commands.decorators.check_permission")
    @patch("commands.decorators.send_permission_denied")
    def test_admin_permission_granted(self, mock_send, mock_check, mock_update, mock_event):
        """測試管理員權限通過"""
        mock_check.return_value = True

        @require_admin
        class TestHandler(BaseTestHandler):
            pass

        handler = TestHandler()
        result = handler.handle(mock_update, mock_event)

        assert result is True
        assert handler.handle_called is True
        mock_check.assert_called_once_with(12345, "testuser", Permission.ADMIN)
        mock_send.assert_not_called()

    @patch("commands.decorators.check_permission")
    @patch("commands.decorators.send_permission_denied")
    def test_admin_permission_denied(self, mock_send, mock_check, mock_update, mock_event):
        """測試管理員權限被拒絕"""
        mock_check.return_value = False

        @require_admin
        class TestHandler(BaseTestHandler):
            pass

        handler = TestHandler()
        result = handler.handle(mock_update, mock_event)

        assert result is False
        assert handler.handle_called is False
        mock_check.assert_called_once_with(12345, "testuser", Permission.ADMIN)
        mock_send.assert_called_once_with(12345, "ADMIN")

    @patch("commands.decorators.check_permission")
    @patch("commands.decorators.send_permission_denied")
    def test_admin_no_username(self, mock_send, mock_check, mock_update, mock_event):
        """測試沒有 username 的情況"""
        mock_check.return_value = True
        mock_update.message.from_user.username = None

        @require_admin
        class TestHandler(BaseTestHandler):
            pass

        handler = TestHandler()
        result = handler.handle(mock_update, mock_event)

        assert result is True
        # username 應該轉為空字串
        mock_check.assert_called_once_with(12345, "", Permission.ADMIN)

    def test_admin_decorator_marks_class(self):
        """測試裝飾器標記類別"""

        @require_admin
        class TestHandler(BaseTestHandler):
            pass

        assert hasattr(TestHandler, "_permission_required")
        assert TestHandler._permission_required == Permission.ADMIN


class TestRequireAllowlist:
    """測試 @require_allowlist 裝飾器"""

    @patch("commands.decorators.check_permission")
    @patch("commands.decorators.send_permission_denied")
    def test_allowlist_permission_granted(self, mock_send, mock_check, mock_update, mock_event):
        """測試 allowlist 權限通過"""
        mock_check.return_value = True

        @require_allowlist
        class TestHandler(BaseTestHandler):
            pass

        handler = TestHandler()
        result = handler.handle(mock_update, mock_event)

        assert result is True
        assert handler.handle_called is True
        mock_check.assert_called_once_with(12345, "testuser", Permission.ALLOWLIST)
        mock_send.assert_not_called()

    @patch("commands.decorators.check_permission")
    @patch("commands.decorators.send_permission_denied")
    def test_allowlist_permission_denied(self, mock_send, mock_check, mock_update, mock_event):
        """測試 allowlist 權限被拒絕"""
        mock_check.return_value = False

        @require_allowlist
        class TestHandler(BaseTestHandler):
            pass

        handler = TestHandler()
        result = handler.handle(mock_update, mock_event)

        assert result is False
        assert handler.handle_called is False
        mock_check.assert_called_once_with(12345, "testuser", Permission.ALLOWLIST)
        mock_send.assert_called_once_with(12345, "ALLOWLIST")

    def test_allowlist_decorator_marks_class(self):
        """測試裝飾器標記類別"""

        @require_allowlist
        class TestHandler(BaseTestHandler):
            pass

        assert hasattr(TestHandler, "_permission_required")
        assert TestHandler._permission_required == Permission.ALLOWLIST


class TestRequirePermission:
    """測試 @require_permission 裝飾器工廠"""

    @patch("commands.decorators.check_permission")
    @patch("commands.decorators.send_permission_denied")
    def test_custom_permission_level(self, mock_send, mock_check, mock_update, mock_event):
        """測試自訂權限等級"""
        mock_check.return_value = True

        @require_permission(Permission.ALLOWLIST)
        class TestHandler(BaseTestHandler):
            pass

        handler = TestHandler()
        result = handler.handle(mock_update, mock_event)

        assert result is True
        mock_check.assert_called_once_with(12345, "testuser", Permission.ALLOWLIST)

    @patch("commands.decorators.check_permission")
    @patch("commands.decorators.send_permission_denied")
    def test_none_permission_always_passes(self, mock_send, mock_check, mock_update, mock_event):
        """測試 NONE 權限總是通過"""
        mock_check.return_value = True

        @require_permission(Permission.NONE)
        class TestHandler(BaseTestHandler):
            pass

        handler = TestHandler()
        result = handler.handle(mock_update, mock_event)

        assert result is True
        mock_check.assert_called_once_with(12345, "testuser", Permission.NONE)


class TestDecoratorEdgeCases:
    """測試裝飾器邊緣情況"""

    @patch("commands.decorators.check_permission")
    @patch("commands.decorators.send_permission_denied")
    def test_no_message_in_update(self, mock_send, mock_check, mock_event):
        """測試 Update 中沒有訊息"""
        update = Mock(spec=Update)
        update.message = None
        update.edited_message = None

        @require_admin
        class TestHandler(BaseTestHandler):
            pass

        handler = TestHandler()
        result = handler.handle(update, mock_event)

        assert result is False
        assert handler.handle_called is False
        mock_check.assert_not_called()
        mock_send.assert_not_called()

    @patch("commands.decorators.check_permission")
    @patch("commands.decorators.send_permission_denied")
    def test_edited_message(self, mock_send, mock_check, mock_event):
        """測試編輯過的訊息"""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        user = Mock(spec=User)
        chat = Mock(spec=Chat)

        user.username = "testuser"
        chat.id = 12345
        message.text = "/test"
        message.from_user = user
        message.chat = chat
        message.chat_id = 12345

        update.message = None
        update.edited_message = message

        mock_check.return_value = True

        @require_admin
        class TestHandler(BaseTestHandler):
            pass

        handler = TestHandler()
        result = handler.handle(update, mock_event)

        assert result is True
        assert handler.handle_called is True
        mock_check.assert_called_once_with(12345, "testuser", Permission.ADMIN)

    @patch("commands.decorators.check_permission")
    @patch("commands.decorators.send_permission_denied")
    def test_handler_returns_false(self, mock_send, mock_check, mock_update, mock_event):
        """測試處理器返回 False"""
        mock_check.return_value = True

        @require_admin
        class TestHandler(BaseTestHandler):
            def __init__(self):
                super().__init__()
                self.handle_result = False

        handler = TestHandler()
        result = handler.handle(mock_update, mock_event)

        # 權限通過但處理失敗
        assert result is False
        assert handler.handle_called is True
        mock_check.assert_called_once()

    @patch("commands.decorators.check_permission")
    @patch("commands.decorators.send_permission_denied")
    def test_multiple_decorators(self, mock_send, mock_check, mock_update, mock_event):
        """測試多個裝飾器（只有最外層的生效）"""
        mock_check.return_value = True

        # 注意：這裡只有最外層的裝飾器會生效
        @require_admin
        @require_allowlist
        class TestHandler(BaseTestHandler):
            pass

        handler = TestHandler()
        result = handler.handle(mock_update, mock_event)

        assert result is True
        # 應該檢查 ADMIN 權限（最外層）
        assert mock_check.call_count >= 1
        # 最後一次呼叫應該是檢查 ADMIN
        last_call = mock_check.call_args_list[-1]
        assert last_call[0][2] == Permission.ADMIN
