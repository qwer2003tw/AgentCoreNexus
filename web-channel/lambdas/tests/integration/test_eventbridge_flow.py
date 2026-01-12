"""Integration tests for EventBridge event flows"""
import json
from datetime import UTC, datetime
from unittest.mock import patch, MagicMock

import pytest


@pytest.mark.integration
def test_message_received_event_structure(aws_environment, test_user_with_binding):
    """Test message.received event is correctly formatted"""
    from default import handler as websocket_handler
    
    # Create connection first
    connections_table = aws_environment["connections"]
    connections_table.put_item(Item={
        "connection_id": "test-conn-123",
        "unified_user_id": test_user_with_binding["unified_user_id"],
        "email": "test@example.com",
        "connected_at": datetime.now(UTC).isoformat(),
    })
    
    # Mock EventBridge to capture the event
    with patch("default.eventbridge") as mock_eb:
        mock_eb.put_events.return_value = {"FailedEntryCount": 0}
        
        # Send message
        event = {
            "requestContext": {"connectionId": "test-conn-123"},
            "body": json.dumps({"message": "Test message", "conversation_id": "conv-123"}),
        }
        
        response = websocket_handler(event, None)
        
        assert response["statusCode"] == 200
        
        # Verify EventBridge was called
        assert mock_eb.put_events.called
        call_args = mock_eb.put_events.call_args[1]
        entries = call_args["Entries"]
        
        # Verify event structure
        assert len(entries) == 1
        event_entry = entries[0]
        assert event_entry["Source"] == "universal-adapter"
        assert event_entry["DetailType"] == "message.received"
        
        # Parse and verify detail
        detail = json.loads(event_entry["Detail"])
        assert detail["user"]["unified_user_id"] == test_user_with_binding["unified_user_id"]
        assert detail["content"]["text"] == "Test message"
        assert detail["conversation_id"] == "conv-123"


@pytest.mark.integration
@patch("router.apigw_management")
def test_message_completed_triggers_router(mock_apigw, aws_environment, test_user_with_binding):
    """Test message.completed event triggers Router correctly"""
    from router import handler as router_handler
    
    # Setup connection
    connections_table = aws_environment["connections"]
    connections_table.put_item(Item={
        "connection_id": "conn-456",
        "unified_user_id": test_user_with_binding["unified_user_id"],
        "email": "test@example.com",
    })
    
    # Mock WebSocket client
    mock_client = MagicMock()
    mock_apigw.__enter__ = MagicMock(return_value=mock_client)
    mock_apigw.__exit__ = MagicMock(return_value=False)
    
    import router
    router.apigw_management = mock_client
    
    # Create completion event
    event = {
        "detail": {
            "response": "AI response text",
            "conversation_id": "conv-789",
            "original": {
                "user": {"unified_user_id": test_user_with_binding["unified_user_id"]},
                "content": {"text": "User question"},
                "channel": {"type": "web", "channel_id": "conn-456"},
                "conversation_id": "conv-789",
            },
        }
    }
    
    # Execute router
    response = router_handler(event, None)
    
    # Verify success
    assert response["statusCode"] == 200
    
    # Verify history saved
    history_table = aws_environment["history"]
    result = history_table.query(
        KeyConditionExpression="unified_user_id = :uid",
        ExpressionAttributeValues={":uid": test_user_with_binding["unified_user_id"]},
    )
    
    assert len(result["Items"]) == 2  # User + Assistant messages
    
    # Verify WebSocket message sent
    assert mock_client.post_to_connection.called


@pytest.mark.integration
def test_event_routing_by_channel_type(aws_environment, test_user_with_binding):
    """Test events are routed correctly based on channel type"""
    from router import handler as router_handler
    
    unified_user_id = test_user_with_binding["unified_user_id"]
    
    # Test web channel routing
    web_event = {
        "detail": {
            "response": "Web response",
            "original": {
                "user": {"unified_user_id": unified_user_id},
                "content": {"text": "Test"},
                "channel": {"type": "web", "channel_id": "conn-web"},
                "conversation_id": "conv-web",
            },
        }
    }
    
    with patch("router.send_to_websocket") as mock_ws:
        response = router_handler(web_event, None)
        
        # Verify routed to WebSocket
        assert response["statusCode"] == 200
        assert mock_ws.called
        
        # Verify history saved regardless of channel
        history_table = aws_environment["history"]
        result = history_table.query(
            KeyConditionExpression="unified_user_id = :uid",
            ExpressionAttributeValues={":uid": unified_user_id},
        )
        
        assert len(result["Items"]) >= 2  # User + Assistant messages