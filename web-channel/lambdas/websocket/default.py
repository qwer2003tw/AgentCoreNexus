"""
WebSocket $default handler
Handles incoming WebSocket messages and sends to EventBridge
"""

import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
eventbridge = boto3.client("events")

# Environment variables
CONNECTIONS_TABLE = os.environ["CONNECTIONS_TABLE"]
BINDINGS_TABLE = os.environ["BINDINGS_TABLE"]
EVENT_BUS_NAME = os.environ["EVENT_BUS_NAME"]

# DynamoDB tables
connections_table = dynamodb.Table(CONNECTIONS_TABLE)
bindings_table = dynamodb.Table(BINDINGS_TABLE)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Handle WebSocket $default route (incoming messages)

    Args:
        event: API Gateway WebSocket event
        context: Lambda context

    Returns:
        Response with statusCode 200 or error code
    """
    connection_id = event["requestContext"]["connectionId"]

    print(f"Received WebSocket message from connection: {connection_id}")

    try:
        # Parse message body
        body = json.loads(event.get("body", "{}"))
        body.get("action", "sendMessage")
        message_text = body.get("message", "")

        if not message_text:
            return {"statusCode": 400, "body": "Missing message"}

        # Get connection info
        connection = get_connection(connection_id)
        if not connection:
            print(f"Connection not found: {connection_id}")
            return {"statusCode": 404, "body": "Connection not found"}

        unified_user_id = connection["unified_user_id"]
        email = connection["email"]

        # Get user binding info for additional context
        get_binding(unified_user_id)
        role = "user"  # Default role

        # Create unified message format
        unified_message = create_unified_message(
            unified_user_id=unified_user_id,
            connection_id=connection_id,
            email=email,
            message_text=message_text,
            role=role,
        )

        # Send to EventBridge
        send_to_eventbridge(unified_message)

        # Update last activity
        update_connection_activity(connection_id)

        print(f"Message sent to EventBridge for user: {email}")

        return {"statusCode": 200, "body": "Message sent"}

    except Exception as e:
        print(f"Error handling message: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"statusCode": 500, "body": "Internal server error"}


def get_connection(connection_id: str) -> dict[str, Any] | None:
    """
    Get connection info from DynamoDB

    Args:
        connection_id: API Gateway connection ID

    Returns:
        Connection item or None
    """
    try:
        response = connections_table.get_item(Key={"connection_id": connection_id})
        return response.get("Item")
    except ClientError as e:
        print(f"Error getting connection: {str(e)}")
        return None


def get_binding(unified_user_id: str) -> dict[str, Any] | None:
    """
    Get user binding info

    Args:
        unified_user_id: Unified user ID

    Returns:
        Binding item or None
    """
    try:
        response = bindings_table.get_item(Key={"unified_user_id": unified_user_id})
        return response.get("Item")
    except ClientError as e:
        print(f"Error getting binding: {str(e)}")
        return None


def create_unified_message(
    unified_user_id: str, connection_id: str, email: str, message_text: str, role: str
) -> dict[str, Any]:
    """
    Create unified message format for EventBridge

    Args:
        unified_user_id: Unified user ID
        connection_id: WebSocket connection ID
        email: User email
        message_text: Message text
        role: User role

    Returns:
        Unified message dict
    """
    message_id = str(uuid.uuid4())
    timestamp = datetime.now(UTC).isoformat()

    return {
        "message_id": message_id,
        "timestamp": timestamp,
        "channel": {"type": "web", "channel_id": connection_id, "metadata": {}},
        "user": {"unified_user_id": unified_user_id, "identifier": email, "role": role},
        "content": {"text": message_text, "message_type": "text", "attachments": []},
        "context": {"conversation_id": unified_user_id, "session_id": unified_user_id},
    }


def send_to_eventbridge(message: dict[str, Any]) -> None:
    """
    Send unified message to EventBridge

    Args:
        message: Unified message dict
    """
    try:
        response = eventbridge.put_events(
            Entries=[
                {
                    "Source": "universal-adapter",
                    "DetailType": "message.received",
                    "Detail": json.dumps(message),
                    "EventBusName": EVENT_BUS_NAME,
                }
            ]
        )

        if response["FailedEntryCount"] > 0:
            print(f"Failed to send event: {response}")
            raise Exception("Failed to send event to EventBridge")

        print(f"Event sent to EventBridge: {message['message_id']}")

    except Exception as e:
        print(f"Error sending to EventBridge: {str(e)}")
        raise


def update_connection_activity(connection_id: str) -> None:
    """
    Update last activity timestamp for connection

    Args:
        connection_id: API Gateway connection ID
    """
    try:
        now = datetime.now(UTC).isoformat()

        connections_table.update_item(
            Key={"connection_id": connection_id},
            UpdateExpression="SET last_activity = :now",
            ExpressionAttributeValues={":now": now},
        )

    except ClientError as e:
        print(f"Error updating connection activity: {str(e)}")
        # Non-critical error, just log it
