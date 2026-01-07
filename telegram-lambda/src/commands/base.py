"""
Command Handler Base Class - 指令處理器基礎類別
"""

from abc import ABC, abstractmethod

from telegram import Update


class CommandHandler(ABC):
    """
    指令處理器基礎類別

    所有指令處理器都應該繼承此類別並實作 can_handle 和 handle 方法
    """

    @abstractmethod
    def can_handle(self, text: str) -> bool:
        """
        判斷是否能處理此指令

        Args:
            text: 訊息文字內容

        Returns:
            bool: True 如果此處理器可以處理這個指令

        Example:
            def can_handle(self, text: str) -> bool:
                return text.startswith('/debug')
        """
        pass

    @abstractmethod
    def handle(self, update: Update, event: dict) -> bool:
        """
        處理指令

        Args:
            update: Telegram Update 物件
            event: API Gateway event（完整的請求資料）

        Returns:
            bool: True 如果成功處理，False 如果處理失敗

        Note:
            如果使用了權限 decorator (@require_admin 或 @require_allowlist)，
            此方法只會在權限檢查通過後才被呼叫。
            權限檢查失敗時會自動發送權限不足訊息並返回 False。
        """
        pass

    def get_command_name(self) -> str:
        """
        取得指令名稱（用於日誌和錯誤訊息）

        Returns:
            str: 指令處理器的類別名稱

        Note:
            子類別可以覆寫此方法以提供更友善的名稱
        """
        return self.__class__.__name__

    def get_description(self) -> str:
        """
        取得指令描述（可選）

        Returns:
            str: 指令的描述文字

        Note:
            子類別可以覆寫此方法以提供指令說明，
            用於自動生成 help 訊息等用途
        """
        return ""
