"""Integration tests for Lambda and DynamoDB interactions"""

import pytest


@pytest.mark.integration
def test_websocket_connect_saves_to_dynamodb(
    aws_environment, test_user_with_binding, valid_jwt_token
):
    """Test WebSocket connection saves data to DynamoDB correctly"""
    from connect import handler

    # Create connection event
    event = {
        "requestContext": {"connectionId": "test-conn-integration-123"},
        "queryStringParameters": {"token": valid_jwt_token},
    }

    # Execute handler
    response = handler(event, None)

    # Verify success
    assert response["statusCode"] == 200

    # Verify connection saved in DynamoDB
    connections_table = aws_environment["connections"]
    result = connections_table.get_item(Key={"connection_id": "test-conn-integration-123"})

    assert "Item" in result
    conn = result["Item"]
    assert conn["email"] == "test@example.com"
    assert conn["unified_user_id"] == test_user_with_binding["unified_user_id"]
    assert "connected_at" in conn
    assert "ttl" in conn


@pytest.mark.integration
def test_router_saves_conversation_history_to_dynamodb(aws_environment, test_user_with_binding):
    """Test Router saves complete conversation history to DynamoDB"""
    from router import save_conversation_history

    unified_user_id = test_user_with_binding["unified_user_id"]

    # Create original message
    original_message = {
        "user": {"unified_user_id": unified_user_id},
        "content": {"text": "Hello, how are you?"},
        "conversation_id": "conv-integration-123",
        "channel": {"type": "web"},
        "context": {"conversation_id": "conv-integration-123"},
    }

    # Save history
    new_title = save_conversation_history(original_message, "I'm doing great, thanks!")

    # Verify history saved
    history_table = aws_environment["history"]
    result = history_table.query(
        KeyConditionExpression="unified_user_id = :uid",
        ExpressionAttributeValues={":uid": unified_user_id},
    )

    items = result["Items"]
    assert len(items) == 2  # User message + Assistant message

    # Verify user message
    user_msg = [i for i in items if i["role"] == "user"][0]
    assert user_msg["content"]["text"] == "Hello, how are you?"
    assert user_msg["conversation_id"] == "conv-integration-123"

    # Verify assistant message
    assistant_msg = [i for i in items if i["role"] == "assistant"][0]
    assert assistant_msg["content"]["text"] == "I'm doing great, thanks!"
    assert assistant_msg["conversation_id"] == "conv-integration-123"

    # Verify conversation metadata updated
    conversations_table = aws_environment["conversations"]
    conv_result = conversations_table.get_item(
        Key={"unified_user_id": unified_user_id, "conversation_id": "conv-integration-123"}
    )

    assert "Item" in conv_result
    # Title is auto-generated from AI response (first 30 chars)
    assert conv_result["Item"]["title"] == "I'm doing great, thanks!"
    assert conv_result["Item"]["message_count"] == 1


@pytest.mark.integration
def test_conversations_crud_operations_with_dynamodb(aws_environment, test_user_with_binding):
    """Test complete conversation CRUD operations"""
    from default import auto_assign_conversation_id, create_new_conversation

    unified_user_id = test_user_with_binding["unified_user_id"]

    # Create conversation
    conv_id = create_new_conversation(unified_user_id)
    assert conv_id

    # Verify created in DynamoDB
    conversations_table = aws_environment["conversations"]
    result = conversations_table.get_item(
        Key={"unified_user_id": unified_user_id, "conversation_id": conv_id}
    )

    assert "Item" in result
    conv = result["Item"]
    assert conv["title"] == "New Chat"
    assert conv["message_count"] == 0
    assert conv["is_deleted"] is False

    # Test auto-assign returns the conversation
    assigned_id = auto_assign_conversation_id(unified_user_id)
    assert assigned_id == conv_id  # Should return the recent conversation
