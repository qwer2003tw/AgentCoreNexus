"""
Telegram Lambda Handler - Webhook Receiver
接收 Telegram webhook 並驗證允許名單後發送到 SQS
"""
import json
import os
import time
import uuid
import datetime
from typing import Dict, Any, Optional
import boto3
from telegram import Update
from allowlist import check_allowed
from sqs_client import send_to_queue
from secrets_manager import get_telegram_secret_token
from commands.router import CommandRouter
from commands.handlers.debug_handler import DebugCommandHandler
from commands.handlers.info_handler import InfoCommandHandler
from commands.handlers.admin_handler import AdminCommandHandler
from utils.logger import get_logger
from utils.response import create_response
from utils.metrics import (
    metric_scope,
    set_default_dimensions,
    record_count_metric,
    record_duration_metric,
    METRIC_INVALID_TOKEN,
    METRIC_TOKEN_VALIDATION_SUCCESS,
    METRIC_ALLOWLIST_DENIED,
    METRIC_ALLOWLIST_APPROVED,
    METRIC_MESSAGES_RECEIVED,
    METRIC_MESSAGES_PROCESSED,
    METRIC_SQS_SUCCESS,
    METRIC_SQS_FAILURE,
    METRIC_DEBUG_COMMAND_RECEIVED,
    METRIC_LAMBDA_ERROR,
    METRIC_INVALID_PAYLOAD,
    METRIC_WEBHOOK_PARSING_FALLBACK,
    METRIC_MESSAGE_TYPE_TEXT,
    METRIC_MESSAGE_TYPE_PHOTO,
    METRIC_MESSAGE_TYPE_DOCUMENT,
    METRIC_MESSAGE_TYPE_VIDEO,
    METRIC_MESSAGE_TYPE_AUDIO,
    METRIC_MESSAGE_TYPE_OTHER,
    METRIC_TOTAL_DURATION,
    METRIC_SQS_DURATION,
)

logger = get_logger(__name__)

# 初始化 EventBridge 客戶端
_eventbridge_client = None

def get_eventbridge_client():
    """取得 EventBridge 客戶端單例"""
    global _eventbridge_client
    if _eventbridge_client is None:
        _eventbridge_client = boto3.client('events')
    return _eventbridge_client

# 初始化指令路由器（全域單例）
_command_router = None

def detect_channel(event: Dict[str, Any]) -> str:
    """
    檢測訊息來源通道
    
    Args:
        event: API Gateway event
        
    Returns:
        通道類型: 'telegram', 'discord', 'slack', 'web'
    """
    path = (event.get('path') or "").lower()
    if 'telegram' in path:
        return 'telegram'
    if 'discord' in path:
        return 'discord'
    if 'slack' in path:
        return 'slack'
    return 'web'

def normalize_message(raw_data: Dict[str, Any], channel: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    將原始訊息標準化為 Universal Message Schema
    
    Args:
        raw_data: 原始訊息資料
        channel: 通道類型
        event: 完整的 API Gateway event
        
    Returns:
        標準化的訊息物件
    """
    if channel == 'telegram':
        msg = raw_data.get('message') or {}
        from_user = msg.get('from') or {}
        chat = msg.get('chat') or {}
        text = msg.get('text', '')
        caption = msg.get('caption', '')
        
        # 判斷訊息類型
        message_type = 'text'
        attachments = []
        if msg.get('photo'):
            message_type = 'image'
            attachments.append({'type': 'photo', 'file_id': msg['photo'][-1].get('file_id')})
        elif msg.get('document'):
            message_type = 'file'
            attachments.append({'type': 'document', 'file_id': msg['document'].get('file_id')})
        elif msg.get('video'):
            message_type = 'video'
            attachments.append({'type': 'video', 'file_id': msg['video'].get('file_id')})
        elif msg.get('audio') or msg.get('voice'):
            message_type = 'audio'
            file_id = msg.get('audio', {}).get('file_id') or msg.get('voice', {}).get('file_id')
            attachments.append({'type': 'audio', 'file_id': file_id})
        
        return {
            "messageId": str(uuid.uuid4()),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "channel": {
                "type": "telegram",
                "channelId": str(chat.get('id')),
                "metadata": {
                    "chat_type": chat.get('type', 'private'),
                    "message_id": msg.get('message_id')
                }
            },
            "user": {
                "id": f"tg:{from_user.get('id')}",
                "channelUserId": str(from_user.get('id')),
                "username": from_user.get('username', ''),
                "displayName": (from_user.get('first_name', '') + ' ' + from_user.get('last_name', '')).strip() or 'Unknown'
            },
            "content": {
                "text": text or caption,
                "attachments": attachments,
                "messageType": message_type
            },
            "context": {
                "conversationId": str(chat.get('id')),
                "sessionId": str(from_user.get('id')),
                "threadId": ""
            },
            "routing": {
                "priority": "normal",
                "tags": [],
                "targetAgent": ""
            },
            "raw": raw_data  # 保留原始資料供後續處理使用
        }
    
    # 其他通道的標準化邏輯（未來擴展）
    return {
        "messageId": str(uuid.uuid4()),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "channel": {
            "type": channel,
            "channelId": "unknown",
            "metadata": {}
        },
        "user": {
            "id": "unknown",
            "channelUserId": "unknown",
            "username": "",
            "displayName": "Unknown"
        },
        "content": {
            "text": "",
            "attachments": [],
            "messageType": "text"
        },
        "context": {
            "conversationId": "unknown",
            "sessionId": "unknown",
            "threadId": ""
        },
        "routing": {
            "priority": "normal",
            "tags": [],
            "targetAgent": ""
        },
        "raw": raw_data
    }

def publish_to_eventbridge(normalized_message: Dict[str, Any]) -> bool:
    """
    發布標準化訊息到 EventBridge
    
    Args:
        normalized_message: 標準化的訊息物件
        
    Returns:
        發布是否成功
    """
    event_bus_name = os.getenv('EVENT_BUS_NAME')
    if not event_bus_name:
        logger.warning("EVENT_BUS_NAME not configured, skipping EventBridge publish")
        return False
    
    try:
        evb = get_eventbridge_client()
        
        # 移除 raw 資料以減少 EventBridge 事件大小
        message_copy = normalized_message.copy()
        message_copy.pop('raw', None)
        
        response = evb.put_events(
            Entries=[{
                "Source": "universal-adapter",
                "DetailType": "message.received",
                "Detail": json.dumps(message_copy),
                "EventBusName": event_bus_name
            }]
        )
        
        # 檢查發布結果
        if response.get('FailedEntryCount', 0) > 0:
            logger.error(f"EventBridge publish failed: {response}")
            return False
        
        logger.info(
            "Message published to EventBridge",
            extra={
                'event_type': 'eventbridge_publish',
                'message_id': normalized_message.get('messageId'),
                'channel': normalized_message['channel']['type']
            }
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish to EventBridge: {e}", exc_info=True)
        return False

def get_command_router() -> CommandRouter:
    """
    取得指令路由器單例
    
    Returns:
        CommandRouter: 路由器實例
    """
    global _command_router
    if _command_router is None:
        _command_router = CommandRouter()
        # 註冊所有指令處理器
        _command_router.register(DebugCommandHandler())
        _command_router.register(InfoCommandHandler())
        _command_router.register(AdminCommandHandler())
        logger.info("Command router initialized with handlers")
    return _command_router


def record_message_type_metric(metrics, update: Optional[Update]) -> None:
    """
    記錄訊息類型指標
    
    Args:
        metrics: MetricsLogger 實例
        update: Telegram Update 物件（可能為 None）
    """
    if not update or not update.effective_message:
        return
    
    msg = update.effective_message
    
    # 按照優先順序判斷訊息類型
    if msg.text and not msg.caption:
        # 純文字訊息（不包含有 caption 的媒體）
        record_count_metric(metrics, METRIC_MESSAGE_TYPE_TEXT)
    elif msg.photo:
        record_count_metric(metrics, METRIC_MESSAGE_TYPE_PHOTO)
    elif msg.document:
        record_count_metric(metrics, METRIC_MESSAGE_TYPE_DOCUMENT)
    elif msg.video:
        record_count_metric(metrics, METRIC_MESSAGE_TYPE_VIDEO)
    elif msg.audio or msg.voice:
        record_count_metric(metrics, METRIC_MESSAGE_TYPE_AUDIO)
    else:
        # 其他類型（sticker, location, contact, poll 等）
        record_count_metric(metrics, METRIC_MESSAGE_TYPE_OTHER)


@metric_scope
def lambda_handler(event: Dict[str, Any], context: Any, metrics) -> Dict[str, Any]:
    """
    Lambda 入口函數
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    # 設定 EMF 預設維度
    function_name = context.function_name if context else 'telegram-lambda-receiver'
    set_default_dimensions(metrics, function_name)
    
    # 記錄開始時間用於計算總執行時間
    start_time = time.time()
    
    try:
        # 驗證 Telegram Secret Token（從 Secrets Manager 動態讀取）
        expected_token = get_telegram_secret_token()
        if expected_token:
            headers = event.get('headers', {})
            # 支援大小寫 header key
            actual_token = (
                headers.get('X-Telegram-Bot-Api-Secret-Token') or 
                headers.get('x-telegram-bot-api-secret-token', '')
            )
            
            if actual_token != expected_token:
                logger.warning(
                    "Invalid secret token",
                    extra={'event_type': 'invalid_token'}
                )
                # 記錄秘密令牌驗證失敗指標
                record_count_metric(metrics, METRIC_INVALID_TOKEN)
                return create_response(403, {'error': 'Unauthorized'})
            else:
                # 記錄秘密令牌驗證成功指標
                record_count_metric(metrics, METRIC_TOKEN_VALIDATION_SUCCESS)
        
        # 解析請求體
        body = json.loads(event.get('body', '{}'))
        logger.info("Received webhook", extra={'event_type': 'webhook_received'})
        
        # 記錄收到訊息指標
        record_count_metric(metrics, METRIC_MESSAGES_RECEIVED)
        
        # 檢測通道類型
        channel = detect_channel(event)
        logger.debug(f"Detected channel: {channel}")
        
        # 使用 python-telegram-bot 的 Update 物件解析（帶降級處理）
        chat_id: Optional[int] = None
        username: str = ''
        text: str = ''
        caption: str = ''
        
        try:
            update = Update.de_json(body, None)
            if update and update.effective_message:
                chat_id = update.effective_chat.id
                username = update.effective_user.username if update.effective_user else ''
                text = update.effective_message.text or ''
                caption = update.effective_message.caption or ''
                logger.debug("Successfully parsed update with Update object")
            else:
                # Update 物件存在但沒有有效訊息，降級
                raise ValueError("No effective message in update")
        except Exception as e:
            # 降級：使用原始方式解析
            logger.debug(f"Failed to parse with Update object, using fallback: {str(e)}")
            # 記錄 Update 解析失敗降級指標
            record_count_metric(metrics, METRIC_WEBHOOK_PARSING_FALLBACK)
            
            message = body.get('message', {})
            chat = message.get('chat', {})
            from_user = message.get('from', {})
            
            chat_id = chat.get('id')
            username = from_user.get('username', '')
            text = message.get('text', '')
            update = None  # 降級時設為 None
        
        # 驗證必要欄位
        if not chat_id:
            logger.warning("Missing chat_id in webhook")
            # 記錄無效 payload 指標
            record_count_metric(metrics, METRIC_INVALID_PAYLOAD)
            return create_response(400, {'error': 'Invalid webhook payload'})
        
        # 嘗試使用指令路由器處理訊息（在 allowlist 檢查之前）
        if update and update.effective_message:
            command_text = text or caption
            if command_text:
                router = get_command_router()
                handled = router.route(update, event)
                
                # 只有當指令被成功處理時（handled == True），才返回 command_handled
                # 如果 handled == False，代表不是指令，應該繼續正常流程
                if handled:
                    # 指令已被處理，記錄相關指標
                    # 檢查是否為 debug 指令以記錄指標
                    if command_text.strip() == '/debug' or command_text.strip().startswith('/debug '):
                        record_count_metric(metrics, METRIC_DEBUG_COMMAND_RECEIVED)
                    
                    logger.info(
                        "Command handled by router",
                        extra={
                            'chat_id': chat_id,
                            'username': username,
                            'command_success': handled,
                            'event_type': 'command_handled'
                        }
                    )
                    return create_response(200, {'status': 'command_handled'})
        
        # 檢查允許名單
        if not check_allowed(chat_id, username):
            logger.warning(
                "Unauthorized access attempt",
                extra={
                    'chat_id': chat_id,
                    'username': username,
                    'event_type': 'unauthorized'
                }
            )
            # 記錄被白名單拒絕指標
            record_count_metric(metrics, METRIC_ALLOWLIST_DENIED)
            # 即使被 allowlist 阻擋，也要回應 200 OK
            # 這樣 Telegram 才不會重複發送同樣的訊息
            return create_response(200, {'status': 'ignored'})
        
        # 白名單檢查通過，記錄相關指標
        record_count_metric(metrics, METRIC_ALLOWLIST_APPROVED)
        # 記錄訊息類型指標
        record_message_type_metric(metrics, update)
        
        # 標準化訊息（轉換為 Universal Message Schema）
        normalized = normalize_message(body, channel, event)
        logger.debug(f"Message normalized: {normalized['messageId']}")
        
        # 發布到 EventBridge（新增的多通道事件匯流排）
        eventbridge_success = publish_to_eventbridge(normalized)
        if eventbridge_success:
            logger.info(
                "Message sent to EventBridge",
                extra={
                    'message_id': normalized['messageId'],
                    'channel': channel,
                    'event_type': 'eventbridge_sent'
                }
            )
        
        # 發送到 SQS（保持向後兼容，雙軌運行）
        sqs_start_time = time.time()
        success = send_to_queue(body)
        sqs_duration = (time.time() - sqs_start_time) * 1000  # 轉換為毫秒
        
        # 記錄 SQS 發送時間
        record_duration_metric(metrics, METRIC_SQS_DURATION, sqs_duration)
        
        if not success:
            logger.error(
                "Failed to send message to SQS",
                extra={
                    'chat_id': chat_id,
                    'event_type': 'sqs_error'
                }
            )
            # 記錄 SQS 發送失敗指標
            record_count_metric(metrics, METRIC_SQS_FAILURE)
            # 即使 SQS 發送失敗，也回應 200 OK 避免 Telegram 重試
            # 錯誤已經記錄在日誌中，可以稍後處理
            return create_response(200, {'status': 'sqs_failed'})
        
        logger.info(
            "Message processed successfully",
            extra={
                'chat_id': chat_id,
                'username': username,
                'event_type': 'success'
            }
        )
        
        # 記錄 SQS 發送成功和訊息處理成功指標
        record_count_metric(metrics, METRIC_SQS_SUCCESS)
        record_count_metric(metrics, METRIC_MESSAGES_PROCESSED)
        
        # 記錄總執行時間
        total_duration = (time.time() - start_time) * 1000  # 轉換為毫秒
        record_duration_metric(metrics, METRIC_TOTAL_DURATION, total_duration)
        
        # 快速回應 200 OK
        return create_response(200, {'status': 'ok'})
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {str(e)}")
        # 記錄無效 payload 和 Lambda 錯誤指標
        record_count_metric(metrics, METRIC_INVALID_PAYLOAD)
        record_count_metric(metrics, METRIC_LAMBDA_ERROR)
        return create_response(400, {'error': 'Invalid JSON'})
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        # 記錄 Lambda 錯誤指標
        record_count_metric(metrics, METRIC_LAMBDA_ERROR)
        # 回應 200 OK 避免 Telegram 重試訊息
        # 錯誤已經記錄在日誌中，可以稍後排查
        return create_response(200, {'status': 'error', 'message': 'Internal error occurred'})
