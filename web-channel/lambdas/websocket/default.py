"""
WebSocket $default handler
Handles incoming WebSocket messages and sends to EventBridge
"""

import contextlib
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
eventbridge = boto3.client("events")

# Environment variables
CONNECTIONS_TABLE = os.environ["CONNECTIONS_TABLE"]
BINDINGS_TABLE = os.environ["BINDINGS_TABLE"]
CONVERSATIONS_TABLE = os.environ["CONVERSATIONS_TABLE"]
EVENT_BUS_NAME = os.environ["EVENT_BUS_NAME"]

# DynamoDB tables
connections_table = dynamodb.Table(CONNECTIONS_TABLE)
bindings_table = dynamodb.Table(BINDINGS_TABLE)
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle WebSocket $default route"""
    connection_id = event["requestContext"]["connectionId"]
    print(f"Received WebSocket message from: {connection_id}")

    try:
        body = json.loads(event.get("body", "{}"))
        message_text = body.get("message", "")
        attachments = body.get("attachments") or []
        conversation_id = body.get("conversation_id")

        # Convert Web attachments to unified format
        if attachments:
            attachments = convert_web_attachments(attachments, message_text)

        if not message_text and not attachments:
            return {"statusCode": 400, "body": "Missing message"}

        connection = get_connection(connection_id)
        if not connection:
            return {"statusCode": 404, "body": "Connection not found"}

        unified_user_id = connection["unified_user_id"]
        email = connection["email"]

        if not conversation_id:
            conversation_id = auto_assign_conversation_id(unified_user_id)

        message_type = "text" if message_text else "attachments"

        unified_message = create_unified_message(
            unified_user_id,
            connection_id,
            email,
            message_text,
            "user",
            conversation_id,
            attachments,
            message_type,
        )

        send_to_eventbridge(unified_message)
        update_connection_activity(connection_id)

        return {"statusCode": 200, "body": "Message sent"}

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"statusCode": 500, "body": "Internal server error"}


def convert_web_attachments(web_attachments: list, user_message: str = "") -> list:
    """
    Convert Web attachment format to unified format
    """
    result = []
    bucket = "agentcore-web-channel-attachments-190825685292"

    for att in web_attachments:
        s3_url = f"s3://{bucket}/{att['key']}"
        content_type = att.get("content_type", "")
        att_type = "photo" if content_type.startswith("image/") else "document"

        if not user_message:
            if att_type == "photo":
                task = "Please describe this image."
            else:
                task = f"Please summarize the file {att['name']}."
        else:
            task = user_message

        result.append(
            {
                "type": att_type,
                "file_name": att["name"],
                "file_id": att["id"],
                "mime_type": content_type,
                "file_size": att["size"],
                "s3_url": s3_url,
                "task": task,
            }
        )

    print(f"Converted {len(web_attachments)} Web attachments")
    return result


def get_connection(connection_id: str) -> dict[str, Any] | None:
    try:
        response = connections_table.get_item(Key={"connection_id": connection_id})
        return response.get("Item")
    except ClientError as e:
        print(f"Error getting connection: {str(e)}")
        return None


def create_unified_message(
    unified_user_id: str,
    connection_id: str,
    email: str,
    message_text: str,
    role: str,
    conversation_id: str,
    attachments: list[dict[str, Any]] | None = None,
    message_type: str = "text",
) -> dict[str, Any]:
    return {
        "message_id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "channel": {"type": "web", "channel_id": connection_id, "metadata": {}},
        "user": {"unified_user_id": unified_user_id, "identifier": email, "role": role},
        "content": {
            "text": message_text,
            "message_type": message_type,
            "attachments": attachments or [],
        },
        "context": {"conversation_id": conversation_id, "session_id": connection_id},
    }


def send_to_eventbridge(message: dict[str, Any]) -> None:
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
        raise Exception("Failed to send event to EventBridge")


def update_connection_activity(connection_id: str) -> None:
    with contextlib.suppress(ClientError):
        connections_table.update_item(
            Key={"connection_id": connection_id},
            UpdateExpression="SET last_activity = :now",
            ExpressionAttributeValues={":now": datetime.now(UTC).isoformat()},
        )


def auto_assign_conversation_id(unified_user_id: str) -> str:
    try:
        one_hour_ago = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        result = conversations_table.query(
            IndexName="user-by-time-index",
            KeyConditionExpression="unified_user_id = :uid AND last_message_time >= :time",
            ExpressionAttributeValues={
                ":uid": unified_user_id,
                ":time": one_hour_ago,
                ":false": False,
            },
            FilterExpression="attribute_not_exists(is_deleted) OR is_deleted = :false",
            Limit=1,
            ScanIndexForward=False,
        )

        items = result.get("Items", [])
        if items:
            return items[0]["conversation_id"]

        return create_new_conversation(unified_user_id)
    except Exception:
        return create_new_conversation(unified_user_id)


def create_new_conversation(unified_user_id: str) -> str:
    conv_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    try:
        conversations_table.put_item(
            Item={
                "unified_user_id": unified_user_id,
                "conversation_id": conv_id,
                "title": "New Chat",
                "created_at": now,
                "last_message_time": now,
                "message_count": 0,
                "is_pinned": False,
                "is_deleted": False,
            }
        )
        return conv_id
    except Exception:
        return f"temp_{uuid.uuid4()}"
