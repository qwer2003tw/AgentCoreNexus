# 部署後必要配置指南

**版本**: 1.0  
**創建日期**: 2026-01-19  
**適用於**: Stack 重建或新部署後

---

## 🎯 目的

此文檔記錄在 CloudFormation Stack 部署後必須手動執行的配置步驟。這些步驟無法完全在 SAM template 中自動化，需要在部署完成後立即執行。

---

## ⚠️ 關鍵問題記錄

### 問題 1: Lambda 環境變數在 Stack 重建後遺失

**現象**：
- Stack 刪除並重建後，某些環境變數被重置為空字符串
- 導致功能失效（例如：無法發送回覆事件）

**根本原因**：
- CloudFormation 的 `AWS::Serverless::Function` 在某些情況下會覆蓋環境變數
- 跨 Stack 引用（ImportValue）可能在部署順序不當時導致環境變數為空

**受影響的環境變數**：
1. `EVENT_BUS_NAME` - Processor 必須用它發送回覆事件
2. `BEDROCK_AGENTCORE_MEMORY_ID` - Memory 功能需要

---

## 📋 必須執行的配置步驟

### Step 1: 驗證 Stack 部署狀態

```bash
# 檢查所有 Stack 狀態
aws cloudformation describe-stacks --region us-west-2 \
  --query 'Stacks[?contains(StackName, `agentcore`)].{Name:StackName,Status:StackStatus}' \
  --output table
```

**預期輸出**：
- agentcore-telegram-adapter: `CREATE_COMPLETE` 或 `UPDATE_COMPLETE`
- agentcore-ai-processor: `CREATE_COMPLETE` 或 `UPDATE_COMPLETE`

---

### Step 2: 獲取必要的配置值

#### 2.1 獲取 EventBus 名稱

```bash
EVENT_BUS_NAME=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-telegram-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`EventBusName`].OutputValue' \
  --output text)

echo "EVENT_BUS_NAME: $EVENT_BUS_NAME"
```

**預期值**: `agentcore-telegram-adapter-events`

#### 2.2 獲取 Memory ID

```bash
# 從文件讀取
MEMORY_ID=$(cat ai-processor/MEMORY_ID.txt)
echo "MEMORY_ID: $MEMORY_ID"
```

**預期格式**: `TelegramBotMemory-XXXXXXXXXX`

#### 2.3 獲取其他配置

```bash
# File Storage Bucket（從 Telegram Stack）
FILE_BUCKET=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-telegram-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`FileStorageBucket`].OutputValue' \
  --output text)

echo "FILE_BUCKET: $FILE_BUCKET"
```

---

### Step 3: 驗證當前 Lambda 配置

```bash
# 檢查 Processor Lambda 環境變數
aws lambda get-function-configuration \
  --region us-west-2 \
  --function-name agentcore-ai-processor-main \
  --query 'Environment.Variables' \
  --output json | jq .
```

**檢查清單**：
- [ ] `EVENT_BUS_NAME` 不是空字符串
- [ ] `BEDROCK_AGENTCORE_MEMORY_ID` 不是空字符串
- [ ] `FILE_STORAGE_BUCKET` 正確
- [ ] `BROWSER_ENABLED` = "true"
- [ ] `FILE_ENABLED` = "true"
- [ ] `BEDROCK_MODEL_ID` = "anthropic.claude-3-5-sonnet-20241022-v2:0"

---

### Step 4: 更新 Processor Lambda 環境變數（如需要）

如果 Step 3 發現環境變數不正確，執行以下命令：

```bash
aws lambda update-function-configuration \
  --region us-west-2 \
  --function-name agentcore-ai-processor-main \
  --environment "Variables={
    EVENT_BUS_NAME=$EVENT_BUS_NAME,
    BEDROCK_AGENTCORE_MEMORY_ID=$MEMORY_ID,
    FILE_STORAGE_BUCKET=$FILE_BUCKET,
    FILE_ENABLED=true,
    BROWSER_ENABLED=true,
    BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0,
    LOG_LEVEL=INFO
  }"

# 等待更新完成
aws lambda wait function-updated \
  --region us-west-2 \
  --function-name agentcore-ai-processor-main

# 驗證更新
aws lambda get-function-configuration \
  --region us-west-2 \
  --function-name agentcore-ai-processor-main \
  --query '{State: State, LastUpdateStatus: LastUpdateStatus}' \
  --output json
```

**預期結果**：
```json
{
    "State": "Active",
    "LastUpdateStatus": "Successful"
}
```

---

### Step 5: 更新 Telegram Bot Token（如需要）

```bash
# 獲取 Secrets Manager ARN
SECRETS_ARN=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-telegram-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`TelegramSecretsArn`].OutputValue' \
  --output text)

# 更新 secret（替換為實際的 token）
aws secretsmanager update-secret \
  --region us-west-2 \
  --secret-id "$SECRETS_ARN" \
  --secret-string '{
    "bot_token": "YOUR_BOT_TOKEN_HERE",
    "webhook_secret_token": "YOUR_WEBHOOK_SECRET_HERE"
  }'
```

---

### Step 6: 設置 Telegram Webhook

```bash
# 獲取 Webhook URL
WEBHOOK_URL=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-telegram-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' \
  --output text)

# 獲取 Bot Token 和 Webhook Secret
BOT_TOKEN=$(aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id "$SECRETS_ARN" \
  --query SecretString --output text | jq -r .bot_token)

WEBHOOK_SECRET=$(aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id "$SECRETS_ARN" \
  --query SecretString --output text | jq -r .webhook_secret_token)

# 設置 webhook
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${WEBHOOK_URL}\",
    \"secret_token\": \"${WEBHOOK_SECRET}\"
  }"
```

**預期回應**：
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

---

### Step 7: 驗證 Webhook 狀態

```bash
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo" | jq .
```

**檢查項目**：
- [ ] `url` 正確（應該是 API Gateway URL）
- [ ] `has_custom_certificate` = false
- [ ] `pending_update_count` = 0
- [ ] `last_error_date` 不存在或很舊

---

## 🧪 功能測試

### Test 1: 簡單消息測試

在 Telegram 發送：`你好`

**預期**：Bot 在 5-10 秒內回覆

### Test 2: /info 命令測試

在 Telegram 發送：`/info`

**預期**：Bot 立即回覆系統信息

### Test 3: Memory 測試

1. 發送：`請記住我的名字是 Alice`
2. 發送：`我叫什麼名字？`

**預期**：Bot 回答 "Alice" 或類似內容

### Test 4: Browser 功能測試

發送：`幫我搜尋最新的新聞`

**預期**：Bot 使用瀏覽器工具並回覆搜尋結果

---

## 🔍 診斷問題

### 問題：Bot 不回覆消息

**診斷步驟**：

1. 檢查 Receiver Lambda 日誌：
```bash
aws logs tail /aws/lambda/agentcore-telegram-adapter-receiver \
  --region us-west-2 --since 5m
```

2. 檢查 Processor Lambda 日誌：
```bash
aws logs tail /aws/lambda/agentcore-ai-processor-main \
  --region us-west-2 --since 5m
```

3. 檢查 Response Router 日誌：
```bash
aws logs tail /aws/lambda/agentcore-telegram-adapter-router \
  --region us-west-2 --since 5m
```

**常見原因**：
- ❌ `EVENT_BUS_NAME` 為空 → Processor 無法發送回覆事件
- ❌ EventBridge Rule 沒有 Target → 消息無法路由
- ❌ Lambda Permission 缺失 → EventBridge 無法調用 Lambda

---

### 問題：Memory 功能不工作

**診斷步驟**：

1. 檢查 MEMORY_ID 環境變數：
```bash
aws lambda get-function-configuration \
  --region us-west-2 \
  --function-name agentcore-ai-processor-main \
  --query 'Environment.Variables.BEDROCK_AGENTCORE_MEMORY_ID' \
  --output text
```

2. 檢查日誌中的 Memory 錯誤：
```bash
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/agentcore-ai-processor-main \
  --filter-pattern "Memory\|Session" \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

**常見原因**：
- ❌ `BEDROCK_AGENTCORE_MEMORY_ID` 為空
- ❌ Memory 不存在或已刪除
- ❌ IAM 權限不足

---

### 問題：Browser 功能失敗

**檢查日誌**：
```bash
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/agentcore-ai-processor-main \
  --filter-pattern "browser\|Browser" \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

**常見錯誤**：
- ❌ `No module named 'playwright'` → 預期行為，會自動切換到備用瀏覽器
- ❌ Browser sandbox 權限錯誤 → 檢查 IAM 權限

---

## 📝 完整檢查清單（部署後）

### Telegram Adapter Stack
- [ ] Stack 狀態：CREATE_COMPLETE 或 UPDATE_COMPLETE
- [ ] EventBus 已創建
- [ ] EventBridge Rules 有 Targets
- [ ] Secrets Manager 包含 bot_token 和 webhook_secret_token
- [ ] Receiver Lambda 狀態：Active
- [ ] Response Router Lambda 狀態：Active
- [ ] API Gateway 可訪問

### AI Processor Stack
- [ ] Stack 狀態：CREATE_COMPLETE 或 UPDATE_COMPLETE
- [ ] Processor Lambda 狀態：Active
- [ ] 環境變數：EVENT_BUS_NAME 正確
- [ ] 環境變數：BEDROCK_AGENTCORE_MEMORY_ID 正確
- [ ] 環境變數：FILE_STORAGE_BUCKET 正確
- [ ] IAM 權限包含 EventBridge、Bedrock、S3、Browser sandbox

### Webhook 配置
- [ ] Webhook URL 已設置
- [ ] Webhook secret 已配置
- [ ] pending_update_count = 0
- [ ] 沒有 last_error

### 功能測試
- [ ] 簡單消息回覆正常
- [ ] /info 命令正常
- [ ] Memory 功能正常
- [ ] Browser 功能正常

---

## 🚨 緊急修復腳本

如果部署後發現問題，使用此腳本快速修復：

```bash
#!/bin/bash
# 快速修復部署後配置問題

set -e

echo "🔧 開始修復配置..."

# 1. 獲取必要值
EVENT_BUS_NAME=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-telegram-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`EventBusName`].OutputValue' \
  --output text)

MEMORY_ID=$(cat ai-processor/MEMORY_ID.txt)

FILE_BUCKET=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-telegram-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`FileStorageBucket`].OutputValue' \
  --output text)

echo "✅ 配置值獲取完成"
echo "   EVENT_BUS_NAME: $EVENT_BUS_NAME"
echo "   MEMORY_ID: $MEMORY_ID"
echo "   FILE_BUCKET: $FILE_BUCKET"

# 2. 更新 Processor Lambda
echo "🔄 更新 Processor Lambda..."
aws lambda update-function-configuration \
  --region us-west-2 \
  --function-name agentcore-ai-processor-main \
  --environment "Variables={
    EVENT_BUS_NAME=$EVENT_BUS_NAME,
    BEDROCK_AGENTCORE_MEMORY_ID=$MEMORY_ID,
    FILE_STORAGE_BUCKET=$FILE_BUCKET,
    FILE_ENABLED=true,
    BROWSER_ENABLED=true,
    BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0,
    LOG_LEVEL=INFO
  }" > /dev/null

# 3. 等待更新
echo "⏳ 等待 Lambda 更新完成..."
aws lambda wait function-updated \
  --region us-west-2 \
  --function-name agentcore-ai-processor-main

echo "✅ 配置修復完成！"
echo ""
echo "請執行測試驗證功能："
echo "1. 在 Telegram 發送測試消息"
echo "2. 檢查 Bot 是否回覆"
```

---

## 📚 相關文檔

- [部署指南](./deployment-guide.md)
- [Stack 管理](./STACK_MANAGEMENT.md)
- [故障排除](./../.clinerules/deployment/aws-lambda-telegram-bot-deployment-issues.md)

---

**文檔版本**: 1.0  
**最後更新**: 2026-01-19  
**維護者**: AgentCoreNexus Team