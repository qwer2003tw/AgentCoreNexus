"""
History REST API Lambda
Handles conversation history queries and export
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")

# Environment variables
HISTORY_TABLE = os.environ["HISTORY_TABLE"]
BINDINGS_TABLE = os.environ["BINDINGS_TABLE"]

# DynamoDB tables
history_table = dynamodb.Table(HISTORY_TABLE)
bindings_table = dynamodb.Table(BINDINGS_TABLE)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main handler for history operations
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    
    print(f"{method} {path}")
    
    # Extract email from JWT (assuming Lambda Authorizer has validated)
    email = extract_email_from_token(event)
    if not email:
        return response(401, {"error": "Unauthorized"})
    
    try:
        if path == "/history" and method == "GET":
            return handle_get_history(email, event)
        
        elif path == "/history/export" and method == "GET":
            return handle_export_history(email, event)
        
        elif path == "/history/stats" and method == "GET":
            return handle_get_stats(email)
        
        else:
            return response(404, {"error": "Not found"})
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return response(500, {"error": "Internal server error"})


def handle_get_history(email: str, event: dict[str, Any]) -> dict[str, Any]:
    """
    Get conversation history for user
    
    Args:
        email: User email
        event: API Gateway event with query parameters
        
    Returns:
        Paginated conversation history
    """
    # Get unified_user_id
    unified_user_id = get_unified_user_id_by_email(email)
    if not unified_user_id:
        return response(200, {"conversations": [], "count": 0})
    
    # Get query parameters
    query_params = event.get("queryStringParameters") or {}
    limit = int(query_params.get("limit", 50))
    last_key = query_params.get("last_key")
    channel_filter = query_params.get("channel")  # 'web', 'telegram', or None (all)
    
    try:
        # Query history
        query_kwargs = {
            "KeyConditionExpression": "unified_user_id = :user_id",
            "ExpressionAttributeValues": {":user_id": unified_user_id},
            "Limit": limit,
            "ScanIndexForward": False  # Newest first
        }
        
        if last_key:
            query_kwargs["ExclusiveStartKey"] = {
                "unified_user_id": unified_user_id,
                "timestamp_msgid": last_key
            }
        
        result = history_table.query(**query_kwargs)
        
        # Filter by channel if specified
        messages = result.get("Items", [])
        if channel_filter:
            messages = [m for m in messages if m.get("channel") == channel_filter]
        
        # Convert to JSON-safe format
        messages = [convert_dynamodb_to_json(m) for m in messages]
        
        # Group by time periods
        grouped = group_messages_by_time(messages)
        
        response_data = {
            "conversations": grouped,
            "count": len(messages)
        }
        
        # Include pagination token
        if "LastEvaluatedKey" in result:
            response_data["last_key"] = result["LastEvaluatedKey"]["timestamp_msgid"]
        
        return response(200, response_data)
        
    except ClientError as e:
        print(f"Error querying history: {str(e)}")
        return response(500, {"error": "Failed to retrieve history"})


def handle_export_history(email: str, event: dict[str, Any]) -> dict[str, Any]:
    """
    Export conversation history in specified format
    
    Args:
        email: User email
        event: API Gateway event with query parameters
        
    Returns:
        Exported conversation data
    """
    # Get unified_user_id
    unified_user_id = get_unified_user_id_by_email(email)
    if not unified_user_id:
        return response(200, {"data": "", "format": "json"})
    
    # Get query parameters
    query_params = event.get("queryStringParameters") or {}
    export_format = query_params.get("format", "json")  # 'json' or 'markdown'
    channel_filter = query_params.get("channel")
    
    try:
        # Query ALL history (no limit)
        all_messages = []
        last_evaluated_key = None
        
        while True:
            query_kwargs = {
                "KeyConditionExpression": "unified_user_id = :user_id",
                "ExpressionAttributeValues": {":user_id": unified_user_id},
                "ScanIndexForward": False
            }
            
            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key
            
            result = history_table.query(**query_kwargs)
            all_messages.extend(result.get("Items", []))
            
            last_evaluated_key = result.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break
        
        # Filter by channel if specified
        if channel_filter:
            all_messages = [m for m in all_messages if m.get("channel") == channel_filter]
        
        # Convert to JSON-safe format
        all_messages = [convert_dynamodb_to_json(m) for m in all_messages]
        
        # Export in requested format
        if export_format == "markdown":
            exported_data = export_as_markdown(all_messages, email)
        else:
            exported_data = json.dumps(all_messages, indent=2, ensure_ascii=False)
        
        return response(200, {
            "data": exported_data,
            "format": export_format,
            "message_count": len(all_messages),
            "exported_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        print(f"Error exporting history: {str(e)}")
        return response(500, {"error": "Failed to export history"})


def handle_get_stats(email: str) -> dict[str, Any]:
    """
    Get conversation statistics for user
    
    Args:
        email: User email
        
    Returns:
        Statistics data
    """
    unified_user_id = get_unified_user_id_by_email(email)
    if not unified_user_id:
        return response(200, {"total_messages": 0})
    
    try:
        # Query to count messages (could be optimized with a counter table)
        result = history_table.query(
            KeyConditionExpression="unified_user_id = :user_id",
            ExpressionAttributeValues={":user_id": unified_user_id},
            Select="COUNT"
        )
        
        total_messages = result.get("Count", 0)
        
        # Calculate oldest and newest message timestamps
        # Query oldest (ScanIndexForward=True, Limit=1)
        oldest_result = history_table.query(
            KeyConditionExpression="unified_user_id = :user_id",
            ExpressionAttributeValues={":user_id": unified_user_id},
            ScanIndexForward=True,
            Limit=1
        )
        
        # Query newest (ScanIndexForward=False, Limit=1)
        newest_result = history_table.query(
            KeyConditionExpression="unified_user_id = :user_id",
            ExpressionAttributeValues={":user_id": unified_user_id},
            ScanIndexForward=False,
            Limit=1
        )
        
        oldest_timestamp = None
        newest_timestamp = None
        
        if oldest_result.get("Items"):
            oldest_timestamp = oldest_result["Items"][0]["timestamp_msgid"].split("#")[0]
        
        if newest_result.get("Items"):
            newest_timestamp = newest_result["Items"][0]["timestamp_msgid"].split("#")[0]
        
        return response(200, {
            "total_messages": total_messages,
            "oldest_message": oldest_timestamp,
            "newest_message": newest_timestamp
        })
        
    except Exception as e:
        print(f"Error getting stats: {str(e)}")
        return response(500, {"error": "Failed to get statistics"})


# ============================================================
# Helper Functions
# ============================================================

def get_unified_user_id_by_email(email: str) -> str | None:
    """
    Get unified_user_id for a web user
    
    Args:
        email: User email
        
    Returns:
        Unified user ID or None
    """
    try:
        result = bindings_table.query(
            IndexName="web_email-index",
            KeyConditionExpression="web_email = :email",
            ExpressionAttributeValues={":email": email}
        )
        
        items = result.get("Items", [])
        if items:
            return items[0]["unified_user_id"]
        
        return None
        
    except Exception as e:
        print(f"Error getting unified_user_id: {str(e)}")
        return None


def group_messages_by_time(messages: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """
    Group messages by time period (today, yesterday, this week, earlier)
    
    Args:
        messages: List of messages
        
    Returns:
        Grouped messages
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=7)
    
    grouped = {
        "today": [],
        "yesterday": [],
        "this_week": [],
        "earlier": []
    }
    
    for msg in messages:
        timestamp_str = msg.get("timestamp_msgid", "").split("#")[0]
        try:
            msg_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            
            if msg_time >= today_start:
                grouped["today"].append(msg)
            elif msg_time >= yesterday_start:
                grouped["yesterday"].append(msg)
            elif msg_time >= week_start:
                grouped["this_week"].append(msg)
            else:
                grouped["earlier"].append(msg)
        except Exception:
            grouped["earlier"].append(msg)
    
    return grouped


def export_as_markdown(messages: list[dict[str, Any]], email: str) -> str:
    """
    Export messages as Markdown format
    
    Args:
        messages: List of messages
        email: User email
        
    Returns:
        Markdown string
    """
    lines = [
        f"# Conversation History Export",
        f"",
        f"**User**: {email}",
        f"**Exported**: {datetime.now(timezone.utc).isoformat()}",
        f"**Total Messages**: {len(messages)}",
        f"",
        f"---",
        f""
    ]
    
    # Reverse to show oldest first
    messages_sorted = sorted(messages, key=lambda m: m.get("timestamp_msgid", ""))
    
    current_date = None
    
    for msg in messages_sorted:
        timestamp_str = msg.get("timestamp_msgid", "").split("#")[0]
        role = msg.get("role", "unknown")
        content_text = msg.get("content", {}).get("text", "")
        channel = msg.get("channel", "unknown")
        
        try:
            msg_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            date_str = msg_time.strftime("%Y-%m-%d")
            time_str = msg_time.strftime("%H:%M:%S")
            
            # Add date header if new date
            if date_str != current_date:
                lines.append(f"## {date_str}")
                lines.append("")
                current_date = date_str
            
            # Add message
            role_icon = "👤" if role == "user" else "🤖"
            channel_tag = f"*[{channel}]*"
            lines.append(f"**{time_str}** {role_icon} **{role.title()}** {channel_tag}")
            lines.append("")
            lines.append(content_text)
            lines.append("")
            lines.append("---")
            lines.append("")
            
        except Exception:
            lines.append(f"**{role.title()}**: {content_text}")
            lines.append("")
    
    return "\n".join(lines)


def convert_dynamodb_to_json(item: dict[str, Any]) -> dict[str, Any]:
    """
    Convert DynamoDB item with Decimal to JSON-safe format
    
    Args:
        item: DynamoDB item
        
    Returns:
        JSON-safe dict
    """
    def decimal_to_int(obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        elif isinstance(obj, dict):
            return {k: decimal_to_int(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [decimal_to_int(i) for i in obj]
        return obj
    
    return decimal_to_int(item)


def extract_email_from_token(event: dict[str, Any]) -> str | None:
    """
    Extract email from JWT token in Authorization header
    (Simplified - actual implementation should verify token)
    
    Args:
        event: API Gateway event
        
    Returns:
        Email or None
    """
    # In real implementation, this would decode JWT
    # For now, assume Lambda Authorizer has set requestContext.authorizer.email
    authorizer = event.get("requestContext", {}).get("authorizer", {})
    return authorizer.get("email")


def response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """
    Create API Gateway response
    
    Args:
        status_code: HTTP status code
        body: Response body dict
        
    Returns:
        API Gateway response
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }