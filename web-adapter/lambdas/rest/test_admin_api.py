"""
Admin API 本地測試

測試對話列表和詳情 API 的邏輯
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Mock sys.path.insert before importing admin_api
import sys
if '/opt/python' not in sys.path:
    sys.path.insert(0, '/opt/python')

from admin_api import (
    list_conversations,
    get_conversation_detail,
    lambda_handler,
    decimal_to_float,
    create_response,
    extract_user_context
)


class TestHelperFunctions:
    """測試輔助函數"""
    
    def test_decimal_to_float_single_value(self):
        """測試 Decimal 轉換 - 單個值"""
        assert decimal_to_float(Decimal('10')) == 10
        assert decimal_to_float(Decimal('10.5')) == 10.5
        assert decimal_to_float('string') == 'string'
        assert decimal_to_float(42) == 42
    
    def test_decimal_to_float_nested(self):
        """測試 Decimal 轉換 - 嵌套結構"""
        data = {
            'count': Decimal('5'),
            'items': [
                {'value': Decimal('10.5')},
                {'value': Decimal('20')}
            ]
        }
        result = decimal_to_float(data)
        assert result['count'] == 5
        assert result['items'][0]['value'] == 10.5
        assert result['items'][1]['value'] == 20
    
    def test_create_response(self):
        """測試響應創建"""
        response = create_response(200, {'message': 'ok'})
        assert response['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in response['headers']
        body = json.loads(response['body'])
        assert body['message'] == 'ok'
    
    def test_extract_user_context(self):
        """測試用戶上下文提取"""
        event = {
            'requestContext': {
                'authorizer': {
                    'principalId': 'user123',
                    'role': 'admin',
                    'email': 'admin@example.com'
                }
            }
        }
        context = extract_user_context(event)
        assert context['user_id'] == 'user123'
        assert context['role'] == 'admin'
        assert context['email'] == 'admin@example.com'
    
    def test_extract_user_context_missing(self):
        """測試提取用戶上下文 - 缺少數據"""
        event = {}
        context = extract_user_context(event)
        assert context['user_id'] == 'unknown'
        assert context['role'] == 'user'


@patch('admin_api.dynamodb')
@patch('admin_api.audit_service')
class TestListConversations:
    """測試對話列表 API"""
    
    def test_list_conversations_default(self, mock_audit, mock_dynamodb):
        """測試對話列表 - 默認參數"""
        # Mock table query
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [
                {
                    'conversation_id': 'conv1',
                    'user_id': 'user1',
                    'channel': 'web',
                    'timestamp': '2026-01-26T10:00:00Z'
                }
            ],
            'Count': 1
        }
        
        # 創建 event
        event = {
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'principalId': 'admin1',
                    'role': 'admin'
                }
            }
        }
        
        # 執行
        response = list_conversations(event, None)
        
        # 驗證
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 1
        assert len(body['conversations']) == 1
        assert body['conversations'][0]['conversation_id'] == 'conv1'
    
    def test_list_conversations_with_channel_filter(self, mock_audit, mock_dynamodb):
        """測試對話列表 - 通道篩選"""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [
                {'conversation_id': 'conv1', 'channel': 'telegram'}
            ]
        }
        
        event = {
            'queryStringParameters': {'channel': 'telegram'},
            'requestContext': {
                'authorizer': {'principalId': 'admin1', 'role': 'admin'}
            }
        }
        
        response = list_conversations(event, None)
        
        assert response['statusCode'] == 200
        # 驗證使用了 ChannelTimestampIndex
        call_args = mock_table.query.call_args[1]
        assert call_args['IndexName'] == 'ChannelTimestampIndex'
    
    def test_list_conversations_with_pagination(self, mock_audit, mock_dynamodb):
        """測試對話列表 - 分頁"""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [{'conversation_id': f'conv{i}'} for i in range(20)],
            'LastEvaluatedKey': {'conversation_id': 'conv20', 'timestamp': '2026-01-26'}
        }
        
        event = {
            'queryStringParameters': {'limit': '20'},
            'requestContext': {
                'authorizer': {'principalId': 'admin1', 'role': 'admin'}
            }
        }
        
        response = list_conversations(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'next_token' in body


@patch('admin_api.dynamodb')
@patch('admin_api.audit_service')
class TestGetConversationDetail:
    """測試對話詳情 API"""
    
    def test_get_conversation_detail_success(self, mock_audit, mock_dynamodb):
        """測試獲取對話詳情 - 成功"""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {
                'conversation_id': 'conv1',
                'user_id': 'user1',
                'channel': 'telegram',
                'messages': [
                    {
                        'role': 'user',
                        'content': 'Hello',
                        'attachments': [
                            {'type': 'photo', 'url': 's3://...'}
                        ]
                    },
                    {
                        'role': 'assistant',
                        'content': 'Hi there!'
                    }
                ]
            }
        }
        
        event = {
            'pathParameters': {'conversation_id': 'conv1'},
            'requestContext': {
                'authorizer': {'principalId': 'admin1', 'role': 'admin'}
            }
        }
        
        response = get_conversation_detail(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['conversation_id'] == 'conv1'
        assert body['statistics']['message_count'] == 2
        assert body['statistics']['attachments']['images'] == 1
        assert body['statistics']['attachments']['total'] == 1
    
    def test_get_conversation_detail_not_found(self, mock_audit, mock_dynamodb):
        """測試獲取對話詳情 - 不存在"""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {}
        
        event = {
            'pathParameters': {'conversation_id': 'nonexistent'},
            'requestContext': {
                'authorizer': {'principalId': 'admin1', 'role': 'admin'}
            }
        }
        
        response = get_conversation_detail(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_get_conversation_detail_missing_id(self, mock_audit, mock_dynamodb):
        """測試獲取對話詳情 - 缺少 ID"""
        event = {
            'pathParameters': {},
            'requestContext': {
                'authorizer': {'principalId': 'admin1', 'role': 'admin'}
            }
        }
        
        response = get_conversation_detail(event, None)
        
        assert response['statusCode'] == 400


@patch('admin_api.list_conversations')
@patch('admin_api.get_conversation_detail')
class TestLambdaHandler:
    """測試主 handler 路由"""
    
    def test_route_list_conversations(self, mock_detail, mock_list):
        """測試路由 - 對話列表"""
        mock_list.return_value = create_response(200, {'conversations': []})
        
        event = {
            'httpMethod': 'GET',
            'path': '/admin/conversations'
        }
        
        response = lambda_handler(event, None)
        
        mock_list.assert_called_once()
        assert response['statusCode'] == 200
    
    def test_route_conversation_detail(self, mock_detail, mock_list):
        """測試路由 - 對話詳情"""
        mock_detail.return_value = create_response(200, {'conversation_id': 'conv1'})
        
        event = {
            'httpMethod': 'GET',
            'path': '/admin/conversations/conv1'
        }
        
        response = lambda_handler(event, None)
        
        mock_detail.assert_called_once()
        assert response['statusCode'] == 200
    
    def test_route_options(self, mock_detail, mock_list):
        """測試路由 - OPTIONS 預檢"""
        event = {
            'httpMethod': 'OPTIONS',
            'path': '/admin/conversations'
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        mock_list.assert_not_called()
        mock_detail.assert_not_called()
    
    def test_route_not_found(self, mock_detail, mock_list):
        """測試路由 - 404"""
        event = {
            'httpMethod': 'GET',
            'path': '/admin/unknown'
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 404


if __name__ == '__main__':
    pytest.main([__file__, '-v'])