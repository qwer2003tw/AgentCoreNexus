# Check IAM Permissions Workflow

檢查 Lambda 代碼使用的 AWS 操作是否在 CloudFormation template 的 IAM 中授權。

**使用時機**：
- 添加新的 Lambda 函數後
- 修改 Lambda 代碼（特別是 boto3 調用）後
- 部署前最後檢查
- 收到 AccessDeniedException 後

**預計時間**：5-10 分鐘

---

## 步驟

### Step 1: 掃描代碼中的 DynamoDB 操作

```bash
# 在 Lambda 代碼目錄
cd [lambda-directory]

# 掃描所有 DynamoDB 操作
echo "📋 掃描代碼中的 DynamoDB 操作..."
grep -r "table\.\(scan\|query\|get_item\|put_item\|update_item\|delete_item\)" . \
  --include="*.py" \
  | grep -v "test" \
  | sort -u

# 記錄發現的操作
```

**常見模式**：
- `table.scan()` → 需要 `dynamodb:Scan`
- `table.query()` → 需要 `dynamodb:Query`
- `table.get_item()` → 需要 `dynamodb:GetItem`
- `table.put_item()` → 需要 `dynamodb:PutItem`
- `table.update_item()` → 需要 `dynamodb:UpdateItem`
- `table.delete_item()` → 需要 `dynamodb:DeleteItem`

---

### Step 2: 檢查 Template 中的 IAM 權限

```bash
# 在 infrastructure 目錄
cd [infrastructure-directory]

# 查找特定 Lambda 的權限
echo "📋 檢查 template 中的 IAM 權限..."
grep -A30 "FunctionName: FUNCTION_NAME" template.yaml \
  | grep -A20 "Policies:" \
  | grep "dynamodb:"

# 或查找所有 DynamoDB 權限
grep "dynamodb:" template.yaml | sort -u
```

---

### Step 3: 對比和報告

**手動對比**：
- 列出代碼使用的操作
- 列出 IAM 允許的操作
- 找出缺少的權限

**範例報告**：
```
代碼使用的操作：
- scan (admin_api.py:150)
- query (admin_api.py:120)
- put_item (admin_api.py:200)

IAM 允許的操作：
✅ dynamodb:Query
✅ dynamodb:PutItem  
❌ dynamodb:Scan ⚠️ 缺少！

需要添加到 template.yaml：
- dynamodb:Scan
```

---

### Step 4: 修復 Template

在 `Policies` 中添加缺少的操作：

```yaml
Policies:
  - Statement:
      - Effect: Allow
        Action:
          - dynamodb:Query
          - dynamodb:PutItem
          - dynamodb:Scan  # ⭐ 添加
        Resource:
          - !Sub 'arn:aws:dynamodb:...table-name'
```

---

### Step 5: 驗證修復

```bash
# SAM validate
sam validate --template TEMPLATE_FILE

# 重新部署
sam build --template TEMPLATE_FILE
sam deploy --stack-name STACK_NAME --resolve-s3 --capabilities CAPABILITY_IAM

# 測試 API
curl API_ENDPOINT

# 檢查日誌（應該沒有 AccessDeniedException）
aws logs tail /aws/lambda/FUNCTION_NAME --since 5m | grep AccessDenied
```

---

## 常見 DynamoDB 操作和權限映射

| 代碼操作 | 需要的 IAM 權限 | 說明 |
|---------|----------------|------|
| `table.scan()` | `dynamodb:Scan` | 掃描整個表 |
| `table.query()` | `dynamodb:Query` | 使用主鍵或 GSI 查詢 |
| `table.get_item()` | `dynamodb:GetItem` | 讀取單個項目 |
| `table.put_item()` | `dynamodb:PutItem` | 創建或覆蓋項目 |
| `table.update_item()` | `dynamodb:UpdateItem` | 更新項目 |
| `table.delete_item()` | `dynamodb:DeleteItem` | 刪除項目 |
| `table.batch_get_item()` | `dynamodb:BatchGetItem` | 批量讀取 |
| `table.batch_write_item()` | `dynamodb:BatchWriteItem` | 批量寫入 |

---

## 常見錯誤模式

### 模式 1: 只有 Query 沒有 Scan

**症狀**：
```python
# 代碼中使用
response = table.scan(FilterExpression=...)
```

**IAM 中只有**：
```yaml
Action:
  - dynamodb:Query  # ❌ 缺少 Scan
```

**修復**：添加 `dynamodb:Scan`

---

### 模式 2: 忘記 GSI 權限

**症狀**：
```python
response = table.query(IndexName='my-index', ...)
```

**IAM 缺少 GSI resource**：
```yaml
Resource:
  - !Sub '...table-name'  # ❌ 缺少 index/*
```

**修復**：
```yaml
Resource:
  - !Sub '...table-name'
  - !Sub '...table-name/index/*'  # ⭐ 添加
```

---

### 模式 3: 寬泛權限 vs 精確權限

**寬泛**（快速但不安全）：
```yaml
Action: dynamodb:*
Resource: '*'
```

**精確**（推薦）：
```yaml
Action:
  - dynamodb:Query
  - dynamodb:Scan
Resource:
  - !Sub '...specific-table'
```

---

## 預防措施

### 寫代碼時

**✅ 同時更新 Template**：
- 添加新的 boto3 調用 → 立即檢查 IAM
- 不要等到部署後才發現

### 部署前

**✅ 運行此 Workflow**：
```bash
/check-iam-permissions.md
```

### Code Review

**✅ 檢查清單**：
- [ ] 所有 boto3 調用都有對應權限
- [ ] GSI 查詢有 index/* resource
- [ ] 沒有過度寬泛的權限（`*`）

---

## 自動化工具（未來）

可以創建腳本自動檢查：

```python
# scripts/check-iam-coverage.py
def scan_code_operations(file):
    # 掃描 boto3 調用
    pass

def scan_template_permissions(template, function):
    # 掃描 IAM 權限
    pass

def report_missing(code_ops, iam_ops):
    # 報告缺少的權限
    pass
```

---

## 相關資源

- **部署最佳實踐**：`.clinerules/deployment/lambda-development-best-practices.md`
- **部署 Workflow**：`.clinerules/workflows/deploy-lambda.md`
- **IAM 最佳實踐**：AWS 文檔

---

**Workflow 版本**: 1.0  
**創建日期**: 2027-01-27  
**基於案例**: Admin API AccessDeniedException（缺少 Scan 權限）