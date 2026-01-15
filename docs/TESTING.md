# 📋 AgentCoreNexus 測試指南

本文檔說明專案的測試策略、執行方法和最佳實踐。

---

## 🎯 測試概覽

AgentCoreNexus 由三個獨立組件組成，每個組件都有完整的測試套件：

| 組件 | 測試框架 | 測試類型 | 覆蓋率要求 |
|------|---------|---------|-----------|
| **ai-processor** | pytest | 單元測試 | 新代碼 ≥ 80% |
| **telegram-adapter** | pytest | 單元 + E2E | 新代碼 ≥ 80% |
| **web-adapter** | Playwright | E2E 測試 | N/A |

---

## 🚀 快速開始

### 一鍵測試所有組件

```bash
# 在專案根目錄執行
./run_all_tests.sh

# 或使用 Makefile
make test
```

### 快速測試（跳過 Web E2E）

```bash
# 節省時間，適合開發時快速驗證
./run_all_tests.sh --quick

# 或
make test-quick
```

---

## 📦 組件測試

### 1. ai-processor（AI 處理器）

**測試內容**：
- 配置管理測試
- 工具函數測試（計算器、天氣、文件讀取等）
- 服務測試（記憶、瀏覽器、文件服務）
- Agent 測試（對話代理）
- 錯誤處理測試
- Memory 整合測試

**執行測試**：

```bash
cd ai-processor

# 方法 1: 使用覆蓋率腳本（推薦）
./run_tests_with_coverage.sh

# 方法 2: 使用 pytest 直接執行
python3.11 -m pytest tests/ -v

# 方法 3: 使用原有的 unittest 腳本
python3.11 run_tests.py

# 帶覆蓋率報告
python3.11 -m pytest tests/ --cov=. --cov-report=html
```

**查看覆蓋率報告**：

```bash
# 終端顯示
python3.11 -m coverage report

# 瀏覽器查看詳細報告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

### 2. telegram-adapter（Webhook 接收器）

**測試內容**：
- 單元測試：Handler、Allowlist、Commands、Secrets Manager 等
- E2E 測試：完整的消息流程，使用 aiogram 生成真實 Telegram Update

**執行測試**：

```bash
cd telegram-adapter

# 完整測試（推薦）
./run_all_tests.sh --cov

# 只運行單元測試
python3.11 -m pytest tests/ --ignore=tests/e2e/ -v

# 只運行 E2E 測試
python3.11 -m pytest tests/e2e/ -v

# 特定測試文件
python3.11 -m pytest tests/e2e/test_commands.py -v
```

**覆蓋率要求**：
- 整體覆蓋率：目標 > 70%
- **新代碼覆蓋率：強制 ≥ 80%**

---

### 3. web-adapter（Web 前端）

**測試內容**：
- 認證測試（登入、登出、Session）
- 聊天功能測試（發送消息、接收回覆、跨對話路由）
- 對話管理測試（創建、切換、重命名、刪除、搜尋）

**執行測試**：

```bash
cd web-adapter/e2e-tests

# 首次執行需要安裝依賴
npm install
npx playwright install

# 執行所有測試
npm test

# 執行特定測試
npm run test:chat           # 聊天功能
npm run test:conversations  # 對話管理
npm run test:auth           # 認證功能

# 帶界面執行（調試用）
npm run test:headed

# 使用 UI 模式（互動式）
npm run test:ui
```

**查看測試報告**：

```bash
npm run test:report
```

---

## 🎭 Makefile 命令

為了方便使用，專案提供了統一的 Makefile 命令：

```bash
# 測試相關
make test              # 執行所有測試（推薦）
make test-backend      # 測試後端組件
make test-frontend     # 測試前端組件
make test-agentcore    # 只測試 AI 處理器
make test-lambda       # 只測試 Webhook 接收器
make test-web          # 只測試 Web 前端
make test-quick        # 快速測試（不含 Web E2E）
make coverage-report   # 查看覆蓋率報告

# 查看幫助
make help
```

---

## 📊 覆蓋率要求

### 整體策略

- **新代碼覆蓋率**：≥ 80%（強制，使用 diff-cover 檢查）
- **整體覆蓋率**：目標 > 70%（建議，逐步提升）

### 檢查新代碼覆蓋率

```bash
# 確保已安裝 diff-cover
pip install diff-cover

# ai-processor
cd ai-processor
pytest tests/ --cov=. --cov-report=xml
diff-cover coverage.xml --compare-branch=main --fail-under=80

# telegram-adapter
cd telegram-adapter
pytest tests/ --cov=src --cov-report=xml
diff-cover coverage.xml --compare-branch=main --fail-under=80
```

### 覆蓋率報告位置

- ai-processor: `htmlcov/index.html`
- telegram-adapter: `htmlcov/index.html`
- XML 報告: `coverage.xml`（用於 CI/CD）

---

## 🔄 Pre-commit Hook

專案已配置 pre-commit hook，會在每次 commit 前自動執行：

1. 🔍 Ruff 代碼質量檢查（自動修復 + 格式化）
2. 🧪 單元測試
3. 🎭 E2E 測試（如果依賴已安裝）
4. 📊 覆蓋率檢查（新代碼 ≥ 80%）

**安裝 Hook**：

```bash
./setup-hooks.sh
```

**緊急跳過**（不推薦）：

```bash
git commit --no-verify
```

---

## 🐛 測試除錯

### 查看詳細日誌

```bash
# pytest 詳細輸出
pytest tests/ -v -s --log-cli-level=DEBUG

# 只運行失敗的測試
pytest tests/ --lf

# 進入除錯模式
pytest tests/ --pdb
```

### 常見問題

#### 問題 1: ModuleNotFoundError

```bash
# 解決：安裝測試依賴
cd telegram-adapter
pip install -r requirements-test.txt

cd ai-processor
pip install pytest pytest-cov pytest-asyncio
```

#### 問題 2: Python 版本錯誤

**必須使用 Python 3.11**：

```bash
# 檢查版本
python3.11 --version

# 使用正確版本執行
python3.11 -m pytest tests/ -v
```

#### 問題 3: Playwright 瀏覽器未安裝

```bash
cd web-adapter/e2e-tests
npx playwright install
```

---

## 📝 撰寫新測試

### ai-processor 範例

```python
# tests/test_new_feature.py
import pytest

def test_my_new_feature():
    """測試新功能"""
    # Arrange
    input_data = "test"
    
    # Act
    result = my_function(input_data)
    
    # Assert
    assert result == expected_output
```

### telegram-adapter 範例

```python
# tests/test_new_handler.py
import pytest
from tests.e2e.helpers.telegram_factory import TelegramUpdateFactory

@pytest.mark.e2e
def test_new_command(full_mock_env, lambda_context):
    """測試新命令"""
    # Arrange
    event = TelegramUpdateFactory.create_command_update("mycommand")
    
    # Act
    response = lambda_handler(event, lambda_context)
    
    # Assert
    assert response["statusCode"] == 200
```

### web-adapter 範例

```typescript
// tests/new-feature.spec.ts
import { test, expect } from '../setup/fixtures'

test.describe('New Feature', () => {
  test('should work correctly', async ({ authenticatedPage: page }) => {
    // Arrange
    await page.goto('/')
    
    // Act
    await page.click('button#new-feature')
    
    // Assert
    await expect(page.locator('.result')).toBeVisible()
  })
})
```

---

## 🎯 測試最佳實踐

### 通用原則

1. ✅ **獨立性**：每個測試應該獨立運行
2. ✅ **可重複**：多次運行結果一致
3. ✅ **快速**：單元測試 < 1 秒，E2E < 30 秒
4. ✅ **清晰**：測試名稱描述測試內容
5. ✅ **AAA 模式**：Arrange, Act, Assert

### Python 測試

```python
# ✅ 好的測試
def test_calculator_addition():
    """測試計算器的加法功能"""
    # Arrange
    calc = Calculator()
    
    # Act
    result = calc.add(2, 3)
    
    # Assert
    assert result == 5

# ❌ 不好的測試
def test_stuff():
    assert Calculator().add(2, 3) == 5  # 沒有說明，難以理解
```

### TypeScript 測試

```typescript
// ✅ 好的測試
test('should display error message when login fails', async ({ page }) => {
  await page.fill('#email', 'wrong@email.com')
  await page.fill('#password', 'wrongpass')
  await page.click('button[type="submit"]')
  
  await expect(page.locator('.error')).toHaveText('Invalid credentials')
})

// ❌ 不好的測試
test('login', async ({ page }) => {
  // 測試多個場景，難以定位問題
})
```

---

## 📈 CI/CD 整合

### GitHub Actions（計劃中）

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: ./run_all_tests.sh --quick
      
  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: cd web-adapter/e2e-tests && npm test
```

---

## 🔗 相關資源

### 組件測試文檔

- [telegram-adapter E2E 測試](../telegram-adapter/tests/e2e/README.md)
- [web-adapter E2E 測試](../web-adapter/e2e-tests/README.md)

### 工作流規範

- [測試標準與規範](../.clinerules/TESTING_STANDARDS.md)
- [代碼質量工作流](../.clinerules/CODE_QUALITY_WORKFLOW.md)

### 測試框架文檔

- [pytest 官方文檔](https://docs.pytest.org/)
- [Playwright 官方文檔](https://playwright.dev/)
- [aiogram 官方文檔](https://docs.aiogram.dev/)

---

## 📞 需要幫助？

如果遇到測試問題：

1. 查看 [常見問題](#常見問題) 章節
2. 檢查組件的測試文檔
3. 查看測試日誌輸出
4. 開 issue 並附上錯誤訊息

---

**文檔版本**: 1.0  
**最後更新**: 2026-01-12  
**維護者**: AgentCoreNexus Team