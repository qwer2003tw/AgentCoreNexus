"""
工具模組測試
測試所有工具函數
"""

import json
import unittest
from datetime import datetime

from tools.calculator import calculate
from tools.time_utils import get_current_time
from tools.user_info import get_user_info
from tools.weather import get_weather


class TestWeatherTool(unittest.TestCase):
    """測試天氣工具"""

    def test_get_weather_taipei(self):
        """測試取得台北天氣"""
        result = get_weather("台北")
        self.assertIn("晴天", result)
        self.assertIn("25°C", result)

    def test_get_weather_taichung(self):
        """測試取得台中天氣"""
        result = get_weather("台中")
        self.assertIn("多雲", result)
        self.assertIn("23°C", result)

    def test_get_weather_kaohsiung(self):
        """測試取得高雄天氣"""
        result = get_weather("高雄")
        self.assertIn("晴天", result)
        self.assertIn("28°C", result)

    def test_get_weather_unknown_city(self):
        """測試未知城市"""
        result = get_weather("未知城市")
        self.assertIn("未知城市", result)
        self.assertIn("尚未提供", result)


class TestCalculatorTool(unittest.TestCase):
    """測試計算器工具"""

    def test_simple_addition(self):
        """測試簡單加法"""
        result = calculate("2 + 2")
        self.assertIn("4", result)

    def test_simple_subtraction(self):
        """測試簡單減法"""
        result = calculate("10 - 5")
        self.assertIn("5", result)

    def test_multiplication(self):
        """測試乘法"""
        result = calculate("3 * 4")
        self.assertIn("12", result)

    def test_division(self):
        """測試除法"""
        result = calculate("10 / 2")
        self.assertIn("5", result)

    def test_complex_expression(self):
        """測試複雜運算式"""
        result = calculate("(2 + 3) * 4")
        self.assertIn("20", result)

    def test_invalid_characters(self):
        """測試無效字元"""
        result = calculate("2 + abc")
        self.assertIn("只允許基本數學運算", result)

    def test_dangerous_expression(self):
        """測試危險運算式"""
        result = calculate("__import__('os').system('ls')")
        self.assertIn("只允許基本數學運算", result)

    def test_division_by_zero(self):
        """測試除以零"""
        result = calculate("10 / 0")
        self.assertIn("錯誤", result)


class TestUserInfoTool(unittest.TestCase):
    """測試用戶資訊工具"""

    def test_get_user_info(self):
        """測試取得用戶資訊"""
        result = get_user_info("test_user_123")
        data = json.loads(result)

        self.assertEqual(data["user_id"], "test_user_123")
        self.assertEqual(data["status"], "active")
        self.assertIn("joined_date", data)
        self.assertIn("timestamp", data)

    def test_user_info_structure(self):
        """測試用戶資訊結構"""
        result = get_user_info("user456")
        data = json.loads(result)

        # 檢查所有必要欄位
        required_fields = ["user_id", "status", "joined_date", "timestamp"]
        for field in required_fields:
            self.assertIn(field, data)

    def test_user_info_timestamp_format(self):
        """測試時間戳格式"""
        result = get_user_info("user789")
        data = json.loads(result)

        # 驗證時間戳格式
        timestamp = data["timestamp"]
        datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")


class TestTimeUtilsTool(unittest.TestCase):
    """測試時間工具"""

    def test_get_current_time(self):
        """測試取得當前時間"""
        result = get_current_time()
        self.assertIn("目前時間", result)
        self.assertIn("台北時間", result)

    def test_time_format(self):
        """測試時間格式"""
        result = get_current_time()
        # 檢查是否包含日期和時間格式
        self.assertIn("-", result)  # 日期分隔符
        self.assertIn(":", result)  # 時間分隔符


class TestToolsModule(unittest.TestCase):
    """測試工具模組"""

    def test_available_tools_import(self):
        """測試 AVAILABLE_TOOLS 導入"""
        from tools import AVAILABLE_TOOLS

        self.assertIsNotNone(AVAILABLE_TOOLS)
        self.assertIsInstance(AVAILABLE_TOOLS, list)
        self.assertGreater(len(AVAILABLE_TOOLS), 0)

    def test_individual_tool_imports(self):
        """測試個別工具導入"""
        from tools import (
            browse_website_backup,
            browse_website_official,
            calculate,
            get_current_time,
            get_user_info,
            get_weather,
        )

        # 確保所有工具都可以導入
        self.assertIsNotNone(get_weather)
        self.assertIsNotNone(calculate)
        self.assertIsNotNone(get_user_info)
        self.assertIsNotNone(get_current_time)
        self.assertIsNotNone(browse_website_official)
        self.assertIsNotNone(browse_website_backup)


if __name__ == "__main__":
    unittest.main()
