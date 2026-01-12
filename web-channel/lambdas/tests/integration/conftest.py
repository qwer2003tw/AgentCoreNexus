"""Shared fixtures for integration tests"""

import json
import os
import sys
from datetime import UTC, datetime, timedelta

# Set environment variables before any imports
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["CONNECTIONS_TABLE"] = "test-connections"
os.environ["WEB_USERS_TABLE"] = "test-web-users"
os.environ["BINDINGS_TABLE"] = "test-bindings"
os.environ["CONVERSATIONS_TABLE"] = "test-conversations"
os.environ["HISTORY_TABLE"] = "test-history"
os.environ["JWT_SECRET_ARN"] = "test-jwt-secret"
os.environ["EVENT_BUS_NAME"] = "test-event-bus"
os.environ["WEBSOCKET_API_ENDPOINT"] = "wss://test.execute-api.us-east-1.amazonaws.com/test"

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../websocket"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../rest"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../router"))

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(scope="function")
def aws_environment():
    """Complete AWS environment with all services"""
    with mock_aws():
        # Setup DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Connections table
        connections_table = dynamodb.create_table(
            TableName="test-connections",
            KeySchema=[{"AttributeName": "connection_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "connection_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Web users table
        users_table = dynamodb.create_table(
            TableName="test-web-users",
            KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Bindings table with GSI
        bindings_table = dynamodb.create_table(
            TableName="test-bindings",
            KeySchema=[{"AttributeName": "unified_user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "unified_user_id", "AttributeType": "S"},
                {"AttributeName": "web_email", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "web_email-index",
                    "KeySchema": [{"AttributeName": "web_email", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Conversations table with GSI
        conversations_table = dynamodb.create_table(
            TableName="test-conversations",
            KeySchema=[
                {"AttributeName": "unified_user_id", "KeyType": "HASH"},
                {"AttributeName": "conversation_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "unified_user_id", "AttributeType": "S"},
                {"AttributeName": "conversation_id", "AttributeType": "S"},
                {"AttributeName": "last_message_time", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "user-by-time-index",
                    "KeySchema": [
                        {"AttributeName": "unified_user_id", "KeyType": "HASH"},
                        {"AttributeName": "last_message_time", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # History table
        history_table = dynamodb.create_table(
            TableName="test-history",
            KeySchema=[
                {"AttributeName": "unified_user_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp_msgid", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "unified_user_id", "AttributeType": "S"},
                {"AttributeName": "timestamp_msgid", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Setup Secrets Manager
        secrets_client = boto3.client("secretsmanager", region_name="us-east-1")
        secrets_client.create_secret(
            Name="test-jwt-secret",
            SecretString=json.dumps(
                {
                    "jwt_secret": "test-secret-key-123",
                    "jwt_algorithm": "HS256",
                    "jwt_expiry_days": 7,
                }
            ),
        )

        yield {
            "connections": connections_table,
            "users": users_table,
            "bindings": bindings_table,
            "conversations": conversations_table,
            "history": history_table,
        }


@pytest.fixture
def test_user_with_binding(aws_environment):
    """Create a test user with binding"""
    users_table = aws_environment["users"]
    bindings_table = aws_environment["bindings"]

    # Create user (use pre-computed bcrypt hash)
    password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYqY5GyYq"
    users_table.put_item(
        Item={
            "email": "test@example.com",
            "password_hash": password_hash,
            "enabled": True,
            "role": "user",
            "created_at": datetime.now(UTC).isoformat(),
        }
    )

    # Create binding
    unified_user_id = "test-unified-user-123"
    bindings_table.put_item(
        Item={
            "unified_user_id": unified_user_id,
            "web_email": "test@example.com",
            "binding_status": "web_only",
            "created_at": datetime.now(UTC).isoformat(),
        }
    )

    return {
        "email": "test@example.com",
        "unified_user_id": unified_user_id,
        "password": "testpass123",
    }


@pytest.fixture
def valid_jwt_token():
    """Generate a valid JWT token"""
    import jwt

    payload = {
        "sub": "test@example.com",
        "role": "user",
        "exp": datetime.now(UTC) + timedelta(days=1),
    }
    return jwt.encode(payload, "test-secret-key-123", algorithm="HS256")
