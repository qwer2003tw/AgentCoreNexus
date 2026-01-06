# `/debug test` 指令使用說明

## 概述

這個除錯指令讓您可以查看 Lambda 收到的完整 API Gateway event，方便開發和故障排除。

## 快速開始

### 1. 設定 Bot Token

使用 AWS CLI 更新 Lambda 環境變數：

```bash
aws lambda update-function-configuration \
  --function-name telegram-lambda-receiver \
  --environment Variables="{
    TELEGRAM_SECRET_TOKEN='',
    TELEGRAM_BOT_TOKEN='YOUR_BOT_TOKEN_HERE',
    SQS_QUEUE_URL='YOUR_QUEUE_URL',
    ALLOWLIST_TABLE_NAME='telegram-allowlist',
    LOG_LEVEL='INFO'
  }"
```

將 `YOUR_BOT_TOKEN_HERE` 替換為您的實際 Bot Token。

### 2. 使用指令

在 Telegram 中向您的 Bot 發送任何 `/debug` 開頭的指令：

```
/debug
/debug test
/debug 123
/debug any string
```

### 3. 查看結果

Bot 會回覆完整的 API Gateway event JSON，包含：
- HTTP Headers
- Request Body  
- API Gateway 配置
- 請求路徑和參數

## 功能特性

✅ **靈活指令**：支援 `/debug` 單獨或任何 `/debug` 開頭的指令  
✅ **自動分段**：如果內容超過 4096 字元（Telegram 限制），會自動分成多則訊息  
✅ **JSON 格式化**：使用 Markdown 代碼塊美化顯示  
✅ **完全放行**：任何用戶都可以使用（請注意安全性）  
✅ **非阻塞**：除錯功能不影響正常訊息處理

## 安全注意事項

⚠️ **警告**：當前實作為完全放行，任何人都可以使用此指令。

**建議做法**：
- 僅在開發/測試環境使用
- 生產環境應該移除或加上允許名單限制
- 檢查回傳的內容，確保沒有洩漏敏感資訊

## 技術實作

### 檔案結構

```
src/
├── telegram_client.py    # 新增：Telegram API 客戶端
└── handler.py           # 修改：新增 /debug test 檢測邏輯
```

### 處理流程

```
接收 webhook 
  → 驗證 chat_id 存在
  → 檢測 /debug test 指令
  → 格式化 event 為 JSON
  → 呼叫 Telegram sendMessage API
  → 回應 200 OK
```

### 關鍵函數

- `send_debug_info(chat_id, event)` - 發送除錯資訊
- `send_message(chat_id, text)` - 發送 Telegram 訊息
- `_split_message(text, max_length)` - 分割長訊息

## 測試

執行測試：

```bash
pytest tests/test_telegram_client.py -v
pytest tests/test_handler.py::TestLambdaHandler::test_debug_command -v
```

## 故障排除

### Bot 沒有回應

1. 檢查 `TELEGRAM_BOT_TOKEN` 是否設定正確
2. 檢查 Lambda 日誌：
   ```bash
   aws logs tail /aws/lambda/telegram-lambda-receiver --follow
   ```

### 回應格式錯誤

檢查 Telegram API 錯誤：
- HTTP 403：Bot Token 無效
- HTTP 400：訊息格式錯誤
- HTTP 429：請求過於頻繁

## 未來改進

可考慮的增強功能：
- [ ] 加入允許名單限制
- [ ] 支援更多除錯指令（如 `/debug env`、`/debug stats`）
- [ ] 過濾敏感資訊
- [ ] 加入指令權限管理

## 相關文件

- [README.md](README.md) - 專案主文件
- [tests/test_telegram_client.py](tests/test_telegram_client.py) - 測試案例
