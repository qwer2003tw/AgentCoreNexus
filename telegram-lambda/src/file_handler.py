"""
Telegram 檔案處理模組
負責從 Telegram 下載檔案並上傳到 S3
"""
import os
import boto3
import requests
from typing import Dict, Any, Optional, Tuple
from utils.logger import get_logger
from secrets_manager import get_telegram_secrets

logger = get_logger(__name__)

# S3 客戶端（延遲初始化）
_s3_client = None

def get_s3_client():
    """獲取 S3 客戶端單例"""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client

# 從環境變數獲取 S3 bucket 名稱
S3_BUCKET = os.environ.get('FILE_STORAGE_BUCKET', '')

def get_bot_token() -> str:
    """
    從 Secrets Manager 獲取 Telegram Bot Token
    
    Returns:
        Bot token 字串
    """
    try:
        secrets = get_telegram_secrets()
        if secrets:
            return secrets.get('bot_token', '')
        return ''
    except Exception as e:
        logger.error(f"Failed to get bot token: {str(e)}", exc_info=True)
        return ''


def download_telegram_file(file_id: str) -> Optional[bytes]:
    """
    從 Telegram 下載檔案
    
    Args:
        file_id: Telegram file_id
    
    Returns:
        檔案內容（bytes）或 None
    """
    try:
        bot_token = get_bot_token()
        if not bot_token:
            logger.error("Bot token not available")
            return None
        
        # 1. 獲取 file_path
        get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile"
        response = requests.get(
            get_file_url, 
            params={'file_id': file_id}, 
            timeout=10
        )
        response.raise_for_status()
        
        file_info = response.json()
        if not file_info.get('ok'):
            logger.error(f"Failed to get file info: {file_info}")
            return None
        
        file_path = file_info['result']['file_path']
        file_size = file_info['result'].get('file_size', 0)
        logger.info(f"✅ Got file_path: {file_path}, size: {file_size} bytes")
        
        # 2. 下載檔案
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        download_response = requests.get(download_url, timeout=30)
        download_response.raise_for_status()
        
        file_content = download_response.content
        logger.info(f"✅ Downloaded file: {len(file_content)} bytes")
        
        return file_content
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ HTTP error downloading file: {str(e)}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"❌ Failed to download file: {str(e)}", exc_info=True)
        return None


def upload_to_s3(
    file_content: bytes, 
    chat_id: int, 
    message_id: int, 
    filename: str,
    mime_type: Optional[str] = None
) -> Optional[str]:
    """
    上傳檔案到 S3
    
    Args:
        file_content: 檔案內容
        chat_id: Telegram chat ID
        message_id: 訊息 ID
        filename: 檔案名稱
        mime_type: MIME 類型（可選）
    
    Returns:
        S3 URL 或 None
    """
    if not S3_BUCKET:
        logger.error("FILE_STORAGE_BUCKET not configured")
        return None
    
    try:
        # S3 key: chat_id/message_id/filename
        s3_key = f"{chat_id}/{message_id}/{filename}"
        
        # 準備上傳參數
        put_params = {
            'Bucket': S3_BUCKET,
            'Key': s3_key,
            'Body': file_content,
        }
        
        # 如果有 MIME 類型，添加 ContentType
        if mime_type:
            put_params['ContentType'] = mime_type
        else:
            put_params['ContentType'] = 'application/octet-stream'
        
        # 上傳到 S3
        s3_client = get_s3_client()
        s3_client.put_object(**put_params)
        
        s3_url = f"s3://{S3_BUCKET}/{s3_key}"
        logger.info(
            f"✅ Uploaded to S3: {s3_url}",
            extra={
                'event_type': 's3_upload_success',
                'bucket': S3_BUCKET,
                'key': s3_key,
                'size': len(file_content)
            }
        )
        
        return s3_url
        
    except Exception as e:
        logger.error(
            f"❌ Failed to upload to S3: {str(e)}", 
            extra={
                'event_type': 's3_upload_failure',
                'bucket': S3_BUCKET,
                'error': str(e)
            },
            exc_info=True
        )
        return None


def process_file_attachment(
    file_id: str,
    filename: str,
    chat_id: int,
    message_id: int,
    mime_type: Optional[str] = None,
    file_size: Optional[int] = None,
    caption: Optional[str] = None
) -> Dict[str, Any]:
    """
    處理檔案附件
    
    Args:
        file_id: Telegram file_id
        filename: 檔案名稱
        chat_id: Telegram chat ID
        message_id: 訊息 ID
        mime_type: MIME 類型（可選）
        file_size: 檔案大小（可選）
        caption: Caption 文字（可選）
    
    Returns:
        處理後的附件資訊字典
    """
    logger.info(
        f"Processing file attachment",
        extra={
            'event_type': 'file_processing_start',
            'file_id': file_id,
            'file_name': filename,
            'chat_id': chat_id,
            'message_id': message_id,
            'file_size': file_size
        }
    )
    
    # 判斷是否為圖片
    attachment_type = _detect_attachment_type(filename, mime_type)
    
    # 基礎附件資訊
    attachment = {
        "type": attachment_type,
        "file_id": file_id,
        "file_name": filename,
        "mime_type": mime_type or "application/octet-stream",
        "file_size": file_size or 0,
        "task": caption if caption else ("請描述這張圖片的內容。" if attachment_type == "photo" else "摘要此檔案的內容")
    }
    
    # 1. 下載檔案
    file_content = download_telegram_file(file_id)
    if not file_content:
        attachment["error"] = "檔案下載失敗"
        logger.warning(
            "File download failed",
            extra={
                'event_type': 'file_download_failed',
                'file_id': file_id
            }
        )
        return attachment
    
    # 更新實際檔案大小
    attachment["file_size"] = len(file_content)
    
    # 2. 上傳到 S3
    s3_url = upload_to_s3(
        file_content, 
        chat_id, 
        message_id, 
        filename,
        mime_type
    )
    
    if not s3_url:
        attachment["error"] = "檔案上傳失敗"
        logger.warning(
            "File upload failed",
            extra={
                'event_type': 'file_upload_failed',
                'file_id': file_id
            }
        )
        return attachment
    
    # 3. 添加 S3 URL
    attachment["s3_url"] = s3_url
    
    logger.info(
        f"✅ File processing completed",
        extra={
            'event_type': 'file_processing_success',
            'file_id': file_id,
            's3_url': s3_url,
            'size': len(file_content)
        }
    )
    
    return attachment


def _detect_attachment_type(filename: str, mime_type: Optional[str] = None) -> str:
    """
    根據檔案名稱和 MIME 類型判斷附件類型
    
    Args:
        filename: 檔案名稱
        mime_type: MIME 類型（可選）
    
    Returns:
        附件類型：'photo' 或 'document'
    """
    import os
    
    # 支援的圖片副檔名
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    # 支援的圖片 MIME 類型
    image_mime_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    
    # 檢查副檔名
    ext = os.path.splitext(filename)[1].lower()
    if ext in image_extensions:
        return 'photo'
    
    # 檢查 MIME 類型
    if mime_type and mime_type in image_mime_types:
        return 'photo'
    
    return 'document'


def validate_file_size(file_size: int, max_size: int = 20 * 1024 * 1024) -> Tuple[bool, str]:
    """
    驗證檔案大小
    
    Args:
        file_size: 檔案大小（bytes）
        max_size: 最大允許大小（bytes），預設 20MB
    
    Returns:
        (是否有效, 錯誤訊息)
    """
    if file_size <= 0:
        return False, "檔案大小無效"
    
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        return False, f"檔案過大（{actual_mb:.1f}MB），最大支援 {max_mb:.0f}MB"
    
    return True, ""
