# 對話管理系統完整實施指南

**版本**: 2.0  
**預計時間**: 20-21 小時（3 個工作日）  
**難度**: 🔴 高（涉及前後端架構改造）  
**狀態**: 實施中

---

## 📋 目錄

- [Part 1: 後端架構升級](#part-1-後端架構升級)
- [Part 2: 數據遷移](#part-2-數據遷移)
- [Part 3: 前端實現](#part-3-前端實現)
- [Part 4: 測試和部署](#part-4-測試和部署)
- [Part 5: 故障排除](#part-5-故障排除)

---

# Part 1: 後端架構升級

## 1.1 創建 Conversations DynamoDB 表

### 修改文件：`web-adapter/infrastructure/web-adapter-template.yaml`

在 `Resources:` 部分添加新表定義：

```yaml
  # ========================================
  # Conversations Table
  # ========================================
  ConversationsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub '${AWS::StackName}-conversations'
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: unified_user_id
          AttributeType: S
        - AttributeName: conversation_id
          AttributeType: S
        - AttributeName: last_message_time
          AttributeType: S
      KeySchema:
        - AttributeName: unified_user_id
          KeyType: HASH
        - AttributeName: conversation_id
          KeyType: RANGE
      GlobalSecondaryIndexes:
        # 按 conversation_id 查詢
        - IndexName: conversation_id-index
          KeySchema:
            - AttributeName: conversation_id
              KeyType: HASH
          Projection:
            ProjectionType: ALL
        # 按時間排序的對話列表
        - IndexName: user-by-time-index
          KeySchema:
            - AttributeName: unified_user_id
              KeyType: HASH
            - AttributeName: last_message_time
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
      StreamSpecification:
        StreamViewType: NEW_AND_OLD_IMAGES
      SSESpecification:
        SSEEnabled: true
      Tags:
        - Key: Project
          Value: AgentCoreNexus
        - Key: Component
          Value: WebChannel
```

### 在 Outputs 部分添加：

```yaml
  ConversationsTableName:
    Description: Conversations DynamoDB Table Name
    Value: !Ref ConversationsTable
    Export:
      Name: !Sub '${AWS::StackName}-ConversationsTable'
  
  ConversationsTableArn:
    Description: Conversations DynamoDB Table ARN
    Value: !GetAtt ConversationsTable.Arn
```

---

## 1.2 修改 WebSocket Lambda

### 文件：`web-adapter/lambdas/websocket/handler.py`

#### 添加導入和環境變數：

```python
import os
import json
import uuid
from datetime import UTC, datetime

import boto3
from botocore.exceptions import ClientError

# 初始化
dynamodb = boto3.resource("dynamodb")
eventbridge = boto3.client("events")

# 環境變數
CONNECTIONS_TABLE = os.environ["CONNECTIONS_TABLE"]
BINDINGS_TABLE = os.environ["BINDINGS_TABLE"]
CONVERSATIONS_TABLE = os.environ["CONVERSATIONS_TABLE"]  # 新增
EVENT_BUS_NAME = os.environ["EVENT_BUS_NAME"]

# Tables
connections_table = dynamodb.Table(CONNECTIONS_TABLE)
bindings_table = dynamodb.Table(BINDINGS_TABLE)
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)  # 新增
```

#### 修改 `handle_send_message` 函數：

```python
def handle_send_message(connection_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """
    處理發送消息請求，支持 conversation_id
    
    Args:
        connection_id: WebSocket connection ID
        body: Message body with 'message' and optional 'conversation_id'
    
    Returns:
        Response dict
    """
    message = body.get("message", "").strip()
    conversation_id = body.get("conversation_id")  # 新增：前端提供
    
    if not message:
        return {"statusCode": 400, "body": "Message required"}
    
    # 查詢連接信息
    try:
        conn_result = connections_table.get_item(Key={"connection_id": connection_id})
        
        if "Item" not in conn_result:
            return {"statusCode": 404, "body": "Connection not found"}
        
        connection = conn_result["Item"]
        unified_user_id = connection["unified_user_id"]
        email = connection["email"]
        
    except ClientError as e:
        print(f"Error querying connection: {str(e)}")
        return {"statusCode": 500, "body": "Failed to get connection info"}
    
    # 如果沒有提供 conversation_id，自動分配
    if not conversation_id:
        conversation_id = auto_assign_conversation_id(unified_user_id)
        print(f"Auto-assigned conversation_id: {conversation_id}")
    else:
        print(f"Using provided conversation_id: {conversation_id}")
    
    # 驗證 conversation 是否屬於此用戶
    if not verify_conversation_ownership(unified_user_id, conversation_id):
        return {"statusCode": 403, "body": "Conversation access denied"}
    
    # 構建 EventBridge event
    message_id = str(uuid.uuid4())
    timestamp = datetime.now(UTC).isoformat()
    
    event_detail = {
        "message_id": message_id,
        "conversation_id": conversation_id,  # 新增
        "timestamp": timestamp,
        "channel": {
            "type": "web",
            "channel_id": connection_id,
            "metadata": {}
        },
        "user": {
            "unified_user_id": unified_user_id,
            "identifier": email,
            "role": "user"
        },
        "content": {
            "text": message,
            "message_type": "text",
            "attachments": []
        },
        "context": {
            "conversation_id": conversation_id,
            "session_id": connection_id
        }
    }
    
    # 發送到 EventBridge
    try:
        eventbridge.put_events(
            Entries=[
                {
                    "Source": "agentcore.web-adapter",
                    "DetailType": "message.received",
                    "Detail": json.dumps(event_detail),
                    "EventBusName": EVENT_BUS_NAME,
                }
            ]
        )
        
        print(f"Message sent to EventBridge: {message_id}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "ok",
                "message_id": message_id,
                "conversation_id": conversation_id
            })
        }
        
    except Exception as e:
        print(f"Error sending to EventBridge: {str(e)}")
        return {"statusCode": 500, "body": "Failed to send message"}


def auto_assign_conversation_id(unified_user_id: str) -> str:
    """
    自動分配 conversation_id
    
    策略：
    1. 查詢用戶最近的對話（1 小時內）
    2. 如果有，延續該對話
    3. 否則創建新對話
    
    Args:
        unified_user_id: 用戶 ID
    
    Returns:
        conversation_id
    """
    try:
        # 查詢最近 1 小時的對話
        now = datetime.now(UTC)
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        
        result = conversations_table.query(
            IndexName="user-by-time-index",
            KeyConditionExpression="unified_user_id = :uid AND last_message_time >= :time",
            ExpressionAttributeValues={
                ":uid": unified_user_id,
                ":time": one_hour_ago
            },
            FilterExpression="attribute_not_exists(is_deleted) OR is_deleted = :false",
            ExpressionAttributeValues={
                ":uid": unified_user_id,
                ":time": one_hour_ago,
                ":false": False
            },
            Limit=1,
            ScanIndexForward=False  # 最新在前
        )
        
        items = result.get("Items", [])
        if items:
            # 延續最近的對話
            return items[0]["conversation_id"]
        
        # 創建新對話
        return create_new_conversation(unified_user_id)
        
    except Exception as e:
        print(f"Error auto-assigning conversation: {str(e)}")
        # 降級方案：創建新對話
        return create_new_conversation(unified_user_id)


def create_new_conversation(unified_user_id: str, title: str = "新對話") -> str:
    """
    創建新對話記錄
    
    Args:
        unified_user_id: 用戶 ID
        title: 對話標題
    
    Returns:
        新的 conversation_id
    """
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
        
        print(f"Created new conversation: {conv_id}")
        return conv_id
        
    except Exception as e:
        print(f"Error creating conversation: {str(e)}")
        # 降級方案：返回臨時 ID
        return f"temp_{uuid.uuid4()}"


def verify_conversation_ownership(unified_user_id: str, conversation_id: str) -> bool:
    """
    驗證對話是否屬於該用戶
    
    Args:
        unified_user_id: 用戶 ID
        conversation_id: 對話 ID
    
    Returns:
        True if owned by user
    """
    try:
        result = conversations_table.get_item(
            Key={
                "unified_user_id": unified_user_id,
                "conversation_id": conversation_id
            }
        )
        
        return "Item" in result
        
    except Exception as e:
        print(f"Error verifying ownership: {str(e)}")
        return True  # 降級方案：允許（避免阻塞用戶）
```

---

## 1.3 修改 Response Router Lambda

### 文件：`web-adapter/lambdas/router/response_router.py`

#### 添加環境變數：

```python
import os
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb")
apigateway = boto3.client("apigatewaymanagementapi")

HISTORY_TABLE = os.environ["HISTORY_TABLE"]
CONVERSATIONS_TABLE = os.environ["CONVERSATIONS_TABLE"]  # 新增
CONNECTIONS_TABLE = os.environ["CONNECTIONS_TABLE"]
WEBSOCKET_ENDPOINT = os.environ["WEBSOCKET_ENDPOINT"]

history_table = dynamodb.Table(HISTORY_TABLE)
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)  # 新增
connections_table = dynamodb.Table(CONNECTIONS_TABLE)
```

#### 修改保存歷史函數：

```python
def save_to_conversation_history(message_data: dict) -> bool:
    """
    保存消息到對話歷史，並更新 conversation 元數據
    
    Args:
        message_data: Message data from EventBridge
    
    Returns:
        True if successful
    """
    try:
        unified_user_id = message_data["user"]["unified_user_id"]
        message_id = message_data["message_id"]
        conversation_id = message_data.get("context", {}).get("conversation_id", "default")
        timestamp = message_data["timestamp"]
        
        # 保存消息
        history_table.put_item(
            Item={
                "unified_user_id": unified_user_id,
                "timestamp_msgid": f"{timestamp}#{message_id}",
                "conversation_id": conversation_id,  # 新增
                "role": "assistant",
                "content": message_data["content"],
                "channel": message_data["channel"]["type"],
                "metadata": message_data.get("metadata", {}),
                "ttl": calculate_ttl(90),
            }
        )
        
        print(f"Saved message to history: {message_id}")
        
        # 更新 conversation 元數據
        update_conversation_metadata(
            unified_user_id, 
            conversation_id,
            message_data["content"]["text"],
            timestamp
        )
        
        return True
        
    except Exception as e:
        print(f"Error saving to history: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def update_conversation_metadata(
    unified_user_id: str,
    conversation_id: str,
    last_message_preview: str,
    timestamp: str
) -> None:
    """
    更新對話元數據（最後消息時間、計數）
    
    Args:
        unified_user_id: 用戶 ID
        conversation_id: 對話 ID
        last_message_preview: 最後消息預覽
        timestamp: 時間戳
    """
    try:
        # 獲取現有對話
        result = conversations_table.get_item(
            Key={
                "unified_user_id": unified_user_id,
                "conversation_id": conversation_id
            }
        )
        
        if "Item" not in result:
            # 對話不存在，創建它
            # 這種情況應該很少發生（舊數據或錯誤）
            conversations_table.put_item(Item={
                "unified_user_id": unified_user_id,
                "conversation_id": conversation_id,
                "title": last_message_preview[:30],
                "created_at": timestamp,
                "last_message_time": timestamp,
                "message_count": 1,
                "is_pinned": False,
                "is_deleted": False
            })
            print(f"Created missing conversation: {conversation_id}")
            return
        
        # 更新現有對話
        conversation = result["Item"]
        current_count = conversation.get("message_count", 0)
        current_title = conversation.get("title", "")
        
        # 如果標題是默認的，更新它
        if not current_title or current_title == "新對話":
            new_title = last_message_preview[:30]
        else:
            new_title = current_title
        
        conversations_table.update_item(
            Key={
                "unified_user_id": unified_user_id,
                "conversation_id": conversation_id
            },
            UpdateExpression="SET last_message_time = :time, message_count = :count, title = :title",
            ExpressionAttributeValues={
                ":time": timestamp,
                ":count": current_count + 1,
                ":title": new_title
            }
        )
        
        print(f"Updated conversation metadata: {conversation_id}")
        
    except Exception as e:
        print(f"Error updating conversation metadata: {str(e)}")
        # 非關鍵錯誤，不中斷消息流
```

---

## 1.4 創建 Conversations API Lambda

### 新建文件：`web-adapter/lambdas/rest/conversations.py`

```python
"""
Conversations REST API Lambda
處理對話管理：列出、創建、更新、刪除對話
"""

import json
import os
from datetime import UTC, datetime, timedelta
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
        # 注意：需要在 history_table 上添加 GSI for conversation_id
        # 或者使用掃描（慢但簡單）
        
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
```

---

## 1.5 更新 CloudFormation Template

### 文件：`web-adapter/infrastructure/web-adapter-template.yaml`

#### 添加 Conversations Lambda 函數定義：

```yaml
  # ========================================
  # Conversations API Lambda
  # ========================================
  ConversationsFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub '${AWS::StackName}-conversations-api'
      CodeUri: ../lambdas/rest/
      Handler: conversations.handler
      Runtime: python3.12
      Timeout: 30
      MemorySize: 256
      Environment:
        Variables:
          CONVERSATIONS_TABLE: !Ref ConversationsTable
          HISTORY_TABLE: !Ref ConversationHistoryTable
          BINDINGS_TABLE: !Ref UserBindingsTable
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref ConversationsTable
        - DynamoDBReadPolicy:
            TableName: !Ref ConversationHistoryTable
        - DynamoDBReadPolicy:
            TableName: !Ref UserBindingsTable
      Events:
        ListConversations:
          Type: Api
          Properties:
            RestApiId: !Ref RestApi
            Path: /conversations
            Method: GET
            Auth:
              Authorizer: JWTAuthorizer
        CreateConversation:
          Type: Api
          Properties:
            RestApiId: !Ref RestApi
            Path: /conversations
            Method: POST
            Auth:
              Authorizer: JWTAuthorizer
        UpdateConversation:
          Type: Api
          Properties:
            RestApiId: !Ref RestApi
            Path: /conversations/{id}
            Method: PUT
            Auth:
              Authorizer: JWTAuthorizer
        DeleteConversation:
          Type: Api
          Properties:
            RestApiId: !Ref RestApi
            Path: /conversations/{id}
            Method: DELETE
            Auth:
              Authorizer: JWTAuthorizer
        GetMessages:
          Type: Api
          Properties:
            RestApiId: !Ref RestApi
            Path: /conversations/{id}/messages
            Method: GET
            Auth:
              Authorizer: JWTAuthorizer
```

#### 更新 WebSocket Lambda 環境變數：

找到 `WebSocketConnectFunction` 和其他 WebSocket functions，添加：

```yaml
      Environment:
        Variables:
          # ... 現有變數 ...
          CONVERSATIONS_TABLE: !Ref ConversationsTable  # 新增
```

#### 更新 Response Router Lambda 環境變數：

找到 `ResponseRouterFunction`，添加：

```yaml
      Environment:
        Variables:
          # ... 現有變數 ...
          CONVERSATIONS_TABLE: !Ref ConversationsTable  # 新增
```

---

## 1.6 部署後端

### 部署步驟

```bash
# Step 1: 進入 infrastructure 目錄
cd web-adapter/infrastructure

# Step 2: 驗證 template
sam validate -t web-adapter-template.yaml

# Step 3: 建構
sam build -t web-adapter-template.yaml

# Step 4: 部署
sam deploy \
  --template-file web-adapter-template.yaml \
  --stack-name agentcore-web-adapter \
  --region us-west-2 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset

# Step 5: 驗證部署
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].StackStatus'

# 應該看到：UPDATE_COMPLETE
```

### 驗證新資源

```bash
# 驗證 conversations 表已創建
aws dynamodb describe-table \
  --region us-west-2 \
  --table-name agentcore-web-adapter-conversations \
  --query 'Table.{Name:TableName,Status:TableStatus,ItemCount:ItemCount}'

# 驗證 Lambda 函數已更新
aws lambda list-functions --region us-west-2 \
  --query 'Functions[?contains(FunctionName,`agentcore-web-adapter`)].{Name:FunctionName,Runtime:Runtime,LastModified:LastModified}' \
  --output table

# 測試新 API
TOKEN="<your_jwt_token>"
REST_API=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`RestApiEndpoint`].OutputValue' \
  --output text)

curl -X GET "$REST_API/conversations" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'
```

---

# Part 2: 數據遷移

## 2.1 創建遷移腳本

### 新建文件：`web-adapter/scripts/migrate-conversations.py`

```python
"""
數據遷移腳本：為現有消息創建 conversation_id 和 conversations 記錄

執行前確認：
1. 後端已部署（conversations 表已創建）
2. 備份現有數據（可選但建議）

執行方式：
    python migrate-conversations.py --dry-run  # 預覽
    python migrate-conversations.py           # 實際執行
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

import boto3
from botocore.exceptions import ClientError

# 配置
REGION = "us-west-2"
HISTORY_TABLE = "conversation_history"
CONVERSATIONS_TABLE = "agentcore-web-adapter-conversations"
BINDINGS_TABLE = "user_bindings"

# 時間間隔閾值（超過此時間視為新對話）
CONVERSATION_GAP_HOURS = 1

# 初始化
dynamodb = boto3.resource("dynamodb", region_name=REGION)
history_table = dynamodb.Table(HISTORY_TABLE)
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)
bindings_table = dynamodb.Table(BINDINGS_TABLE)


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="遷移對話數據")
    parser.add_argument("--dry-run", action="store_true", help="只預覽，不實際執行")
    parser.add_argument("--user-id", help="只遷移特定用戶（測試用）")
    args = parser.parse_args()
    
    print("=" * 60)
    print("對話數據遷移腳本")
    print("=" * 60)
    print(f"模式: {'預覽模式' if args.dry_run else '執行模式'}")
    print(f"區域: {REGION}")
    print(f"對話間隔閾值: {CONVERSATION_GAP_HOURS} 小時")
    print("=" * 60)
    print()
    
    if not args.dry_run:
        confirm = input("⚠️  這將修改生產數據。確定繼續嗎？ (yes/no): ")
        if confirm.lower() != "yes":
            print("❌ 已取消")
            return
        print()
    
    # 獲取所有用戶
    if args.user_id:
        user_ids = [args.user_id]
    else:
        user_ids = get_all_user_ids()
    
    print(f"📊 找到 {len(user_ids)} 個用戶需要遷移")
    print()
    
    total_conversations = 0
    total_messages = 0
    errors = []
    
    for i, user_id in enumerate(user_ids, 1):
        print(f"[{i}/{len(user_ids)}] 處理用戶: {user_id[:8]}...")
        
        try:
            conv_count, msg_count = migrate_user_conversations(
                user_id, 
                dry_run=args.dry_run
            )
            total_conversations += conv_count
            total_messages += msg_count
            print(f"  ✅ 完成：{conv_count} 個對話，{msg_count} 條消息")
            
        except Exception as e:
            error_msg = f"用戶 {user_id[:8]}: {str(e)}"
            errors.append(error_msg)
            print(f"  ❌ 錯誤：{str(e)}")
        
        print()
    
    # 總結
    print("=" * 60)
    print("遷移總結")
    print("=" * 60)
    print(f"✅ 成功遷移用戶數: {len(user_ids) - len(errors)}")
    print(f"✅ 創建對話數: {total_conversations}")
    print(f"✅ 更新消息數: {total_messages}")
    
    if errors:
        print(f"❌ 失敗數: {len(errors)}")
        print("\n失敗詳情：")
        for error in errors:
            print(f"  - {error}")
    
    if args.dry_run:
        print("\n💡 這是預覽模式，未實際修改數據")
        print("   移除 --dry-run 參數來執行實際遷移")
    
    print("=" * 60)


def get_all_user_ids() -> List[str]:
    """
    獲取所有 unified_user_id
    """
    user_ids = set()
    
    try:
        # 掃描 bindings 表
        response = bindings_table.scan(
            ProjectionExpression="unified_user_id"
        )
        
        for item in response.get("Items", []):
            user_ids.add(item["unified_user_id"])
        
        # 處理分頁
        while "LastEvaluatedKey" in response:
            response = bindings_table.scan(
                ProjectionExpression="unified_user_id",
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            for item in response.get("Items", []):
                user_ids.add(item["unified_user_id"])
        
        return list(user_ids)
        
    except Exception as e:
        print(f"錯誤：無法獲取用戶列表 - {str(e)}")
        sys.exit(1)


def migrate_user_conversations(user_id: str, dry_run: bool = False) -> tuple[int, int]:
    """
    遷移單個用戶的消息到對話
    
    Args:
        user_id: unified_user_id
        dry_run: 是否只預覽
    
    Returns:
        (conversations_created, messages_updated)
    """
    # Step 1: 獲取所有消息
    messages = get_all_messages(user_id)
    
    if not messages:
        return 0, 0
    
    # Step 2: 按時間分組成對話
    conversations = group_messages_into_conversations(messages)
    
    print(f"  📋 發現 {len(conversations)} 個對話（共 {len(messages)} 條消息）")
    
    if dry_run:
        # 預覽模式：只打印統計
        for i, conv in enumerate(conversations, 1):
            first_msg = conv['messages'][0]
            print(f"    對話 {i}: {len(conv['messages'])} 條消息")
            print(f"      標題: {conv['title']}")
            print(f"      時間: {conv['first_time']} - {conv['last_time']}")
        return len(conversations), len(messages)
    
    # Step 3: 創建 conversations 記錄
    for conv in conversations:
        try:
            conversations_table.put_item(Item={
                "unified_user_id": user_id,
                "conversation_id": conv["id"],
                "title": conv["title"],
                "created_at": conv["first_time"],
                "last_message_time": conv["last_time"],
                "message_count": len(conv["messages"]),
                "is_pinned": False,
                "is_deleted": False
            })
        except Exception as e:
            print(f"    ⚠️  無法創建對話 {conv['id']}: {str(e)}")
    
    # Step 4: 更新消息的 conversation_id
    updated_count = 0
    for conv in conversations:
        for msg in conv["messages"]:
            try:
                history_table.update_item(
                    Key={
                        "unified_user_id": user_id,
                        "timestamp_msgid": msg["timestamp_msgid"]
                    },
                    UpdateExpression="SET conversation_id = :cid",
                    ExpressionAttributeValues={":cid": conv["id"]}
                )
                updated_count += 1
            except Exception as e:
                print(f"    ⚠️  無法更新消息: {str(e)}")
    
    return len(conversations), updated_count


def get_all_messages(user_id: str) -> List[Dict[str, Any]]:
    """
    獲取用戶的所有消息（按時間排序）
    """
    messages = []
    last_key = None
    
    try:
        while True:
            kwargs = {
                "KeyConditionExpression": "unified_user_id = :uid",
                "ExpressionAttributeValues": {":uid": user_id},
                "ScanIndexForward": True  # 最舊在前
            }
            
            if last_key:
                kwargs["ExclusiveStartKey"] = last_key
            
            result = history_table.query(**kwargs)
            messages.extend(result.get("Items", []))
            
            last_key = result.get("LastEvaluatedKey")
            if not last_key:
                break
        
        return messages
        
    except Exception as e:
        raise Exception(f"無法獲取消息：{str(e)}")


def group_messages_into_conversations(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    將消息按時間間隔分組成對話
    
    規則：相鄰消息時間差 > 1 小時 = 新對話
    """
    if not messages:
        return []
    
    conversations = []
    current_conv = None
    
    for msg in messages:
        # 提取時間戳
        timestamp_str = msg["timestamp_msgid"].split("#")[0]
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except Exception:
            continue
        
        # 檢查是否應該開始新對話
        should_start_new = False
        
        if not current_conv:
            should_start_new = True
        else:
            time_diff = (timestamp - current_conv["last_time"]).total_seconds()
            if time_diff > CONVERSATION_GAP_HOURS * 3600:
                should_start_new = True
        
        if should_start_new:
            # 開始新對話
            conv_id = str(uuid.uuid4())
            content_text = msg.get("content", {}).get("text", "無標題")
            title = content_text[:30]
            if len(content_text) > 30:
                title += "..."
            
            current_conv = {
                "id": conv_id,
                "title": title,
                "messages": [],
                "first_time": timestamp.isoformat(),
                "last_time": timestamp.isoformat()
            }
            conversations.append(current_conv)
        
        # 添加消息到當前對話
        current_conv["messages"].append(msg)
        current_conv["last_time"] = timestamp.isoformat()
    
    return conversations


if __name__ == "__main__":
    main()
```

---

## 2.2 創建驗證腳本

### 新建文件：`web-adapter/scripts/verify-migration.py`

```python
"""
驗證遷移結果
"""

import boto3

REGION = "us-west-2"
HISTORY_TABLE = "conversation_history"
CONVERSATIONS_TABLE = "agentcore-web-adapter-conversations"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
history_table = dynamodb.Table(HISTORY_TABLE)
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)


def verify_migration():
    """驗證遷移結果"""
    print("🔍 驗證遷移結果...")
    print()
    
    # 1. 統計 conversations 表
    conv_result = conversations_table.scan(Select="COUNT")
    conv_count = conv_result["Count"]
    print(f"✅ Conversations 表：{conv_count} 個對話")
    
    # 2. 檢查消息是否都有 conversation_id
    sample = history_table.scan(Limit=100)
    messages_with_conv_id = sum(
        1 for item in sample["Items"] 
        if "conversation_id" in item
    )
    print(f"✅ 消息樣本：{messages_with_conv_id}/100 有 conversation_id")
    
    # 3. 驗證對話元數據的準確性
    sample_convs = conversations_table.scan(Limit=10)
    print(f"\n📋 樣本對話：")
    for conv in sample_convs["Items"][:5]:
        print(f"  - {conv.get('title', '無標題')}")
        print(f"    消息數: {conv.get('message_count', 0)}")
        print(f"    最後活動: {conv.get('last_message_time', 'N/A')}")
    
    print("\n✅ 驗證完成")


if __name__ == "__main__":
    verify_migration()
```

---

## 2.3 執行遷移

### 步驟

```bash
# Step 1: 安裝依賴（如果需要）
pip install boto3

# Step 2: 配置 AWS 認證
aws configure

# Step 3: 預覽遷移（建議先執行）
cd web-adapter/scripts
python migrate-conversations.py --dry-run

# 檢查輸出，確認分組合理

# Step 4: 執行實際遷移
python migrate-conversations.py

# 會提示確認，輸入 "yes" 繼續

# Step 5: 驗證結果
python verify-migration.py

# Step 6: 手動檢查幾個用戶的數據
```

### 遷移時間估算

| 消息數 | 預計時間 |
|--------|----------|
| < 1,000 | < 1 分鐘 |
| 1,000 - 10,000 | 5-10 分鐘 |
| 10,000 - 100,000 | 30-60 分鐘 |
| > 100,000 | 1-2 小時 |

---

# Part 3: 前端實現

## 3.1 擴展 chatStore

### 文件：`web-adapter/frontend/src/stores/chatStore.ts`

**完整替換為以下內容**：

```typescript
/**
 * Chat state store with conversation management
 */

import { create } from 'zustand'
import { websocket, Message } from '@/services/websocket'
import { api } from '@/services/api'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  channel?: string
}

export interface Conversation {
  id: string
  title: string
  messages: ChatMessage[]
  lastMessageTime: string
  messageCount: number
  isPinned: boolean
  createdAt: string
}

interface ChatState {
  // Conversations
  conversations: Conversation[]
  currentConversationId: string | null
  isLoadingConversations: boolean
  searchQuery: string
  
  // Connection
  isConnected: boolean
  isSending: boolean
  error: string | null
  
  // Actions - Conversations
  loadConversations: () => Promise<void>
  createNewConversation: (title?: string) => Promise<string>
  switchConversation: (id: string) => void
  deleteConversation: (id: string) => Promise<void>
  renameConversation: (id: string, title: string) => Promise<void>
  togglePinConversation: (id: string) => Promise<void>
  setSearchQuery: (query: string) => void
  getFilteredConversations: () => { pinned: Conversation[], recent: Conversation[] }
  
  // Actions - Messages
  sendMessage: (content: string) => Promise<void>
  addMessage: (message: ChatMessage) => void
  getCurrentMessages: () => ChatMessage[]
  
  // Actions - Connection
  setConnected: (connected: boolean) => void
  clearError: () => void
  
  // Initialize
  initialize: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  // Initial state
  conversations: [],
  currentConversationId: null,
  isLoadingConversations: false,
  searchQuery: '',
  isConnected: false,
  isSending: false,
  error: null,
  
  // ============================================================
  // Conversation Management
  // ============================================================
  
  loadConversations: async () => {
    set({ isLoadingConversations: true })
    
    try {
      const response = await api.getConversations()
      const { pinned = [], recent = [] } = response.conversations || {}
      
      const allConversations: Conversation[] = [
        ...pinned.map((c: any) => ({
          id: c.conversation_id,
          title: c.title,
          messages: [],  // 暫時為空，切換時再載入
          lastMessageTime: c.last_message_time,
          messageCount: c.message_count,
          isPinned: c.is_pinned,
          createdAt: c.created_at
        })),
        ...recent.map((c: any) => ({
          id: c.conversation_id,
          title: c.title,
          messages: [],
          lastMessageTime: c.last_message_time,
          messageCount: c.message_count,
          isPinned: c.is_pinned,
          createdAt: c.created_at
        }))
      ]
      
      set({ 
        conversations: allConversations,
        isLoadingConversations: false
      })
      
      // 如果沒有當前對話，選擇最新的
      if (!get().currentConversationId && allConversations.length > 0) {
        get().switchConversation(allConversations[0].id)
      }
      
    } catch (error: any) {
      console.error('Failed to load conversations:', error)
      set({ 
        error: '無法載入對話列表',
        isLoadingConversations: false
      })
    }
  },
  
  createNewConversation: async (title = '新對話') => {
    try {
      const response = await api.createConversation(title)
      const newConv: Conversation = {
        id: response.conversation_id,
        title: response.title,
        messages: [],
        lastMessageTime: response.created_at,
        messageCount: 0,
        isPinned: false,
        createdAt: response.created_at
      }
      
      set(state => ({
        conversations: [newConv, ...state.conversations],
        currentConversationId: newConv.id
      }))
      
      return newConv.id
      
    } catch (error: any) {
      console.error('Failed to create conversation:', error)
      set({ error: '無法創建新對話' })
      throw error
    }
  },
  
  switchConversation: async (id: string) => {
    const state = get()
    const conversation = state.conversations.find(c => c.id === id)
    
    if (!conversation) {
      console.error('Conversation not found:', id)
      return
    }
    
    // 如果該對話的消息還沒載入，從 API 載入
    if (conversation.messages.length === 0 && conversation.messageCount > 0) {
      try {
        const response = await api.getConversationMessages(id)
        const messages: ChatMessage[] = response.messages.map((m: any) => ({
          id: m.timestamp_msgid.split('#')[1],
          role: m.role,
          content: m.content.text,
          timestamp: m.timestamp_msgid.split('#')[0],
          channel: m.channel
        }))
        
        // 更新該對話的消息
        set(state => ({
          conversations: state.conversations.map(c =>
            c.id === id ? { ...c, messages } : c
          ),
          currentConversationId: id
        }))
        
      } catch (error: any) {
        console.error('Failed to load messages:', error)
        set({ error: '無法載入對話消息' })
      }
    } else {
      // 消息已載入，直接切換
      set({ currentConversationId: id })
    }
  },
  
  deleteConversation: async (id: string) => {
    try {
      await api.deleteConversation(id)
      
      const state = get()
      const newConversations = state.conversations.filter(c => c.id !== id)
      
      // 如果刪除的是當前對話，切換到最新對話
      let newCurrentId = state.currentConversationId
      if (state.currentConversationId === id) {
        newCurrentId = newConversations.length > 0 ? newConversations[0].id : null
      }
      
      set({
        conversations: newConversations,
        currentConversationId: newCurrentId
      })
      
    } catch (error: any) {
      console.error('Failed to delete conversation:', error)
      set({ error: '無法刪除對話' })
      throw error
    }
  },
  
  renameConversation: async (id: string, title: string) => {
    try {
      await api.updateConversation(id, { title })
      
      set(state => ({
        conversations: state.conversations.map(c =>
          c.id === id ? { ...c, title } : c
        )
      }))
      
    } catch (error: any) {
      console.error('Failed to rename conversation:', error)
      set({ error: '無法重命名對話' })
      throw error
    }
  },
  
  togglePinConversation: async (id: string) => {
    const conversation = get().conversations.find(c => c.id === id)
    if (!conversation) return
    
    const newPinned = !conversation.isPinned
    
    try {
      await api.updateConversation(id, { is_pinned: newPinned })
      
      set(state => ({
        conversations: state.conversations.map(c =>
          c.id === id ? { ...c, isPinned: newPinned } : c
        )
      }))
      
    } catch (error: any) {
      console.error('Failed to toggle pin:', error)
      set({ error: '無法置頂對話' })
      throw error
    }
  },
  
  setSearchQuery: (query: string) => {
    set({ searchQuery: query })
  },
  
  getFilteredConversations: () => {
    const { conversations, searchQuery } = get()
    
    // 搜索過濾
    let filtered = conversations
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = conversations.filter(c =>
        c.title.toLowerCase().includes(query) ||
        c.messages.some(m => m.content.toLowerCase().includes(query))
      )
    }
    
    // 分組：置頂 + 未置頂
    const pinned = filtered.filter(c => c.isPinned)
    const recent = filtered.filter(c => !c.isPinned)
    
    return { pinned, recent }
  },
  
  // ============================================================
  // Message Management
  // ============================================================
  
  sendMessage: async (content: string) => {
    if (!websocket.isConnected()) {
      set({ error: '未連接到伺服器' })
      return
    }
    
    const currentConvId = get().currentConversationId
    if (!currentConvId) {
      set({ error: '請先選擇或創建對話' })
      return
    }
    
    set({ isSending: true, error: null })
    
    try {
      // 添加用戶消息（樂觀更新）
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
        channel: 'web'
      }
      
      get().addMessage(userMessage)
      
      // 發送到服務器（包含 conversation_id）
      websocket.sendMessage(content, currentConvId)
      
      set({ isSending: false })
      
    } catch (error: any) {
      set({
        error: error.message || '發送失敗',
        isSending: false
      })
    }
  },
  
  addMessage: (message: ChatMessage) => {
    const state = get()
    const currentConvId = state.currentConversationId
    
    if (!currentConvId) return
    
    // 添加消息到當前對話
    set(state => ({
      conversations: state.conversations.map(c =>
        c.id === currentConvId
          ? { 
              ...c, 
              messages: [...c.messages, message],
              lastMessageTime: message.timestamp,
              messageCount: c.messageCount + 1
            }
          : c
      )
    }))
  },
  
  getCurrentMessages: () => {
    const state = get()
    const currentConv = state.conversations.find(
      c => c.id === state.currentConversationId
    )
    return currentConv?.messages || []
  },
  
  // ============================================================
  // Connection Management
  // ============================================================
  
  setConnected: (connected: boolean) => {
    set({ isConnected: connected })
  },
  
  clearError: () => {
    set({ error: null })
  },
  
  // ============================================================
  // Initialize
  // ============================================================
  
  initialize: () => {
    // 訂閱 WebSocket 消息
    const unsubscribeMessage = websocket.onMessage((message: Message) => {
      if (message.type === 'message') {
        const chatMessage: ChatMessage = {
          id: Date.now().toString(),
          role: 'assistant',
          content: message.content,
          timestamp: message.timestamp,
          channel: 'web'
        }
        get().addMessage(chatMessage)
      }
    })
    
    // 訂閱連接變化
    const unsubscribeConnection = websocket.onConnectionChange((connected: boolean) => {
      get().setConnected(connected)
    })
    
    // 設置初始連接狀態
    set({ isConnected: websocket.isConnected() })
    
    // 載入對話列表
    get().loadConversations()
    
    // 清理函數
    return () => {
      unsubscribeMessage()
      unsubscribeConnection()
    }
  }
}))
```

---

## 3.2 擴展 API Service

### 文件：`web-adapter/frontend/src/services/api.ts`

添加新的 API 方法：

```typescript
// 在 ApiClient 類中添加以下方法

// ============================================================
// Conversations API
// ============================================================

async getConversations(params?: {
  limit?: number
  last_key?: string
  include_deleted?: boolean
}): Promise<{
  conversations: {
    pinned: any[]
    recent: any[]
  }
  count: number
  last_key?: string
}> {
  const queryParams = new URLSearchParams()
  if (params?.limit) queryParams.set('limit', params.limit.toString())
  if (params?.last_key) queryParams.set('last_key', params.last_key)
  if (params?.include_deleted) queryParams.set('include_deleted', 'true')
  
  const query = queryParams.toString()
  return this.request(`/conversations${query ? '?' + query : ''}`)
}

async createConversation(title: string = '新對話'): Promise<{
  conversation_id: string
  title: string
  created_at: string
  message: string
}> {
  return this.request('/conversations', {
    method: 'POST',
    body: JSON.stringify({ title })
  })
}

async updateConversation(
  conversationId: string,
  updates: {
    title?: string
    is_pinned?: boolean
  }
): Promise<{ message: string }> {
  return this.request(`/conversations/${conversationId}`, {
    method: 'PUT',
    body: JSON.stringify(updates)
  })
}

async deleteConversation(conversationId: string): Promise<{ message: string }> {
  return this.request(`/conversations/${conversationId}`, {
    method: 'DELETE'
  })
}

async getConversationMessages(
  conversationId: string,
  params?: {
    limit?: number
    last_key?: string
  }
): Promise<{
  messages: any[]
  count: number
  last_key?: string
}> {
  const queryParams = new URLSearchParams()
  if (params?.limit) queryParams.set('limit', params.limit.toString())
  if (params?.last_key) queryParams.set('last_key', params.last_key)
  
  const query = queryParams.toString()
  return this.request(`/conversations/${conversationId}/messages${query ? '?' + query : ''}`)
}
```

---

## 3.3 更新 WebSocket Service

### 文件：`web-adapter/frontend/src/services/websocket.ts`

修改 `sendMessage` 方法以支持 conversation_id：

```typescript
sendMessage(message: string, conversationId?: string): void {
  if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
    throw new Error('WebSocket not connected')
  }
  
  const payload = {
    action: 'sendMessage',
    message,
    conversation_id: conversationId  // 新增
  }
  
  console.log('Sending message:', payload)
  this.ws.send(JSON.stringify(payload))
}
```

---

## 3.4 創建 ConversationList 組件

### 新建文件：`web-adapter/frontend/src/components/Chat/ConversationList.tsx`

```typescript
import { useState } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { Search, Plus } from 'lucide-react'
import ConversationItem from './ConversationItem'
import ConversationContextMenu from './ConversationContextMenu'
import RenameConversationDialog from './RenameConversationDialog'
import DeleteConfirmDialog from './DeleteConfirmDialog'

interface ContextMenuState {
  conversationId: string | null
  x: number
  y: number
}

export default function ConversationList() {
  const {
    isLoadingConversations,
    searchQuery,
    setSearchQuery,
    getFilteredConversations,
    createNewConversation,
    currentConversationId,
    switchConversation
  } = useChatStore()
  
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    conversationId: null,
    x: 0,
    y: 0
  })
  const [renameDialog, setRenameDialog] = useState<string | null>(null)
  const [deleteDialog, setDeleteDialog] = useState<string | null>(null)
  
  const { pinned, recent } = getFilteredConversations()
  
  const handleContextMenu = (e: React.MouseEvent, conversationId: string) => {
    e.preventDefault()
    setContextMenu({
      conversationId,
      x: e.clientX,
      y: e.clientY
    })
  }
  
  const closeContextMenu = () => {
    setContextMenu({ conversationId: null, x: 0, y: 0 })
  }
  
  const handleNewConversation = async () => {
    try {
      await createNewConversation()
    } catch (error) {
      console.error('Failed to create conversation:', error)
    }
  }
  
  if (isLoadingConversations) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-dark-text-secondary">載入中...</div>
      </div>
    )
  }
  
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 搜索框 */}
      <div className="p-3 border-b border-dark-border">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-text-secondary" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索對話..."
            className="w-full pl-10 pr-4 py-2 rounded-lg input-field text-sm"
          />
        </div>
      </div>
      
      {/* 新對話按鈕 */}
      <div className="p-2 border-b border-dark-border">
        <button
          onClick={handleNewConversation}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-dark-surface-hover transition-colors text-sm"
        >
          <Plus className="w-4 h-4" />
          <span>新對話</span>
        </button>
      </div>
      
      {/* 對話列表 */}
      <div className="flex-1 overflow-y-auto">
        {/* 置頂對話 */}
        {pinned.length > 0 && (
          <div className="p-2">
            <div className="text-xs text-dark-text-secondary px-3 py-1 mb-1">
              📌 置頂
            </div>
            {pinned.map(conv => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                isActive={conv.id === currentConversationId}
                onClick={() => switchConversation(conv.id)}
                onContextMenu={(e) => handleContextMenu(e, conv.id)}
              />
            ))}
          </div>
        )}
        
        {/* 最近對話 */}
        {recent.length > 0 && (
          <div className="p-2">
            {pinned.length > 0 && (
              <div className="text-xs text-dark-text-secondary px-3 py-1 mb-1 border-t border-dark-border pt-2">
                最近對話
              </div>
            )}
            {recent.map(conv => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                isActive={conv.id === currentConversationId}
                onClick={() => switchConversation(conv.id)}
                onContextMenu={(e) => handleContextMenu(e, conv.id)}
              />
            ))}
          </div>
        )}
        
        {/* 空狀態 */}
        {pinned.length === 0 && recent.length === 0 && !searchQuery && (
          <div className="flex-1 flex items-center justify-center p-6">
            <div className="text-center text-dark-text-secondary text-sm">
              <p>還沒有對話</p>
              <p className="mt-2">點擊上方「新對話」開始</p>
            </div>
          </div>
        )}
        
        {/* 搜索無結果 */}
        {pinned.length === 0 && recent.length === 0 && searchQuery && (
          <div className="flex-1 flex items-center justify-center p-6">
            <div className="text-center text-dark-text-secondary text-sm">
              <p>沒有找到匹配的對話</p>
              <p className="mt-2">「{searchQuery}」</p>
            </div>
          </div>
        )}
      </div>
      
      {/* 右鍵菜單 */}
      {contextMenu.conversationId && (
        <ConversationContextMenu
          conversationId={contextMenu.conversationId}
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={closeContextMenu}
          onRename={(id) => {
            setRenameDialog(id)
            closeContextMenu()
          }}
          onDelete={(id) => {
            setDeleteDialog(id)
            closeContextMenu()
          }}
        />
      )}
      
      {/* 重命名對話框 */}
      {renameDialog && (
        <RenameConversationDialog
          conversationId={renameDialog}
          onClose={() => setRenameDialog(null)}
        />
      )}
      
      {/* 刪除確認對話框 */}
      {deleteDialog && (
        <DeleteConfirmDialog
          conversationId={deleteDialog}
          onClose={() => setDeleteDialog(null)}
        />
      )}
    </div>
  )
}
```

---

## 3.5 創建 ConversationItem 組件

### 新建文件：`web-adapter/frontend/src/components/Chat/ConversationItem.tsx`

```typescript
import { Conversation } from '@/stores/chatStore'
import { Pin } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { zhTW } from 'date-fns/locale'

interface ConversationItemProps {
  conversation: Conversation
  isActive: boolean
  onClick: () => void
  onContextMenu: (e: React.MouseEvent) => void
}

export default function ConversationItem({
  conversation,
  isActive,
  onClick,
  onContextMenu
}: ConversationItemProps) {
  // 格式化時間
  const timeAgo = formatDistanceToNow(
    new Date(conversation.lastMessageTime),
    { addSuffix: true, locale: zhTW }
  )
  
  // 獲取最後消息預覽
  const lastMessage = conversation.messages[conversation.messages.length - 1]
  const preview = lastMessage?.content.slice(0, 50) || '開始對話...'
  
  return (
    <button
      onClick={onClick}
      onContextMenu={onContextMenu}
      className={`
        w-full text-left px-3 py-3 rounded-lg transition-colors mb-1
        ${isActive 
          ? 'bg-dark-surface-hover border border-primary' 
          : 'hover:bg-dark-bg border border-transparent'
        }
      `}
    >
      <div className="flex items-start gap-2 mb-1">
        {/* 置頂圖標 */}
        {conversation.isPinned && (
          <Pin className="w-3 h-3 text-primary flex-shrink-0 mt-1" />
        )}
        
        {/* 標題 */}
        <h3 className="flex-1 text-sm font-medium truncate">
          {conversation.title}
        </h3>
        
        {/* 消息數量 */}
        {conversation.messageCount > 0 && (
          <span className="text-xs text-dark-text-secondary">
            {conversation.messageCount}
          </span>
        )}
      </div>
      
      {/* 預覽和時間 */}
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-dark-text-secondary truncate flex-1">
          {preview}
        </p>
        <span className="text-xs text-dark-text-secondary whitespace-nowrap">
          {timeAgo}
        </span>
      </div>
    </button>
  )
}
```

**Note**: 需要安裝 `date-fns`:
```bash
cd web-adapter/frontend
npm install date-fns
```

---

## 3.6 創建 ConversationContextMenu 組件

### 新建文件：`web-adapter/frontend/src/components/Chat/ConversationContextMenu.tsx`

```typescript
import { useEffect, useRef } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { Edit2, Pin, PinOff, Trash2, Download } from 'lucide-react'

interface ConversationContextMenuProps {
  conversationId: string
  x: number
  y: number
  onClose: () => void
  onRename: (id: string) => void
  onDelete: (id: string) => void
}

export default function ConversationContextMenu({
  conversationId,
  x,
  y,
  onClose,
  onRename,
  onDelete
}: ConversationContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null)
  const { conversations, togglePinConversation } = useChatStore()
  
  const conversation = conversations.find(c => c.id === conversationId)
  if (!conversation) return null
  
  const isPinned = conversation.isPinned
  
  // 點擊外部關閉
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [onClose])
  
  const handlePin = async () => {
    try {
      await togglePinConversation(conversationId)
      onClose()
    } catch (error) {
      console.error('Failed to toggle pin:', error)
    }
  }
  
  return (
    <div
      ref={menuRef}
      className="fixed bg-dark-surface border border-dark-border rounded-lg shadow-xl py-1 min-w-[180px] z-50"
      style={{
        top: `${y}px`,
        left: `${x}px`
      }}
    >
      {/* 重命名 */}
      <button
        onClick={() => onRename(conversationId)}
        className="w-full px-4 py-2 text-left text-sm hover:bg-dark-surface-hover transition-colors flex items-center gap-3"
      >
        <Edit2 className="w-4 h-4" />
        <span>重命名對話</span>
      </button>
      
      {/* 置頂/取消置頂 */}
      <button
        onClick={handlePin}
        className="w-full px-4 py-2 text-left text-sm hover:bg-dark-surface-hover transition-colors flex items-center gap-3"
      >
        {isPinned ? (
          <>
            <PinOff className="w-4 h-4" />
            <span>取消置頂</span>
          </>
        ) : (
          <>
            <Pin className="w-4 h-4" />
            <span>置頂對話</span>
          </>
        )}
      </button>
      
      {/* 分隔線 */}
      <div className="my-1 border-t border-dark-border" />
      
      {/* 導出 */}
      <button
        onClick={() => {
          // TODO: 實現導出功能
          console.log('Export conversation:', conversationId)
          onClose()
        }}
        className="w-full px-4 py-2 text-left text-sm hover:bg-dark-surface-hover transition-colors flex items-center gap-3"
      >
        <Download className="w-4 h-4" />
        <span>導出對話</span>
      </button>
      
      {/* 刪除 */}
      <button
        onClick={() => onDelete(conversationId)}
        className="w-full px-4 py-2 text-left text-sm hover:bg-dark-surface-hover transition-colors flex items-center gap-3 text-error"
      >
        <Trash2 className="w-4 h-4" />
        <span>刪除對話</span>
      </button>
    </div>
  )
}
```

---

## 3.7 創建 RenameConversationDialog 組件

### 新建文件：`web-adapter/frontend/src/components/Chat/RenameConversationDialog.tsx`

```typescript
import { useState, useEffect, useRef } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { Edit2, X, Loader2 } from 'lucide-react'

interface RenameConversationDialogProps {
  conversationId: string
  onClose: () => void
}

export default function RenameConversationDialog({
  conversationId,
  onClose
}: RenameConversationDialogProps) {
  const { conversations, renameConversation } = useChatStore()
  const conversation = conversations.find(c => c.id === conversationId)
  
  const [title, setTitle] = useState(conversation?.title || '')
  const [isRenaming, setIsRenaming] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  
  useEffect(() => {
    // 自動選中輸入框
    inputRef.current?.select()
    
    // ESC 鍵關閉
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isRenaming) {
        onClose()
      }
    }
    
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onClose, isRenaming])
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const newTitle = title.trim()
    if (!newTitle) {
      setError('標題不能為空')
      return
    }
    
    if (newTitle === conversation?.title) {
      onClose()
      return
    }
    
    setIsRenaming(true)
    setError('')
    
    try {
      await renameConversation(conversationId, newTitle)
      onClose()
    } catch (error: any) {
      setError(error.message || '重命名失敗')
      setIsRenaming(false)
    }
  }
  
  if (!conversation) return null
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-surface rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="p-6 border-b border-dark-border flex items-center justify-between">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Edit2 className="w-5 h-5" />
            重命名對話
          </h2>
          <button
            onClick={onClose}
            disabled={isRenaming}
            className="p-1 hover:bg-dark-surface-hover rounded transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6">
          <div className="mb-4">
            <label htmlFor="title" className="block text-sm font-medium mb-2">
              對話標題
            </label>
            <input
              ref={inputRef}
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isRenaming}
              className="w-full px-4 py-2 rounded-lg input-field"
              maxLength={50}
              autoComplete="off"
            />
            <p className="text-xs text-dark-text-secondary mt-1">
              {title.length}/50
            </p>
          </div>
          
          {/* 錯誤訊息 */}
          {error && (
            <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-lg text-error text-sm">
              {error}
            </div>
          )}
          
          {/* 按鈕 */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isRenaming}
              className="btn-secondary"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={isRenaming || !title.trim()}
              className="btn-primary flex items-center gap-2"
            >
              {isRenaming ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  重命名中...
                </>
              ) : (
                '確定'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
```

---

## 3.8 創建 DeleteConfirmDialog 組件

### 新建文件：`web-adapter/frontend/src/components/Chat/DeleteConfirmDialog.tsx`

```typescript
import { useState } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { Trash2, X, Loader2, AlertCircle } from 'lucide-react'

interface DeleteConfirmDialogProps {
  conversationId: string
  onClose: () => void
}

export default function DeleteConfirmDialog({
  conversationId,
  onClose
}: DeleteConfirmDialogProps) {
  const { conversations, deleteConversation } = useChatStore()
  const conversation = conversations.find(c => c.id === conversationId)
  
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState('')
  
  const handleDelete = async () => {
    setIsDeleting(true)
    setError('')
    
    try {
      await deleteConversation(conversationId)
      onClose()
    } catch (error: any) {
      setError(error.message || '刪除失敗')
      setIsDeleting(false)
    }
  }
  
  if (!conversation) return null
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-surface rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="p-6 border-b border-dark-border flex items-center justify-between">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Trash2 className="w-5 h-5 text-error" />
            刪除對話
          </h2>
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="p-1 hover:bg-dark-surface-hover rounded transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6">
          <div className="flex items-start gap-3 mb-4">
            <AlertCircle className="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-dark-text mb-2">
                確定要刪除這個對話嗎？
              </p>
              <p className="text-sm text-dark-text-secondary">
                對話標題：<strong>{conversation.title}</strong>
              </p>
              <p className="text-sm text-dark-text-secondary">
                包含 <strong>{conversation.messageCount}</strong> 條消息
              </p>
              <p className="text-sm text-error mt-2">
                ⚠️ 刪除後無法恢復
              </p>
            </div>
          </div>
          
          {/* 錯誤訊息 */}
          {error && (
            <div className="p-3 bg-error/10 border border-error/20 rounded-lg text-error text-sm">
              {error}
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="p-6 border-t border-dark-border flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="btn-secondary"
          >
            取消
          </button>
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="bg-error hover:bg-error/90 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                刪除中...
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                刪除
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
```

---

## 3.9 修改 Sidebar

### 文件：`web-adapter/frontend/src/components/Chat/Sidebar.tsx`

**完整替換為以下內容**：

```typescript
import { useAuthStore } from '@/stores/authStore'
import { LogOut, X, User, Shield } from 'lucide-react'
import ConversationList from './ConversationList'

interface SidebarProps {
  onClose: () => void
}

export default function Sidebar({ onClose }: SidebarProps) {
  const { user, logout } = useAuthStore()
  const isAdmin = user?.role === 'admin'
  
  return (
    <div className="h-full bg-dark-surface border-r border-dark-border flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-dark-border flex items-center justify-between">
        <h2 className="font-semibold text-lg">AgentCore</h2>
        <button
          onClick={onClose}
          className="lg:hidden p-1 hover:bg-dark-surface-hover rounded transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
      
      {/* User info */}
      <div className="p-4 border-b border-dark-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center">
            {isAdmin ? (
              <Shield className="w-5 h-5 text-white" />
            ) : (
              <User className="w-5 h-5 text-white" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.email}</p>
            <p className="text-xs text-dark-text-secondary">
              {isAdmin ? '管理員' : '用戶'}
            </p>
          </div>
        </div>
      </div>
      
      {/* Conversation List */}
      <ConversationList />
      
      {/* Footer with logout */}
      <div className="p-4 border-t border-dark-border">
        <button
          onClick={() => {
            if (confirm('確定要登出嗎？')) {
              logout()
            }
          }}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-dark-text-secondary hover:bg-dark-bg hover:text-error transition-colors"
        >
          <LogOut className="w-5 h-5" />
          <span>登出</span>
        </button>
      </div>
    </div>
  )
}
```

---

## 3.10 修改 ChatWindow

### 文件：`web-adapter/frontend/src/components/Chat/ChatWindow.tsx`

更新以使用 `getCurrentMessages()` 而不是直接訪問 messages：

```typescript
import { useState, useRef, useEffect } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { Send, Loader2, AlertCircle } from 'lucide-react'
import MessageList from './MessageList'

export default function ChatWindow() {
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  
  const { 
    sendMessage, 
    isSending, 
    isConnected, 
    error, 
    clearError,
    currentConversationId,
    conversations
  } = useChatStore()
  
  const currentConversation = conversations.find(c => c.id === currentConversationId)
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!input.trim() || isSending || !isConnected || !currentConversationId) {
      return
    }
    
    const message = input.trim()
    setInput('')
    
    try {
      await sendMessage(message)
      
      // Focus back on input
      inputRef.current?.focus()
    } catch (err) {
      // Error handled by store
    }
  }
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Submit on Enter (but not Shift+Enter)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }
  
  useEffect(() => {
    // Auto-focus input on mount
    inputRef.current?.focus()
  }, [])
  
  // 空狀態（沒有選擇對話）
  if (!currentConversationId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-dark-bg">
        <div className="text-center text-dark-text-secondary">
          <p className="text-lg mb-2">👈 選擇一個對話開始聊天</p>
          <p className="text-sm">或點擊「新對話」創建新的對話</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Connection error banner */}
      {!isConnected && (
        <div className="bg-error/10 border-b border-error/20 px-4 py-2 flex items-center gap-2 text-error">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">未連接到伺服器，正在重新連接...</span>
        </div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="bg-error/10 border-b border-error/20 px-4 py-2 flex items-center justify-between text-error">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">{error}</span>
          </div>
          <button
            onClick={clearError}
            className="text-xs hover:underline"
          >
            關閉
          </button>
        </div>
      )}
      
      {/* Conversation title */}
      {currentConversation && (
        <div className="px-4 py-2 border-b border-dark-border bg-dark-surface">
          <h3 className="text-sm font-medium truncate">
            {currentConversation.title}
          </h3>
          <p className="text-xs text-dark-text-secondary">
            {currentConversation.messageCount} 條消息
          </p>
        </div>
      )}
      
      {/* Messages */}
      <div className="flex-1 overflow-hidden">
        <MessageList />
      </div>
      
      {/* Input area */}
      <div className="border-t border-dark-border bg-dark-surface p-4">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3">
            {/* Text input */}
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={isConnected ? "輸入訊息... (Enter 發送，Shift+Enter 換行)" : "等待連接..."}
                className="w-full px-4 py-3 rounded-xl input-field resize-none"
                rows={1}
                style={{
                  minHeight: '48px',
                  maxHeight: '200px',
                  height: 'auto'
                }}
                disabled={!isConnected || isSending || !currentConversationId}
              />
            </div>
            
            {/* Send button */}
            <button
              type="submit"
              disabled={!input.trim() || !isConnected || isSending || !currentConversationId}
              className="btn-primary flex items-center gap-2 px-6 py-3"
            >
              {isSending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          
          {/* Character count */}
          <div className="mt-2 text-xs text-dark-text-secondary text-right">
            {input.length} / 4000
          </div>
        </form>
      </div>
    </div>
  )
}
```

---

## 3.11 修改 MessageList

### 文件：`web-adapter/frontend/src/components/Chat/MessageList.tsx`

更新以使用 `getCurrentMessages()`:

```typescript
import { useEffect, useRef } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { User, Bot } from 'lucide-react'

export default function MessageList() {
  const { getCurrentMessages } = useChatStore()
  const messages = getCurrentMessages()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // Auto-scroll to bottom when new message arrives
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])
  
  if (messages.length === 0) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center text-dark-text-secondary">
          <p className="text-lg mb-2">💬 開始新對話</p>
          <p className="text-sm">在下方輸入框發送您的第一條消息</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex gap-3 ${
            message.role === 'user' ? 'justify-end' : 'justify-start'
          }`}
        >
          {/* Avatar (for assistant) */}
          {message.role === 'assistant' && (
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
          )}
          
          {/* Message bubble */}
          <div
            className={`max-w-[70%] rounded-2xl px-4 py-3 ${
              message.role === 'user'
                ? 'bg-primary text-white'
                : 'bg-dark-surface border border-dark-border'
            }`}
          >
            <p className="text-sm whitespace-pre-wrap break-words">
              {message.content}
            </p>
            <p
              className={`text-xs mt-1 ${
                message.role === 'user' ? 'text-white/70' : 'text-dark-text-secondary'
              }`}
            >
              {new Date(message.timestamp).toLocaleTimeString('zh-TW', {
                hour: '2-digit',
                minute: '2-digit'
              })}
            </p>
          </div>
          
          {/* Avatar (for user) */}
          {message.role === 'user' && (
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <User className="w-5 h-5 text-primary" />
            </div>
          )}
        </div>
      ))}
      
      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </div>
  )
}
```

---

# Part 4: 測試和部署

## 4.1 完整測試清單

### 後端測試

```bash
# 1. 測試 Conversations API

TOKEN="<your_jwt_token>"
REST_API="<your_rest_api_endpoint>"

# 列出對話
curl -X GET "$REST_API/conversations" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# 創建新對話
curl -X POST "$REST_API/conversations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"測試對話"}' | jq '.'

# 獲取 conversation_id 後
CONV_ID="<conversation_id>"

# 重命名對話
curl -X PUT "$REST_API/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"新標題"}' | jq '.'

# 置頂對話
curl -X PUT "$REST_API/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_pinned":true}' | jq '.'

# 獲取對話消息
curl -X GET "$REST_API/conversations/$CONV_ID/messages" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# 刪除對話
curl -X DELETE "$REST_API/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### 前端測試清單

#### 基本功能
- [ ] 登入後自動載入對話列表
- [ ] 點擊「新對話」創建新對話並自動切換
- [ ] 點擊對話項切換對話
- [ ] 切換對話時正確載入消息
- [ ] 在當前對話中發送消息

#### 搜索功能
- [ ] 搜索框輸入關鍵字
- [ ] 搜索標題和內容
- [ ] 搜索結果即時更新
- [ ] 清空搜索恢復完整列表

#### 右鍵菜單
- [ ] 右鍵點擊對話項顯示菜單
- [ ] 點擊「重命名」打開重命名對話框
- [ ] 重命名成功後標題更新
- [ ] 點擊「置頂」將對話移到置頂區
- [ ] 再次點擊「取消置頂」恢復
- [ ] 點擊「刪除」打開確認對話框
- [ ] 確認後對話從列表移除
- [ ] 刪除當前對話後自動切換到最新對話

#### 狀態管理
- [ ] 發送消息時禁用輸入框
- [ ] 切換對話時保持連接
- [ ] 網絡斷線時顯示錯誤
- [ ] 錯誤可以關閉

#### 響應式設計
- [ ] 桌面端左側欄固定顯示
- [ ] 移動端左側欄可收合
- [ ] 搜索框在小螢幕正常顯示
- [ ] 右鍵菜單不超出螢幕

#### 無障礙功能
- [ ] Tab 鍵可以導航
- [ ] ESC 鍵關閉對話框和菜單
- [ ] Enter 鍵提交表單
- [ ] 螢幕閱讀器可以讀取內容

---

## 4.2 前端部署

### 安裝依賴

```bash
cd web-adapter/frontend

# 安裝 date-fns（用於時間格式化）
npm install date-fns
```

### 建構和部署

```bash
# 建構
npm run build

# 上傳到 S3
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text)

aws s3 sync dist/ s3://$BUCKET_NAME/ --delete

# 清除 CloudFront 快取
DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
  --output text)

aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*"
```

---

## 4.3 完整部署檢查清單

### Day 1: 後端部署
- [ ] CloudFormation template 驗證通過
- [ ] SAM build 成功
- [ ] SAM deploy 成功
- [ ] Conversations 表已創建
- [ ] 所有 Lambda 函數已更新
- [ ] 新 API 端點可訪問
- [ ] 後端 API 測試通過

### Day 2: 數據遷移
- [ ] 遷移腳本 dry-run 檢查通過
- [ ] 實際遷移執行成功
- [ ] 驗證腳本確認數據正確
- [ ] 手動抽查用戶數據正常
- [ ] 舊消息都有 conversation_id
- [ ] Conversations 表記錄準確

### Day 3: 前端部署
- [ ] 前端依賴安裝完成
- [ ] TypeScript 編譯無錯誤
- [ ] 建構成功
- [ ] 上傳到 S3 完成
- [ ] CloudFront 快取已清除
- [ ] 前端功能測試全部通過

---

# Part 5: 故障排除

## 5.1 常見問題

### 問題 1：對話列表空白

**症狀**：登入後看不到對話列表

**可能原因**：
1. API 未正確返回數據
2. unified_user_id 映射問題
3. 前端 API 調用失敗

**解決步驟**：
```bash
# 檢查後端日誌
aws logs tail /aws/lambda/agentcore-web-adapter-conversations-api \
  --region us-west-2 --since 5m

# 檢查 DynamoDB 表
aws dynamodb scan \
  --region us-west-2 \
  --table-name agentcore-web-adapter-conversations \
  --limit 5

# 檢查前端控制台
# F12 → Console → 查看錯誤
```

---

### 問題 2：無法切換對話

**症狀**：點擊對話項沒有反應

**可能原因**：
1. conversation_id 不存在
2. 消息載入失敗
3. 前端狀態未更新

**解決步驟**：
```typescript
// 在瀏覽器控制台執行
import { useChatStore } from '@/stores/chatStore'
const store = useChatStore.getState()
console.log('Current conversation ID:', store.currentConversationId)
console.log('Conversations:', store.conversations)
```

---

### 問題 3：消息發送到錯誤的對話

**症狀**：消息出現在其他對話中

**可能原因**：
1. conversation_id 未正確傳遞
2. WebSocket 消息格式錯誤

**解決步驟**：
```bash
# 檢查 WebSocket Lambda 日誌
aws logs tail /aws/lambda/agentcore-web-adapter-ws-default \
  --region us-west-2 --since 5m --follow

# 查看 conversation_id 是否正確
```

---

### 問題 4：遷移失敗

**症狀**：遷移腳本報錯

**可能原因**：
1. AWS 權限不足
2. 表名錯誤
3. 數據格式問題

**解決步驟**：
```bash
# 檢查權限
aws sts get-caller-identity

# 檢查表是否存在
aws dynamodb list-tables --region us-west-2 | grep conversation

# 嘗試單用戶遷移
python migrate-conversations.py --user-id "<user_id>" --dry-run
```

---

## 5.2 回滾計劃

### 如果後端部署失敗

```bash
# CloudFormation 會自動回滾
# 手動檢查狀態
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter

# 如果需要手動回滾
aws cloudformation cancel-update-stack \
  --region us-west-2 \
  --stack-name agentcore-web-adapter
```

### 如果遷移出錯

```bash
# 方案 1：重新運行遷移（冪等性）
python migrate-conversations.py

# 方案 2：手動修正特定用戶
python migrate-conversations.py --user-id "<user_id>"

# 方案 3：刪除 conversations 表重新開始
aws dynamodb delete-table \
  --region us-west-2 \
  --table-name agentcore-web-adapter-conversations

# 重新部署後端（會重新創建表）
```

### 如果前端有 bug

```bash
# 回滾前端到上一版本
cd web-adapter/frontend

# 檢出上一次提交
git checkout HEAD~1

# 重新建構和部署
npm run build
aws s3 sync dist/ s3://$BUCKET_NAME/ --delete

# 清除快取
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*"
```

---

## 5.3 監控設置

### CloudWatch Alarms

```bash
# 為 Conversations API 設置警報
aws cloudwatch put-metric-alarm \
  --region us-west-2 \
  --alarm-name "ConversationsAPI-Errors" \
  --alarm-description "Alert when Conversations API error rate > 5%" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=agentcore-web-adapter-conversations-api \
  --evaluation-periods 1
```

---

## 5.4 性能優化建議

### 減少 API 調用

```typescript
// 使用 React Query 緩存
import { useQuery } from '@tanstack/react-query'

const { data: conversations } = useQuery({
  queryKey: ['conversations'],
  queryFn: () => api.getConversations(),
  staleTime: 5 * 60 * 1000,  // 5 分鐘內不重新獲取
  cacheTime: 30 * 60 * 1000   // 30 分鐘緩存
})
```

### 虛擬滾動（大量對話）

```typescript
// 使用 react-window 或 react-virtualized
import { FixedSizeList } from 'react-window'

<FixedSizeList
  height={600}
  itemCount={conversations.length}
  itemSize={80}
  width="100%"
>
  {({ index, style }) => (
    <div style={style}>
      <ConversationItem conversation={conversations[index]} />
    </div>
  )}
</FixedSizeList>
```

---

# 📊 實施總結

## 完成後的功能

✅ **對話管理**
- 對話列表顯示（置頂 + 時間排序）
- 創建新對話
- 切換對話
- 重命名對話
- 刪除對話
- 置頂對話

✅ **搜索功能**
- 搜索對話標題
- 搜索對話內容
- 即時搜索結果

✅ **持久化**
- 對話保存到 DynamoDB
- 跨設備同步
- 歷史對話完整保留

✅ **用戶體驗**
- 美觀的 UI
- 響應式設計
- 無障礙支持
- 良好的錯誤處理

---

## 預期成本影響

| 項目 | 舊架構 | 新架構 | 增加 |
|------|--------|--------|------|
| DynamoDB 寫入 | 每條消息 1 次 | 每條消息 2-3 次 | +100-200% |
| DynamoDB 讀取 | 載入歷史時 | +對話列表 | +10-20% |
| Lambda 調用 | 現有 | +Conversations API | +5-10% |
| 存儲 | 消息 | +Conversations 表 | +5% |

**總成本增加估算**: 約 20-30% DynamoDB 成本

---

## 時間總結

| 階段 | 預計時間 | 實際時間 |
|------|----------|----------|
| 後端升級 | 5-6 小時 | _____ |
| 數據遷移 | 1-2 小時 | _____ |
| 前端實現 | 8-10 小時 | _____ |
| 測試部署 | 3-4 小時 | _____ |
| **總計** | **20-22 小時** | **_____** |

---

**文檔版本**: 2.0  
**創建日期**: 2026-01-08  
**狀態**: 完成  
**適用於**: AgentCore Nexus Web Channel

**下一步**: 按照本指南逐步實施！
