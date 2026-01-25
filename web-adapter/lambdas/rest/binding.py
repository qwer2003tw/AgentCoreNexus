"""
Binding REST API Lambda - Phase 2
Handles identity binding using IdentityService

Flow:
1. Telegram: /bind generates 6-digit code
2. Web: enters code -> calls verify_and_bind()
3. System: creates unified_conversation_id
"""

import json
import os
import sys
from typing import Any

# Import IdentityService from Lambda Layer
sys.path.insert(0, "/opt/python")
from identity_service import IdentityService

# Initialize IdentityService
BINDING_CODES_TABLE = os.environ["BINDING_CODES_TABLE"]
IDENTITY_MAP_TABLE = os.environ["IDENTITY_MAP_TABLE"]

identity_service = IdentityService(
    binding_codes_table_name=BINDING_CODES_TABLE, identity_map_table_name=IDENTITY_MAP_TABLE
)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main handler for binding operations

    Endpoints:
    - POST /binding/verify: Verify binding code and bind identities
    - GET /binding/status: Get binding status
    - DELETE /binding/unbind: Unbind identity

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
        if path == "/binding/verify" and method == "POST":
            return handle_verify_code(email, event)

        elif path == "/binding/status" and method == "GET":
            return handle_get_status(email)

        elif path == "/binding/unbind" and method == "DELETE":
            return handle_unbind(email)

        else:
            return response(404, {"error": "Not found"})

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return response(500, {"error": "Internal server error"})


def handle_verify_code(email: str, event: dict[str, Any]) -> dict[str, Any]:
    """
    Verify binding code and bind Web user to Telegram user

    Args:
        email: Web user email
        event: API Gateway event (contains body with code)

    Returns:
        Binding result
    """
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        code = body.get("code", "").strip()

        if not code:
            return response(400, {"error": "Binding code is required"})

        if len(code) != 6 or not code.isdigit():
            return response(400, {"error": "Invalid code format (must be 6 digits)"})

        # Use IdentityService to verify and bind
        result = identity_service.verify_and_bind(code=code, web_user_id=email, web_email=email)

        print(f"Binding successful: {email} -> {result['unified_conversation_id']}")

        return response(
            200,
            {
                "success": result["success"],
                "unified_conversation_id": result["unified_conversation_id"],
                "telegram_user_id": result["telegram_user_id"],
                "message": "Binding successful! Your Telegram and Web accounts are now linked.",
            },
        )

    except ValueError as e:
        # IdentityService raises ValueError for invalid/expired/used codes
        error_msg = str(e)
        print(f"Binding failed: {error_msg}")

        if "Invalid binding code" in error_msg:
            return response(404, {"error": "Invalid binding code"})
        elif "expired" in error_msg:
            return response(400, {"error": "Binding code has expired"})
        elif "already used" in error_msg:
            return response(400, {"error": "Binding code has already been used"})
        else:
            return response(400, {"error": error_msg})

    except Exception as e:
        print(f"Error verifying code: {str(e)}")
        import traceback

        traceback.print_exc()
        return response(500, {"error": "Failed to verify binding code"})


def handle_get_status(email: str) -> dict[str, Any]:
    """
    Get binding status for Web user

    Args:
        email: Web user email

    Returns:
        Binding status and bound identities
    """
    try:
        web_identity_id = f"web:{email}"
        bindings = identity_service.get_bindings(web_identity_id)

        if not bindings:
            return response(
                200,
                {
                    "bound": False,
                    "message": "No binding found. Use /bind command in Telegram to get a binding code.",
                },
            )

        # Format bound identities
        bound_identities = []
        for identity in bindings.get("bound_identities", []):
            bound_identities.append(
                {
                    "platform": identity.get("platform"),
                    "user_id": identity.get("user_id"),
                    "identity_id": identity.get("identity_id"),
                    "bound_at": identity.get("bound_at"),
                }
            )

        return response(
            200,
            {
                "bound": True,
                "identity_id": web_identity_id,
                "unified_conversation_id": bindings.get("unified_conversation_id"),
                "telegram_bound": any(b["platform"] == "telegram" for b in bound_identities),
                "bound_identities": bound_identities,
                "created_at": bindings.get("metadata", {}).get("bound_at"),
            },
        )

    except Exception as e:
        print(f"Error getting binding status: {str(e)}")
        import traceback

        traceback.print_exc()
        return response(500, {"error": "Failed to get binding status"})


def handle_unbind(email: str) -> dict[str, Any]:
    """
    Unbind Web user identity

    Args:
        email: Web user email

    Returns:
        Unbind result
    """
    try:
        web_identity_id = f"web:{email}"
        success = identity_service.unbind(web_identity_id)

        if success:
            print(f"Unbind successful: {email}")
            return response(
                200,
                {"success": True, "message": "Your Web identity has been unbound from Telegram."},
            )
        else:
            return response(404, {"success": False, "message": "No binding found to unbind."})

    except Exception as e:
        print(f"Error unbinding: {str(e)}")
        import traceback

        traceback.print_exc()
        return response(500, {"error": "Failed to unbind identity"})


# ============================================================
# Helper Functions
# ============================================================


def extract_email_from_token(event: dict[str, Any]) -> str | None:
    """Extract email from JWT token"""
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
