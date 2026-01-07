"""
Unit tests for telegram_client.py sensitive data redaction
"""

import json

from src.telegram_client import _redact_path, redact_sensitive_data


class TestRedactSensitiveData:
    """測試敏感資料遮蔽功能"""

    def test_redact_single_value(self):
        """測試遮蔽單一值"""
        data = {
            "headers": {
                "X-Telegram-Bot-Api-Secret-Token": "secret123",
                "Content-Type": "application/json",
            }
        }
        paths = [("headers", "X-Telegram-Bot-Api-Secret-Token")]

        result = redact_sensitive_data(data, paths)

        assert result["headers"]["X-Telegram-Bot-Api-Secret-Token"] == "[REDACTED]"
        assert result["headers"]["Content-Type"] == "application/json"
        # 確認原始資料未被修改
        assert data["headers"]["X-Telegram-Bot-Api-Secret-Token"] == "secret123"

    def test_redact_list_value(self):
        """測試遮蔽列表值"""
        data = {
            "multiValueHeaders": {
                "X-Telegram-Bot-Api-Secret-Token": ["secret123", "secret456"],
                "Accept": ["application/json"],
            }
        }
        paths = [("multiValueHeaders", "X-Telegram-Bot-Api-Secret-Token")]

        result = redact_sensitive_data(data, paths)

        assert result["multiValueHeaders"]["X-Telegram-Bot-Api-Secret-Token"] == [
            "[REDACTED]",
            "[REDACTED]",
        ]
        assert result["multiValueHeaders"]["Accept"] == ["application/json"]

    def test_redact_nested_value(self):
        """測試遮蔽巢狀值"""
        data = {"requestContext": {"accountId": "123456789012", "stage": "prod"}}
        paths = [("requestContext", "accountId")]

        result = redact_sensitive_data(data, paths)

        assert result["requestContext"]["accountId"] == "[REDACTED]"
        assert result["requestContext"]["stage"] == "prod"

    def test_redact_multiple_fields(self):
        """測試同時遮蔽多個欄位"""
        data = {
            "headers": {"X-Telegram-Bot-Api-Secret-Token": "secret123"},
            "multiValueHeaders": {"X-Telegram-Bot-Api-Secret-Token": ["secret456"]},
            "requestContext": {"accountId": "123456789012"},
        }
        paths = [
            ("headers", "X-Telegram-Bot-Api-Secret-Token"),
            ("multiValueHeaders", "X-Telegram-Bot-Api-Secret-Token"),
            ("requestContext", "accountId"),
        ]

        result = redact_sensitive_data(data, paths)

        assert result["headers"]["X-Telegram-Bot-Api-Secret-Token"] == "[REDACTED]"
        assert result["multiValueHeaders"]["X-Telegram-Bot-Api-Secret-Token"] == ["[REDACTED]"]
        assert result["requestContext"]["accountId"] == "[REDACTED]"

    def test_redact_nonexistent_field(self):
        """測試遮蔽不存在的欄位（應該不會出錯）"""
        data = {"headers": {"Content-Type": "application/json"}}
        paths = [("headers", "NonExistentField")]

        result = redact_sensitive_data(data, paths)

        assert result == data

    def test_redact_with_actual_event_structure(self):
        """測試使用實際 API Gateway event 結構"""
        event = {
            "headers": {
                "X-Telegram-Bot-Api-Secret-Token": "QDJxJf37waXXxacORJXtPYEJ3JTjxRH1pcarospeAAfn8pJC0dfPHfOqcgJqGkPd",
                "Content-Type": "application/json",
            },
            "multiValueHeaders": {
                "X-Telegram-Bot-Api-Secret-Token": [
                    "QDJxJf37waXXxacORJXtPYEJ3JTjxRH1pcarospeAAfn8pJC0dfPHfOqcgJqGkPd"
                ]
            },
            "requestContext": {"accountId": "190825685292", "apiId": "abcd1234", "stage": "prod"},
            "body": '{"message": {"text": "/debug"}}',
        }

        paths = [
            ("headers", "X-Telegram-Bot-Api-Secret-Token"),
            ("multiValueHeaders", "X-Telegram-Bot-Api-Secret-Token"),
            ("requestContext", "accountId"),
        ]

        result = redact_sensitive_data(event, paths)

        # 驗證敏感欄位已遮蔽
        assert result["headers"]["X-Telegram-Bot-Api-Secret-Token"] == "[REDACTED]"
        assert result["multiValueHeaders"]["X-Telegram-Bot-Api-Secret-Token"] == ["[REDACTED]"]
        assert result["requestContext"]["accountId"] == "[REDACTED]"

        # 驗證非敏感欄位未被修改
        assert result["headers"]["Content-Type"] == "application/json"
        assert result["requestContext"]["apiId"] == "abcd1234"
        assert result["requestContext"]["stage"] == "prod"
        assert result["body"] == '{"message": {"text": "/debug"}}'

        # 驗證原始 event 未被修改
        assert event["headers"]["X-Telegram-Bot-Api-Secret-Token"] != "[REDACTED]"


class TestRedactPath:
    """測試 _redact_path 輔助函數"""

    def test_redact_path_single_level(self):
        """測試單層路徑遮蔽"""
        data = {"key": "value"}
        _redact_path(data, ("key",))
        assert data["key"] == "[REDACTED]"

    def test_redact_path_nested(self):
        """測試巢狀路徑遮蔽"""
        data = {"outer": {"inner": "value"}}
        _redact_path(data, ("outer", "inner"))
        assert data["outer"]["inner"] == "[REDACTED]"

    def test_redact_path_list(self):
        """測試列表值遮蔽"""
        data = {"key": ["value1", "value2", "value3"]}
        _redact_path(data, ("key",))
        assert data["key"] == ["[REDACTED]", "[REDACTED]", "[REDACTED]"]

    def test_redact_path_empty(self):
        """測試空路徑（不應該修改資料）"""
        data = {"key": "value"}
        _redact_path(data, ())
        assert data["key"] == "value"

    def test_redact_path_invalid_key(self):
        """測試無效 key（不應該出錯）"""
        data = {"key": "value"}
        _redact_path(data, ("nonexistent",))
        assert data == {"key": "value"}

    def test_redact_path_non_dict_data(self):
        """測試非字典資料（不應該出錯）"""
        data = "not a dict"
        _redact_path(data, ("key",))
        # 應該不會拋出異常


class TestRedactionIntegration:
    """整合測試"""

    def test_json_serialization_after_redaction(self):
        """測試遮蔽後的資料可以正常序列化為 JSON"""
        data = {
            "headers": {"X-Telegram-Bot-Api-Secret-Token": "secret123"},
            "requestContext": {"accountId": "123456789012"},
        }
        paths = [("headers", "X-Telegram-Bot-Api-Secret-Token"), ("requestContext", "accountId")]

        result = redact_sensitive_data(data, paths)

        # 應該可以正常序列化為 JSON
        json_str = json.dumps(result, indent=2)
        assert "[REDACTED]" in json_str
        assert "secret123" not in json_str
        assert "123456789012" not in json_str

    def test_multiple_redaction_calls(self):
        """測試多次呼叫遮蔽函數"""
        data = {"field1": "value1", "field2": "value2", "field3": "value3"}

        # 第一次遮蔽
        result1 = redact_sensitive_data(data, [("field1",)])
        assert result1["field1"] == "[REDACTED]"
        assert result1["field2"] == "value2"

        # 第二次遮蔽（使用原始資料）
        result2 = redact_sensitive_data(data, [("field2",)])
        assert result2["field1"] == "value1"  # 原始資料未被修改
        assert result2["field2"] == "[REDACTED]"

        # 第三次遮蔽（遮蔽多個欄位）
        result3 = redact_sensitive_data(data, [("field1",), ("field3",)])
        assert result3["field1"] == "[REDACTED]"
        assert result3["field2"] == "value2"
        assert result3["field3"] == "[REDACTED]"
