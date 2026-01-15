# 創建測試用戶指令

**目標**：創建 4 個 E2E 測試用戶

---

## 📋 執行步驟

### 準備

**Web Users Table**: agentcore-web-channel-web-users

### 創建用戶（4個）

```bash
# User 1
./web-channel/scripts/create-admin-user.sh aws-e2e-test1@example.com

# User 2  
./web-channel/scripts/create-admin-user.sh aws-e2e-test2@example.com

# User 3
./web-channel/scripts/create-admin-user.sh aws-e2e-test3@example.com

# User 4
./web-channel/scripts/create-admin-user.sh aws-e2e-test4@example.com
```

**密碼**：腳本會自動生成並輸出

---

## 驗證

```bash
aws dynamodb scan \
  --region us-west-2 \
  --table-name agentcore-web-channel-web-users \
  --filter-expression "begins_with(email, :prefix)" \
  --expression-attribute-values '{":prefix":{"S":"aws-e2e-test"}}' \
  --projection-expression "email,#r" \
  --expression-attribute-names '{"#r":"role"}'
```

**預期結果**：4 個用戶，全部 enabled=true

