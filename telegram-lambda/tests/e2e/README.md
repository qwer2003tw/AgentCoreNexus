# 端對端測試指南

本目錄包含 Telegram Bot 的端對端（E2E）測試，使用 **aiogram** 生成標準的 Telegram Update 物件。

## 🎯 測試目的

- **本地開發測試**：在不部署到 AWS 的情況下測試完整流程
- **部署前驗證**：確保代碼變更不會破壞現有功能
- **快速反饋**：幾秒內完成所有測試，支持快速迭代

## 📦 安裝依賴

```bash
cd telegram-lambda
pip install -r requirements-test.txt
```

## 🚀 運行測試

### 運行所有 E2E 測試
```bash
pytest tests/e2e/ -v
```

### 運行特定測試文件
```bash
# 測試命令處理
pytest tests/e2e/test_commands.py -v

# 測試訊息流程
pytest tests/e2e/test_message_flow.py -v
```

### 運行特定測試
```bash
pytest tests/e2e/test_commands.py::TestCommands::test_info_command_success -v
```

### 帶覆蓋率報告
```bash
pytest tests/e2e/ --cov=src --cov-report=html
# 報告生成在 htmlcov/index.html
```

### 排除慢速測試
```bash
pytest tests/e2e/ -m "not slow" -v
```

## 📂 測試結構

```
tests/e2e/
├── README.md                  # 本文件
├── conftest.py                # Fixtures 和測試設置
├── test_commands.py           # 命令處理測試
├── test_message_flow.py       # 訊息流程測試
└── helpers/
    ├── telegram_factory.py    # Telegram Update 生成器
    └── aws_mocks.py           # AWS 服務 Mock
```

## 🛠️ 核心組件

### TelegramUpdateFactory

使用 aiogram 生成標準的 Telegram Update 對象：

```python
from tests.e2e.helpers.telegram_factory import TelegramUpdateFactory

# 創建文字訊息
event = TelegramUpdateFactory.create_message_update("你好")

# 創建命令
event = TelegramUpdateFactory.create_command_update("info")

# 創建圖片訊息
event = TelegramUpdateFactory.create_photo_update(caption="測試圖片")
```

### Mock 服務

所有 AWS 服務都被 mock，無需實際的 AWS 資源：

- **MockEventBridge**：記錄發送的事件
- **MockTelegramAPI**：記錄發送的訊息
- **MockDynamoDB**：模擬 allowlist
- **MockSecretsManager**：提供測試 secrets

## 📝 撰寫新測試

### 基本測試範例

```python
import pytest
from handler import lambda_handler
from tests.e2e.helpers.telegram_factory import TelegramUpdateFactory

@pytest.mark.e2e
def test_my_feature(full_mock_env, lambda_context):
    """測試我的新功能"""
    # Arrange
    event = TelegramUpdateFactory.create_message_update("測試訊息")
    telegram_api = full_mock_env["telegram_api"]
    
    # Act
    response = lambda_handler(event, lambda_context)
    
    # Assert
    assert response["statusCode"] == 200
    
    # 驗證發送的訊息
    sent_messages = telegram_api.get_sent_messages()
    assert len(sent_messages) > 0
```

### 使用 Fixtures

可用的 fixtures：

- `full_mock_env`：完整的測試環境（推薦）
- `mock_env`：環境變數
- `mock_secrets`：Secrets Manager
- `mock_eventbridge`：EventBridge 客戶端
- `mock_telegram_api`：Telegram API
- `mock_allowlist`：DynamoDB allowlist
- `lambda_context`：Lambda context

### 測試標記

使用 pytest 標記分類測試：

```python
@pytest.mark.e2e           # 端對端測試
@pytest.mark.slow          # 慢速測試
@pytest.mark.requires_aws  # 需要 AWS 資源
```

## 🔍 測試覆蓋範圍

### ✅ 已覆蓋

- **命令處理**
  - `/info` 命令
  - 未知命令轉發
  - 管理員命令權限檢查

- **訊息流程**
  - 文字訊息標準化
  - EventBridge 事件發送
  - 訊息類型檢測（text, image, file）

- **認證授權**
  - Secret token 驗證
  - Allowlist 檢查
  - 非授權用戶拒絕

- **錯誤處理**
  - 無效 JSON payload
  - 缺少必要欄位
  - API 錯誤回應

### 📋 待添加

- [ ] 附件下載和處理
- [ ] 重試邏輯測試
- [ ] 併發請求測試
- [ ] 性能基準測試

## 🐛 除錯技巧

### 查看詳細日誌

```bash
pytest tests/e2e/ -v -s --log-cli-level=DEBUG
```

### 只運行失敗的測試

```bash
pytest tests/e2e/ --lf
```

### 進入除錯模式

```bash
pytest tests/e2e/ --pdb
```

### 查看 Mock 調用

```python
def test_debug_mocks(full_mock_env, lambda_context):
    # ...運行測試...
    
    # 檢查 EventBridge 事件
    events = full_mock_env["eventbridge"].get_events()
    print(f"發送了 {len(events)} 個事件")
    
    # 檢查 Telegram 訊息
    messages = full_mock_env["telegram_api"].get_sent_messages()
    print(f"發送了 {len(messages)} 條訊息")
    for msg in messages:
        print(f"  - {msg['text'][:50]}...")
```

## 📊 CI/CD 整合

### GitHub Actions

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd telegram-lambda
          pip install -r requirements-test.txt
      - name: Run E2E tests
        run: |
          cd telegram-lambda
          pytest tests/e2e/ -v --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## ⚡ 性能預期

- **單個測試**：< 0.5 秒
- **完整 E2E 套件**：< 10 秒
- **包含覆蓋率**：< 15 秒

## 🤝 貢獻指南

添加新測試時請：

1. 遵循現有測試的命名和結構
2. 使用清晰的測試描述
3. 添加適當的測試標記
4. 確保測試是獨立的（不依賴其他測試）
5. 運行所有測試確保沒有破壞現有功能

## 📚 相關資源

- [aiogram 官方文檔](https://docs.aiogram.dev/)
- [pytest 官方文檔](https://docs.pytest.org/)
- [moto (AWS mocking) 文檔](http://docs.getmoto.org/)
- [專案測試策略](../../docs/testing-strategy.md)

---

**問題回報**：如果遇到測試問題，請開 issue 並附上：
- 測試命令
- 錯誤訊息
- Python 版本
- 依賴版本（`pip list`）