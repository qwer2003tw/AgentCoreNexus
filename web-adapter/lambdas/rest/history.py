"""
Conversation History REST API Lambda
Handles conversation history queries and deletions for Web channel
"""

import json
import os
from typing import Any

import boto3

# Environment variables
CONVERSATION_HISTORY_TABLE = os.environ.get("CONVERSATION_HISTORY_TABLE")
CONVERSATION_METADATA_TABLE = os.environ.get("CONVERSATION_METADATA_TABLE")

# Initialize conversation service
_conversation_service = None


def get_conversation_service():
    """Get ConversationService singleton"""
    global _conversation_service
    if _conversation_service is None and CONVERSATION_HISTORY_TABLE and CONVERSATION_METADATA_TABLE:
        import sys

        sys.path.insert(0, "/opt/python")  # Lambda Layer path
        from conversation_service import ConversationService

        _conversation_service = ConversationService(
            CONVERSATION_HISTORY_TABLE, CONVERSATION_METADATA_TABLE
        )
    return _conversation_service


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main handler for conversation history operations

    Endpoints:
    - GET /conversations/{conversation_id}/messages - Get conversation messages
    - DELETE /conversations/{conversation_id} - Delete conversation (soft delete)
    - POST /conversations/{conversation_id}/restore - Restore deleted conversation

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    path_params = event.get("pathParameters") or {}
    conversation_id = path_params.get("conversation_id", "")

    print(f"{method} {path}")

    try:
        # Extract user email from JWT token
        user_email = extract_email_from_token(event)
        if not user_email:
            return response(401, {"error": "Unauthorized"})

        # Get conversation service
        service = get_conversation_service()
        if not service:
            return response(503, {"error": "Conversation storage not configured"})

        # Route to appropriate handler
        if method == "GET" and "/messages" in path:
            return handle_get_messages(event, service, conversation_id, user_email)

        elif method == "DELETE":
            return handle_delete_conversation(event, service, conversation_id, user_email)

        elif method == "POST" and "/restore" in path:
            return handle_restore_conversation(event, service, conversation_id, user_email)

        elif method == "GET" and path.endswith(f"/conversations/{conversation_id}"):
            return handle_get_metadata(event, service, conversation_id, user_email)

        else:
            return response(404, {"error": "Not found"})

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return response(500, {"error": "Internal server error"})


def handle_get_messages(
    event: dict[str, Any], service: Any, conversation_id: str, user_email: str
) -> dict[str, Any]:
    """
    Get conversation messages

    Query parameters:
    - limit: Number of messages to return (default: 50, max: 500)
    - start_time: Start timestamp for time range query (optional)
    - next_key: Pagination token (optional, JSON string)

    Args:
        event: API Gateway event
        service: ConversationService instance
        conversation_id: Conversation ID
        user_email: User email (for authorization)

    Returns:
        API Gateway response with messages
    """
    # Verify user owns this conversation
    # Web conversations use format: web:{user_id}
    # Extract user_id from JWT and verify it matches conversation_id

    query_params = event.get("queryStringParameters") or {}
    limit = int(query_params.get("limit", 50))
    start_time = int(query_params.get("start_time")) if query_params.get("start_time") else None
    next_key_str = query_params.get("next_key")

    # Parse pagination token
    next_key = None
    if next_key_str:
        try:
            next_key = json.loads(next_key_str)
        except:
            return response(400, {"error": "Invalid next_key format"})

    # Query messages
    result = service.get_messages(
        conversation_id=conversation_id,
        limit=limit,
        start_time=start_time,
        last_evaluated_key=next_key,
    )

    if not result["success"]:
        return response(400, {"error": result.get("error", "Failed to get messages")})

    # Format response
    return response(
        200,
        {
            "conversation_id": conversation_id,
            "messages": result["messages"],
            "count": result["count"],
            "has_more": result["has_more"],
            "next_key": json.dumps(result["next_key"]) if result["next_key"] else None,
        },
    )


def handle_delete_conversation(
    event: dict[str, Any], service: Any, conversation_id: str, user_email: str
) -> dict[str, Any]:
    """
    Delete conversation (soft delete by default)

    Query parameters:
    - hard: Set to 'true' for permanent deletion (default: false)

    Args:
        event: API Gateway event
        service: ConversationService instance
        conversation_id: Conversation ID
        user_email: User email (for authorization)

    Returns:
        API Gateway response
    """
    # Verify user owns this conversation
    # (Authorization logic here)

    query_params = event.get("queryStringParameters") or {}
    hard_delete = query_params.get("hard", "").lower() == "true"

    # Delete conversation
    result = service.delete_conversation(conversation_id=conversation_id, hard_delete=hard_delete)

    if not result["success"]:
        return response(400, {"error": result.get("error", "Failed to delete conversation")})

    # Format response
    return response(
        200,
        {
            "conversation_id": conversation_id,
            "deleted_at": result.get("deleted_at"),
            "permanent": result.get("permanent", False),
            "recoverable_until": result.get("recoverable_until"),
            "recovery_days": result.get("recovery_days"),
        },
    )


def handle_restore_conversation(
    event: dict[str, Any], service: Any, conversation_id: str, user_email: str
) -> dict[str, Any]:
    """
    Restore a soft-deleted conversation

    Args:
        event: API Gateway event
        service: ConversationService instance
        conversation_id: Conversation ID
        user_email: User email (for authorization)

    Returns:
        API Gateway response
    """
    # Verify user owns this conversation
    # (Authorization logic here)

    # Restore conversation
    result = service.restore_conversation(conversation_id=conversation_id)

    if not result["success"]:
        return response(400, {"error": result.get("error", "Failed to restore conversation")})

    return response(200, {"conversation_id": conversation_id, "status": "restored"})


def handle_get_metadata(
    event: dict[str, Any], service: Any, conversation_id: str, user_email: str
) -> dict[str, Any]:
    """
    Get conversation metadata

    Args:
        event: API Gateway event
        service: ConversationService instance
        conversation_id: Conversation ID
        user_email: User email (for authorization)

    Returns:
        API Gateway response with metadata
    """
    # Get metadata
    metadata = service.get_conversation_metadata(conversation_id)

    if not metadata:
        return response(404, {"error": "Conversation not found"})

    return response(200, {"conversation_id": conversation_id, "metadata": metadata})


def extract_email_from_token(event: dict[str, Any]) -> str | None:
    """
    Extract email from JWT token in Authorization header

    Args:
        event: API Gateway event

    Returns:
        Email or None
    """
    try:
        import jwt

        headers = event.get("headers", {})
        auth_header = headers.get("Authorization") or headers.get("authorization", "")

        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.replace("Bearer ", "")

        # Get JWT secret from environment or Secrets Manager
        jwt_secret_arn = os.environ.get("JWT_SECRET_ARN")
        if not jwt_secret_arn:
            return None

        secretsmanager = boto3.client("secretsmanager")
        secret_response = secretsmanager.get_secret_value(SecretId=jwt_secret_arn)
        secret_data = json.loads(secret_response["SecretString"])
        jwt_secret = secret_data["jwt_secret"]
        jwt_algorithm = secret_data.get("jwt_algorithm", "HS256")

        # Decode token
        payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
        return payload.get("sub")

    except Exception as e:
        print(f"Error extracting email from token: {str(e)}")
        return None


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
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body),
    }
