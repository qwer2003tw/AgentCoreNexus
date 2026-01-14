"""Response Router Lambda - Routes AI responses to channels"""

import builtins
import contextlib
import json
import os
import time
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
apigw_management = None

CONNECTIONS_TABLE = os.environ["CONNECTIONS_TABLE"]
HISTORY_TABLE = os.environ["HISTORY_TABLE"]
CONVERSATIONS_TABLE = os.environ["CONVERSATIONS_TABLE"]
WEBSOCKET_API_ENDPOINT = os.environ["WEBSOCKET_API_ENDPOINT"]

connections_table = dynamodb.Table(CONNECTIONS_TABLE)
history_table = dynamodb.Table(HISTORY_TABLE)
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    print("Response router invoked")
    try:
        detail = event.get("detail", {})
        if not detail:
            return {"statusCode": 400, "body": "Missing event detail"}
        original_message = detail.get("original", detail)
        response_content = detail.get("response", "")
        response_attachments = detail.get("attachments") or []
        if not response_content:
            return {"statusCode": 400, "body": "Missing response"}
        user_info = detail.get("user", {}) or original_message.get("user", {})
        user_info.get("unified_user_id")
        channel_info = detail.get("channel", {})
        orig_channel = original_message.get("channel", {})
        if isinstance(channel_info, str):
            channel_type = channel_info
            channel_id = (
                orig_channel.get("channel_id", "") if isinstance(orig_channel, dict) else ""
            )
        else:
            channel_type = channel_info.get(
                "type", orig_channel.get("type") if isinstance(orig_channel, dict) else "unknown"
            )
            channel_id = channel_info.get(
                "channel_id",
                orig_channel.get("channel_id", "") if isinstance(orig_channel, dict) else "",
            )
        print(f"Routing to {channel_type}")
        conversation_id = (
            detail.get("conversation_id")
            or original_message.get("conversation_id")
            or original_message.get("context", {}).get("conversation_id", "default")
        )
        new_title = save_conversation_history(
            original_message, response_content, response_attachments
        )
        if channel_type == "web":
            send_to_websocket(
                channel_id,
                response_content,
                conversation_id,
                new_title,
                response_attachments,
            )
        return {"statusCode": 200, "body": "Success"}
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"statusCode": 500, "body": "Error"}


def save_conversation_history(
    original_message: dict[str, Any],
    response_content: str,
    response_attachments: list[dict[str, Any]] | None = None,
) -> str | None:
    try:
        unified_user_id = original_message.get("user", {}).get("unified_user_id")
        user_text = original_message.get("content", {}).get("text", "")
        user_attachments = original_message.get("content", {}).get("attachments", [])
        conversation_id = original_message.get("conversation_id") or original_message.get(
            "context", {}
        ).get("conversation_id", "default")
        channel_info = original_message.get("channel", {})
        channel_type = (
            channel_info if isinstance(channel_info, str) else channel_info.get("type", "unknown")
        )
        if not unified_user_id:
            return None
        ttl = int(time.time()) + (90 * 24 * 60 * 60)
        import uuid

        user_msg_id = str(uuid.uuid4())
        timestamp_user = datetime.now(UTC).isoformat()
        history_table.put_item(
            Item={
                "unified_user_id": unified_user_id,
                "timestamp_msgid": f"{timestamp_user}#{user_msg_id}",
                "conversation_id": conversation_id,
                "role": "user",
                "content": {"text": user_text, "attachments": user_attachments},
                "channel": channel_type,
                "metadata": {},
                "ttl": ttl,
            }
        )
        assistant_msg_id = str(uuid.uuid4())
        timestamp_assistant = datetime.now(UTC).isoformat()
        history_table.put_item(
            Item={
                "unified_user_id": unified_user_id,
                "timestamp_msgid": f"{timestamp_assistant}#{assistant_msg_id}",
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": {
                    "text": response_content,
                    "attachments": response_attachments or [],
                },
                "channel": channel_type,
                "metadata": {},
                "ttl": ttl,
            }
        )
        print("Saved history")
        return update_conversation_metadata(
            unified_user_id, conversation_id, response_content, timestamp_assistant
        )
    except ClientError as e:
        print(f"Error saving: {str(e)}")
        return None


def send_to_websocket(
    connection_id: str,
    message: str,
    conversation_id: str,
    title: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> None:
    try:
        endpoint = WEBSOCKET_API_ENDPOINT.replace("wss://", "https://")
        global apigw_management
        if apigw_management is None:
            apigw_management = boto3.client("apigatewaymanagementapi", endpoint_url=endpoint)

        data = {
            "type": "message",
            "content": message,
            "conversation_id": conversation_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "attachments": attachments or [],
        }
        if title:
            data["title"] = title

        apigw_management.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(data).encode("utf-8"),
        )
        print(
            f"Sent to WebSocket: {connection_id}, conversation: {conversation_id}, title: {title}"
        )
    except apigw_management.exceptions.GoneException:
        print(f"Connection gone: {connection_id}")
        with contextlib.suppress(builtins.BaseException):
            connections_table.delete_item(Key={"connection_id": connection_id})
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        raise


def update_conversation_metadata(
    unified_user_id: str, conversation_id: str, last_message_preview: str, timestamp: str
) -> str | None:
    try:
        result = conversations_table.get_item(
            Key={"unified_user_id": unified_user_id, "conversation_id": conversation_id}
        )
        if "Item" not in result:
            title = last_message_preview[:30]
            conversations_table.put_item(
                Item={
                    "unified_user_id": unified_user_id,
                    "conversation_id": conversation_id,
                    "title": title,
                    "created_at": timestamp,
                    "last_message_time": timestamp,
                    "message_count": 1,
                    "is_pinned": False,
                    "is_deleted": False,
                }
            )
            return title
        conversation = result["Item"]
        current_count = conversation.get("message_count", 0)
        current_title = conversation.get("title", "")
        should_auto_title = (
            not current_title
            or current_title == "New Chat"
            or current_title == "First Chat"
            or current_title.startswith("New")
            or len(current_title) < 5
        )
        new_title = last_message_preview[:30] if should_auto_title else current_title
        conversations_table.update_item(
            Key={"unified_user_id": unified_user_id, "conversation_id": conversation_id},
            UpdateExpression="SET last_message_time = :time, message_count = :count, title = :title",
            ExpressionAttributeValues={
                ":time": timestamp,
                ":count": current_count + 1,
                ":title": new_title,
            },
        )
        print(f"Updated: {conversation_id}, title: {new_title}")
        return new_title
    except Exception as e:
        print(f"Error: {str(e)}")
        return None
