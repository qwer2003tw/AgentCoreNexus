# 指令系統架構

## 📋 概述

telegram-adapter 實作了模組化的指令處理系統，使用 Command Handler Pattern 和 Python Decorators 來管理 Telegram 指令。

## 🏗️ 架構設計

### 核心組件

```
┌─────────────────────────────────────────────────────┐
│                  handler.py                         │
│  ┌───────────────────────────────────────────────┐  │
│  │  Lambda Handler                               │  │
│  │  - 接收 Telegram webhook                      │  │
│  │  - 驗證 Secret Token                          │  │
│  └────────────┬──────────────────────────────────┘  │
│               │                                      │
│               ▼                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │  Command Router                               │  │
│  │  - 路由指令到對應的處理器                      │  │
│  │  - 在 allowlist 檢查之前執行                  │  │
│  └────────────┬──────────────────────────────────┘  │
│               │                                      │
│               ▼                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │  Command Handlers                             │  │
│  │  - DebugCommandHandler                        │  │
│  │  - (未來可新增更多處理器)                      │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 目錄結構

```
src/
├── handler.py                      # Lambda 入口
├── commands/
│   ├── __init__.py
│   ├── base.py                     # CommandHandler 抽象基類
│   ├── router.py                   # CommandRouter 路由器
│   ├── decorators.py               # 權限裝飾器（預留）
│   └── handlers/
│       ├── __init__.py
│       └── debug_handler.py        # Debug 指令處理器
└── auth/                           # 權限系統（預留）
    ├── __init__.py
    ├── permissions.py              # 權限枚舉
    └── admin_list.py               # Admin 管理（預留）
```

## 📝 核心類別

### CommandHandler（抽象基類）

所有指令處理器的基類，定義了標準介面。

```python
from abc import ABC, abstractmethod
from telegram import Update

class CommandHandler(ABC):
    """指令處理器抽象基類"""
    
    @abstractmethod
    def can_handle(self, text: str) -> bool:
        """判斷是否能處理此指令"""
        pass
    
    @abstractmethod
    def handle(self, update: Update, event: dict) -> bool:
        """處理指令"""
        pass
    
    @abstractmethod
    def get_command_name(self) -> str:
        """取得指令名稱"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """取得指令描述"""
        pass
```

### CommandRouter（路由器）

負責管理和分發指令到對應的處理器。

```python
class CommandRouter:
    """指令路由器"""
    
    def __init__(self):
        self._handlers: List[CommandHandler] = []
    
    def register(self, handler: CommandHandler) -> None:
        """註冊指令處理器"""
        self._handlers.append(handler)
    
    def route(self, update: Update, event: dict) -> Optional[bool]:
        """路由訊息到對應的處理器"""
        message = update.effective_message
        if not message:
            return None
        
        text = message.text or message.caption or ''
        
        # 嘗試所有處理器
        for handler in self._handlers:
            if handler.can_handle(text):
                try:
                    return handler.handle(update, event)
                except Exception as e:
                    logger.warning(f"Handler failed: {e}")
                    return False
        
        return None  # 沒有處理器可處理此指令
```

## 🔨 實作新的指令處理器

### 步驟 1：創建處理器類別

在 `src/commands/handlers/` 目錄下創建新的處理器：

```python
# src/commands/handlers/my_command_handler.py
from telegram import Update
from commands.base import CommandHandler
from utils.logger import get_logger

logger = get_logger(__name__)

class MyCommandHandler(CommandHandler):
    """我的自訂指令處理器"""
    
    def can_handle(self, text: str) -> bool:
        """判斷是否為 /mycommand 指令"""
        if not text:
            return False
        stripped = text.strip()
        return stripped == '/mycommand' or stripped.startswith('/mycommand ')
    
    def handle(self, update: Update, event: dict) -> bool:
        """處理 /mycommand 指令"""
        message = update.effective_message
        if not message:
            return False
        
        chat_id = message.chat_id
        
        # 實作你的指令邏輯
        logger.info(f"Processing my command for chat_id: {chat_id}")
        
        # 返回 True 表示成功處理，False 表示失敗
        return True
    
    def get_command_name(self) -> str:
        return "MyCommand"
    
    def get_description(self) -> str:
        return "我的自訂指令"
```

### 步驟 2：註冊處理器

在 `src/handler.py` 的 `get_command_router()` 函數中註冊新的處理器：

```python
from commands.handlers.debug_handler import DebugCommandHandler
from commands.handlers.my_command_handler import MyCommandHandler

def get_command_router() -> CommandRouter:
    global _command_router
    if _command_router is None:
        _command_router = CommandRouter()
        # 註冊所有指令處理器
        _command_router.register(DebugCommandHandler())
        _command_router.register(MyCommandHandler())  # 新增這行
        logger.info("Command router initialized with handlers")
    return _command_router
```

### 步驟 3：撰寫測試

在 `tests/` 目錄下為新的處理器撰寫測試：

```python
# tests/test_my_command_handler.py
import pytest
from telegram import Update, Message, Chat, User
from commands.handlers.my_command_handler import MyCommandHandler

class TestMyCommandHandler:
    def test_can_handle_valid_command(self):
        handler = MyCommandHandler()
        assert handler.can_handle('/mycommand')
        assert handler.can_handle('/mycommand test')
    
    def test_can_handle_invalid_command(self):
        handler = MyCommandHandler()
        assert not handler.can_handle('/other')
        assert not handler.can_handle('')
```

## 🔒 權限系統（預留）

專案已預留權限系統架構，未來可實作：

### 權限裝飾器

```python
# src/commands/decorators.py
from functools import wraps
from commands.base import CommandHandler

def require_admin(handler_class):
    """要求 admin 權限的裝飾器（預留）"""
    original_handle = handler_class.handle
    
    @wraps(original_handle)
    def wrapper(self, update, event):
        # 未來實作：檢查用戶是否為 admin
        # if not is_admin(update.effective_user.id):
        #     return False
        return original_handle(self, update, event)
    
    handler_class.handle = wrapper
    return handler_class

def require_allowlist(handler_class):
    """要求 allowlist 權限的裝飾器（預留）"""
    # 類似實作
    pass
```

### 使用裝飾器

```python
@require_admin
class AdminCommandHandler(CommandHandler):
    """需要 admin 權限的指令"""
    # ...
```

## 📊 指令執行流程

```
1. Telegram webhook → API Gateway → Lambda Handler
                                        ↓
2. 驗證 Secret Token
                                        ↓
3. 解析 Telegram Update 物件
                                        ↓
4. Command Router 嘗試路由指令
   ├─ 成功路由 → 指令處理器執行 → 返回 200 OK
   └─ 無法路由 → 繼續正常流程
                                        ↓
5. 檢查 Allowlist
                                        ↓
6. 發送到 SQS
                                        ↓
7. 返回 200 OK
```

## 🎯 設計原則

### 1. 單一職責原則（SRP）
每個處理器只負責一個指令的處理邏輯。

### 2. 開放封閉原則（OCP）
- 開放：可以輕鬆新增新的指令處理器
- 封閉：不需要修改現有的核心程式碼

### 3. 依賴反轉原則（DIP）
- 高層模組（Router）依賴抽象（CommandHandler）
- 低層模組（具體處理器）實作抽象介面

### 4. 介面隔離原則（ISP）
CommandHandler 介面簡潔明確，只包含必要的方法。

## 🔍 現有指令

### /debug 指令

處理器：`DebugCommandHandler`  
權限：無需權限（全部開放）  
功能：發送當前請求的除錯資訊

詳細說明請參閱：[DEBUG_COMMAND.md](DEBUG_COMMAND.md)

### /info 指令

處理器：`InfoCommandHandler`  
權限：無需權限（全部開放）  
功能：顯示系統部署資訊，包括最後部署時間、Stack 名稱、Region、Stack 狀態和 Lambda 函數名稱

**使用方式：**
```
/info
```

**回應範例：**
```
📊 系統資訊

🚀 最後部署時間：2025-01-05 11:00:23 UTC
📦 Stack 名稱：telegram-adapter
🌍 Region：us-west-2
✅ Stack 狀態：UPDATE_COMPLETE
⚙️ Lambda 函數：telegram-adapter-receiver
```

**技術實作：**
- 使用 boto3 CloudFormation client 查詢 Stack 資訊
- 從 `STACK_NAME` 和 `AWS_REGION` 環境變數取得配置
- 需要 `cloudformation:DescribeStacks` IAM 權限
- 自動處理各種錯誤情況（權限不足、找不到 Stack、API 錯誤等）

**錯誤處理：**
- 權限不足：顯示「權限不足，無法查詢部署資訊」
- 找不到 Stack：顯示「找不到 Stack: {stack_name}」
- API 錯誤：顯示具體的錯誤代碼

## 🚀 最佳實踐

### 1. 錯誤處理
指令處理器應該妥善處理錯誤，並返回適當的布林值：
- `True`：成功處理
- `False`：處理失敗
- `None`：無法處理此指令

### 2. 日誌記錄
使用結構化日誌記錄重要事件：

```python
logger.info(
    "Command processed",
    extra={
        'chat_id': chat_id,
        'command': command_text,
        'event_type': 'command_success'
    }
)
```

### 3. 單元測試
每個處理器都應該有完整的單元測試，測試：
- `can_handle()` 的各種輸入
- `handle()` 的成功和失敗情況
- 邊界條件和錯誤處理

### 4. 性能考量
- 指令檢查應該快速（< 10ms）
- 使用 `startswith()` 而非正則表達式進行簡單匹配
- 避免在 `can_handle()` 中執行耗時操作

## 📈 未來擴展

### 計畫中的功能

1. **權限系統**
   - Admin 權限管理
   - 基於 DynamoDB 的角色儲存
   - 權限裝飾器實作

2. **更多指令**
   - `/help` - 顯示可用指令列表
   - `/status` - 顯示系統狀態
   - `/admin` - 管理功能（需要 admin 權限）

3. **指令參數解析**
   - 標準化的參數解析機制
   - 參數驗證

4. **指令別名**
   - 支援指令別名（如 `/d` 作為 `/debug` 的別名）

5. **動態指令註冊**
   - 從設定檔載入指令處理器
   - 執行時期動態註冊/註銷處理器

## 🔗 相關文件

- [DEBUG_COMMAND.md](DEBUG_COMMAND.md) - Debug 指令詳細說明
- [DEPLOYMENT_GUIDE.md](../deployment/DEPLOYMENT_GUIDE.md) - 部署指南
- [README.md](../../README.md) - 專案概述
