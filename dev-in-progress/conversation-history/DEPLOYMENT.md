# 對話紀錄系統部署指南

## 📋 部署順序

### 前置條件
- ✅ AWS CLI 已配置
- ✅ SAM CLI 已安裝
- ✅ Python 3.11 環境
- ✅ 已有 agentcore-telegram-adapter 和 agentcore-ai-processor stacks

---

## Step 1: 部署對話儲存基礎設施

### 1.1 驗證 Template
```bash
cd infrastructure
sam validate -t conversation-storage.yaml
```

### 1.2 部署 DynamoDB Tables
```bash
./deploy-conversation-storage.sh
```

或手動：
```bash
sam deploy \
  --template-file conversation-storage.yaml \
  --stack-name agentcore-conversation-storage \
  --region us-west-2 \
  --parameter-overrides Environment=prod \
  --capabilities CAPABILITY_IAM \
  --resolve-s3
```

### 1.3 驗證部署
```bash
# 檢查 stack 狀態
aws cloudformation describe-stacks \
  --stack-name agentcore-conversation-storage \
  --region us-west-2 \
  --query 'Stacks[0].StackStatus'

# 應該看到：CREATE_COMPLETE 或 UPDATE_COMPLETE

# 列出創建的表
aws dynamodb list-tables --region us-west-2 | grep conversation
```

**預期看到**：
- agentcore-conversation-history-prod
- agentcore-conversation-metadata-prod
- agentcore-identity-map-prod

---

## Step 2: 建立 Lambda Layer（共享 conversation_service）

### 2.1 建立 Layer
```bash
cd infrastructure/layers
./build-layer.sh
```

### 2.2 打包 Layer
```bash
cd conversation-layer
zip -r ../conversation-layer.zip python/
cd ..
```

### 2.3 發布 Layer
```bash
aws lambda publish-layer-version \
  --layer-name agentcore-conversation-service \
  --description "Shared conversation storage service" \
  --zip-file fileb://conversation-layer.zip \
  --compatible-runtimes python3.11 \
  --region us-west-2
```

**記下 LayerVersionArn**，稍後需要添加到 Lambda functions。

---

## Step 3: 更新現有 Lambda Functions

### 3.1 添加 Layer 到 Telegram Adapter

```bash
# 取得 Layer ARN
LAYER_ARN=$(aws lambda list-layer-versions \
  --layer-name agentcore-conversation-service \
  --region us-west-2 \
  --query 'LayerVersions[0].LayerVersionArn' \
  --output text)

# 添加到 Telegram receiver
aws lambda update-function-configuration \
  --function-name agentcore-telegram-adapter-receiver \
  --layers "$LAYER_ARN" \
  --region us-west-2
```

### 3.2 添加 Layer 到 AI Processor

```bash
aws lambda update-function-configuration \
  --function-name agentcore-ai-processor-main \
  --layers "$LAYER_ARN" \
  --region us-west-2
```

### 3.3 添加 Layer 到 Web Adapter（如果已部署）

```bash
aws lambda update-function-configuration \
  --function-name agentcore-web-adapter-history \
  --layers "$LAYER_ARN" \
  --region us-west-2
```

---

## Step 4: 重新部署更新的 Lambdas

### 4.1 部署 Telegram Adapter

```bash
cd telegram-adapter
sam build
sam deploy \
  --stack-name agentcore-telegram-adapter \
  --region us-west-2 \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --no-confirm-changeset
```

### 4.2 部署 AI Processor

```bash
cd ai-processor
sam build
sam deploy \
  --stack-name agentcore-ai-processor \
  --region us-west-2 \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --no-confirm-changeset
```

---

## Step 5: 驗證功能

### 5.1 檢查環境變數

```bash
# Telegram Receiver
aws lambda get-function-configuration \
  --function-name agentcore-telegram-adapter-receiver \
  --region us-west-2 \
  --query 'Environment.Variables' | grep CONVERSATION

# AI Processor
aws lambda get-function-configuration \
  --function-name agentcore-ai-processor-main \
  --region us-west-2 \
  --query 'Environment.Variables' | grep CONVERSATION
```

**預期看到**：
```json
{
  "CONVERSATION_HISTORY_TABLE": "agentcore-conversation-history-prod",
  "CONVERSATION_METADATA_TABLE": "agentcore-conversation-metadata-prod"
}
```

### 5.2 測試訊息儲存

發送測試訊息到 Telegram bot：
```
你好，這是測試
```

### 5.3 檢查 DynamoDB

```bash
# 查詢對話歷史
aws dynamodb query \
  --table-name agentcore-conversation-history-prod \
  --key-condition-expression "conversation_id = :id" \
  --expression-attribute-values '{":id":{"S":"tg:YOUR_CHAT_ID"}}' \
  --region us-west-2
```

### 5.4 檢查日誌

```bash
# Telegram receiver 日誌
aws logs tail /aws/lambda/agentcore-telegram-adapter-receiver \
  --region us-west-2 \
  --since 5m \
  --follow

# 尋找：
# ✅ "ConversationService initialized"
# ✅ "Message saved to conversation history"

# AI processor 日誌
aws logs tail /aws/lambda/agentcore-ai-processor-main \
  --region us-west-2 \
  --since 5m \
  --follow

# 尋找：
# ✅ "Loaded group context for conversation"
# ✅ "AI response saved to conversation history"
```

---

## 故障排除

### 問題 1: ConversationService 初始化失敗

**症狀**：日誌顯示 "Conversation storage not configured"

**檢查**：
```bash
# 1. 環境變數是否設定？
aws lambda get-function-configuration \
  --function-name FUNCTION_NAME \
  --query 'Environment.Variables'

# 2. Lambda Layer 是否附加？
aws lambda get-function-configuration \
  --function-name FUNCTION_NAME \
  --query 'Layers'
```

**解決**：
- 確認環境變數已設定
- 確認 Layer 已附加

### 問題 2: DynamoDB 權限錯誤

**症狀**：`AccessDeniedException: User is not authorized to perform: dynamodb:PutItem`

**解決**：
```bash
# 檢查 IAM policy
aws lambda get-function \
  --function-name FUNCTION_NAME \
  --query 'Configuration.Role'

# 確認 policy 包含 DynamoDB 權限
```

### 問題 3: 訊息沒有儲存

**檢查**：
```bash
# 1. 功能是否啟用？
aws logs filter-log-events \
  --log-group-name /aws/lambda/agentcore-telegram-adapter-receiver \
  --filter-pattern "conversation history" \
  --region us-west-2

# 2. 是否有錯誤？
aws logs filter-log-events \
  --log-group-name /aws/lambda/agentcore-telegram-adapter-receiver \
  --filter-pattern "Failed to save conversation" \
  --region us-west-2
```

---

## 回滾計劃

如果需要回滾：

### 1. 停用對話記錄功能

```bash
# 移除環境變數
aws lambda update-function-configuration \
  --function-name agentcore-telegram-adapter-receiver \
  --environment Variables={} \
  --region us-west-2
```

### 2. 保留 DynamoDB Tables

**重要**：不要刪除 tables！資料很寶貴。

如果確實需要刪除：
```bash
aws cloudformation delete-stack \
  --stack-name agentcore-conversation-storage \
  --region us-west-2
```

---

## 成本估算

**DynamoDB（PAY_PER_REQUEST）**：
- 讀取：$0.25/百萬請求
- 寫入：$1.25/百萬請求
- 儲存：$0.25/GB
- PITR：~$1/月

**預估月成本**：
- 1000 訊息/天 = 60K 寫入/月
- 讀取：~10K/月
- 儲存：~100MB
- **總計：~$2-3/月**

---

## 監控建議

### CloudWatch Alarms

```bash
# 寫入失敗告警
aws cloudwatch put-metric-alarm \
  --alarm-name conversation-write-failures \
  --alarm-description "Alert on conversation write failures" \
  --metric-name UserErrors \
  --namespace AWS/DynamoDB \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=TableName,Value=agentcore-conversation-history-prod
```

### 關鍵指標

監控這些指標：
- DynamoDB 寫入成功率
- 查詢延遲（p95 < 50ms）
- Lambda 錯誤率（< 1%）
- 儲存容量增長

---

## 下一步

Phase 1 完成後：
- ✅ 所有對話永久保留
- ✅ 群組對話完整上下文
- ✅ Web 對話查詢和刪除

Phase 2 計劃：
- [ ] identity_map 表整合
- [ ] 跨通道綁定功能
- [ ] 進階查詢和過濾

Phase 3 計劃：
- [ ] 用戶行為統計
- [ ] 對話品質分析
- [ ] 監控 Dashboard