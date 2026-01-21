"""
測試 allowlist session 管理功能
"""

from unittest.mock import MagicMock, patch

from src.allowlist import check_allowed_with_session, update_session_id


class TestUpdateSessionId:
    """測試 update_session_id 函數"""

    @patch("src.allowlist.get_dynamodb_table")
    def test_update_session_id_success(self, mock_get_table):
        """測試成功更新 session ID"""
        # 設定 mock
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        # 執行
        result = update_session_id(123456, "session-20260121-123456")

        # 驗證
        assert result is True
        mock_table.update_item.assert_called_once()

        # 檢查呼叫參數
        call_args = mock_table.update_item.call_args
        assert call_args[1]["Key"] == {"chat_id": 123456}
        assert "current_session_id" in call_args[1]["UpdateExpression"]

    @patch("src.allowlist.get_dynamodb_table")
    def test_update_session_id_dynamodb_error(self, mock_get_table):
        """測試 DynamoDB 錯誤時的處理"""
        # 設定 mock 拋出錯誤
        mock_table = MagicMock()
        from botocore.exceptions import ClientError

        mock_table.update_item.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "UpdateItem"
        )
        mock_get_table.return_value = mock_table

        # 執行
        result = update_session_id(123456, "session-20260121-123456")

        # 驗證：應該返回 False 但不拋出異常
        assert result is False

    @patch("src.allowlist.get_dynamodb_table")
    def test_update_session_id_unexpected_error(self, mock_get_table):
        """測試未預期錯誤時的處理"""
        # 設定 mock 拋出未預期錯誤
        mock_table = MagicMock()
        mock_table.update_item.side_effect = Exception("Unexpected error")
        mock_get_table.return_value = mock_table

        # 執行
        result = update_session_id(123456, "session-20260121-123456")

        # 驗證：應該返回 False 但不拋出異常
        assert result is False


class TestCheckAllowedWithSession:
    """測試 check_allowed_with_session 函數"""

    @patch("src.allowlist.get_dynamodb_table")
    @patch("src.allowlist.check_allowed")
    def test_check_allowed_with_session_has_custom_session(
        self, mock_check_allowed, mock_get_table
    ):
        """測試獲取自定義 session ID"""
        # 設定 mock
        mock_check_allowed.return_value = True
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "chat_id": 123456,
                "username": "testuser",
                "current_session_id": "session-custom-123",
            }
        }
        mock_get_table.return_value = mock_table

        # 執行
        allowed, username, session_id = check_allowed_with_session(123456, "testuser")

        # 驗證
        assert allowed is True
        assert username == "testuser"
        assert session_id == "session-custom-123"

    @patch("src.allowlist.get_dynamodb_table")
    @patch("src.allowlist.check_allowed")
    def test_check_allowed_with_session_no_custom_session(self, mock_check_allowed, mock_get_table):
        """測試沒有自定義 session ID（向後兼容）"""
        # 設定 mock
        mock_check_allowed.return_value = True
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"chat_id": 123456, "username": "testuser"}
            # 沒有 current_session_id 欄位
        }
        mock_get_table.return_value = mock_table

        # 執行
        allowed, username, session_id = check_allowed_with_session(123456, "testuser")

        # 驗證：應該回退到使用 chat_id
        assert allowed is True
        assert username == "testuser"
        assert session_id == "123456"

    @patch("src.allowlist.check_allowed")
    def test_check_allowed_with_session_not_in_allowlist(self, mock_check_allowed):
        """測試用戶不在 allowlist"""
        # 設定 mock
        mock_check_allowed.return_value = False

        # 執行
        allowed, username, session_id = check_allowed_with_session(123456, "testuser")

        # 驗證
        assert allowed is False
        assert username == "testuser"
        assert session_id == "123456"  # 即使不在 allowlist，也返回 chat_id

    @patch("src.allowlist.get_dynamodb_table")
    @patch("src.allowlist.check_allowed")
    def test_check_allowed_with_session_dynamodb_error(self, mock_check_allowed, mock_get_table):
        """測試 DynamoDB 錯誤時的回退機制"""
        # 設定 mock
        mock_check_allowed.return_value = True
        mock_table = MagicMock()
        from botocore.exceptions import ClientError

        mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "GetItem"
        )
        mock_get_table.return_value = mock_table

        # 執行
        allowed, username, session_id = check_allowed_with_session(123456, "testuser")

        # 驗證：應該回退到使用 chat_id
        assert allowed is True
        assert username == "testuser"
        assert session_id == "123456"
