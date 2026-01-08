"""
Context 大小分析器
幫助診斷 token 限制和 context 過大問題
"""

from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)

# Token 估算：平均每個字元約 0.25 tokens（中文）或 0.33 tokens（英文）
# 保守估計使用 0.4
CHARS_PER_TOKEN = 2.5


def estimate_tokens(text: str | list | dict) -> int:
    """
    估算文字的 token 數量

    Args:
        text: 文字、列表或字典

    Returns:
        估算的 token 數量
    """
    if isinstance(text, (list, dict)) or not isinstance(text, str):
        text = str(text)

    char_count = len(text)
    estimated_tokens = int(char_count / CHARS_PER_TOKEN)

    return estimated_tokens


def analyze_context_size(
    messages: Any = None,
    memory_context: Any = None,
    tool_results: Any = None,
    images: list | None = None,
) -> dict[str, Any]:
    """
    分析 context 各部分的大小

    Args:
        messages: 消息內容
        memory_context: Memory 檢索的內容
        tool_results: 工具執行結果
        images: 圖片列表

    Returns:
        分析結果字典
    """
    analysis = {
        "messages_chars": 0,
        "messages_tokens": 0,
        "memory_chars": 0,
        "memory_tokens": 0,
        "tool_results_chars": 0,
        "tool_results_tokens": 0,
        "images_count": 0,
        "images_tokens": 0,  # 每張圖片約 ~1000 tokens
        "total_tokens": 0,
        "is_large": False,
        "warning_level": "normal",  # normal, warning, critical
    }

    # 分析消息
    if messages:
        messages_str = str(messages)
        analysis["messages_chars"] = len(messages_str)
        analysis["messages_tokens"] = estimate_tokens(messages_str)

    # 分析 Memory context
    if memory_context:
        memory_str = str(memory_context)
        analysis["memory_chars"] = len(memory_str)
        analysis["memory_tokens"] = estimate_tokens(memory_str)

    # 分析工具結果
    if tool_results:
        tool_str = str(tool_results)
        analysis["tool_results_chars"] = len(tool_str)
        analysis["tool_results_tokens"] = estimate_tokens(tool_str)

    # 分析圖片
    if images:
        analysis["images_count"] = len(images)
        analysis["images_tokens"] = len(images) * 1000  # 每張圖片約 1000 tokens

    # 計算總 tokens
    analysis["total_tokens"] = (
        analysis["messages_tokens"]
        + analysis["memory_tokens"]
        + analysis["tool_results_tokens"]
        + analysis["images_tokens"]
    )

    # 判斷大小級別
    if analysis["total_tokens"] > 150000:  # >150K tokens
        analysis["is_large"] = True
        analysis["warning_level"] = "critical"
    elif analysis["total_tokens"] > 100000:  # >100K tokens
        analysis["is_large"] = True
        analysis["warning_level"] = "warning"

    return analysis


def log_context_analysis(
    analysis: dict[str, Any], user_id: str | None = None, operation: str = "process_message"
) -> None:
    """
    記錄 context 分析結果到日誌

    Args:
        analysis: 分析結果
        user_id: 用戶 ID
        operation: 操作類型
    """
    log_extra = {
        "user_id": user_id,
        "operation": operation,
        "total_tokens": analysis["total_tokens"],
        "messages_tokens": analysis["messages_tokens"],
        "memory_tokens": analysis["memory_tokens"],
        "tool_results_tokens": analysis["tool_results_tokens"],
        "images_count": analysis["images_count"],
        "warning_level": analysis["warning_level"],
    }

    if analysis["warning_level"] == "critical":
        logger.warning(
            f"🚨 Context size CRITICAL: {analysis['total_tokens']} tokens (>150K)",
            extra=log_extra,
        )
    elif analysis["warning_level"] == "warning":
        logger.warning(
            f"⚠️ Context size WARNING: {analysis['total_tokens']} tokens (>100K)",
            extra=log_extra,
        )
    else:
        logger.info(f"📊 Context size: {analysis['total_tokens']} tokens", extra=log_extra)


def should_truncate_context(analysis: dict[str, Any]) -> bool:
    """
    判斷是否應該截斷 context

    Args:
        analysis: 分析結果

    Returns:
        是否應該截斷
    """
    # 超過 150K tokens 建議截斷
    return analysis["total_tokens"] > 150000


def get_truncation_suggestion(analysis: dict[str, Any]) -> dict[str, str]:
    """
    提供 context 截斷建議

    Args:
        analysis: 分析結果

    Returns:
        截斷建議
    """
    suggestions = []

    # Memory 佔用過大
    if analysis.get("memory_tokens", 0) > 50000:
        suggestions.append("limit_memory")

    # 工具結果過大
    if analysis.get("tool_results_tokens", 0) > 30000:
        suggestions.append("summarize_tool_results")

    # 消息過長
    if analysis.get("messages_tokens", 0) > 50000:
        suggestions.append("truncate_messages")

    return {
        "should_truncate": should_truncate_context(analysis),
        "suggestions": suggestions,
        "reason": f"Total tokens: {analysis.get('total_tokens', 0)} (limit: ~200K)",
    }
