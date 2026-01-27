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
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

sys.path.insert(0, '/opt/python')
# 導入審計裝飾器
from audit_decorator import audit_log, require_permission

# 初始化 DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-west-2'))

# 環境變數（使用完整表名）
TABLE_NAME = os.environ.get('CONVERSATION_TABLE_NAME', 'agentcore-conversation-history-dev')
METADATA_TABLE_NAME = os.environ.get('METADATA_TABLE_NAME', 'agentcore-conversation-metadata-prod')


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
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(decimal_to_float(body), ensure_ascii=False)
    }


def extract_user_context(event: dict[str, Any]) -> dict[str, str]:
    """
    從 API Gateway event 提取用戶上下文
    
    包含：user_id, role, email
    """
    authorizer = event.get('requestContext', {}).get('authorizer', {})

    return {
        'user_id': authorizer.get('principalId', 'unknown'),
        'role': authorizer.get('role', 'user'),
        'email': authorizer.get('email', '')
    }


@audit_log(
    action='admin_view_conversations',
    resource_type='conversation'
)
@require_permission('admin')
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
        params = event.get('queryStringParameters') or {}
        limit = int(params.get('limit', '50'))
        limit = min(limit, 100)

        next_token = params.get('next_token')
        channel_filter = params.get('channel')

        # 查詢 metadata 表（對話摘要）
        metadata_table = dynamodb.Table(METADATA_TABLE_NAME)

        scan_params = {
            'Limit': limit
        }

        if next_token:
            scan_params['ExclusiveStartKey'] = json.loads(next_token)

        # 執行掃描
        response = metadata_table.scan(**scan_params)
        conversations = response.get('Items', [])

        # 客戶端篩選（如有 channel 條件）
        if channel_filter:
            # 需要從 history 表查詢 channel 資訊（較慢）
            # 或在 metadata 表添加 channel 欄位（更好）
            pass

        # 添加必要欄位：user_id（前端期望）
        for conv in conversations:
            # 從 unified_user_id 複製（如果沒有 user_id）
            if 'user_id' not in conv:
                conv['user_id'] = conv.get('unified_user_id', '')

            # 確保有 timestamp 欄位（前端排序用）
            if 'timestamp' not in conv:
                conv['timestamp'] = conv.get('last_message_time', conv.get('created_at', ''))

        # 準備響應
        result = {
            'conversations': conversations,
            'count': len(conversations)
        }

        if 'LastEvaluatedKey' in response:
            result['next_token'] = json.dumps(decimal_to_float(response['LastEvaluatedKey']))

        return create_response(200, result)

    except ValueError as e:
        return create_response(400, {'error': f'Invalid parameter: {str(e)}'})
    except Exception as e:
        print(f"Error listing conversations: {e}")
        return create_response(500, {'error': 'Internal server error'})


@audit_log(
    action='admin_view_conversation_detail',
    resource_type='conversation'
)
@require_permission('admin')
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
        path_params = event.get('pathParameters') or {}
        conversation_id = path_params.get('conversation_id')

        if not conversation_id:
            return create_response(400, {'error': 'conversation_id is required'})

        # 查詢該對話的所有消息（使用 query，不是 get_item）
        table = dynamodb.Table(TABLE_NAME)
        response = table.query(
            KeyConditionExpression=Key('conversation_id').eq(conversation_id),
            ScanIndexForward=True  # 按時間升序（早到晚）
        )

        items = response.get('Items', [])

        if not items:
            return create_response(404, {'error': 'Conversation not found'})

        # 組裝對話數據
        messages = []
        unified_user_id = None
        channel = None
        created_at = None
        updated_at = None

        attachments_count = {
            'images': 0,
            'files': 0,
            'total': 0
        }

        for item in items:
            # 提取基本資訊（從第一條記錄）
            if unified_user_id is None:
                # 處理兩種格式：Telegram 用 sender_id，Web 用 unified_user_id
                unified_user_id = item.get('unified_user_id') or item.get('sender_id', '')
                channel = item.get('channel', 'unknown')
                created_at = item.get('timestamp')

            updated_at = item.get('timestamp')  # 最後一條的時間

            # 組裝消息（處理 Telegram 和 Web 兩種格式）
            content = item.get('content', {})

            # Telegram 格式：content 是字符串
            if isinstance(content, str):
                message_text = content
                message_attachments = []
            # Web 格式：content 是對象 {text: ..., attachments: [...]}
            else:
                message_text = content.get('text', '')
                message_attachments = content.get('attachments', [])

            message = {
                'role': item.get('role', 'user'),
                'content': message_text,
                'timestamp': item.get('timestamp'),
                'attachments': message_attachments
            }
            messages.append(message)

            # 統計附件
            for att in message_attachments:
                attachments_count['total'] += 1
                if att.get('type') == 'photo':
                    attachments_count['images'] += 1
                else:
                    attachments_count['files'] += 1

        # 構建響應
        result = {
            'conversation_id': conversation_id,
            'user_id': unified_user_id,
            'channel': channel,
            'messages': messages,
            'created_at': created_at,
            'updated_at': updated_at,
            'statistics': {
                'message_count': len(messages),
                'attachments': attachments_count
            }
        }

        return create_response(200, result)

    except Exception as e:
        print(f"Error getting conversation detail: {e}")
        import traceback
        traceback.print_exc()
        return create_response(500, {'error': 'Internal server error'})


@audit_log(
    action='admin_view_audit_logs',
    resource_type='audit'
)
@require_permission('admin')
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
        params = event.get('queryStringParameters') or {}
        limit = int(params.get('limit', '20'))
        limit = min(limit, 100)

        next_token = params.get('next_token')
        admin_email = params.get('admin_email')
        action = params.get('action')

        # 查詢審計日誌表
        audit_table = dynamodb.Table(os.environ.get('AUDIT_LOGS_TABLE', 'agentcore-admin-audit-logs-dev'))

        # 使用 scan（簡單實現）或 GSI（如果有篩選）
        query_params = {
            'Limit': limit,
        }

        if next_token:
            query_params['ExclusiveStartKey'] = json.loads(next_token)

        # 執行掃描
        response = audit_table.scan(**query_params)

        logs = response.get('Items', [])

        # 客戶端篩選（如果有條件）
        if admin_email:
            logs = [log for log in logs if log.get('admin_email') == admin_email]
        if action:
            logs = [log for log in logs if log.get('action') == action]

        # 按時間降序排序
        logs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

        result = {
            'logs': logs,
            'count': len(logs)
        }

        if 'LastEvaluatedKey' in response:
            result['next_token'] = json.dumps(decimal_to_float(response['LastEvaluatedKey']))

        return create_response(200, result)

    except ValueError as e:
        return create_response(400, {'error': f'Invalid parameter: {str(e)}'})
    except Exception as e:
        print(f"Error listing audit logs: {e}")
        return create_response(500, {'error': 'Internal server error'})


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Admin API 主 handler
    
    路由請求到對應的處理函數
    """
    # OPTIONS 預檢請求
    if event.get('httpMethod') == 'OPTIONS':
        return create_response(200, {})

    # 提取路徑和方法
    path = event.get('path', '')
    method = event.get('httpMethod', '')

    print(f"Admin API request: {method} {path}")

    # 路由
    if path == '/admin/conversations' and method == 'GET':
        return list_conversations(event, context)

    elif path == '/admin/audit-logs' and method == 'GET':
        return list_audit_logs(event, context)

    elif path.startswith('/admin/conversations/') and method == 'GET':
        return get_conversation_detail(event, context)

    else:
        return create_response(404, {'error': 'Not found'})
