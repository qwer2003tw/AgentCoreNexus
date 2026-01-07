"""
Base Message Delivery Interface
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class DeliveryResult:
    """訊息傳送結果"""

    success: bool
    channel: str
    user_id: str
    error: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """轉換為字典格式"""
        result = {
            "success": self.success,
            "channel": self.channel,
            "user_id": self.user_id,
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result


class MessageDelivery(ABC):
    """訊息傳送抽象基類"""

    @abstractmethod
    def deliver(
        self, user_id: str, message: str, context: dict[str, Any] | None = None
    ) -> DeliveryResult:
        """
        傳送訊息給使用者

        Args:
            user_id: 使用者 ID（例如 Telegram chat_id）
            message: 要傳送的訊息內容
            context: 額外的上下文資訊

        Returns:
            DeliveryResult: 傳送結果
        """
        pass

    @abstractmethod
    def get_channel_name(self) -> str:
        """
        取得頻道名稱

        Returns:
            str: 頻道名稱（telegram, discord, slack, web）
        """
        pass

    def format_error_message(self, error: str) -> str:
        """
        格式化錯誤訊息（子類可覆寫以自訂格式）

        Args:
            error: 原始錯誤訊息

        Returns:
            str: 格式化後的錯誤訊息
        """
        return f"❌ 訊息傳送失敗\n\n錯誤：{error}"

    def validate_user_id(self, user_id: str) -> bool:
        """
        驗證使用者 ID 格式（子類可覆寫）

        Args:
            user_id: 使用者 ID

        Returns:
            bool: 是否有效
        """
        return bool(user_id and user_id.strip())
