"""
Response Router - Main Lambda handler for routing AI responses back to users

This Lambda function:
1. Receives message.completed events from EventBridge
2. Extracts routing information (channel, user_id)
3. Formats the response for the target channel
4. Delivers the message to the user
5. Publishes metrics for monitoring
"""
import json
import os
import time
from typing import Dict, Any, Optional
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from router.delivery import TelegramDelivery, DeliveryResult
from router.formatters import TelegramFormatter
from utils.logger import get_logger

logger = get_logger(__name__)

# Simple metric publishing function (can be enhanced later)
def publish_metric(metric_name: str, value: float, unit: str) -> None:
    """Publish a CloudWatch metric (simplified implementation)"""
    logger.info(
        f"Metric: {metric_name} = {value} {unit}",
        extra={
            'metric_name': metric_name,
            'value': value,
            'unit': unit
        }
    )

# Delivery implementations by channel
DELIVERY_MAP = {
    'telegram': TelegramDelivery,
    # Future channels:
    # 'discord': DiscordDelivery,
    # 'slack': SlackDelivery,
    # 'web': WebDelivery,
}

# Formatter implementations by channel
FORMATTER_MAP = {
    'telegram': TelegramFormatter,
    # Future channels:
    # 'discord': DiscordFormatter,
    # 'slack': SlackFormatter,
    # 'web': WebFormatter,
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda 主處理器 - 處理 message.completed 事件
    
    Args:
        event: EventBridge 事件
        context: Lambda context
        
    Returns:
        Dict: 處理結果
    """
    start_time = time.time()
    
    logger.info(
        "Response router invoked",
        extra={
            'event_type': 'router_invoked',
            'event_source': event.get('source'),
            'detail_type': event.get('detail-type')
        }
    )
    
    try:
        # 解析事件
        detail = event.get('detail', {})
        
        # 驗證必要欄位
        required_fields = ['messageId', 'channel', 'user', 'response']
        missing_fields = [f for f in required_fields if f not in detail]
        
        if missing_fields:
            error_msg = f"Missing required fields: {missing_fields}"
            logger.error(
                error_msg,
                extra={
                    'event_type': 'router_invalid_event',
                    'missing_fields': missing_fields
                }
            )
            publish_metric('RouterInvalidEvent', 1, 'Count')
            return {
                'statusCode': 400,
                'body': json.dumps({'error': error_msg})
            }
        
        # 提取訊息資訊
        message_id = detail['messageId']
        channel = detail['channel']
        user_info = detail['user']
        user_id = user_info.get('id', user_info.get('userId'))
        response_content = detail['response']
        metadata = detail.get('metadata', {})
        
        logger.info(
            "Processing completed message",
            extra={
                'event_type': 'router_processing',
                'message_id': message_id,
                'channel': channel,
                'user_id': user_id,
                'response_length': len(response_content) if isinstance(response_content, str) else 0
            }
        )
        
        # 路由訊息到對應頻道
        result = route_message(
            channel=channel,
            user_id=user_id,
            content=response_content,
            metadata=metadata
        )
        
        # 計算處理時間
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 記錄結果
        if result.success:
            logger.info(
                "Message routed successfully",
                extra={
                    'event_type': 'router_success',
                    'message_id': message_id,
                    'channel': channel,
                    'user_id': user_id,
                    'duration_ms': duration_ms
                }
            )
            publish_metric('RouterSuccess', 1, 'Count')
            publish_metric('RouterDuration', duration_ms, 'Milliseconds')
            publish_metric(f'Router{channel.capitalize()}Success', 1, 'Count')
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'messageId': message_id,
                    'channel': channel,
                    'userId': user_id,
                    'durationMs': duration_ms
                })
            }
        else:
            logger.error(
                "Message routing failed",
                extra={
                    'event_type': 'router_failed',
                    'message_id': message_id,
                    'channel': channel,
                    'user_id': user_id,
                    'error': result.error,
                    'duration_ms': duration_ms
                }
            )
            publish_metric('RouterFailure', 1, 'Count')
            publish_metric(f'Router{channel.capitalize()}Failure', 1, 'Count')
            
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'messageId': message_id,
                    'error': result.error
                })
            }
    
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(
            f"Router handler error: {str(e)}",
            extra={
                'event_type': 'router_error',
                'duration_ms': duration_ms
            },
            exc_info=True
        )
        publish_metric('RouterError', 1, 'Count')
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }


def route_message(
    channel: str,
    user_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> DeliveryResult:
    """
    路由訊息到指定頻道
    
    Args:
        channel: 頻道名稱 (telegram, discord, slack, web)
        user_id: 使用者 ID
        content: 訊息內容
        metadata: 額外的元資料
        
    Returns:
        DeliveryResult: 傳送結果
    """
    # 檢查頻道是否支援
    if channel not in DELIVERY_MAP:
        error_msg = f"Unsupported channel: {channel}"
        logger.error(
            error_msg,
            extra={
                'event_type': 'router_unsupported_channel',
                'channel': channel,
                'supported_channels': list(DELIVERY_MAP.keys())
            }
        )
        publish_metric('RouterUnsupportedChannel', 1, 'Count')
        
        return DeliveryResult(
            success=False,
            channel=channel,
            user_id=user_id,
            error=error_msg
        )
    
    try:
        # 取得對應的 formatter 和 delivery
        formatter_class = FORMATTER_MAP.get(channel, TelegramFormatter)
        delivery_class = DELIVERY_MAP[channel]
        
        # 建立實例
        formatter = formatter_class()
        delivery = delivery_class()
        
        logger.info(
            "Formatting message",
            extra={
                'event_type': 'router_formatting',
                'channel': channel,
                'formatter': formatter_class.__name__,
                'content_length': len(content)
            }
        )
        
        # 格式化訊息
        formatted_content = formatter.format(content, metadata)
        
        logger.info(
            "Delivering message",
            extra={
                'event_type': 'router_delivering',
                'channel': channel,
                'delivery': delivery_class.__name__,
                'formatted_length': len(formatted_content)
            }
        )
        
        # 準備 context（包含 parse_mode 等）
        context = {
            'parse_mode': formatter.get_parse_mode()
        }
        if metadata:
            context.update(metadata)
        
        # 傳送訊息
        result = delivery.deliver(
            user_id=user_id,
            message=formatted_content,
            context=context
        )
        
        return result
    
    except Exception as e:
        error_msg = f"Routing error: {str(e)}"
        logger.error(
            error_msg,
            extra={
                'event_type': 'router_exception',
                'channel': channel,
                'user_id': user_id
            },
            exc_info=True
        )
        
        return DeliveryResult(
            success=False,
            channel=channel,
            user_id=user_id,
            error=error_msg
        )


def get_delivery_for_channel(channel: str):
    """
    取得指定頻道的 Delivery 實例
    
    Args:
        channel: 頻道名稱
        
    Returns:
        MessageDelivery: Delivery 實例，或 None
    """
    delivery_class = DELIVERY_MAP.get(channel)
    if delivery_class:
        return delivery_class()
    return None


def get_formatter_for_channel(channel: str):
    """
    取得指定頻道的 Formatter 實例
    
    Args:
        channel: 頻道名稱
        
    Returns:
        Formatter: Formatter 實例
    """
    formatter_class = FORMATTER_MAP.get(channel, TelegramFormatter)
    return formatter_class()


def get_supported_channels():
    """
    取得支援的頻道列表
    
    Returns:
        list: 支援的頻道名稱列表
    """
    return list(DELIVERY_MAP.keys())
