"""
Conversation Storage Service
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
        """
        儲存訊息到對話歷史

        Args:
            conversation_id: 對話ID
            sender_id: 發送者ID（例如：tg:12345, ai）
            sender_name: 發送者顯示名稱
            content: 訊息內容
            message_type: 訊息類型（text/image/file）
            channel: 通道類型（telegram/web/discord）
            metadata: 額外資料（可選）

        Returns:
            儲存的訊息物件
        """
        # 生成訊息ID和時間戳
        message_id = str(uuid.uuid4())
        timestamp = int(time.time() * 1000)  # 毫秒級時間戳

        # 準備訊息項目
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

        # 添加 metadata（如果提供）
        if metadata:
            item["metadata"] = metadata

        try:
            # 寫入對話歷史表
            self.history_table.put_item(Item=item)

            # 更新對話元數據（訊息計數、最後訊息時間）
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
        """
        查詢對話訊息

        Args:
            conversation_id: 對話ID
            limit: 返回數量限制（預設50，最大500）
            start_time: 起始時間戳（可選，用於時間範圍查詢）
            last_evaluated_key: 分頁標記（可選）

        Returns:
            訊息列表和分頁資訊
        """
        # 限制最大查詢數量
        limit = min(limit, 500)

        try:
            # 檢查對話是否被刪除
            metadata = self._get_metadata(conversation_id)
            if metadata and metadata.get("deleted_at"):
                return {
                    "success": False,
                    "error": "Conversation has been deleted",
                    "messages": [],
                }

            # 準備查詢參數
            query_params = {
                "KeyConditionExpression": "conversation_id = :conv_id",
                "ExpressionAttributeValues": {":conv_id": conversation_id},
                "Limit": limit,
                "ScanIndexForward": False,  # 從最新往舊排序
            }

            # 時間範圍查詢（可選）
            if start_time:
                query_params["KeyConditionExpression"] += " AND #ts >= :start_time"
                query_params["ExpressionAttributeNames"] = {"#ts": "timestamp"}
                query_params["ExpressionAttributeValues"][":start_time"] = start_time

            # 分頁查詢（可選）
            if last_evaluated_key:
                query_params["ExclusiveStartKey"] = last_evaluated_key

            # 執行查詢
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

    def delete_conversation(
        self, conversation_id: str, hard_delete: bool = False
    ) -> dict[str, Any]:
        """
        刪除對話（預設軟刪除）

        Args:
            conversation_id: 對話ID
            hard_delete: 是否硬刪除（立即刪除所有訊息）

        Returns:
            刪除結果
        """
        try:
            if hard_delete:
                # 硬刪除：直接刪除所有訊息（慎用！）
                return self._hard_delete_conversation(conversation_id)
            else:
                # 軟刪除：設定 deleted_at（推薦）
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
        """
        軟刪除對話（設定 deleted_at，30天後自動清理）

        Args:
            conversation_id: 對話ID

        Returns:
            刪除結果
        """
        now = int(time.time())
        delete_time = now + (30 * 86400)  # 30天後

        # 更新 metadata（標記為已刪除）
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
        """
        硬刪除對話（立即刪除所有訊息）

        警告：此操作不可恢復！

        Args:
            conversation_id: 對話ID

        Returns:
            刪除結果
        """
        deleted_count = 0

        # 查詢所有訊息
        response = self.history_table.query(
            KeyConditionExpression="conversation_id = :conv_id",
            ExpressionAttributeValues={":conv_id": conversation_id},
            ProjectionExpression="conversation_id, #ts",
            ExpressionAttributeNames={"#ts": "timestamp"},
        )

        # 批次刪除
        with self.history_table.batch_writer() as batch:
            for item in response.get("Items", []):
                batch.delete_item(
                    Key={
                        "conversation_id": item["conversation_id"],
                        "timestamp": item["timestamp"],
                    }
                )
                deleted_count += 1

        # 刪除 metadata
        self.metadata_table.delete_item(Key={"conversation_id": conversation_id})

        return {
            "success": True,
            "deleted_count": deleted_count,
            "permanent": True,
        }

    def restore_conversation(self, conversation_id: str) -> dict[str, Any]:
        """
        恢復已刪除的對話（僅軟刪除可恢復）

        Args:
            conversation_id: 對話ID

        Returns:
            恢復結果
        """
        try:
            # 清除 deleted_at 和 delete_at
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
        """
        取得對話元數據

        Args:
            conversation_id: 對話ID

        Returns:
            元數據物件或 None
        """
        try:
            response = self.metadata_table.get_item(Key={"conversation_id": conversation_id})
            return response.get("Item")
        except ClientError as e:
            print(f"❌ Failed to get metadata: {str(e)}")
            return None

    def _get_metadata(self, conversation_id: str) -> dict[str, Any] | None:
        """內部使用：取得元數據（無錯誤處理）"""
        try:
            response = self.metadata_table.get_item(Key={"conversation_id": conversation_id})
            return response.get("Item")
        except:
            return None

    def _update_metadata(self, conversation_id: str, sender_id: str, channel: str) -> None:
        """
        更新對話元數據（訊息計數、最後訊息時間、參與者）

        Args:
            conversation_id: 對話ID
            sender_id: 發送者ID
            channel: 通道類型
        """
        now = int(time.time())
        is_group = "group" in conversation_id

        try:
            # 檢查是否為新對話
            existing = self._get_metadata(conversation_id)

            if not existing:
                # 新對話：創建 metadata
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
                # 更新現有對話
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
            # metadata 更新失敗不應該阻止訊息儲存
            print(f"⚠️ Failed to update metadata: {str(e)}")

    def get_participant_stats(self, conversation_id: str) -> dict[str, Any]:
        """
        取得對話參與者統計

        Args:
            conversation_id: 對話ID

        Returns:
            參與者統計資料
        """
        try:
            # 查詢所有訊息（只取 sender_id）
            response = self.history_table.query(
                KeyConditionExpression="conversation_id = :conv_id",
                ExpressionAttributeValues={":conv_id": conversation_id},
                ProjectionExpression="sender_id, sender_name",
            )

            messages = response.get("Items", [])

            # 統計每個發送者的訊息數
            stats = {}
            for msg in messages:
                sender_id = msg.get("sender_id", "unknown")
                sender_name = msg.get("sender_name", "Unknown")

                if sender_id not in stats:
                    stats[sender_id] = {
                        "sender_id": sender_id,
                        "sender_name": sender_name,
                        "message_count": 0,
                    }

                stats[sender_id]["message_count"] += 1

            # 轉換為列表並排序
            participant_list = list(stats.values())
            participant_list.sort(key=lambda x: x["message_count"], reverse=True)

            return {
                "success": True,
                "conversation_id": conversation_id,
                "total_messages": len(messages),
                "participants": participant_list,
                "participant_count": len(participant_list),
            }

        except ClientError as e:
            return {
                "success": False,
                "error": str(e),
            }

    def format_messages_for_ai(
        self, conversation_id: str, limit: int = 50, include_sender_name: bool = True
    ) -> str:
        """
        格式化訊息給 AI 使用（用於群組上下文）

        Args:
            conversation_id: 對話ID
            limit: 訊息數量限制
            include_sender_name: 是否包含發送者名稱（群組需要）

        Returns:
            格式化的對話文字
        """
        result = self.get_messages(conversation_id, limit=limit)

        if not result["success"]:
            return ""

        messages = result["messages"]

        # 格式化為文字（從舊到新排序）
        formatted_lines = []
        for msg in reversed(messages):  # 反轉為時間順序
            sender_name = msg.get("sender_name", "Unknown")
            content = msg.get("content", "")

            if include_sender_name:
                # 群組模式：[發送者] 內容
                formatted_lines.append(f"[{sender_name}] {content}")
            else:
                # 私人模式：直接內容
                formatted_lines.append(content)

        return "\n".join(formatted_lines)


# ============================================================
# 工廠函數（便於在 Lambda 中使用）
# ============================================================


def create_conversation_service(
    history_table_name: str | None = None, metadata_table_name: str | None = None
) -> ConversationService:
    """
    創建 ConversationService 實例

    Args:
        history_table_name: 對話歷史表名稱（可選，從環境變數讀取）
        metadata_table_name: 對話元數據表名稱（可選，從環境變數讀取）

    Returns:
        ConversationService 實例
    """
    import os

    history_table = history_table_name or os.environ.get(
        "CONVERSATION_HISTORY_TABLE", "agentcore-conversation-history-dev"
    )

    metadata_table = metadata_table_name or os.environ.get(
        "CONVERSATION_METADATA_TABLE", "agentcore-conversation-metadata-dev"
    )

    return ConversationService(history_table, metadata_table)
