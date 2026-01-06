"""
Telegram Client Module v2 - 使用 python-telegram-bot
"""
import os
import asyncio
import json
import copy
from typing import Optional, List
from telegram import Bot
from telegram.error import TelegramError
from telegram.constants import ParseMode
from secrets_manager import get_telegram_bot_token
from utils.logger import get_logger

logger = get_logger(__name__)

# Telegram API 限制
MAX_MESSAGE_LENGTH = 4096

# 敏感欄位配置 - 需要遮蔽的欄位路徑
SENSITIVE_FIELDS = [
    ('headers', 'X-Telegram-Bot-Api-Secret-Token'),
    ('multiValueHeaders', 'X-Telegram-Bot-Api-Secret-Token'),
    ('requestContext', 'accountId'),
]


def get_bot_token() -> str:
    """
    獲取 Bot Token (從 Secrets Manager)
    
    Returns:
        str: Bot Token
    """
    token = get_telegram_bot_token()
    if not token:
        logger.error("Failed to retrieve bot token from Secrets Manager")
        return ''
    return token


def send_message(chat_id: int, text: str, parse_mode: str = 'Markdown') -> bool:
    """
    發送訊息到 Telegram (同步包裝)
    
    Args:
        chat_id: Telegram chat ID
        text: 訊息內容
        parse_mode: 解析模式 (Markdown, HTML, 或 None)
        
    Returns:
        bool: True 如果成功發送
    """
    try:
        # 在 Lambda 中執行 async 函數
        return asyncio.run(_send_message_async(chat_id, text, parse_mode))
    except Exception as e:
        logger.error(
            f"Failed to send message: {str(e)}",
            extra={
                'chat_id': chat_id,
                'event_type': 'telegram_send_error'
            },
            exc_info=True
        )
        return False


async def _send_message_async(
    chat_id: int,
    text: str,
    parse_mode: str = 'Markdown'
) -> bool:
    """
    異步發送訊息到 Telegram
    
    Args:
        chat_id: Telegram chat ID
        text: 訊息內容
        parse_mode: 解析模式
        
    Returns:
        bool: True 如果成功發送
    """
    bot_token = get_bot_token()
    
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return False
    
    try:
        bot = Bot(token=bot_token)
        
        # 處理 parse_mode
        telegram_parse_mode = None
        if parse_mode == 'Markdown':
            telegram_parse_mode = ParseMode.MARKDOWN_V2
        elif parse_mode == 'HTML':
            telegram_parse_mode = ParseMode.HTML
        
        # 如果訊息太長，分段發送
        if len(text) > MAX_MESSAGE_LENGTH:
            return await _send_long_message_async(bot, chat_id, text, telegram_parse_mode)
        
        # 發送訊息
        message = await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=telegram_parse_mode
        )
        
        logger.info(
            "Message sent successfully",
            extra={
                'chat_id': chat_id,
                'message_id': message.message_id,
                'event_type': 'telegram_send_success'
            }
        )
        return True
        
    except TelegramError as e:
        logger.error(
            f"Telegram error: {str(e)}",
            extra={
                'chat_id': chat_id,
                'error_type': type(e).__name__,
                'event_type': 'telegram_api_error'
            }
        )
        return False


def send_long_message(chat_id: int, text: str, parse_mode: str = 'Markdown') -> bool:
    """
    發送長訊息（自動分段）- 同步包裝
    
    Args:
        chat_id: Telegram chat ID
        text: 訊息內容
        parse_mode: 解析模式
        
    Returns:
        bool: True 如果所有分段都成功發送
    """
    try:
        bot_token = get_bot_token()
        if not bot_token:
            return False
        
        bot = Bot(token=bot_token)
        
        # 處理 parse_mode
        telegram_parse_mode = None
        if parse_mode == 'Markdown':
            telegram_parse_mode = ParseMode.MARKDOWN_V2
        elif parse_mode == 'HTML':
            telegram_parse_mode = ParseMode.HTML
        
        return asyncio.run(_send_long_message_async(bot, chat_id, text, telegram_parse_mode))
    except Exception as e:
        logger.error(f"Failed to send long message: {str(e)}", exc_info=True)
        return False


async def _send_long_message_async(
    bot: Bot,
    chat_id: int,
    text: str,
    parse_mode: Optional[str]
) -> bool:
    """
    發送長訊息（自動分段）
    
    Args:
        bot: Bot 實例
        chat_id: Telegram chat ID
        text: 訊息內容
        parse_mode: 解析模式
        
    Returns:
        bool: True 如果所有分段都成功發送
    """
    chunks = _split_message(text, MAX_MESSAGE_LENGTH)
    
    logger.info(
        f"Sending long message in {len(chunks)} chunks",
        extra={
            'chat_id': chat_id,
            'total_length': len(text),
            'chunks': len(chunks),
            'event_type': 'long_message_split'
        }
    )
    
    all_success = True
    for i, chunk in enumerate(chunks, 1):
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"📄 Part {i}/{len(chunks)}\n\n{chunk}",
                parse_mode=parse_mode
            )
        except TelegramError as e:
            all_success = False
            logger.warning(
                f"Failed to send chunk {i}/{len(chunks)}: {str(e)}",
                extra={
                    'chat_id': chat_id,
                    'chunk_index': i,
                    'event_type': 'chunk_send_failed'
                }
            )
    
    return all_success


def _split_message(text: str, max_length: int) -> List[str]:
    """
    將長文字分割成多個片段
    
    Args:
        text: 原始文字
        max_length: 每段最大長度
        
    Returns:
        List[str]: 分割後的文字片段
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_pos = 0
    
    while current_pos < len(text):
        end_pos = current_pos + max_length
        
        if end_pos < len(text):
            newline_pos = text.rfind('\n', current_pos, end_pos)
            if newline_pos > current_pos:
                end_pos = newline_pos + 1
        
        chunk = text[current_pos:end_pos]
        chunks.append(chunk)
        current_pos = end_pos
    
    return chunks


def redact_sensitive_data(data: dict, sensitive_paths: List[tuple]) -> dict:
    """
    遮蔽敏感資料 - Deep copy 並遮蔽指定路徑的值
    
    Args:
        data: 原始資料字典
        sensitive_paths: 需要遮蔽的路徑列表，每個路徑是一個 tuple
        
    Returns:
        dict: 已遮蔽敏感資料的副本
        
    Example:
        >>> data = {'headers': {'X-Telegram-Bot-Api-Secret-Token': 'secret123'}}
        >>> paths = [('headers', 'X-Telegram-Bot-Api-Secret-Token')]
        >>> redact_sensitive_data(data, paths)
        {'headers': {'X-Telegram-Bot-Api-Secret-Token': '[REDACTED]'}}
    """
    redacted_data = copy.deepcopy(data)
    
    for path in sensitive_paths:
        _redact_path(redacted_data, path)
    
    return redacted_data


def _redact_path(data: dict, path: tuple) -> None:
    """
    遞迴遮蔽指定路徑的值
    
    Args:
        data: 資料字典 (會被直接修改)
        path: 路徑 tuple，例如 ('headers', 'X-Telegram-Bot-Api-Secret-Token')
        
    Note:
        此函數會直接修改傳入的 data，支援單一值和列表值
    """
    if not path or not isinstance(data, dict):
        return
    
    key = path[0]
    
    # 如果是最後一個 key
    if len(path) == 1:
        if key in data:
            # 如果值是列表，遮蔽列表中的所有元素
            if isinstance(data[key], list):
                data[key] = ['[REDACTED]'] * len(data[key])
            else:
                data[key] = '[REDACTED]'
    else:
        # 遞迴處理下一層
        if key in data and isinstance(data[key], dict):
            _redact_path(data[key], path[1:])


def send_permission_denied(chat_id: int, required_permission: str) -> bool:
    """
    發送權限不足訊息
    
    Args:
        chat_id: Telegram chat ID
        required_permission: 需要的權限等級 ('ALLOWLIST' 或 'ADMIN')
        
    Returns:
        bool: True 如果成功發送
    """
    try:
        if required_permission == 'ADMIN':
            message = "❌ **權限不足**\n\n此指令需要管理員權限。"
        else:  # ALLOWLIST
            message = "❌ **權限不足**\n\n您沒有使用此 Bot 的權限。"
        
        logger.info(
            "Sending permission denied message",
            extra={
                'chat_id': chat_id,
                'required_permission': required_permission,
                'event_type': 'permission_denied_message'
            }
        )
        
        return send_message(chat_id, message)
        
    except Exception as e:
        logger.error(
            f"Failed to send permission denied message: {str(e)}",
            extra={
                'chat_id': chat_id,
                'required_permission': required_permission,
                'event_type': 'permission_denied_message_error'
            },
            exc_info=True
        )
        return False


def send_debug_info(chat_id: int, event: dict) -> bool:
    """
    發送除錯資訊（已遮蔽敏感欄位）
    
    Args:
        chat_id: Telegram chat ID
        event: API Gateway event
        
    Returns:
        bool: True 如果成功發送
    """
    try:
        logger.info(
            "Starting debug info redaction",
            extra={
                'chat_id': chat_id,
                'event_type': 'debug_redaction_start',
                'sensitive_fields_count': len(SENSITIVE_FIELDS)
            }
        )
        
        # 遮蔽敏感資料
        redacted_event = redact_sensitive_data(event, SENSITIVE_FIELDS)
        
        # 檢查遮蔽是否成功
        redaction_applied = []
        for path in SENSITIVE_FIELDS:
            field_name = '.'.join(path)
            # 檢查欄位是否存在且被遮蔽
            try:
                current = event
                for key in path:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        current = None
                        break
                
                if current is not None:
                    redaction_applied.append(field_name)
            except:
                pass
        
        logger.info(
            "Debug info redaction completed",
            extra={
                'chat_id': chat_id,
                'event_type': 'debug_redaction_complete',
                'redacted_fields': redaction_applied,
                'redacted_count': len(redaction_applied)
            }
        )
        
        # 格式化除錯訊息
        debug_text = "🔍 **Debug Information**\n"
        debug_text += "_Note: Sensitive fields have been redacted_\n\n"
        debug_text += "```json\n"
        debug_text += json.dumps(redacted_event, indent=2, ensure_ascii=False)
        debug_text += "\n```"
        
        logger.debug(
            "Debug message prepared for sending",
            extra={
                'chat_id': chat_id,
                'message_length': len(debug_text),
                'event_type': 'debug_message_prepared'
            }
        )
        
        return send_message(chat_id, debug_text)
        
    except Exception as e:
        logger.error(
            f"Failed to format debug info: {str(e)}",
            extra={
                'chat_id': chat_id,
                'event_type': 'debug_format_error'
            },
            exc_info=True
        )
        return False
