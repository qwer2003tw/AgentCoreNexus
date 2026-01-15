# 部署完成 - 後續配置步驟

## ✅ 部署狀態
專案已成功部署到 AWS！

## 📋 部署資訊

### API Gateway
- **Webhook URL**: `https://19168bj3c7.execute-api.us-west-2.amazonaws.com/Prod/webhook`

### Lambda Function
- **名稱**: `telegram-lambda-receiver`
- **ARN**: `arn:aws:lambda:us-west-2:190825685292:function:telegram-lambda-receiver`

### 其他資源
- **SQS Queue**: `https://sqs.us-west-2.amazonaws.com/190825685292/telegram-inbound`
- **DynamoDB Table**: `telegram-allowlist`
- **Region**: `us-west-2`

## 🔧 必要的後續配置

### 1. 設定 Telegram Bot Token（用於 /debug test 功能）

**使用 AWS CLI**：
```bash
# 取得當前環境變數
aws lambda get-function-configuration \
  --function-name telegram-lambda-receiver \
  --region us-west-2 \
  --query 'Environment.Variables'

# 更新環境變數（將 YOUR_BOT_TOKEN 替換為實際 token）
aws lambda update-function-configuration \
  --function-name telegram-lambda-receiver \
  --region us-west-2 \
  --environment Variables="{
    TELEGRAM_SECRET_TOKEN='',
    TELEGRAM_BOT_TOKEN='YOUR_BOT_TOKEN',
    SQS_QUEUE_URL='https://sqs.us-west-2.amazonaws.com/190825685292/telegram-inbound',
    ALLOWLIST_TABLE_NAME='telegram-allowlist',
    LOG_LEVEL='INFO'
  }"
```

**或使用 AWS Console**：
1. 前往 Lambda 控制台
2. 選擇 `telegram-lambda-receiver`
3. Configuration → Environment variables → Edit
4. 設定 `TELEGRAM_BOT_TOKEN` = 您的 Bot Token
5. Save

### 2. 設定 Telegram Webhook

**取得 Secret Token**：
```bash
aws secretsmanager get-secret-value \
  --secret-id telegram-lambda-secret-token \
  --region us-west-2 \
  --query 'SecretString' \
  --output text | jq -r .token
```

**設定 Webhook**（將 YOUR_BOT_TOKEN 和 YOUR_SECRET_TOKEN 替換）：
```bash
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook" \
  -d "url=https://19168bj3c7.execute-api.us-west-2.amazonaws.com/Prod/webhook" \
  -d "secret_token=YOUR_SECRET_TOKEN"
```

**驗證 Webhook**：
```bash
curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo"
```

### 3. 設定允許名單

新增允許的用戶到 DynamoDB：
```bash
aws dynamodb put-item \
  --table-name telegram-allowlist \
  --region us-west-2 \
  --item '{
    "chat_id": {"N": "YOUR_CHAT_ID"},
    "username": {"S": "your_username"},
    "enabled": {"BOOL": true}
  }'
```

## 🧪 測試 /debug test 功能

設定完 Bot Token 後：

1. 在 Telegram 向您的 Bot 發送：
   ```
   /debug test
   ```

2. Bot 應該回覆完整的 API Gateway event JSON

3. 如果沒有回應，檢查日誌：
   ```bash
   aws logs tail /aws/lambda/telegram-lambda-receiver \
     --region us-west-2 \
     --follow
   ```

## 📊 監控和日誌

### 查看 Lambda 日誌
```bash
aws logs tail /aws/lambda/telegram-lambda-receiver \
  --region us-west-2 \
  --follow
```

### 查看 SQS 佇列狀態
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-west-2.amazonaws.com/190825685292/telegram-inbound \
  --region us-west-2 \
  --attribute-names All
```

### 查看 CloudWatch Metrics
前往 AWS Console → CloudWatch → Metrics → Lambda

## ⚠️ 重要提醒

1. **Bot Token 安全**：
   - 不要將 Bot Token 提交到版本控制
   - 定期輪換 token
   
2. **除錯功能**：
   - `/debug test` 目前為完全放行
   - 建議僅在開發/測試環境使用
   - 生產環境應加上允許名單限制

3. **成本控制**：
   - 監控 Lambda 執行次數
   - 設定 CloudWatch Alarms
   - 定期檢視 AWS 帳單

## 🔄 重新部署

如需更新程式碼：
```bash
cd /home/ec2-user/telegram-lambda
sam build
sam deploy
```

## 📚 相關文件

- [README.md](README.md) - 專案主文件
- [DEBUG_COMMAND.md](DEBUG_COMMAND.md) - 除錯功能說明
- [CHANGELOG_DEBUG_FEATURE.md](CHANGELOG_DEBUG_FEATURE.md) - 變更日誌

## 🆘 故障排除

### Lambda 無回應
```bash
# 檢查 Lambda 狀態
aws lambda get-function \
  --function-name telegram-lambda-receiver \
  --region us-west-2

# 檢查最近的錯誤
aws logs filter-log-events \
  --log-group-name /aws/lambda/telegram-lambda-receiver \
  --region us-west-2 \
  --filter-pattern "ERROR"
```

### Webhook 設定失敗
- 確認 Bot Token 正確
- 確認 Webhook URL 可訪問
- 檢查 Secret Token 是否正確

### /debug test 無回應
- 確認 `TELEGRAM_BOT_TOKEN` 已設定
- 檢查 Lambda 日誌中的錯誤訊息
- 確認 Bot 有權限發送訊息

## ✅ 完成檢查清單

- [ ] 已設定 `TELEGRAM_BOT_TOKEN` 環境變數
- [ ] 已取得 Secret Token
- [ ] 已設定 Telegram Webhook
- [ ] 已驗證 Webhook 設定成功
- [ ] 已新增至少一個用戶到允許名單
- [ ] 已測試 `/debug test` 功能
- [ ] 已測試正常訊息流程
- [ ] 已設定 CloudWatch Alarms
- [ ] 已檢視初始日誌確認無錯誤
