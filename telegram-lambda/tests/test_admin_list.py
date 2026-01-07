"""
Tests for auth.admin_list module
"""

from unittest.mock import patch

from auth.admin_list import get_user_role, is_admin, set_user_role
from botocore.exceptions import ClientError


class TestGetUserRole:
    """測試 get_user_role 函數"""

    @patch("auth.admin_list.table")
    def test_get_admin_role(self, mock_table):
        """測試取得 admin 角色"""
        mock_table.get_item.return_value = {
            "Item": {"chat_id": 123, "username": "admin_user", "enabled": True, "role": "admin"}
        }

        role = get_user_role(123, "admin_user")
        assert role == "admin"

    @patch("auth.admin_list.table")
    def test_get_user_role(self, mock_table):
        """測試取得 user 角色"""
        mock_table.get_item.return_value = {
            "Item": {"chat_id": 123, "username": "normal_user", "enabled": True, "role": "user"}
        }

        role = get_user_role(123, "normal_user")
        assert role == "user"

    @patch("auth.admin_list.table")
    def test_get_role_with_default(self, mock_table):
        """測試取得角色時的預設值（沒有 role 欄位時預設為 user）"""
        mock_table.get_item.return_value = {
            "Item": {
                "chat_id": 123,
                "username": "old_user",
                "enabled": True,
                # 沒有 role 欄位
            }
        }

        role = get_user_role(123, "old_user")
        assert role == "user"  # 預設值

    @patch("auth.admin_list.table")
    def test_user_not_found(self, mock_table):
        """測試用戶不存在的情況"""
        mock_table.get_item.return_value = {}  # 沒有 Item

        role = get_user_role(999, "unknown")
        assert role == "none"

    @patch("auth.admin_list.table")
    def test_disabled_user(self, mock_table):
        """測試已停用的用戶"""
        mock_table.get_item.return_value = {
            "Item": {"chat_id": 123, "username": "disabled_user", "enabled": False, "role": "admin"}
        }

        role = get_user_role(123, "disabled_user")
        assert role == "none"  # 停用用戶視為 none

    @patch("auth.admin_list.table")
    def test_dynamodb_error(self, mock_table):
        """測試 DynamoDB 錯誤"""
        mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "GetItem"
        )

        role = get_user_role(123, "test")
        assert role == "none"  # 錯誤時返回 none

    @patch("auth.admin_list.table")
    def test_unexpected_error(self, mock_table):
        """測試未預期的錯誤"""
        mock_table.get_item.side_effect = Exception("Unexpected error")

        role = get_user_role(123, "test")
        assert role == "none"  # 錯誤時返回 none


class TestIsAdmin:
    """測試 is_admin 函數"""

    @patch("auth.admin_list.get_user_role")
    def test_is_admin_true(self, mock_get_role):
        """測試 admin 用戶"""
        mock_get_role.return_value = "admin"

        result = is_admin(123, "admin_user")
        assert result is True

    @patch("auth.admin_list.get_user_role")
    def test_is_admin_false_for_user(self, mock_get_role):
        """測試一般用戶"""
        mock_get_role.return_value = "user"

        result = is_admin(123, "normal_user")
        assert result is False

    @patch("auth.admin_list.get_user_role")
    def test_is_admin_false_for_none(self, mock_get_role):
        """測試不存在的用戶"""
        mock_get_role.return_value = "none"

        result = is_admin(999, "unknown")
        assert result is False


class TestSetUserRole:
    """測試 set_user_role 函數"""

    @patch("auth.admin_list.table")
    def test_set_role_to_admin(self, mock_table):
        """測試設定為 admin"""
        mock_table.update_item.return_value = {}

        result = set_user_role(123, "admin", "test_user")
        assert result is True

        # 驗證呼叫參數
        call_args = mock_table.update_item.call_args
        assert call_args[1]["Key"] == {"chat_id": 123}
        assert ":role" in str(call_args[1]["ExpressionAttributeValues"])

    @patch("auth.admin_list.table")
    def test_set_role_without_username(self, mock_table):
        """測試不提供 username 時設定角色"""
        mock_table.update_item.return_value = {}

        result = set_user_role(123, "user")
        assert result is True

    @patch("auth.admin_list.table")
    def test_set_role_with_username(self, mock_table):
        """測試同時更新 username"""
        mock_table.update_item.return_value = {}

        result = set_user_role(123, "admin", "new_admin")
        assert result is True

        # 驗證有更新 username
        call_args = mock_table.update_item.call_args
        assert ":username" in str(call_args[1]["ExpressionAttributeValues"])

    @patch("auth.admin_list.table")
    def test_set_role_dynamodb_error(self, mock_table):
        """測試 DynamoDB 錯誤"""
        mock_table.update_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem"
        )

        result = set_user_role(123, "admin")
        assert result is False
