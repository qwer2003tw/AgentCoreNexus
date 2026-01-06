"""
Admin Command Handler - 管理員指令處理器
"""
from telegram import Update
from commands.base import CommandHandler
from commands.decorators import require_admin
import telegram_client
from utils.logger import get_logger

logger = get_logger(__name__)


@require_admin
class AdminCommandHandler(CommandHandler):
    """
    管理員指令處理器
    
    處理 /admin 指令，用於管理員操作
    
    權限：需要管理員權限 (ADMIN)
    """
    
    def can_handle(self, text: str) -> bool:
        """
        判斷是否為 /admin 指令
        
        Args:
            text: 訊息文字內容
            
        Returns:
            bool: True 如果是 /admin 或 /admin 開頭的指令
        """
        if not text:
            return False
        
        stripped = text.strip()
        return stripped == '/admin' or stripped.startswith('/admin ')
    
    def handle(self, update: Update, event: dict) -> bool:
        """
        處理 /admin 指令
        
        Args:
            update: Telegram Update 物件
            event: API Gateway event（完整的請求資料）
            
        Returns:
            bool: True 如果成功發送訊息
        """
        message = update.message or update.edited_message
        if not message:
            logger.warning(
                "No message in update for admin command",
                extra={'event_type': 'admin_no_message'}
            )
            return False
        
        chat_id = message.chat_id
        username = message.from_user.username if message.from_user else None
        command_text = message.text or message.caption or ''
        
        logger.info(
            "Processing admin command",
            extra={
                'chat_id': chat_id,
                'username': username,
                'command': command_text.strip(),
                'event_type': 'admin_command'
            }
        )
        
        # 發送測試訊息
        success = telegram_client.send_message(chat_id, "Test")
        
        if success:
            logger.info(
                "Admin command response sent successfully",
                extra={
                    'chat_id': chat_id,
                    'event_type': 'admin_response_sent'
                }
            )
            return True
        else:
            logger.warning(
                "Failed to send admin command response",
                extra={
                    'chat_id': chat_id,
                    'event_type': 'admin_response_failed'
                }
            )
            return False
    
    def get_command_name(self) -> str:
        """取得指令名稱"""
        return "AdminCommand"
    
    def get_description(self) -> str:
        """取得指令描述"""
        return "管理員指令（需要管理員權限）"
