"""
Response Router Lambda
Routes AI responses to appropriate channels and saves conversation history
"""

import json
import os
import time
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
apigw_management = None  # Initialized per request with endpoint

# Environment variables
CONNECTIONS_TABLE = os.environ["CONNECTIONS_TABLE"]
HISTORY_TABLE = os.environ["HISTORY_TABLE"]
WEBSOCKET_API_ENDPOINT = os.environ["WEBSOCKET_API_ENDPOINT"]

# DynamoDB tables
connections_table = dynamodb.Table(CONNECTIONS_TABLE)
history_table = dynamodb.Table(HISTORY_TABLE)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Handle message.completed events from EventBridge

    Args:
        event: EventBridge event
        context: Lambda context

    Returns:
        Success/failure status
    """
    print("Response router invoked")

    try:
        # Extract detail from EventBridge event
        detail = event.get("detail", {})

        if not detail:
            print("No detail in event")
            return {"statusCode": 400, "body": "Missing event detail"}

        # Support both formats: new (original+response) and existing (direct fields)
        original_message = detail.get("original", detail)  # Fallback to detail itself
        response_content = detail.get("response", "")

        if not response_content:
            print("Missing response content")
            return {"statusCode": 400, "body": "Missing response"}

        # Extract user and channel info
        user_info = detail.get("user", {}) or original_message.get("user", {})
        unified_user_id = user_info.get("unified_user_id")

        # Channel can be string or dict
        channel_info = detail.get("channel", {})
        orig_channel = original_message.get("channel", {})

        if isinstance(channel_info, str):
            channel_type = channel_info
            # When channel is string, get channel_id from original message
            if isinstance(orig_channel, dict):
                channel_id = orig_channel.get("channel_id", "")
            else:
                channel_id = ""
        else:
            channel_type = channel_info.get(
                "type", orig_channel.get("type") if isinstance(orig_channel, dict) else "unknown"
            )
            channel_id = channel_info.get(
                "channel_id",
                orig_channel.get("channel_id", "") if isinstance(orig_channel, dict) else "",
            )

        print(f"Routing response for user {unified_user_id} to {channel_type}")
        print(f"Debug: channel_id = {channel_id}")

        # Save conversation to history (both user message and assistant response)
        save_conversation_history(original_message, response_content)

        # Route to appropriate channel
        if channel_type == "web":
            print(f"Debug: Attempting to send to WebSocket connection: {channel_id}")
            send_to_websocket(channel_id, response_content)
        elif channel_type == "telegram":
            # Telegram routing handled by existing telegram-lambda response router
            pass

        return {"statusCode": 200, "body": "Response routed successfully"}

    except Exception as e:
        print(f"Error routing response: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"statusCode": 500, "body": "Internal server error"}


def save_conversation_history(original_message: dict[str, Any], response_content: str) -> None:
    """
    Save both user message and assistant response to conversation history

    Args:
        original_message: Original user message
        response_content: Assistant response
    """
    try:
        unified_user_id = original_message.get("user", {}).get("unified_user_id")
        user_text = original_message.get("content", {}).get("text", "")

        # Channel can be string or dict
        channel_info = original_message.get("channel", {})
        if isinstance(channel_info, str):
            channel_type = channel_info
        else:
            channel_type = channel_info.get("type", "unknown")

        if not unified_user_id:
            print("No unified_user_id, skipping history save")
            return

        # Calculate TTL (90 days from now)
        ttl = int(time.time()) + (90 * 24 * 60 * 60)

        # Save user message
        import uuid

        user_msg_id = str(uuid.uuid4())
        timestamp_user = datetime.now(UTC).isoformat()

        history_table.put_item(
            Item={
                "unified_user_id": unified_user_id,
                "timestamp_msgid": f"{timestamp_user}#{user_msg_id}",
                "role": "user",
                "content": {"text": user_text, "attachments": []},
                "channel": channel_type,
                "metadata": {},
                "ttl": ttl,
            }
        )

        # Save assistant response
        assistant_msg_id = str(uuid.uuid4())
        timestamp_assistant = datetime.now(UTC).isoformat()

        history_table.put_item(
            Item={
                "unified_user_id": unified_user_id,
                "timestamp_msgid": f"{timestamp_assistant}#{assistant_msg_id}",
                "role": "assistant",
                "content": {"text": response_content, "attachments": []},
                "channel": channel_type,
                "metadata": {},
                "ttl": ttl,
            }
        )

        print(f"Saved conversation history for user: {unified_user_id}")

    except ClientError as e:
        print(f"Error saving history: {str(e)}")
        # Don't fail the routing if history save fails


def send_to_websocket(connection_id: str, message: str) -> None:
    """
    Send message to WebSocket connection

    Args:
        connection_id: API Gateway connection ID
        message: Message to send
    """
    try:
        # Initialize API Gateway Management API client
        # Remove 'wss://' and '/prod' from endpoint
        endpoint = WEBSOCKET_API_ENDPOINT.replace("wss://", "https://")

        global apigw_management
        if apigw_management is None:
            apigw_management = boto3.client("apigatewaymanagementapi", endpoint_url=endpoint)

        # Send message
        apigw_management.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(
                {"type": "message", "content": message, "timestamp": datetime.now(UTC).isoformat()}
            ).encode("utf-8"),
        )

        print(f"Message sent to WebSocket connection: {connection_id}")

    except apigw_management.exceptions.GoneException:
        print(f"Connection gone: {connection_id}, cleaning up")
        # Clean up stale connection
        try:
            connections_table.delete_item(Key={"connection_id": connection_id})
        except Exception as e:
            print(f"Error cleaning up connection: {str(e)}")

    except Exception as e:
        print(f"Error sending to WebSocket: {str(e)}")
        import traceback

        traceback.print_exc()
        raise
