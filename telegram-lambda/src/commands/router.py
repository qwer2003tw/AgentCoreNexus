"""
Command Router - 指令路由器
"""
from typing import List, Optional
from telegram import Update
from commands.base import CommandHandler
from utils.logger import get_logger

logger = get_logger(__name__)


class CommandRouter:
    """
    指令路由器
    
    負責管理所有指令處理器，並根據訊息內容路由到對應的處理器
    """
    
    def __init__(self):
        """初始化路由器"""
        self._handlers: List[CommandHandler] = []
    
    def register(self, handler: CommandHandler) -> None:
        """
        註冊指令處理器
        
        Args:
            handler: CommandHandler 實例
            
        Example:
            router = CommandRouter()
            router.register(DebugCommandHandler())
        """
        if not isinstance(handler, CommandHandler):
            raise TypeError(
                f"Handler must be an instance of CommandHandler, "
                f"got {type(handler).__name__}"
            )
        
        self._handlers.append(handler)
        
        logger.info(
            f"Registered command handler: {handler.get_command_name()}",
            extra={
                'handler_name': handler.get_command_name(),
                'event_type': 'handler_registered'
            }
        )
    
    def route(self, update: Update, event: dict) -> bool:
        """
        路由訊息到對應的處理器
        
        Args:
            update: Telegram Update 物件
            event: API Gateway event
            
        Returns:
            bool: True 如果訊息被成功處理
            
        Note:
            - 會按照註冊順序嘗試每個處理器
            - 第一個能處理（can_handle 返回 True）的處理器會執行
            - 如果沒有處理器能處理，返回 False
        """
        # 取得訊息文字
        message = update.message or update.edited_message
        if not message or not message.text:
            logger.debug(
                "No text message to route",
                extra={'event_type': 'route_no_text'}
            )
            return False
        
        text = message.text
        chat_id = message.chat_id
        username = message.from_user.username if message.from_user else None
        
        logger.info(
            f"Routing message: {text[:50]}...",
            extra={
                'chat_id': chat_id,
                'username': username,
                'message_text': text,
                'event_type': 'route_start'
            }
        )
        
        # 嘗試每個處理器
        for handler in self._handlers:
            try:
                if handler.can_handle(text):
                    handler_name = handler.get_command_name()
                    
                    logger.info(
                        f"Handler matched: {handler_name}",
                        extra={
                            'handler_name': handler_name,
                            'chat_id': chat_id,
                            'event_type': 'handler_matched'
                        }
                    )
                    
                    # 執行處理器
                    success = handler.handle(update, event)
                    
                    if success:
                        logger.info(
                            f"Handler executed successfully: {handler_name}",
                            extra={
                                'handler_name': handler_name,
                                'chat_id': chat_id,
                                'event_type': 'handler_success'
                            }
                        )
                    else:
                        logger.warning(
                            f"Handler execution failed: {handler_name}",
                            extra={
                                'handler_name': handler_name,
                                'chat_id': chat_id,
                                'event_type': 'handler_failed'
                            }
                        )
                    
                    return success
                    
            except Exception as e:
                logger.error(
                    f"Error in handler {handler.get_command_name()}: {str(e)}",
                    extra={
                        'handler_name': handler.get_command_name(),
                        'chat_id': chat_id,
                        'event_type': 'handler_error'
                    },
                    exc_info=True
                )
                # 繼續嘗試下一個處理器
                continue
        
        # 沒有處理器能處理此訊息
        logger.debug(
            "No handler matched for message",
            extra={
                'chat_id': chat_id,
                'message_text': text,
                'event_type': 'route_no_match'
            }
        )
        return False
    
    def get_registered_handlers(self) -> List[CommandHandler]:
        """
        取得所有已註冊的處理器
        
        Returns:
            List[CommandHandler]: 處理器列表
        """
        return self._handlers.copy()
    
    def clear(self) -> None:
        """清除所有已註冊的處理器（主要用於測試）"""
        self._handlers.clear()
        logger.debug("All handlers cleared", extra={'event_type': 'handlers_cleared'})
