# E2E 測試環境配置指南

## 📋 已獲取的部署資訊

### AWS Endpoints
- **REST API**: `https://kvofk12uz2.execute-api.us-west-2.amazonaws.com/prod`
- **WebSocket**: `wss://cfsm0w7id2.execute-api.us-west-2.amazonaws.com/prod`
- **Frontend**: `https://d1acz2ktx0n1il.cloudfront.net`

### Stack 資訊
- **Stack 名稱**: `agentcore-web-adapter`
- **Region**: `us-west-2`
- **Status**: `CREATE_COMPLETE` ✅

---

## 🔐 測試帳號配置

### 測試帳號配置

系統中已配置以下測試帳號（密碼：`Test123!`）：
- `aws-e2e-test1@test.com` - Worker 0
- `aws-e2e-test2@test.com` - Worker 1
- `aws-e2e-test3@test.com` - Worker 2
- `aws-e2e-test4@test.com` - Worker 3
- `test@test.com` - 通用測試帳號

### E2E 測試使用 4 個帳號

E2E 測試使用 4 個 parallel workers，每個 worker 使用獨立的測試帳號：
1. `aws-e2e-test1@test.com` - Worker 0
2. `aws-e2e-test2@test.com` - Worker 1
3. `aws-e2e-test3@test.com` - Worker 2
4. `aws-e2e-test4@test.com` - Worker 3

---

## 🔑 GitHub Secrets 配置

### 方法 1：使用 GitHub Web UI（推薦）

1. 前往：https://github.com/qwer2003tw/AgentCoreNexus/settings/secrets/actions

2. 點擊 "New repository secret"，逐一添加以下 secrets：

#### API Endpoints
```
Name: TEST_API_ENDPOINT
Value: https://kvofk12uz2.execute-api.us-west-2.amazonaws.com/prod
```

```
Name: TEST_WS_ENDPOINT
Value: wss://cfsm0w7id2.execute-api.us-west-2.amazonaws.com/prod
```

#### 測試帳號 1
```
Name: TEST_USER_1_EMAIL
Value: aws-e2e-test1@test.com
```

```
Name: TEST_USER_1_PASSWORD
Value: Test123!
```

#### 測試帳號 2
```
Name: TEST_USER_2_EMAIL
Value: aws-e2e-test2@test.com
```

```
Name: TEST_USER_2_PASSWORD
Value: Test123!
```

#### 測試帳號 3
```
Name: TEST_USER_3_EMAIL
Value: aws-e2e-test3@test.com
```

```
Name: TEST_USER_3_PASSWORD
Value: Test123!
```

#### 測試帳號 4
```
Name: TEST_USER_4_EMAIL
Value: aws-e2e-test4@test.com
```

```
Name: TEST_USER_4_PASSWORD
Value: Test123!
```

---

### 方法 2：使用 GitHub CLI

如果你已經認證了 gh CLI，可以使用以下命令：

```bash
# API Endpoints
gh secret set TEST_API_ENDPOINT --body "https://kvofk12uz2.execute-api.us-west-2.amazonaws.com/prod"
gh secret set TEST_WS_ENDPOINT --body "wss://cfsm0w7id2.execute-api.us-west-2.amazonaws.com/prod"

# 測試帳號 1
gh secret set TEST_USER_1_EMAIL --body "aws-e2e-test1@test.com"
gh secret set TEST_USER_1_PASSWORD --body "Test123!"

# 測試帳號 2
gh secret set TEST_USER_2_EMAIL --body "aws-e2e-test2@test.com"
gh secret set TEST_USER_2_PASSWORD --body "Test123!"

# 測試帳號 3
gh secret set TEST_USER_3_EMAIL --body "aws-e2e-test3@test.com"
gh secret set TEST_USER_3_PASSWORD --body "Test123!"

# 測試帳號 4
gh secret set TEST_USER_4_EMAIL --body "aws-e2e-test4@test.com"
gh secret set TEST_USER_4_PASSWORD --body "Test123!"
```

---

## 🧪 本地測試（可選）

在推送到 GitHub 前，可以本地驗證配置：

```bash
cd web-adapter/tests

# 設置環境變數
export TEST_USER_1_EMAIL="aws-e2e-test1@test.com"
export TEST_USER_1_PASSWORD="Test123!"
export TEST_USER_2_EMAIL="aws-e2e-test2@test.com"
export TEST_USER_2_PASSWORD="Test123!"
export TEST_USER_3_EMAIL="aws-e2e-test3@test.com"
export TEST_USER_3_PASSWORD="Test123!"
export TEST_USER_4_EMAIL="aws-e2e-test4@test.com"
export TEST_USER_4_PASSWORD="Test123!"

# 運行測試（使用真實 AWS 環境）
E2E_ENV=aws npm test
```

---

## 📝 測試帳號密碼要求

根據 `fixtures.ts` 中的預設值，測試帳號密碼格式為：
- 預設密碼：`Test123!`
- 需要確認實際系統是否有特定密碼要求

### 查詢實際密碼（如果忘記）

**重要**：密碼在 DynamoDB 中是加密儲存的，無法直接查看。

如果需要重置密碼，可以：
1. 使用 REST API 的 `/auth/change-password` endpoint
2. 或直接在 DynamoDB 中更新密碼 hash

---

## ✅ 驗證配置

配置完成後：

1. **推送到 GitHub**：
   ```bash
   git push origin your-branch
   ```

2. **檢查 GitHub Actions**：
   - 前往：https://github.com/qwer2003tw/AgentCoreNexus/actions
   - 查看最新的 workflow run
   - 確認 "Frontend Tests - web-adapter" job 通過

3. **預期結果**：
   ```
   ✅ 43 tests passed
   ❌ 0 tests failed
   ```

---

## 🐛 故障排除

### 問題 1：認證失敗
**症狀**：`page.waitForResponse: Timeout waiting for /auth/login`

**檢查**：
1. Email 是否正確？
2. Password 是否正確？
3. 帳號是否存在於 DynamoDB？

**解決**：
```bash
# 檢查帳號是否存在
aws dynamodb get-item --region us-west-2 \
  --table-name agentcore-web-adapter-web-users \
  --key '{"email":{"S":"aws-e2e-test1@test.com"}}'
```

### 問題 2：測試超時
**症狀**：Tests timeout after 120s

**檢查**：
1. API endpoints 是否正確？
2. WebSocket 連接是否正常？
3. Lambda 函數是否運行正常？

**解決**：
```bash
# 測試 API
curl https://kvofk12uz2.execute-api.us-west-2.amazonaws.com/prod/auth/login \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test123!"}'

# 檢查 Lambda logs
aws logs tail /aws/lambda/agentcore-web-adapter-auth --since 10m --region us-west-2
```

---

## 📞 需要幫助？

如果測試帳號密碼忘記或需要重置，請告知，我可以協助：
1. 創建新的測試帳號
2. 或重置現有帳號密碼