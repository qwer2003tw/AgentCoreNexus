"""
E2E 測試 Bot 客戶端
封裝 Telegram Bot 操作，用於自動化測試
"""

import asyncio
import time
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile, Message


class E2EBotClient:
    """E2E 測試的 Bot 客戶端封裝"""

    def __init__(self, bot_token: str, test_chat_id: int):
        """
        初始化 Bot 客戶端

        Args:
            bot_token: Telegram Bot Token
            test_chat_id: 測試用的 chat ID（你的 Telegram ID）
        """
        self.bot = Bot(token=bot_token)
        self.chat_id = test_chat_id
        self.last_update_id = None
        self.sent_message_ids = []

    async def send_text(self, text: str) -> Message:
        """
        發送文字訊息

        Args:
            text: 訊息文字

        Returns:
            發送的 Message 對象
        """
        msg = await self.bot.send_message(self.chat_id, text)
        self.sent_message_ids.append(msg.message_id)
        return msg

    async def send_photo(self, photo_path: str | Path, caption: str = "") -> Message:
        """
        上傳圖片

        Args:
            photo_path: 圖片檔案路徑
            caption: 圖片說明

        Returns:
            發送的 Message 對象
        """
        photo = FSInputFile(photo_path)
        msg = await self.bot.send_photo(
            self.chat_id,
            photo=photo,
            caption=caption if caption else None,
        )
        self.sent_message_ids.append(msg.message_id)
        return msg

    async def send_document(self, doc_path: str | Path, caption: str = "") -> Message:
        """
        上傳檔案

        Args:
            doc_path: 檔案路徑
            caption: 檔案說明

        Returns:
            發送的 Message 對象
        """
        document = FSInputFile(doc_path)
        msg = await self.bot.send_document(
            self.chat_id,
            document=document,
            caption=caption if caption else None,
        )
        self.sent_message_ids.append(msg.message_id)
        return msg

    async def wait_for_reply(
        self, timeout: int = 30, poll_interval: int = 2, min_length: int = 5
    ) -> str | None:
        """
        等待 Bot 回應

        Args:
            timeout: 最長等待時間（秒）
            poll_interval: 輪詢間隔（秒）
            min_length: 最小回應長度（過濾過短的回應）

        Returns:
            Bot 回應的文字，或 None（超時）
        """
        start_time = time.time()
        last_message_id = max(self.sent_message_ids) if self.sent_message_ids else 0

        while time.time() - start_time < timeout:
            # 獲取更新
            updates = await self.bot.get_updates(
                offset=self.last_update_id + 1 if self.last_update_id else None,
                timeout=poll_interval,
            )

            for update in updates:
                self.last_update_id = update.update_id

                # 檢查是否是這個 chat 的訊息
                if update.message and update.message.chat.id == self.chat_id:
                    # 檢查是否是 bot 的回應（message_id 大於我們發送的）
                    if update.message.message_id > last_message_id:
                        # 檢查是否有文字
                        if update.message.text:
                            text = update.message.text.strip()
                            if len(text) >= min_length:
                                return text

            await asyncio.sleep(poll_interval)

        return None

    async def clear_session(self):
        """清除 Memory session（發送 /clearsession 命令）"""
        await self.send_text("/clearsession")
        # 等待處理完成
        await asyncio.sleep(3)

    async def close(self):
        """關閉 Bot session"""
        await self.bot.session.close()
