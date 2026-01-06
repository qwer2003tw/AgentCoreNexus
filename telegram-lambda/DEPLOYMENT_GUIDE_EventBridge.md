# AgentCore Nexus - EventBridge 整合部署指南

本指南說明如何部署已完成的 EventBridge 多通道架構。

## 📋 部署前檢查

### 已完成的開發工作 ✅

**telegram-lambda (Universal Message Adapter)**
- ✅ EventBridge 事件匯流排（UniversalEventBus）
- ✅ 通道檢測邏輯（detect_channel）
- ✅ 訊息標準化（Universal Message Schema）
- ✅ EventBridge 發布功能
- ✅ 雙軌運行（EventBridge + SQS）
- 📦 Commits: b46c0c7, 415ff15

**telegram-agentcore-bot (Agent Processor)**
- ✅ EventBridge 事件處理器（processor_entry.py）
- ✅ 標準化訊息處理
- ✅ SQS 向後兼容
- ✅ 完成/失敗事件發布
- ✅ SAM 部署模板
- 📦 Commits: 0fb409e, 74c176e

### 當前架構

```
┌─────────────┐
│  Telegram   │
└──────┬──────┘
       │ HTTPS Webhook
       ▼
┌──────────────────────────────────┐
│ Universal Message Adapter        │ ← telegram-lambda
│ - API Gateway                    │   Stack 1
│ - Lambda (通道檢測/標準化)         │
│ - EventBridge 發布                │
└──┬───────────────────────────┬───┘
   │ EventBridge              │ SQS
   │ message.received         │ (backup)
   ▼                          ▼
┌──────────────────────┐   ┌──────────┐
│ Agent Processor      │   │ Legacy   │
│ - EventBridge Handler│   │ Processor│
│ - AgentCore 整合      │   └──────────┘
│ - message.completed  │
└──────────────────────┘
     (Stack 2)
```

## 🚀 部署步驟

### 步驟 1: 部署 Adapter (telegram-lambda)

```bash
cd /home/ec2-user/Projects/AgentCoreNexus/telegram-lambda

# 構建並部署
sam build
sam deploy \
  --stack-name telegram-lambda-dev \
  --parameter-overrides TelegramBotToken="YOUR_BOT_TOKEN" \
  --capabilities CAPABILITY_IAM \
  --region us-west-2 \
  --resolve-s3

# 記錄輸出的 EventBus 資訊
aws cloudformation describe-stacks \
  --stack-name telegram-lambda-dev \
  --query 'Stacks[0].Outputs' \
  --output table
```

**重要輸出**：
- `EventBusName`: 用於 Processor 部署
- `EventBusArn`: 用於 Processor 部署
- `WebhookUrl`: 用於設置 Telegram webhook

### 步驟 2: 部署 Processor (telegram-agentcore-bot)

```bash
cd /home/ec2-user/Projects/AgentCoreNexus/telegram-agentcore-bot

# 使用 Step 1 的輸出值
EVENT_BUS_NAME="telegram-lambda-dev-events"
EVENT_BUS_ARN="arn:aws:events:us-west-2:ACCOUNT_ID:event-bus/telegram-lambda-dev-events"

# 構建並部署
sam build
sam deploy \
  --stack-name telegram-processor-dev \
  --parameter-overrides \
      EventBusName="$EVENT_BUS_NAME" \
      EventBusArn="$EVENT_BUS_ARN" \
      BedrockModelId="anthropic.claude-3-5-sonnet-20241022-v2:0" \
  --capabilities CAPABILITY_IAM \
  --region us-west-2 \
  --resolve-s3

# 記錄 Processor ARN
PROCESSOR_ARN=$(aws cloudformation describe-stacks \
  --stack-name telegram-processor-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ProcessorFunctionArn`].OutputValue' \
  --output text)

echo "Processor ARN: $PROCESSOR_ARN"
```

### 步驟 3: 連接 EventBridge Rule 與 Processor

```bash
# 取得 Rule 名稱
RULE_NAME="telegram-lambda-dev-message-received"

# 為 Rule 添加 Processor 作為目標
aws events put-targets \
  --rule $RULE_NAME \
  --event-bus-name $EVENT_BUS_NAME \
  --targets \
    "Id"="AgentProcessor","Arn"="$PROCESSOR_ARN"

# 驗證配置
aws events list-targets-by-rule \
  --rule $RULE_NAME \
  --event-bus-name $EVENT_BUS_NAME
```

### 步驟 4: 設置 Telegram Webhook

```bash
# 取得 Webhook URL
WEBHOOK_URL=$(aws cloudformation describe-stacks \
  --stack-name telegram-lambda-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' \
  --output text)

# 取得 Bot Token
BOT_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id telegram-lambda-dev-secrets \
  --query SecretString \
  --output text | jq -r .bot_token)

# 設置 webhook
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${WEBHOOK_URL}\"}"
```

## 🧪 測試驗證

### 1. 測試 Adapter 功能

發送訊息到 Telegram bot，檢查 CloudWatch：

```bash
# 查看 Adapter Lambda 日誌
aws logs tail /aws/lambda/telegram-lambda-receiver --follow

# 檢查關鍵日誌：
# - "Detected channel: telegram"
# - "Message normalized: <uuid>"
# - "Message sent to EventBridge"
# - "Message processed successfully"
```

### 2. 測試 EventBridge 事件流

```bash
# 查看 EventBridge 指標
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name Invocations \
  --dimensions Name=RuleName,Value=telegram-lambda-dev-message-received \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### 3. 測試 Processor 功能

```bash
# 查看 Processor Lambda 日誌
aws logs tail /aws/lambda/telegram-processor-dev-processor --follow

# 檢查關鍵日誌：
# - "Processing EventBridge event"
# - "Processing text message from <user>"
# - "Message processed successfully"
# - "Completion event published"
```

### 4. 端到端測試

1. 向 Telegram bot 發送測試訊息
2. 檢查 Adapter 日誌確認接收
3. 檢查 EventBridge 指標確認路由
4. 檢查 Processor 日誌確認處理
5. 確認 message.completed 事件發布

## 📊 監控與除錯

### CloudWatch Insights 查詢

**查看事件流**:
```
fields @timestamp, @message
| filter @message like /eventbridge/
| sort @timestamp desc
| limit 20
```

**查看標準化訊息**:
```
fields @timestamp, message_id, channel
| filter event_type = "eventbridge_publish"
| sort @timestamp desc
```

**查看處理結果**:
```
fields @timestamp, user_id, @message
| filter @message like /processed successfully/
| sort @timestamp desc
```

### 常見問題排查

**問題 1: EventBridge 無事件**
- 檢查 Lambda 是否有 events:PutEvents 權限
- 確認 EVENT_BUS_NAME 環境變數正確設置
- 查看 Adapter Lambda 日誌

**問題 2: Processor 未觸發**
- 確認 EventBridge Rule 有正確的 Target
- 檢查 Lambda 執行權限
- 驗證 Event Pattern 匹配

**問題 3: SQS 路徑正常但 EventBridge 失敗**
- 這是預期的漸進式遷移狀態
- EventBridge 路徑獨立，不影響 SQS
- 可以逐步除錯和優化

## 🔄 回滾方案

如需回滾到整合前狀態：

```bash
# telegram-lambda
cd /home/ec2-user/Projects/AgentCoreNexus/telegram-lambda
git checkout backup-before-eventbridge-integration
sam deploy --stack-name telegram-lambda-dev

# telegram-agentcore-bot  
cd /home/ec2-user/Projects/AgentCoreNexus/telegram-agentcore-bot
git checkout backup-before-eventbridge-integration
# 刪除新部署的 Processor stack
aws cloudformation delete-stack --stack-name telegram-processor-dev
```

## 📈 成本估算

**新增成本**：
- EventBridge: ~$1 per million events
- Processor Lambda: 按執行時間計費
- CloudWatch Logs: 標準費率

**預估**：每月 1000 則訊息約 $0.01-0.05

## ✅ 部署檢查清單

- [ ] telegram-lambda 部署成功
- [ ] EventBridge 事件匯流排已建立
- [ ] telegram-agentcore-bot Processor 部署成功
- [ ] EventBridge Rule Target 已設定
- [ ] Telegram webhook 已更新
- [ ] 測試訊息成功流轉
- [ ] CloudWatch 日誌正常
- [ ] SQS 備援路徑仍可運作

## 🎯 下一步：Phase 4 Response Router

完成 Phase 3 後，可以開始實作：
- Response Router Lambda
- 通道特定格式化
- message.completed → 通道回送邏輯

## 📞 支援

如有問題，請檢查：
1. CloudWatch Logs: `/aws/lambda/telegram-lambda-receiver` 和 `/aws/lambda/telegram-processor-dev-processor`
2. EventBridge 規則狀態和目標配置
3. IAM 權限設定
4. 環境變數配置

---

**版本**: Phase 3 完成版
**日期**: 2026-01-06
**分支**: feature/eventbridge-integration
