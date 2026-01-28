"""
Identity Service for cross-channel identity binding.

Provides functionality to:
1. Generate binding codes for Telegram users
2. Verify codes and bind Web users to Telegram users
3. Manage identity mappings and unified conversation IDs
4. Query and unbind identities

Author: AgentCore Team
Created: 2026-01-25
"""

import contextlib
import random
import time
import uuid
from typing import Any

import boto3
from botocore.exceptions import ClientError


class IdentityService:
    """Service for managing cross-channel identity binding."""

    # 綁定碼配置
    BINDING_CODE_LENGTH = 6
    BINDING_CODE_EXPIRY_MINUTES = 10
    BINDING_CODE_MAX_ATTEMPTS = 5

    def __init__(
        self, binding_codes_table_name: str, identity_map_table_name: str, dynamodb_resource=None
    ):
        """
        Initialize Identity Service.

        Args:
            binding_codes_table_name: DynamoDB table for binding codes
            identity_map_table_name: DynamoDB table for identity mappings
            dynamodb_resource: Optional DynamoDB resource (for testing)
        """
        self.binding_codes_table_name = binding_codes_table_name
        self.identity_map_table_name = identity_map_table_name

        if dynamodb_resource:
            self.dynamodb = dynamodb_resource
        else:
            self.dynamodb = boto3.resource("dynamodb")

        self.binding_codes_table = self.dynamodb.Table(binding_codes_table_name)
        self.identity_map_table = self.dynamodb.Table(identity_map_table_name)

    def generate_binding_code(self, telegram_user_id: str) -> dict[str, Any]:
        """
        Generate a binding code for a Telegram user.

        The code is a 6-digit number valid for 10 minutes.

        Args:
            telegram_user_id: Telegram user ID (e.g., "316743844")

        Returns:
            dict: {
                'code': '123456',
                'expires_at': timestamp,
                'expires_in_minutes': 10
            }

        Raises:
            Exception: If code generation fails
        """
        # 生成 6 位隨機數字碼
        code = "".join([str(random.randint(0, 9)) for _ in range(self.BINDING_CODE_LENGTH)])

        current_time = int(time.time())
        expires_at = current_time + (self.BINDING_CODE_EXPIRY_MINUTES * 60)
        ttl = expires_at + 3600  # TTL = expires_at + 1 hour（保留一段時間用於除錯）

        try:
            # 儲存綁定碼到 DynamoDB
            self.binding_codes_table.put_item(
                Item={
                    "code": code,
                    "telegram_user_id": telegram_user_id,
                    "created_at": current_time,
                    "expires_at": expires_at,
                    "used": False,
                    "attempts": 0,
                    "ttl": ttl,
                },
                # 條件：碼不存在（防止覆蓋）
                ConditionExpression="attribute_not_exists(code)",
            )

            return {
                "code": code,
                "expires_at": expires_at,
                "expires_in_minutes": self.BINDING_CODE_EXPIRY_MINUTES,
            }

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                # 碼已存在（極低機率），遞迴重試
                return self.generate_binding_code(telegram_user_id)
            else:
                raise Exception(f"Failed to generate binding code: {e}") from e

    def verify_and_bind(
        self, code: str, web_user_id: str, web_email: str | None = None
    ) -> dict[str, Any]:
        """
        Verify a binding code and bind Web user to Telegram user.

        Args:
            code: 6-digit binding code
            web_user_id: Web user ID (e.g., "user123")
            web_email: Optional Web user email

        Returns:
            dict: {
                'success': True,
                'unified_conversation_id': 'unified:xxx-xxx',
                'telegram_user_id': 'tg:316743844',
                'web_user_id': 'web:user123',
                'message': 'Binding successful'
            }

        Raises:
            ValueError: If code is invalid, expired, or already used
            Exception: If binding fails
        """
        current_time = int(time.time())

        try:
            # 1. 查詢綁定碼
            response = self.binding_codes_table.get_item(Key={"code": code})

            if "Item" not in response:
                raise ValueError("Invalid binding code")

            code_data = response["Item"]

            # 2. 驗證碼狀態
            if code_data.get("used", False):
                raise ValueError("Binding code already used")

            if current_time > code_data["expires_at"]:
                raise ValueError("Binding code expired")

            if code_data.get("attempts", 0) >= self.BINDING_CODE_MAX_ATTEMPTS:
                raise ValueError("Too many attempts for this code")

            telegram_user_id = code_data["telegram_user_id"]

            # 3. 檢查是否已有綁定
            telegram_identity_id = f"tg:{telegram_user_id}"
            web_identity_id = f"web:{web_user_id}"

            existing_telegram_binding = self._get_binding(telegram_identity_id)
            existing_web_binding = self._get_binding(web_identity_id)

            # 如果其中一個已有 unified_conversation_id，使用現有的
            unified_conversation_id = None
            if existing_telegram_binding and existing_telegram_binding.get(
                "unified_conversation_id"
            ):
                unified_conversation_id = existing_telegram_binding["unified_conversation_id"]
            elif existing_web_binding and existing_web_binding.get("unified_conversation_id"):
                unified_conversation_id = existing_web_binding["unified_conversation_id"]

            # 否則生成新的 unified_conversation_id
            if not unified_conversation_id:
                unified_conversation_id = f"unified:{uuid.uuid4()}"

            # 4. 更新/創建 identity_map 記錄
            self._create_or_update_binding(
                identity_id=telegram_identity_id,
                unified_conversation_id=unified_conversation_id,
                metadata={
                    "platform": "telegram",
                    "user_id": telegram_user_id,
                    "bound_at": current_time,
                },
            )

            self._create_or_update_binding(
                identity_id=web_identity_id,
                unified_conversation_id=unified_conversation_id,
                metadata={
                    "platform": "web",
                    "user_id": web_user_id,
                    "email": web_email,
                    "bound_at": current_time,
                },
            )

            # 5. 標記綁定碼為已使用
            self.binding_codes_table.update_item(
                Key={"code": code},
                UpdateExpression="SET used = :used, used_at = :used_at, used_by = :used_by",
                ExpressionAttributeValues={
                    ":used": True,
                    ":used_at": current_time,
                    ":used_by": web_user_id,
                },
            )

            return {
                "success": True,
                "unified_conversation_id": unified_conversation_id,
                "telegram_user_id": telegram_identity_id,
                "web_user_id": web_identity_id,
                "message": "Binding successful",
            }

        except ValueError as e:
            # 增加嘗試次數
            with contextlib.suppress(Exception):
                self.binding_codes_table.update_item(
                    Key={"code": code},
                    UpdateExpression="SET attempts = if_not_exists(attempts, :zero) + :one",
                    ExpressionAttributeValues={":zero": 0, ":one": 1},
                )

            raise e

        except ClientError as e:
            raise Exception(f"Failed to bind identities: {e}") from e

    def get_bindings(self, identity_id: str) -> dict[str, Any]:
        """
        Get all bindings for an identity.

        Args:
            identity_id: Identity ID (e.g., "tg:316743844" or "web:user123")

        Returns:
            dict: {
                'identity_id': 'tg:316743844',
                'unified_conversation_id': 'unified:xxx',
                'bound_identities': [
                    {'platform': 'web', 'user_id': 'user123', ...}
                ],
                'bound_at': timestamp
            }

        Returns None if no binding exists.
        """
        binding = self._get_binding(identity_id)

        if not binding:
            return None

        unified_id = binding.get("unified_conversation_id")
        if not unified_id:
            return {
                "identity_id": identity_id,
                "unified_conversation_id": None,
                "bound_identities": [],
                "metadata": binding.get("metadata", {}),
            }

        # 查詢所有使用相同 unified_conversation_id 的身份
        try:
            response = self.identity_map_table.query(
                IndexName="UnifiedConversationIndex",
                KeyConditionExpression="unified_conversation_id = :unified_id",
                ExpressionAttributeValues={":unified_id": unified_id},
            )

            bound_identities = []
            for item in response.get("Items", []):
                if item["identity_id"] != identity_id:  # 排除自己
                    bound_identities.append(
                        {
                            "identity_id": item["identity_id"],
                            "platform": item.get("metadata", {}).get("platform"),
                            "user_id": item.get("metadata", {}).get("user_id"),
                            "bound_at": item.get("metadata", {}).get("bound_at"),
                        }
                    )

            return {
                "identity_id": identity_id,
                "unified_conversation_id": unified_id,
                "bound_identities": bound_identities,
                "metadata": binding.get("metadata", {}),
            }

        except ClientError as e:
            raise Exception(f"Failed to get bindings: {e}") from e

    def unbind(self, identity_id: str) -> bool:
        """
        Unbind an identity (remove unified_conversation_id).

        This does NOT delete the identity_map entry, just clears the
        unified_conversation_id to "unbind" it.

        Args:
            identity_id: Identity ID to unbind

        Returns:
            bool: True if successful, False if identity not found
        """
        try:
            self.identity_map_table.update_item(
                Key={"identity_id": identity_id},
                UpdateExpression="REMOVE unified_conversation_id",
                ConditionExpression="attribute_exists(identity_id)",
            )
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False  # Identity doesn't exist
            else:
                raise Exception(f"Failed to unbind identity: {e}") from e

    def get_unified_conversation_id(self, identity_id: str) -> str | None:
        """
        Get the unified conversation ID for an identity.

        Args:
            identity_id: Identity ID

        Returns:
            str: Unified conversation ID (e.g., "unified:xxx") or None
        """
        binding = self._get_binding(identity_id)
        return binding.get("unified_conversation_id") if binding else None

    # ==================== Helper Methods ====================

    def _get_binding(self, identity_id: str) -> dict[str, Any] | None:
        """Get binding data for an identity."""
        try:
            response = self.identity_map_table.get_item(Key={"identity_id": identity_id})
            return response.get("Item")
        except ClientError:
            return None

    def _create_or_update_binding(
        self, identity_id: str, unified_conversation_id: str, metadata: dict[str, Any]
    ):
        """Create or update an identity binding."""
        current_time = int(time.time())

        self.identity_map_table.put_item(
            Item={
                "identity_id": identity_id,
                "unified_conversation_id": unified_conversation_id,
                "metadata": metadata,
                "updated_at": current_time,
                "created_at": current_time,  # 只在創建時設置
            }
        )
