# Lambda 部署流程

安全地部署 Lambda 函數到 AWS，包含完整的前置檢查和驗證步驟。

## 使用方式

在 Cline 中輸入：`/deploy-lambda.md`

---

## 前置檢查

### 1. 確認 Git 狀態 📋

檢查當前 git 工作目錄狀態：

```bash
git status
```

**處理邏輯**：
- 如果有未提交的變更，詢問用戶：
  ```
  ⚠️ 檢測到未提交的變更。
  
  是否要先提交這些變更？
  - 是：執行 git add 和 commit
  - 否：繼續部署（不推薦）
  - 取消：中止部署
  ```

---

### 2. 執行測試驗證 🧪

使用 `/test-full.md` workflow 執行完整測試：

```
調用 /test-full.md workflow
```

**要求**：
- 所有測試必須通過
- 覆蓋率必須達標
- 如果測試失敗，**停止部署流程**

---

## 部署步驟

### 3. 選擇要部署的 Stack 🎯

詢問用戶要部署哪個 stack：

```
請選擇要部署的 Stack：

1. telegram-adapter-receiver（接收器）
   - API Gateway
   - Webhook 接收 Lambda
   - 響應路由 Lambda
   
2. telegram-unified-bot（處理器）
   - AI 處理器 Lambda
   - Browser sandbox 整合
   
3. 兩者都部署（完整系統）

請輸入選項 (1/2/3):
```

---

### 4. 執行 SAM 部署 🚀

根據用戶選擇，執行相應的部署命令：

#### 選項 1: 部署接收器
```bash
cd telegram-adapter
sam build
sam deploy --stack-name telegram-adapter-receiver \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --region us-west-2
```

#### 選項 2: 部署處理器
```bash
cd ai-processor
sam build
sam deploy --stack-name telegram-unified-bot \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --region us-west-2
```

#### 選項 3: 部署兩者
依序執行選項 1 和 選項 2

**監控部署**：
- 顯示 CloudFormation 進度
- 如果部署失敗，顯示錯誤訊息
- 等待狀態變為 CREATE_COMPLETE 或 UPDATE_COMPLETE

---

### 5. 驗證部署成功 ✅

#### 5.1 檢查 CloudFormation Stack 狀態

```bash
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name [STACK_NAME] \
  --query 'Stacks[0].{Status:StackStatus,LastUpdated:LastUpdatedTime}'
```

**預期結果**：
- StackStatus: `CREATE_COMPLETE` 或 `UPDATE_COMPLETE`

---

#### 5.2 檢查 Lambda 函數狀態

```bash
aws lambda list-functions \
  --region us-west-2 \
  --query 'Functions[?contains(FunctionName, `telegram`)].{Name:FunctionName,State:State,LastUpdate:LastUpdateStatus}'
```

**預期結果**：
- State: `Active`
- LastUpdateStatus: `Successful`

如果狀態為 `Pending` 或 `InProgress`，等待完成：
```bash
aws lambda wait function-updated \
  --region us-west-2 \
  --function-name [FUNCTION_NAME]
```

---

#### 5.3 檢查最近日誌（確認無錯誤）

```bash
# 檢查接收器日誌
aws logs tail /aws/lambda/telegram-adapter-receiver \
  --region us-west-2 \
  --since 5m

# 檢查處理器日誌
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 \
  --since 5m
```

**驗證要點**：
- 無 `ERROR` 或 `ImportModuleError`
- 無 `Runtime.*` 錯誤
- Lambda 正常初始化

---

### 6. 提供部署總結和後續步驟 📊

#### 成功部署的報告格式

```
🎉 部署成功！

📦 已部署的 Stack：
- [Stack Name]: [Status]

🔍 驗證結果：
✅ CloudFormation Stack: UPDATE_COMPLETE
✅ Lambda 函數狀態: Active
✅ 最近日誌: 無錯誤

📝 重要輸出：
- Webhook URL: [URL]（如果是 receiver）
- EventBus ARN: [ARN]

🔗 後續步驟：
1. [如果是首次部署] 設置 Telegram Webhook
2. [如果更新了處理器] 測試 AI 對話功能
3. [如果更新了接收器] 測試 /info 命令
4. 監控 CloudWatch Logs 確保無異常

相關文檔：
- 部署指南: docs/deployment-guide.md
- 快速參考: .clinerules/deployment/telegram-bot-quick-reference.md
```

---

## 常見問題處理

### 問題 1: SAM 使用舊緩存

**症狀**: 代碼更新了但部署沒反應

**解決**:
```bash
rm -rf .aws-sam
sam build
sam deploy ...
```

---

### 問題 2: Lambda 緩存未清除

**症狀**: Secrets 更新了但 Lambda 讀到舊值

**解決**:
```bash
# 強制更新（緊急情況）
aws lambda update-function-code \
  --region us-west-2 \
  --function-name [FUNCTION_NAME] \
  --s3-bucket [BUCKET] \
  --s3-key [KEY] \
  --publish

# 之後必須再次 SAM deploy 確認
```

---

### 問題 3: EventBridge Rules 缺少 Targets

**症狀**: 消息沒有回應

**檢查**:
```bash
aws events list-targets-by-rule \
  --region us-west-2 \
  --rule telegram-adapter-receiver-message-received \
  --event-bus-name telegram-adapter-receiver-events
```

---

## 部署檢查清單

部署前確認：
- [ ] 所有測試通過
- [ ] Git 狀態乾淨（或已提交）
- [ ] 已選擇正確的 stack

部署後驗證：
- [ ] CloudFormation stack 狀態正常
- [ ] Lambda 函數狀態 Active
- [ ] 最近日誌無錯誤
- [ ] （如適用）Webhook 已更新

---

## 安全注意事項

### 權限檢查
- 確認 AWS CLI 配置正確
- 確認有足夠的 IAM 權限

### 環境變數
- 部署前檢查必要的環境變數
- 特別注意 EVENT_BUS_NAME（處理器必須）

### Secrets 管理
- 不要在日誌中顯示敏感信息
- 更新 secrets 後記得清除 Lambda 緩存

---

**Workflow 版本**: v1.0  
**創建日期**: 2026-01-14  
**AWS 區域**: us-west-2  
**預計執行時間**: 5-10 分鐘（視 stack 大小）