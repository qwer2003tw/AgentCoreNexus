"""
Attachments REST API Lambda
Handles file upload/download presign for web chat attachments.
"""

import json
import os
import uuid
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

# Initialize AWS clients with region-specific endpoint
s3_client = boto3.client(
    "s3",
    region_name="us-west-2",
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)
dynamodb = boto3.resource("dynamodb")

# Environment variables
ATTACHMENTS_BUCKET = os.environ["ATTACHMENTS_BUCKET"]
BINDINGS_TABLE = os.environ["BINDINGS_TABLE"]

# DynamoDB tables
bindings_table = dynamodb.Table(BINDINGS_TABLE)

MAX_ATTACHMENT_SIZE_BYTES = 25 * 1024 * 1024


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main handler for attachments operations

    Routes:
        POST /attachments/presign - Generate presigned upload URL
        POST /attachments/download - Generate presigned download URL
    """
    path = event.get("path", "")
    method = event.get("httpMethod", "")

    print(f"{method} {path}")

    if method == "OPTIONS":
        return response(200, {"message": "OK"})

    email = extract_email_from_token(event)
    if not email:
        return response(401, {"error": "Unauthorized"})

    try:
        if path == "/attachments/presign" and method == "POST":
            return handle_presign_upload(email, event)
        if path == "/attachments/download" and method == "POST":
            return handle_presign_download(email, event)
        return response(404, {"error": "Not found"})
    except Exception as exc:
        print(f"Error: {str(exc)}")
        import traceback

        traceback.print_exc()
        return response(500, {"error": "Internal server error"})


# ============================================================
# Handler Functions
# ============================================================


def handle_presign_upload(email: str, event: dict[str, Any]) -> dict[str, Any]:
    unified_user_id = get_unified_user_id_by_email(email)
    if not unified_user_id:
        return response(403, {"error": "User not found"})

    body = json.loads(event.get("body", "{}"))
    filename = (body.get("filename") or "").strip()
    content_type = (body.get("content_type") or "application/octet-stream").strip()
    size = int(body.get("size") or 0)

    if not filename:
        return response(400, {"error": "Missing filename"})
    if size <= 0:
        return response(400, {"error": "Invalid file size"})
    if size > MAX_ATTACHMENT_SIZE_BYTES:
        return response(400, {"error": "File exceeds max size"})

    safe_filename = os.path.basename(filename)
    attachment_id = str(uuid.uuid4())
    key = f"attachments/{unified_user_id}/{attachment_id}/{safe_filename}"

    try:
        upload_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": ATTACHMENTS_BUCKET,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=900,
        )

        return response(
            200,
            {
                "upload_url": upload_url,
                "attachment": {
                    "id": attachment_id,
                    "name": safe_filename,
                    "size": size,
                    "content_type": content_type,
                    "key": key,
                },
            },
        )
    except ClientError as exc:
        print(f"Error generating presigned URL: {str(exc)}")
        return response(500, {"error": "Failed to generate upload URL"})


def handle_presign_download(email: str, event: dict[str, Any]) -> dict[str, Any]:
    unified_user_id = get_unified_user_id_by_email(email)
    if not unified_user_id:
        return response(403, {"error": "User not found"})

    body = json.loads(event.get("body", "{}"))
    key = (body.get("key") or "").strip()
    if not key:
        return response(400, {"error": "Missing key"})

    user_prefix = f"attachments/{unified_user_id}/"
    if not key.startswith(user_prefix):
        return response(403, {"error": "Forbidden"})

    try:
        download_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": ATTACHMENTS_BUCKET,
                "Key": key,
                "ResponseContentDisposition": "attachment",
            },
            ExpiresIn=600,
        )
        return response(200, {"download_url": download_url})
    except ClientError as exc:
        print(f"Error generating download URL: {str(exc)}")
        return response(500, {"error": "Failed to generate download URL"})


# ============================================================
# Helper Functions
# ============================================================


def get_unified_user_id_by_email(email: str) -> str | None:
    try:
        result = bindings_table.query(
            IndexName="web_email-index",
            KeyConditionExpression="web_email = :email",
            ExpressionAttributeValues={":email": email},
        )

        items = result.get("Items", [])
        if items:
            return items[0]["unified_user_id"]

        return None
    except Exception as exc:
        print(f"Error getting unified_user_id: {str(exc)}")
        return None


def extract_email_from_token(event: dict[str, Any]) -> str | None:
    authorizer = event.get("requestContext", {}).get("authorizer", {})
    return authorizer.get("email")


def response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
