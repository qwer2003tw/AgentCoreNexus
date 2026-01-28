"""
Admin API Handler - 管理員對話管理

提供管理員專用的 API endpoints：
- 對話列表查詢（使用 GSI）
- 對話詳情查看
- 全文搜尋（未來）
- AI 摘要生成（Day 7-8）
"""

import json
import os

# 導入審計和權限系統
import sys
from datetime import datetime
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

sys.path.insert(0, "/opt/python")
# 導入審計裝飾器
from audit_decorator import audit_log, require_permission

# 初始化 AWS clients
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-west-2"))
bedrock_runtime = boto3.client(
    "bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-west-2")
)

# 環境變數（使用完整表名）
TABLE_NAME = os.environ.get("CONVERSATION_TABLE_NAME", "agentcore-conversation-history-dev")
METADATA_TABLE_NAME = os.environ.get("METADATA_TABLE_NAME", "agentcore-conversation-metadata-prod")
SUMMARIES_TABLE_NAME = os.environ.get("SUMMARIES_TABLE", "agentcore-conversation-summaries-dev")


def decimal_to_float(obj: Any) -> Any:
    """
    遞歸轉換 DynamoDB Decimal 為 float/int
    """
    if isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: decimal_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    return obj


def create_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """
    創建標準 API 響應
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(decimal_to_float(body), ensure_ascii=False),
    }


def extract_user_context(event: dict[str, Any]) -> dict[str, str]:
    """
    從 API Gateway event 提取用戶上下文

    包含：user_id, role, email
    """
    authorizer = event.get("requestContext", {}).get("authorizer", {})

    return {
        "user_id": authorizer.get("principalId", "unknown"),
        "role": authorizer.get("role", "user"),
        "email": authorizer.get("email", ""),
    }


@audit_log(action="admin_view_conversations", resource_type="conversation")
@require_permission("admin")
def list_conversations(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    列出所有對話（查詢 metadata 表獲取對話摘要）

    Query Parameters:
    - limit: 每頁數量（默認 50，最大 100）
    - next_token: 分頁 token
    - channel: 篩選通道（telegram/web）

    Returns:
    {
        "conversations": [...],
        "next_token": "...",
        "count": 20
    }
    """
    try:
        # 提取查詢參數
        params = event.get("queryStringParameters") or {}
        limit = int(params.get("limit", "50"))
        limit = min(limit, 100)

        next_token = params.get("next_token")
        channel_filter = params.get("channel")

        # 查詢 metadata 表（對話摘要）
        metadata_table = dynamodb.Table(METADATA_TABLE_NAME)

        scan_params = {"Limit": limit}

        if next_token:
            scan_params["ExclusiveStartKey"] = json.loads(next_token)

        # 執行掃描
        response = metadata_table.scan(**scan_params)
        conversations = response.get("Items", [])

        # 客戶端篩選（如有 channel 條件）
        if channel_filter:
            # 需要從 history 表查詢 channel 資訊（較慢）
            # 或在 metadata 表添加 channel 欄位（更好）
            pass

        # 添加必要欄位：user_id（前端期望）
        for conv in conversations:
            # 從 unified_user_id 複製（如果沒有 user_id）
            if "user_id" not in conv:
                conv["user_id"] = conv.get("unified_user_id", "")

            # 確保有 timestamp 欄位（前端排序用）
            if "timestamp" not in conv:
                conv["timestamp"] = conv.get("last_message_time", conv.get("created_at", ""))

        # 準備響應
        result = {"conversations": conversations, "count": len(conversations)}

        if "LastEvaluatedKey" in response:
            result["next_token"] = json.dumps(decimal_to_float(response["LastEvaluatedKey"]))

        return create_response(200, result)

    except ValueError as e:
        return create_response(400, {"error": f"Invalid parameter: {str(e)}"})
    except Exception as e:
        print(f"Error listing conversations: {e}")
        return create_response(500, {"error": "Internal server error"})


@audit_log(action="admin_view_conversation_detail", resource_type="conversation")
@require_permission("admin")
def get_conversation_detail(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    獲取對話詳情（查詢 history 表的所有消息）

    Path Parameters:
    - conversation_id: 對話 ID

    Returns:
    {
        "conversation_id": "...",
        "user_id": "...",
        "channel": "telegram",
        "messages": [...],
        "statistics": {...}
    }
    """
    try:
        # 提取 conversation_id
        path_params = event.get("pathParameters") or {}
        conversation_id = path_params.get("conversation_id")

        if not conversation_id:
            return create_response(400, {"error": "conversation_id is required"})

        # 查詢該對話的所有消息（使用 query，不是 get_item）
        table = dynamodb.Table(TABLE_NAME)
        response = table.query(
            KeyConditionExpression=Key("conversation_id").eq(conversation_id),
            ScanIndexForward=True,  # 按時間升序（早到晚）
        )

        items = response.get("Items", [])

        if not items:
            return create_response(404, {"error": "Conversation not found"})

        # 組裝對話數據
        messages = []
        unified_user_id = None
        channel = None
        created_at = None
        updated_at = None

        attachments_count = {"images": 0, "files": 0, "total": 0}

        for item in items:
            # 提取基本資訊（從第一條記錄）
            if unified_user_id is None:
                # 處理兩種格式：Telegram 用 sender_id，Web 用 unified_user_id
                unified_user_id = item.get("unified_user_id") or item.get("sender_id", "")
                channel = item.get("channel", "unknown")
                created_at = item.get("timestamp")

            updated_at = item.get("timestamp")  # 最後一條的時間

            # 組裝消息（處理 Telegram 和 Web 兩種格式）
            content = item.get("content", {})

            # Telegram 格式：content 是字符串，附件在 metadata
            if isinstance(content, str):
                message_text = content
                # ⭐ Telegram 附件在 metadata.attachments
                metadata = item.get("metadata", {})
                message_attachments = metadata.get("attachments", [])
            # Web 格式：content 是對象 {text: ..., attachments: [...]}
            else:
                message_text = content.get("text", "")
                message_attachments = content.get("attachments", [])

            message = {
                "role": item.get("role", "user"),
                "content": message_text,
                "timestamp": item.get("timestamp"),
                "attachments": message_attachments,
            }
            messages.append(message)

            # 統計附件
            for att in message_attachments:
                attachments_count["total"] += 1
                if att.get("type") == "photo":
                    attachments_count["images"] += 1
                else:
                    attachments_count["files"] += 1

        # 構建響應
        result = {
            "conversation_id": conversation_id,
            "user_id": unified_user_id,
            "channel": channel,
            "messages": messages,
            "created_at": created_at,
            "updated_at": updated_at,
            "statistics": {"message_count": len(messages), "attachments": attachments_count},
        }

        return create_response(200, result)

    except Exception as e:
        print(f"Error getting conversation detail: {e}")
        import traceback

        traceback.print_exc()
        return create_response(500, {"error": "Internal server error"})


@audit_log(action="admin_view_audit_logs", resource_type="audit")
@require_permission("admin")
def list_audit_logs(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    列出審計日誌

    Query Parameters:
    - limit: 每頁數量（默認 20，最大 100）
    - next_token: 分頁 token
    - admin_email: 篩選管理員
    - action: 篩選操作類型
    - start_time: 開始時間（timestamp）
    - end_time: 結束時間（timestamp）
    """
    try:
        params = event.get("queryStringParameters") or {}
        limit = int(params.get("limit", "20"))
        limit = min(limit, 100)

        next_token = params.get("next_token")
        admin_email = params.get("admin_email")
        action = params.get("action")

        # 查詢審計日誌表
        audit_table = dynamodb.Table(
            os.environ.get("AUDIT_LOGS_TABLE", "agentcore-admin-audit-logs-dev")
        )

        # 使用 scan（簡單實現）或 GSI（如果有篩選）
        query_params = {
            "Limit": limit,
        }

        if next_token:
            query_params["ExclusiveStartKey"] = json.loads(next_token)

        # 執行掃描
        response = audit_table.scan(**query_params)

        logs = response.get("Items", [])

        # 客戶端篩選（如果有條件）
        if admin_email:
            logs = [log for log in logs if log.get("admin_email") == admin_email]
        if action:
            logs = [log for log in logs if log.get("action") == action]

        # 按時間降序排序
        logs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        result = {"logs": logs, "count": len(logs)}

        if "LastEvaluatedKey" in response:
            result["next_token"] = json.dumps(decimal_to_float(response["LastEvaluatedKey"]))

        return create_response(200, result)

    except ValueError as e:
        return create_response(400, {"error": f"Invalid parameter: {str(e)}"})
    except Exception as e:
        print(f"Error listing audit logs: {e}")
        return create_response(500, {"error": "Internal server error"})


@audit_log(action="admin_generate_summary", resource_type="conversation")
@require_permission("admin")
def generate_summary(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    生成對話的 AI 摘要

    POST /admin/conversations/:conversation_id/summary

    Returns:
    {
        "conversation_id": "...",
        "summary_text": "...",
        "attachment_stats": {...},
        "generated_at": timestamp,
        "cached": false
    }
    """
    try:
        # 1. 提取 conversation_id
        path_params = event.get("pathParameters") or {}
        conversation_id = path_params.get("conversation_id")

        if not conversation_id:
            return create_response(400, {"error": "conversation_id is required"})

        print(f"Generating summary for conversation: {conversation_id}")

        # 2. 檢查緩存（24小時內）
        summaries_table = dynamodb.Table(SUMMARIES_TABLE_NAME)
        cached = summaries_table.get_item(Key={"conversation_id": conversation_id})

        if "Item" in cached:
            cached_time = cached["Item"].get("generated_at", 0)
            current_time = int(datetime.now().timestamp() * 1000)

            # 如果小於 24 小時，返回緩存
            if current_time - cached_time < 24 * 3600 * 1000:
                print(
                    f"Returning cached summary (age: {(current_time - cached_time) / 3600000:.1f} hours)"
                )
                result = cached["Item"]
                result["cached"] = True
                # ⭐ 兼容性：同時提供 summary 和 summary_text
                result["summary"] = result.get("summary_text", "")
                return create_response(200, result)

        # 3. 獲取對話消息
        table = dynamodb.Table(TABLE_NAME)
        response = table.query(
            KeyConditionExpression=Key("conversation_id").eq(conversation_id), ScanIndexForward=True
        )

        items = response.get("Items", [])
        if not items:
            return create_response(404, {"error": "Conversation not found"})

        print(f"Found {len(items)} messages in conversation")

        # 4. 統計附件並組裝消息
        attachment_stats = {"images": 0, "documents": 0, "total": 0}
        messages_text = []

        for item in items:
            role = item.get("role", "user")
            content = item.get("content", {})

            # 處理兩種格式
            if isinstance(content, str):
                text = content
                # ⭐ Telegram 附件在 metadata.attachments
                metadata = item.get("metadata", {})
                attachments = metadata.get("attachments", [])
            else:
                text = content.get("text", "")
                attachments = content.get("attachments", [])

            messages_text.append(f"{role}: {text}")

            # 統計附件
            for att in attachments:
                attachment_stats["total"] += 1
                if att.get("type") == "photo":
                    attachment_stats["images"] += 1
                else:
                    attachment_stats["documents"] += 1

        print(f"Attachment stats: {attachment_stats}")

        # 5. 構建 Prompt
        prompt = _build_summary_prompt(messages_text, attachment_stats)

        # 6. 調用 Bedrock
        print("Calling Bedrock to generate summary...")
        summary_text = _call_bedrock(prompt)

        # 7. 保存摘要
        generated_at = int(datetime.now().timestamp() * 1000)
        summary_item = {
            "conversation_id": conversation_id,
            "summary_text": summary_text,
            "attachment_stats": attachment_stats,
            "generated_at": generated_at,
            "model_used": "anthropic.claude-3-haiku-20240307-v1:0",
        }

        summaries_table.put_item(Item=summary_item)
        print("Summary saved successfully")

        # 8. 返回結果（兼容性：同時提供 summary 和 summary_text）
        summary_item["cached"] = False
        summary_item["summary"] = summary_text  # ⭐ 添加兼容欄位
        return create_response(200, summary_item)

    except Exception as e:
        print(f"Error generating summary: {e}")
        import traceback

        traceback.print_exc()
        return create_response(500, {"error": f"Failed to generate summary: {str(e)}"})


def _build_summary_prompt(messages: list[str], attachment_stats: dict) -> str:
    """
    構建摘要 Prompt

    Args:
        messages: 消息列表（格式：["user: xxx", "assistant: yyy"]）
        attachment_stats: 附件統計

    Returns:
        完整的 prompt 字符串
    """
    att_desc = ""
    if attachment_stats["total"] > 0:
        att_desc = f"\n本對話包含 {attachment_stats['images']} 張圖片和 {attachment_stats['documents']} 個文件。"

    messages_str = "\n\n".join(messages[:50])  # 限制最多 50 條消息

    return f"""你是專業的對話摘要助手。請閱讀以下對話並生成結構化摘要。
{att_desc}

對話內容：
{messages_str}

請生成簡潔的摘要（200-300字），包含：
1. 【對話主題】（1-2句話）
2. 【關鍵討論點】（3-5個要點）
3. 【用戶需求】（如有）
4. 【解決方案】（如有）

請直接輸出摘要文字，不要添加額外說明。"""


def _call_bedrock(prompt: str) -> str:
    """
    調用 Bedrock 生成摘要

    Args:
        prompt: 完整的 prompt

    Returns:
        生成的摘要文字
    """
    try:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0", body=json.dumps(request_body)
        )

        response_body = json.loads(response["body"].read())

        # 提取文字
        content = response_body.get("content", [])
        if content and isinstance(content, list):
            return content[0].get("text", "摘要生成失敗")

        return "摘要生成失敗"

    except Exception as e:
        print(f"Bedrock invocation error: {e}")
        import traceback

        traceback.print_exc()
        return f"摘要生成時發生錯誤: {str(e)}"


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Admin API 主 handler

    路由請求到對應的處理函數
    """
    # OPTIONS 預檢請求
    if event.get("httpMethod") == "OPTIONS":
        return create_response(200, {})

    # 提取路徑和方法
    path = event.get("path", "")
    method = event.get("httpMethod", "")

    print(f"Admin API request: {method} {path}")

    # 路由
    if path == "/admin/conversations" and method == "GET":
        return list_conversations(event, context)

    elif path == "/admin/audit-logs" and method == "GET":
        return list_audit_logs(event, context)

    elif (
        path.startswith("/admin/conversations/") and path.endswith("/summary") and method == "POST"
    ):
        return generate_summary(event, context)

    elif path.startswith("/admin/conversations/") and method == "GET":
        return get_conversation_detail(event, context)

    else:
        return create_response(404, {"error": "Not found"})
