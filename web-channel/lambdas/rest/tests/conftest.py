"""Shared test fixtures for REST Lambda"""

import json
import os
from datetime import UTC, datetime

# Set environment variables before any imports
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["WEB_USERS_TABLE"] = "test-web-users"
os.environ["JWT_SECRET_ARN"] = "test-jwt-secret"

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

        # Web users table
        users_table = dynamodb.create_table(
            TableName="test-web-users",
            KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        os.environ["WEB_USERS_TABLE"] = "test-web-users"

        yield {"users": users_table}


@pytest.fixture(scope="function")
def jwt_secret(aws_credentials):
    """Create mock JWT secret in Secrets Manager"""
    with mock_aws():
        client = boto3.client("secretsmanager", region_name="us-east-1")
        client.create_secret(
            Name="test-jwt-secret",
            SecretString=json.dumps(
                {
                    "jwt_secret": "test-secret-key-123",
                    "jwt_algorithm": "HS256",
                    "jwt_expiry_days": 7,
                }
            ),
        )

        os.environ["JWT_SECRET_ARN"] = "test-jwt-secret"

        yield "test-jwt-secret"


@pytest.fixture
def test_user(dynamodb_tables):
    """Create a test user with mock hashed password"""
    users_table = dynamodb_tables["users"]

    # Use a pre-computed bcrypt hash for "testpass123"
    # This avoids needing bcrypt library during test collection
    password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYqY5GyYq"

    user_data = {
        "email": "test@example.com",
        "password_hash": password_hash,
        "enabled": True,
        "role": "user",
        "created_at": datetime.now(UTC).isoformat(),
    }
    users_table.put_item(Item=user_data)
    return user_data


@pytest.fixture
def api_event():
    """Create a sample API Gateway event"""
    return {
        "httpMethod": "POST",
        "path": "/auth/login",
        "headers": {},
        "body": json.dumps({"email": "test@example.com", "password": "testpass123"}),
    }
