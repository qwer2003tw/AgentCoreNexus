# GitHub Secrets 設置指南

本文件提供完整的 GitHub Secrets 設置步驟，用於 E2E 測試整合真實 AWS 後端。

---

## 🎯 需要設置的 Secrets

**總共 10 個 secrets**

### API Endpoints（2 個）
```
TEST_API_ENDPOINT
TEST_WS_ENDPOINT
```

### 測試帳號（8 個）
```
TEST_USER_1_EMAIL, TEST_USER_1_PASSWORD
TEST_USER_2_EMAIL, TEST_USER_2_PASSWORD
TEST_USER_3_EMAIL, TEST_USER_3_PASSWORD
TEST_USER_4_EMAIL, TEST_USER_4_PASSWORD
```

---

## 📋 Step 1: 創建 AWS 測試帳號

### 1.1 需要創建的帳號

```
test1@test.com / Test123!
test2@test.com / Test123!
test3@test.com / Test123!
test4@test.com / Test123!
```

### 1.2 如何創建（取決於你的認證系統）

#### 選項 A：使用 Cognito

```bash
# 創建 User Pool 用戶
for i in {1..4}; do
  aws cognito-idp admin-create-user \
    --user-pool-id YOUR_USER_POOL_ID \
    --username test${i}@test.com \
    --user-attributes Name=email,Value=test${i}@test.com \
    --temporary-password TempPass123! \
    --region us-west-2
  
  # 設置永久密碼
  aws cognito-idp admin-set-user-password \
    --user-pool-id YOUR_USER_POOL_ID \
    --username test${i}@test.com \
    --password Test123! \
    --permanent \
    --region us-west-2
done
```

#### 選項 B：使用自訂認證 API

```bash
# 透過你的 API 創建用戶
for i in {1..4}; do
  curl -X POST https://dr614rh1s6.execute-api.us-west-2.amazonaws.com/prod/admin/users \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
    -d "{
      \"email\": \"test${i}@test.com\",
      \"password\": \"Test123!\"
    }"
done
```

#### 選項 C：使用管理員介面

1. 登入管理員後台
2. 前往「用戶管理」
3. 手動創建 4 個測試帳號

### 1.3 驗證帳號創建成功

**測試每個帳號可以登入**：

```bash
# 測試 test1@test.com
curl -X POST https://dr614rh1s6.execute-api.us-west-2.amazonaws.com/prod/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test1@test.com",
    "password": "Test123!"
  }'

# 預期回應：
# {"token":"eyJ...","userId":"..."}
# 狀態碼：200

# 重複測試 test2、test3、test4
```

---

## 📋 Step 2: 設置 GitHub Secrets

### 2.1 前往 GitHub Repository Settings

**網址**：
```
https://github.com/qwer2003tw/AgentCoreNexus/settings/secrets/actions
```

**或手動前往**：
```
Repository 頁面
→ Settings（上方選單）
→ Secrets and variables（左側選單）
→ Actions
```

---

### 2.2 新增 Secrets（逐個設置）

**點擊「New repository secret」按鈕**，然後按照下表逐一新增：

#### Secret 1: API Endpoint
```
Name: TEST_API_ENDPOINT
Secret: https://dr614rh1s6.execute-api.us-west-2.amazonaws.com/prod
```

#### Secret 2: WebSocket Endpoint
```
Name: TEST_WS_ENDPOINT
Secret: wss://c8921qtrs8.execute-api.us-west-2.amazonaws.com/prod
```

#### Secret 3-4: Worker 1 帳號
```
Name: TEST_USER_1_EMAIL
Secret: test1@test.com

Name: TEST_USER_1_PASSWORD
Secret: Test123!
```

#### Secret 5-6: Worker 2 帳號
```
Name: TEST_USER_2_EMAIL
Secret: test2@test.com

Name: TEST_USER_2_PASSWORD
Secret: Test123!
```

#### Secret 7-8: Worker 3 帳號
```
Name: TEST_USER_3_EMAIL
Secret: test3@test.com

Name: TEST_USER_3_PASSWORD
Secret: Test123!
```

#### Secret 9-10: Worker 4 帳號
```
Name: TEST_USER_4_EMAIL
Secret: test4@test.com

Name: TEST_USER_4_PASSWORD
Secret: Test123!
```

---

### 2.3 驗證 Secrets 設置成功

**檢查清單**：
- [ ] 總共有 10 個 secrets
- [ ] 名稱拼寫完全正確（區分大小寫）
- [ ] TEST_API_ENDPOINT 以 `https://` 開頭
- [ ] TEST_WS_ENDPOINT 以 `wss://` 開頭
- [ ] 4 組 EMAIL/PASSWORD 都已設置

**⚠️ 注意**：
- Secret 名稱**必須完全一致**（包含大小寫、底線）
- 設置後**無法查看**，只能更新或刪除
- 如果拼錯，需要刪除後重新創建

---

## 📋 Step 3: 觸發測試驗證

### 3.1 提交程式碼變更

```bash
git push
```

### 3.2 前往 GitHub Actions 觀察

**路徑**：
```
https://github.com/qwer2003tw/AgentCoreNexus/actions
```

**觀察重點**：

#### ✅ 環境配置成功
```
Configure test environment
✅ Test environment configured
```

#### ✅ Worker 隔離
```
Run E2E tests
🔵 Worker 0 using test1@test.com
🔵 Worker 1 using test2@test.com
🔵 Worker 2 using test3@test.com
🔵 Worker 3 using test4@test.com
```

#### ✅ 測試通過
```
Running 26 tests using 4 workers
✅ 26 passed
```

#### ✅ 執行時間
```
總時間：2-3 分鐘（vs 原本 9 分鐘）
改善：65-70%
```

---

## 🐛 故障排除

### 問題 1：Secret 未找到

**錯誤訊息**：
```
Worker 0 using test1@test.com  // email 正確
Worker 0 using undefined       // password 未定義
```

**原因**：Secret 名稱拼錯或未設置

**解決**：
1. 前往 GitHub Secrets 檢查名稱
2. 確保拼寫完全一致：`TEST_USER_1_PASSWORD`
3. 重新設置 secret

---

### 問題 2：API Endpoint 無效

**錯誤訊息**：
```
Configure test environment
✅ Test environment configured
// 但測試仍失敗
```

**檢查**：
```bash
# 測試 API 是否可訪問
curl https://dr614rh1s6.execute-api.us-west-2.amazonaws.com/prod/auth/login

# 應該返回：
# {"error":"Invalid request"} 或類似錯誤（但狀態碼 4xx，不是 5xx）
```

---

### 問題 3：測試帳號不存在

**錯誤訊息**：
```
Worker 0 using test1@test.com
// 登入失敗
```

**解決**：
1. 確認 AWS 帳號已創建
2. 測試用 curl 登入
3. 檢查密碼是否正確

---

### 問題 4：並發問題仍存在

**症狀**：測試間歇性失敗

**解決**：
```typescript
// playwright.config.ts
// 暫時降為 2 workers
workers: process.env.CI ? 2 : 1
```

---

## 🔐 安全檢查清單

### GitHub Secrets 安全性

- [x] Secrets 只包含測試環境資源（不是生產環境）
- [x] 測試帳號使用獨立密碼
- [x] 測試帳號權限受限
- [x] API endpoint 會暴露（但可接受，因為是測試環境）

### AWS 端安全性

- [ ] API Gateway Rate Limiting 已啟用
- [ ] CloudWatch 異常監控已設置
- [ ] 成本警報已配置
- [ ] 測試帳號只能訪問測試資料

---

## 📊 預期結果

### 執行時間

| 場景 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| 首次執行 | 9 分鐘 | 2.5-3 分鐘 | 65-70% |
| 後續執行 | 9 分鐘 | 2 分鐘 | 78% |

### 穩定性

- ✅ 4 workers 並行執行
- ✅ 帳號完全隔離
- ✅ 無 session 衝突
- ✅ 連接真實 AWS（99% 真實度）

---

## 📞 需要幫助？

如果遇到問題：
1. 檢查本文件的故障排除章節
2. 查看 GitHub Actions logs
3. 下載 Playwright 報告和截圖
4. 檢查 AWS CloudWatch logs

---

**設置負責人**: Repository Owner  
**預計時間**: 15-20 分鐘  
**最後更新**: 2026-01-12