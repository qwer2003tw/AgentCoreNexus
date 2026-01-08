"""
Binding REST API Lambda
Handles account binding operations
"""

import json
import os
import random
from datetime import UTC, datetime
from typing import Any

import boto3

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")

# Environment variables
BINDINGS_TABLE = os.environ["BINDINGS_TABLE"]
BINDING_CODES_TABLE = os.environ["BINDING_CODES_TABLE"]

# DynamoDB tables
bindings_table = dynamodb.Table(BINDINGS_TABLE)
binding_codes_table = dynamodb.Table(BINDING_CODES_TABLE)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main handler for binding operations

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    path = event.get("path", "")
    method = event.get("httpMethod", "")

    print(f"{method} {path}")

    # Extract email from JWT
    email = extract_email_from_token(event)
    if not email:
        return response(401, {"error": "Unauthorized"})

    try:
        if path == "/binding/generate-code" and method == "POST":
            return handle_generate_code(email)

        elif path == "/binding/status" and method == "GET":
            return handle_get_status(email)

        else:
            return response(404, {"error": "Not found"})

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return response(500, {"error": "Internal server error"})


def handle_generate_code(email: str) -> dict[str, Any]:
    """
    Generate a 6-digit binding code for web user

    Args:
        email: User email

    Returns:
        Binding code and expiry time
    """
    try:
        # Check if user already has an active code
        existing_codes = get_active_codes(email)
        if existing_codes:
            # Return existing code
            code_item = existing_codes[0]
            return response(
                200,
                {
                    "code": code_item["code"],
                    "expires_at": code_item["expires_at"],
                    "expires_in": 300,
                    "message": "Use this code in Telegram with /bind command",
                },
            )

        # Generate new 6-digit code
        code = generate_6_digit_code()

        # Ensure code is unique
        while code_exists(code):
            code = generate_6_digit_code()

        # Calculate expiry (5 minutes)
        now = datetime.now(UTC)
        expires_at = now.timestamp() + 300
        expires_at_iso = datetime.fromtimestamp(expires_at, tz=UTC).isoformat()
        ttl = int(expires_at) + 300  # TTL = expiry + 5 min buffer

        # Save code to DynamoDB
        binding_codes_table.put_item(
            Item={
                "code": code,
                "web_email": email,
                "created_at": now.isoformat(),
                "expires_at": expires_at_iso,
                "status": "pending",
                "ttl": ttl,
            }
        )

        print(f"Generated binding code for {email}: {code}")

        return response(
            200,
            {
                "code": code,
                "expires_at": expires_at_iso,
                "expires_in": 300,
                "message": "Use this code in Telegram with /bind command within 5 minutes",
            },
        )

    except Exception as e:
        print(f"Error generating code: {str(e)}")
        return response(500, {"error": "Failed to generate binding code"})


def handle_get_status(email: str) -> dict[str, Any]:
    """
    Get binding status for user

    Args:
        email: User email

    Returns:
        Binding status information
    """
    try:
        # Query bindings by web_email
        result = bindings_table.query(
            IndexName="web_email-index",
            KeyConditionExpression="web_email = :email",
            ExpressionAttributeValues={":email": email},
        )

        items = result.get("Items", [])

        if not items:
            return response(200, {"bound": False, "message": "No binding found"})

        binding = items[0]

        has_telegram = binding.get("telegram_chat_id") is not None

        return response(
            200,
            {
                "bound": has_telegram,
                "unified_user_id": binding["unified_user_id"],
                "telegram_bound": has_telegram,
                "binding_status": binding.get("binding_status", "unknown"),
                "created_at": binding.get("created_at"),
            },
        )

    except Exception as e:
        print(f"Error getting binding status: {str(e)}")
        return response(500, {"error": "Failed to get binding status"})


# ============================================================
# Helper Functions
# ============================================================


def generate_6_digit_code() -> str:
    """Generate a random 6-digit code"""
    return f"{random.randint(0, 999999):06d}"


def code_exists(code: str) -> bool:
    """Check if code already exists in database"""
    try:
        result = binding_codes_table.get_item(Key={"code": code})
        return "Item" in result
    except Exception:
        return False


def get_active_codes(email: str) -> list[dict[str, Any]]:
    """
    Get active (non-expired, pending) codes for email

    Args:
        email: User email

    Returns:
        List of active codes
    """
    try:
        now = datetime.now(UTC).isoformat()

        result = binding_codes_table.query(
            IndexName="web_email-index",
            KeyConditionExpression="web_email = :email",
            FilterExpression="expires_at > :now AND #status = :pending",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":email": email, ":now": now, ":pending": "pending"},
        )

        return result.get("Items", [])

    except Exception as e:
        print(f"Error getting active codes: {str(e)}")
        return []


def extract_email_from_token(event: dict[str, Any]) -> str | None:
    """Extract email from JWT token (simplified)"""
    authorizer = event.get("requestContext", {}).get("authorizer", {})
    return authorizer.get("email")


def response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Create API Gateway response"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
