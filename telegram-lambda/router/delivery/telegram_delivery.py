"""
Telegram Message Delivery Implementation
"""
import sys
import os
from typing import Optional, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from router.delivery.base import MessageDelivery, DeliveryResult
from telegram_client import send_message
from utils.logger import get_logger

logger = get_logger(__name__)


class TelegramDelivery(MessageDelivery):
    """Telegram 訊息傳送實作"""
    
    def __init__(self):
        """初始化 Telegram 傳送器"""
        self.channel = 'telegram'
        logger.info("TelegramDelivery initialized")
    
    def get_channel_name(self) -> str:
        """取得頻道名稱"""
        return self.channel
    
    def deliver(
        self,
        user_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> DeliveryResult:
        """
        傳送訊息到 Telegram
        
        Args:
            user_id: Telegram chat_id (字串格式，可能包含 "tg:" 前綴)
            message: 要傳送的訊息內容
            context: 額外的上下文資訊 (可包含 parse_mode 等)
            
        Returns:
            DeliveryResult: 傳送結果
        """
        # 移除 "tg:" 前綴（如果存在）
        clean_user_id = user_id.replace('tg:', '') if user_id.startswith('tg:') else user_id
        
        # 驗證 user_id
        if not self.validate_user_id(clean_user_id):
            error_msg = f"Invalid user_id: {user_id}"
            logger.error(
                error_msg,
                extra={
                    'event_type': 'telegram_delivery_invalid_user_id',
                    'user_id': user_id,
                    'clean_user_id': clean_user_id
                }
            )
            return DeliveryResult(
                success=False,
                channel=self.channel,
                user_id=user_id,
                error=error_msg
            )
        
        # 轉換 user_id 為整數 (Telegram chat_id)
        try:
            chat_id = int(clean_user_id)
        except ValueError:
            error_msg = f"user_id must be numeric for Telegram: {user_id}"
            logger.error(
                error_msg,
                extra={
                    'event_type': 'telegram_delivery_invalid_chat_id',
                    'user_id': user_id,
                    'clean_user_id': clean_user_id
                }
            )
            return DeliveryResult(
                success=False,
                channel=self.channel,
                user_id=user_id,
                error=error_msg
            )
        
        # 取得 parse_mode (預設 None，避免特殊字符問題)
        # 可以通過 context 覆蓋為 'Markdown' 或 'HTML'
        parse_mode = None
        if context and 'parse_mode' in context:
            parse_mode = context['parse_mode']
        
        # 記錄傳送嘗試
        logger.info(
            "Attempting to deliver message to Telegram",
            extra={
                'event_type': 'telegram_delivery_attempt',
                'chat_id': chat_id,
                'message_length': len(message),
                'parse_mode': parse_mode
            }
        )
        
        # 使用現有的 telegram_client.send_message()
        success = send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=parse_mode
        )
        
        if success:
            logger.info(
                "Message delivered successfully to Telegram",
                extra={
                    'event_type': 'telegram_delivery_success',
                    'chat_id': chat_id,
                    'message_length': len(message)
                }
            )
            return DeliveryResult(
                success=True,
                channel=self.channel,
                user_id=user_id,
                metadata={
                    'chat_id': chat_id,
                    'message_length': len(message),
                    'parse_mode': parse_mode
                }
            )
        else:
            error_msg = "Failed to send message via telegram_client"
            logger.error(
                error_msg,
                extra={
                    'event_type': 'telegram_delivery_failed',
                    'chat_id': chat_id
                }
            )
            return DeliveryResult(
                success=False,
                channel=self.channel,
                user_id=user_id,
                error=error_msg
            )
    
    def validate_user_id(self, user_id: str) -> bool:
        """
        驗證 Telegram user_id 格式
        
        Args:
            user_id: 使用者 ID
            
        Returns:
            bool: 是否有效
        """
        if not super().validate_user_id(user_id):
            return False
        
        # Telegram chat_id 必須是數字
        try:
            int(user_id)
            return True
        except ValueError:
            return False
