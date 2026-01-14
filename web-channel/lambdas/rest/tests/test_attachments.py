"""Tests for Attachments REST Lambda"""

import json
import os

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("ATTACHMENTS_BUCKET", "test-attachments")
os.environ.setdefault("BINDINGS_TABLE", "test-bindings")

from attachments import handler


@pytest.fixture
def aws_env():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["ATTACHMENTS_BUCKET"] = "test-attachments"
    os.environ["BINDINGS_TABLE"] = "test-bindings"


def _create_bindings_table():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.create_table(
        TableName="test-bindings",
        KeySchema=[
            {"AttributeName": "unified_user_id", "KeyType": "HASH"},
            {"AttributeName": "binding_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "unified_user_id", "AttributeType": "S"},
            {"AttributeName": "binding_id", "AttributeType": "S"},
            {"AttributeName": "web_email", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "web_email-index",
                "KeySchema": [{"AttributeName": "web_email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    table.put_item(
        Item={
            "unified_user_id": "user-123",
            "binding_id": "binding-1",
            "web_email": "test@example.com",
        }
    )
    return table


def _create_bucket():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-attachments")


@pytest.mark.unit
def test_presign_upload_success(aws_env):
    with mock_aws():
        _create_bindings_table()
        _create_bucket()

        event = {
            "httpMethod": "POST",
            "path": "/attachments/presign",
            "requestContext": {"authorizer": {"email": "test@example.com"}},
            "body": json.dumps(
                {"filename": "report.pdf", "content_type": "application/pdf", "size": 1024}
            ),
        }

        response = handler(event, None)

        assert response["statusCode"] == 200
        payload = json.loads(response["body"])
        assert "upload_url" in payload
        assert payload["attachment"]["name"] == "report.pdf"
        assert payload["attachment"]["key"].startswith("attachments/user-123/")


@pytest.mark.unit
def test_presign_download_forbidden(aws_env):
    with mock_aws():
        _create_bindings_table()
        _create_bucket()

        event = {
            "httpMethod": "POST",
            "path": "/attachments/download",
            "requestContext": {"authorizer": {"email": "test@example.com"}},
            "body": json.dumps({"key": "attachments/other-user/att/file.txt"}),
        }

        response = handler(event, None)

        assert response["statusCode"] == 403
        payload = json.loads(response["body"])
        assert payload["error"] == "Forbidden"
