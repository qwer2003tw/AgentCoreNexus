"""
Telegram Message Formatter - Format AI responses for Telegram
"""

import re
from typing import Any


class TelegramFormatter:
    """Telegram 訊息格式化器"""

    # Telegram 訊息長度限制
    MAX_MESSAGE_LENGTH = 4096

    def __init__(self, parse_mode: str | None = None):
        """
        初始化格式化器

        Args:
            parse_mode: 解析模式 ('Markdown', 'HTML', 或 None 表示純文字)
        """
        self.parse_mode = parse_mode

    def format(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """
        格式化訊息內容

        Args:
            content: 原始訊息內容
            metadata: 額外的元資料

        Returns:
            str: 格式化後的訊息
        """
        # 如果訊息為空，返回預設訊息
        if not content or not content.strip():
            return "✅ 處理完成（無回應內容）"

        # 移除過多的空白行
        formatted = self._normalize_whitespace(content)

        # 如果有元資料，添加到訊息末尾
        if metadata and self._should_include_metadata(metadata):
            formatted = self._append_metadata(formatted, metadata)

        # 確保訊息長度不超過限制
        if len(formatted) > self.MAX_MESSAGE_LENGTH:
            formatted = self._truncate_message(formatted)

        return formatted

    def format_error(self, error_message: str, show_details: bool = False) -> str:
        """
        格式化錯誤訊息

        Args:
            error_message: 錯誤訊息
            show_details: 是否顯示詳細錯誤

        Returns:
            str: 格式化後的錯誤訊息
        """
        if show_details:
            return f"❌ **處理失敗**\n\n錯誤詳情：\n```\n{error_message}\n```"
        else:
            return "❌ **處理失敗**\n\n抱歉，處理您的訊息時發生錯誤。請稍後再試。"

    def format_success(self, message: str = "") -> str:
        """
        格式化成功訊息

        Args:
            message: 額外的成功訊息

        Returns:
            str: 格式化後的成功訊息
        """
        if message:
            return f"✅ {message}"
        return "✅ 處理完成"

    def _normalize_whitespace(self, text: str) -> str:
        """
        正規化空白字元（移除過多的空白行）

        Args:
            text: 原始文字

        Returns:
            str: 正規化後的文字
        """
        # 移除行尾空白
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

        # 將連續的空白行（3 行以上）壓縮為 2 行
        text = re.sub(r"\n{3,}", "\n\n", text)

        # 移除開頭和結尾的空白
        text = text.strip()

        return text

    def _should_include_metadata(self, metadata: dict[str, Any]) -> bool:
        """
        判斷是否應該包含元資料

        Args:
            metadata: 元資料字典

        Returns:
            bool: 是否包含
        """
        # 只有在有有用資訊時才包含
        useful_keys = ["processing_time", "model", "tokens_used"]
        return any(key in metadata for key in useful_keys)

    def _append_metadata(self, content: str, metadata: dict[str, Any]) -> str:
        """
        添加元資料到訊息末尾

        Args:
            content: 原始內容
            metadata: 元資料

        Returns:
            str: 添加元資料後的內容
        """
        meta_parts = []

        if "processing_time" in metadata:
            time_ms = metadata["processing_time"]
            if isinstance(time_ms, (int, float)):
                meta_parts.append(f"⏱ {time_ms:.0f}ms")

        if "model" in metadata:
            model = metadata["model"]
            if isinstance(model, str) and model:
                # 簡化模型名稱（例如 "claude-3-sonnet" → "Sonnet"）
                simplified_model = self._simplify_model_name(model)
                meta_parts.append(f"🤖 {simplified_model}")

        if "tokens_used" in metadata:
            tokens = metadata["tokens_used"]
            if isinstance(tokens, int):
                meta_parts.append(f"📊 {tokens} tokens")

        if meta_parts:
            meta_text = " • ".join(meta_parts)
            return f"{content}\n\n---\n_{meta_text}_"

        return content

    def _simplify_model_name(self, model: str) -> str:
        """
        簡化模型名稱

        Args:
            model: 完整模型名稱

        Returns:
            str: 簡化後的名稱
        """
        # 常見模型簡化
        simplifications = {
            "claude-3-opus": "Opus",
            "claude-3-sonnet": "Sonnet",
            "claude-3-haiku": "Haiku",
            "gpt-4": "GPT-4",
            "gpt-3.5-turbo": "GPT-3.5",
        }

        # 檢查精確匹配
        for full_name, simple_name in simplifications.items():
            if full_name in model.lower():
                return simple_name

        # 如果沒有匹配，返回原名稱（截斷過長的名稱）
        if len(model) > 20:
            return model[:17] + "..."
        return model

    def _truncate_message(self, text: str) -> str:
        """
        截斷過長的訊息

        Args:
            text: 原始文字

        Returns:
            str: 截斷後的文字
        """
        # 保留一些空間給截斷提示
        max_content_length = self.MAX_MESSAGE_LENGTH - 100

        if len(text) <= max_content_length:
            return text

        # 截斷並添加提示
        truncated = text[:max_content_length]

        # 嘗試在段落邊界截斷
        last_paragraph = truncated.rfind("\n\n")
        if last_paragraph > max_content_length * 0.8:
            truncated = truncated[:last_paragraph]

        # 添加截斷提示
        truncated += f"\n\n---\n⚠️ _訊息過長，已截斷（共 {len(text)} 字元）_"

        return truncated

    def get_parse_mode(self) -> str | None:
        """
        取得當前的解析模式

        Returns:
            Optional[str]: 解析模式
        """
        return self.parse_mode
