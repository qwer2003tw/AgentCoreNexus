"""
WebSocket $connect handler
Handles new WebSocket connections with JWT authentication
"""

import json
import os
import time
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
secretsmanager = boto3.client("secretsmanager")

# Environment variables
CONNECTIONS_TABLE = os.environ["CONNECTIONS_TABLE"]
WEB_USERS_TABLE = os.environ["WEB_USERS_TABLE"]
BINDINGS_TABLE = os.environ["BINDINGS_TABLE"]
JWT_SECRET_ARN = os.environ["JWT_SECRET_ARN"]

# DynamoDB tables
connections_table = dynamodb.Table(CONNECTIONS_TABLE)
web_users_table = dynamodb.Table(WEB_USERS_TABLE)
bindings_table = dynamodb.Table(BINDINGS_TABLE)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Handle WebSocket $connect route

    Args:
        event: API Gateway WebSocket event
        context: Lambda context

    Returns:
        Response with statusCode 200 (success) or 401 (unauthorized)
    """
    connection_id = event["requestContext"]["connectionId"]

    print(f"New WebSocket connection: {connection_id}")

    try:
        # Extract JWT token from query string
        query_params = event.get("queryStringParameters") or {}
        token = query_params.get("token")

        if not token:
            print("No JWT token provided")
            return {"statusCode": 401, "body": "Unauthorized: Missing token"}

        # Verify JWT and get user info
        user_info = verify_jwt_token(token)
        if not user_info:
            print("Invalid or expired JWT token")
            return {"statusCode": 401, "body": "Unauthorized: Invalid token"}

        email = user_info["email"]

        # Check if user is enabled
        user = get_web_user(email)
        if not user or not user.get("enabled", False):
            print(f"User not enabled: {email}")
            return {"statusCode": 401, "body": "Unauthorized: User disabled"}

        # Get unified_user_id (from bindings or generate)
        unified_user_id = get_unified_user_id(email)

        # Save connection to DynamoDB
        save_connection(connection_id, unified_user_id, email)

        print(
            f"Connection established: {connection_id} for user {email} (unified: {unified_user_id})"
        )

        return {"statusCode": 200, "body": "Connected"}

    except Exception as e:
        print(f"Error handling connection: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"statusCode": 500, "body": "Internal server error"}


def verify_jwt_token(token: str) -> dict[str, Any] | None:
    """
    Verify JWT token and extract user information

    Args:
        token: JWT token string

    Returns:
        User info dict or None if invalid
    """
    try:
        import jwt

        # Get JWT secret from Secrets Manager
        secret_response = secretsmanager.get_secret_value(SecretId=JWT_SECRET_ARN)
        secret_data = json.loads(secret_response["SecretString"])
        jwt_secret = secret_data["jwt_secret"]
        jwt_algorithm = secret_data.get("jwt_algorithm", "HS256")

        # Decode and verify JWT
        payload = jwt.decode(
            token, jwt_secret, algorithms=[jwt_algorithm], options={"verify_exp": True}
        )

        return {"email": payload["sub"], "role": payload.get("role", "user"), "exp": payload["exp"]}

    except jwt.ExpiredSignatureError:
        print("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"Invalid JWT token: {str(e)}")
        return None
    except Exception as e:
        print(f"Error verifying JWT: {str(e)}")
        return None


def get_web_user(email: str) -> dict[str, Any] | None:
    """
    Get web user from DynamoDB

    Args:
        email: User email

    Returns:
        User item or None
    """
    try:
        response = web_users_table.get_item(Key={"email": email})
        return response.get("Item")
    except ClientError as e:
        print(f"Error getting web user: {str(e)}")
        return None


def get_unified_user_id(email: str) -> str:
    """
    Get or create unified_user_id for a web user

    Args:
        email: User email

    Returns:
        Unified user ID (UUID)
    """
    try:
        # Query bindings by web_email
        response = bindings_table.query(
            IndexName="web_email-index",
            KeyConditionExpression="web_email = :email",
            ExpressionAttributeValues={":email": email},
        )

        items = response.get("Items", [])
        if items:
            return items[0]["unified_user_id"]

        # No binding found, create new unified_user_id
        import uuid

        unified_user_id = str(uuid.uuid4())

        # Create binding record (web only, no telegram)
        now = datetime.now(UTC).isoformat()
        bindings_table.put_item(
            Item={
                "unified_user_id": unified_user_id,
                "web_email": email,
                "binding_status": "web_only",
                "created_at": now,
                "updated_at": now,
            }
        )

        print(f"Created new unified_user_id: {unified_user_id} for {email}")
        return unified_user_id

    except Exception as e:
        print(f"Error getting unified_user_id: {str(e)}")
        # Fallback: generate temporary ID
        import uuid

        return str(uuid.uuid4())


def save_connection(connection_id: str, unified_user_id: str, email: str) -> None:
    """
    Save WebSocket connection to DynamoDB

    Args:
        connection_id: API Gateway connection ID
        unified_user_id: Unified user ID
        email: User email
    """
    try:
        now = datetime.now(UTC).isoformat()
        ttl = int(time.time()) + 7200  # 2 hours

        connections_table.put_item(
            Item={
                "connection_id": connection_id,
                "unified_user_id": unified_user_id,
                "email": email,
                "connected_at": now,
                "last_activity": now,
                "ttl": ttl,
            }
        )

        print(f"Saved connection: {connection_id}")

    except ClientError as e:
        print(f"Error saving connection: {str(e)}")
        raise
