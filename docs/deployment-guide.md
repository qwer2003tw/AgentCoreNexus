# AgentCore Nexus 完整部署指南

## 🎯 部署前檢查清單

### ✅ 已完成的檢查
- [x] 代碼完整性檢查
- [x] 依賴項驗證
- [x] SAM Template 驗證
- [x] **Router 依賴問題修復** (Commit 4538333)
- [x] Git 狀態清理

### 📝 需要準備的資料

1. **Telegram Bot Token**
   ```bash
   # 從 @BotFather 獲取
   # 格式: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

2. **AWS Region**
   - 建議: `us-east-1` 或 `ap-northeast-1`
   - 確認該區域有 Bedrock 服務

3. **Bedrock 模型訪問權限**
   - 需要申請：`anthropic.claude-3-5-sonnet-20241022-v2:0`
   - 或使用其他可用模型

---

## 🚀 部署步驟（方案 A：完整部署）

### Step 1: 部署 Adapter + Router Stack

```bash
cd /home/ec2-user/Projects/AgentCoreNexus/telegram-adapter

# 建置
sam build

# 部署（首次使用 --guided）
sam deploy --guided

# 部署時會詢問：
# Stack Name: telegram-adapter (或自訂名稱)
# AWS Region: us-east-1 (或您選擇的區域)
# Parameter TelegramBotToken: [您的 Bot Token]
# Confirm changes before deploy: Y
# Allow SAM CLI IAM role creation: Y
# Save arguments to configuration file: Y
```

**重要輸出（記錄下來）：**
```
Outputs:
- EventBusName: telegram-adapter-events
- EventBusArn: arn:aws:events:...
- WebhookUrl: https://....execute-api....amazonaws.com/Prod/webhook
- ResponseRouterFunctionArn: arn:aws:lambda:...
```

### Step 2: 部署 Processor Stack

```bash
cd /home/ec2-user/Projects/AgentCoreNexus/ai-processor

# 建置
sam build

# 部署（使用 Step 1 的輸出）
sam deploy --guided \
  --parameter-overrides \
    EventBusName="<Step1-EventBusName>" \
    EventBusArn="<Step1-EventBusArn>" \
    BedrockModelId="anthropic.claude-3-5-sonnet-20241022-v2:0"

# 部署時會詢問：
# Stack Name: ai-processor (或自訂名稱)
# AWS Region: [與 Step 1 相同]
# Confirm changes before deploy: Y
# Allow SAM CLI IAM role creation: Y
# Save arguments to configuration file: Y
```

**重要輸出（記錄下來）：**
```
Outputs:
- ProcessorFunctionArn: arn:aws:lambda:...
- DeploymentInstructions: [EventBridge 連接指令]
```

### Step 3: 連接 EventBridge Rule 到 Processor

```bash
# 使用 Step 2 輸出中的 DeploymentInstructions
aws events put-targets \
  --rule telegram-adapter-message-received \
  --event-bus-name telegram-adapter-events \
  --targets "Id"="AgentProcessor","Arn"="<ProcessorFunctionArn>"

# 驗證 Rule 已連接
aws events list-targets-by-rule \
  --rule telegram-adapter-message-received \
  --event-bus-name telegram-adapter-events
```

### Step 4: 配置 Telegram Webhook

```bash
# 使用 Step 1 的 WebhookUrl
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "<WebhookUrl>",
    "allowed_updates": ["message"]
  }'

# 驗證 Webhook
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

### Step 5: 測試完整流程

```bash
# 1. 發送測試訊息到 Telegram Bot
# 在 Telegram 中找到您的 Bot 並發送: "Hello"

# 2. 檢查 Adapter Lambda 日誌
aws logs tail /aws/lambda/telegram-adapter-receiver --follow

# 3. 檢查 Processor Lambda 日誌
aws logs tail /aws/lambda/ai-processor-processor --follow

# 4. 檢查 Router Lambda 日誌
aws logs tail /aws/lambda/telegram-adapter-response-router --follow

# 5. 應該在 Telegram 收到 AI 回應
```

---

## 🔍 驗證部署成功

### 檢查點 1: Lambda Functions
```bash
aws lambda list-functions --query "Functions[?contains(FunctionName, 'telegram')].FunctionName"
# 應該看到：
# - telegram-adapter-receiver
# - telegram-adapter-response-router
# - ai-processor-processor
```

### 檢查點 2: EventBridge Rules
```bash
aws events list-rules --event-bus-name telegram-adapter-events
# 應該看到：
# - telegram-adapter-message-received
# - telegram-adapter-message-completed
```

### 檢查點 3: SQS Queues
```bash
aws sqs list-queues --queue-name-prefix telegram
# 應該看到：
# - telegram-inbound
# - telegram-inbound-dlq
```

### 檢查點 4: 訊息流程測試
```
1. 發送訊息到 Bot ✅
2. Receiver Lambda 處理 ✅
3. EventBridge 路由到 Processor ✅
4. Processor 呼叫 Bedrock ✅
5. EventBridge 路由到 Router ✅
6. Router 回傳給用戶 ✅
```

---

## 🐛 常見問題排查

### 問題 1: Bedrock 權限錯誤
```
錯誤: AccessDeniedException
解決: 
1. 前往 AWS Bedrock Console
2. 申請模型訪問權限
3. 等待審核通過（通常幾分鐘）
```

### 問題 2: EventBridge 事件未路由
```bash
# 檢查 EventBridge 規則
aws events describe-rule \
  --name telegram-adapter-message-received \
  --event-bus-name telegram-adapter-events

# 檢查 Target
aws events list-targets-by-rule \
  --rule telegram-adapter-message-received \
  --event-bus-name telegram-adapter-events
```

### 問題 3: Lambda 超時
```
原因: Bedrock 回應時間較長
解決: 已設定 Processor Timeout: 300s (5分鐘)
```

### 問題 4: Router 無法發送訊息
```
原因: 可能是 Secrets Manager 權限
解決: 檢查 ResponseRouterFunction 是否有 secretsmanager:GetSecretValue 權限
```

---

## 📊 監控與日誌

### CloudWatch Logs 查詢

```bash
# Adapter 日誌
aws logs tail /aws/lambda/telegram-adapter-receiver --since 1h

# Processor 日誌
aws logs tail /aws/lambda/ai-processor-processor --since 1h

# Router 日誌
aws logs tail /aws/lambda/telegram-adapter-response-router --since 1h
```

### CloudWatch Insights 查詢

```sql
-- 查看訊息處理流程
fields @timestamp, event_type, message_id, channel, user_id
| filter event_type in ["message_received", "router_success"]
| sort @timestamp desc
| limit 20

-- 查看錯誤
fields @timestamp, event_type, @message
| filter event_type like /error|failed/
| sort @timestamp desc
| limit 20
```

### EventBridge 指標

```bash
# 查看事件數量
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name Invocations \
  --dimensions Name=RuleName,Value=telegram-adapter-message-completed \
  --start-time 2026-01-06T00:00:00Z \
  --end-time 2026-01-06T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

---

## 🔄 更新與回滾

### 更新 Lambda 代碼
```bash
cd telegram-adapter
sam build
sam deploy  # 使用已保存的配置
```

### 回滾到前一版本
```bash
aws lambda update-function-code \
  --function-name telegram-adapter-response-router \
  --s3-bucket <deployment-bucket> \
  --s3-key <previous-version-key>
```

---

## 🗑️ 清理資源（可選）

```bash
# 刪除 Processor Stack
aws cloudformation delete-stack \
  --stack-name ai-processor

# 刪除 Adapter + Router Stack
aws cloudformation delete-stack \
  --stack-name telegram-adapter

# 注意：DynamoDB AllowlistTable 有 DeletionPolicy: Retain
# 需要手動刪除（如果需要）
```

---

## 📈 架構摘要

```
Telegram User
    ↓
📥 API Gateway → Receiver Lambda
    ├─→ EventBridge → message.received
    └─→ SQS (備份)
    ↓
⚙️ Processor Lambda (EventBridge 觸發)
    ├─→ Bedrock API
    └─→ EventBridge → message.completed
    ↓
📤 Router Lambda (EventBridge 觸發)
    ├─→ TelegramFormatter
    ├─→ TelegramDelivery
    └─→ telegram_client.send_message()
    ↓
✅ User receives AI response
```

---

## ✅ 部署檢查清單總結

- [x] 代碼檢查完成
- [x] 依賴驗證通過
- [x] Router 問題已修復 (Commit 4538333)
- [ ] 準備 Telegram Bot Token
- [ ] 選擇 AWS Region
- [ ] 申請 Bedrock 權限
- [ ] 執行 Step 1-5
- [ ] 驗證完整流程

---

**最後更新**: 2026-01-06
**Git Commit**: 4538333
**狀態**: ✅ Ready for Deployment
