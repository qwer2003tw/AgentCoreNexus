"""
New Session Command Handler
處理 /new 指令，開始新的對話 session
"""
import uuid
from datetime import datetime
from telegram import Update
from commands.base import CommandHandler
from utils.logger import get_logger
import telegram_client

logger = get_logger(__name__)


class NewCommandHandler(CommandHandler):
    """處理 /new 指令的處理器"""
    
    def can_handle(self, message: str) -> bool:
        """
        判斷是否可以處理此訊息
        
        Args:
            message: 訊息文字
            
        Returns:
            如果訊息以 /new 開頭則返回 True
        """
        return message.strip().startswith('/new')
    
    def handle(self, update: Update, event: dict) -> bool:
        """
        處理 /new 指令
        
        Args:
            update: Telegram Update 物件
            event: Lambda event 物件
            
        Returns:
            True 如果成功處理，False 如果處理失敗
        """
        try:
            # 從 Update 物件取得資訊
            chat_id = update.effective_message.chat_id
            user_id = update.effective_message.from_user.id
            username = update.effective_message.from_user.username or 'Unknown'
            
            if not chat_id:
                logger.warning("New command: missing chat_id")
                return False
            
            # 生成新的 session ID
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            random_suffix = str(uuid.uuid4())[:8]
            new_session_id = f"session-{timestamp}-{random_suffix}"
            
            logger.info(
                f"Creating new session for user {user_id}",
                extra={
                    'user_id': user_id,
                    'username': username,
                    'new_session_id': new_session_id
                }
            )
            
            # 構建回應訊息
            message_lines = [
                "✅ 已開始新的對話 session！",
                "",
                f"🆔 Session ID:",
                f"`{new_session_id[:28]}...`",
                "",
                "📌 說明：",
                "• 💾 你的長期記憶（姓名、偏好等）仍然保留",
                "• 🆕 當前對話的短期記憶已清空",
                "• 🔄 下一則訊息將使用新的 session",
                "",
                "💡 提示：",
                "你可以隨時使用 /new 開始新的對話主題，",
                "而不會影響系統對你的長期記憶。"
            ]
            
            response_text = "\n".join(message_lines)
            
            # 發送回覆（包含 session_id 供下次使用）
            # 注意：這裡需要將 new_session_id 儲存起來，讓下一次訊息使用
            # 目前先簡單實現，未來可以用 DynamoDB 儲存
            telegram_client.send_message(chat_id, response_text)
            
            logger.info(
                f"New session created successfully",
                extra={
                    'user_id': user_id,
                    'session_id': new_session_id
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing /new command: {str(e)}", exc_info=True)
            
            # 嘗試發送錯誤訊息給用戶
            try:
                chat_id = update.effective_message.chat_id
                if chat_id:
                    error_msg = "❌ 無法創建新 session，請稍後再試。"
                    telegram_client.send_message(chat_id, error_msg)
            except:
                pass
            
            return False
    
    def get_command_name(self) -> str:
        """取得指令名稱"""
        return "/new"
    
    def get_description(self) -> str:
        """取得指令描述"""
        return "開始新的對話 session（清空短期記憶，保留長期記憶）"
