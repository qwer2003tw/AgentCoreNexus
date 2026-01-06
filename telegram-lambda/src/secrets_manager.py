"""
Secrets Manager Module - 安全地獲取和快取敏感資訊
"""
import json
import os
from typing import Dict, Optional
from functools import lru_cache
import boto3
from botocore.exceptions import ClientError
from utils.logger import get_logger

logger = get_logger(__name__)

# 全域 Secrets Manager 客戶端
_secrets_client = None


def get_secrets_client():
    """獲取或建立 Secrets Manager 客戶端"""
    global _secrets_client
    if _secrets_client is None:
        _secrets_client = boto3.client('secretsmanager')
    return _secrets_client


@lru_cache(maxsize=10)
def get_secret(secret_arn: str) -> Optional[Dict[str, str]]:
    """
    從 Secrets Manager 獲取 secret (帶快取)
    
    Args:
        secret_arn: Secret ARN
        
    Returns:
        Dict: Secret 內容，或 None 如果失敗
    """
    try:
        client = get_secrets_client()
        response = client.get_secret_value(SecretId=secret_arn)
        
        # 解析 JSON
        secret_string = response.get('SecretString')
        if secret_string:
            secret_data = json.loads(secret_string)
            logger.info(
                "Secret retrieved successfully",
                extra={
                    'secret_arn': secret_arn,
                    'event_type': 'secret_retrieved'
                }
            )
            return secret_data
        
        logger.error(
            "Secret has no SecretString",
            extra={'secret_arn': secret_arn}
        )
        return None
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(
            f"Failed to retrieve secret: {error_code}",
            extra={
                'secret_arn': secret_arn,
                'error_code': error_code,
                'event_type': 'secret_retrieval_failed'
            },
            exc_info=True
        )
        return None
    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse secret JSON: {str(e)}",
            extra={'secret_arn': secret_arn},
            exc_info=True
        )
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error retrieving secret: {str(e)}",
            extra={'secret_arn': secret_arn},
            exc_info=True
        )
        return None


def get_telegram_secrets() -> Optional[Dict[str, str]]:
    """
    獲取所有 Telegram Secrets (bot_token 和 webhook_secret_token)
    
    Returns:
        Dict: 包含 'bot_token' 和 'webhook_secret_token' 的字典，或 None 如果失敗
    """
    secret_arn = os.environ.get('TELEGRAM_SECRETS_ARN')
    if not secret_arn:
        logger.error("TELEGRAM_SECRETS_ARN environment variable not set")
        return None
    
    secret_data = get_secret(secret_arn)
    if secret_data:
        # 驗證必要的 keys 是否存在
        if 'bot_token' in secret_data and 'webhook_secret_token' in secret_data:
            return secret_data
        else:
            logger.error(
                "Secret data missing required keys",
                extra={
                    'has_bot_token': 'bot_token' in secret_data,
                    'has_webhook_secret_token': 'webhook_secret_token' in secret_data
                }
            )
    
    return None


def get_telegram_bot_token() -> Optional[str]:
    """
    獲取 Telegram Bot Token
    
    Returns:
        str: Bot Token，或 None 如果失敗
    """
    secrets = get_telegram_secrets()
    if secrets:
        return secrets.get('bot_token')
    return None


def get_telegram_secret_token() -> Optional[str]:
    """
    獲取 Telegram Webhook Secret Token
    
    Returns:
        str: Secret Token，或 None 如果失敗
    """
    secrets = get_telegram_secrets()
    if secrets:
        return secrets.get('webhook_secret_token')
    return None


def clear_secrets_cache():
    """
    清除 secrets 快取（主要用於測試）
    """
    get_secret.cache_clear()
    logger.debug("Secrets cache cleared")
