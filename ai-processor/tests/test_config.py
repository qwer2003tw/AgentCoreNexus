"""
配置模組測試
測試 config.settings 和 config.prompts
"""

import os
import unittest

from config.prompts import get_browser_prompt, get_error_message
from config.settings import Settings


class TestSettings(unittest.TestCase):
    """測試 Settings 類別"""

    def setUp(self):
        """測試前設定"""
        # 保存原始環境變數
        self.original_env = os.environ.copy()

    def tearDown(self):
        """測試後清理"""
        # 恢復原始環境變數
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_default_settings(self):
        """測試預設配置"""
        settings = Settings()
        self.assertEqual(settings.AWS_REGION, "us-west-2")
        self.assertIsNotNone(settings.BEDROCK_MODEL_ID)
        self.assertFalse(settings.MEMORY_ENABLED)

    def test_custom_region(self):
        """測試自定義區域"""
        os.environ["AWS_REGION"] = "us-east-1"
        settings = Settings()
        self.assertEqual(settings.AWS_REGION, "us-east-1")

    def test_memory_enabled(self):
        """測試 Memory 啟用"""
        os.environ["BEDROCK_AGENTCORE_MEMORY_ID"] = "test-memory-id"
        settings = Settings()
        self.assertTrue(settings.MEMORY_ENABLED)
        self.assertEqual(settings.MEMORY_ID, "test-memory-id")

    def test_memory_config(self):
        """測試 Memory 配置"""
        os.environ["BEDROCK_AGENTCORE_MEMORY_ID"] = "test-memory-id"
        settings = Settings()
        config = settings.memory_config
        self.assertIsNotNone(config)
        self.assertEqual(config["memory_id"], "test-memory-id")
        self.assertTrue(config["enabled"])

    def test_memory_config_disabled(self):
        """測試 Memory 未啟用時的配置"""
        settings = Settings()
        config = settings.memory_config
        self.assertIsNone(config)

    def test_is_production(self):
        """測試生產環境檢查"""
        os.environ["ENVIRONMENT"] = "production"
        settings = Settings()
        self.assertTrue(settings.is_production)

        os.environ["ENVIRONMENT"] = "development"
        settings = Settings()
        self.assertFalse(settings.is_production)

    def test_browser_settings(self):
        """測試瀏覽器配置"""
        os.environ["BROWSER_TIMEOUT"] = "60000"
        os.environ["BROWSER_ENABLED"] = "false"
        settings = Settings()
        self.assertEqual(settings.BROWSER_TIMEOUT, 60000)
        self.assertFalse(settings.BROWSER_ENABLED)

    def test_settings_string(self):
        """測試配置摘要字串"""
        settings = Settings()
        summary = str(settings)
        self.assertIn("AWS Region", summary)
        self.assertIn("Model", summary)
        self.assertIn("Memory", summary)


class TestPrompts(unittest.TestCase):
    """測試提示詞模組"""

    def test_get_error_message(self):
        """測試錯誤訊息取得"""
        msg = get_error_message("general", error="測試錯誤")
        self.assertIn("測試錯誤", msg)

    def test_get_error_message_invalid_type(self):
        """測試無效的錯誤類型"""
        msg = get_error_message("invalid_type", error="測試錯誤")
        self.assertIn("測試錯誤", msg)

    def test_get_browser_prompt(self):
        """測試瀏覽器提示"""
        prompt = get_browser_prompt("extracting_content")
        self.assertIsNotNone(prompt)
        self.assertIsInstance(prompt, str)

    def test_get_browser_prompt_invalid(self):
        """測試無效的瀏覽器提示"""
        prompt = get_browser_prompt("invalid_prompt")
        self.assertEqual(prompt, "")


if __name__ == "__main__":
    unittest.main()
