# Webhook 設定故障排除

## ❌ 遇到的錯誤

```json
{"ok":false,"error_code":404,"description":"Not Found"}
```

## 🔍 錯誤原因

**404 Not Found** 表示 Telegram API 找不到對應的 Bot。這是因為使用了 `YOUR_BOT_TOKEN` 占位符，而不是實際的 Bot Token。

## ✅ 正確的設定步驟

### 步驟 1: 取得您的 Bot Token

您的 Bot Token 應該來自 [@BotFather](https://t.me/BotFather)，格式如下：
```
123456789:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890
```

**如何取得**：
1. 在 Telegram 中找到 @BotFather
2. 發送 `/mybots`
3. 選擇您的 Bot
4. 點擊 "API Token"
5. 複製顯示的 Token

### 步驟 2: 取得 Secret Token

```bash
aws secretsmanager get-secret-value \
  --secret-id telegram-adapter-secret-token \
  --region us-west-2 \
  --query 'SecretString' \
  --output text | jq -r .token
```

這會輸出類似：
```
UqXlcZ3XyBgFlB0a6jaLpKF7fZmO1djEWIJlQAtu4NFbQ8vzapMiJ4TnYhgjmf3A
```

### 步驟 3: 設定 Webhook（使用實際 Token）

**重要**：將 `123456789:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890` 替換為您的實際 Bot Token！

```bash
# 設定變數（方便使用）
BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890"  # 替換為您的實際 Token
SECRET_TOKEN="UqXlcZ3XyBgFlB0a6jaLpKF7fZmO1djEWIJlQAtu4NFbQ8vzapMiJ4TnYhgjmf3A"  # 您已有的值
WEBHOOK_URL="https://19168bj3c7.execute-api.us-west-2.amazonaws.com/Prod/webhook"

# 設定 Webhook
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=${WEBHOOK_URL}" \
  -d "secret_token=${SECRET_TOKEN}"
```

**成功的回應應該是**：
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

### 步驟 4: 驗證 Webhook 設定

```bash
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

**成功的回應範例**：
```json
{
  "ok": true,
  "result": {
    "url": "https://19168bj3c7.execute-api.us-west-2.amazonaws.com/Prod/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "max_connections": 40,
    "ip_address": "xxx.xxx.xxx.xxx"
  }
}
```

## 🔧 其他常見錯誤

### 錯誤 1: 401 Unauthorized
```json
{"ok":false,"error_code":401,"description":"Unauthorized"}
```
**原因**：Bot Token 無效或格式錯誤  
**解決**：檢查 Token 是否完整複製，包含冒號前後的所有字元

### 錯誤 2: 400 Bad Request - Invalid URL
```json
{"ok":false,"error_code":400,"description":"Bad Request: bad webhook: HTTPS url must be provided"}
```
**原因**：Webhook URL 必須是 HTTPS  
**解決**：確認 URL 以 `https://` 開頭

### 錯誤 3: 400 Bad Request - URL validation failed
```json
{"ok":false,"error_code":400,"description":"Bad Request: bad webhook: Failed to resolve host"}
```
**原因**：URL 無法訪問  
**解決**：檢查 API Gateway 是否正確部署

## 🧪 測試流程

### 1. 測試 API Gateway 可訪問性

```bash
curl -X POST https://19168bj3c7.execute-api.us-west-2.amazonaws.com/Prod/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: ${SECRET_TOKEN}" \
  -d '{
    "message": {
      "chat": {"id": 123456},
      "from": {"username": "test"},
      "text": "test"
    }
  }'
```

**預期回應**：
```json
{"status": "ok"}
```
或
```json
{"error": "Unauthorized"}  // 如果不在允許名單中
```

### 2. 設定 Bot Token 環境變數（啟用 /debug test）

```bash
aws lambda update-function-configuration \
  --function-name telegram-adapter-receiver \
  --region us-west-2 \
  --environment Variables="{
    TELEGRAM_SECRET_TOKEN='',
    TELEGRAM_BOT_TOKEN='123456789:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890',
    SQS_QUEUE_URL='https://sqs.us-west-2.amazonaws.com/190825685292/telegram-inbound',
    ALLOWLIST_TABLE_NAME='telegram-allowlist',
    LOG_LEVEL='INFO'
  }"
```

**注意**：這裡也要用實際的 Bot Token！

### 3. 測試 /debug test 功能

在 Telegram 向您的 Bot 發送：
```
/debug test
```

如果設定正確，Bot 會回覆完整的 API Gateway event JSON。

## 📋 檢查清單

完成以下步驟以確保正確設定：

- [ ] 已從 @BotFather 取得實際的 Bot Token
- [ ] Bot Token 格式正確（包含冒號，如 `123456:ABC...`）
- [ ] 已取得 Secret Token（從 Secrets Manager）
- [ ] 使用實際 Token 設定 Webhook（不是占位符）
- [ ] Webhook 設定成功（收到 `"ok": true`）
- [ ] 已驗證 Webhook 狀態（getWebhookInfo）
- [ ] 已在 Lambda 設定 TELEGRAM_BOT_TOKEN 環境變數
- [ ] 已測試發送訊息到 Bot
- [ ] 已測試 /debug test 功能

## 🆘 仍然有問題？

### 檢查 Lambda 日誌
```bash
aws logs tail /aws/lambda/telegram-adapter-receiver \
  --region us-west-2 \
  --follow
```

### 檢查 API Gateway 日誌
前往 AWS Console → API Gateway → telegram-webhook-api → Logs

### 常見問題

**Q: 為什麼要設定兩次 Bot Token？**  
A: 
1. 一次是在 **Telegram Webhook 設定**時（告訴 Telegram 往哪裡發送）
2. 一次是在 **Lambda 環境變數**中（讓 Lambda 能回覆訊息，用於 /debug test）

**Q: Secret Token 和 Bot Token 有什麼不同？**  
A:
- **Bot Token**: 您的 Bot 身份識別，用於呼叫 Telegram API
- **Secret Token**: Webhook 驗證用，確保請求真的來自 Telegram

**Q: /debug test 沒有回應？**  
A: 確認：
1. `TELEGRAM_BOT_TOKEN` 已設定在 Lambda 環境變數
2. Token 格式正確
3. 檢查 Lambda 日誌查看錯誤訊息

## 📞 需要更多協助？

1. 檢視 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. 檢視 [DEBUG_COMMAND.md](DEBUG_COMMAND.md)
3. 查看 Lambda 日誌中的詳細錯誤訊息
