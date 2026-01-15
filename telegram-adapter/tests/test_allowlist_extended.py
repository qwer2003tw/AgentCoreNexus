"""
Extended tests for allowlist module - 擴展 allowlist 模組測試
專注於提升覆蓋率：add, remove, update, stats 等功能
"""

from unittest.mock import patch

import allowlist
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws


@pytest.fixture
def mock_dynamodb_table():
    """Mock DynamoDB table"""
    with mock_aws():
        import boto3

        # 創建 DynamoDB table
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        table = dynamodb.create_table(
            TableName="telegram-allowlist",
            KeySchema=[{"AttributeName": "chat_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "chat_id", "AttributeType": "N"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # 重新初始化 allowlist 模組的 table
        allowlist.table = table

        yield table


class TestAddToAllowlist:
    """測試 add_to_allowlist 函數"""

    def test_add_user_success(self, mock_dynamodb_table):
        """測試成功添加用戶"""
        result = allowlist.add_to_allowlist(12345, "testuser", enabled=True)

        assert result is True

        # 驗證用戶已添加
        response = mock_dynamodb_table.get_item(Key={"chat_id": 12345})
        assert "Item" in response
        assert response["Item"]["chat_id"] == 12345
        assert response["Item"]["username"] == "testuser"
        assert response["Item"]["enabled"] is True

    def test_add_user_disabled(self, mock_dynamodb_table):
        """測試添加禁用的用戶"""
        result = allowlist.add_to_allowlist(12345, "testuser", enabled=False)

        assert result is True

        response = mock_dynamodb_table.get_item(Key={"chat_id": 12345})
        assert response["Item"]["enabled"] is False

    @patch("allowlist.table")
    def test_add_user_client_error(self, mock_table):
        """測試添加用戶時 DynamoDB 錯誤"""
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "Throttled"}},
            "PutItem",
        )

        result = allowlist.add_to_allowlist(12345, "testuser")

        assert result is False


class TestRemoveFromAllowlist:
    """測試 remove_from_allowlist 函數"""

    def test_remove_user_success(self, mock_dynamodb_table):
        """測試成功移除用戶"""
        # 先添加用戶
        mock_dynamodb_table.put_item(
            Item={"chat_id": 12345, "username": "testuser", "enabled": True}
        )

        # 移除用戶
        result = allowlist.remove_from_allowlist(12345)

        assert result is True

        # 驗證用戶已移除
        response = mock_dynamodb_table.get_item(Key={"chat_id": 12345})
        assert "Item" not in response

    @patch("allowlist.table")
    def test_remove_user_client_error(self, mock_table):
        """測試移除用戶時 DynamoDB 錯誤"""
        mock_table.delete_item.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}}, "DeleteItem"
        )

        result = allowlist.remove_from_allowlist(12345)

        assert result is False


class TestGetUserInfo:
    """測試 get_user_info 函數"""

    def test_get_existing_user(self, mock_dynamodb_table):
        """測試獲取存在的用戶"""
        # 添加測試用戶
        mock_dynamodb_table.put_item(
            Item={"chat_id": 12345, "username": "testuser", "enabled": True, "role": "user"}
        )

        result = allowlist.get_user_info(12345)

        assert result is not None
        assert result["chat_id"] == 12345
        assert result["username"] == "testuser"
        assert result["enabled"] is True
        assert result["role"] == "user"

    def test_get_nonexistent_user(self, mock_dynamodb_table):
        """測試獲取不存在的用戶"""
        result = allowlist.get_user_info(99999)

        assert result is None

    @patch("allowlist.table")
    def test_get_user_client_error(self, mock_table):
        """測試獲取用戶時 DynamoDB 錯誤"""
        mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "Server error"}}, "GetItem"
        )

        result = allowlist.get_user_info(12345)

        assert result is None


class TestListAllUsers:
    """測試 list_all_users 函數"""

    def test_list_users_success(self, mock_dynamodb_table):
        """測試成功列出用戶"""
        # 添加多個用戶
        mock_dynamodb_table.put_item(Item={"chat_id": 1, "username": "user1", "enabled": True})
        mock_dynamodb_table.put_item(Item={"chat_id": 2, "username": "user2", "enabled": False})
        mock_dynamodb_table.put_item(Item={"chat_id": -100, "username": "group1", "enabled": True})

        result = allowlist.list_all_users(limit=10)

        assert len(result) == 3
        # 應該按 chat_id 排序（群組在前，負數）
        assert result[0]["chat_id"] == -100
        assert result[1]["chat_id"] == 1
        assert result[2]["chat_id"] == 2

    def test_list_users_with_limit(self, mock_dynamodb_table):
        """測試帶限制的列表"""
        # 添加用戶
        for i in range(5):
            mock_dynamodb_table.put_item(
                Item={"chat_id": i, "username": f"user{i}", "enabled": True}
            )

        result = allowlist.list_all_users(limit=3)

        assert len(result) <= 3

    def test_list_empty_table(self, mock_dynamodb_table):
        """測試空表"""
        result = allowlist.list_all_users()

        assert result == []

    @patch("allowlist.table")
    def test_list_users_client_error(self, mock_table):
        """測試列表用戶時 DynamoDB 錯誤"""
        mock_table.scan.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "Server error"}}, "Scan"
        )

        result = allowlist.list_all_users()

        assert result == []


class TestUpdateUserEnabled:
    """測試 update_user_enabled 函數"""

    def test_enable_user(self, mock_dynamodb_table):
        """測試啟用用戶"""
        # 先添加禁用的用戶
        mock_dynamodb_table.put_item(
            Item={"chat_id": 12345, "username": "testuser", "enabled": False}
        )

        result = allowlist.update_user_enabled(12345, enabled=True)

        assert result is True

        # 驗證狀態已更新
        response = mock_dynamodb_table.get_item(Key={"chat_id": 12345})
        assert response["Item"]["enabled"] is True

    def test_disable_user(self, mock_dynamodb_table):
        """測試禁用用戶"""
        # 先添加啟用的用戶
        mock_dynamodb_table.put_item(
            Item={"chat_id": 12345, "username": "testuser", "enabled": True}
        )

        result = allowlist.update_user_enabled(12345, enabled=False)

        assert result is True

        response = mock_dynamodb_table.get_item(Key={"chat_id": 12345})
        assert response["Item"]["enabled"] is False

    @patch("allowlist.table")
    def test_update_enabled_client_error(self, mock_table):
        """測試更新狀態時 DynamoDB 錯誤"""
        mock_table.update_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Failed"}},
            "UpdateItem",
        )

        result = allowlist.update_user_enabled(12345, enabled=True)

        assert result is False


class TestUpdateUserRole:
    """測試 update_user_role 函數"""

    def test_update_to_admin(self, mock_dynamodb_table):
        """測試更新用戶為 admin"""
        # 先添加一般用戶
        mock_dynamodb_table.put_item(
            Item={"chat_id": 12345, "username": "testuser", "enabled": True, "role": "user"}
        )

        result = allowlist.update_user_role(12345, "admin")

        assert result is True

        response = mock_dynamodb_table.get_item(Key={"chat_id": 12345})
        assert response["Item"]["role"] == "admin"

    def test_update_to_user(self, mock_dynamodb_table):
        """測試更新 admin 為一般用戶"""
        mock_dynamodb_table.put_item(
            Item={"chat_id": 12345, "username": "testuser", "enabled": True, "role": "admin"}
        )

        result = allowlist.update_user_role(12345, "user")

        assert result is True

        response = mock_dynamodb_table.get_item(Key={"chat_id": 12345})
        assert response["Item"]["role"] == "user"

    @patch("allowlist.table")
    def test_update_role_client_error(self, mock_table):
        """測試更新角色時 DynamoDB 錯誤"""
        mock_table.update_item.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid"}}, "UpdateItem"
        )

        result = allowlist.update_user_role(12345, "admin")

        assert result is False


class TestGetStats:
    """測試 get_stats 函數"""

    def test_stats_with_data(self, mock_dynamodb_table):
        """測試統計資訊"""
        # 添加測試資料
        mock_dynamodb_table.put_item(
            Item={"chat_id": 1, "username": "user1", "enabled": True, "role": "user"}
        )
        mock_dynamodb_table.put_item(
            Item={"chat_id": 2, "username": "user2", "enabled": False, "role": "user"}
        )
        mock_dynamodb_table.put_item(
            Item={"chat_id": 3, "username": "admin1", "enabled": True, "role": "admin"}
        )
        mock_dynamodb_table.put_item(
            Item={"chat_id": -100, "username": "group1", "enabled": True, "role": "user"}
        )

        result = allowlist.get_stats()

        assert result["total_users"] == 4
        assert result["enabled_users"] == 3
        assert result["disabled_users"] == 1
        assert result["admin_count"] == 1
        assert result["user_count"] == 3
        assert result["group_count"] == 1
        assert result["private_count"] == 3

    def test_stats_empty_table(self, mock_dynamodb_table):
        """測試空表統計"""
        result = allowlist.get_stats()

        assert result["total_users"] == 0
        assert result["enabled_users"] == 0
        assert result["disabled_users"] == 0

    @patch("allowlist.table")
    def test_stats_client_error(self, mock_table):
        """測試統計時 DynamoDB 錯誤"""
        mock_table.scan.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "Error"}}, "Scan"
        )

        result = allowlist.get_stats()

        assert result == {}


class TestCheckFilePermission:
    """測試 check_file_permission 函數"""

    def test_user_with_file_permission(self, mock_dynamodb_table):
        """測試有檔案權限的用戶"""
        mock_dynamodb_table.put_item(
            Item={
                "chat_id": 12345,
                "username": "testuser",
                "enabled": True,
                "permissions": {"file_reader": True},
            }
        )

        result = allowlist.check_file_permission(12345)

        assert result is True

    def test_user_without_file_permission(self, mock_dynamodb_table):
        """測試沒有檔案權限的用戶"""
        mock_dynamodb_table.put_item(
            Item={
                "chat_id": 12345,
                "username": "testuser",
                "enabled": True,
                "permissions": {"file_reader": False},
            }
        )

        result = allowlist.check_file_permission(12345)

        assert result is False

    def test_user_no_permissions_field(self, mock_dynamodb_table):
        """測試沒有 permissions 欄位的用戶"""
        mock_dynamodb_table.put_item(
            Item={"chat_id": 12345, "username": "testuser", "enabled": True}
        )

        result = allowlist.check_file_permission(12345)

        assert result is False  # 預設無權限

    def test_disabled_user(self, mock_dynamodb_table):
        """測試禁用的用戶"""
        mock_dynamodb_table.put_item(
            Item={
                "chat_id": 12345,
                "username": "testuser",
                "enabled": False,
                "permissions": {"file_reader": True},
            }
        )

        result = allowlist.check_file_permission(12345)

        assert result is False  # 禁用用戶無權限

    def test_user_not_in_allowlist(self, mock_dynamodb_table):
        """測試不在 allowlist 的用戶"""
        result = allowlist.check_file_permission(99999)

        assert result is False

    @patch("allowlist.table")
    def test_file_permission_client_error(self, mock_table):
        """測試檢查權限時 DynamoDB 錯誤"""
        mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "Error"}}, "GetItem"
        )

        result = allowlist.check_file_permission(12345)

        assert result is False

    @patch("allowlist.table")
    def test_file_permission_unexpected_error(self, mock_table):
        """測試檢查權限時非預期錯誤"""
        mock_table.get_item.side_effect = RuntimeError("Unexpected error")

        result = allowlist.check_file_permission(12345)

        assert result is False


class TestUpdateFilePermission:
    """測試 update_file_permission 函數"""

    def test_enable_file_permission(self, mock_dynamodb_table):
        """測試啟用檔案權限"""
        # 先添加用戶（無檔案權限）
        mock_dynamodb_table.put_item(
            Item={"chat_id": 12345, "username": "testuser", "enabled": True}
        )

        result = allowlist.update_file_permission(12345, enabled=True)

        assert result is True

    def test_disable_file_permission(self, mock_dynamodb_table):
        """測試禁用檔案權限"""
        # 先添加用戶（有檔案權限）
        mock_dynamodb_table.put_item(
            Item={
                "chat_id": 12345,
                "username": "testuser",
                "enabled": True,
                "permissions": {"file_reader": True},
            }
        )

        result = allowlist.update_file_permission(12345, enabled=False)

        assert result is True

    @patch("allowlist.table")
    def test_update_file_permission_client_error(self, mock_table):
        """測試更新權限時 DynamoDB 錯誤"""
        mock_table.update_item.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid"}}, "UpdateItem"
        )

        result = allowlist.update_file_permission(12345, enabled=True)

        assert result is False

    @patch("allowlist.table")
    def test_update_file_permission_unexpected_error(self, mock_table):
        """測試更新權限時非預期錯誤"""
        mock_table.update_item.side_effect = RuntimeError("Unexpected error")

        result = allowlist.update_file_permission(12345, enabled=True)

        assert result is False


class TestCheckAllowedErrorHandling:
    """測試 check_allowed 的錯誤處理"""

    def test_check_allowed_user_disabled(self, mock_dynamodb_table):
        """測試檢查禁用的用戶"""
        mock_dynamodb_table.put_item(
            Item={"chat_id": 12345, "username": "testuser", "enabled": False}
        )

        result = allowlist.check_allowed(12345, "testuser")

        assert result is False

    def test_check_allowed_username_mismatch(self, mock_dynamodb_table):
        """測試用戶名不匹配"""
        mock_dynamodb_table.put_item(
            Item={"chat_id": 12345, "username": "correct_user", "enabled": True}
        )

        result = allowlist.check_allowed(12345, "wrong_user")

        assert result is False

    def test_check_allowed_no_username(self, mock_dynamodb_table):
        """測試沒有提供 username"""
        mock_dynamodb_table.put_item(Item={"chat_id": 12345, "enabled": True})

        result = allowlist.check_allowed(12345, "")

        assert result is True  # 沒有 username 時跳過驗證

    @patch("allowlist.table")
    def test_check_allowed_unexpected_error(self, mock_table):
        """測試 check_allowed 時非預期錯誤"""
        mock_table.get_item.side_effect = RuntimeError("Unexpected error")

        result = allowlist.check_allowed(12345, "testuser")

        assert result is False


class TestComplexScenarios:
    """測試複雜場景"""

    def test_user_lifecycle(self, mock_dynamodb_table):
        """測試用戶生命週期：添加 → 更新 → 移除"""
        # 1. 添加用戶
        assert allowlist.add_to_allowlist(12345, "testuser", enabled=True) is True

        # 2. 驗證用戶存在
        user = allowlist.get_user_info(12345)
        assert user is not None
        assert user["enabled"] is True

        # 3. 禁用用戶
        assert allowlist.update_user_enabled(12345, enabled=False) is True

        # 4. 更新角色
        assert allowlist.update_user_role(12345, "admin") is True

        # 5. 啟用檔案權限
        assert allowlist.update_file_permission(12345, enabled=True) is True

        # 6. 移除用戶
        assert allowlist.remove_from_allowlist(12345) is True

        # 7. 驗證已移除
        user = allowlist.get_user_info(12345)
        assert user is None

    def test_stats_calculation(self, mock_dynamodb_table):
        """測試統計計算準確性"""
        # 添加各種類型的用戶
        mock_dynamodb_table.put_item(
            Item={"chat_id": 1, "username": "user1", "enabled": True, "role": "user"}
        )
        mock_dynamodb_table.put_item(
            Item={"chat_id": 2, "username": "user2", "enabled": True, "role": "admin"}
        )
        mock_dynamodb_table.put_item(
            Item={"chat_id": 3, "username": "user3", "enabled": False, "role": "user"}
        )
        mock_dynamodb_table.put_item(
            Item={"chat_id": -100, "username": "group1", "enabled": True, "role": "user"}
        )

        stats = allowlist.get_stats()

        assert stats["total_users"] == 4
        assert stats["enabled_users"] == 3
        assert stats["disabled_users"] == 1
        assert stats["admin_count"] == 1
        assert stats["user_count"] == 3
        assert stats["group_count"] == 1
        assert stats["private_count"] == 3
