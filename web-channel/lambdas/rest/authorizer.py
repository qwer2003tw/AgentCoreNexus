"""
Lambda Authorizer for REST API
Validates JWT tokens and generates IAM policies
"""

import json
import os
from typing import Any

import boto3

# Initialize AWS clients
secretsmanager = boto3.client("secretsmanager")

# Environment variables
JWT_SECRET_ARN = os.environ["JWT_SECRET_ARN"]


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Lambda Authorizer handler

    Args:
        event: API Gateway authorizer event
        context: Lambda context

    Returns:
        IAM policy document
    """
    token = event.get("authorizationToken", "")
    method_arn = event.get("methodArn", "")

    print("Authorizing request")

    # Remove 'Bearer ' prefix
    if token.startswith("Bearer "):
        token = token[7:]

    try:
        # Verify JWT token
        user_info = verify_jwt_token(token)

        if user_info:
            # Token valid - generate Allow policy
            email = user_info["email"]
            role = user_info["role"]

            print(f"Authorization granted for: {email}")

            return generate_policy(
                principal_id=email,
                effect="Allow",
                resource=method_arn,
                context={"email": email, "role": role},
            )
        else:
            # Token invalid - generate Deny policy
            print("Authorization denied: Invalid token")
            return generate_policy(principal_id="user", effect="Deny", resource=method_arn)

    except Exception as e:
        print(f"Error in authorizer: {str(e)}")
        import traceback

        traceback.print_exc()
        # Deny on error
        return generate_policy(principal_id="user", effect="Deny", resource=method_arn)


def verify_jwt_token(token: str) -> dict[str, Any] | None:
    """
    Verify JWT token

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


def generate_policy(
    principal_id: str, effect: str, resource: str, context: dict[str, str] | None = None
) -> dict[str, Any]:
    """
    Generate IAM policy document

    Args:
        principal_id: Principal identifier
        effect: 'Allow' or 'Deny'
        resource: Resource ARN
        context: Optional context to pass to backend

    Returns:
        Policy document
    """
    policy = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{"Action": "execute-api:Invoke", "Effect": effect, "Resource": resource}],
        },
    }

    # Add context if provided
    if context:
        policy["context"] = context

    return policy
