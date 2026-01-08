"""
Authentication REST API Lambda
Handles login, logout, and password management
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
secretsmanager = boto3.client("secretsmanager")

# Environment variables
WEB_USERS_TABLE = os.environ["WEB_USERS_TABLE"]
JWT_SECRET_ARN = os.environ["JWT_SECRET_ARN"]

# DynamoDB table
web_users_table = dynamodb.Table(WEB_USERS_TABLE)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main handler for authentication operations
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    
    print(f"{method} {path}")
    
    try:
        body = json.loads(event.get("body", "{}"))
        
        if path == "/auth/login" and method == "POST":
            return handle_login(body)
        
        elif path == "/auth/logout" and method == "POST":
            return handle_logout(event)
        
        elif path == "/auth/change-password" and method == "POST":
            return handle_change_password(event, body)
        
        elif path == "/auth/me" and method == "GET":
            return handle_get_user(event)
        
        else:
            return response(404, {"error": "Not found"})
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return response(500, {"error": "Internal server error"})


def handle_login(body: dict[str, Any]) -> dict[str, Any]:
    """
    Handle login request
    
    Args:
        body: Request body with email and password
        
    Returns:
        API Gateway response with JWT token
    """
    email = body.get("email", "").lower().strip()
    password = body.get("password", "")
    
    if not email or not password:
        return response(400, {"error": "Missing email or password"})
    
    # Validate email format
    if not is_valid_email(email):
        return response(400, {"error": "Invalid email format"})
    
    # Check rate limiting
    if is_rate_limited(email):
        return response(429, {"error": "Too many login attempts. Please try again later."})
    
    # Get user from database
    user = get_web_user(email)
    if not user:
        # Record failed attempt
        record_failed_login(email)
        return response(401, {"error": "Invalid credentials"})
    
    # Check if user is enabled
    if not user.get("enabled", False):
        return response(403, {"error": "Account disabled"})
    
    # Verify password
    import bcrypt
    password_hash = user.get("password_hash", "")
    
    try:
        if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
            # Record failed attempt
            record_failed_login(email)
            return response(401, {"error": "Invalid credentials"})
    except Exception as e:
        print(f"Error verifying password: {str(e)}")
        record_failed_login(email)
        return response(401, {"error": "Invalid credentials"})
    
    # Clear failed attempts
    clear_failed_attempts(email)
    
    # Generate JWT token
    token = generate_jwt_token(email, user.get("role", "user"))
    
    # Update last login
    update_last_login(email)
    
    print(f"Login successful: {email}")
    
    return response(200, {
        "token": token,
        "user": {
            "email": email,
            "role": user.get("role", "user"),
            "require_password_change": user.get("require_password_change", False)
        }
    })


def handle_logout(event: dict[str, Any]) -> dict[str, Any]:
    """
    Handle logout request
    
    Args:
        event: API Gateway event with Authorization header
        
    Returns:
        API Gateway response
    """
    # For JWT-based auth, logout is client-side (remove token from localStorage)
    # Server-side: could invalidate token but we'll keep it simple for MVP
    
    return response(200, {"message": "Logged out successfully"})


def handle_change_password(event: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    """
    Handle password change request
    
    Args:
        event: API Gateway event with Authorization header
        body: Request body with old and new passwords
        
    Returns:
        API Gateway response
    """
    # Extract email from JWT token
    email = extract_email_from_token(event)
    if not email:
        return response(401, {"error": "Unauthorized"})
    
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")
    
    if not old_password or not new_password:
        return response(400, {"error": "Missing old or new password"})
    
    # Validate new password strength
    validation_error = validate_password_strength(new_password)
    if validation_error:
        return response(400, {"error": validation_error})
    
    # Get user
    user = get_web_user(email)
    if not user:
        return response(404, {"error": "User not found"})
    
    # Verify old password
    import bcrypt
    password_hash = user.get("password_hash", "")
    
    try:
        if not bcrypt.checkpw(old_password.encode("utf-8"), password_hash.encode("utf-8")):
            return response(401, {"error": "Invalid old password"})
    except Exception as e:
        print(f"Error verifying old password: {str(e)}")
        return response(401, {"error": "Invalid old password"})
    
    # Hash new password
    new_password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    
    # Update password in database
    try:
        web_users_table.update_item(
            Key={"email": email},
            UpdateExpression="SET password_hash = :hash, require_password_change = :false",
            ExpressionAttributeValues={
                ":hash": new_password_hash.decode("utf-8"),
                ":false": False
            }
        )
        
        print(f"Password changed: {email}")
        return response(200, {"message": "Password changed successfully"})
        
    except ClientError as e:
        print(f"Error updating password: {str(e)}")
        return response(500, {"error": "Failed to update password"})


def handle_get_user(event: dict[str, Any]) -> dict[str, Any]:
    """
    Get current user information
    
    Args:
        event: API Gateway event with Authorization header
        
    Returns:
        User information
    """
    email = extract_email_from_token(event)
    if not email:
        return response(401, {"error": "Unauthorized"})
    
    user = get_web_user(email)
    if not user:
        return response(404, {"error": "User not found"})
    
    return response(200, {
        "email": email,
        "role": user.get("role", "user"),
        "require_password_change": user.get("require_password_change", False),
        "created_at": user.get("created_at")
    })


# ============================================================
# Helper Functions
# ============================================================

def generate_jwt_token(email: str, role: str) -> str:
    """
    Generate JWT token for user
    
    Args:
        email: User email
        role: User role
        
    Returns:
        JWT token string
    """
    import jwt
    
    # Get JWT secret
    secret_response = secretsmanager.get_secret_value(SecretId=JWT_SECRET_ARN)
    secret_data = json.loads(secret_response["SecretString"])
    jwt_secret = secret_data["jwt_secret"]
    jwt_algorithm = secret_data.get("jwt_algorithm", "HS256")
    jwt_expiry_days = int(secret_data.get("jwt_expiry_days", 7))
    
    # Create payload
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=jwt_expiry_days)
    
    payload = {
        "sub": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expiry.timestamp())
    }
    
    # Generate token
    token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)
    
    return token


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
        
        # Get JWT secret
        secret_response = secretsmanager.get_secret_value(SecretId=JWT_SECRET_ARN)
        secret_data = json.loads(secret_response["SecretString"])
        jwt_secret = secret_data["jwt_secret"]
        jwt_algorithm = secret_data.get("jwt_algorithm", "HS256")
        
        # Decode token
        payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
        return payload.get("sub")
        
    except Exception as e:
        print(f"Error extracting email from token: {str(e)}")
        return None


def get_web_user(email: str) -> dict[str, Any] | None:
    """Get web user from DynamoDB"""
    try:
        response = web_users_table.get_item(Key={"email": email})
        return response.get("Item")
    except ClientError as e:
        print(f"Error getting web user: {str(e)}")
        return None


def update_last_login(email: str) -> None:
    """Update user's last login timestamp"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        web_users_table.update_item(
            Key={"email": email},
            UpdateExpression="SET last_login = :now",
            ExpressionAttributeValues={":now": now}
        )
    except ClientError as e:
        print(f"Error updating last login: {str(e)}")


def is_valid_email(email: str) -> bool:
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password_strength(password: str) -> str | None:
    """
    Validate password strength
    
    Returns:
        Error message or None if valid
    """
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number"
    
    return None


# Rate limiting (simple in-memory for MVP, should use DynamoDB for production)
_failed_attempts: dict[str, list[float]] = {}

def is_rate_limited(email: str) -> bool:
    """Check if user is rate limited (5 attempts in 15 minutes)"""
    now = time.time()
    cutoff = now - 900  # 15 minutes ago
    
    # Clean old attempts
    if email in _failed_attempts:
        _failed_attempts[email] = [t for t in _failed_attempts[email] if t > cutoff]
        
        if len(_failed_attempts[email]) >= 5:
            return True
    
    return False


def record_failed_login(email: str) -> None:
    """Record failed login attempt"""
    now = time.time()
    if email not in _failed_attempts:
        _failed_attempts[email] = []
    _failed_attempts[email].append(now)


def clear_failed_attempts(email: str) -> None:
    """Clear failed login attempts for user"""
    if email in _failed_attempts:
        del _failed_attempts[email]


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
        "body": json.dumps(body)
    }