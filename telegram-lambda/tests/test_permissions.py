"""
Tests for auth.permissions module
"""

from unittest.mock import patch

from auth.permissions import Permission, UserRole, check_permission, get_permission_level


class TestPermission:
    """測試 Permission 枚舉"""

    def test_permission_values(self):
        """測試權限等級數值"""
        assert Permission.NONE == 0
        assert Permission.ALLOWLIST == 1
        assert Permission.ADMIN == 2

    def test_permission_ordering(self):
        """測試權限等級排序"""
        assert Permission.NONE < Permission.ALLOWLIST
        assert Permission.ALLOWLIST < Permission.ADMIN


class TestUserRole:
    """測試 UserRole 常數"""

    def test_role_values(self):
        """測試角色常數值"""
        assert UserRole.USER == "user"
        assert UserRole.ADMIN == "admin"


class TestCheckPermission:
    """測試 check_permission 函數"""

    def test_permission_none_always_granted(self):
        """測試 NONE 權限總是通過"""
        result = check_permission(123, "test_user", Permission.NONE)
        assert result is True

    @patch("auth.admin_list.is_admin")
    def test_admin_has_all_permissions(self, mock_is_admin):
        """測試 admin 擁有所有權限"""
        mock_is_admin.return_value = True

        # Admin 可以通過所有權限檢查
        assert check_permission(123, "admin", Permission.ALLOWLIST) is True
        assert check_permission(123, "admin", Permission.ADMIN) is True

    @patch("auth.admin_list.is_admin")
    @patch("auth.permissions.check_allowed")
    def test_allowlist_permission_check(self, mock_check_allowed, mock_is_admin):
        """測試 allowlist 權限檢查"""
        mock_is_admin.return_value = False
        mock_check_allowed.return_value = True

        result = check_permission(123, "user", Permission.ALLOWLIST)
        assert result is True
        mock_check_allowed.assert_called_once_with(123, "user")

    @patch("auth.admin_list.is_admin")
    @patch("auth.permissions.check_allowed")
    def test_allowlist_permission_denied(self, mock_check_allowed, mock_is_admin):
        """測試 allowlist 權限拒絕"""
        mock_is_admin.return_value = False
        mock_check_allowed.return_value = False

        result = check_permission(123, "user", Permission.ALLOWLIST)
        assert result is False

    @patch("auth.admin_list.is_admin")
    def test_admin_permission_denied_for_non_admin(self, mock_is_admin):
        """測試非 admin 用戶無法通過 ADMIN 權限檢查"""
        mock_is_admin.return_value = False

        result = check_permission(123, "user", Permission.ADMIN)
        assert result is False


class TestGetPermissionLevel:
    """測試 get_permission_level 函數"""

    def test_admin_role(self):
        """測試 admin 角色"""
        level = get_permission_level(UserRole.ADMIN)
        assert level == Permission.ADMIN

    def test_user_role(self):
        """測試 user 角色"""
        level = get_permission_level(UserRole.USER)
        assert level == Permission.ALLOWLIST

    def test_unknown_role(self):
        """測試未知角色"""
        level = get_permission_level("unknown")
        assert level == Permission.NONE

    def test_empty_role(self):
        """測試空字串角色"""
        level = get_permission_level("")
        assert level == Permission.NONE
