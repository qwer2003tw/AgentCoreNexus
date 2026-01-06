"""
Info Command Handler

處理 /info 指令，顯示系統部署資訊。
"""

import os
import boto3
import re
from datetime import datetime
from typing import Dict, Any, Optional
from telegram import Update
import telegram_client
from commands.base import CommandHandler
from utils.logger import get_logger

logger = get_logger(__name__)


def escape_markdown_v2(text: str) -> str:
    """
    轉義 MarkdownV2 特殊字符
    
    Args:
        text: 要轉義的文字
        
    Returns:
        轉義後的文字
    """
    # MarkdownV2 需要轉義的字符
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', text)


class InfoCommandHandler(CommandHandler):
    """處理 /info 指令的處理器"""
    
    def __init__(self):
        """初始化 InfoCommandHandler"""
        self.stack_name = os.environ.get('STACK_NAME', 'telegram-lambda')
        self.region = os.environ.get('AWS_REGION', 'us-west-2')
        self.cfn_client = boto3.client('cloudformation', region_name=self.region)
        
    def can_handle(self, message: str) -> bool:
        """
        判斷是否可以處理此訊息
        
        Args:
            message: 訊息文字
            
        Returns:
            如果訊息以 /info 開頭則返回 True
        """
        return message.strip().startswith('/info')
    
    def handle(self, update: Update, event: dict) -> bool:
        """
        處理 /info 指令
        
        Args:
            update: Telegram Update 物件
            event: Lambda event 物件
            
        Returns:
            True 如果成功處理，False 如果處理失敗
        """
        try:
            # 從 Update 物件取得 chat_id
            chat_id = update.effective_message.chat_id
            
            if not chat_id:
                logger.warning("Info command: missing chat_id")
                return False
            
            logger.info(f"Processing /info command for chat_id: {chat_id}")
            
            # 取得部署資訊
            info_text = self._get_deployment_info()
            
            # 發送回覆
            telegram_client.send_message(chat_id, info_text)
            
            logger.info(f"Info command processed successfully for chat_id: {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing /info command: {str(e)}", exc_info=True)
            
            # 嘗試發送錯誤訊息給用戶
            try:
                chat_id = update.effective_message.chat_id
                if chat_id:
                    error_msg = "❌ 無法取得系統資訊，請稍後再試。"
                    telegram_client.send_message(chat_id, error_msg)
            except:
                pass
            
            return False
    
    def _get_deployment_info(self) -> str:
        """
        取得部署資訊
        
        Returns:
            格式化的部署資訊文字
        """
        try:
            # 查詢 CloudFormation Stack
            response = self.cfn_client.describe_stacks(
                StackName=self.stack_name
            )
            
            if not response.get('Stacks'):
                return self._format_error_message("找不到 Stack 資訊")
            
            stack = response['Stacks'][0]
            
            # 取得資訊
            last_updated = stack.get('LastUpdatedTime') or stack.get('CreationTime')
            stack_status = stack.get('StackStatus', 'UNKNOWN')
            stack_name = stack.get('StackName', self.stack_name)
            
            # 格式化時間（轉換為 UTC 字串）
            if last_updated:
                # last_updated 是 datetime 物件
                time_str = last_updated.strftime('%Y-%m-%d %H:%M:%S UTC')
            else:
                time_str = 'Unknown'
            
            # 取得 Lambda 函數名稱（從環境變數）
            function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'telegram-lambda-receiver')
            
            # 格式化輸出（轉義特殊字符）
            info_lines = [
                "📊 系統資訊",
                "",
                f"🚀 最後部署時間：{escape_markdown_v2(time_str)}",
                f"📦 Stack 名稱：{escape_markdown_v2(stack_name)}",
                f"🌍 Region：{escape_markdown_v2(self.region)}",
                f"✅ Stack 狀態：{escape_markdown_v2(stack_status)}",
                f"⚙️ Lambda 函數：{escape_markdown_v2(function_name)}",
            ]
            
            return "\n".join(info_lines)
            
        except self.cfn_client.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"CloudFormation API error: {error_code} - {str(e)}")
            
            if error_code == 'AccessDenied':
                return self._format_error_message("權限不足，無法查詢部署資訊")
            elif error_code == 'ValidationError':
                return self._format_error_message(f"找不到 Stack: {self.stack_name}")
            else:
                return self._format_error_message(f"API 錯誤: {error_code}")
                
        except Exception as e:
            logger.error(f"Unexpected error getting deployment info: {str(e)}")
            return self._format_error_message("系統錯誤")
    
    def _format_error_message(self, error: str) -> str:
        """
        格式化錯誤訊息
        
        Args:
            error: 錯誤描述
            
        Returns:
            格式化的錯誤訊息
        """
        return f"❌ 無法取得部署資訊\n\n錯誤：{escape_markdown_v2(error)}"
    
    def get_command_name(self) -> str:
        """取得指令名稱"""
        return "/info"
    
    def get_description(self) -> str:
        """取得指令描述"""
        return "顯示系統部署資訊"
