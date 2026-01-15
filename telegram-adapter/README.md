# telegram-lambda

Telegram Webhook Receiver - 接收 Telegram webhook 並透過允許名單驗證後轉發到 SQS 佇列。

## 📋 專案概述

此專案是 Telegram Bot 架構的接收層（Receiver），負責：
- ✅ 接收 Telegram webhook 請求
- ✅ 驗證用戶允許名單（DynamoDB）
- ✅ 快速回應 200 OK（< 3秒）
- ✅ 將合法訊息轉發到 SQS 佇列

## 🏗️ 架構圖

```
┌─────────────┐
│  Telegram   │
│   Users     │
└──────┬──────┘
       │ HTTPS Webhook
       ▼
┌─────────────────────────────────────┐
│     AWS API Gateway                 │
│  /webhook (POST)                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│   telegram-lambda (Receiver)                    │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  handler.py (入口)                      │   │
│  │  - 接收 Telegram webhook               │   │
│  │  - ✅ 驗證允許名單 (Allowlist)         │   │
│  │  - 快速回應 200 OK                     │   │
│  └────────┬────────────────────────────────┘   │
│           │                                     │
│  ┌────────▼────────────────────────────────┐   │
│  │  allowlist.py                           │   │
│  │  - check_allowed(chat_id, username)     │   │
│  │  - DynamoDB Query                       │   │
│  └────────┬────────────────────────────────┘   │
│           │ ✅ 通過檢查                         │
│           ▼                                     │
│  ┌─────────────────────────────────────────┐   │
│  │  sqs_client.py                          │   │
│  │  - send_to_queue(message)               │   │
│  └─────────────────────────────────────────┘   │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   AWS SQS Queue       │
        │  telegram-inbound     │
        └───────────────────────┘
```

## 📁 專案結構

```
telegram-lambda/
├── src/                        # 原始碼
│   ├── handler.py              # Lambda 入口函數
│   ├── allowlist.py            # 允許名單驗證模組
│   ├── sqs_client.py           # SQS 客戶端
│   ├── telegram_client.py      # Telegram API 客戶端（用於除錯功能）
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           # 日誌工具
│       └── response.py         # API Gateway 回應格式化
├── tests/                      # 測試檔案
│   ├── __init__.py
│   ├── test_handler.py         # Handler 測試
│   ├── test_allowlist.py       # Allowlist 測試
│   ├── test_sqs_client.py      # SQS Client 測試
│   └── test_telegram_client.py # Telegram Client 測試
├── docs/                       # 📚 文件目錄
│   ├── deployment/             # 部署相關文件
│   ├── features/               # 功能說明文件
│   ├── troubleshooting/        # 故障排除文件
│   └── changelog/              # 變更日誌文件
├── template.yaml               # SAM 部署模板
├── requirements.txt            # Python 依賴
├── .gitignore
└── README.md
```

## 📚 完整文件

更多詳細文件請參閱 [docs 目錄](docs/README.md)：

- 📘 [部署指南](docs/deployment/DEPLOYMENT_GUIDE.md)
- 📗 [部署最佳實踐](docs/deployment/DEPLOYMENT_BEST_PRACTICES.md)
- 📙 [除錯指令說明](docs/features/DEBUG_COMMAND.md)
- 📕 [指令系統架構](docs/features/COMMAND_SYSTEM.md)
- 📕 [Webhook 故障排除](docs/troubleshooting/WEBHOOK_SETUP_TROUBLESHOOTING.md)

## 🚀 快速開始

### 前置需求

- Python 3.11+
- AWS CLI
- AWS SAM CLI
- AWS 帳戶與適當的 IAM 權限

### 安裝依賴

```bash
pip install -r requirements.txt
```

### 本地測試

```bash
# 安裝測試依賴
pip install pytest pytest-mock

# 執行測試
pytest tests/ -v

# 執行測試並顯示覆蓋率
pytest tests/ -v --cov=src
```

## 📦 部署

### 1. 建構專案

```bash
sam build
```

### 2. 部署到 AWS

首次部署使用 guided 模式：

```bash
sam deploy --guided
```

後續部署：

```bash
sam deploy
```

### 3. 取得 Webhook URL 和 Secret Token

部署完成後，從輸出中取得 `WebhookUrl` 和查詢 secret token 的命令：

```
Outputs:
  WebhookUrl: https://xxxxx.execute-api.us-east-1.amazonaws.com/Prod/webhook
  GetSecretTokenCommand: aws secretsmanager get-secret-value --secret-id telegram-lambda-secret-token-xxx --query 'SecretString' --output text | jq -r .token
```

執行命令取得 secret token：

```bash
aws secretsmanager get-secret-value \
  --secret-id telegram-lambda-secret-token \
  --query 'SecretString' \
  --output text | jq -r .token
```

**輸出範例**：
```
AbCdEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEfGhIjKlMnOpQrStUvWxYz01
```

### 4. 設定 Telegram Webhook

使用取得的 webhook URL 和 secret token 設定 Telegram webhook：

```bash
# 將下方的 <YOUR_BOT_TOKEN> 和 <YOUR_SECRET_TOKEN> 替換為實際值
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://xxxxx.execute-api.us-east-1.amazonaws.com/Prod/webhook" \
  -d "secret_token=<YOUR_SECRET_TOKEN>"
```

**範例**：
```bash
curl -X POST "https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/setWebhook" \
  -d "url=https://abcd1234.execute-api.us-east-1.amazonaws.com/Prod/webhook" \
  -d "secret_token=AbCdEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEfGhIjKlMnOpQrStUvWxYz01"
```

驗證 webhook 設定：
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

### 5. 初始化允許名單

新增允許的用戶到 DynamoDB：

```bash
aws dynamodb put-item \
  --table-name telegram-allowlist \
  --item '{
    "chat_id": {"N": "123456789"},
    "username": {"S": "your_username"},
    "enabled": {"BOOL": true}
  }'
```

## 🔌 指令系統

專案採用 **Command Handler Pattern（指令處理器模式）** 設計，將不同指令的處理邏輯獨立出來，提供良好的可擴展性和維護性。

### 架構特點

- **模組化設計**：每個指令獨立成處理器類別
- **路由機制**：統一的指令路由器分發請求
- **易於擴展**：新增指令只需實作新的處理器類別
- **權限系統**：預留權限驗證架構（未來可擴展）

### 現有指令

- **`/debug`** - 除錯指令，回傳完整的 API Gateway event（無權限限制）

更多詳細資訊請參閱 [指令系統架構文件](docs/features/COMMAND_SYSTEM.md)。

## 🐛 除錯功能

### `/debug test` 指令

專案支援特殊的除錯指令，可以讓 Lambda 將收到的完整 API Gateway event 回傳給用戶，方便開發和故障排除。

#### 使用方式

在 Telegram 中向 Bot 發送任何 `/debug` 開頭的指令：
```
/debug
/debug test
/debug any string
```

Lambda 會回傳完整的 API Gateway event（JSON 格式），包含：
- HTTP Headers
- Request Body
- API Gateway 配置
- 其他請求相關資訊

#### 設定 Bot Token

要使用此功能，需要設定 `TELEGRAM_BOT_TOKEN` 環境變數：

**方法 1：使用 AWS CLI 更新**
```bash
aws lambda update-function-configuration \
  --function-name telegram-lambda-receiver \
  --environment "Variables={TELEGRAM_SECRET_TOKEN='',TELEGRAM_BOT_TOKEN='YOUR_BOT_TOKEN',SQS_QUEUE_URL='YOUR_QUEUE_URL',ALLOWLIST_TABLE_NAME='telegram-allowlist',LOG_LEVEL='INFO'}"
```

**方法 2：使用 AWS Console**
1. 進入 Lambda 控制台
2. 選擇 `telegram-lambda-receiver` 函數
3. 點擊「Configuration」→「Environment variables」
4. 編輯 `TELEGRAM_BOT_TOKEN` 變數
5. 輸入您的 Bot Token（格式：`123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`）
6. 儲存變更

#### 安全注意事項

⚠️ **重要**：當前實作為**完全放行**，任何用戶都可以使用此指令。

除錯資訊可能包含敏感資料：
- API Gateway 配置
- 環境變數名稱
- 請求路徑和參數

**建議**：
- 僅在開發/測試環境使用
- 生產環境應移除此功能或加上允許名單限制
- 使用後立即檢視日誌確認沒有洩漏敏感資訊

#### 訊息長度限制

- Telegram 單則訊息限制 4096 字元
- 如果 event 內容超過限制，會自動分成多則訊息發送
- 每則訊息會標註 `📄 Part X/Y`

## 🔧 環境變數

Lambda 函數使用以下環境變數：

| 變數名稱 | 說明 | 預設值 |
|---------|------|--------|
| `TELEGRAM_SECRET_TOKEN` | Telegram webhook secret token | (由 Secrets Manager 自動生成) |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token（用於 /debug test 功能） | '' |
| `SQS_QUEUE_URL` | SQS 佇列 URL | (由 SAM 自動設定) |
| `ALLOWLIST_TABLE_NAME` | DynamoDB 表名稱 | telegram-allowlist |
| `LOG_LEVEL` | 日誌等級 | INFO |

## 📊 AWS 資源

此專案會建立以下 AWS 資源：

- **Secrets Manager**: telegram-lambda-secret-token (自動生成 secret token)
- **Lambda Function**: telegram-lambda-receiver
- **API Gateway**: telegram-webhook-api
- **SQS Queue**: telegram-inbound
- **SQS DLQ**: telegram-inbound-dlq
- **DynamoDB Table**: telegram-allowlist
- **CloudWatch Log Group**: /aws/lambda/telegram-lambda-receiver
- **CloudWatch Alarms**: 
  - Lambda 錯誤告警
  - SQS 佇列深度告警

**成本估算**：
- Secrets Manager: ~$0.40/月
- 其他資源：按使用量計費（Lambda、API Gateway、DynamoDB、SQS）

## 🔐 安全性

- ✅ **Telegram Secret Token**：自動生成 64 字元隨機 token（A-Z, a-z, 0-9）
- ✅ **允許名單驗證**：只有在 DynamoDB 中的用戶才能使用
- ✅ **雙重驗證**：同時驗證 chat_id 和 username
- ✅ **最小權限原則**：Lambda 僅有必要的 IAM 權限
- ✅ **資料加密**：DynamoDB、SQS 和 Secrets Manager 都啟用了加密
- ✅ **日誌過濾**：敏感資訊不會記錄到 CloudWatch

## 📈 監控

### CloudWatch Metrics

- Lambda 執行次數
- Lambda 錯誤率
- Lambda 執行時間
- SQS 訊息數量

### CloudWatch Alarms

1. **Lambda 錯誤告警**：5 分鐘內超過 5 個錯誤
2. **SQS 佇列深度告警**：平均訊息數超過 100

### 檢視日誌

```bash
# 檢視 Lambda 日誌
sam logs -n TelegramReceiverFunction --tail

# 或使用 AWS CLI
aws logs tail /aws/lambda/telegram-lambda-receiver --follow
```

## 🔍 故障排除

### Webhook 無回應

```bash
# 檢查 Lambda 日誌
aws logs tail /aws/lambda/telegram-lambda-receiver --follow

# 檢查 API Gateway 日誌
aws logs tail /aws/apigateway/telegram-webhook-api --follow
```

### 用戶被拒絕訪問

檢查 DynamoDB 允許名單：

```bash
aws dynamodb get-item \
  --table-name telegram-allowlist \
  --key '{"chat_id": {"N": "123456789"}}'
```

### SQS 訊息未送達

檢查 Dead Letter Queue：

```bash
aws sqs receive-message \
  --queue-url <DLQ_URL> \
  --max-number-of-messages 10
```

## 🧪 測試

### 單元測試

```bash
pytest tests/ -v
```

### 手動測試 Webhook

**注意**：手動測試需要包含正確的 secret token header。

```bash
# 先取得 secret token
SECRET_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id telegram-lambda-secret-token \
  --query 'SecretString' \
  --output text | jq -r .token)

# 使用 secret token 測試 webhook
curl -X POST https://xxxxx.execute-api.us-east-1.amazonaws.com/Prod/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: $SECRET_TOKEN" \
  -d '{
    "message": {
      "message_id": 123,
      "chat": {"id": 123456789},
      "from": {"username": "test_user"},
      "text": "Hello"
    }
  }'
```

## 📝 API 參考

### POST /webhook

接收 Telegram webhook 請求。

**請求體**：Telegram Update 物件

**回應**：
- `200 OK`: 訊息已接收並轉發
- `400 Bad Request`: 請求格式錯誤
- `403 Forbidden`: 用戶未在允許名單中
- `500 Internal Server Error`: 伺服器錯誤

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

MIT License

## 🔗 相關專案

- [telegram-processor](../telegram-processor) - 處理 SQS 訊息的 Lambda
- [telegram-agentcore-bot](../telegram-agentcore-bot) - AgentCore 整合

## 📞 聯絡方式

如有問題請開 Issue。
