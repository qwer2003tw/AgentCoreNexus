"""
Telegram Update Factory
使用 aiogram 生成標準的 Telegram Update 對象供測試使用
"""

import json
from datetime import datetime

from aiogram.types import Chat, Message, Update, User


class TelegramUpdateFactory:
    """使用 aiogram 創建標準 Telegram Update 的工廠類"""

    @staticmethod
    def create_message_update(
        text: str,
        user_id: int = 316743844,
        username: str = "qwer2003tw",
        chat_id: int | None = None,
        first_name: str = "Test",
        last_name: str = "User",
        message_id: int = 1,
    ) -> dict:
        """
        創建文字訊息 Update（Lambda event 格式）

        Args:
            text: 訊息文字
            user_id: 用戶 ID
            username: 用戶名
            chat_id: 聊天 ID（預設與 user_id 相同）
            first_name: 名字
            last_name: 姓氏
            message_id: 訊息 ID

        Returns:
            Lambda event 格式的字典
        """
        chat_id = chat_id or user_id

        # 使用 aiogram 創建標準對象
        user = User(
            id=user_id,
            is_bot=False,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )

        chat = Chat(id=chat_id, type="private", username=username, first_name=first_name)

        message = Message(
            message_id=message_id,
            date=datetime.now(),
            chat=chat,
            from_user=user,
            text=text,
        )

        update = Update(update_id=1, message=message)

        # 轉換為 Lambda event 格式
        return {
            "body": update.model_dump_json(),
            "headers": {"X-Telegram-Bot-Api-Secret-Token": "test_secret"},
            "requestContext": {"requestId": "test-request-id"},
            "isBase64Encoded": False,
        }

    @staticmethod
    def create_command_update(command: str, **kwargs) -> dict:
        """
        創建命令 Update

        Args:
            command: 命令名稱（不含 /）
            **kwargs: 傳遞給 create_message_update 的其他參數

        Returns:
            Lambda event 格式的字典
        """
        return TelegramUpdateFactory.create_message_update(text=f"/{command}", **kwargs)

    @staticmethod
    def create_photo_update(
        caption: str = "",
        file_id: str = "test_photo_id",
        user_id: int = 316743844,
        username: str = "qwer2003tw",
    ) -> dict:
        """
        創建圖片訊息 Update

        Args:
            caption: 圖片說明
            file_id: 檔案 ID
            user_id: 用戶 ID
            username: 用戶名

        Returns:
            Lambda event 格式的字典
        """
        # 手動構建包含圖片的 Update（aiogram 沒有簡單的方法生成）
        body = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": username,
                },
                "chat": {"id": user_id, "type": "private", "username": username},
                "date": int(datetime.now().timestamp()),
                "photo": [
                    {
                        "file_id": file_id,
                        "file_unique_id": "test_unique_id",
                        "file_size": 1024,
                        "width": 800,
                        "height": 600,
                    }
                ],
                "caption": caption,
            },
        }

        return {
            "body": json.dumps(body),
            "headers": {"X-Telegram-Bot-Api-Secret-Token": "test_secret"},
            "requestContext": {"requestId": "test-request-id"},
            "isBase64Encoded": False,
        }

    @staticmethod
    def create_document_update(
        filename: str = "test.pdf",
        file_id: str = "test_doc_id",
        mime_type: str = "application/pdf",
        user_id: int = 316743844,
        username: str = "qwer2003tw",
    ) -> dict:
        """
        創建文件訊息 Update

        Args:
            filename: 檔案名稱
            file_id: 檔案 ID
            mime_type: MIME 類型
            user_id: 用戶 ID
            username: 用戶名

        Returns:
            Lambda event 格式的字典
        """
        body = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": username,
                },
                "chat": {"id": user_id, "type": "private", "username": username},
                "date": int(datetime.now().timestamp()),
                "document": {
                    "file_id": file_id,
                    "file_unique_id": "test_unique_id",
                    "file_name": filename,
                    "mime_type": mime_type,
                    "file_size": 2048,
                },
            },
        }

        return {
            "body": json.dumps(body),
            "headers": {"X-Telegram-Bot-Api-Secret-Token": "test_secret"},
            "requestContext": {"requestId": "test-request-id"},
            "isBase64Encoded": False,
        }
