# Web Channel E2E Tests

Playwright E2E 測試套件，用於自動化測試 AgentCore Web Channel 的核心功能。

## 📋 測試覆蓋

### 已實現的測試（16 個測試用例）

#### Authentication (5 tests)
- ✅ 登入成功
- ✅ 登入失敗（錯誤密碼）
- ✅ 登出
- ✅ Session 持久性
- ✅ WebSocket 連接

#### Chat Core (5 tests)
- ✅ 發送消息並收到回覆
- ✅ **跨對話回覆路由**（關鍵）
- ✅ **標題即時更新**（關鍵）
- ✅ 快速連續消息處理
- ✅ WebSocket 重連

#### Conversation Management (6 tests)
- ✅ 創建多個對話
- ✅ 切換對話
- ✅ 重命名對話
- ✅ 刪除對話
- ✅ 置頂對話
- ✅ 搜尋對話

## 🚀 快速開始

### 安裝依賴

```bash
cd web-adapter/e2e-tests
npm install
npx playwright install
```

### 執行測試

```bash
# 執行所有測試
npm test

# 執行特定測試文件
npm run test:chat           # 聊天功能測試
npm run test:conversations  # 對話管理測試
npm run test:auth           # 認證測試

# 帶界面執行（調試用）
npm run test:headed

# 使用 Playwright UI（互動式）
npm run test:ui

# 調試模式
npm run test:debug
```

### 查看測試報告

```bash
npm run test:report
```

## 📊 測試結果

執行測試後會生成：
- `playwright-report/` - HTML 報告
- `test-results.json` - JSON 格式結果
- `test-results/` - 截圖和影片（失敗時）

## ⚙️ 配置

### 測試環境

#### **本地開發**
- **Base URL**: `http://localhost:5173`
- **API**: 使用 `.env.local` 或 `.env.test` 配置

#### **GitHub Actions CI**

**API Endpoints**（從 GitHub Secrets 讀取）：
- `TEST_API_ENDPOINT`: `https://dr614rh1s6.execute-api.us-west-2.amazonaws.com/prod`
- `TEST_WS_ENDPOINT`: `wss://c8921qtrs8.execute-api.us-west-2.amazonaws.com/prod`

**設置 GitHub Secrets**：

前往 `Repository → Settings → Secrets and variables → Actions`，新增：

```
TEST_API_ENDPOINT = https://dr614rh1s6.execute-api.us-west-2.amazonaws.com/prod
TEST_WS_ENDPOINT = wss://c8921qtrs8.execute-api.us-west-2.amazonaws.com/prod
TEST_USER_1_EMAIL = test1@test.com
TEST_USER_1_PASSWORD = Test123!
TEST_USER_2_EMAIL = test2@test.com
TEST_USER_2_PASSWORD = Test123!
TEST_USER_3_EMAIL = test3@test.com
TEST_USER_3_PASSWORD = Test123!
TEST_USER_4_EMAIL = test4@test.com
TEST_USER_4_PASSWORD = Test123!
```

**修改測試環境**：
編輯 `playwright.config.ts` 或使用環境變數

### 測試帳號

#### **本地開發**
- `test@test.com / Test123!`（或設置環境變數）

#### **GitHub Actions CI（4 Workers）**

使用 4 個獨立測試帳號確保 worker 隔離：
- Worker 1: `test1@test.com / Test123!`
- Worker 2: `test2@test.com / Test123!`
- Worker 3: `test3@test.com / Test123!`
- Worker 4: `test4@test.com / Test123!`

**配置方式**：
1. 在 AWS 後端創建 4 個測試帳號
2. 在 GitHub Repository Settings → Secrets 設置：
   - `TEST_USER_1_EMAIL` 和 `TEST_USER_1_PASSWORD`
   - `TEST_USER_2_EMAIL` 和 `TEST_USER_2_PASSWORD`
   - `TEST_USER_3_EMAIL` 和 `TEST_USER_3_PASSWORD`
   - `TEST_USER_4_EMAIL` 和 `TEST_USER_4_PASSWORD`

**為什麼需要 4 個帳號**：
- 4 workers 並行執行測試
- 避免 session 衝突和並發競爭
- 確保測試穩定性

**修改測試帳號**：
編輯 `setup/fixtures.ts` 中的 `TEST_USERS` 陣列

## 🔍 測試細節

### 關鍵測試說明

#### 1. 跨對話路由測試
**目的**：確保 AI 回覆顯示在正確的對話中

**步驟**：
1. 創建對話 A 和 B
2. 在對話 A 發送消息
3. 立即切換到對話 B
4. 等待 AI 回覆
5. 驗證對話 B 是空的
6. 切換回對話 A
7. 驗證回覆在對話 A

#### 2. 標題即時更新測試
**目的**：確保對話標題自動更新且無需刷新

**步驟**：
1. 創建新對話（標題：「新對話」）
2. 發送消息
3. 等待標題變更（使用 waitForFunction）
4. 驗證標題已更新為 AI 回覆內容
5. 確認沒有執行 page.reload()

## 🐛 測試故障排除

### 測試超時
- 增加 `timeout` 設置
- 檢查 backend Lambda 是否正常
- 確認本地開發伺服器運行中

### WebSocket 連接失敗
- 檢查 `.env.local` 配置
- 驗證 AWS backend 可訪問
- 查看瀏覽器 Console 錯誤

### 元素找不到
- 檢查 CSS selector 是否正確
- 使用 Playwright Inspector 調試
- 截圖查看實際 DOM 結構

## 📈 未來擴展

### 計劃添加的測試
- [ ] 歷史記錄功能
- [ ] 導出對話
- [ ] 帳號綁定（Telegram）
- [ ] 管理員功能
- [ ] 錯誤處理和邊界情況
- [ ] 性能測試（載入時間）
- [ ] 響應式設計（手機/平板）

### CI/CD 整合
- [ ] GitHub Actions workflow
- [ ] 自動化測試執行
- [ ] 測試報告上傳
- [ ] PR 檢查

## 📝 撰寫新測試

### 測試模板

```typescript
import { test, expect } from '../setup/fixtures'

test.describe('Feature Name', () => {
  
  test('test description', async ({ authenticatedPage: page }) => {
    // Arrange - 設置測試環境
    
    // Act - 執行操作
    
    // Assert - 驗證結果
    expect(result).toBe(expected)
  })
})
```

### 最佳實踐
1. 每個測試獨立（不依賴其他測試）
2. 使用描述性的測試名稱
3. 添加適當的等待時間
4. 驗證關鍵狀態變化
5. 處理異步操作

## 🎯 執行建議

### 開發時
```bash
# 監視模式（自動重跑）
npm run test:ui

# 或單獨執行修改的測試
npm run test:chat
```

### CI/CD
```bash
# 完整測試套件
npm test

# 生成報告
npm run test:report
```

---

**總計**：16 個 E2E 測試用例  
**覆蓋**：認證、聊天、對話管理  
**狀態**：✅ 已創建，待執行