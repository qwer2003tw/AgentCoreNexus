"""
SQS Client Module - 發送訊息到 SQS Queue
"""

import json
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from utils.logger import get_logger

logger = get_logger(__name__)

# 初始化 SQS 客戶端
sqs = boto3.client("sqs")
queue_url = os.environ.get("SQS_QUEUE_URL", "")


def send_to_queue(message: dict[str, Any], retry_count: int = 3) -> bool:
    """
    發送訊息到 SQS Queue

    Args:
        message: Telegram webhook payload
        retry_count: 重試次數

    Returns:
        bool: True 如果成功發送
    """
    if not queue_url:
        logger.error("SQS_QUEUE_URL environment variable not set")
        return False

    # 準備訊息體
    message_body = json.dumps(message, ensure_ascii=False)

    # 提取一些元數據用於日誌
    chat_id = message.get("message", {}).get("chat", {}).get("id", "unknown")
    message_id = message.get("message", {}).get("message_id", "unknown")

    for attempt in range(1, retry_count + 1):
        try:
            response = sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=message_body,
                MessageAttributes={
                    "chat_id": {"StringValue": str(chat_id), "DataType": "String"},
                    "message_id": {"StringValue": str(message_id), "DataType": "String"},
                },
            )

            logger.info(
                "Message sent to SQS successfully",
                extra={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "sqs_message_id": response.get("MessageId"),
                    "attempt": attempt,
                    "event_type": "sqs_send_success",
                },
            )
            return True

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            logger.warning(
                f"SQS send failed (attempt {attempt}/{retry_count}): {error_code}",
                extra={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "error_code": error_code,
                    "attempt": attempt,
                    "event_type": "sqs_send_retry",
                },
            )

            # 如果是最後一次嘗試，記錄錯誤
            if attempt == retry_count:
                logger.error(
                    f"Failed to send message to SQS after {retry_count} attempts",
                    extra={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "error": str(e),
                        "event_type": "sqs_send_failed",
                    },
                    exc_info=True,
                )
                return False

        except Exception as e:
            logger.error(
                f"Unexpected error sending to SQS (attempt {attempt}/{retry_count}): {str(e)}",
                extra={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "attempt": attempt,
                    "event_type": "sqs_send_error",
                },
                exc_info=True,
            )

            if attempt == retry_count:
                return False

    return False


def get_queue_attributes() -> dict[str, Any]:
    """
    取得 SQS Queue 屬性 (用於監控)

    Returns:
        dict: Queue 屬性
    """
    try:
        response = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
        )
        return response.get("Attributes", {})

    except ClientError as e:
        logger.error(f"Failed to get queue attributes: {str(e)}")
        return {}
