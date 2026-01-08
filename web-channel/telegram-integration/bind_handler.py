"""
Telegram /bind command handler
Allows Telegram users to bind their account with Web account
"""

import os
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")

# Environment variables (to be added to telegram-lambda)
BINDINGS_TABLE = os.environ.get("BINDINGS_TABLE", "")
BINDING_CODES_TABLE = os.environ.get("BINDING_CODES_TABLE", "")

# DynamoDB tables
bindings_table = dynamodb.Table(BINDINGS_TABLE) if BINDINGS_TABLE else None
binding_codes_table = dynamodb.Table(BINDING_CODES_TABLE) if BINDING_CODES_TABLE else None


def handle_bind_command(chat_id: int, username: str, args: list[str]) -> dict[str, Any]:
    """
    Handle /bind command
    
    Args:
        chat_id: Telegram chat ID
        username: Telegram username
        args: Command arguments (should contain 6-digit code)
        
    Returns:
        Response dict with success/error message
    """
    if not BINDINGS_TABLE or not BINDING_CODES_TABLE:
        return {
            "success": False,
            "message": "❌ Binding功能尚未啟用"
        }
    
    # Check if code is provided
    if not args or len(args) == 0:
        return {
            "success": False,
            "message": "❌ 請提供綁定碼\n\n使用方式: /bind 123456"
        }
    
    code = args[0].strip()
    
    # Validate code format (6 digits)
    if not code.isdigit() or len(code) != 6:
        return {
            "success": False,
            "message": "❌ 綁定碼格式錯誤\n\n綁定碼應為 6 位數字"
        }
    
    try:
        # Verify binding code
        code_info = verify_binding_code(code)
        
        if not code_info:
            return {
                "success": False,
                "message": "❌ 綁定碼無效或已過期\n\n請在 Web 端重新生成綁定碼"
            }
        
        web_email = code_info["web_email"]
        
        # Check if Telegram account is already bound
        existing_binding = get_binding_by_telegram(chat_id)
        if existing_binding:
            return {
                "success": False,
                "message": f"❌ 此 Telegram 帳號已綁定至另一個帳戶\n\n如需重新綁定，請聯絡管理員"
            }
        
        # Create or update binding
        unified_user_id = code_info.get("unified_user_id")
        if not unified_user_id:
            # Get unified_user_id from web email binding
            web_binding = get_binding_by_email(web_email)
            unified_user_id = web_binding["unified_user_id"] if web_binding else None
        
        if not unified_user_id:
            return {
                "success": False,
                "message": "❌ 綁定失敗：找不到 Web 帳號\n\n請確認 Web 帳號存在"
            }
        
        # Update binding to include Telegram
        update_binding_with_telegram(unified_user_id, chat_id, web_email)
        
        # Mark code as used
        mark_code_as_used(code)
        
        print(f"Binding successful: {web_email} <-> Telegram {chat_id}")
        
        return {
            "success": True,
            "message": f"✅ 綁定成功！\n\n您的 Telegram 帳號已與 {web_email} 綁定\n\n現在您可以在 Web 和 Telegram 之間共享對話記錄和記憶功能。"
        }
        
    except Exception as e:
        print(f"Error in bind command: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": "❌ 綁定過程發生錯誤\n\n請稍後再試或聯絡管理員"
        }


def verify_binding_code(code: str) -> dict[str, Any] | None:
    """
    Verify binding code is valid and not expired
    
    Args:
        code: 6-digit binding code
        
    Returns:
        Code info or None if invalid
    """
    try:
        response = binding_codes_table.get_item(Key={"code": code})
        
        if "Item" not in response:
            return None
        
        code_item = response["Item"]
        
        # Check status
        if code_item.get("status") != "pending":
            print(f"Code already used: {code}")
            return None
        
        # Check expiry
        expires_at = code_item.get("expires_at", "")
        now = datetime.now(timezone.utc).isoformat()
        
        if expires_at < now:
            print(f"Code expired: {code}")
            return None
        
        return code_item
        
    except ClientError as e:
        print(f"Error verifying code: {str(e)}")
        return None


def get_binding_by_telegram(telegram_chat_id: int) -> dict[str, Any] | None:
    """
    Check if Telegram account is already bound
    
    Args:
        telegram_chat_id: Telegram chat ID
        
    Returns:
        Binding or None
    """
    try:
        response = bindings_table.query(
            IndexName="telegram_chat_id-index",
            KeyConditionExpression="telegram_chat_id = :chat_id",
            ExpressionAttributeValues={":chat_id": telegram_chat_id}
        )
        
        items = response.get("Items", [])
        return items[0] if items else None
        
    except Exception as e:
        print(f"Error getting binding by telegram: {str(e)}")
        return None


def get_binding_by_email(email: str) -> dict[str, Any] | None:
    """
    Get binding by web email
    
    Args:
        email: Web email
        
    Returns:
        Binding or None
    """
    try:
        response = bindings_table.query(
            IndexName="web_email-index",
            KeyConditionExpression="web_email = :email",
            ExpressionAttributeValues={":email": email}
        )
        
        items = response.get("Items", [])
        return items[0] if items else None
        
    except Exception as e:
        print(f"Error getting binding by email: {str(e)}")
        return None


def update_binding_with_telegram(
    unified_user_id: str,
    telegram_chat_id: int,
    web_email: str
) -> None:
    """
    Update binding to include Telegram account
    
    Args:
        unified_user_id: Unified user ID
        telegram_chat_id: Telegram chat ID
        web_email: Web email
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        bindings_table.update_item(
            Key={"unified_user_id": unified_user_id},
            UpdateExpression="SET telegram_chat_id = :chat_id, binding_status = :status, updated_at = :now",
            ExpressionAttributeValues={
                ":chat_id": telegram_chat_id,
                ":status": "complete",
                ":now": now
            }
        )
        
        print(f"Updated binding: {unified_user_id} with Telegram {telegram_chat_id}")
        
    except ClientError as e:
        print(f"Error updating binding: {str(e)}")
        raise


def mark_code_as_used(code: str) -> None:
    """
    Mark binding code as used
    
    Args:
        code: Binding code
    """
    try:
        binding_codes_table.update_item(
            Key={"code": code},
            UpdateExpression="SET #status = :used",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":used": "used"}
        )
        
        print(f"Marked code as used: {code}")
        
    except ClientError as e:
        print(f"Error marking code as used: {str(e)}")
        # Non-critical error


# ============================================================
# Integration with telegram-lambda command system
# ============================================================

# This should be registered in telegram-lambda/src/commands/router.py
# Example registration:
#
# from commands.handlers.bind_handler import handle_bind_command
#
# COMMANDS = {
#     ...
#     "bind": {
#         "handler": handle_bind_command,
#         "permission": Permission.ALLOWLIST,
#         "description": "綁定 Telegram 與 Web 帳號"
#     }
# }