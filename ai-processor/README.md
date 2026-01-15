# Telegram AgentCore Bot

基於 AWS Bedrock AgentCore 的 Telegram 機器人，採用模組化架構設計。

## 🏗️ 專案架構

```
telegram-agentcore-bot/
├── config/                 # 配置模組
│   ├── __init__.py        # 導出 settings 和 SYSTEM_PROMPT
│   ├── settings.py        # 環境變數管理
│   └── prompts.py         # 系統提示詞管理
├── utils/                  # 工具模組
│   ├── __init__.py        # 導出 get_logger
│   └── logger.py          # 日誌配置
├── tools/                  # Agent 工具
│   ├── __init__.py        # 導出所有工具和 AVAILABLE_TOOLS
│   ├── weather.py         # 天氣查詢工具
│   ├── calculator.py      # 計算器工具
│   ├── user_info.py       # 用戶資訊工具
│   ├── time_utils.py      # 時間工具
│   └── browser.py         # 網頁瀏覽工具
├── services/               # 服務層
│   ├── __init__.py        # 導出 MemoryService 和 BrowserService
│   ├── memory_service.py  # Memory 服務管理
│   └── browser_service.py # 瀏覽器服務管理
├── agents/                 # Agent 層
│   ├── __init__.py        # 導出 ConversationAgent
│   └── conversation_agent.py  # 對話 Agent 實作
├── telegram_agent.py       # 主入口點（僅負責 AgentCore 整合）
├── requirements.txt        # Python 依賴
└── .env.example           # 環境變數範例
```

## 🎯 設計原則

### 1. 單一入口點
- `telegram_agent.py` 僅負責 AgentCore 整合
- 所有業務邏輯都在模組中實作

### 2. 模組化設計
- **config**: 集中管理配置和提示詞
- **utils**: 共用工具函數（日誌等）
- **tools**: Agent 可用的所有工具
- **services**: 業務服務層（Memory、Browser）
- **agents**: Agent 實作層

### 3. 環境變數驅動
- 所有配置都透過環境變數設定
- 無硬編碼值
- 提供 `.env.example` 作為範本

### 4. 完整錯誤處理
- 每個模組都有適當的錯誤處理
- 統一的日誌記錄
- 友善的錯誤訊息

### 5. 相對導入
- 所有模組使用相對導入
- 清晰的依賴關係

## 🚀 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

複製 `.env.example` 為 `.env` 並填入實際值：

```bash
cp .env.example .env
```

必要的環境變數：
- `AWS_REGION`: AWS 區域（預設: us-west-2）
- `BEDROCK_MODEL_ID`: Bedrock 模型 ID

可選的環境變數：
- `BEDROCK_AGENTCORE_MEMORY_ID`: 啟用 Memory 功能
- `LOG_LEVEL`: 日誌等級（預設: INFO）
- `BROWSER_ENABLED`: 啟用瀏覽器功能（預設: true）
- `AGENT_SYSTEM_PROMPT`: 自定義系統提示詞

### 3. 配置 Bedrock AgentCore

⚠️ **重要**: `.bedrock_agentcore.yaml` 包含敏感的 AWS 帳號資訊，**請勿提交到版本控制**。

複製 `.bedrock_agentcore.yaml.example` 為 `.bedrock_agentcore.yaml` 並填入實際值：

```bash
cp .bedrock_agentcore.yaml.example .bedrock_agentcore.yaml
```

需要設定的項目：
- `<YOUR_ACCOUNT_ID>`: 您的 AWS 帳號 ID
- `<YOUR_ROLE_NAME>`: IAM 執行角色名稱
- `<YOUR_AGENT_ID>`: Bedrock AgentCore Agent ID
- `<YOUR_SESSION_ID>`: Agent Session ID
- `<YOUR_CODEBUILD_ROLE_NAME>`: CodeBuild 執行角色名稱
- `/path/to/your/telegram_agent.py`: 實際的專案路徑
- `/path/to/your/project`: 實際的專案根目錄路徑

**安全提醒**：
- `.bedrock_agentcore.yaml` 已被 `.gitignore` 忽略
- 請勿將此檔案提交到 Git 儲存庫
- 如果不小心提交了，請使用 `git rm --cached .bedrock_agentcore.yaml` 移除

### 4. 執行

```bash
python telegram_agent.py
```

## 📦 模組說明

### Config 模組

**settings.py**
- `Settings` 類別管理所有環境變數
- 提供配置驗證和摘要功能
- 全域 `settings` 實例供其他模組使用

**prompts.py**
- 集中管理系統提示詞
- 錯誤訊息模板
- 提供輔助函數取得格式化訊息

### Utils 模組

**logger.py**
- `get_logger()` 函數提供統一的日誌配置
- 支援彩色輸出（開發環境）
- 統一的日誌格式

### Tools 模組

每個工具都使用 `@tool` 裝飾器：
- `get_weather`: 天氣查詢
- `calculate`: 數學計算（安全版）
- `get_user_info`: 用戶資訊
- `get_current_time`: 取得當前時間
- `browse_website_official`: 官方瀏覽器工具
- `browse_website_backup`: 備用瀏覽器工具

`AVAILABLE_TOOLS` 列表包含所有可用工具。

### Services 模組

**memory_service.py**
- `MemoryService` 類別管理 AgentCore Memory
- `get_session_manager()` 取得 Session Manager
- 自動處理 Memory 啟用/停用邏輯

**browser_service.py**
- `BrowserService` 類別封裝瀏覽器操作
- 提供統一的瀏覽器介面
- 處理瀏覽器初始化和錯誤

### Agents 模組

**conversation_agent.py**
- `ConversationAgent` 類別封裝對話邏輯
- `process_message()` 處理用戶訊息
- 自動提取和格式化回應
- 完整的錯誤處理

## 🧪 測試

專案包含完整的單元測試套件，使用 Python 的 `unittest` 框架。

### 測試結構

```
tests/
├── __init__.py           # 測試套件初始化
├── test_config.py        # Config 模組測試
├── test_tools.py         # Tools 模組測試
├── test_services.py      # Services 模組測試
└── test_agents.py        # Agents 模組測試
```

### 執行測試

#### 執行所有測試

```bash
python run_tests.py
```

#### 執行特定模組的測試

```bash
# 測試 config 模組
python run_tests.py -m test_config

# 測試 tools 模組
python run_tests.py -m test_tools

# 測試 services 模組
python run_tests.py -m test_services

# 測試 agents 模組
python run_tests.py -m test_agents
```

#### 調整輸出詳細程度

```bash
# 詳細模式（預設）
python run_tests.py -v 2

# 正常模式
python run_tests.py -v 1

# 安靜模式
python run_tests.py -q
```

#### 使用 unittest 直接執行

```bash
# 執行所有測試
python -m unittest discover tests

# 執行特定測試檔案
python -m unittest tests.test_config

# 執行特定測試類別
python -m unittest tests.test_config.TestSettings

# 執行特定測試方法
python -m unittest tests.test_config.TestSettings.test_init_with_defaults
```

### 測試覆蓋範圍

**test_config.py** (13 個測試)
- `TestSettings`: 9 個測試
  - 初始化與預設值
  - 環境變數載入
  - Memory 配置
  - 環境檢測
  - 配置摘要
- `TestPrompts`: 4 個測試
  - 系統提示詞
  - 錯誤訊息
  - 輔助函數

**test_tools.py** (19 個測試)
- `TestWeatherTool`: 4 個測試
- `TestCalculatorTool`: 8 個測試（包含安全性測試）
- `TestUserInfoTool`: 3 個測試
- `TestTimeUtilsTool`: 2 個測試
- `TestToolsModule`: 2 個測試（導入驗證）

**test_services.py** (19 個測試)
- `TestMemoryService`: 8 個測試
  - 初始化
  - Session manager 建立
  - 狀態檢查
  - Actor ID 提取
- `TestBrowserService`: 8 個測試
  - 初始化
  - 可用性檢查
  - URL 提取
  - Session 名稱生成
- `TestServicesModule`: 3 個測試（導入驗證）

**test_agents.py** (18 個測試)
- `TestConversationAgent`: 16 個測試
  - Agent 初始化
  - 訊息處理
  - 回應提取（多種格式）
  - 錯誤處理
- `TestAgentsModule`: 2 個測試（導入驗證）

**總計**: 69 個單元測試

### 測試特點

1. **使用 Mock 物件**
   - 所有外部依賴都使用 mock
   - 測試不依賴真實的 AWS 服務
   - 測試執行快速且可靠

2. **全面的覆蓋**
   - 測試正常流程
   - 測試錯誤處理
   - 測試邊界條件
   - 測試各種輸入格式

3. **清晰的測試結構**
   - 每個模組對應一個測試檔案
   - 測試方法命名清楚
   - 包含詳細的註解

4. **獨立性**
   - 每個測試都是獨立的
   - 不依賴測試執行順序
   - 使用 setUp/tearDown 管理測試狀態

### 編寫新測試

當添加新功能時，應該同時編寫對應的測試：

```python
# tests/test_my_module.py
import unittest
from unittest.mock import Mock, patch
from my_module import MyClass

class TestMyClass(unittest.TestCase):
    """測試 MyClass 類別"""
    
    def setUp(self):
        """測試前準備"""
        self.instance = MyClass()
    
    def test_my_method(self):
        """測試 my_method 方法"""
        result = self.instance.my_method("input")
        self.assertEqual(result, "expected_output")
    
    def test_error_handling(self):
        """測試錯誤處理"""
        with self.assertRaises(ValueError):
            self.instance.my_method(None)

if __name__ == '__main__':
    unittest.main()
```

### CI/CD 整合

可以在 CI/CD 管道中執行測試：

```bash
# 在 GitHub Actions, GitLab CI 等中
python run_tests.py
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Tests failed!"
    exit 1
fi
```

## 🔧 擴展指南

### 新增工具

1. 在 `tools/` 目錄建立新檔案
2. 使用 `@tool` 裝飾器定義工具函數
3. 在 `tools/__init__.py` 中導出新工具
4. 新工具會自動加入 `AVAILABLE_TOOLS`

範例：

```python
# tools/new_tool.py
from strands import tool
from utils.logger import get_logger

logger = get_logger(__name__)

@tool
def my_new_tool(param: str) -> str:
    """工具說明"""
    try:
        # 實作邏輯
        result = f"處理結果: {param}"
        logger.info(f"✅ 工具執行成功")
        return result
    except Exception as e:
        logger.error(f"❌ 工具執行失敗: {e}")
        return f"錯誤: {str(e)}"
```

```python
# tools/__init__.py
from .new_tool import my_new_tool

__all__ = [
    # ... 其他工具
    'my_new_tool'
]

AVAILABLE_TOOLS = [
    # ... 其他工具
    my_new_tool
]
```

### 新增服務

1. 在 `services/` 目錄建立新檔案
2. 建立服務類別
3. 在 `services/__init__.py` 中導出
4. 在需要的地方導入使用

### 修改系統提示詞

有兩種方式：

1. **環境變數**（推薦）：
   ```bash
   export AGENT_SYSTEM_PROMPT="你的提示詞"
   ```

2. **修改 config/prompts.py**：
   直接編輯 `SYSTEM_PROMPT` 的預設值

## 📊 日誌

所有模組都使用統一的日誌系統：

```python
from utils.logger import get_logger

logger = get_logger(__name__)
logger.info("資訊訊息")
logger.warning("警告訊息")
logger.error("錯誤訊息")
```

日誌等級可透過環境變數 `LOG_LEVEL` 設定。

## 🔒 安全考量

1. **環境變數**: 所有敏感資訊都透過環境變數管理
2. **安全計算**: calculator 工具使用白名單驗證
3. **錯誤處理**: 完整的異常捕獲和日誌記錄
4. **輸入驗證**: 所有工具都進行輸入驗證

## 🧪 測試

專案包含多個測試檔案：
- `test_browser.py`: 瀏覽器功能測試
- `test_backup_tool.py`: 備用工具測試
- `test_response_fix.py`: 回應處理測試
- `test_playwright_integration.py`: Playwright 整合測試

## 📝 授權

本專案採用 MIT 授權。

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📮 聯絡方式

如有問題或建議，請開啟 Issue。
