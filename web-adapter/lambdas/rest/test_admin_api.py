"""
Tests for admin_api.py - Admin conversation management endpoints
"""

import json

# Mock audit_decorator before importing admin_api
import sys
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, '/opt/python')

# Create stub decorators
def audit_log(**kwargs):
    def decorator(func):
        return func
    return decorator

def require_permission(role):
    def decorator(func):
        return func
    return decorator

# Mock the module
sys.modules['audit_decorator'] = MagicMock(
    audit_log=audit_log,
    require_permission=require_permission
)

# Now import admin_api
import admin_api


@pytest.fixture
def dynamodb_tables():
    """Setup mock DynamoDB tables"""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

        # Create conversation_history table
        history_table = dynamodb.create_table(
            TableName='test-conversation-history',
            KeySchema=[
                {'AttributeName': 'conversation_id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'conversation_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'N'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create summaries table
        summaries_table = dynamodb.create_table(
            TableName='test-summaries',
            KeySchema=[
                {'AttributeName': 'conversation_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'conversation_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        yield {
            'history': history_table,
            'summaries': summaries_table,
            'dynamodb': dynamodb
        }


class TestGetConversationDetail:
    """Tests for get_conversation_detail function"""

    @patch.dict('os.environ', {'CONVERSATION_TABLE_NAME': 'test-conversation-history'})
    def test_telegram_format_with_attachments(self, dynamodb_tables):
        """Test Telegram message format with attachments in metadata"""
        history_table = dynamodb_tables['history']

        # Insert Telegram message with attachment
        history_table.put_item(Item={
            'conversation_id': 'tg:12345',
            'timestamp': 1000000,
            'sender_id': 'tg:12345',
            'channel': 'telegram',
            'role': 'user',
            'content': '這是什麼？',  # Telegram format: string
            'metadata': {
                'attachments': [
                    {
                        'type': 'photo',
                        'file_name': 'photo.jpg',
                        's3_url': 's3://bucket/photo.jpg'
                    }
                ]
            }
        })

        # Mock event
        event = {
            'pathParameters': {'conversation_id': 'tg:12345'},
            'requestContext': {'authorizer': {'role': 'admin'}}
        }

        # Call function
        with patch.object(admin_api, 'dynamodb') as mock_dynamodb:
            mock_dynamodb.Table.return_value = history_table

            response = admin_api.get_conversation_detail(event, None)

        # Verify
        assert response['statusCode'] == 200
        body = json.loads(response['body'])

        # Check attachments counted
        assert body['statistics']['attachments']['images'] == 1
        assert body['statistics']['attachments']['files'] == 0
        assert body['statistics']['attachments']['total'] == 1

        # Check message has attachments
        assert len(body['messages']) == 1
        assert len(body['messages'][0]['attachments']) == 1

    @patch.dict('os.environ', {'CONVERSATION_TABLE_NAME': 'test-conversation-history'})
    def test_web_format_with_attachments(self, dynamodb_tables):
        """Test Web message format with attachments in content"""
        history_table = dynamodb_tables['history']

        # Insert Web message with attachment
        history_table.put_item(Item={
            'conversation_id': 'web:12345',
            'timestamp': 1000000,
            'unified_user_id': 'uuid-12345',
            'channel': 'web',
            'role': 'user',
            'content': {  # Web format: object
                'text': '這是什麼？',
                'attachments': [
                    {
                        'type': 'document',
                        'file_name': 'doc.pdf'
                    }
                ]
            }
        })

        event = {
            'pathParameters': {'conversation_id': 'web:12345'},
            'requestContext': {'authorizer': {'role': 'admin'}}
        }

        with patch.object(admin_api, 'dynamodb') as mock_dynamodb:
            mock_dynamodb.Table.return_value = history_table

            response = admin_api.get_conversation_detail(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])

        # Check attachments counted
        assert body['statistics']['attachments']['images'] == 0
        assert body['statistics']['attachments']['files'] == 1
        assert body['statistics']['attachments']['total'] == 1


class TestGenerateSummary:
    """Tests for generate_summary function"""

    @patch.dict('os.environ', {
        'CONVERSATION_TABLE_NAME': 'test-conversation-history',
        'SUMMARIES_TABLE': 'test-summaries',
        'AWS_REGION': 'us-west-2'
    })
    @patch('admin_api.bedrock_runtime')
    def test_generate_new_summary(self, mock_bedrock, dynamodb_tables):
        """Test generating new summary (no cache)"""
        history_table = dynamodb_tables['history']
        summaries_table = dynamodb_tables['summaries']

        # Insert messages
        history_table.put_item(Item={
            'conversation_id': 'tg:12345',
            'timestamp': 1000000,
            'role': 'user',
            'content': '你好',
            'metadata': {'attachments': []}
        })

        # Mock Bedrock response
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: json.dumps({
                'content': [{'text': '測試摘要內容'}]
            }).encode())
        }

        event = {
            'pathParameters': {'conversation_id': 'tg:12345'},
            'requestContext': {'authorizer': {'role': 'admin'}}
        }

        with patch.object(admin_api, 'dynamodb') as mock_dynamodb:
            # Mock Table to return correct table based on name
            def get_table(name):
                if 'history' in name or name == 'test-conversation-history':
                    return history_table
                elif 'summaries' in name or name == 'test-summaries':
                    return summaries_table
                raise KeyError(f"Unknown table: {name}")

            mock_dynamodb.Table.side_effect = get_table

            response = admin_api.generate_summary(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])

        # Verify field compatibility
        assert 'summary' in body
        assert 'summary_text' in body
        assert body['summary'] == body['summary_text']
        assert body['summary'] == '測試摘要內容'
        assert not body['cached']

    @patch.dict('os.environ', {'SUMMARIES_TABLE': 'test-summaries'})
    def test_return_cached_summary(self, dynamodb_tables):
        """Test returning cached summary (within 24 hours)"""
        summaries_table = dynamodb_tables['summaries']

        # Insert cached summary (1 hour ago)
        one_hour_ago = int(datetime.now().timestamp() * 1000) - (3600 * 1000)
        summaries_table.put_item(Item={
            'conversation_id': 'tg:12345',
            'summary_text': '緩存的摘要',
            'attachment_stats': {'images': 0, 'documents': 0, 'total': 0},
            'generated_at': one_hour_ago,
            'model_used': 'claude-haiku'
        })

        event = {
            'pathParameters': {'conversation_id': 'tg:12345'},
            'requestContext': {'authorizer': {'role': 'admin'}}
        }

        with patch.object(admin_api, 'dynamodb') as mock_dynamodb:
            mock_dynamodb.Table.return_value = summaries_table

            response = admin_api.generate_summary(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])

        # Verify cached
        assert body['cached']
        assert body['summary'] == '緩存的摘要'
        assert body['summary_text'] == '緩存的摘要'


class TestFieldCompatibility:
    """Test backward compatibility of field names"""

    def test_decimal_to_float(self):
        """Test Decimal conversion"""
        obj = {
            'count': Decimal('10'),
            'nested': {
                'value': Decimal('3.14')
            },
            'list': [Decimal('1'), Decimal('2.5')]
        }

        result = admin_api.decimal_to_float(obj)

        assert result['count'] == 10
        assert result['nested']['value'] == 3.14
        assert result['list'] == [1, 2.5]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
