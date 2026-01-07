"""
測試記憶功能整合
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from processor_entry import process_normalized_message, process_sqs_event, memory_service


class TestMemoryIntegration:
    """記憶功能整合測試"""
    
    def test_memory_service_initialization(self):
        """測試 Memory 服務初始化"""
        assert memory_service is not None
        assert hasattr(memory_service, 'enabled')
        assert hasattr(memory_service, 'get_session_manager')
    
    def test_process_normalized_message_without_memory(self):
        """測試無 Memory 的訊息處理"""
        # 準備測試數據
        normalized = {
            'messageId': 'test-123',
            'content': {
                'text': '你好',
                'messageType': 'text'
            },
            'user': {
                'id': '316743844',
                'displayName': 'Test User'
            },
            'context': {
                'sessionId': 'test-session'
            }
        }
        
        # Mock ConversationAgent
        with patch('processor_entry.ConversationAgent') as MockAgent:
            mock_agent_instance = Mock()
            mock_agent_instance.process_message.return_value = {
                'response': '你好！我是 Telegram Agent。'
            }
            MockAgent.return_value = mock_agent_instance
            
            # 執行測試
            result = process_normalized_message(normalized)
            
            # 驗證結果
            assert result['success'] is True
            assert 'response' in result
            assert result['user_id'] == '316743844'
            assert result['session_id'] == 'test-session'
            
            # 驗證 Agent 被正確建立
            MockAgent.assert_called_once()
            call_args = MockAgent.call_args
            assert 'tools' in call_args.kwargs or len(call_args.args) > 0
            assert 'session_manager' in call_args.kwargs or len(call_args.args) > 1
    
    def test_process_normalized_message_with_memory_enabled(self):
        """測試啟用 Memory 的訊息處理"""
        # 準備測試數據
        normalized = {
            'messageId': 'test-456',
            'content': {
                'text': '記住我的名字是 Steven',
                'messageType': 'text'
            },
            'user': {
                'id': '316743844',
                'displayName': 'Steven'
            },
            'context': {
                'sessionId': 'steven-session'
            }
        }
        
        # Mock Memory Service
        with patch.object(memory_service, 'enabled', True), \
             patch.object(memory_service, 'get_session_manager') as mock_get_session:
            
            # Mock Session Manager
            mock_session_manager = Mock()
            mock_get_session.return_value = mock_session_manager
            
            # Mock ConversationAgent
            with patch('processor_entry.ConversationAgent') as MockAgent:
                mock_agent_instance = Mock()
                mock_agent_instance.process_message.return_value = {
                    'response': '好的，我會記住你的名字是 Steven。'
                }
                MockAgent.return_value = mock_agent_instance
                
                # 執行測試
                result = process_normalized_message(normalized)
                
                # 驗證結果
                assert result['success'] is True
                assert '記住' in result['response'] or 'Steven' in result['response']
                
                # 驗證 Session Manager 被請求
                mock_get_session.assert_called_once()
                
                # 驗證 Agent 使用了 Session Manager
                MockAgent.assert_called_once()
                call_kwargs = MockAgent.call_args.kwargs
                assert call_kwargs.get('session_manager') == mock_session_manager
    
    def test_process_normalized_message_memory_failure_fallback(self):
        """測試 Memory 失敗時的容錯處理"""
        normalized = {
            'messageId': 'test-789',
            'content': {
                'text': '測試容錯',
                'messageType': 'text'
            },
            'user': {
                'id': '316743844',
                'displayName': 'Test User'
            },
            'context': {
                'sessionId': 'test-session'
            }
        }
        
        # Mock Memory Service 拋出異常
        with patch.object(memory_service, 'enabled', True), \
             patch.object(memory_service, 'get_session_manager', side_effect=Exception("Memory error")):
            
            # Mock ConversationAgent
            with patch('processor_entry.ConversationAgent') as MockAgent:
                mock_agent_instance = Mock()
                mock_agent_instance.process_message.return_value = {
                    'response': '處理成功（無記憶）'
                }
                MockAgent.return_value = mock_agent_instance
                
                # 執行測試（不應該拋出異常）
                result = process_normalized_message(normalized)
                
                # 驗證結果
                assert result['success'] is True
                
                # 驗證 Agent 使用 None 作為 session_manager（容錯模式）
                MockAgent.assert_called_once()
                call_kwargs = MockAgent.call_args.kwargs
                assert call_kwargs.get('session_manager') is None
    
    def test_process_sqs_event_with_memory(self):
        """測試 SQS 事件的 Memory 整合"""
        sqs_event = {
            'Records': [
                {
                    'body': '{"message": {"from": {"id": 316743844}, "text": "測試 SQS"}}'
                }
            ]
        }
        
        # Mock Memory Service
        with patch.object(memory_service, 'enabled', True), \
             patch.object(memory_service, 'get_session_manager') as mock_get_session:
            
            mock_session_manager = Mock()
            mock_get_session.return_value = mock_session_manager
            
            # Mock ConversationAgent
            with patch('processor_entry.ConversationAgent') as MockAgent:
                mock_agent_instance = Mock()
                mock_agent_instance.process_message.return_value = {
                    'response': 'SQS 處理成功'
                }
                MockAgent.return_value = mock_agent_instance
                
                # 執行測試
                result = process_sqs_event(sqs_event, None)
                
                # 驗證結果
                assert result['statusCode'] == 200
                
                # 驗證 Session Manager 被使用
                mock_get_session.assert_called_once()
                MockAgent.assert_called_once()
    
    def test_user_id_conversion_to_string(self):
        """測試 user_id 正確轉換為字串"""
        normalized = {
            'messageId': 'test-string',
            'content': {
                'text': '測試',
                'messageType': 'text'
            },
            'user': {
                'id': 316743844,  # 整數型別
                'displayName': 'Test'
            },
            'context': {
                'sessionId': 'test-session'
            }
        }
        
        with patch('processor_entry.ConversationAgent') as MockAgent:
            mock_agent_instance = Mock()
            mock_agent_instance.process_message.return_value = {
                'response': '測試回應'
            }
            MockAgent.return_value = mock_agent_instance
            
            result = process_normalized_message(normalized)
            
            # 驗證 user_id 是字串
            assert isinstance(result['user_id'], str)
            assert result['user_id'] == '316743844'
    
    def test_session_id_defaults_to_user_id(self):
        """測試 session_id 預設為 user_id"""
        normalized = {
            'messageId': 'test-default',
            'content': {
                'text': '測試',
                'messageType': 'text'
            },
            'user': {
                'id': '999888777',
                'displayName': 'Test'
            },
            'context': {}  # 沒有 sessionId
        }
        
        with patch('processor_entry.ConversationAgent') as MockAgent:
            mock_agent_instance = Mock()
            mock_agent_instance.process_message.return_value = {
                'response': '測試回應'
            }
            MockAgent.return_value = mock_agent_instance
            
            result = process_normalized_message(normalized)
            
            # 驗證 session_id 使用 user_id
            assert result['session_id'] == '999888777'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
