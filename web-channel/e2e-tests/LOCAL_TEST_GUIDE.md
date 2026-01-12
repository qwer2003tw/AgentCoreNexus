# E2E 本地測試指南

**目的**：在本地環境測試修復後的 E2E 測試

---

## 📋 前置需求

### 1. 確認環境
```bash
# 檢查 Node.js 版本（需要 18+）
node --version

# 檢查 npm
npm --version

# 當前目錄
pwd  # 應該在 AgentCoreNexus 根目錄
```

### 2. 安裝依賴（如果還沒裝）
```bash
# 安裝前端依賴
cd web-channel/frontend
npm install

# 安裝 E2E 測試依賴
cd ../e2e-tests
npm install

# 安裝 Playwright 瀏覽器
npx playwright install --with-deps
```

---

## 🔧 設置測試環境

### 步驟 1：配置 API 端點

創建 `web-channel/frontend/.env.local`：

```bash
cd web-channel/frontend

# 如果使用測試環境（AWS）
cat > .env.local << 'EOF'
VITE_API_ENDPOINT=https://your-api-endpoint.amazonaws.com
VITE_WS_ENDPOINT=wss://your-ws-endpoint.amazonaws.com
EOF

# 或如果使用本地後端
cat > .env.local << 'EOF'
VITE_API_ENDPOINT=http://localhost:8000
VITE_WS_ENDPOINT=ws://localhost:8000
EOF
```

**重要**：替換為實際的端點 URL！

### 步驟 2：配置測試帳號

```bash
cd ../e2e-tests

# 設置測試帳號環境變數
export TEST_USER_1_EMAIL=test1@test.com
export TEST_USER_1_PASSWORD=Test123!

# 或者如果有多個帳號要測試
export TEST_USER_2_EMAIL=test2@test.com
export TEST_USER_2_PASSWORD=Test123!
export TEST_USER_3_EMAIL=test3@test.com
export TEST_USER_3_PASSWORD=Test123!
export TEST_USER_4_EMAIL=test4@test.com
export TEST_USER_4_PASSWORD=Test123!
```

**注意**：替換為實際的測試帳號！

---

## 🧪 執行測試

### 方法 1：快速測試（Headless）

```bash
cd web-channel/e2e-tests
npm test
```

**預期輸出**：
```
Running 54 tests using 2 workers

  ✓ [chromium] › auth.spec.ts:5:3 › Authentication › can login with valid credentials
  ✓ [chromium] › auth.spec.ts:20:3 › Authentication › cannot login with invalid credentials
  ...
  
54 passed (2.5m)
```

### 方法 2：可見測試（Headed - 推薦用於 Debug）

```bash
npm test -- --headed
```

**好處**：
- 可以看到瀏覽器實際操作
- 看到登入過程
- 看到頁面導航
- 看到測試如何與 UI 互動

### 方法 3：UI 模式（互動式 Debug）

```bash
npm run test:ui
```

**功能**：
- 逐步執行測試
- 查看每個步驟的狀態
- 檢查元素選擇器
- 時間旅行 debug

### 方法 4：測試特定檔案

```bash
# 只測試登入功能
npm run test:auth

# 只測試聊天功能
npm run test:chat

# 只測試對話管理
npm run test:conversations
```

### 方法 5：Debug 單一測試

```bash
npm test -- --debug tests/auth.spec.ts
```

---

## 🔍 觀察修復效果

### 查看詳細日誌

在測試執行過程中，你應該看到：

```
🔵 Worker 0 using test1@test.com
📍 Worker 0: Navigated to login page
📍 Worker 0: Login form filled
📍 Worker 0: Login submitted
📍 Worker 0: Login API responded successfully
⚠️ Worker 0: User load API not detected, continuing...
📍 Worker 0: DOM content loaded
📍 Worker 0: Current URL after login: http://localhost:5173/chat
📍 Worker 0: Chat page loaded - "新對話" button found
✅ Worker 0 authenticated successfully
```

### 重點觀察

**Step 7 的關鍵日誌**：
```
📍 Worker 0: Current URL after login: http://localhost:5173/chat
```

**如果需要手動導航**（預期的兜底機制）：
```
📍 Worker 0: Current URL after login: http://localhost:5173/
⚠️ Worker 0: Not on chat page, attempting manual navigation...
📍 Worker 0: Manually navigated to: http://localhost:5173/chat
```

**如果失敗**（會看到診斷資訊）：
```
❌ Authentication failed for worker 0
Current URL: http://localhost:5173/
Page title: AgentCore Login
Screenshot saved: test-results/auth-failure-worker-0.png
```

---

## 📊 查看測試結果

### HTML 報告

```bash
# 測試完成後查看詳細報告
npm run test:report

# 會自動打開瀏覽器顯示：
# - 所有測試結果
# - 失敗測試的截圖
# - Trace 文件
# - 執行時間統計
```

### 截圖位置

如果測試失敗，截圖會保存在：
```
web-channel/e2e-tests/test-results/
├── auth-failure-worker-0.png  # 診斷截圖
└── test-results/
    └── [test-name]/
        ├── test-failed-1.png   # Playwright 自動截圖
        └── trace.zip           # 完整追蹤
```

### Trace 分析

```bash
# 查看某個測試的完整追蹤
npx playwright show-trace test-results/[test-name]/trace.zip
```

**可以看到**：
- 每個操作的時間軸
- 網路請求詳情
- 頁面導航記錄
- 截圖序列
- 日誌輸出

---

## 🐛 常見問題排查

### 問題 1: Frontend 啟動失敗

**錯誤**：
```
Error: Failed to start webServer
```

**解決**：
```bash
# 手動啟動 frontend（在另一個終端）
cd web-channel/frontend
npm run dev

# 然後在原終端執行測試，配置跳過 webServer
# 修改 playwright.config.ts 的 reuseExistingServer: true
```

### 問題 2: API 端點配置錯誤

**症狀**：所有測試都失敗，網路錯誤

**解決**：
```bash
# 檢查 .env.local
cat web-channel/frontend/.env.local

# 確認 API 端點可訪問
curl https://your-api-endpoint.amazonaws.com/health
```

### 問題 3: 測試帳號無效

**症狀**：登入失敗

**解決**：
```bash
# 驗證測試帳號（如果有後端可用）
curl -X POST https://your-api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test1@test.com","password":"Test123!"}'

# 或在瀏覽器手動登入測試
```

### 問題 4: Playwright 瀏覽器未安裝

**錯誤**：
```
browserType.launch: Executable doesn't exist
```

**解決**：
```bash
cd web-channel/e2e-tests
npx playwright install --with-deps
```

### 問題 5: 權限問題（Linux）

**錯誤**：
```
Permission denied
```

**解決**：
```bash
# 安裝系統依賴
sudo npx playwright install-deps
```

---

## ✅ 驗證修復成功的標準

### 1. 所有測試通過
```
54 passed (2.5m)
```

### 2. 日誌輸出清晰
- 每個 worker 都有完整的步驟日誌
- 能看到 URL 導航驗證
- 沒有未預期的錯誤

### 3. 截圖（如果失敗）
- 截圖清晰顯示失敗時的頁面狀態
- 能從截圖判斷問題

### 4. 執行時間合理
- 單一測試：< 30 秒
- 完整套件：2-5 分鐘（本地 2 workers）

---

## 📝 測試後的回報

如果測試成功，請回報：
```
✅ 本地測試通過
- 執行時間：X 分鐘
- 通過測試：54/54
- 是否看到手動導航日誌：是/否
```

如果測試失敗，請提供：
```
❌ 測試失敗
- 失敗的測試：[測試名稱]
- 錯誤訊息：[完整錯誤]
- 截圖：[截圖路徑]
- Current URL：[從日誌中提取]
```

---

## 🚀 下一步

### 如果本地測試通過
1. Commit 修改
2. Push 到 GitHub
3. 在 GitHub Actions 驗證（4 workers）

### 如果本地測試失敗
1. 查看截圖
2. 分析日誌
3. 使用 `--debug` 或 `--ui` 模式深入調查
4. 報告問題以便進一步修復

---

**測試愉快！** 🎉

如有問題，請提供詳細的錯誤訊息和日誌輸出。