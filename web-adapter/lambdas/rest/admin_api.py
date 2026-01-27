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
    列出所有對話（使用 GlobalTimestampIndex GSI）
    
    Query Parameters:
    - limit: 每頁數量（默認 20，最大 100）
    - next_token: 分頁 token
    - channel: 篩選通道（telegram/web）
    - start_time: 開始時間（ISO 8601）
    - end_time: 結束時間（ISO 8601）
    
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
        limit = int(params.get('limit', '20'))
        limit = min(limit, 100)  # 最大 100

        next_token = params.get('next_token')
        channel = params.get('channel')  # telegram 或 web
        start_time = params.get('start_time')
        end_time = params.get('end_time')

        # 選擇 GSI
        table = dynamodb.Table(TABLE_NAME)

        if channel:
            # 使用 ChannelTimestampIndex
            index_name = 'ChannelTimestampIndex'
            key_condition = Key('channel').eq(channel)

            # 添加時間範圍條件
            if start_time:
                key_condition = key_condition & Key('timestamp').gte(start_time)
            elif end_time:
                key_condition = key_condition & Key('timestamp').lte(end_time)
        else:
            # 使用 GlobalTimestampIndex
            index_name = 'GlobalTimestampIndex'
            key_condition = Key('global_partition').eq('ALL')

            # 添加時間範圍條件
            if start_time and end_time:
                key_condition = key_condition & Key('timestamp').between(start_time, end_time)
            elif start_time:
                key_condition = key_condition & Key('timestamp').gte(start_time)
            elif end_time:
                key_condition = key_condition & Key('timestamp').lte(end_time)

        # 構建查詢參數
        query_params = {
            'IndexName': index_name,
            'KeyConditionExpression': key_condition,
            'Limit': limit,
            'ScanIndexForward': False  # 降序（最新的在前）
        }

        # 分頁
        if next_token:
            query_params['ExclusiveStartKey'] = json.loads(next_token)

        # 執行查詢
        response = table.query(**query_params)

        # 提取對話
        conversations = response.get('Items', [])

        # 準備響應
        result = {
            'conversations': conversations,
            'count': len(conversations)
        }

        # 分頁 token
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
    獲取對話詳情
    
    Path Parameters:
    - conversation_id: 對話 ID
    
    Returns:
    {
        "conversation_id": "...",
        "user_id": "...",
        "channel": "telegram",
        "messages": [...],
        "attachments": [...],
        "created_at": "...",
        "updated_at": "..."
    }
    """
    try:
        # 提取 conversation_id
        path_params = event.get('pathParameters') or {}
        conversation_id = path_params.get('conversation_id')

        if not conversation_id:
            return create_response(400, {'error': 'conversation_id is required'})

        # 查詢對話
        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(
            Key={'conversation_id': conversation_id}
        )

        if 'Item' not in response:
            return create_response(404, {'error': 'Conversation not found'})

        conversation = response['Item']

        # 統計附件
        messages = conversation.get('messages', [])
        attachments_count = {
            'images': 0,
            'files': 0,
            'total': 0
        }

        for msg in messages:
            if 'attachments' in msg and msg['attachments']:
                for att in msg['attachments']:
                    attachments_count['total'] += 1
                    if att.get('type') == 'photo':
                        attachments_count['images'] += 1
                    else:
                        attachments_count['files'] += 1

        # 添加統計
        conversation['statistics'] = {
            'message_count': len(messages),
            'attachments': attachments_count
        }

        return create_response(200, conversation)

    except Exception as e:
        print(f"Error getting conversation detail: {e}")
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

    elif path.startswith('/admin/conversations/') and method == 'GET':
        return get_conversation_detail(event, context)

    else:
        return create_response(404, {'error': 'Not found'})
