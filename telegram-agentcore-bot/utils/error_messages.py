"""
用戶友善錯誤訊息管理
將技術錯誤轉換為易懂的用戶提示
"""

from typing import Any

# 錯誤類型到友善訊息的映射
ERROR_MESSAGES = {
    "bedrock_stream_error": "😔 AI 服務暫時無法回應，請稍後再試",
    "bedrock_throttling": "⏸️ 服務繁忙中，請稍候片刻再試",
    "context_too_large": "📚 對話歷史過長，請使用 /new 開始新對話",
    "memory_error": "💾 記憶服務暫時無法使用，已切換到無記憶模式",
    "timeout": "⏱️ 處理時間過長，請簡化問題或分段詢問",
    "file_processing_error": "📁 檔案處理失敗，請檢查檔案格式",
    "image_processing_error": "🖼️ 圖片處理失敗，請確認圖片格式正確",
    "generic": "❌ 系統處理時遇到問題，請稍後再試",
}


def get_user_friendly_error(error: Exception | str, context: dict[str, Any] | None = None) -> str:
    """
    將技術錯誤轉換為用戶友善的訊息

    Args:
        error: 異常物件或錯誤訊息
        context: 額外的上下文資訊

    Returns:
        用戶友善的錯誤訊息
    """
    error_str = str(error).lower()
    context = context or {}

    # Bedrock streaming 錯誤
    if "modelstreamerrorexception" in error_str or "eventstreamerror" in error_str:
        return ERROR_MESSAGES["bedrock_stream_error"]

    # Throttling 錯誤
    if "throttling" in error_str or "rate" in error_str:
        return ERROR_MESSAGES["bedrock_throttling"]

    # Context 過大錯誤
    if "context" in error_str and ("large" in error_str or "limit" in error_str):
        return ERROR_MESSAGES["context_too_large"]

    # Memory 相關錯誤
    if "memory" in error_str or context.get("memory_error"):
        return ERROR_MESSAGES["memory_error"]

    # Timeout 錯誤
    if "timeout" in error_str or "timed out" in error_str:
        return ERROR_MESSAGES["timeout"]

    # 檔案處理錯誤
    if context.get("processing_file"):
        return ERROR_MESSAGES["file_processing_error"]

    # 圖片處理錯誤
    if context.get("processing_image"):
        return ERROR_MESSAGES["image_processing_error"]

    # 通用錯誤
    return ERROR_MESSAGES["generic"]


def should_suggest_new_conversation(error: Exception | str) -> bool:
    """
    判斷是否應該建議用戶開始新對話

    Args:
        error: 異常物件或錯誤訊息

    Returns:
        是否建議開始新對話
    """
    error_str = str(error).lower()

    # Context 相關問題建議重新開始
    return any(
        keyword in error_str
        for keyword in ["context", "token", "limit", "large", "memory", "history"]
    )


def format_error_response(
    error: Exception | str, context: dict[str, Any] | None = None, include_hint: bool = True
) -> str:
    """
    格式化完整的錯誤回應

    Args:
        error: 異常物件或錯誤訊息
        context: 額外的上下文資訊
        include_hint: 是否包含操作提示

    Returns:
        格式化的錯誤訊息
    """
    friendly_message = get_user_friendly_error(error, context)

    if not include_hint:
        return friendly_message

    # 添加操作提示
    hints = []

    if should_suggest_new_conversation(error):
        hints.append("💡 建議：使用 /new 開始新對話")

    # 如果是重試後仍失敗
    if context and context.get("retry_count", 0) > 0:
        hints.append("💡 已自動重試但仍失敗，請稍後再試")

    if hints:
        return f"{friendly_message}\n\n{chr(10).join(hints)}"

    return friendly_message
