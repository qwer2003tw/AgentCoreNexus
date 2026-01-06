"""
Admin List Module - Admin 權限驗證
從 DynamoDB 的 role 欄位讀取用戶角色
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


def get_user_role(chat_id: int, username: str = '') -> str:
    """
    取得用戶角色
    
    Args:
        chat_id: Telegram chat ID
        username: Telegram username (用於日誌)
        
    Returns:
        str: 用戶角色 ('admin', 'user', 或 'none')
    """
    try:
        # 查詢 DynamoDB
        response = table.get_item(
            Key={'chat_id': chat_id}
        )
        
        # 檢查是否存在記錄
        if 'Item' not in response:
            logger.debug(
                f"User not found in database",
                extra={
                    'chat_id': chat_id,
                    'username': username,
                    'event_type': 'user_not_found'
                }
            )
            return 'none'
        
        item = response['Item']
        
        # 檢查是否啟用
        if not item.get('enabled', False):
            logger.debug(
                f"User is disabled",
                extra={
                    'chat_id': chat_id,
                    'username': username,
                    'event_type': 'user_disabled'
                }
            )
            return 'none'
        
        # 取得角色（預設為 'user'）
        role = item.get('role', 'user')
        
        logger.debug(
            f"User role retrieved",
            extra={
                'chat_id': chat_id,
                'username': username,
                'role': role,
                'event_type': 'role_retrieved'
            }
        )
        
        return role
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(
            f"DynamoDB error: {error_code}",
            extra={
                'chat_id': chat_id,
                'username': username,
                'error': str(e),
                'event_type': 'dynamodb_error'
            },
            exc_info=True
        )
        return 'none'
        
    except Exception as e:
        logger.error(
            f"Unexpected error retrieving user role: {str(e)}",
            extra={
                'chat_id': chat_id,
                'username': username,
                'event_type': 'role_retrieval_error'
            },
            exc_info=True
        )
        return 'none'


def is_admin(chat_id: int, username: str = '') -> bool:
    """
    檢查用戶是否為 admin
    
    Args:
        chat_id: Telegram chat ID
        username: Telegram username (用於日誌)
        
    Returns:
        bool: True 如果是 admin
    """
    role = get_user_role(chat_id, username)
    is_admin_user = (role == 'admin')
    
    if is_admin_user:
        logger.info(
            f"Admin check: granted",
            extra={
                'chat_id': chat_id,
                'username': username,
                'role': role,
                'event_type': 'admin_check_granted'
            }
        )
    else:
        logger.debug(
            f"Admin check: denied",
            extra={
                'chat_id': chat_id,
                'username': username,
                'role': role,
                'event_type': 'admin_check_denied'
            }
        )
    
    return is_admin_user


def set_user_role(chat_id: int, role: str, username: str = '') -> bool:
    """
    設定用戶角色（輔助函數）
    
    Args:
        chat_id: Telegram chat ID
        role: 新角色 ('admin' 或 'user')
        username: Telegram username (可選)
        
    Returns:
        bool: True 如果成功
    """
    try:
        # 建立更新表達式
        update_expression = "SET #role = :role"
        expression_attribute_names = {'#role': 'role'}
        expression_attribute_values = {':role': role}
        
        # 如果提供了 username，也更新它
        if username:
            update_expression += ", username = :username"
            expression_attribute_values[':username'] = username
        
        # 更新 DynamoDB
        table.update_item(
            Key={'chat_id': chat_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        logger.info(
            f"User role updated",
            extra={
                'chat_id': chat_id,
                'username': username,
                'new_role': role,
                'event_type': 'role_updated'
            }
        )
        return True
        
    except ClientError as e:
        logger.error(
            f"Failed to update user role: {str(e)}",
            extra={
                'chat_id': chat_id,
                'username': username,
                'target_role': role,
                'event_type': 'role_update_failed'
            },
            exc_info=True
        )
        return False
