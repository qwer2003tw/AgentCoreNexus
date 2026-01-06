"""
Allowlist Module - DynamoDB 允許名單驗證
"""
import os
import boto3
from typing import Optional
from botocore.exceptions import ClientError
from utils.logger import get_logger

logger = get_logger(__name__)

# 初始化 DynamoDB 客戶端
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('ALLOWLIST_TABLE_NAME', 'telegram-allowlist')
table = dynamodb.Table(table_name)


def check_allowed(chat_id: int, username: str = '') -> bool:
    """
    檢查用戶是否在允許名單中
    
    Args:
        chat_id: Telegram chat ID
        username: Telegram username (可選)
        
    Returns:
        bool: True 如果允許，False 如果拒絕
    """
    try:
        # 查詢 DynamoDB
        response = table.get_item(
            Key={'chat_id': chat_id}
        )
        
        # 檢查是否存在記錄
        if 'Item' not in response:
            logger.info(
                f"Chat ID not found in allowlist",
                extra={
                    'chat_id': chat_id,
                    'username': username,
                    'event_type': 'allowlist_miss'
                }
            )
            return False
        
        item = response['Item']
        
        # 檢查 enabled 狀態
        if not item.get('enabled', False):
            logger.warning(
                f"Chat ID is disabled",
                extra={
                    'chat_id': chat_id,
                    'username': username,
                    'event_type': 'allowlist_disabled'
                }
            )
            return False
        
        # 如果提供了 username，進行額外驗證
        stored_username = item.get('username', '')
        if username and stored_username and username != stored_username:
            logger.warning(
                f"Username mismatch",
                extra={
                    'chat_id': chat_id,
                    'provided_username': username,
                    'stored_username': stored_username,
                    'event_type': 'username_mismatch'
                }
            )
            return False
        
        logger.info(
            f"Access granted",
            extra={
                'chat_id': chat_id,
                'username': username,
                'event_type': 'allowlist_hit'
            }
        )
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(
            f"DynamoDB error: {error_code}",
            extra={
                'chat_id': chat_id,
                'error': str(e),
                'event_type': 'dynamodb_error'
            },
            exc_info=True
        )
        # 發生錯誤時預設拒絕訪問
        return False
        
    except Exception as e:
        logger.error(
            f"Unexpected error in allowlist check: {str(e)}",
            extra={
                'chat_id': chat_id,
                'event_type': 'allowlist_error'
            },
            exc_info=True
        )
        return False


def add_to_allowlist(chat_id: int, username: str, enabled: bool = True) -> bool:
    """
    新增用戶到允許名單 (輔助函數，非 Lambda 主流程使用)
    
    Args:
        chat_id: Telegram chat ID
        username: Telegram username
        enabled: 是否啟用
        
    Returns:
        bool: True 如果成功
    """
    try:
        table.put_item(
            Item={
                'chat_id': chat_id,
                'username': username,
                'enabled': enabled
            }
        )
        logger.info(
            f"Added to allowlist",
            extra={
                'chat_id': chat_id,
                'username': username,
                'enabled': enabled,
                'event_type': 'allowlist_add'
            }
        )
        return True
        
    except ClientError as e:
        logger.error(f"Failed to add to allowlist: {str(e)}", exc_info=True)
        return False


def remove_from_allowlist(chat_id: int) -> bool:
    """
    從允許名單中移除用戶 (輔助函數)
    
    Args:
        chat_id: Telegram chat ID
        
    Returns:
        bool: True 如果成功
    """
    try:
        table.delete_item(
            Key={'chat_id': chat_id}
        )
        logger.info(
            f"Removed from allowlist",
            extra={
                'chat_id': chat_id,
                'event_type': 'allowlist_remove'
            }
        )
        return True
        
    except ClientError as e:
        logger.error(f"Failed to remove from allowlist: {str(e)}", exc_info=True)
        return False
