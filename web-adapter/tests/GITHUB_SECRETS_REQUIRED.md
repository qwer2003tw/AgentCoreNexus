# GitHub Secrets 配置說明

**目的**: 確保 CI/CD E2E 測試能連接到真實 AWS 環境  
**更新日期**: 2026-01-28

---

## 🔑 必需的 GitHub Secrets

在 GitHub repository 設置中（Settings → Secrets and variables → Actions），需要配置以下 secrets：

### AWS Endpoints（3 個）

#### 1. FRONTEND_URL
```
值: https://d1p3mmbx4pyq2j.cloudfront.net
用途: Playwright 測試的 baseURL
```

#### 2. TEST_API_ENDPOINT
```
值: https://jooap0xv8l.execute-api.us-west-2.amazonaws.com/prod
用途: REST API endpoint
來源: CloudFormation stack "agentcore-web-adapter" 的 Output "RestApiEndpoint"
```

#### 3. TEST_WS_ENDPOINT
```
值: wss://356rrmw4pg.execute-api.us-west-2.amazonaws.com/prod
用途: WebSocket API endpoint
來源: CloudFormation stack "agentcore-web-adapter" 的 Output "WebSocketEndpoint"
```

### 測試用戶帳號（8 個，4 組）

**用途**: 支援 4 個並行 workers，避免衝突

#### Worker 1
```
TEST_USER_1_EMAIL: aws-e2e-test1@test.com
TEST_USER_1_PASSWORD: Test123!
```

#### Worker 2
```
TEST_USER_2_EMAIL: aws-e2e-test2@test.com
TEST_USER_2_PASSWORD: Test123!
```

#### Worker 3
```
TEST_USER_3_EMAIL: aws-e2e-test3@test.com
TEST_USER_3_PASSWORD: Test123!
```

#### Worker 4
```
TEST_USER_4_EMAIL: aws-e2e-test4@test.com
TEST_USER_4_PASSWORD: Test123!
```

---

## 📋 設置步驟

### 1. 在 GitHub 設置 Secrets

```bash
# 方法 1: 使用 GitHub UI
1. 進入 repository → Settings
2. Secrets and variables → Actions
3. New repository secret
4. 逐一添加上述 11 個 secrets

# 方法 2: 使用 GitHub CLI（更快）
gh secret set FRONTEND_URL -b "https://d1p3mmbx4pyq2j.cloudfront.net"
gh secret set TEST_API_ENDPOINT -b "https://jooap0xv8l.execute-api.us-west-2.amazonaws.com/prod"
gh secret set TEST_WS_ENDPOINT -b "wss://356rrmw4pg.execute-api.us-west-2.amazonaws.com/prod"

gh secret set TEST_USER_1_EMAIL -b "aws-e2e-test1@test.com"
gh secret set TEST_USER_1_PASSWORD -b "Test123!"
gh secret set TEST_USER_2_EMAIL -b "aws-e2e-test2@test.com"
gh secret set TEST_USER_2_PASSWORD -b "Test123!"
gh secret set TEST_USER_3_EMAIL -b "aws-e2e-test3@test.com"
gh secret set TEST_USER_3_PASSWORD -b "Test123!"
gh secret set TEST_USER_4_EMAIL -b "aws-e2e-test4@test.com"
gh secret set TEST_USER_4_PASSWORD -b "Test123!"
```

### 2. 驗證 Secrets 已設置

```bash
# 列出所有 secrets（只顯示名稱）
gh secret list
```

**預期輸出**：
```
FRONTEND_URL
TEST_API_ENDPOINT
TEST_USER_1_EMAIL
TEST_USER_1_PASSWORD
TEST_USER_2_EMAIL
TEST_USER_2_PASSWORD
TEST_USER_3_EMAIL
TEST_USER_3_PASSWORD
TEST_USER_4_EMAIL
TEST_USER_4_PASSWORD
TEST_WS_ENDPOINT
```

---

## 🔄 Secrets 更新時機

**需要更新 secrets 的情況**：

1. **部署新的 Stack 時**
   ```bash
   # 獲取最新 endpoints
   aws cloudformation describe-stacks \
     --stack-name agentcore-web-adapter \
     --region us-west-2 \
     --query 'Stacks[0].Outputs'
   
   # 更新對應的 secrets
   gh secret set TEST_API_ENDPOINT -b "新的值"
   gh secret set TEST_WS_ENDPOINT -b "新的值"
   ```

2. **更換測試帳號時**
   ```bash
   # 更新測試用戶
   gh secret set TEST_USER_1_EMAIL -b "new-test@test.com"
   gh secret set TEST_USER_1_PASSWORD -b "NewPassword123!"
   ```

3. **更換 CloudFront distribution 時**
   ```bash
   gh secret set FRONTEND_URL -b "https://new-distribution.cloudfront.net"
   ```

---

## 🧪 驗證 Secrets 配置

### 測試單個 secret

```bash
# 在 GitHub Actions 中，secrets 不會顯示實際值
# 但可以驗證是否可讀取
echo "${{ secrets.TEST_API_ENDPOINT }}" | wc -c
# 應該輸出 > 0
```

### 運行測試驗證

```bash
# Trigger GitHub Actions workflow
git commit --allow-empty -m "test: trigger CI/CD"
git push

# 或使用 gh CLI
gh workflow run tests.yml
```

---

## ⚠️ 安全考量

### 不要在日誌中暴露 Secrets

```yaml
# ❌ 錯誤
- name: Debug
  run: echo "API: ${{ secrets.TEST_API_ENDPOINT }}"

# ✅ 正確
- name: Verify secrets
  run: |
    if [ -z "${{ secrets.TEST_API_ENDPOINT }}" ]; then
      echo "❌ TEST_API_ENDPOINT not set"
      exit 1
    fi
    echo "✅ TEST_API_ENDPOINT is configured"
```

### Secrets 權限管理

- 只有 repository 管理員可以管理 secrets
- Secrets 在 pull request 中可用（來自 fork 的 PR 除外）
- 建議為每個環境使用不同的 secrets

---

## 📚 相關文檔

- [GitHub Secrets 官方文檔](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- `.github/workflows/tests.yml` - Workflow 配置
- `web-adapter/tests/.env.aws` - AWS 環境配置模板
- `web-adapter/tests/GITHUB_SECRETS_SETUP.md` - 詳細設置指南

---

## ✅ 檢查清單

設置完成後，驗證：

- [ ] 所有 11 個 secrets 已設置（`gh secret list`）
- [ ] Secrets 值正確（與 `.env.aws` 一致）
- [ ] GitHub Actions 可以讀取 secrets
- [ ] 觸發 workflow 測試成功

---

**版本**: v1.0  
**維護者**: DevOps Team  
**最後更新**: 2026-01-28