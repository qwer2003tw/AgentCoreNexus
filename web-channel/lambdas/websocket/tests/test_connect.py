"""Tests for WebSocket connect handler"""
import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from connect import get_unified_user_id, handler, verify_jwt_token


@pytest.mark.unit
def test_connect_with_valid_token(dynamodb_tables, jwt_secret, test_user, valid_jwt_token):
    """Test successful connection with valid JWT"""
    # Create event
    event = {
        "requestContext": {"connectionId": "test-conn-123"},
        "queryStringParameters": {"token": valid_jwt_token},
    }

    # Execute
    response = handler(event, None)

    # Assert
    assert response["statusCode"] == 200
    assert response["body"] == "Connected"

    # Verify connection saved in DynamoDB
    conn_table = dynamodb_tables["connections"]
    result = conn_table.get_item(Key={"connection_id": "test-conn-123"})
    assert "Item" in result
    assert result["Item"]["email"] == "test@example.com"
    assert "unified_user_id" in result["Item"]
    assert "ttl" in result["Item"]


@pytest.mark.unit
def test_connect_without_token(dynamodb_tables, jwt_secret):
    """Test connection fails without JWT token"""
    event = {"requestContext": {"connectionId": "test-conn-456"}, "queryStringParameters": {}}

    response = handler(event, None)

    assert response["statusCode"] == 401
    assert "Unauthorized" in response["body"]


@pytest.mark.unit
def test_connect_with_expired_token(dynamodb_tables, jwt_secret):
    """Test connection fails with expired JWT"""
    # Create expired token
    token = jwt.encode(
        {"sub": "test@example.com", "exp": datetime.now(UTC) - timedelta(days=1)},  # Expired
        "test-secret-key-123",
        algorithm="HS256",
    )

    event = {
        "requestContext": {"connectionId": "test-conn-789"},
        "queryStringParameters": {"token": token},
    }

    response = handler(event, None)

    assert response["statusCode"] == 401
    assert "Unauthorized" in response["body"]


@pytest.mark.unit
def test_connect_with_disabled_user(dynamodb_tables, jwt_secret):
    """Test connection fails for disabled user"""
    # Add disabled user
    users_table = dynamodb_tables["users"]
    users_table.put_item(Item={"email": "disabled@example.com", "enabled": False, "role": "user"})

    token = jwt.encode(
        {"sub": "disabled@example.com", "exp": datetime.now(UTC) + timedelta(days=1)},
        "test-secret-key-123",
        algorithm="HS256",
    )

    event = {
        "requestContext": {"connectionId": "test-conn-999"},
        "queryStringParameters": {"token": token},
    }

    response = handler(event, None)

    assert response["statusCode"] == 401
    assert "disabled" in response["body"].lower()


@pytest.mark.unit
def test_get_unified_user_id_creates_new_binding(dynamodb_tables):
    """Test unified_user_id creation for new user"""
    result = get_unified_user_id("newuser@example.com")

    # Should return a UUID
    assert len(result) == 36  # UUID format
    assert "-" in result  # UUID contains hyphens

    # Verify binding created in DynamoDB
    bindings_table = dynamodb_tables["bindings"]
    response = bindings_table.query(
        IndexName="web_email-index",
        KeyConditionExpression="web_email = :email",
        ExpressionAttributeValues={":email": "newuser@example.com"},
    )

    assert len(response["Items"]) == 1
    assert response["Items"][0]["unified_user_id"] == result
    assert response["Items"][0]["binding_status"] == "web_only"


@pytest.mark.unit
def test_get_unified_user_id_returns_existing_binding(dynamodb_tables):
    """Test unified_user_id retrieval for existing user"""
    # Create existing binding
    bindings_table = dynamodb_tables["bindings"]
    existing_id = "existing-uuid-12345"
    bindings_table.put_item(
        Item={
            "unified_user_id": existing_id,
            "web_email": "existing@example.com",
            "binding_status": "web_only",
        }
    )

    # Get unified_user_id
    result = get_unified_user_id("existing@example.com")

    # Should return existing ID
    assert result == existing_id


@pytest.mark.unit
def test_verify_jwt_token_valid(jwt_secret, valid_jwt_token):
    """Test JWT verification with valid token"""
    user_info = verify_jwt_token(valid_jwt_token)

    assert user_info is not None
    assert user_info["email"] == "test@example.com"
    assert user_info["role"] == "user"
    assert "exp" in user_info


@pytest.mark.unit
def test_verify_jwt_token_expired(jwt_secret):
    """Test JWT verification with expired token"""
    expired_token = jwt.encode(
        {"sub": "test@example.com", "exp": datetime.now(UTC) - timedelta(days=1)},
        "test-secret-key-123",
        algorithm="HS256",
    )

    user_info = verify_jwt_token(expired_token)

    assert user_info is None


@pytest.mark.unit
def test_verify_jwt_token_invalid(jwt_secret):
    """Test JWT verification with invalid token"""
    user_info = verify_jwt_token("invalid.token.here")

    assert user_info is None