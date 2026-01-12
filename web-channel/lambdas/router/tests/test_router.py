"""Tests for Router Lambda"""
import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from router import (
    handler,
    save_conversation_history,
    send_to_websocket,
    update_conversation_metadata,
)


@pytest.mark.unit
def test_handler_success(dynamodb_tables, sample_event, test_connection):
    """Test successful event handling"""
    with patch("router.send_to_websocket") as mock_send:
        response = handler(sample_event, None)

        assert response["statusCode"] == 200
        assert response["body"] == "Success"

        # Verify WebSocket send was called
        assert mock_send.called


@pytest.mark.unit
def test_handler_without_response(dynamodb_tables):
    """Test handler fails without event detail"""
    event = {"detail": {}}

    response = handler(event, None)

    assert response["statusCode"] == 400
    assert "Missing event detail" in response["body"]


@pytest.mark.unit
def test_save_conversation_history(dynamodb_tables):
    """Test conversation history saving"""
    original_message = {
        "user": {"unified_user_id": "user-123"},
        "content": {"text": "User message"},
        "conversation_id": "conv-123",
        "channel": {"type": "web"},
        "context": {"conversation_id": "conv-123"},
    }

    new_title = save_conversation_history(original_message, "AI response")

    # Verify messages saved
    history_table = dynamodb_tables["history"]
    result = history_table.query(
        KeyConditionExpression="unified_user_id = :uid",
        ExpressionAttributeValues={":uid": "user-123"},
    )

    items = result["Items"]
    assert len(items) == 2  # User message + AI message

    # Check user message
    user_msg = [i for i in items if i["role"] == "user"][0]
    assert user_msg["content"]["text"] == "User message"
    assert user_msg["conversation_id"] == "conv-123"

    # Check assistant message
    assistant_msg = [i for i in items if i["role"] == "assistant"][0]
    assert assistant_msg["content"]["text"] == "AI response"
    assert assistant_msg["conversation_id"] == "conv-123"


@pytest.mark.unit
def test_update_conversation_metadata_creates_new(dynamodb_tables):
    """Test conversation metadata creation"""
    now = datetime.now(UTC).isoformat()

    title = update_conversation_metadata("user-123", "conv-new", "Test message", now)

    # Should return a title
    assert title == "Test message"

    # Verify conversation created
    conv_table = dynamodb_tables["conversations"]
    result = conv_table.get_item(Key={"unified_user_id": "user-123", "conversation_id": "conv-new"})

    assert "Item" in result
    assert result["Item"]["title"] == "Test message"
    assert result["Item"]["message_count"] == 1


@pytest.mark.unit
def test_update_conversation_metadata_updates_existing(dynamodb_tables):
    """Test conversation metadata update"""
    # Create existing conversation
    conv_table = dynamodb_tables["conversations"]
    now = datetime.now(UTC).isoformat()

    conv_table.put_item(
        Item={
            "unified_user_id": "user-123",
            "conversation_id": "conv-existing",
            "title": "Old Title",
            "created_at": now,
            "last_message_time": now,
            "message_count": 5,
        }
    )

    # Update conversation
    title = update_conversation_metadata("user-123", "conv-existing", "New message", now)

    # Title should not change for existing conversations with good titles
    assert title == "Old Title"

    # Verify metadata updated
    result = conv_table.get_item(
        Key={"unified_user_id": "user-123", "conversation_id": "conv-existing"}
    )

    assert result["Item"]["message_count"] == 6  # Incremented


@pytest.mark.unit
def test_update_conversation_metadata_auto_titles(dynamodb_tables):
    """Test auto-titling for generic conversation titles"""
    conv_table = dynamodb_tables["conversations"]
    now = datetime.now(UTC).isoformat()

    # Create conversation with generic title
    conv_table.put_item(
        Item={
            "unified_user_id": "user-123",
            "conversation_id": "conv-generic",
            "title": "New Chat",  # Generic title
            "created_at": now,
            "last_message_time": now,
            "message_count": 1,
        }
    )

    # Update with better content
    title = update_conversation_metadata(
        "user-123", "conv-generic", "This is a much better title content", now
    )

    # Should update to new title (truncated to 30 chars)
    assert title == "This is a much better title co"
    assert len(title) == 30


@pytest.mark.unit
@patch("router.apigw_management")
def test_send_to_websocket_success(mock_apigw, dynamodb_tables, test_connection):
    """Test successful WebSocket message send"""
    mock_client = MagicMock()
    mock_apigw.__enter__ = MagicMock(return_value=mock_client)
    mock_apigw.__exit__ = MagicMock(return_value=False)

    # Mock the client to be initialized
    import router

    router.apigw_management = mock_client

    send_to_websocket("conn-456", "Test message", "conv-123", "Test Title")

    # Verify post_to_connection was called
    assert mock_client.post_to_connection.called
    call_args = mock_client.post_to_connection.call_args[1]

    assert call_args["ConnectionId"] == "conn-456"

    # Parse the data
    data = json.loads(call_args["Data"].decode("utf-8"))
    assert data["content"] == "Test message"
    assert data["conversation_id"] == "conv-123"
    assert data["title"] == "Test Title"


@pytest.mark.unit
@patch("router.apigw_management")
def test_send_to_websocket_connection_gone(mock_apigw, dynamodb_tables, test_connection):
    """Test WebSocket send with gone connection"""
    from botocore.exceptions import ClientError

    mock_client = MagicMock()
    mock_client.exceptions = MagicMock()
    mock_client.exceptions.GoneException = ClientError

    # Simulate GoneException
    mock_client.post_to_connection.side_effect = ClientError(
        {"Error": {"Code": "GoneException"}}, "PostToConnection"
    )

    import router

    router.apigw_management = mock_client

    # Should handle exception gracefully
    try:
        send_to_websocket("conn-456", "Test", "conv-123")
    except:
        pytest.fail("Should handle GoneException gracefully")