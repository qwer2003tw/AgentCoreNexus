# 檢查部署狀態

快速檢查所有 AWS 資源的狀態，包含 CloudFormation stacks、Lambda 函數、EventBridge 和日誌。

## 使用方式

在 Cline 中輸入：`/check-status.md`

---

## 執行步驟

### 1. 檢查 CloudFormation Stacks 📦

列出所有 telegram 相關的 stacks：

```bash
aws cloudformation describe-stacks \
  --region us-west-2 \
  --query 'Stacks[?contains(StackName, `telegram`)].{Name:StackName,Status:StackStatus,Updated:LastUpdatedTime}' \
  --output table
```

**分析結果**：
- ✅ `CREATE_COMPLETE` 或 `UPDATE_COMPLETE` - 正常
- ⚠️ `UPDATE_IN_PROGRESS` - 正在更新中
- ❌ `ROLLBACK_*` 或 `*_FAILED` - 有問題

**報告格式**：
```
📦 CloudFormation Stacks:
- telegram-adapter-receiver: CREATE_COMPLETE ✅
- agentcore-ai-processor: UPDATE_COMPLETE ✅
```

---

### 2. 檢查 Lambda 函數狀態 🔧

列出所有 telegram Lambda 函數：

```bash
aws lambda list-functions \
  --region us-west-2 \
  --query 'Functions[?contains(FunctionName, `telegram`)].{Name:FunctionName,State:State,LastUpdate:LastUpdateStatus,Runtime:Runtime}' \
  --output table
```

**分析結果**：
- ✅ State: `Active` + LastUpdateStatus: `Successful` - 正常
- ⚠️ State: `Pending` 或 `InProgress` - 更新中
- ❌ State: `Failed` 或 `Inactive` - 有問題

**報告格式**：
```
🔧 Lambda 函數:
- telegram-adapter-receiver: Active (Successful) ✅
- agentcore-ai-processor-processor: Active (Successful) ✅
- telegram-adapter-response-router: Active (Successful) ✅
```

---

### 3. 檢查 EventBridge Rules 📡

檢查 EventBridge rules 和 targets：

```bash
# 列出 rules
aws events list-rules \
  --region us-west-2 \
  --event-bus-name telegram-adapter-receiver-events

# 檢查每個 rule 的 targets
aws events list-targets-by-rule \
  --region us-west-2 \
  --rule telegram-adapter-receiver-message-received \
  --event-bus-name telegram-adapter-receiver-events
```

**分析結果**：
- ✅ Rule 存在且有 targets - 正常
- ❌ Rule 存在但無 targets - 消息無法路由
- ❌ Rule 不存在 - 配置問題

**報告格式**：
```
📡 EventBridge Rules:
- message-received: 1 target ✅
- message-completed: 1 target ✅
```

---

### 4. 檢查最近日誌 📊

查看最近 5 分鐘的日誌，尋找錯誤：

```bash
# 接收器日誌
aws logs tail /aws/lambda/telegram-adapter-receiver \
  --region us-west-2 \
  --since 5m \
  --filter-pattern "ERROR"

# 處理器日誌
aws logs tail /aws/lambda/agentcore-ai-processor-processor \
  --region us-west-2 \
  --since 5m \
  --filter-pattern "ERROR"

# 路由器日誌
aws logs tail /aws/lambda/telegram-adapter-response-router \
  --region us-west-2 \
  --since 5m \
  --filter-pattern "ERROR"
```

**分析結果**：
- ✅ 無錯誤日誌 - 正常運行
- ⚠️ 有 WARNING - 需要關注
- ❌ 有 ERROR - 需要處理

**報告格式**：
```
📊 最近日誌 (5分鐘):
- telegram-adapter-receiver: 無錯誤 ✅
- agentcore-ai-processor-processor: 無錯誤 ✅
- telegram-adapter-response-router: 無錯誤 ✅
```

---

### 5. 檢查關鍵配置 ⚙️

驗證關鍵環境變數和配置：

```bash
# 檢查處理器的 EVENT_BUS_NAME
aws lambda get-function-configuration \
  --region us-west-2 \
  --function-name agentcore-ai-processor-processor \
  --query 'Environment.Variables.EVENT_BUS_NAME'
```

**必須檢查的配置**：
- ✅ EVENT_BUS_NAME（處理器必須有）
- ✅ BEDROCK_MODEL_ID（處理器）
- ✅ TELEGRAM_SECRETS_ARN（接收器）

**報告格式**：
```
⚙️ 關鍵配置:
- EVENT_BUS_NAME: telegram-adapter-receiver-events ✅
- BEDROCK_MODEL_ID: anthropic.claude-3-5-sonnet-... ✅
```

---

### 6. 檢查 Telegram Webhook 狀態 🤖

檢查 webhook 連接狀態：

```bash
# 需要 bot token（從 Secrets Manager 獲取或詢問用戶）
BOT_TOKEN=$(aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-adapter-receiver-secrets \
  --query SecretString --output text | jq -r .bot_token)

curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

**分析結果**：
- ✅ `pending_update_count: 0` - Webhook 正常
- ⚠️ `pending_update_count > 0` - 有積壓消息
- ❌ `url: ""` - Webhook 未設置

**報告格式**：
```
🤖 Telegram Webhook:
- URL: https://...execute-api...amazonaws.com/Prod/webhook
- 狀態: 已連接 ✅
- 積壓消息: 0
```

---

### 7. 生成狀態摘要報告 📋

綜合所有檢查結果，生成總結報告：

#### ✅ 系統健康的情況

```
🎉 系統狀態健康！

📦 CloudFormation Stacks: 全部正常 (2/2)
🔧 Lambda 函數: 全部 Active (3/3)
📡 EventBridge Rules: 配置正常 (2/2)
📊 最近日誌: 無錯誤
⚙️ 關鍵配置: 完整
🤖 Telegram Webhook: 已連接

💡 系統運行正常，無需額外操作。
```

---

#### ⚠️ 有警告的情況

```
⚠️ 系統基本正常，但有警告項目：

✅ CloudFormation Stacks: 全部正常
✅ Lambda 函數: 全部 Active
⚠️ EventBridge Rules: telegram-adapter-receiver-message-received 無 targets
✅ 最近日誌: 無錯誤
✅ 關鍵配置: 完整

🔧 建議操作：
1. 檢查 EventBridge rule 配置
2. 添加缺少的 targets
3. 重新部署 receiver stack
```

---

#### ❌ 有錯誤的情況

```
❌ 檢測到系統問題：

問題 1: Lambda 函數狀態異常
- agentcore-ai-processor-processor: Failed
- 建議: 查看詳細日誌並重新部署

問題 2: EventBridge 配置缺失
- message-received rule 無 targets
- 建議: 重新部署 receiver stack

問題 3: 日誌中有錯誤
- [ERROR] ImportModuleError: No module named 'xxx'
- 建議: 檢查依賴並重新部署

🚨 需要立即處理這些問題才能正常運行！
```

---

## 快速診斷指令

### 只檢查 stacks
```bash
aws cloudformation describe-stacks --region us-west-2 \
  --query 'Stacks[?contains(StackName,`telegram`)].{Name:StackName,Status:StackStatus}'
```

### 只檢查 Lambda
```bash
aws lambda list-functions --region us-west-2 \
  --query 'Functions[?contains(FunctionName,`telegram`)].{Name:FunctionName,State:State}'
```

### 只查看錯誤日誌
```bash
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/agentcore-ai-processor-processor \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

---

## 常見問題解讀

### Lambda State: Pending
**原因**: 配置更新中  
**處理**: 等待完成（通常 1-2 分鐘）

### EventBridge Rule 無 Targets
**原因**: 部署問題或手動刪除  
**處理**: 重新部署 stack

### Webhook pending_update_count > 0
**原因**: Bot 無法處理消息或處理太慢  
**處理**: 檢查 Lambda 日誌找出原因

---

## 何時使用這個 Workflow

### 定期檢查
- ✅ 每天早上檢查系統狀態
- ✅ 部署後驗證
- ✅ 用戶報告問題時

### 故障排除
- ✅ Bot 無響應時
- ✅ 部署後行為異常
- ✅ 性能下降時

### 監控
- ✅ 定期健康檢查
- ✅ 發布前驗證
- ✅ 維護窗口後確認

---

**Workflow 版本**: v1.0  
**創建日期**: 2026-01-14  
**AWS 區域**: us-west-2  
**預計執行時間**: 2-3 分鐘