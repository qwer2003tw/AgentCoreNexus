"""
Tests for router.py - Response router for Web and Telegram channels
"""

import os
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

# Set environment variables before importing router
os.environ['CONNECTIONS_TABLE'] = 'test-connections'
os.environ['HISTORY_TABLE'] = 'test-history'
os.environ['CONVERSATIONS_TABLE'] = 'test-conversations'
os.environ['WEBSOCKET_API_ENDPOINT'] = 'wss://test.execute-api.us-west-2.amazonaws.com/prod'

import router


@pytest.fixture
def dynamodb_tables():
    """Setup mock DynamoDB tables"""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

        # Create conversations table
        conversations_table = dynamodb.create_table(
            TableName='test-conversations',
            KeySchema=[
                {'AttributeName': 'unified_user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'conversation_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'unified_user_id', 'AttributeType': 'S'},
                {'AttributeName': 'conversation_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create history table
        history_table = dynamodb.create_table(
            TableName='test-history',
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

        yield {
            'conversations': conversations_table,
            'history': history_table,
            'dynamodb': dynamodb
        }


class TestUpdateConversationMetadata:
    """Tests for update_conversation_metadata function"""

    @patch.dict('os.environ', {'CONVERSATIONS_TABLE': 'test-conversations'})
    def test_increment_message_count_by_2(self, dynamodb_tables):
        """Test that message_count increments by 2 (user + assistant)"""
        conversations_table = dynamodb_tables['conversations']

        # Insert existing conversation
        conversations_table.put_item(Item={
            'unified_user_id': 'user-123',
            'conversation_id': 'conv-456',
            'title': 'Test Chat',
            'created_at': '1000000',
            'last_message_time': '1000000',
            'message_count': 4,  # Existing: 4 messages
            'is_pinned': False,
            'is_deleted': False
        })

        # Call update function
        with patch.object(router, 'conversations_table', conversations_table):
            result = router.update_conversation_metadata(
                'user-123',
                'conv-456',
                'New message preview',
                '2000000'
            )

        # Verify
        response = conversations_table.get_item(
            Key={'unified_user_id': 'user-123', 'conversation_id': 'conv-456'}
        )

        item = response['Item']
        # Should increment by 2 (user + assistant messages)
        assert item['message_count'] == 6  # 4 + 2 = 6
        assert item['last_message_time'] == '2000000'
        assert result is not None

    @patch.dict('os.environ', {'CONVERSATIONS_TABLE': 'test-conversations'})
    def test_create_new_conversation(self, dynamodb_tables):
        """Test creating new conversation metadata"""
        conversations_table = dynamodb_tables['conversations']

        # Call update function (no existing conversation)
        with patch.object(router, 'conversations_table', conversations_table):
            title = router.update_conversation_metadata(
                'user-789',
                'conv-new',
                'First message in conversation',
                '3000000'
            )

        # Verify new conversation created
        response = conversations_table.get_item(
            Key={'unified_user_id': 'user-789', 'conversation_id': 'conv-new'}
        )

        assert 'Item' in response
        item = response['Item']

        # Initial message_count should be 1 (will be incremented to 2 on next update)
        assert item['message_count'] == 1
        assert item['title'] == 'First message in conversation'
        assert title == 'First message in conversation'

    @patch.dict('os.environ', {'CONVERSATIONS_TABLE': 'test-conversations'})
    def test_auto_title_generation(self, dynamodb_tables):
        """Test automatic title generation from message"""
        conversations_table = dynamodb_tables['conversations']

        # Insert conversation with generic title
        conversations_table.put_item(Item={
            'unified_user_id': 'user-123',
            'conversation_id': 'conv-456',
            'title': 'New Chat',  # Generic title
            'created_at': '1000000',
            'last_message_time': '1000000',
            'message_count': 2,
            'is_pinned': False,
            'is_deleted': False
        })

        # Update with meaningful message
        with patch.object(router, 'conversations_table', conversations_table):
            title = router.update_conversation_metadata(
                'user-123',
                'conv-456',
                'How do I deploy my Lambda function to AWS?',
                '2000000'
            )

        # Verify title updated
        assert title == 'How do I deploy my Lambda func'

        response = conversations_table.get_item(
            Key={'unified_user_id': 'user-123', 'conversation_id': 'conv-456'}
        )
        assert response['Item']['title'] == title


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=router', '--cov-report=term'])
