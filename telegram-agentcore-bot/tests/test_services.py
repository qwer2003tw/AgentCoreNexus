"""
測試 Services 模組
測試 Memory 和 Browser 服務功能
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from services.memory_service import MemoryService, memory_service
from services.browser_service import BrowserService


class TestMemoryService(unittest.TestCase):
    """測試 MemoryService 類別"""
    
    @patch('services.memory_service.settings')
    def test_init_with_memory_disabled(self, mock_settings):
        """測試 Memory 未啟用時的初始化"""
        mock_settings.MEMORY_ID = None
        mock_settings.MEMORY_ENABLED = False
        
        service = MemoryService()
        
        self.assertIsNone(service.memory_id)
        self.assertFalse(service.enabled)
    
    @patch('services.memory_service.settings')
    def test_init_with_memory_enabled(self, mock_settings):
        """測試 Memory 啟用時的初始化"""
        mock_settings.MEMORY_ID = "test-memory-id"
        mock_settings.MEMORY_ENABLED = True
        mock_settings.AWS_REGION = "us-west-2"
        
        # Mock 導入失敗（因為測試環境沒有真實的模組）
        with patch('services.memory_service.MemoryService._initialize_memory'):
            service = MemoryService()
            
            self.assertEqual(service.memory_id, "test-memory-id")
            self.assertTrue(service.enabled)
    
    @patch('services.memory_service.settings')
    def test_get_session_manager_disabled(self, mock_settings):
        """測試 Memory 未啟用時返回 None"""
        mock_settings.MEMORY_ENABLED = False
        
        service = MemoryService()
        service.enabled = False
        
        result = service.get_session_manager(Mock())
        
        self.assertIsNone(result)
    
    @patch('services.memory_service.settings')
    def test_extract_actor_id_from_headers(self, mock_settings):
        """測試從 headers 提取 actor_id"""
        service = MemoryService()
        
        mock_context = Mock()
        mock_context.headers = {
            'X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id': 'custom_user'
        }
        
        actor_id = service._extract_actor_id(mock_context)
        
        self.assertEqual(actor_id, 'custom_user')
    
    @patch('services.memory_service.settings')
    def test_extract_actor_id_default(self, mock_settings):
        """測試預設 actor_id"""
        service = MemoryService()
        
        mock_context = Mock(spec=[])  # 沒有 headers 屬性
        
        actor_id = service._extract_actor_id(mock_context)
        
        self.assertEqual(actor_id, 'user')
    
    @patch('services.memory_service.settings')
    def test_get_status(self, mock_settings):
        """測試取得服務狀態"""
        mock_settings.MEMORY_ID = "test-id"
        mock_settings.MEMORY_ENABLED = True
        mock_settings.AWS_REGION = "us-east-1"
        
        with patch('services.memory_service.MemoryService._initialize_memory'):
            service = MemoryService()
            status = service.get_status()
            
            self.assertIn('enabled', status)
            self.assertIn('memory_id', status)
            self.assertIn('region', status)
            self.assertEqual(status['region'], 'us-east-1')
    
    @patch('services.memory_service.settings')
    def test_create_memory_config(self, mock_settings):
        """測試建立 Memory 配置"""
        service = MemoryService()
        service._memory_config_class = Mock()
        service._retrieval_config_class = Mock(return_value=Mock())
        
        config = service._create_memory_config("session-123", "user-456")
        
        service._memory_config_class.assert_called_once()


class TestBrowserService(unittest.TestCase):
    """測試 BrowserService 類別"""
    
    def test_init_success(self):
        """測試初始化成功"""
        service = BrowserService(region="us-west-2")
        
        # 測試環境已安裝 strands_tools，初始化會成功
        self.assertTrue(service._available)
        self.assertIsNotNone(service.browser_tool)
        self.assertEqual(service.region, "us-west-2")
    
    def test_is_available_true(self):
        """測試瀏覽器可用"""
        service = BrowserService(region="us-west-2")
        
        # 測試環境中瀏覽器可用
        self.assertTrue(service.is_available())
    
    def test_init_with_custom_region(self):
        """測試使用自定義區域初始化"""
        service = BrowserService(region="ap-northeast-1")
        
        self.assertEqual(service.region, "ap-northeast-1")
        self.assertTrue(service._available)
    
    def test_browse_with_backup_unavailable(self):
        """測試瀏覽器不可用時的處理"""
        service = BrowserService(region="us-west-2")
        # 手動設置為不可用來測試錯誤處理
        service._available = False
        
        result = service.browse_with_backup("https://example.com", "test task")
        
        self.assertIn("瀏覽器服務不可用", result)
    
    def test_get_status(self):
        """測試取得服務狀態"""
        service = BrowserService(region="us-west-2")
        status = service.get_status()
        
        self.assertIn('available', status)
        self.assertIn('region', status)
        self.assertEqual(status['region'], 'us-west-2')
        self.assertTrue(status['available'])  # 測試環境中可用
    
    def test_extract_error_text(self):
        """測試提取錯誤文字"""
        service = BrowserService(region="us-west-2")
        
        # 測試正常情況
        result = {'content': [{'text': '錯誤訊息'}]}
        error = service._extract_error_text(result)
        self.assertEqual(error, '錯誤訊息')
        
        # 測試異常情況
        result = {}
        error = service._extract_error_text(result)
        self.assertEqual(error, '未知錯誤')
    
    def test_format_result(self):
        """測試格式化結果"""
        service = BrowserService(region="us-west-2")
        result = service._format_result(
            "https://example.com",
            "測試標題",
            "測試內容"
        )
        
        self.assertIn("https://example.com", result)
        self.assertIn("測試標題", result)
        self.assertIn("測試內容", result)


class TestServicesModule(unittest.TestCase):
    """測試 services 模組的導入"""
    
    def test_module_imports(self):
        """測試模組可以正確導入"""
        from services import MemoryService, BrowserService
        
        self.assertIsNotNone(MemoryService)
        self.assertIsNotNone(BrowserService)
    
    def test_memory_service_is_class(self):
        """測試 MemoryService 是一個類別"""
        from services import MemoryService
        import inspect
        
        self.assertTrue(inspect.isclass(MemoryService))
    
    def test_browser_service_is_class(self):
        """測試 BrowserService 是一個類別"""
        from services import BrowserService
        import inspect
        
        self.assertTrue(inspect.isclass(BrowserService))
    
    def test_memory_service_global_instance(self):
        """測試全域 memory_service 實例"""
        from services.memory_service import memory_service
        
        self.assertIsNotNone(memory_service)
        self.assertIsInstance(memory_service, MemoryService)


if __name__ == '__main__':
    unittest.main()
