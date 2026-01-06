# Telegram Bot 快速參考指南

本文檔提供 AgentCoreNexus Telegram Bot 的快速參考信息，用於日常操作和故障排除。

## 📍 系統基礎信息

### AWS 區域
```
us-west-2 (Oregon)
```

### CloudFormation Stacks
| Stack 名稱 | 用途 | 主要資源 |
|-----------|------|----------|
| `telegram-unified-bot` | AI 處理器 | telegram-unified-bot-processor |
| `telegram-lambda-receiver` | Webhook 接收 | telegram-lambda-receiver<br>telegram-lambda-response-router |

### Lambda 函數
| 函數名稱 | 用途 | 內存 | 超時 |
|---------|------|------|------|
| telegram-unified-bot-processor | AI 處理 + Browser | 1024 MB | 300s |
| telegram-lambda-receiver | Webhook 接收 | 256 MB | 30s |
| telegram-lambda-response-router | 響應路由 | 256 MB | 30s |

### 其他資源
- **API Gateway**: jpyhj26jw9.execute-api.us-west-2.amazonaws.com
- **EventBus**: telegram-lambda-receiver-events
- **DynamoDB**: telegram-allowlist
- **Secrets**: telegram-lambda-receiver-secrets

---

## 🚀 部署命令

### 完整部署流程

#### 1. 部署處理器 Lambda
```bash
cd telegram-agentcore-bot
sam build
sam deploy --stack-name telegram-unified-bot \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --region us-west-2
```

#### 2. 部署接收器和路由器
```bash
cd telegram-lambda
sam build
sam deploy --stack-name telegram-lambda-receiver \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --region us-west-2
```

### 快速更新（無變更集確認）
```bash
sam deploy --stack-name STACK_NAME \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --region us-west-2 \
  --no-confirm-changeset
```

### 清除緩存重新部署
```bash
rm -rf .aws-sam
sam build
sam deploy --stack-name STACK_NAME --resolve-s3 --capabilities CAPABILITY_IAM --region us-west-2
```

---

## 📊 日誌查詢

### 查看實時日誌
```bash
# 處理器日誌（AI 和瀏覽器）
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 \
  --follow

# 接收器日誌（webhook 和命令處理）
aws logs tail /aws/lambda/telegram-lambda-receiver \
  --region us-west-2 \
  --follow

# 響應路由日誌
aws logs tail /aws/lambda/telegram-lambda-response-router \
  --region us-west-2 \
  --follow
```

### 查看最近日誌
```bash
# 最近 5 分鐘
aws logs tail /aws/lambda/FUNCTION_NAME --region us-west-2 --since 5m

# 最近 1 小時
aws logs tail /aws/lambda/FUNCTION_NAME --region us-west-2 --since 1h

# 特定時間範圍
aws logs tail /aws/lambda/FUNCTION_NAME \
  --region us-west-2 \
  --start-time 2026-01-06T15:00:00Z \
  --end-time 2026-01-06T16:00:00Z
```

### 搜索特定錯誤
```bash
# 搜索錯誤日誌
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/FUNCTION_NAME \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000

# 搜索特定關鍵字
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/FUNCTION_NAME \
  --filter-pattern "browser" \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

---

## 🧪 測試方法

### 1. 測試 API Gateway（直接）

#### 測試 /info 命令
```bash
curl -X POST https://jpyhj26jw9.execute-api.us-west-2.amazonaws.com/Prod/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: r1JU5g0FgZURDUeJpFFtzznE5cTBEJnvXNnxBnMJWMQGvKJTrQBVOyhJJMcPTq7D" \
  -d '{
    "message": {
      "message_id": 1,
      "from": {"id": 316743844, "username": "qwer2003tw"},
      "chat": {"id": 316743844, "username": "qwer2003tw"},
      "text": "/info"
    }
  }'
```

#### 測試對話
```bash
curl -X POST https://jpyhj26jw9.execute-api.us-west-2.amazonaws.com/Prod/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: r1JU5g0FgZURDUeJpFFtzznE5cTBEJnvXNnxBnMJWMQGvKJTrQBVOyhJJMcPTq7D" \
  -d '{
    "message": {
      "message_id": 2,
      "from": {"id": 316743844, "username": "qwer2003tw"},
      "chat": {"id": 316743844, "username": "qwer2003tw"},
      "text": "你好"
    }
  }'
```

#### 測試瀏覽器功能
```bash
curl -X POST https://jpyhj26jw9.execute-api.us-west-2.amazonaws.com/Prod/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: r1JU5g0FgZURDUeJpFFtzznE5cTBEJnvXNnxBnMJWMQGvKJTrQBVOyhJJMcPTq7D" \
  -d '{
    "message": {
      "message_id": 3,
      "from": {"id": 316743844, "username": "qwer2003tw"},
      "chat": {"id": 316743844, "username": "qwer2003tw"},
      "text": "幫我瀏覽 https://example.com"
    }
  }'
```

### 2. 測試 Telegram Webhook

#### 檢查 Webhook 狀態
```bash
# 獲取 bot token
BOT_TOKEN=$(aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-lambda-receiver-secrets \
  --query SecretString --output text | jq -r .bot_token)

# 檢查 webhook 信息
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

#### 設置 Webhook
```bash
# 獲取 webhook secret
WEBHOOK_SECRET=$(aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-lambda-receiver-secrets \
  --query SecretString --output text | jq -r .webhook_secret_token)

# 設置 webhook
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"https://jpyhj26jw9.execute-api.us-west-2.amazonaws.com/Prod/webhook\",
    \"secret_token\": \"${WEBHOOK_SECRET}\"
  }"
```

---

## 🔍 常用查詢命令

### 檢查 Stack 狀態
```bash
# 列出所有 telegram 相關 stacks
aws cloudformation describe-stacks --region us-west-2 \
  --query 'Stacks[?contains(StackName, `telegram`)].{Name:StackName,Status:StackStatus}' \
  --output table

# 檢查特定 stack
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name telegram-unified-bot \
  --query 'Stacks[0].StackStatus'
```

### 檢查 Lambda 函數
```bash
# 列出所有 telegram Lambda
aws lambda list-functions --region us-west-2 \
  --query 'Functions[?contains(FunctionName, `telegram`)].FunctionName' \
  --output table

# 檢查函數狀態
aws lambda get-function \
  --region us-west-2 \
  --function-name telegram-unified-bot-processor \
  --query 'Configuration.{State:State,LastUpdateStatus:LastUpdateStatus}'

# 檢查環境變數
aws lambda get-function-configuration \
  --region us-west-2 \
  --function-name telegram-unified-bot-processor \
  --query 'Environment.Variables'
```

### 檢查 Secrets Manager
```bash
# 列出所有 secrets
aws secretsmanager list-secrets --region us-west-2 \
  --query 'SecretList[?contains(Name, `telegram`)].Name' \
  --output table

# 獲取 bot token
aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-lambda-receiver-secrets \
  --query SecretString --output text | jq -r .bot_token

# 獲取 webhook secret
aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-lambda-receiver-secrets \
  --query SecretString --output text | jq -r .webhook_secret_token
```

### 檢查 EventBridge Rules
```bash
# 列出 Event Bus 上的 rules
aws events list-rules --region us-west-2 \
  --event-bus-name telegram-lambda-receiver-events

# 檢查 rule targets
aws events list-targets-by-rule \
  --region us-west-2 \
  --rule RULE_NAME \
  --event-bus-name telegram-lambda-receiver-events
```

### 檢查 DynamoDB Allowlist
```bash
# 掃描所有允許的用戶
aws dynamodb scan --region us-west-2 \
  --table-name telegram-allowlist \
  --query 'Items[*].{ChatID:chat_id.N,Username:username.S}' \
  --output table

# 檢查特定用戶
aws dynamodb get-item --region us-west-2 \
  --table-name telegram-allowlist \
  --key '{"chat_id":{"N":"316743844"}}'
```

---

## 🔧 常用操作

### 更新 Lambda 環境變數
```bash
aws lambda update-function-configuration \
  --region us-west-2 \
  --function-name telegram-unified-bot-processor \
  --environment "Variables={
    BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0,
    BROWSER_ENABLED=true,
    EVENT_BUS_NAME=telegram-lambda-receiver-events,
    LOG_LEVEL=INFO
  }"
```

### 清除 Lambda 緩存
```bash
# 強制更新代碼
aws lambda update-function-code \
  --region us-west-2 \
  --function-name FUNCTION_NAME \
  --s3-bucket BUCKET \
  --s3-key KEY \
  --publish
```

### 添加用戶到 Allowlist
```bash
aws dynamodb put-item --region us-west-2 \
  --table-name telegram-allowlist \
  --item '{
    "chat_id": {"N": "CHAT_ID"},
    "username": {"S": "USERNAME"}
  }'
```

### 更新 Bot Token
```bash
# 獲取現有 webhook secret
WEBHOOK_SECRET=$(aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-lambda-receiver-secrets \
  --query SecretString --output text | jq -r .webhook_secret_token)

# 更新包含新 bot token
aws secretsmanager update-secret \
  --region us-west-2 \
  --secret-id telegram-lambda-receiver-secrets \
  --secret-string "{\"bot_token\":\"NEW_TOKEN\",\"webhook_secret_token\":\"$WEBHOOK_SECRET\"}"

# 清除 Lambda 緩存（必須）
aws lambda update-function-code \
  --region us-west-2 \
  --function-name telegram-lambda-receiver \
  --s3-bucket aws-sam-cli-managed-default-samclisourcebucket-tephzsvbizdo \
  --s3-key LATEST_KEY \
  --publish
```

---

## 🐛 故障排除

### Lambda 沒有回應

**檢查步驟**：
```bash
# 1. 檢查 Lambda 狀態
aws lambda get-function --region us-west-2 \
  --function-name telegram-unified-bot-processor \
  --query 'Configuration.State'

# 2. 檢查 EventBridge rule targets
aws events list-targets-by-rule --region us-west-2 \
  --rule telegram-lambda-receiver-message-received \
  --event-bus-name telegram-lambda-receiver-events

# 3. 檢查環境變數
aws lambda get-function-configuration --region us-west-2 \
  --function-name telegram-unified-bot-processor \
  --query 'Environment.Variables.EVENT_BUS_NAME'

# 4. 查看最近日誌
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 --since 10m
```

### 權限錯誤

**檢查 IAM 策略**：
```bash
# 獲取角色名稱
ROLE_NAME=$(aws lambda get-function --region us-west-2 \
  --function-name telegram-unified-bot-processor \
  --query 'Configuration.Role' --output text | cut -d'/' -f2)

# 查看角色策略
aws iam get-role-policy --role-name $ROLE_NAME --policy-name POLICY_NAME
```

**必須包含的權限**：
- events:PutEvents
- bedrock:InvokeModel*
- bedrock-agentcore:*BrowserSession
- secretsmanager:GetSecretValue

### 瀏覽器功能問題

**驗證清單**：
```bash
# 1. 檢查 BROWSER_ENABLED
aws lambda get-function-configuration --region us-west-2 \
  --function-name telegram-unified-bot-processor \
  --query 'Environment.Variables.BROWSER_ENABLED'

# 2. 測試 Browser sandbox 權限
aws bedrock-agentcore start-browser-session \
  --region us-west-2 \
  --identifier aws.browser.v1 2>&1 | head -10

# 3. 查看瀏覽器相關日誌
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/telegram-unified-bot-processor \
  --filter-pattern "browser" \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

---

## 📈 監控指標

### CloudWatch Dashboard
```
Dashboard 名稱: telegram-lambda-monitoring
位置: CloudWatch Console > Dashboards
```

### 關鍵指標
- **MessagesReceived**: 收到的消息數
- **MessagesProcessed**: 處理成功的消息
- **AllowlistDenied**: 被拒絕的請求
- **Lambda Errors**: Lambda 執行錯誤
- **Response Duration**: 響應時間

### 查看指標
```bash
# Lambda 調用次數
aws cloudwatch get-metric-statistics \
  --region us-west-2 \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=telegram-unified-bot-processor \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --period 300 \
  --statistics Sum

# Lambda 錯誤率
aws cloudwatch get-metric-statistics \
  --region us-west-2 \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=telegram-unified-bot-processor \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --period 300 \
  --statistics Sum
```

---

## 🔄 常見維護任務

### 定期檢查（每週）
```bash
# 1. 檢查所有 Lambda 狀態
aws lambda list-functions --region us-west-2 \
  --query 'Functions[?contains(FunctionName, `telegram`)].{Name:FunctionName,State:State}' \
  --output table

# 2. 檢查錯誤日誌
for func in telegram-unified-bot-processor telegram-lambda-receiver telegram-lambda-response-router; do
  echo "=== $func ==="
  aws logs filter-log-events \
    --region us-west-2 \
    --log-group-name /aws/lambda/$func \
    --filter-pattern "ERROR" \
    --start-time $(date -u -d '1 week ago' +%s)000 \
    --max-items 10
done

# 3. 檢查 DLQ 消息
aws sqs get-queue-attributes \
  --region us-west-2 \
  --queue-url https://sqs.us-west-2.amazonaws.com/190825685292/telegram-inbound-dlq \
  --attribute-names ApproximateNumberOfMessages
```

### 清理舊日誌（每月）
```bash
# 日誌已自動設置 14 天保留期
# 檢查日誌組設置
aws logs describe-log-groups --region us-west-2 \
  --log-group-name-prefix /aws/lambda/telegram \
  --query 'logGroups[*].{Name:logGroupName,Retention:retentionInDays}'
```

---

## 🎯 效能基準

### 預期響應時間
| 功能 | 響應時間 | 說明 |
|------|----------|------|
| /info 命令 | 1-2秒 | 直接處理 |
| 簡單對話 | 6-15秒 | AI 推理 |
| 複雜分析 | 15-30秒 | 深度思考 |
| 瀏覽器任務 | 10-20秒 | Browser sandbox |

### Lambda 性能
- **冷啟動**: 2-3 秒
- **熱啟動**: 200-500ms
- **內存使用**: 通常 < 150MB
- **超時設置**: 處理器 300s，其他 30s

---

## 🔐 安全信息

### Webhook Secret Token
```bash
# 獲取 secret token
aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-lambda-receiver-secrets \
  --query SecretString --output text | jq -r .webhook_secret_token
```

### Allowlist 管理
```bash
# 當前允許的用戶
aws dynamodb scan --region us-west-2 \
  --table-name telegram-allowlist \
  --projection-expression "chat_id,username"

# 添加新用戶
aws dynamodb put-item --region us-west-2 \
  --table-name telegram-allowlist \
  --item '{"chat_id":{"N":"CHAT_ID"},"username":{"S":"USERNAME"}}'

# 移除用戶
aws dynamodb delete-item --region us-west-2 \
  --table-name telegram-allowlist \
  --key '{"chat_id":{"N":"CHAT_ID"}}'
```

---

## 📱 Telegram Bot 信息

### Bot 基本信息
- **Bot Token**: 存儲在 Secrets Manager
- **Username**: 從 BotFather 獲取
- **Webhook URL**: https://jpyhj26jw9.execute-api.us-west-2.amazonaws.com/Prod/webhook

### 獲取 Bot 信息
```bash
BOT_TOKEN=$(aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-lambda-receiver-secrets \
  --query SecretString --output text | jq -r .bot_token)

# 獲取 bot 基本信息
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/getMe"
```

---

## 🎯 項目結構

```
AgentCoreNexus/
├── telegram-agentcore-bot/        # AI 處理器
│   ├── template.yaml              # SAM template
│   ├── processor_entry.py         # Lambda 入口
│   ├── agents/                    # Agent 邏輯
│   ├── services/                  # 服務（瀏覽器、記憶）
│   ├── tools/                     # 工具函數
│   └── requirements.txt           # Python 依賴
│
├── telegram-lambda/               # Webhook 接收器
│   ├── template.yaml              # SAM template
│   ├── src/                       # 接收器代碼
│   │   ├── handler.py             # 主處理器
│   │   ├── commands/              # 命令處理器
│   │   └── telegram_client.py    # Telegram API
│   └── router/                    # 響應路由器
│
└── .clinerules/                   # Cline 規則
    └── deployment/                # 部署文檔
        ├── aws-lambda-telegram-bot-deployment-issues.md  # 問題清單
        └── telegram-bot-quick-reference.md              # 快速參考（本文件）
```

---

## 📚 相關文檔

### 項目文檔
- `DEPLOYMENT_GUIDE_Complete.md` - 完整部署指南
- `AgentCore_Nexus_Integration_Guide.md` - 集成指南
- `ADMIN_COMMANDS_GUIDE.md` - 管理員命令

### 部署文檔
- `.clinerules/deployment/aws-lambda-telegram-bot-deployment-issues.md` - 問題清單
- `.clinerules/deployment/telegram-bot-quick-reference.md` - 快速參考（本文件）

### 最近的工作報告
- `ULTIMATE_SUCCESS_REPORT.md` - 完整任務報告（2026-01-06）
- `AWS_BROWSER_SANDBOX_IMPLEMENTATION.md` - 瀏覽器實現
- `BROWSER_PERMISSIONS_FIX.md` - 權限修復

---

## 🎓 重要經驗

### 部署順序
1. ✅ 先部署 telegram-unified-bot（處理器）
2. ✅ 再部署 telegram-lambda-receiver（接收器）
3. ✅ 使用 ImportValue 建立連接

### 權限要點
- ✅ AgentCore Lambda 需要 bedrock-agentcore 權限
- ✅ 接收器需要 secretsmanager 權限
- ✅ 所有 Lambda 需要 events:PutEvents

### 測試要點
- ✅ 使用真實的 username（allowlist 驗證）
- ✅ 包含完整的 Telegram update 格式
- ✅ 等待 Lambda 狀態變為 Active 後測試

### 性能要點
- ✅ AI 推理時間 5-30 秒是正常的
- ✅ 系統處理應該 < 1 秒
- ✅ 瀏覽器任務 10-20 秒是預期的

---

**文檔版本**: 1.0  
**最後更新**: 2026-01-06  
**AWS 區域**: us-west-2  
**適用項目**: AgentCoreNexus Telegram Bot
