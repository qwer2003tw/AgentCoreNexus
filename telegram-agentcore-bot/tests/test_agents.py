"""
測試 Agents 模組
測試 ConversationAgent 類別的功能
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from agents.conversation_agent import ConversationAgent


class TestConversationAgent(unittest.TestCase):
    """測試 ConversationAgent 類別"""
    
    def setUp(self):
        """測試前準備"""
        self.tools = [Mock(), Mock()]
        self.session_manager = Mock()
    
    @patch('agents.conversation_agent.BedrockModel')
    @patch('agents.conversation_agent.Agent')
    def test_init_success(self, mock_agent_class, mock_model_class):
        """測試初始化成功"""
        # 設定 mocks
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent
        
        # 創建實例
        agent = ConversationAgent(self.tools, self.session_manager)
        
        # 驗證
        self.assertIsNotNone(agent)
        self.assertEqual(agent.tools, self.tools)
        self.assertEqual(agent.session_manager, self.session_manager)
        self.assertEqual(agent.agent, mock_agent)
        
        # 驗證 Model 被正確初始化
        mock_model_class.assert_called_once()
        
        # 驗證 Agent 被正確初始化
        mock_agent_class.assert_called_once_with(
            model=mock_model,
            session_manager=self.session_manager,
            system_prompt=unittest.mock.ANY,
            tools=self.tools
        )
    
    @patch('agents.conversation_agent.BedrockModel')
    @patch('agents.conversation_agent.Agent')
    def test_init_without_session_manager(self, mock_agent_class, mock_model_class):
        """測試不使用 session manager 初始化"""
        mock_agent_class.return_value = Mock()
        mock_model_class.return_value = Mock()
        
        agent = ConversationAgent(self.tools)
        
        self.assertIsNone(agent.session_manager)
        mock_agent_class.assert_called_once()
    
    @patch('agents.conversation_agent.BedrockModel')
    @patch('agents.conversation_agent.Agent')
    def test_init_failure(self, mock_agent_class, mock_model_class):
        """測試初始化失敗"""
        mock_model_class.side_effect = Exception("Model 建立失敗")
        
        with self.assertRaises(Exception):
            ConversationAgent(self.tools, self.session_manager)
    
    @patch('agents.conversation_agent.BedrockModel')
    @patch('agents.conversation_agent.Agent')
    def test_process_message_success(self, mock_agent_class, mock_model_class):
        """測試訊息處理成功"""
        # 設定 mocks
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.message = {
            'role': 'assistant',
            'content': [{'text': '這是回應內容'}]
        }
        mock_agent.return_value = mock_result
        mock_agent_class.return_value = mock_agent
        mock_model_class.return_value = Mock()
        
        # 創建實例並處理訊息
        agent = ConversationAgent(self.tools)
        result = agent.process_message("測試訊息")
        
        # 驗證
        self.assertTrue(result['success'])
        self.assertEqual(result['response'], '這是回應內容')
        mock_agent.assert_called_once_with("測試訊息")
    
    @patch('agents.conversation_agent.BedrockModel')
    @patch('agents.conversation_agent.Agent')
    def test_process_message_empty_input(self, mock_agent_class, mock_model_class):
        """測試空訊息處理"""
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.message = {
            'content': [{'text': '回應'}]
        }
        mock_agent.return_value = mock_result
        mock_agent_class.return_value = mock_agent
        mock_model_class.return_value = Mock()
        
        agent = ConversationAgent(self.tools)
        result = agent.process_message("")
        
        # 應該使用預設訊息
        self.assertTrue(result['success'])
        mock_agent.assert_called_once_with("你好，我需要協助")
    
    @patch('agents.conversation_agent.BedrockModel')
    @patch('agents.conversation_agent.Agent')
    def test_process_message_failure(self, mock_agent_class, mock_model_class):
        """測試訊息處理失敗"""
        mock_agent = Mock()
        mock_agent.side_effect = Exception("處理失敗")
        mock_agent_class.return_value = mock_agent
        mock_model_class.return_value = Mock()
        
        agent = ConversationAgent(self.tools)
        result = agent.process_message("測試訊息")
        
        # 驗證錯誤處理
        self.assertFalse(result['success'])
        self.assertIn('處理訊息時發生錯誤', result['response'])
        self.assertIn('error', result)
    
    @patch('agents.conversation_agent.BedrockModel')
    @patch('agents.conversation_agent.Agent')
    def test_extract_response_from_message_dict(self, mock_agent_class, mock_model_class):
        """測試從 message dict 提取回應"""
        mock_agent_class.return_value = Mock()
        mock_model_class.return_value = Mock()
        
        agent = ConversationAgent(self.tools)
        
        # 測試 content 陣列格式
        result = Mock()
        result.message = {
            'role': 'assistant',
            'content': [{'text': '測試回應1'}]
        }
        response = agent._extract_response(result)
        self.assertEqual(response, '測試回應1')
        
        # 測試 text 鍵格式
        result.message = {'text': '測試回應2'}
        response = agent._extract_response(result)
        self.assertEqual(response, '測試回應2')
    
    @patch('agents.conversation_agent.BedrockModel')
    @patch('agents.conversation_agent.Agent')
    def test_extract_response_from_content(self, mock_agent_class, mock_model_class):
        """測試從 content 提取回應"""
        mock_agent_class.return_value = Mock()
        mock_model_class.return_value = Mock()
        
        agent = ConversationAgent(self.tools)
        
        # 測試 content 陣列
        result = Mock()
        result.message = None
        result.content = [{'text': '從 content 提取'}]
        response = agent._extract_response(result)
        self.assertEqual(response, '從 content 提取')
    
    @patch('agents.conversation_agent.BedrockModel')
    @patch('agents.conversation_agent.Agent')
    def test_extract_response_fallback_to_str(self, mock_agent_class, mock_model_class):
        """測試回應提取的降級處理"""
        mock_agent_class.return_value = Mock()
        mock_model_class.return_value = Mock()
        
        agent = ConversationAgent(self.tools)
        
        # 測試字串化降級
        result = Mock()
        result.message = None
        result.content = None
        result.__str__ = lambda self: "字串化回應"
        
        response = agent._extract_response(result)
        self.assertEqual(response, "字串化回應")
    
    @patch('agents.conversation_agent.BedrockModel')
    @patch('agents.conversation_agent.Agent')
    def test_extract_response_empty_result(self, mock_agent_class, mock_model_class):
        """測試空結果的處理"""
        mock_agent_class.return_value = Mock()
        mock_model_class.return_value = Mock()
        
        agent = ConversationAgent(self.tools)
        
        # 測試完全空的結果
        result = Mock()
        result.message = None
        result.content = None
        result.__str__ = lambda self: ""
        
        response = agent._extract_response(result)
        self.assertIn("回應內容為空", response)
    
    @patch('agents.conversation_agent.BedrockModel')
    @patch('agents.conversation_agent.Agent')
    def test_extract_response_filters_meaningless(self, mock_agent_class, mock_model_class):
        """測試過濾無意義的回應"""
        mock_agent_class.return_value = Mock()
        mock_model_class.return_value = Mock()
        
        agent = ConversationAgent(self.tools)
        
        # 測試各種無意義的回應
        for meaningless in ['{}', '[]', 'None', '{"role": "assistant", "content": []}']:
            result = Mock()
            result.message = None
            result.content = None
            result.__str__ = lambda self, m=meaningless: m
            
            response = agent._extract_response(result)
            self.assertIn("回應內容為空", response)
    
    @patch('agents.conversation_agent.BedrockModel')
    @patch('agents.conversation_agent.Agent')
    def test_extract_from_message_various_formats(self, mock_agent_class, mock_model_class):
        """測試 _extract_from_message 的各種格式"""
        mock_agent_class.return_value = Mock()
        mock_model_class.return_value = Mock()
        
        agent = ConversationAgent(self.tools)
        
        # 測試 content 陣列格式
        message = {'content': [{'text': '回應1'}]}
        result = agent._extract_from_message(message)
        self.assertEqual(result, '回應1')
        
        # 測試 text 鍵格式
        message = {'text': '回應2'}
        result = agent._extract_from_message(message)
        self.assertEqual(result, '回應2')
        
        # 測試 assistant role 格式
        message = {
            'role': 'assistant',
            'content': [{'text': '回應3'}]
        }
        result = agent._extract_from_message(message)
        self.assertEqual(result, '回應3')
    
    @patch('agents.conversation_agent.BedrockModel')
    @patch('agents.conversation_agent.Agent')
    def test_extract_from_content_various_types(self, mock_agent_class, mock_model_class):
        """測試 _extract_from_content 的各種類型"""
        mock_agent_class.return_value = Mock()
        mock_model_class.return_value = Mock()
        
        agent = ConversationAgent(self.tools)
        
        # 測試 dict 陣列
        content = [{'text': '內容1'}]
        result = agent._extract_from_content(content)
        self.assertEqual(result, '內容1')
        
        # 測試字串陣列
        content = ['字串內容']
        result = agent._extract_from_content(content)
        self.assertEqual(result, '字串內容')
        
        # 測試直接字串
        content = '直接字串'
        result = agent._extract_from_content(content)
        self.assertEqual(result, '直接字串')


class TestAgentsModule(unittest.TestCase):
    """測試 agents 模組的導入"""
    
    def test_module_imports(self):
        """測試模組可以正確導入"""
        from agents import ConversationAgent
        self.assertIsNotNone(ConversationAgent)
    
    def test_conversation_agent_is_class(self):
        """測試 ConversationAgent 是一個類別"""
        from agents import ConversationAgent
        import inspect
        self.assertTrue(inspect.isclass(ConversationAgent))


if __name__ == '__main__':
    unittest.main()
