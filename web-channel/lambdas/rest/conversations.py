"""
Conversations REST API Lambda
處理對話管理：列出、創建、更新、刪除對話
"""

import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
import uuid

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")

# Environment variables
CONVERSATIONS_TABLE = os.environ["CONVERSATIONS_TABLE"]
HISTORY_TABLE = os.environ["HISTORY_TABLE"]
BINDINGS_TABLE = os.environ["BINDINGS_TABLE"]

# DynamoDB tables
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)
history_table = dynamodb.Table(HISTORY_TABLE)
bindings_table = dynamodb.Table(BINDINGS_TABLE)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main handler for conversations operations
    
    Routes:
        GET /conversations - 列出對話
        POST /conversations - 創建新對話
        PUT /conversations/:id - 更新對話（標題、置頂）
        DELETE /conversations/:id - 刪除對話（軟刪除）
        GET /conversations/:id/messages - 獲取對話的消息
    """
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    
    print(f"{method} {path}")
    
    # 從 JWT 提取 email
    email = extract_email_from_token(event)
    if not email:
        return response(401, {"error": "Unauthorized"})
    
    try:
        if path == "/conversations" and method == "GET":
            return handle_list_conversations(email, event)
        
        elif path == "/conversations" and method == "POST":
            return handle_create_conversation(email, event)
        
        elif path.startswith("/conversations/") and method == "PUT":
            # Extract conversation_id from path
            conv_id = path.split("/")[-1]
            return handle_update_conversation(email, conv_id, event)
        
        elif path.startswith("/conversations/") and method == "DELETE":
            conv_id = path.split("/")[-1]
            return handle_delete_conversation(email, conv_id)
        
        elif path.endswith("/messages") and method == "GET":
            # /conversations/:id/messages
            parts = path.split("/")
            conv_id = parts[-2]
            return handle_get_messages(email, conv_id, event)
        
        else:
            return response(404, {"error": "Not found"})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return response(500, {"error": "Internal server error"})


# ============================================================
# Handler Functions
# ============================================================

def handle_list_conversations(email: str, event: dict[str, Any]) -> dict[str, Any]:
    """
    列出用戶的所有對話（分頁）
    
    Query Parameters:
        - limit: 每頁數量（默認 50）
        - last_key: 分頁鍵
        - include_deleted: 是否包含已刪除（默認 false）
    
    Returns:
        {
            "conversations": {
                "pinned": [...],
                "recent": [...]
            },
            "count": 10,
            "last_key": "..." (optional)
        }
    """
    unified_user_id = get_unified_user_id_by_email(email)
    if not unified_user_id:
        return response(200, {"conversations": {"pinned": [], "recent": []}, "count": 0})
    
    # 查詢參數
    query_params = event.get("queryStringParameters") or {}
    limit = int(query_params.get("limit", 50))
    last_key = query_params.get("last_key")
    include_deleted = query_params.get("include_deleted", "false").lower() == "true"
    
    try:
        # 查詢對話列表（使用 user-by-time-index 按時間排序）
        query_kwargs = {
            "IndexName": "user-by-time-index",
            "KeyConditionExpression": "unified_user_id = :user_id",
            "ExpressionAttributeValues": {":user_id": unified_user_id},
            "Limit": limit,
            "ScanIndexForward": False  # 最新在前
        }
        
        # 過濾已刪除對話
        if not include_deleted:
            query_kwargs["FilterExpression"] = "attribute_not_exists(is_deleted) OR is_deleted = :false"
            query_kwargs["ExpressionAttributeValues"][":false"] = False
        
        if last_key:
            query_kwargs["ExclusiveStartKey"] = json.loads(last_key)
        
        result = conversations_table.query(**query_kwargs)
        
        conversations = [convert_dynamodb_to_json(item) for item in result.get("Items", [])]
        
        # 分組：置頂 + 未置頂
        pinned = [c for c in conversations if c.get("is_pinned", False)]
        unpinned = [c for c in conversations if not c.get("is_pinned", False)]
        
        response_data = {
            "conversations": {
                "pinned": pinned,
                "recent": unpinned
            },
            "count": len(conversations)
        }
        
        # 分頁鍵
        if "LastEvaluatedKey" in result:
            response_data["last_key"] = json.dumps(result["LastEvaluatedKey"])
        
        return response(200, response_data)
        
    except ClientError as e:
        print(f"Error listing conversations: {str(e)}")
        return response(500, {"error": "Failed to list conversations"})


def handle_create_conversation(email: str, event: dict[str, Any]) -> dict[str, Any]:
    """
    創建新對話
    
    Request Body:
        {
            "title": "對話標題" (optional, default: "新對話")
        }
    
    Returns:
        {
            "conversation_id": "uuid",
            "title": "對話標題",
            "created_at": "2026-01-08T..."
        }
    """
    unified_user_id = get_unified_user_id_by_email(email)
    if not unified_user_id:
        return response(403, {"error": "User not found"})
    
    body = json.loads(event.get("body", "{}"))
    title = body.get("title", "新對話")
    
    conv_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    
    try:
        conversations_table.put_item(Item={
            "unified_user_id": unified_user_id,
            "conversation_id": conv_id,
            "title": title,
            "created_at": now,
            "last_message_time": now,
            "message_count": 0,
            "is_pinned": False,
            "is_deleted": False
        })
        
        print(f"Created conversation: {conv_id}")
        
        return response(200, {
            "conversation_id": conv_id,
            "title": title,
            "created_at": now,
            "message": "Conversation created successfully"
        })
        
    except ClientError as e:
        print(f"Error creating conversation: {str(e)}")
        return response(500, {"error": "Failed to create conversation"})


def handle_update_conversation(
    email: str, 
    conv_id: str, 
    event: dict[str, Any]
) -> dict[str, Any]:
    """
    更新對話（重命名、置頂）
    
    Request Body:
        {
            "title": "新標題" (optional),
            "is_pinned": true/false (optional)
        }
    """
    unified_user_id = get_unified_user_id_by_email(email)
    if not unified_user_id:
        return response(403, {"error": "Unauthorized"})
    
    body = json.loads(event.get("body", "{}"))
    
    # 構建更新表達式
    update_parts = []
    expr_values = {}
    
    if "title" in body:
        update_parts.append("title = :title")
        expr_values[":title"] = body["title"]
    
    if "is_pinned" in body:
        update_parts.append("is_pinned = :pinned")
        expr_values[":pinned"] = body["is_pinned"]
    
    if not update_parts:
        return response(400, {"error": "No updates provided"})
    
    try:
        conversations_table.update_item(
            Key={
                "unified_user_id": unified_user_id,
                "conversation_id": conv_id
            },
            UpdateExpression="SET " + ", ".join(update_parts),
            ExpressionAttributeValues=expr_values,
            ConditionExpression="attribute_exists(conversation_id)"  # 確保對話存在
        )
        
        print(f"Updated conversation: {conv_id}")
        return response(200, {"message": "Updated successfully"})
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(404, {"error": "Conversation not found"})
        print(f"Error updating conversation: {str(e)}")
        return response(500, {"error": "Failed to update conversation"})


def handle_delete_conversation(email: str, conv_id: str) -> dict[str, Any]:
    """
    刪除對話（軟刪除）
    
    標記為已刪除，但保留數據
    """
    unified_user_id = get_unified_user_id_by_email(email)
    if not unified_user_id:
        return response(403, {"error": "Unauthorized"})
    
    try:
        conversations_table.update_item(
            Key={
                "unified_user_id": unified_user_id,
                "conversation_id": conv_id
            },
            UpdateExpression="SET is_deleted = :true, deleted_at = :now",
            ExpressionAttributeValues={
                ":true": True,
                ":now": datetime.now(UTC).isoformat()
            },
            ConditionExpression="attribute_exists(conversation_id)"
        )
        
        print(f"Deleted conversation: {conv_id}")
        return response(200, {"message": "Deleted successfully"})
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(404, {"error": "Conversation not found"})
        print(f"Error deleting conversation: {str(e)}")
        return response(500, {"error": "Failed to delete conversation"})


def handle_get_messages(
    email: str, 
    conv_id: str, 
    event: dict[str, Any]
) -> dict[str, Any]:
    """
    獲取特定對話的所有消息
    
    Query Parameters:
        - limit: 每頁數量（默認 100）
        - last_key: 分頁鍵
    """
    unified_user_id = get_unified_user_id_by_email(email)
    if not unified_user_id:
        return response(403, {"error": "Unauthorized"})
    
    # 驗證對話所有權
    try:
        conv_result = conversations_table.get_item(
            Key={
                "unified_user_id": unified_user_id,
                "conversation_id": conv_id
            }
        )
        
        if "Item" not in conv_result:
            return response(404, {"error": "Conversation not found"})
        
    except Exception as e:
        print(f"Error verifying conversation: {str(e)}")
        return response(500, {"error": "Failed to verify conversation"})
    
    # 查詢參數
    query_params = event.get("queryStringParameters") or {}
    limit = int(query_params.get("limit", 100))
    last_key = query_params.get("last_key")
    
    try:
        # 查詢該對話的所有消息
        query_kwargs = {
            "KeyConditionExpression": "unified_user_id = :user_id",
            "FilterExpression": "conversation_id = :conv_id",
            "ExpressionAttributeValues": {
                ":user_id": unified_user_id,
                ":conv_id": conv_id
            },
            "Limit": limit,
            "ScanIndexForward": True  # 最舊在前（時間順序）
        }
        
        if last_key:
            query_kwargs["ExclusiveStartKey"] = json.loads(last_key)
        
        result = history_table.query(**query_kwargs)
        
        messages = [convert_dynamodb_to_json(item) for item in result.get("Items", [])]
        
        response_data = {
            "messages": messages,
            "count": len(messages)
        }
        
        if "LastEvaluatedKey" in result:
            response_data["last_key"] = json.dumps(result["LastEvaluatedKey"])
        
        return response(200, response_data)
        
    except Exception as e:
        print(f"Error getting messages: {str(e)}")
        return response(500, {"error": "Failed to get messages"})


# ============================================================
# Helper Functions
# ============================================================

def get_unified_user_id_by_email(email: str) -> str | None:
    """
    通過 email 獲取 unified_user_id
    """
    try:
        result = bindings_table.query(
            IndexName="web_email-index",
            KeyConditionExpression="web_email = :email",
            ExpressionAttributeValues={":email": email}
        )
        
        items = result.get("Items", [])
        if items:
            return items[0]["unified_user_id"]
        
        return None
        
    except Exception as e:
        print(f"Error getting unified_user_id: {str(e)}")
        return None


def convert_dynamodb_to_json(item: dict[str, Any]) -> dict[str, Any]:
    """
    Convert DynamoDB item with Decimal to JSON-safe format
    """
    def decimal_to_int(obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        elif isinstance(obj, dict):
            return {k: decimal_to_int(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [decimal_to_int(i) for i in obj]
        return obj
    
    return decimal_to_int(item)


def extract_email_from_token(event: dict[str, Any]) -> str | None:
    """
    從 JWT token 提取 email
    """
    authorizer = event.get("requestContext", {}).get("authorizer", {})
    return authorizer.get("email")


def response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """
    創建 API Gateway response
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }