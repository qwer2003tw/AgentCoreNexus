"""
Tests for Command Router - 指令路由器測試
"""

from unittest.mock import Mock

import pytest
from commands.base import CommandHandler
from commands.router import CommandRouter
from telegram import Chat, Message, Update, User


class MockCommandHandler(CommandHandler):
    """測試用的 Mock 指令處理器"""

    def __init__(self, command: str, should_succeed: bool = True):
        self.command = command
        self.should_succeed = should_succeed
        self.handle_called = False

    def can_handle(self, text: str) -> bool:
        return text.startswith(self.command)

    def handle(self, update: Update, event: dict) -> bool:
        self.handle_called = True
        return self.should_succeed

    def get_command_name(self) -> str:
        return f"MockHandler({self.command})"


class TestCommandRouter:
    """CommandRouter 測試類別"""

    @pytest.fixture
    def router(self):
        """創建路由器實例"""
        return CommandRouter()

    @pytest.fixture
    def mock_update(self):
        """創建 Mock Update 物件"""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        user = Mock(spec=User)
        chat = Mock(spec=Chat)

        user.username = "testuser"
        chat.id = 12345
        message.text = "/test"
        message.from_user = user
        message.chat = chat
        message.chat_id = 12345

        update.message = message
        update.edited_message = None

        return update

    @pytest.fixture
    def mock_event(self):
        """創建 Mock event 字典"""
        return {"body": "test"}

    def test_register_handler(self, router):
        """測試註冊處理器"""
        handler = MockCommandHandler("/test")
        router.register(handler)

        handlers = router.get_registered_handlers()
        assert len(handlers) == 1
        assert handlers[0] == handler

    def test_register_multiple_handlers(self, router):
        """測試註冊多個處理器"""
        handler1 = MockCommandHandler("/test1")
        handler2 = MockCommandHandler("/test2")

        router.register(handler1)
        router.register(handler2)

        handlers = router.get_registered_handlers()
        assert len(handlers) == 2
        assert handlers[0] == handler1
        assert handlers[1] == handler2

    def test_register_non_handler_raises_error(self, router):
        """測試註冊非 CommandHandler 實例會拋出錯誤"""
        with pytest.raises(TypeError) as exc_info:
            router.register("not a handler")

        assert "must be an instance of CommandHandler" in str(exc_info.value)

    def test_route_to_matching_handler(self, router, mock_update, mock_event):
        """測試路由到匹配的處理器"""
        handler = MockCommandHandler("/test")
        router.register(handler)

        result = router.route(mock_update, mock_event)

        assert result is True
        assert handler.handle_called is True

    def test_route_to_first_matching_handler(self, router, mock_update, mock_event):
        """測試路由到第一個匹配的處理器"""
        handler1 = MockCommandHandler("/test")
        handler2 = MockCommandHandler("/test")  # 同樣匹配

        router.register(handler1)
        router.register(handler2)

        result = router.route(mock_update, mock_event)

        assert result is True
        assert handler1.handle_called is True
        assert handler2.handle_called is False  # 第二個不應該被呼叫

    def test_route_no_matching_handler(self, router, mock_update, mock_event):
        """測試沒有匹配的處理器"""
        handler = MockCommandHandler("/other")
        router.register(handler)

        result = router.route(mock_update, mock_event)

        assert result is False
        assert handler.handle_called is False

    def test_route_handler_returns_false(self, router, mock_update, mock_event):
        """測試處理器返回 False"""
        handler = MockCommandHandler("/test", should_succeed=False)
        router.register(handler)

        result = router.route(mock_update, mock_event)

        assert result is False
        assert handler.handle_called is True

    def test_route_no_text_message(self, router, mock_event):
        """測試沒有文字訊息"""
        update = Mock(spec=Update)
        update.message = None
        update.edited_message = None

        handler = MockCommandHandler("/test")
        router.register(handler)

        result = router.route(update, mock_event)

        assert result is False
        assert handler.handle_called is False

    def test_route_edited_message(self, router, mock_event):
        """測試處理編輯過的訊息"""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        user = Mock(spec=User)
        chat = Mock(spec=Chat)

        user.username = "testuser"
        chat.id = 12345
        message.text = "/test"
        message.from_user = user
        message.chat = chat
        message.chat_id = 12345

        update.message = None
        update.edited_message = message

        handler = MockCommandHandler("/test")
        router.register(handler)

        result = router.route(update, mock_event)

        assert result is True
        assert handler.handle_called is True

    def test_route_handler_raises_exception(self, router, mock_update, mock_event):
        """測試處理器拋出例外時繼續嘗試下一個"""
        handler1 = MockCommandHandler("/test")
        handler2 = MockCommandHandler("/test")

        # 讓第一個處理器拋出例外
        def raise_error(update, event):
            raise Exception("Test error")

        handler1.handle = raise_error

        router.register(handler1)
        router.register(handler2)

        result = router.route(mock_update, mock_event)

        # 應該跳過失敗的處理器，嘗試下一個
        assert result is True
        assert handler2.handle_called is True

    def test_clear_handlers(self, router):
        """測試清除所有處理器"""
        handler1 = MockCommandHandler("/test1")
        handler2 = MockCommandHandler("/test2")

        router.register(handler1)
        router.register(handler2)

        assert len(router.get_registered_handlers()) == 2

        router.clear()

        assert len(router.get_registered_handlers()) == 0

    def test_get_registered_handlers_returns_copy(self, router):
        """測試取得處理器列表返回副本"""
        handler = MockCommandHandler("/test")
        router.register(handler)

        handlers1 = router.get_registered_handlers()
        handlers2 = router.get_registered_handlers()

        # 應該是不同的列表實例
        assert handlers1 is not handlers2
        # 但內容相同
        assert handlers1 == handlers2
