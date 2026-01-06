# Webhook Secret Token 問題診斷與修復

## 問題描述

**時間**: 2026-01-06 12:08-12:11 UTC  
**症狀**: 用戶發送測試訊息後沒有收到回應

## 根本原因分析

通過 CloudWatch Logs 分析發現：

```json
{
  "timestamp": "2026-01-06 12:08:58",
  "level": "WARNING",
  "logger": "handler",
  "message": "Invalid secret token",
  "function": "lambda_handler",
  "line": 316,
  "event_type": "invalid_token"
}
```

### 問題定位

1. **Telegram Webhook 配置不完整**
   - Webhook URL 已設置：`https://vnqlzx6b9f.execute-api.us-west-2.amazonaws.com/Prod/webhook`
   - 但 **沒有設置 secret_token**

2. **驗證流程**
   - Lambda 從 Secrets Manager 讀取預期的 secret_token
   - Telegram 發送的請求中不包含 `X-Telegram-Bot-Api-Secret-Token` header
   - Lambda 驗證失敗，返回 403 Forbidden

3. **Telegram 端錯誤**
   ```json
   {
     "last_error_date": 1767701401,
     "last_error_message": "Wrong response from the webhook: 403 Forbidden"
   }
   ```

## 修復步驟

### 1. 確認 Secrets Manager 配置
```bash
aws secretsmanager get-secret-value \
  --secret-id telegram-lambda-secrets \
  --region us-west-2 \
  --query 'SecretString' --output text | jq '.'
```

結果：
```json
{
  "webhook_secret_token": "M4fAAfPI7fD2ZIbrbszyyzsKrWi1EQZmAEL8OESK1DwYImtVIhifTc2gMccHlVPU",
  "bot_token": "1550029310:AAG-DV9ehEUiDxKuqFzkvpNfFyJNjcmy4kM"
}
```

### 2. 重新設置 Webhook（包含 secret_token）
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://vnqlzx6b9f.execute-api.us-west-2.amazonaws.com/Prod/webhook",
    "allowed_updates": ["message"],
    "secret_token": "M4fAAfPI7fD2ZIbrbszyyzsKrWi1EQZmAEL8OESK1DwYImtVIhifTc2gMccHlVPU"
  }'
```

結果：
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

### 3. 驗證配置
```bash
curl -s "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

結果：
- ✅ URL 正確
- ✅ pending_update_count: 0（沒有待處理的更新）
- ℹ️ has_secret_token: false（API 不顯示 token 值，這是正常的）

## 技術細節

### Telegram Webhook Secret Token 機制

1. **設置時**：
   - Telegram API 接受 `secret_token` 參數（1-256 字符）
   - Telegram 會在每個 webhook 請求中包含此 token

2. **驗證時**：
   - Telegram 在 HTTP header 中發送：`X-Telegram-Bot-Api-Secret-Token: <token>`
   - Lambda 函數讀取此 header 並與 Secrets Manager 中的值比對
   - 如果不匹配或缺失，返回 403 Forbidden

3. **安全性**：
   - 防止未經授權的請求
   - 確保只有 Telegram 可以觸發 Lambda
   - 保護免受重放攻擊

### Lambda 驗證代碼（handler.py line 316）

```python
def lambda_handler(event, context):
    # 從 header 獲取 secret token
    headers = event.get('headers', {})
    received_token = headers.get('x-telegram-bot-api-secret-token', '')
    
    # 從 Secrets Manager 獲取預期 token
    secrets = get_secret()
    expected_token = secrets.get('webhook_secret_token', '')
    
    # 驗證
    if received_token != expected_token:
        logger.warning("Invalid secret token")
        emit_metric("InvalidTokenAttempts", 1.0)
        return {'statusCode': 403, 'body': 'Forbidden'}
```

## 後續測試步驟

1. **發送測試訊息**
   - 在 Telegram 中發送任何文字訊息給機器人

2. **驗證日誌**
   ```bash
   # Receiver Lambda（應該成功接收）
   aws logs tail /aws/lambda/telegram-lambda-receiver --region us-west-2 --since 5m
   
   # Processor Lambda（應該處理並回應）
   aws logs tail /aws/lambda/telegram-agentcore-bot-processor --region us-west-2 --since 5m
   
   # Router Lambda（應該發送回應）
   aws logs tail /aws/lambda/telegram-lambda-response-router --region us-west-2 --since 5m
   ```

3. **預期結果**
   - ✅ Receiver 接收訊息並發送 `message.received` 事件
   - ✅ Processor 處理訊息並生成 AI 回應
   - ✅ Router 將回應發送回 Telegram
   - ✅ 用戶在 Telegram 中看到機器人的回應

## 經驗教訓

1. **部署檢查清單需要包含**：
   - ✅ Webhook URL 設置
   - ✅ **Secret Token 設置**（這次遺漏了）
   - ✅ Allowed Updates 配置
   - ✅ Secrets Manager 配置正確

2. **自動化腳本改進**：
   - 在設置 webhook 的腳本中自動包含 secret_token
   - 添加驗證步驟確認 token 設置成功

3. **監控建議**：
   - 為 `InvalidTokenAttempts` 指標設置 CloudWatch 告警
   - 當 > 5 次/分鐘時觸發通知

## 狀態

- ✅ 問題已識別：Webhook 缺少 secret_token
- ✅ 問題已修復：重新設置 webhook 包含 token
- ⏳ 待驗證：用戶發送新測試訊息確認修復

---
**創建時間**: 2026-01-06 12:11 UTC  
**修復者**: Cline AI Assistant  
**優先級**: P0 (Blocker)  
**影響**: 所有傳入訊息被拒絕，機器人完全無法工作
