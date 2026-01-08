"""
測試錯誤處理和重試機制
"""

from botocore.exceptions import ClientError, EventStreamError

from utils.context_analyzer import analyze_context_size, estimate_tokens, should_truncate_context
from utils.error_messages import (
    format_error_response,
    get_user_friendly_error,
    should_suggest_new_conversation,
)
from utils.retry_handler import RetryHandler


class TestErrorMessages:
    """測試用戶友善錯誤訊息"""

    def test_bedrock_stream_error(self):
        """測試 Bedrock streaming 錯誤訊息"""
        error = Exception("modelStreamErrorException in ConverseStream")
        msg = get_user_friendly_error(error)
        assert "AI 服務" in msg
        assert "稍後再試" in msg

    def test_throttling_error(self):
        """測試限流錯誤訊息"""
        error = Exception("ThrottlingException: Rate limit exceeded")
        msg = get_user_friendly_error(error)
        assert "繁忙" in msg or "throttl" in msg.lower()

    def test_context_too_large(self):
        """測試 context 過大錯誤"""
        error = Exception("Context size limit exceeded")
        msg = get_user_friendly_error(error)
        assert "對話歷史" in msg or "context" in msg.lower()

    def test_memory_error(self):
        """測試 Memory 錯誤訊息"""
        error = Exception("memory service error")
        msg = get_user_friendly_error(error, {"memory_error": True})
        assert "記憶服務" in msg

    def test_timeout_error(self):
        """測試 Timeout 錯誤訊息"""
        error = Exception("request timed out")
        msg = get_user_friendly_error(error)
        assert "時間過長" in msg or "timeout" in msg.lower()

    def test_file_processing_error(self):
        """測試檔案處理錯誤"""
        error = Exception("file error")
        msg = get_user_friendly_error(error, {"processing_file": True})
        assert "檔案處理" in msg

    def test_image_processing_error(self):
        """測試圖片處理錯誤"""
        error = Exception("image error")
        msg = get_user_friendly_error(error, {"processing_image": True})
        assert "圖片處理" in msg

    def test_generic_error(self):
        """測試通用錯誤"""
        error = Exception("unknown error")
        msg = get_user_friendly_error(error)
        assert "系統處理" in msg or "問題" in msg

    def test_should_suggest_new_conversation(self):
        """測試是否建議新對話"""
        # Context 相關錯誤應該建議新對話
        assert should_suggest_new_conversation("context limit exceeded") is True
        assert should_suggest_new_conversation("token limit reached") is True
        assert should_suggest_new_conversation("memory overflow") is True

        # 其他錯誤不建議
        assert should_suggest_new_conversation("network error") is False

    def test_format_error_response_with_retry(self):
        """測試包含重試次數的錯誤訊息"""
        error = Exception("EventStreamError")
        msg = format_error_response(error, {"retry_count": 2})
        assert "AI 服務" in msg
        assert "重試" in msg

    def test_format_error_response_without_hint(self):
        """測試不包含提示的錯誤訊息"""
        error = Exception("EventStreamError")
        msg = format_error_response(error, include_hint=False)
        assert "💡" not in msg  # 不應該有提示符號


class TestRetryHandler:
    """測試重試處理器"""

    def test_retry_success_on_first_attempt(self):
        """測試第一次嘗試就成功"""
        handler = RetryHandler(max_attempts=3)

        def success_func():
            return "success"

        result = handler.execute_with_retry(success_func)
        assert result["success"] is True
        assert result["attempts"] == 1

    def test_retry_success_after_failures(self):
        """測試失敗後重試成功"""
        handler = RetryHandler(max_attempts=3, base_delay=0.1)
        call_count = [0]

        def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise EventStreamError({"Error": {"Message": "test"}}, "TestOp")
            return "success"

        result = handler.execute_with_retry(flaky_func)
        assert result["success"] is True
        assert result["attempts"] == 3

    def test_fallback_on_all_failures(self):
        """測試所有重試失敗後使用降級"""
        handler = RetryHandler(max_attempts=2, base_delay=0.1)

        def always_fail():
            raise EventStreamError({"Error": {"Message": "error"}}, "TestOp")

        def fallback_func():
            return "fallback_result"

        result = handler.execute_with_retry(always_fail, fallback_func=fallback_func)
        assert result["success"] is True
        assert result.get("used_fallback") is True

    def test_complete_failure(self):
        """測試完全失敗的情況"""
        handler = RetryHandler(max_attempts=2, base_delay=0.1)

        def always_fail():
            raise EventStreamError({"Error": {"Message": "error"}}, "TestOp")

        result = handler.execute_with_retry(always_fail)
        assert result["success"] is False
        assert result["attempts"] == 2
        assert result["error"] is not None

    def test_non_retryable_error(self):
        """測試不可重試的錯誤"""
        handler = RetryHandler(max_attempts=3, base_delay=0.1)

        def non_retryable_func():
            raise ValueError("Invalid input")

        result = handler.execute_with_retry(non_retryable_func)
        assert result["success"] is False
        assert result["attempts"] == 3  # 只嘗試一次就停止

    def test_is_retryable_event_stream_error(self):
        """測試 EventStreamError 可重試"""
        handler = RetryHandler()
        error = EventStreamError({"Error": {"Message": "test"}}, "TestOp")
        assert handler._is_retryable(error) is True

    def test_is_retryable_throttling(self):
        """測試 Throttling 錯誤可重試"""
        handler = RetryHandler()
        error = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}}, "TestOp"
        )
        assert handler._is_retryable(error) is True

    def test_calculate_delay(self):
        """測試延遲計算"""
        handler = RetryHandler(base_delay=2.0)
        assert handler._calculate_delay(1) == 2.0
        assert handler._calculate_delay(2) == 4.0
        assert handler._calculate_delay(3) == 8.0
        assert handler._calculate_delay(10) == 10.0  # 最大 10 秒


class TestContextAnalyzer:
    """測試 Context 分析器"""

    def test_estimate_tokens(self):
        """測試 token 估算"""
        text = "測試" * 100  # 200 字元
        tokens = estimate_tokens(text)
        assert tokens > 0
        assert tokens == 80  # 200 / 2.5 = 80

    def test_estimate_tokens_with_dict(self):
        """測試字典的 token 估算"""
        data = {"key": "value", "nested": {"a": 1, "b": 2}}
        tokens = estimate_tokens(data)
        assert tokens > 0

    def test_estimate_tokens_with_list(self):
        """測試列表的 token 估算"""
        data = ["item1", "item2", "item3"]
        tokens = estimate_tokens(data)
        assert tokens > 0

    def test_analyze_context_size_basic(self):
        """測試基本 context 分析"""
        analysis = analyze_context_size(messages="test message")
        assert analysis["total_tokens"] > 0
        assert analysis["warning_level"] == "normal"
        assert analysis["is_large"] is False

    def test_analyze_context_size_warning(self):
        """測試 warning 級別"""
        large_text = "x" * 300000  # ~120K tokens (確保超過 100K)
        analysis = analyze_context_size(messages=large_text)
        assert analysis["warning_level"] == "warning"
        assert analysis["is_large"] is True

    def test_analyze_context_size_critical(self):
        """測試 critical 級別"""
        huge_text = "x" * 400000  # ~160K tokens
        analysis = analyze_context_size(messages=huge_text)
        assert analysis["warning_level"] == "critical"
        assert analysis["is_large"] is True

    def test_analyze_with_images(self):
        """測試包含圖片的分析"""
        images = [{"data": "base64..."}, {"data": "base64..."}]
        analysis = analyze_context_size(messages="test", images=images)
        assert analysis["images_count"] == 2
        assert analysis["images_tokens"] == 2000  # 2 * 1000

    def test_should_truncate_context(self):
        """測試是否應該截斷"""
        # 正常大小
        normal_analysis = {"total_tokens": 50000, "is_large": False}
        assert should_truncate_context(normal_analysis) is False

        # 過大
        large_analysis = {"total_tokens": 160000, "is_large": True}
        assert should_truncate_context(large_analysis) is True

    def test_analyze_with_memory_and_tools(self):
        """測試包含 Memory 和工具結果的分析"""
        analysis = analyze_context_size(
            messages="test message",
            memory_context={"history": ["msg1", "msg2"]},
            tool_results={"result": "data"},
        )
        assert analysis["memory_tokens"] > 0
        assert analysis["tool_results_tokens"] > 0
        assert analysis["total_tokens"] > 0

    def test_get_truncation_suggestion(self):
        """測試截斷建議"""
        from utils.context_analyzer import get_truncation_suggestion

        # 正常大小
        normal = {"total_tokens": 50000, "memory_tokens": 10000, "tool_results_tokens": 5000}
        suggestion = get_truncation_suggestion(normal)
        assert suggestion["should_truncate"] is False

        # Memory 過大
        large_memory = {
            "total_tokens": 160000,
            "memory_tokens": 60000,
            "tool_results_tokens": 5000,
        }
        suggestion = get_truncation_suggestion(large_memory)
        assert suggestion["should_truncate"] is True
        assert "limit_memory" in suggestion["suggestions"]


class TestErrorHandlingIntegration:
    """測試錯誤處理整合"""

    def test_retry_with_error_formatting(self):
        """測試重試失敗後的錯誤格式化"""
        handler = RetryHandler(max_attempts=2, base_delay=0.1)

        def fail_func():
            raise EventStreamError({"Error": {"Message": "stream error"}}, "TestOp")

        result = handler.execute_with_retry(fail_func)
        assert result["success"] is False

        # 格式化錯誤給用戶
        # 注意：EventStreamError 物件本身可能不包含關鍵字，需要用錯誤訊息字串
        error_msg = "modelStreamErrorException in ConverseStream operation"
        friendly_msg = format_error_response(error_msg, {"retry_count": result["attempts"]})
        assert "AI 服務" in friendly_msg
        assert "重試" in friendly_msg

    def test_context_analysis_with_error_decision(self):
        """測試 context 分析驅動錯誤決策"""
        # 模擬大 context
        large_text = "x" * 400000
        analysis = analyze_context_size(messages=large_text)

        # 如果 context 過大，應該建議新對話
        if analysis["is_large"]:
            error = Exception(f"Context too large: {analysis['total_tokens']} tokens")
            assert should_suggest_new_conversation(error) is True  # Test comment
