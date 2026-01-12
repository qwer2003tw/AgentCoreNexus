"""Shared test fixtures for Router Lambda"""
import json
import os
from datetime import UTC, datetime

# Set environment variables before any imports
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["CONNECTIONS_TABLE"] = "test-connections"
os.environ["HISTORY_TABLE"] = "test-history"
os.environ["CONVERSATIONS_TABLE"] = "test-conversations"
os.environ["WEBSOCKET_API_ENDPOINT"] = "wss://test123.execute-api.us-east-1.amazonaws.com/test"

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

        # Conversations table
        conversations_table = dynamodb.create_table(
            TableName="test-conversations",
            KeySchema=[
                {"AttributeName": "unified_user_id", "KeyType": "HASH"},
                {"AttributeName": "conversation_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "unified_user_id", "AttributeType": "S"},
                {"AttributeName": "conversation_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        yield {
            "connections": connections_table,
            "history": history_table,
            "conversations": conversations_table,
        }


@pytest.fixture
def sample_event():
    """Create a sample EventBridge event"""
    return {
        "detail": {
            "response": "Hello, this is the AI response!",
            "conversation_id": "conv-123",
            "original": {
                "user": {"unified_user_id": "user-123"},
                "content": {"text": "User message"},
                "channel": {"type": "web", "channel_id": "conn-456"},
                "conversation_id": "conv-123",
                "context": {"conversation_id": "conv-123"},
            },
        }
    }


@pytest.fixture
def test_connection(dynamodb_tables):
    """Create a test WebSocket connection"""
    conn_table = dynamodb_tables["connections"]
    conn_data = {
        "connection_id": "conn-456",
        "unified_user_id": "user-123",
        "email": "test@example.com",
    }
    conn_table.put_item(Item=conn_data)
    return conn_data