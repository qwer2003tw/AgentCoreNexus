"""Shared test fixtures for WebSocket Lambda"""
import json
import os
from datetime import UTC, datetime, timedelta

# Set environment variables before any imports
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["CONNECTIONS_TABLE"] = "test-connections"
os.environ["WEB_USERS_TABLE"] = "test-web-users"
os.environ["BINDINGS_TABLE"] = "test-bindings"
os.environ["CONVERSATIONS_TABLE"] = "test-conversations"
os.environ["JWT_SECRET_ARN"] = "test-jwt-secret"
os.environ["EVENT_BUS_NAME"] = "test-event-bus"

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(scope="function")
def aws_credentials():
    """Mock AWS Credentials for testing"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def dynamodb_tables(aws_credentials):
    """Create mock DynamoDB tables"""
    with mock_aws():
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

        # Set environment variables
        os.environ["CONNECTIONS_TABLE"] = "test-connections"
        os.environ["WEB_USERS_TABLE"] = "test-web-users"
        os.environ["BINDINGS_TABLE"] = "test-bindings"
        os.environ["CONVERSATIONS_TABLE"] = "test-conversations"

        yield {
            "connections": connections_table,
            "users": users_table,
            "bindings": bindings_table,
            "conversations": conversations_table,
        }


@pytest.fixture(scope="function")
def jwt_secret(aws_credentials):
    """Create mock JWT secret in Secrets Manager"""
    with mock_aws():
        client = boto3.client("secretsmanager", region_name="us-east-1")
        client.create_secret(
            Name="test-jwt-secret",
            SecretString=json.dumps(
                {"jwt_secret": "test-secret-key-123", "jwt_algorithm": "HS256", "jwt_expiry_days": 7}
            ),
        )

        os.environ["JWT_SECRET_ARN"] = "test-jwt-secret"

        yield "test-jwt-secret"


@pytest.fixture
def test_user(dynamodb_tables):
    """Create a test user"""
    users_table = dynamodb_tables["users"]
    user_data = {"email": "test@example.com", "enabled": True, "role": "user"}
    users_table.put_item(Item=user_data)
    return user_data


@pytest.fixture
def valid_jwt_token():
    """Generate a valid JWT token"""
    import jwt

    payload = {
        "sub": "test@example.com",
        "role": "user",
        "exp": datetime.now(UTC) + timedelta(days=1),
    }
    token = jwt.encode(payload, "test-secret-key-123", algorithm="HS256")
    return token