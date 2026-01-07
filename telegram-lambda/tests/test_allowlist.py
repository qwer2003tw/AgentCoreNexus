"""
Unit tests for allowlist.py
"""

from unittest.mock import patch

from botocore.exceptions import ClientError
from src.allowlist import add_to_allowlist, check_allowed, remove_from_allowlist


class TestAllowlist:
    """測試允許名單驗證功能"""

    @patch("src.allowlist.table")
    def test_allowed_chat_id(self, mock_table):
        """測試允許的 chat_id"""
        # 設定 mock 返回值
        mock_table.get_item.return_value = {
            "Item": {"chat_id": 123456789, "username": "test_user", "enabled": True}
        }

        # 執行測試
        result = check_allowed(123456789, "test_user")

        # 驗證
        assert result is True
        mock_table.get_item.assert_called_once_with(Key={"chat_id": 123456789})

    @patch("src.allowlist.table")
    def test_blocked_chat_id(self, mock_table):
        """測試封鎖的 chat_id"""
        # 設定 mock 返回值 - 不存在的記錄
        mock_table.get_item.return_value = {}

        # 執行測試
        result = check_allowed(123456789, "test_user")

        # 驗證
        assert result is False

    @patch("src.allowlist.table")
    def test_disabled_chat_id(self, mock_table):
        """測試已禁用的 chat_id"""
        # 設定 mock 返回值
        mock_table.get_item.return_value = {
            "Item": {"chat_id": 123456789, "username": "test_user", "enabled": False}
        }

        # 執行測試
        result = check_allowed(123456789, "test_user")

        # 驗證
        assert result is False

    @patch("src.allowlist.table")
    def test_username_mismatch(self, mock_table):
        """測試 username 不匹配"""
        # 設定 mock 返回值
        mock_table.get_item.return_value = {
            "Item": {"chat_id": 123456789, "username": "correct_user", "enabled": True}
        }

        # 執行測試
        result = check_allowed(123456789, "wrong_user")

        # 驗證
        assert result is False

    @patch("src.allowlist.table")
    def test_no_username_provided(self, mock_table):
        """測試未提供 username"""
        # 設定 mock 返回值
        mock_table.get_item.return_value = {
            "Item": {"chat_id": 123456789, "username": "test_user", "enabled": True}
        }

        # 執行測試（不提供 username）
        result = check_allowed(123456789)

        # 驗證（應該通過，因為沒有提供 username 就不驗證）
        assert result is True

    @patch("src.allowlist.table")
    def test_dynamodb_unavailable(self, mock_table):
        """測試 DynamoDB 錯誤"""
        # 設定 mock 拋出異常
        error_response = {"Error": {"Code": "ServiceUnavailable"}}
        mock_table.get_item.side_effect = ClientError(error_response, "GetItem")

        # 執行測試
        result = check_allowed(123456789, "test_user")

        # 驗證（錯誤時應拒絕訪問）
        assert result is False

    @patch("src.allowlist.table")
    def test_add_to_allowlist_success(self, mock_table):
        """測試成功新增到允許名單"""
        # 設定 mock
        mock_table.put_item.return_value = {}

        # 執行測試
        result = add_to_allowlist(123456789, "test_user")

        # 驗證
        assert result is True
        mock_table.put_item.assert_called_once_with(
            Item={"chat_id": 123456789, "username": "test_user", "enabled": True}
        )

    @patch("src.allowlist.table")
    def test_add_to_allowlist_failure(self, mock_table):
        """測試新增到允許名單失敗"""
        # 設定 mock 拋出異常
        error_response = {"Error": {"Code": "ValidationException"}}
        mock_table.put_item.side_effect = ClientError(error_response, "PutItem")

        # 執行測試
        result = add_to_allowlist(123456789, "test_user")

        # 驗證
        assert result is False

    @patch("src.allowlist.table")
    def test_remove_from_allowlist_success(self, mock_table):
        """測試成功從允許名單移除"""
        # 設定 mock
        mock_table.delete_item.return_value = {}

        # 執行測試
        result = remove_from_allowlist(123456789)

        # 驗證
        assert result is True
        mock_table.delete_item.assert_called_once_with(Key={"chat_id": 123456789})

    @patch("src.allowlist.table")
    def test_remove_from_allowlist_failure(self, mock_table):
        """測試從允許名單移除失敗"""
        # 設定 mock 拋出異常
        error_response = {"Error": {"Code": "ResourceNotFoundException"}}
        mock_table.delete_item.side_effect = ClientError(error_response, "DeleteItem")

        # 執行測試
        result = remove_from_allowlist(123456789)

        # 驗證
        assert result is False
