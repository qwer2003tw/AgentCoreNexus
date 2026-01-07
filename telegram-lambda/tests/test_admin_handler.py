"""
Tests for admin_handler - 管理員指令處理器測試
重點測試安全相關功能
"""

from unittest.mock import Mock, patch

import pytest
from commands.handlers.admin_handler import AdminCommandHandler
from telegram import Chat, Message, Update, User


@pytest.fixture(autouse=True)
def mock_admin_permission():
    """自動 Mock 管理員權限"""
    with patch("auth.admin_list.is_admin", return_value=True):
        yield


@pytest.fixture
def admin_handler():
    """創建 Admin Handler"""
    return AdminCommandHandler()


@pytest.fixture
def mock_update():
    """創建 Mock Update"""

    def create_update(text: str, chat_id: int = 12345):
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        user = Mock(spec=User)
        chat = Mock(spec=Chat)

        user.username = "admin_user"
        chat.id = chat_id
        message.chat_id = chat_id
        message.text = text
        message.caption = None
        message.from_user = user
        message.chat = chat

        update.message = message
        update.edited_message = None

        return update

    return create_update


class TestCanHandle:
    """測試指令識別"""

    def test_can_handle_admin_command(self, admin_handler):
        """測試識別 /admin 指令"""
        assert admin_handler.can_handle("/admin") is True
        assert admin_handler.can_handle("/admin help") is True
        assert admin_handler.can_handle("/admin add 123") is True

    def test_cannot_handle_other_commands(self, admin_handler):
        """測試不識別其他指令"""
        assert admin_handler.can_handle("/help") is False
        assert admin_handler.can_handle("/start") is False
        assert admin_handler.can_handle("admin") is False  # 沒有 /

    def test_can_handle_with_spaces(self, admin_handler):
        """測試帶空格的指令"""
        assert admin_handler.can_handle("  /admin  ") is True
        assert admin_handler.can_handle("/admin   help   ") is True


class TestAddCommand:
    """測試添加用戶指令"""

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.add_to_allowlist")
    def test_add_user_success(self, mock_add, mock_send, admin_handler, mock_update):
        """測試成功添加用戶"""
        mock_add.return_value = True
        mock_send.return_value = True

        update = mock_update("/admin add 99999 testuser")
        result = admin_handler.handle(update, {})

        assert result is True
        mock_add.assert_called_once_with(chat_id=99999, username="testuser", enabled=True)
        mock_send.assert_called_once()

        # 驗證發送的訊息包含成功資訊
        call_args = mock_send.call_args
        assert "✅" in call_args[0][1]
        assert "99999" in call_args[0][1]

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.add_to_allowlist")
    def test_add_user_without_username(self, mock_add, mock_send, admin_handler, mock_update):
        """測試添加用戶不提供 username"""
        mock_add.return_value = True
        mock_send.return_value = True

        update = mock_update("/admin add 99999")
        admin_handler.handle(update, {})

        # 應該使用預設 username
        mock_add.assert_called_once()
        call_args = mock_add.call_args
        assert call_args[1]["chat_id"] == 99999
        assert "user_99999" in call_args[1]["username"]

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    def test_add_user_no_args(self, mock_send, admin_handler, mock_update):
        """測試沒有參數"""
        mock_send.return_value = True

        update = mock_update("/admin add")
        admin_handler.handle(update, {})

        # 應該發送錯誤訊息
        call_args = mock_send.call_args
        assert "用法" in call_args[0][1]

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    def test_add_user_invalid_chat_id(self, mock_send, admin_handler, mock_update):
        """測試無效的 chat_id"""
        mock_send.return_value = True

        update = mock_update("/admin add invalid_id")
        admin_handler.handle(update, {})

        # 應該發送錯誤訊息
        call_args = mock_send.call_args
        assert "無效" in call_args[0][1] or "必須是數字" in call_args[0][1]

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.add_to_allowlist")
    def test_add_user_failure(self, mock_add, mock_send, admin_handler, mock_update):
        """測試添加失敗"""
        mock_add.return_value = False
        mock_send.return_value = True

        update = mock_update("/admin add 99999 testuser")
        admin_handler.handle(update, {})

        # 應該發送失敗訊息
        call_args = mock_send.call_args
        assert "失敗" in call_args[0][1]


class TestRemoveCommand:
    """測試移除用戶指令"""

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.remove_from_allowlist")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_remove_user_success(
        self, mock_get_info, mock_remove, mock_send, admin_handler, mock_update
    ):
        """測試成功移除用戶"""
        mock_get_info.return_value = {"chat_id": 99999, "username": "testuser"}
        mock_remove.return_value = True
        mock_send.return_value = True

        update = mock_update("/admin remove 99999")
        result = admin_handler.handle(update, {})

        assert result is True
        mock_remove.assert_called_once_with(99999)

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_remove_self_denied(self, mock_get_info, mock_send, admin_handler, mock_update):
        """測試無法移除自己（安全檢查）"""
        mock_get_info.return_value = {"chat_id": 12345, "username": "admin_user"}
        mock_send.return_value = True

        update = mock_update("/admin remove 12345", chat_id=12345)
        admin_handler.handle(update, {})

        # 應該拒絕
        call_args = mock_send.call_args
        assert "無法移除自己" in call_args[0][1]

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_remove_nonexistent_user(self, mock_get_info, mock_send, admin_handler, mock_update):
        """測試移除不存在的用戶"""
        mock_get_info.return_value = None
        mock_send.return_value = True

        update = mock_update("/admin remove 99999")
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        assert "不在名單中" in call_args[0][1]


class TestEnableDisableCommands:
    """測試啟用/禁用指令"""

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.update_user_enabled")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_enable_user(
        self, mock_get_info, mock_update_enabled, mock_send, admin_handler, mock_update
    ):
        """測試啟用用戶"""
        mock_get_info.return_value = {"chat_id": 99999, "enabled": False}
        mock_update_enabled.return_value = True
        mock_send.return_value = True

        update = mock_update("/admin enable 99999")
        result = admin_handler.handle(update, {})

        assert result is True
        mock_update_enabled.assert_called_once_with(99999, True)

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.update_user_enabled")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_disable_user(
        self, mock_get_info, mock_update_enabled, mock_send, admin_handler, mock_update
    ):
        """測試禁用用戶"""
        mock_get_info.return_value = {"chat_id": 99999, "enabled": True}
        mock_update_enabled.return_value = True
        mock_send.return_value = True

        update = mock_update("/admin disable 99999")
        result = admin_handler.handle(update, {})

        assert result is True
        mock_update_enabled.assert_called_once_with(99999, False)

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_disable_self_denied(self, mock_get_info, mock_send, admin_handler, mock_update):
        """測試無法禁用自己（安全檢查）"""
        mock_get_info.return_value = {"chat_id": 12345}
        mock_send.return_value = True

        update = mock_update("/admin disable 12345", chat_id=12345)
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        assert "無法禁用自己" in call_args[0][1]


class TestPromoteDemoteCommands:
    """測試升級/降級權限指令"""

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.update_user_role")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_promote_user(
        self, mock_get_info, mock_update_role, mock_send, admin_handler, mock_update
    ):
        """測試升級用戶為管理員"""
        mock_get_info.return_value = {"chat_id": 99999, "username": "user1", "role": "user"}
        mock_update_role.return_value = True
        mock_send.return_value = True

        update = mock_update("/admin promote 99999")
        result = admin_handler.handle(update, {})

        assert result is True
        mock_update_role.assert_called_once_with(99999, "admin")

        call_args = mock_send.call_args
        assert "👑" in call_args[0][1]

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_promote_already_admin(self, mock_get_info, mock_send, admin_handler, mock_update):
        """測試升級已是管理員的用戶"""
        mock_get_info.return_value = {"chat_id": 99999, "role": "admin"}
        mock_send.return_value = True

        update = mock_update("/admin promote 99999")
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        assert "已經是管理員" in call_args[0][1]

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.update_user_role")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_demote_user(
        self, mock_get_info, mock_update_role, mock_send, admin_handler, mock_update
    ):
        """測試降級管理員為普通用戶"""
        mock_get_info.return_value = {"chat_id": 99999, "username": "user1", "role": "admin"}
        mock_update_role.return_value = True
        mock_send.return_value = True

        update = mock_update("/admin demote 99999")
        result = admin_handler.handle(update, {})

        assert result is True
        mock_update_role.assert_called_once_with(99999, "user")

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_demote_self_denied(self, mock_get_info, mock_send, admin_handler, mock_update):
        """測試無法降級自己（安全檢查）"""
        mock_get_info.return_value = {"chat_id": 12345, "role": "admin"}
        mock_send.return_value = True

        update = mock_update("/admin demote 12345", chat_id=12345)
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        assert "無法降級自己" in call_args[0][1]

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_demote_already_user(self, mock_get_info, mock_send, admin_handler, mock_update):
        """測試降級已是普通用戶的用戶"""
        mock_get_info.return_value = {"chat_id": 99999, "role": "user"}
        mock_send.return_value = True

        update = mock_update("/admin demote 99999")
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        assert "已經是普通用戶" in call_args[0][1]


class TestListCommand:
    """測試列表指令"""

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.list_all_users")
    def test_list_users(self, mock_list, mock_send, admin_handler, mock_update):
        """測試列出用戶"""
        mock_list.return_value = [
            {"chat_id": 1, "username": "user1", "enabled": True, "role": "user"},
            {"chat_id": 2, "username": "user2", "enabled": False, "role": "user"},
            {"chat_id": -100, "username": "group1", "enabled": True, "role": "user"},
        ]
        mock_send.return_value = True

        update = mock_update("/admin list")
        result = admin_handler.handle(update, {})

        assert result is True
        call_args = mock_send.call_args
        message = call_args[0][1]

        # 驗證包含用戶資訊
        assert "user1" in message
        assert "user2" in message
        assert "group1" in message
        assert "總計: 3" in message

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.list_all_users")
    def test_list_empty(self, mock_list, mock_send, admin_handler, mock_update):
        """測試空列表"""
        mock_list.return_value = []
        mock_send.return_value = True

        update = mock_update("/admin list")
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        assert "為空" in call_args[0][1]


class TestInfoCommand:
    """測試用戶信息指令"""

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_info_user_exists(self, mock_get_info, mock_send, admin_handler, mock_update):
        """測試查看存在的用戶"""
        mock_get_info.return_value = {
            "chat_id": 99999,
            "username": "testuser",
            "enabled": True,
            "role": "user",
        }
        mock_send.return_value = True

        update = mock_update("/admin info 99999")
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        message = call_args[0][1]
        assert "99999" in message
        assert "testuser" in message

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_info_user_not_exists(self, mock_get_info, mock_send, admin_handler, mock_update):
        """測試查看不存在的用戶"""
        mock_get_info.return_value = None
        mock_send.return_value = True

        update = mock_update("/admin info 99999")
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        assert "不在名單中" in call_args[0][1]


class TestStatsCommand:
    """測試統計指令"""

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_stats")
    def test_stats_success(self, mock_stats, mock_send, admin_handler, mock_update):
        """測試獲取統計信息"""
        mock_stats.return_value = {
            "total_users": 10,
            "enabled_users": 8,
            "disabled_users": 2,
            "admin_count": 2,
            "user_count": 8,
            "group_count": 3,
            "private_count": 7,
        }
        mock_send.return_value = True

        update = mock_update("/admin stats")
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        message = call_args[0][1]
        assert "10" in message  # total_users
        assert "8" in message  # enabled_users

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_stats")
    def test_stats_failure(self, mock_stats, mock_send, admin_handler, mock_update):
        """測試統計信息獲取失敗"""
        mock_stats.return_value = {}
        mock_send.return_value = True

        update = mock_update("/admin stats")
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        assert "無法獲取" in call_args[0][1]


class TestBroadcastCommand:
    """測試廣播指令"""

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.list_all_users")
    def test_broadcast_success(self, mock_list, mock_send, admin_handler, mock_update):
        """測試廣播成功"""
        mock_list.return_value = [
            {"chat_id": 1, "enabled": True},
            {"chat_id": 2, "enabled": True},
            {"chat_id": 3, "enabled": False},  # 禁用的不會收到
        ]
        mock_send.return_value = True

        update = mock_update("/admin broadcast 測試訊息")
        admin_handler.handle(update, {})

        # 應該發送確認 + 廣播 + 結果
        # 至少 3 次調用：確認、給 user1、給 user2、結果
        assert mock_send.call_count >= 3

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    def test_broadcast_no_message(self, mock_send, admin_handler, mock_update):
        """測試沒有廣播內容"""
        mock_send.return_value = True

        update = mock_update("/admin broadcast")
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        assert "用法" in call_args[0][1]

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.list_all_users")
    def test_broadcast_no_enabled_users(self, mock_list, mock_send, admin_handler, mock_update):
        """測試沒有啟用的用戶"""
        mock_list.return_value = []
        mock_send.return_value = True

        update = mock_update("/admin broadcast test")
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        assert "沒有啟用的用戶" in call_args[0][1]


class TestHelpCommand:
    """測試幫助指令"""

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    def test_help_command(self, mock_send, admin_handler, mock_update):
        """測試幫助指令"""
        mock_send.return_value = True

        update = mock_update("/admin help")
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        message = call_args[0][1]
        # 應該包含所有子指令說明
        assert "add" in message
        assert "remove" in message
        assert "list" in message

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    def test_admin_alone_shows_help(self, mock_send, admin_handler, mock_update):
        """測試單獨 /admin 顯示幫助"""
        mock_send.return_value = True

        update = mock_update("/admin")
        admin_handler.handle(update, {})

        # 預設應該顯示幫助
        call_args = mock_send.call_args
        assert "幫助" in call_args[0][1] or "管理員指令" in call_args[0][1]

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    def test_unknown_subcommand_shows_help(self, mock_send, admin_handler, mock_update):
        """測試未知子指令顯示幫助"""
        mock_send.return_value = True

        update = mock_update("/admin unknown_command")
        result = admin_handler.handle(update, {})

        # 未知指令應該顯示幫助
        assert result is True


class TestSecurityChecks:
    """測試安全檢查"""

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_cannot_remove_self(self, mock_get_info, mock_send, admin_handler, mock_update):
        """安全：無法移除自己"""
        mock_get_info.return_value = {"chat_id": 12345}
        mock_send.return_value = True

        update = mock_update("/admin remove 12345", chat_id=12345)
        admin_handler.handle(update, {})

        # 應該被拒絕
        call_args = mock_send.call_args
        assert "無法移除自己" in call_args[0][1]

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_cannot_disable_self(self, mock_get_info, mock_send, admin_handler, mock_update):
        """安全：無法禁用自己"""
        mock_get_info.return_value = {"chat_id": 12345}
        mock_send.return_value = True

        update = mock_update("/admin disable 12345", chat_id=12345)
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        assert "無法禁用自己" in call_args[0][1]

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_cannot_demote_self(self, mock_get_info, mock_send, admin_handler, mock_update):
        """安全：無法降級自己"""
        mock_get_info.return_value = {"chat_id": 12345, "role": "admin"}
        mock_send.return_value = True

        update = mock_update("/admin demote 12345", chat_id=12345)
        admin_handler.handle(update, {})

        call_args = mock_send.call_args
        assert "無法降級自己" in call_args[0][1]


class TestErrorHandling:
    """測試錯誤處理"""

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    def test_invalid_chat_id_format(self, mock_send, admin_handler, mock_update):
        """測試無效的 chat_id 格式"""
        mock_send.return_value = True

        for command in ["/admin remove abc", "/admin info xyz", "/admin enable test"]:
            update = mock_update(command)
            admin_handler.handle(update, {})

            # 應該發送錯誤訊息
            assert mock_send.called

    @patch("commands.handlers.admin_handler.telegram_client.send_message")
    @patch("commands.handlers.admin_handler.allowlist.get_user_info")
    def test_user_not_found(self, mock_get_info, mock_send, admin_handler, mock_update):
        """測試用戶不存在"""
        mock_get_info.return_value = None
        mock_send.return_value = True

        for command in ["/admin remove 99999", "/admin info 99999", "/admin enable 99999"]:
            update = mock_update(command)
            admin_handler.handle(update, {})

            call_args = mock_send.call_args
            assert "不在名單中" in call_args[0][1]


class TestCommandMetadata:
    """測試指令元數據"""

    def test_get_command_name(self, admin_handler):
        """測試取得指令名稱"""
        assert admin_handler.get_command_name() == "AdminCommand"

    def test_get_description(self, admin_handler):
        """測試取得指令描述"""
        desc = admin_handler.get_description()
        assert "管理員" in desc
