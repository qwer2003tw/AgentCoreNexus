"""Integration tests for API Gateway endpoints"""

import jwt
import pytest


@pytest.mark.integration
@pytest.mark.skip(reason="Requires bcrypt compilation - tested in E2E")
def test_auth_endpoint_complete_flow(aws_environment, test_user_with_binding):
    """Test complete authentication flow through API Gateway"""
    # This test would be better done in E2E tests
    # Skipping due to bcrypt compilation issues
    pass


@pytest.mark.integration
def test_jwt_token_lifecycle(aws_environment, test_user_with_binding, valid_jwt_token):
    """Test JWT token generation, validation, and expiration"""
    from auth import extract_email_from_token, generate_jwt_token

    # Generate token
    token = generate_jwt_token("test@example.com", "user")

    # Verify token can be decoded
    payload = jwt.decode(token, "test-secret-key-123", algorithms=["HS256"])
    assert payload["sub"] == "test@example.com"

    # Extract email from token
    event = {"headers": {"Authorization": f"Bearer {token}"}}
    email = extract_email_from_token(event)
    assert email == "test@example.com"

    # Verify expired token fails
    expired_token = jwt.encode(
        {"sub": "test@example.com", "exp": 0},  # Expired in 1970
        "test-secret-key-123",
        algorithm="HS256",
    )

    expired_event = {"headers": {"Authorization": f"Bearer {expired_token}"}}
    result = extract_email_from_token(expired_event)
    assert result is None
