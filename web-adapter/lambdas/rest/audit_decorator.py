"""
Audit Decorator - 審計日誌裝飾器
自動記錄管理員的 API 操作
"""

import json
import os
import sys
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

# 在 Lambda 環境，audit_service 在 /opt/python（layer）
sys.path.insert(0, '/opt/python')
from audit_service import AuditService


def create_audit_service():
    """創建 AuditService 實例"""
    audit_table = os.environ.get('AUDIT_LOGS_TABLE', 'agentcore-admin-audit-logs-dev')
    config_table = os.environ.get('SYSTEM_CONFIG_TABLE', 'agentcore-admin-system-config-dev')
    return AuditService(audit_table, config_table)


def audit_log(action: str, resource_type: str, extract_resource_id: Callable | None = None):
    """
    審計日誌裝飾器 - 自動記錄管理員操作

    Args:
        action: 操作類型（見 audit_service.AUDIT_ACTIONS）
        resource_type: 資源類型（conversation/user/stats/system）
        extract_resource_id: 從 event 提取 resource_id 的函數（可選）
                           如果未提供，默認從 pathParameters.id 提取

    Usage:
        @audit_log('view_conversation', 'conversation')
        def get_conversation_handler(event, context):
            ...

        @audit_log('search_conversations', 'conversation',
                   extract_resource_id=lambda e: 'search-query')
        def search_handler(event, context):
            ...

    Returns:
        裝飾後的函數（會自動記錄審計日誌）
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: dict[str, Any], context: Any) -> dict[str, Any]:
            start_time = time.time()
            audit_service = create_audit_service()

            # 提取管理員資訊（從 Lambda Authorizer）
            try:
                authorizer = event.get("requestContext", {}).get("authorizer", {})
                admin_email = authorizer.get("email", "unknown")
                admin_id = authorizer.get("sub", "unknown")
                admin_role = authorizer.get("role", "unknown")
            except:
                admin_email = "unknown"
                admin_id = "unknown"
                admin_role = "unknown"

            # 提取資源 ID
            if extract_resource_id:
                resource_id = extract_resource_id(event)
            else:
                # 默認從 pathParameters.id 提取
                path_params = event.get("pathParameters") or {}
                resource_id = path_params.get("id") or path_params.get("conversation_id") or "N/A"

            # 提取請求資訊
            request_context = event.get("requestContext", {})
            identity = request_context.get("identity", {})
            ip_address = identity.get("sourceIp")
            user_agent = identity.get("userAgent")
            request_id = context.request_id if hasattr(context, "request_id") else None

            # 提取操作詳情（可選）
            details = None
            try:
                # 從 query parameters 或 body 提取相關資訊
                query_params = event.get("queryStringParameters", {})
                if query_params:
                    details = {"query": query_params}

                # 如果是 POST/PUT，嘗試解析 body
                if event.get("httpMethod") in ["POST", "PUT", "PATCH"]:
                    body = event.get("body")
                    if body:
                        try:
                            body_data = json.loads(body)
                            # 只記錄關鍵欄位，不記錄敏感內容
                            safe_keys = [
                                "search",
                                "filter",
                                "limit",
                                "page",
                                "channel",
                                "format",
                            ]
                            details = {k: v for k, v in body_data.items() if k in safe_keys}
                        except:
                            pass
            except:
                pass

            # 執行原函數
            result = None
            status = "success"
            error_message = None

            try:
                result = func(event, context)

                # 檢查響應狀態
                if isinstance(result, dict):
                    status_code = result.get("statusCode", 200)
                    if status_code >= 400:
                        status = "failed"
                        try:
                            body = json.loads(result.get("body", "{}"))
                            error_message = body.get("error", f"HTTP {status_code}")
                        except:
                            error_message = f"HTTP {status_code}"

            except Exception as e:
                status = "failed"
                error_message = str(e)
                raise  # 重新拋出異常

            finally:
                # 計算請求耗時
                request_duration_ms = int((time.time() - start_time) * 1000)

                # 記錄審計日誌（異步，不阻塞響應）
                try:
                    audit_service.log_action(
                        admin_email=admin_email,
                        admin_id=admin_id,
                        admin_role=admin_role,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        details=details,
                        status=status,
                        error_message=error_message,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_id=request_id,
                        request_duration_ms=request_duration_ms,
                    )
                except Exception as audit_error:
                    # 審計失敗不影響主操作
                    print(f"⚠️ Audit logging failed: {str(audit_error)}")

            return result

        return wrapper

    return decorator


def require_permission(permission: str):
    """
    權限檢查裝飾器

    Args:
        permission: 需要的權限（如 'view_audit_logs'）

    Usage:
        @require_permission('view_audit_logs')
        @audit_log('view_audit_logs', 'audit')
        def get_audit_logs_handler(event, context):
            ...

    Returns:
        裝飾後的函數（會檢查權限）
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: dict[str, Any], context: Any) -> dict[str, Any]:
            # 提取用戶角色
            try:
                authorizer = event.get("requestContext", {}).get("authorizer", {})
                user_role = authorizer.get("role", "user")
                admin_email = authorizer.get("email", "unknown")
                admin_id = authorizer.get("sub", "unknown")
            except:
                user_role = "user"
                admin_email = "unknown"
                admin_id = "unknown"

            # Debug 日誌
            check_result = check_permission(user_role, permission)
            print(f"🔍 Permission Check: user_role={repr(user_role)}, required={repr(permission)}, result={check_result}")
            print(f"🔍 USER_ROLES keys: {list(USER_ROLES.keys())}")
            print(f"🔍 Is role in USER_ROLES? {permission in USER_ROLES}")

            # 檢查權限
            if not check_result:
                # 記錄未授權訪問嘗試
                try:
                    audit_service = create_audit_service()
                    audit_service.log_action(
                        admin_email=admin_email,
                        admin_id=admin_id,
                        admin_role=user_role,
                        action="permission_denied",
                        resource_type="system",
                        resource_id=permission,
                        status="failed",
                        error_message=f"User role '{user_role}' lacks permission '{permission}'",
                    )
                except:
                    pass

                return {
                    "statusCode": 403,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(
                        {
                            "error": "Permission denied",
                            "required_permission": permission,
                            "user_role": user_role,
                        }
                    ),
                }

            # 權限檢查通過，執行函數
            return func(event, context)

        return wrapper

    return decorator


# ============================================================
# 權限系統
# ============================================================

USER_ROLES = {
    "user": {
        "permissions": [
            "chat",
            "view_own_history",
            "delete_own_conversation",
        ]
    },
    "admin": {
        "permissions": [
            "view_all_conversations",
            "generate_summary",
            "export_conversations",
            "view_stats",
            "manage_users",
        ],
        "inherits": ["user"],
    },
    "auditor": {
        "permissions": [
            "view_audit_logs",
            "export_audit_logs",
            "search_audit_logs",
            "view_all_conversations",  # 只讀
        ]
    },
    "super_admin": {
        "permissions": ["*"],  # 所有權限
        "inherits": ["admin", "auditor"],
    },
}


def check_permission(user_role: str, required_permission: str) -> bool:
    """
    檢查用戶是否有指定權限

    Args:
        user_role: 用戶角色
        required_permission: 需要的權限或角色名

    Returns:
        是否有權限
    """
    # 如果 required_permission 是角色名，檢查是否匹配
    if required_permission in USER_ROLES:
        # 檢查用戶角色是否等於或高於要求的角色
        if user_role == required_permission:
            return True
        # 檢查是否是 super_admin（最高權限）
        if user_role == 'super_admin':
            return True
        return False

    # 否則當作權限名檢查
    role_config = USER_ROLES.get(user_role, {})
    permissions = role_config.get("permissions", [])

    # super_admin 擁有所有權限
    if "*" in permissions:
        return True

    # 檢查直接權限
    if required_permission in permissions:
        return True

    # 檢查繼承的權限
    inherits = role_config.get("inherits", [])
    for parent_role in inherits:
        if check_permission(parent_role, required_permission):
            return True

    return False
