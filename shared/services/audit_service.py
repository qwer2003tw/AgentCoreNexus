"""
Audit Service - 審計日誌服務
記錄所有管理員操作，提供完整的審計追蹤
"""

import os
import time
import uuid
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# DynamoDB 配置（連接池優化）
_dynamodb_config = Config(
    max_pool_connections=10,
    retries={"max_attempts": 3},
    connect_timeout=5,
    read_timeout=10,
)

# 全局 DynamoDB resource（Lambda 容器複用）
_dynamodb_resource = None


def get_dynamodb_resource():
    """取得 DynamoDB resource 單例"""
    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb", config=_dynamodb_config)
    return _dynamodb_resource


# ============================================================
# Audit Action Types - 審計操作類型定義
# ============================================================

AUDIT_ACTIONS = {
    # 對話相關操作
    "view_conversation_list": "查看對話列表",
    "view_conversation_detail": "查看對話詳情",
    "search_conversations": "搜尋對話",
    "generate_summary": "生成 AI 摘要",
    "batch_generate_summary": "批量生成摘要",
    "regenerate_summary": "重新生成摘要",
    "export_conversation_json": "匯出對話（JSON）",
    "export_conversation_csv": "匯出對話（CSV）",
    "export_batch": "批量匯出對話",
    "delete_conversation": "刪除對話",
    "restore_conversation": "恢復對話",
    # 用戶管理操作
    "create_user": "創建新用戶",
    "update_user": "更新用戶資訊",
    "delete_user": "刪除用戶",
    "disable_user": "禁用用戶",
    "enable_user": "啟用用戶",
    "change_user_role": "修改用戶角色",
    "grant_permission": "授予權限",
    "revoke_permission": "撤銷權限",
    "reset_user_password": "重置用戶密碼",
    "force_password_change": "強制修改密碼",
    "view_user_bindings": "查看用戶綁定",
    "update_user_binding": "更新用戶綁定",
    # 統計和分析操作
    "view_dashboard": "查看統計儀表板",
    "view_user_stats": "查看用戶統計",
    "view_conversation_stats": "查看對話統計",
    "export_stats_report": "匯出統計報告",
    "run_custom_query": "執行自定義查詢",
    "generate_analytics_report": "生成分析報告",
    # 系統設置操作
    "update_system_config": "更新系統配置",
    "update_audit_config": "更新審計配置",
    "update_retention_policy": "更新保留策略",
    "update_ai_model_config": "更新 AI 模型配置",
    "update_summary_settings": "更新摘要設置",
    # 審計日誌操作（meta-audit）
    "view_audit_logs": "查看審計日誌",
    "search_audit_logs": "搜尋審計日誌",
    "export_audit_logs": "匯出審計日誌",
    "update_audit_retention": "更新審計保留期限",
    "configure_audit_alerts": "配置審計告警",
    # 認證和安全操作
    "admin_login": "管理員登入",
    "admin_login_failed": "管理員登入失敗",
    "admin_logout": "管理員登出",
    "admin_session_timeout": "管理員會話超時",
    "unauthorized_access_attempt": "未授權訪問嘗試",
    "permission_denied": "權限被拒絕",
    "bulk_delete_attempt": "批量刪除嘗試",
    "data_export_large": "大量數據匯出",
    # 錯誤和異常
    "api_error": "API 錯誤",
    "database_error": "數據庫錯誤",
    "timeout_error": "超時錯誤",
    "invalid_operation": "無效操作",
    "resource_not_found": "資源不存在",
    "validation_failed": "驗證失敗",
}

# 操作分類
ACTION_CATEGORIES = {
    "read": [
        "view_",
        "search_",
    ],
    "write": [
        "generate_",
        "update_",
        "create_",
        "regenerate_",
    ],
    "export": [
        "export_",
    ],
    "delete": [
        "delete_",
        "restore_",
    ],
    "system": [
        "admin_",
        "configure_",
    ],
    "security": [
        "unauthorized_",
        "permission_",
        "bulk_delete_",
    ],
    "error": [
        "_error",
        "_failed",
        "invalid_",
    ],
}

# 操作敏感度等級（影響保留期限）
ACTION_SENSITIVITY = {
    "critical": [
        "delete_conversation",
        "delete_user",
        "unauthorized_access_attempt",
        "bulk_delete_attempt",
        "data_export_large",
    ],
    "high": [
        "reset_user_password",
        "change_user_role",
        "update_system_config",
        "export_",
    ],
    "medium": [
        "view_conversation",
        "generate_summary",
        "admin_login",
    ],
    "low": [
        "view_dashboard",
        "view_stats",
    ],
}


class AuditService:
    """審計日誌服務"""

    def __init__(self, audit_table_name: str, config_table_name: str):
        """
        初始化審計服務

        Args:
            audit_table_name: 審計日誌表名稱
            config_table_name: 系統配置表名稱
        """
        dynamodb = get_dynamodb_resource()
        self.audit_table = dynamodb.Table(audit_table_name)
        self.config_table = dynamodb.Table(config_table_name)
        self._config_cache = {}  # 配置快取
        self._cache_time = 0

    def log_action(
        self,
        admin_email: str,
        admin_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        admin_role: str | None = None,
        resource_owner: str | None = None,
        details: dict[str, Any] | None = None,
        status: str = "success",
        error_message: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        request_duration_ms: int | None = None,
    ) -> dict[str, Any]:
        """
        記錄管理員操作

        Args:
            admin_email: 管理員 email
            admin_id: 管理員 unified_user_id
            action: 操作類型（見 AUDIT_ACTIONS）
            resource_type: 資源類型（conversation/user/stats）
            resource_id: 資源 ID
            admin_role: 管理員角色（可選）
            resource_owner: 資源擁有者（可選）
            details: 操作詳情（可選）
            status: 操作結果（success/failed）
            error_message: 錯誤訊息（如果失敗）
            ip_address: IP 地址（可選）
            user_agent: User Agent（可選，會截斷到 200 字符）
            request_id: AWS Request ID（可選）
            request_duration_ms: 請求耗時（毫秒，可選）

        Returns:
            記錄結果 {'success': bool, 'log_id': str}
        """
        now = int(time.time() * 1000)  # 毫秒
        log_id = str(uuid.uuid4())

        # 確定操作分類和敏感度
        action_category = self._get_action_category(action)
        action_sensitivity = self._get_action_sensitivity(action)

        # 準備日誌項目
        item = {
            "log_id": log_id,
            "timestamp": now,
            "admin_email": admin_email,
            "admin_id": admin_id,
            "action": action,
            "action_category": action_category,
            "action_sensitivity": action_sensitivity,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "status": status,
        }

        # 可選字段
        if admin_role:
            item["admin_role"] = admin_role
        if resource_owner:
            item["resource_owner"] = resource_owner
        if details:
            item["details"] = details
        if error_message:
            item["error_message"] = error_message[:500]  # 限制錯誤訊息長度
        if ip_address:
            item["ip_address"] = ip_address
        if user_agent:
            item["user_agent"] = user_agent[:200]  # 截斷 User Agent
        if request_id:
            item["request_id"] = request_id
        if request_duration_ms is not None:
            item["request_duration_ms"] = request_duration_ms

        # 設置 TTL（根據配置和敏感度）
        item["ttl"] = self._calculate_ttl(action_sensitivity)
        item["retention_policy"] = action_sensitivity

        try:
            self.audit_table.put_item(Item=item)
            return {"success": True, "log_id": log_id}
        except ClientError as e:
            # 審計日誌記錄失敗不應阻止主操作
            print(f"❌ Failed to log audit action: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_logs(
        self,
        admin_email: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 100,
        last_evaluated_key: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        查詢審計日誌

        Args:
            admin_email: 按管理員篩選（使用 AdminEmailIndex）
            resource_id: 按資源 ID 篩選（使用 ResourceIdIndex）
            action: 按操作類型篩選（使用 ActionIndex）
            start_time: 起始時間（毫秒）
            end_time: 結束時間（毫秒）
            limit: 返回數量限制（最大 500）
            last_evaluated_key: 分頁標記（可選）

        Returns:
            日誌列表和分頁資訊
        """
        limit = min(limit, 500)  # 限制最大查詢數量

        try:
            # 根據篩選條件選擇查詢方式
            if admin_email:
                return self._query_by_admin(
                    admin_email, start_time, end_time, limit, last_evaluated_key
                )
            elif resource_id:
                return self._query_by_resource(
                    resource_id, start_time, end_time, limit, last_evaluated_key
                )
            elif action:
                return self._query_by_action(
                    action, start_time, end_time, limit, last_evaluated_key
                )
            else:
                return self._scan_logs(start_time, end_time, limit, last_evaluated_key)

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            print(f"❌ Failed to get audit logs: {error_code} - {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_code": error_code,
                "logs": [],
            }

    def _query_by_admin(
        self,
        admin_email: str,
        start_time: int | None,
        end_time: int | None,
        limit: int,
        last_key: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """使用 AdminEmailIndex 查詢"""
        query_params = {
            "IndexName": "AdminEmailIndex",
            "KeyConditionExpression": "admin_email = :email",
            "ExpressionAttributeValues": {":email": admin_email},
            "Limit": limit,
            "ScanIndexForward": False,  # 最新優先
        }

        # 時間範圍過濾
        if start_time or end_time:
            time_condition = []
            values = {}
            if start_time:
                time_condition.append("#ts >= :start")
                values[":start"] = start_time
            if end_time:
                time_condition.append("#ts <= :end")
                values[":end"] = end_time

            query_params["KeyConditionExpression"] += " AND " + " AND ".join(time_condition)
            query_params["ExpressionAttributeNames"] = {"#ts": "timestamp"}
            query_params["ExpressionAttributeValues"].update(values)

        if last_key:
            query_params["ExclusiveStartKey"] = last_key

        response = self.audit_table.query(**query_params)
        return self._format_response(response)

    def _query_by_resource(
        self,
        resource_id: str,
        start_time: int | None,
        end_time: int | None,
        limit: int,
        last_key: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """使用 ResourceIdIndex 查詢"""
        query_params = {
            "IndexName": "ResourceIdIndex",
            "KeyConditionExpression": "resource_id = :rid",
            "ExpressionAttributeValues": {":rid": resource_id},
            "Limit": limit,
            "ScanIndexForward": False,
        }

        # 時間範圍過濾（同上）
        if start_time or end_time:
            time_condition = []
            values = {}
            if start_time:
                time_condition.append("#ts >= :start")
                values[":start"] = start_time
            if end_time:
                time_condition.append("#ts <= :end")
                values[":end"] = end_time

            query_params["KeyConditionExpression"] += " AND " + " AND ".join(time_condition)
            query_params["ExpressionAttributeNames"] = {"#ts": "timestamp"}
            query_params["ExpressionAttributeValues"].update(values)

        if last_key:
            query_params["ExclusiveStartKey"] = last_key

        response = self.audit_table.query(**query_params)
        return self._format_response(response)

    def _query_by_action(
        self,
        action: str,
        start_time: int | None,
        end_time: int | None,
        limit: int,
        last_key: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """使用 ActionIndex 查詢"""
        query_params = {
            "IndexName": "ActionIndex",
            "KeyConditionExpression": "action = :act",
            "ExpressionAttributeValues": {":act": action},
            "Limit": limit,
            "ScanIndexForward": False,
        }

        # 時間範圍過濾（同上）
        if start_time or end_time:
            time_condition = []
            values = {}
            if start_time:
                time_condition.append("#ts >= :start")
                values[":start"] = start_time
            if end_time:
                time_condition.append("#ts <= :end")
                values[":end"] = end_time

            query_params["KeyConditionExpression"] += " AND " + " AND ".join(time_condition)
            query_params["ExpressionAttributeNames"] = {"#ts": "timestamp"}
            query_params["ExpressionAttributeValues"].update(values)

        if last_key:
            query_params["ExclusiveStartKey"] = last_key

        response = self.audit_table.query(**query_params)
        return self._format_response(response)

    def _scan_logs(
        self,
        start_time: int | None,
        end_time: int | None,
        limit: int,
        last_key: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        掃描所有日誌（無篩選條件時使用）
        注意：這個操作較慢，建議使用篩選條件
        """
        scan_params = {
            "Limit": limit,
        }

        # 時間範圍過濾
        if start_time or end_time:
            filter_exp = []
            values = {}
            if start_time:
                filter_exp.append("#ts >= :start")
                values[":start"] = start_time
            if end_time:
                filter_exp.append("#ts <= :end")
                values[":end"] = end_time

            scan_params["FilterExpression"] = " AND ".join(filter_exp)
            scan_params["ExpressionAttributeNames"] = {"#ts": "timestamp"}
            scan_params["ExpressionAttributeValues"] = values

        if last_key:
            scan_params["ExclusiveStartKey"] = last_key

        response = self.audit_table.scan(**scan_params)
        return self._format_response(response)

    def _format_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """格式化查詢響應"""
        logs = response.get("Items", [])
        next_key = response.get("LastEvaluatedKey")

        # 按時間排序（最新優先）
        logs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        return {
            "success": True,
            "logs": logs,
            "count": len(logs),
            "has_more": bool(next_key),
            "next_key": next_key,
        }

    def _get_action_category(self, action: str) -> str:
        """根據操作類型判斷分類"""
        for category, prefixes in ACTION_CATEGORIES.items():
            for prefix in prefixes:
                if action.startswith(prefix) or prefix in action:
                    return category
        return "other"

    def _get_action_sensitivity(self, action: str) -> str:
        """根據操作類型判斷敏感度"""
        for sensitivity, actions in ACTION_SENSITIVITY.items():
            for pattern in actions:
                if action == pattern or (pattern.endswith("_") and action.startswith(pattern)):
                    return sensitivity
        return "medium"  # 默認中等敏感度

    def _calculate_ttl(self, sensitivity: str) -> int:
        """
        計算 TTL（根據敏感度和配置）

        Args:
            sensitivity: 敏感度等級（critical/high/medium/low）

        Returns:
            Unix timestamp (TTL)
        """
        # 默認保留期限（天）
        default_retention = {
            "critical": 365,  # 1 年
            "high": 180,  # 6 個月
            "medium": 90,  # 3 個月
            "low": 30,  # 1 個月
        }

        # 嘗試從配置表讀取（帶快取）
        try:
            config_key = f"audit_log_retention_{sensitivity}"
            retention_days = self._get_config(config_key, default_retention[sensitivity])
        except:
            retention_days = default_retention[sensitivity]

        return int(time.time()) + (retention_days * 86400)

    def _get_config(self, config_key: str, default_value: Any = None) -> Any:
        """
        從配置表讀取配置（帶 5 分鐘快取）

        Args:
            config_key: 配置鍵
            default_value: 默認值

        Returns:
            配置值
        """
        now = time.time()

        # 檢查快取（5 分鐘有效）
        if now - self._cache_time < 300 and config_key in self._config_cache:
            return self._config_cache[config_key]

        # 從 DynamoDB 讀取
        try:
            response = self.config_table.get_item(Key={"config_key": config_key})
            if "Item" in response:
                value = response["Item"].get("config_value", default_value)
                self._config_cache[config_key] = value
                self._cache_time = now
                return value
        except ClientError:
            pass

        return default_value

    def update_retention_policy(
        self, sensitivity: str, retention_days: int, admin_email: str
    ) -> dict[str, Any]:
        """
        更新審計日誌保留策略

        Args:
            sensitivity: 敏感度等級（critical/high/medium/low）
            retention_days: 保留天數
            admin_email: 執行更新的管理員

        Returns:
            更新結果
        """
        config_key = f"audit_log_retention_{sensitivity}"

        try:
            # 獲取舊值（用於審計）
            old_value = self._get_config(config_key, None)

            # 更新配置
            self.config_table.put_item(
                Item={
                    "config_key": config_key,
                    "config_value": retention_days,
                    "updated_at": int(time.time()),
                    "updated_by": admin_email,
                    "description": f"審計日誌保留期限（{sensitivity} 敏感度）",
                }
            )

            # 清除快取
            self._config_cache.clear()
            self._cache_time = 0

            return {
                "success": True,
                "config_key": config_key,
                "old_value": old_value,
                "new_value": retention_days,
            }

        except ClientError as e:
            return {"success": False, "error": str(e)}


# ============================================================
# 工廠函數（便於在 Lambda 中使用）
# ============================================================


def create_audit_service(
    audit_table_name: str | None = None, config_table_name: str | None = None
) -> AuditService:
    """
    創建 AuditService 實例

    Args:
        audit_table_name: 審計日誌表名稱（可選，從環境變數讀取）
        config_table_name: 配置表名稱（可選，從環境變數讀取）

    Returns:
        AuditService 實例
    """
    audit_table = audit_table_name or os.environ.get(
        "ADMIN_AUDIT_LOGS_TABLE", "agentcore-admin-audit-logs-dev"
    )

    config_table = config_table_name or os.environ.get(
        "ADMIN_SYSTEM_CONFIG_TABLE", "agentcore-admin-system-config-dev"
    )

    return AuditService(audit_table, config_table)
