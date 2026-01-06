"""
EventBridge Processor Entry Point
處理來自 EventBridge 的標準化訊息事件
"""
import json
import os
from typing import Dict, Any, Optional
import boto3
from agents.conversation_agent import ConversationAgent
from services.memory_service import MemoryService
from utils.logger import get_logger

logger = get_logger(__name__)

# 初始化服務
conversation_agent = ConversationAgent()
memory_service = MemoryService()

# EventBridge 客戶端
_eventbridge_client = None

def get_eventbridge_client():
    """取得 EventBridge 客戶端單例"""
    global _eventbridge_client
    if _eventbridge_client is None:
        _eventbridge_client = boto3.client('events')
    return _eventbridge_client


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda 入口函數 - 處理 EventBridge 事件
    
    支援兩種觸發來源：
    1. EventBridge: event['detail'] 包含標準化訊息
    2. SQS (向後兼容): event['Records'] 包含 SQS 訊息
    
    Args:
        event: EventBridge 事件或 SQS 事件
        context: Lambda context
        
    Returns:
        處理結果
    """
    logger.info(
        "Processor invoked",
        extra={
            'source': event.get('source', 'unknown'),
            'detail_type': event.get('detail-type', 'unknown')
        }
    )
    
    try:
        # 判斷事件來源
        if 'Records' in event:
            # SQS 事件（向後兼容）
            logger.info("Processing SQS event (legacy mode)")
            return process_sqs_event(event, context)
        elif 'detail' in event:
            # EventBridge 事件（新架構）
            logger.info("Processing EventBridge event")
            return process_eventbridge_event(event, context)
        else:
            logger.error("Unknown event format")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Unknown event format'})
            }
            
    except Exception as e:
        logger.error(f"Processor error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def process_eventbridge_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    處理 EventBridge 事件
    
    Args:
        event: EventBridge 事件
        context: Lambda context
        
    Returns:
        處理結果
    """
    detail = event.get('detail', {})
    
    # 驗證事件類型
    detail_type = event.get('detail-type', '')
    if detail_type != 'message.received':
        logger.warning(f"Unsupported detail-type: {detail_type}")
        return {'statusCode': 200, 'body': 'Event ignored'}
    
    # 提取標準化訊息
    normalized_message = detail
    message_id = normalized_message.get('messageId', 'unknown')
    channel_type = normalized_message.get('channel', {}).get('type', 'unknown')
    
    logger.info(
        f"Processing message from {channel_type}",
        extra={
            'message_id': message_id,
            'channel': channel_type
        }
    )
    
    # 處理訊息
    result = process_normalized_message(normalized_message)
    
    # 發布處理完成事件
    if result.get('success'):
        publish_completion_event(normalized_message, result)
    else:
        publish_failure_event(normalized_message, result)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message_id': message_id,
            'status': 'processed' if result.get('success') else 'failed'
        })
    }


def process_sqs_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    處理 SQS 事件（向後兼容現有系統）
    
    Args:
        event: SQS 事件
        context: Lambda context
        
    Returns:
        處理結果
    """
    records = event.get('Records', [])
    
    for record in records:
        try:
            body = json.loads(record.get('body', '{}'))
            
            # 從 Telegram 原始格式提取訊息
            message = body.get('message', {})
            from_user = message.get('from', {})
            text = message.get('text', '')
            
            if text:
                logger.info(f"Processing SQS message from Telegram user {from_user.get('id')}")
                
                # 使用現有的 Agent 處理
                response = conversation_agent.process_message(text)
                
                logger.info(
                    "SQS message processed",
                    extra={'user_id': from_user.get('id')}
                )
        except Exception as e:
            logger.error(f"Failed to process SQS record: {e}", exc_info=True)
    
    return {
        'statusCode': 200,
        'body': json.dumps({'processed': len(records)})
    }


def process_normalized_message(normalized: Dict[str, Any]) -> Dict[str, Any]:
    """
    處理標準化訊息
    
    Args:
        normalized: 標準化的訊息物件
        
    Returns:
        處理結果
    """
    try:
        # 提取訊息內容
        content = normalized.get('content', {})
        text = content.get('text', '')
        message_type = content.get('messageType', 'text')
        
        # 提取用戶資訊
        user = normalized.get('user', {})
        user_id = user.get('id', 'unknown')
        display_name = user.get('displayName', 'Unknown')
        
        # 提取上下文
        context_info = normalized.get('context', {})
        session_id = context_info.get('sessionId', user_id)
        
        logger.info(
            f"Processing {message_type} message from {display_name}",
            extra={
                'user_id': user_id,
                'session_id': session_id,
                'message_type': message_type
            }
        )
        
        # 目前只處理文字訊息
        if message_type == 'text' and text:
            # 使用 ConversationAgent 處理
            response = conversation_agent.process_message(text)
            
            logger.info(
                "Message processed successfully",
                extra={'user_id': user_id}
            )
            
            return {
                'success': True,
                'response': response,
                'user_id': user_id,
                'session_id': session_id
            }
        else:
            logger.warning(f"Unsupported message type: {message_type}")
            return {
                'success': False,
                'error': f"Unsupported message type: {message_type}",
                'user_id': user_id
            }
            
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'user_id': normalized.get('user', {}).get('id', 'unknown')
        }


def publish_completion_event(original_message: Dict[str, Any], result: Dict[str, Any]) -> bool:
    """
    發布訊息處理完成事件到 EventBridge
    
    Args:
        original_message: 原始標準化訊息
        result: 處理結果
        
    Returns:
        發布是否成功
    """
    event_bus_name = os.getenv('EVENT_BUS_NAME')
    if not event_bus_name:
        logger.warning("EVENT_BUS_NAME not configured, skipping completion event")
        return False
    
    try:
        evb = get_eventbridge_client()
        
        completion_event = {
            'original': original_message,
            'response': result.get('response', ''),
            'channel': original_message.get('channel', {}).get('type', 'unknown'),
            'user_id': result.get('user_id', 'unknown'),
            'session_id': result.get('session_id', 'unknown')
        }
        
        response = evb.put_events(
            Entries=[{
                'Source': 'agent-processor',
                'DetailType': 'message.completed',
                'Detail': json.dumps(completion_event),
                'EventBusName': event_bus_name
            }]
        )
        
        if response.get('FailedEntryCount', 0) > 0:
            logger.error(f"Failed to publish completion event: {response}")
            return False
        
        logger.info(
            "Completion event published",
            extra={
                'message_id': original_message.get('messageId'),
                'event_type': 'message.completed'
            }
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish completion event: {e}", exc_info=True)
        return False


def publish_failure_event(original_message: Dict[str, Any], result: Dict[str, Any]) -> bool:
    """
    發布訊息處理失敗事件到 EventBridge
    
    Args:
        original_message: 原始標準化訊息
        result: 處理結果（包含錯誤資訊）
        
    Returns:
        發布是否成功
    """
    event_bus_name = os.getenv('EVENT_BUS_NAME')
    if not event_bus_name:
        logger.warning("EVENT_BUS_NAME not configured, skipping failure event")
        return False
    
    try:
        evb = get_eventbridge_client()
        
        failure_event = {
            'original': original_message,
            'error': result.get('error', 'Unknown error'),
            'channel': original_message.get('channel', {}).get('type', 'unknown'),
            'user_id': result.get('user_id', 'unknown')
        }
        
        response = evb.put_events(
            Entries=[{
                'Source': 'agent-processor',
                'DetailType': 'message.failed',
                'Detail': json.dumps(failure_event),
                'EventBusName': event_bus_name
            }]
        )
        
        if response.get('FailedEntryCount', 0) > 0:
            logger.error(f"Failed to publish failure event: {response}")
            return False
        
        logger.info(
            "Failure event published",
            extra={
                'message_id': original_message.get('messageId'),
                'event_type': 'message.failed'
            }
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish failure event: {e}", exc_info=True)
        return False
