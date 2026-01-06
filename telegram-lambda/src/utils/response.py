"""
Response Utility - API Gateway 回應格式化
"""
import json
from typing import Dict, Any, Optional


def create_response(
    status_code: int,
    body: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    建立標準的 API Gateway 回應格式
    
    Args:
        status_code: HTTP 狀態碼
        body: 回應內容
        headers: 自定義標頭 (可選)
        
    Returns:
        dict: API Gateway 格式的回應
    """
    default_headers = {
        'Content-Type': 'application/json',
        'X-Service': 'telegram-lambda'
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body, ensure_ascii=False)
    }


def success_response(data: Dict[str, Any], message: str = 'Success') -> Dict[str, Any]:
    """
    建立成功回應
    
    Args:
        data: 回應資料
        message: 成功訊息
        
    Returns:
        dict: 200 OK 回應
    """
    return create_response(200, {
        'success': True,
        'message': message,
        'data': data
    })


def error_response(
    status_code: int,
    error_message: str,
    error_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    建立錯誤回應
    
    Args:
        status_code: HTTP 錯誤狀態碼
        error_message: 錯誤訊息
        error_code: 錯誤代碼 (可選)
        
    Returns:
        dict: 錯誤回應
    """
    body = {
        'success': False,
        'error': error_message
    }
    
    if error_code:
        body['error_code'] = error_code
    
    return create_response(status_code, body)


def unauthorized_response(message: str = 'Unauthorized') -> Dict[str, Any]:
    """
    建立 403 未授權回應
    
    Args:
        message: 錯誤訊息
        
    Returns:
        dict: 403 Forbidden 回應
    """
    return error_response(403, message, 'UNAUTHORIZED')


def bad_request_response(message: str = 'Bad Request') -> Dict[str, Any]:
    """
    建立 400 錯誤請求回應
    
    Args:
        message: 錯誤訊息
        
    Returns:
        dict: 400 Bad Request 回應
    """
    return error_response(400, message, 'BAD_REQUEST')


def internal_error_response(message: str = 'Internal Server Error') -> Dict[str, Any]:
    """
    建立 500 內部錯誤回應
    
    Args:
        message: 錯誤訊息
        
    Returns:
        dict: 500 Internal Server Error 回應
    """
    return error_response(500, message, 'INTERNAL_ERROR')
