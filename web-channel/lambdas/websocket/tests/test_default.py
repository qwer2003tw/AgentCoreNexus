"""Tests for WebSocket default handler"""

import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from default import (
    auto_assign_conversation_id,
    create_new_conversation,
    create_unified_message,
    get_connection,
    handler,
    update_connection_activity,
)


@pytest.fixture
def test_connection(dynamodb_tables):
    """Create a test connection"""
    conn_table = dynamodb_tables["connections"]
    conn_data = {
        "connection_id": "test-conn-123",
        "unified_user_id": "test-user-uuid",
        "email": "test@example.com",
        "connected_at": datetime.now(UTC).isoformat(),
    }
    conn_table.put_item(Item=conn_data)
    return conn_data


@pytest.fixture
def mock_eventbridge():
    """Mock EventBridge client"""
    with patch("default.eventbridge") as mock_eb:
        mock_eb.put_events.return_value = {"FailedEntryCount": 0}
        yield mock_eb


@pytest.mark.unit
def test_handler_with_valid_message(dynamodb_tables, test_connection, mock_eventbridge):
    """Test successful message handling"""
    import os

    os.environ["EVENT_BUS_NAME"] = "test-event-bus"

    event = {
        "requestContext": {"connectionId": "test-conn-123"},
        "body": json.dumps({"message": "Hello, world!", "conversation_id": "conv-123"}),
    }

    response = handler(event, None)

    assert response["statusCode"] == 200
    assert response["body"] == "Message sent"

    # Verify EventBridge was called
    assert mock_eventbridge.put_events.called
    call_args = mock_eventbridge.put_events.call_args[1]
    entries = call_args["Entries"]
    assert len(entries) == 1
    assert entries[0]["Source"] == "universal-adapter"
    assert entries[0]["DetailType"] == "message.received"


@pytest.mark.unit
def test_handler_without_message(dynamodb_tables, test_connection):
    """Test handler fails without message text"""
    event = {"requestContext": {"connectionId": "test-conn-123"}, "body": json.dumps({})}

    response = handler(event, None)

    assert response["statusCode"] == 400
    assert "Missing message" in response["body"]


@pytest.mark.unit
def test_handler_with_attachments_only(dynamodb_tables, test_connection, mock_eventbridge):
    """Test handler accepts attachments without text"""
    import os

    os.environ["EVENT_BUS_NAME"] = "test-event-bus"

    event = {
        "requestContext": {"connectionId": "test-conn-123"},
        "body": json.dumps(
            {
                "attachments": [
                    {
                        "id": "att-1",
                        "name": "report.pdf",
                        "size": 1024,
                        "content_type": "application/pdf",
                        "key": "attachments/user-1/att-1/report.pdf",
                    }
                ],
                "conversation_id": "conv-123",
            }
        ),
    }

    response = handler(event, None)

    assert response["statusCode"] == 200
    assert response["body"] == "Message sent"


@pytest.mark.unit
def test_handler_with_invalid_connection(dynamodb_tables):
    """Test handler fails with non-existent connection"""
    event = {
        "requestContext": {"connectionId": "invalid-conn"},
        "body": json.dumps({"message": "Test"}),
    }

    response = handler(event, None)

    assert response["statusCode"] == 404
    assert "Connection not found" in response["body"]


@pytest.mark.unit
def test_handler_auto_assigns_conversation_id(dynamodb_tables, test_connection, mock_eventbridge):
    """Test handler auto-assigns conversation_id when not provided"""
    import os

    os.environ["EVENT_BUS_NAME"] = "test-event-bus"

    event = {
        "requestContext": {"connectionId": "test-conn-123"},
        "body": json.dumps({"message": "Hello!"}),  # No conversation_id
    }

    response = handler(event, None)

    assert response["statusCode"] == 200

    # Verify EventBridge message includes conversation_id
    call_args = mock_eventbridge.put_events.call_args[1]
    detail = json.loads(call_args["Entries"][0]["Detail"])
    assert "conversation_id" in detail
    assert detail["conversation_id"]  # Should not be empty


@pytest.mark.unit
def test_get_connection(dynamodb_tables, test_connection):
    """Test getting connection from DynamoDB"""
    conn = get_connection("test-conn-123")

    assert conn is not None
    assert conn["connection_id"] == "test-conn-123"
    assert conn["email"] == "test@example.com"


@pytest.mark.unit
def test_get_connection_not_found(dynamodb_tables):
    """Test getting non-existent connection"""
    conn = get_connection("non-existent")

    assert conn is None


@pytest.mark.unit
def test_create_unified_message():
    """Test unified message creation"""
    message = create_unified_message(
        unified_user_id="user-123",
        connection_id="conn-456",
        email="test@example.com",
        message_text="Test message",
        role="user",
        conversation_id="conv-789",
        attachments=[
            {
                "id": "att-1",
                "name": "image.png",
                "size": 2048,
                "content_type": "image/png",
                "key": "attachments/user-123/att-1/image.png",
            }
        ],
        message_type="attachments",
    )

    assert message["user"]["unified_user_id"] == "user-123"
    assert message["channel"]["channel_id"] == "conn-456"
    assert message["content"]["text"] == "Test message"
    assert message["content"]["attachments"][0]["name"] == "image.png"
    assert message["conversation_id"] == "conv-789"
    assert "message_id" in message
    assert "timestamp" in message


@pytest.mark.unit
def test_update_connection_activity(dynamodb_tables, test_connection):
    """Test connection activity update"""
    update_connection_activity("test-conn-123")

    # Verify last_activity was updated
    conn_table = dynamodb_tables["connections"]
    result = conn_table.get_item(Key={"connection_id": "test-conn-123"})
    assert "last_activity" in result["Item"]


@pytest.mark.unit
def test_auto_assign_conversation_id_creates_new(dynamodb_tables):
    """Test auto-assign creates new conversation when none recent"""
    conv_id = auto_assign_conversation_id("test-user-uuid")

    # Should return a UUID
    assert len(conv_id) == 36
    assert "-" in conv_id

    # Verify conversation created in DynamoDB
    conv_table = dynamodb_tables["conversations"]
    result = conv_table.get_item(
        Key={"unified_user_id": "test-user-uuid", "conversation_id": conv_id}
    )
    assert "Item" in result
    assert result["Item"]["title"] == "New Chat"


@pytest.mark.unit
def test_auto_assign_conversation_id_returns_recent(dynamodb_tables):
    """Test auto-assign returns recent conversation if exists"""
    # Create a recent conversation
    conv_table = dynamodb_tables["conversations"]
    recent_conv_id = "recent-conv-123"
    now = datetime.now(UTC).isoformat()

    conv_table.put_item(
        Item={
            "unified_user_id": "test-user-uuid",
            "conversation_id": recent_conv_id,
            "title": "Existing Chat",
            "created_at": now,
            "last_message_time": now,
            "message_count": 5,
            "is_deleted": False,
        }
    )

    # Auto-assign should return this conversation
    result = auto_assign_conversation_id("test-user-uuid")

    assert result == recent_conv_id


@pytest.mark.unit
def test_create_new_conversation(dynamodb_tables):
    """Test new conversation creation"""
    conv_id = create_new_conversation("test-user-uuid")

    # Should return a UUID
    assert len(conv_id) == 36

    # Verify conversation created
    conv_table = dynamodb_tables["conversations"]
    result = conv_table.get_item(
        Key={"unified_user_id": "test-user-uuid", "conversation_id": conv_id}
    )
    assert "Item" in result
    assert result["Item"]["title"] == "New Chat"
    assert result["Item"]["is_pinned"] is False
    assert result["Item"]["is_deleted"] is False
