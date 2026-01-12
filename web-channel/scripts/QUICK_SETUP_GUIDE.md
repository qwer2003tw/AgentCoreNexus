# E2E 測試快速設置指南

**目標**：創建 4 個測試帳號 + 設置 GitHub Secrets

**預計時間**：10-15 分鐘

---

## 🚀 Step 1: 創建測試帳號（5 分鐘）

### 方法 1：使用自動化腳本（推薦）⭐

```bash
cd web-channel/scripts

# 1. 先用管理員帳號登入獲取 token
ADMIN_TOKEN=$(curl -s -X POST https://dr614rh1s6.execute-api.us-west-2.amazonaws.com/prod/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"YOUR_ADMIN_EMAIL","password":"YOUR_ADMIN_PASSWORD"}' | jq -r .token)

# 2. 執行腳本創建 4 個帳號
ADMIN_TOKEN=$ADMIN_TOKEN ./create-test-accounts.sh

# 3. 驗證帳號創建成功
./verify-test-accounts.sh
```

**預期輸出**：
```
✅ 帳號創建成功
✅ 密碼設置成功: Test123!
...
🎉 所有測試帳號都可以正常登入！
```

---

### 方法 2：手動創建（備用）

如果沒有管理員權限，可以手動：

1. 登入你的應用管理員介面
2. 前往用戶管理
3. 創建以下帳號：
   ```
   test1@test.com / Test123!
   test2@test.com / Test123!
   test3@test.com / Test123!
   test4@test.com / Test123!
   ```

---

## 🔐 Step 2: 設置 GitHub Secrets（5 分鐘）

### 2.1 前往 GitHub Secrets 頁面

**直接連結**：
```
https://github.com/qwer2003tw/AgentCoreNexus/settings/secrets/actions
```

### 2.2 新增 10 個 Secrets

**點擊「New repository secret」**，逐一新增：

#### Secrets 清單（複製貼上）

```
Name: TEST_API_ENDPOINT
Value: https://dr614rh1s6.execute-api.us-west-2.amazonaws.com/prod

Name: TEST_WS_ENDPOINT
Value: wss://c8921qtrs8.execute-api.us-west-2.amazonaws.com/prod

Name: TEST_USER_1_EMAIL
Value: test1@test.com

Name: TEST_USER_1_PASSWORD
Value: Test123!

Name: TEST_USER_2_EMAIL
Value: test2@test.com

Name: TEST_USER_2_PASSWORD
Value: Test123!

Name: TEST_USER_3_EMAIL
Value: test3@test.com

Name: TEST_USER_3_PASSWORD
Value: Test123!

Name: TEST_USER_4_EMAIL
Value: test4@test.com

Name: TEST_USER_4_PASSWORD
Value: Test123!
```

### 2.3 驗證 Secrets 設置

**檢查清單**：
- [ ] 總共 10 個 secrets
- [ ] 名稱完全正確（注意大小寫）
- [ ] API endpoint 以 https:// 開頭
- [ ] WS endpoint 以 wss:// 開頭

---

## ✅ Step 3: 觸發測試（1 分鐘）

```bash
# 提交並 push
git add .
git commit -m "chore: add test account setup scripts"
git push
```

**前往觀察**：
```
https://github.com/qwer2003tw/AgentCoreNexus/actions
```

**預期結果**：
```
✅ Configure test environment
✅ Worker 0 using test1@test.com
✅ Worker 1 using test2@test.com
✅ Worker 2 using test3@test.com
✅ Worker 3 using test4@test.com
✅ Running 26 tests using 4 workers
✅ 26 passed
⏱️ Total: 2-3 minutes
```

---

## 🐛 故障排除

### 問題：腳本執行失敗

**錯誤**：`ADMIN_TOKEN 環境變數未設置`

**解決**：
```bash
# 方法 1：在同一行設置
ADMIN_TOKEN=your_token ./create-test-accounts.sh

# 方法 2：先 export
export ADMIN_TOKEN=your_token
./create-test-accounts.sh
```

---

### 問題：jq 命令未找到

**錯誤**：`jq: command not found`

**解決**：
```bash
# macOS
brew install jq

# Linux (Amazon Linux 2)
sudo yum install jq

# Ubuntu/Debian
sudo apt-get install jq
```

---

### 問題：curl 無法連接

**錯誤**：`Could not resolve host`

**檢查**：
```bash
# 測試 API 是否可訪問
curl https://dr614rh1s6.execute-api.us-west-2.amazonaws.com/prod/auth/login

# 應該返回（即使是錯誤，但能連接）：
# {"error":"Invalid request"}
```

---

## 📝 驗證檢查清單

完成所有步驟後，確認：

### AWS 端
- [ ] 4 個測試帳號已創建
- [ ] 每個帳號可以登入（執行 verify 腳本）
- [ ] 密碼都是 Test123!

### GitHub 端
- [ ] 10 個 secrets 已設置
- [ ] Secret 名稱完全正確
- [ ] API endpoints 正確

### 測試端
- [ ] git push 已執行
- [ ] GitHub Actions 正在執行
- [ ] 觀察測試結果

---

## 🎯 成功標準

**測試通過時會看到**：
```
✅ 26 tests passed
⏱️ Duration: ~2-3 minutes
🎯 Optimization: 70% faster (9min → 3min)
```

---

**快速設置版本**: v1.0  
**API Endpoint**: dr614rh1s6.execute-api.us-west-2.amazonaws.com  
**最後更新**: 2026-01-12