"""
Admin REST API Lambda
Handles user management operations (admin only)
"""

import json
import os
import secrets
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")

# Environment variables
WEB_USERS_TABLE = os.environ["WEB_USERS_TABLE"]
BINDINGS_TABLE = os.environ["BINDINGS_TABLE"]

# DynamoDB tables
web_users_table = dynamodb.Table(WEB_USERS_TABLE)
bindings_table = dynamodb.Table(BINDINGS_TABLE)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main handler for admin operations

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    path = event.get("path", "")
    method = event.get("httpMethod", "")

    print(f"{method} {path}")

    # TODO: Verify admin role from JWT token
    # For now, assuming Lambda Authorizer has validated admin role

    try:
        body = json.loads(event.get("body", "{}")) if event.get("body") else {}

        if path == "/admin/users" and method == "POST":
            return handle_create_user(body)

        elif path == "/admin/users" and method == "GET":
            return handle_list_users(event)

        elif path.startswith("/admin/users/") and "/password" in path and method == "PUT":
            email = extract_email_from_path(path)
            return handle_reset_password(email, body)

        elif path.startswith("/admin/users/") and "/role" in path and method == "PUT":
            email = extract_email_from_path(path)
            return handle_update_role(email, body)

        elif path == "/admin/bindings" and method == "GET":
            return handle_list_bindings(event)

        else:
            return response(404, {"error": "Not found"})

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return response(500, {"error": "Internal server error"})


def handle_create_user(body: dict[str, Any]) -> dict[str, Any]:
    """
    Create a new web user

    Args:
        body: Request body with email and optional role

    Returns:
        API Gateway response with user info and temporary password
    """
    email = body.get("email", "").lower().strip()
    role = body.get("role", "user")

    if not email:
        return response(400, {"error": "Missing email"})

    # Validate email
    if not is_valid_email(email):
        return response(400, {"error": "Invalid email format"})

    # Check if user already exists
    existing_user = get_web_user(email)
    if existing_user:
        return response(409, {"error": "User already exists"})

    # Generate temporary password
    temp_password = generate_temp_password()

    # Hash password
    import bcrypt

    password_hash = bcrypt.hashpw(temp_password.encode("utf-8"), bcrypt.gensalt(rounds=12))

    # Create user in DynamoDB
    now = datetime.now(UTC).isoformat()

    try:
        web_users_table.put_item(
            Item={
                "email": email,
                "password_hash": password_hash.decode("utf-8"),
                "enabled": True,
                "role": role,
                "require_password_change": True,
                "created_at": now,
                "last_login": None,
            }
        )

        print(f"User created: {email} (role: {role})")

        return response(
            201,
            {
                "email": email,
                "role": role,
                "temporary_password": temp_password,
                "require_password_change": True,
                "message": "User created successfully. Provide the temporary password to the user.",
            },
        )

    except ClientError as e:
        print(f"Error creating user: {str(e)}")
        return response(500, {"error": "Failed to create user"})


def handle_list_users(event: dict[str, Any]) -> dict[str, Any]:
    """
    List all web users

    Args:
        event: API Gateway event with optional query parameters

    Returns:
        List of users (without sensitive data)
    """
    try:
        # Get query parameters for pagination
        query_params = event.get("queryStringParameters") or {}
        limit = int(query_params.get("limit", 50))
        last_key = query_params.get("last_key")

        # Scan users table
        scan_kwargs = {"Limit": limit}
        if last_key:
            scan_kwargs["ExclusiveStartKey"] = {"email": last_key}

        result = web_users_table.scan(**scan_kwargs)

        # Remove sensitive data
        users = []
        for item in result.get("Items", []):
            users.append(
                {
                    "email": item["email"],
                    "enabled": item.get("enabled", False),
                    "role": item.get("role", "user"),
                    "created_at": item.get("created_at"),
                    "last_login": item.get("last_login"),
                }
            )

        response_data = {"users": users, "count": len(users)}

        # Include pagination token if there are more results
        if "LastEvaluatedKey" in result:
            response_data["last_key"] = result["LastEvaluatedKey"]["email"]

        return response(200, response_data)

    except Exception as e:
        print(f"Error listing users: {str(e)}")
        return response(500, {"error": "Failed to list users"})


def handle_reset_password(email: str, body: dict[str, Any]) -> dict[str, Any]:
    """
    Reset user password (admin only)

    Args:
        email: User email
        body: Request body (can be empty for auto-generate)

    Returns:
        New temporary password
    """
    if not email:
        return response(400, {"error": "Missing email"})

    # Check if user exists
    user = get_web_user(email)
    if not user:
        return response(404, {"error": "User not found"})

    # Generate new temporary password
    new_password = body.get("new_password") or generate_temp_password()

    # Hash password
    import bcrypt

    password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt(rounds=12))

    # Update password
    try:
        web_users_table.update_item(
            Key={"email": email},
            UpdateExpression="SET password_hash = :hash, require_password_change = :true",
            ExpressionAttributeValues={":hash": password_hash.decode("utf-8"), ":true": True},
        )

        print(f"Password reset for user: {email}")

        return response(
            200,
            {
                "email": email,
                "temporary_password": new_password,
                "message": "Password reset successfully",
            },
        )

    except ClientError as e:
        print(f"Error resetting password: {str(e)}")
        return response(500, {"error": "Failed to reset password"})


def handle_update_role(email: str, body: dict[str, Any]) -> dict[str, Any]:
    """
    Update user role

    Args:
        email: User email
        body: Request body with new role

    Returns:
        API Gateway response
    """
    new_role = body.get("role")

    if new_role not in ["user", "admin"]:
        return response(400, {"error": "Invalid role. Must be 'user' or 'admin'"})

    # Check if user exists
    user = get_web_user(email)
    if not user:
        return response(404, {"error": "User not found"})

    # Update role
    try:
        web_users_table.update_item(
            Key={"email": email},
            UpdateExpression="SET #role = :role",
            ExpressionAttributeNames={"#role": "role"},
            ExpressionAttributeValues={":role": new_role},
        )

        print(f"Role updated for {email}: {new_role}")

        return response(
            200, {"email": email, "role": new_role, "message": "Role updated successfully"}
        )

    except ClientError as e:
        print(f"Error updating role: {str(e)}")
        return response(500, {"error": "Failed to update role"})


def handle_list_bindings(event: dict[str, Any]) -> dict[str, Any]:
    """
    List all user bindings

    Args:
        event: API Gateway event with optional query parameters

    Returns:
        List of bindings
    """
    try:
        query_params = event.get("queryStringParameters") or {}
        limit = int(query_params.get("limit", 50))

        result = bindings_table.scan(Limit=limit)

        bindings = result.get("Items", [])

        return response(200, {"bindings": bindings, "count": len(bindings)})

    except Exception as e:
        print(f"Error listing bindings: {str(e)}")
        return response(500, {"error": "Failed to list bindings"})


# ============================================================
# Helper Functions
# ============================================================


def get_web_user(email: str) -> dict[str, Any] | None:
    """Get web user from DynamoDB"""
    try:
        result = web_users_table.get_item(Key={"email": email})
        return result.get("Item")
    except ClientError as e:
        print(f"Error getting web user: {str(e)}")
        return None


def is_valid_email(email: str) -> bool:
    """Validate email format"""
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def generate_temp_password() -> str:
    """
    Generate a secure temporary password

    Returns:
        12-character password with mixed case, numbers, and symbols
    """
    # Generate 12 character password
    password = secrets.token_urlsafe(12)[:12]

    # Ensure it meets complexity requirements
    if not any(c.isupper() for c in password):
        password = password[0].upper() + password[1:]
    if not any(c.isdigit() for c in password):
        password = password + "1"

    return password


def extract_email_from_path(path: str) -> str:
    """
    Extract email from URL path

    Args:
        path: URL path like /admin/users/user@example.com/password

    Returns:
        Email address
    """
    parts = path.split("/")
    for i, part in enumerate(parts):
        if part == "users" and i + 1 < len(parts):
            return parts[i + 1]
    return ""


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
