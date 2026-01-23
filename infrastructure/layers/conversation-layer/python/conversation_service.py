"""
Conversation Storage Service (Lambda Layer Version)
管理對話歷史的 DynamoDB 讀寫操作
"""

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


class ConversationService:
    """對話儲存服務"""

    def __init__(self, history_table_name: str, metadata_table_name: str):
        """
        初始化對話服務

        Args:
            history_table_name: 對話歷史表名稱
            metadata_table_name: 對話元數據表名稱
        """
        dynamodb = get_dynamodb_resource()
        self.history_table = dynamodb.Table(history_table_name)
        self.metadata_table = dynamodb.Table(metadata_table_name)

    def save_message(
        self,
        conversation_id: str,
        sender_id: str,
        sender_name: str,
        content: str,
        message_type: str = "text",
        channel: str = "telegram",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """儲存訊息到對話歷史"""
        message_id = str(uuid.uuid4())
        timestamp = int(time.time() * 1000)

        item = {
            "conversation_id": conversation_id,
            "timestamp": timestamp,
            "message_id": message_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": content,
            "message_type": message_type,
            "channel": channel,
        }

        if metadata:
            item["metadata"] = metadata

        try:
            self.history_table.put_item(Item=item)
            self._update_metadata(conversation_id, sender_id, channel)

            return {
                "success": True,
                "message_id": message_id,
                "timestamp": timestamp,
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            print(f"❌ Failed to save message: {error_code} - {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_code": error_code,
            }

    def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        start_time: int | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """查詢對話訊息"""
        limit = min(limit, 500)

        try:
            metadata = self._get_metadata(conversation_id)
            if metadata and metadata.get("deleted_at"):
                return {
                    "success": False,
                    "error": "Conversation has been deleted",
                    "messages": [],
                }

            query_params = {
                "KeyConditionExpression": "conversation_id = :conv_id",
                "ExpressionAttributeValues": {":conv_id": conversation_id},
                "Limit": limit,
                "ScanIndexForward": False,
            }

            if start_time:
                query_params["KeyConditionExpression"] += " AND #ts >= :start_time"
                query_params["ExpressionAttributeNames"] = {"#ts": "timestamp"}
                query_params["ExpressionAttributeValues"][":start_time"] = start_time

            if last_evaluated_key:
                query_params["ExclusiveStartKey"] = last_evaluated_key

            response = self.history_table.query(**query_params)

            messages = response.get("Items", [])
            next_key = response.get("LastEvaluatedKey")

            return {
                "success": True,
                "messages": messages,
                "count": len(messages),
                "has_more": bool(next_key),
                "next_key": next_key,
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            print(f"❌ Failed to get messages: {error_code} - {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_code": error_code,
                "messages": [],
            }

    def delete_conversation(self, conversation_id: str, hard_delete: bool = False) -> dict[str, Any]:
        """刪除對話（預設軟刪除）"""
        try:
            if hard_delete:
                return self._hard_delete_conversation(conversation_id)
            else:
                return self._soft_delete_conversation(conversation_id)

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            print(f"❌ Failed to delete conversation: {error_code} - {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_code": error_code,
            }

    def _soft_delete_conversation(self, conversation_id: str) -> dict[str, Any]:
        """軟刪除對話"""
        now = int(time.time())
        delete_time = now + (30 * 86400)

        self.metadata_table.update_item(
            Key={"conversation_id": conversation_id},
            UpdateExpression="SET deleted_at = :now, delete_at = :delete_time",
            ExpressionAttributeValues={
                ":now": now,
                ":delete_time": delete_time,
            },
        )

        return {
            "success": True,
            "deleted_at": now,
            "recoverable_until": delete_time,
            "recovery_days": 30,
        }

    def _hard_delete_conversation(self, conversation_id: str) -> dict[str, Any]:
        """硬刪除對話"""
        deleted_count = 0

        response = self.history_table.query(
            KeyConditionExpression="conversation_id = :conv_id",
            ExpressionAttributeValues={":conv_id": conversation_id},
            ProjectionExpression="conversation_id, #ts",
            ExpressionAttributeNames={"#ts": "timestamp"},
        )

        with self.history_table.batch_writer() as batch:
            for item in response.get("Items", []):
                batch.delete_item(
                    Key={
                        "conversation_id": item["conversation_id"],
                        "timestamp": item["timestamp"],
                    }
                )
                deleted_count += 1

        self.metadata_table.delete_item(Key={"conversation_id": conversation_id})

        return {
            "success": True,
            "deleted_count": deleted_count,
            "permanent": True,
        }

    def restore_conversation(self, conversation_id: str) -> dict[str, Any]:
        """恢復已刪除的對話"""
        try:
            self.metadata_table.update_item(
                Key={"conversation_id": conversation_id},
                UpdateExpression="REMOVE deleted_at, delete_at",
            )

            return {"success": True, "conversation_id": conversation_id}

        except ClientError as e:
            return {
                "success": False,
                "error": str(e),
            }

    def get_conversation_metadata(self, conversation_id: str) -> dict[str, Any] | None:
        """取得對話元數據"""
        try:
            response = self.metadata_table.get_item(Key={"conversation_id": conversation_id})
            return response.get("Item")
        except ClientError as e:
            print(f"❌ Failed to get metadata: {str(e)}")
            return None

    def _get_metadata(self, conversation_id: str) -> dict[str, Any] | None:
        """內部使用：取得元數據"""
        try:
            response = self.metadata_table.get_item(Key={"conversation_id": conversation_id})
            return response.get("Item")
        except:
            return None

    def _update_metadata(self, conversation_id: str, sender_id: str, channel: str) -> None:
        """更新對話元數據"""
        now = int(time.time())
        is_group = "group" in conversation_id

        try:
            existing = self._get_metadata(conversation_id)

            if not existing:
                self.metadata_table.put_item(
                    Item={
                        "conversation_id": conversation_id,
                        "created_at": now,
                        "last_message_at": now,
                        "message_count": 1,
                        "participant_ids": [sender_id],
                        "channel": channel,
                        "is_group": is_group,
                    }
                )
            else:
                participant_ids = existing.get("participant_ids", [])
                if sender_id not in participant_ids:
                    participant_ids.append(sender_id)

                self.metadata_table.update_item(
                    Key={"conversation_id": conversation_id},
                    UpdateExpression="SET last_message_at = :now, "
                    "message_count = message_count + :one, "
                    "participant_ids = :participants",
                    ExpressionAttributeValues={
                        ":now": now,
                        ":one": 1,
                        ":participants": participant_ids,
                    },
                )

        except ClientError as e:
            print(f"⚠️ Failed to update metadata: {str(e)}")

    def format_messages_for_ai(
        self, conversation_id: str, limit: int = 50, include_sender_name: bool = True
    ) -> str:
        """格式化訊息給 AI 使用（群組上下文）"""
        result = self.get_messages(conversation_id, limit=limit)

        if not result["success"]:
            return ""

        messages = result["messages"]

        formatted_lines = []
        for msg in reversed(messages):
            sender_name = msg.get("sender_name", "Unknown")
            content = msg.get("content", "")

            if include_sender_name:
                formatted_lines.append(f"[{sender_name}] {content}")
            else:
                formatted_lines.append(content)

        return "\n".join(formatted_lines)
</content>
</replace_in_file>

<write_to_file>
<path>infrastructure/layers/conversation-layer/requirements.txt</path>
<content>boto3>=1.42.0
botocore>=1.42.0