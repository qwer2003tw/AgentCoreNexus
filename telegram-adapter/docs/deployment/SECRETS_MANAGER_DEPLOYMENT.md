# Secrets Manager 部署指南

本指南說明如何使用新的 Secrets Manager 整合來安全地管理 Telegram Bot Token 和 Webhook Secret Token。

## 📋 目錄

- [概述](#概述)
- [為什麼使用 Secrets Manager](#為什麼使用-secrets-manager)
- [部署步驟](#部署步驟)
- [更新現有部署](#更新現有部署)
- [驗證部署](#驗證部署)
- [管理 Secrets](#管理-secrets)
- [故障排除](#故障排除)
- [成本考量](#成本考量)

## 概述

此專案使用 AWS Secrets Manager 來安全地儲存和管理所有敏感資訊。所有 tokens 儲存在**單一 Secret** 中，包含：
- `bot_token`: Telegram Bot Token
- `webhook_secret_token`: Telegram Webhook Secret Token（自動生成）

### Secret 結構

```json
{
  "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
  "webhook_secret_token": "auto-generated-64-char-string-with-A-Z-a-z-0-9-only"
}
```

### 主要改進

✅ **安全性提升**
- Token 不再以明文存在環境變數或程式碼中
- 所有敏感資訊集中在單一 Secret 管理
- Webhook secret token 自動生成，確保隨機性
- 支援自動 token 輪替
- 符合安全最佳實踐

✅ **效能優化**
- LRU 快取減少 Secrets Manager API 呼叫
- Lambda 執行環境重用進一步減少呼叫次數
- 全域客戶端單例模式
- 單一 API 呼叫獲取所有 tokens

✅ **成本優化**
- 只需要一個 Secret（每月 $0.40）
- 減少 API 呼叫次數
- 比分開管理多個 secrets 更經濟

✅ **維護性改善**
- 所有相關 tokens 集中在同一處
- 更容易審計和更新
- 支援多環境部署
- 簡化配置管理

## 為什麼使用 Secrets Manager

### 安全問題

**之前的做法（不建議）：**
```yaml
Environment:
  Variables:
    TELEGRAM_BOT_TOKEN: "123456:ABC-DEF..."  # ❌ 明文儲存
    TELEGRAM_SECRET_TOKEN: "my-secret"       # ❌ 明文儲存
```

**問題：**
- Token 可能出現在 CloudFormation 範本中
- 環境變數可透過 Lambda Console 查看
- 難以進行 token 輪替
- 不符合安全合規要求

**新的做法（建議）：**
```yaml
Environment:
  Variables:
    TELEGRAM_SECRETS_ARN: !Ref TelegramSecrets  # ✅ 僅參考 ARN
```

## 部署步驟

### 1. 準備 Token

您只需要準備 **Telegram Bot Token**：

1. **Telegram Bot Token**
   - 從 [@BotFather](https://t.me/botfather) 獲取
   - 格式：`123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

2. **Telegram Webhook Secret Token**
   - ✅ **自動生成** - 部署時 CloudFormation 會自動產生
   - 64 字元隨機字串（僅包含 A-Z, a-z, 0-9）
   - 無需手動準備

### 2. 建立參數檔案

建立 `deploy-parameters.json`（**請勿提交到版本控制**）：

```json
{
  "Parameters": {
    "TelegramBotToken": "YOUR_BOT_TOKEN_HERE"
  }
}
```

**注意**：不需要提供 `TelegramSecretToken`，它會自動生成。

**重要：** 將此檔案加入 `.gitignore`：
```bash
echo "deploy-parameters.json" >> .gitignore
```

### 3. 建立部署

**方法 A：使用參數檔案（推薦）**

```bash
# 建立部署套件
sam build

# 部署
sam deploy \
  --parameter-overrides file://deploy-parameters.json \
  --capabilities CAPABILITY_IAM \
  --stack-name telegram-adapter

# 首次部署可能需要 --guided
sam deploy --guided \
  --parameter-overrides file://deploy-parameters.json
```

**方法 B：使用命令列參數**

```bash
sam deploy \
  --parameter-overrides \
    TelegramBotToken="YOUR_BOT_TOKEN" \
  --capabilities CAPABILITY_IAM \
  --stack-name telegram-adapter
```

**注意**：Secret token 會自動生成，無需提供參數。

### 4. 獲取部署資訊

部署完成後，查看輸出：

```bash
aws cloudformation describe-stacks \
  --stack-name telegram-adapter \
  --query 'Stacks[0].Outputs' \
  --output table
```

重要輸出包括：
- `WebhookUrl`: Telegram webhook URL
- `TelegramSecretsArn`: Telegram Secrets 的 ARN（包含所有 tokens）
- `TelegramSecretsName`: Secret 名稱（用於 CLI 命令）
- `GetBotTokenCommand`: 取得 bot token 的命令
- `GetWebhookSecretTokenCommand`: 取得自動生成的 webhook secret token 的命令

**重要**：首次部署後，請執行 `GetWebhookSecretTokenCommand` 取得自動生成的 webhook secret token，用於設定 Telegram webhook。

## 更新現有部署

如果您已有舊版部署（使用環境變數），請按以下步驟更新：

### 1. 備份現有 Token

```bash
# 取得當前的 Lambda 環境變數
aws lambda get-function-configuration \
  --function-name telegram-adapter-receiver \
  --query 'Environment.Variables' \
  --output json > current-env-vars.json

# 查看並保存 token
cat current-env-vars.json
```

### 2. 更新部署

```bash
# 使用備份的 bot token 建立參數檔案（只需要 bot token）
cat > deploy-parameters.json <<EOF
{
  "Parameters": {
    "TelegramBotToken": "從 current-env-vars.json 複製 TELEGRAM_BOT_TOKEN"
  }
}
EOF

# 執行更新
sam build
sam deploy --parameter-overrides file://deploy-parameters.json
```

**重要提醒**：
- 新版本的 secret token 會自動生成
- 如果您想保留舊的 secret token，需要在部署後手動更新 Secrets Manager
- 或者，您可以從舊環境變數中獲取 secret token，部署後手動更新到 Secrets Manager

### 3. 驗證更新

```bash
# 檢查新的環境變數（應該只有 ARN）
aws lambda get-function-configuration \
  --function-name telegram-adapter-receiver \
  --query 'Environment.Variables'

# 測試 Lambda 函數
sam local invoke TelegramReceiverFunction \
  --event events/test_webhook.json
```

## 驗證部署

### 1. 檢查 Secrets Manager

```bash
# 列出 secrets
aws secretsmanager list-secrets \
  --filters Key=name,Values=telegram-adapter

# 取得完整的 secret（包含所有 tokens）
aws secretsmanager get-secret-value \
  --secret-id telegram-adapter-secrets \
  --query 'SecretString' \
  --output text | jq

# 取得 bot token
aws secretsmanager get-secret-value \
  --secret-id telegram-adapter-secrets \
  --query 'SecretString' \
  --output text | jq -r .bot_token

# 取得 webhook secret token
aws secretsmanager get-secret-value \
  --secret-id telegram-adapter-secrets \
  --query 'SecretString' \
  --output text | jq -r .webhook_secret_token
```

### 2. 檢查 Lambda 權限

```bash
# 檢查 Lambda 的 IAM 角色
aws lambda get-function \
  --function-name telegram-adapter-receiver \
  --query 'Configuration.Role'

# 檢查角色的權限（應包含 secretsmanager:GetSecretValue）
aws iam get-role-policy \
  --role-name [ROLE_NAME] \
  --policy-name [POLICY_NAME]
```

### 3. 測試端到端

```bash
# 檢查 CloudWatch Logs
aws logs tail /aws/lambda/telegram-adapter-receiver --follow

# 發送測試 webhook（需要先設定 webhook URL）
curl -X POST https://[API_GATEWAY_URL]/Prod/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: YOUR_SECRET_TOKEN" \
  -d @test_webhook_payload.json
```

## 管理 Secrets

### 更新 Token

**方法 A：透過 AWS Console**
1. 前往 AWS Secrets Manager
2. 選擇 secret (telegram-adapter-bot-token 或 telegram-adapter-secret-token)
3. 點擊「Retrieve secret value」
4. 點擊「Edit」
5. 更新 token 值
6. 儲存

**方法 B：透過 AWS CLI**

```bash
# 更新整個 secret（需要同時提供兩個 tokens）
aws secretsmanager update-secret \
  --secret-id telegram-adapter-secrets \
  --secret-string '{
    "bot_token": "NEW_BOT_TOKEN_HERE",
    "webhook_secret_token": "NEW_WEBHOOK_SECRET_TOKEN_HERE"
  }'

# 或者只更新 bot token（先取得現有值）
CURRENT_WEBHOOK_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id telegram-adapter-secrets \
  --query 'SecretString' \
  --output text | jq -r .webhook_secret_token)

aws secretsmanager update-secret \
  --secret-id telegram-adapter-secrets \
  --secret-string "{
    \"bot_token\": \"NEW_BOT_TOKEN_HERE\",
    \"webhook_secret_token\": \"$CURRENT_WEBHOOK_TOKEN\"
  }"
```

### 清除 Lambda 快取

更新 secret 後，Lambda 快取可能仍保留舊值。可以：

1. **等待自然過期**（Lambda 執行環境重置時）
2. **更新 Lambda 環境變數**（觸發重新部署）：
   ```bash
   aws lambda update-function-configuration \
     --function-name telegram-adapter-receiver \
     --environment "Variables={FORCE_REFRESH=$(date +%s)}"
   ```

### Token 輪替

建立自動輪替（可選）：

```bash
# 為 secret 設定輪替
aws secretsmanager rotate-secret \
  --secret-id telegram-adapter-secrets \
  --rotation-lambda-arn [ROTATION_FUNCTION_ARN] \
  --rotation-rules AutomaticallyAfterDays=90
```

**注意：** 
- Telegram Bot Token 輪替需要額外的協調（需更新 BotFather 中的 token）
- Webhook secret token 可以獨立輪替，但需要同時更新 Telegram webhook 設定

## 故障排除

### 問題 1：Lambda 無法讀取 Secret

**症狀：**
```
Failed to retrieve secret: AccessDeniedException
```

**解決方案：**
```bash
# 檢查 IAM 權限
aws lambda get-policy --function-name telegram-adapter-receiver

# 確認 template.yaml 中的權限設定正確
# 必須包含：
Policies:
  - Statement:
      - Effect: Allow
        Action:
          - secretsmanager:GetSecretValue
        Resource:
          - !Ref TelegramSecrets
```

### 問題 2：Secret 不存在

**症狀：**
```
ResourceNotFoundException: Secrets Manager can't find the specified secret
```

**解決方案：**
```bash
# 檢查 secret 是否存在
aws secretsmanager list-secrets \
  --filters Key=name,Values=telegram-adapter

# 如果不存在，重新部署 stack
sam deploy --parameter-overrides file://deploy-parameters.json
```

### 問題 3：Token 格式錯誤

**症狀：**
```
Failed to parse secret JSON
```

**解決方案：**
```bash
# 檢查 secret 格式
aws secretsmanager get-secret-value \
  --secret-id telegram-adapter-secrets \
  --query 'SecretString' \
  --output text

# 應該是有效的 JSON: {"bot_token": "...", "webhook_secret_token": "..."}
# 如果格式錯誤，更新：
aws secretsmanager update-secret \
  --secret-id telegram-adapter-secrets \
  --secret-string '{
    "bot_token": "YOUR_BOT_TOKEN",
    "webhook_secret_token": "YOUR_WEBHOOK_SECRET_TOKEN"
  }'
```

### 問題 4：環境變數未設定

**症狀：**
```
TELEGRAM_SECRETS_ARN environment variable not set
```

**解決方案：**
```bash
# 檢查 Lambda 環境變數
aws lambda get-function-configuration \
  --function-name telegram-adapter-receiver \
  --query 'Environment.Variables'

# 應該包含 TELEGRAM_SECRETS_ARN
# 如果缺少，重新部署
sam deploy
```

## 成本考量

### Secrets Manager 定價

截至 2024 年的定價（請查看最新定價）：

- **Secret 儲存**：$0.40 USD/secret/月
- **API 呼叫**：$0.05 USD/10,000 次呼叫

### 此專案的預估成本

**假設：**
- 1 個 secret（包含 bot token + webhook secret token）
- Lambda 每天處理 1,000 個請求
- Lambda 執行環境平均重用 100 次請求

**每月成本：**
```
Secret 儲存：1 secret × $0.40 = $0.40
API 呼叫：(1,000 requests/day × 30 days) / 100 reuse × $0.05/10,000 = $0.015

總計：約 $0.42/月
```

**相比分開管理的成本優勢：**
- 節省 50% 的 Secret 儲存成本（$0.40 vs $0.80）
- 單一 API 呼叫獲取所有 tokens，效率更高

### 優化成本

1. **利用快取**：已實作 LRU 快取和執行環境重用
2. **合併 secrets**：✅ 已實作 - 所有 tokens 在單一 secret 中
3. **監控使用**：定期檢查 CloudWatch Metrics
4. **最小化 API 呼叫**：充分利用 Lambda 執行環境重用

## 安全最佳實踐

### ✅ 應該做的事

1. **定期輪替 token**（建議每 90 天）
2. **啟用 CloudTrail** 記錄 Secrets Manager 存取
3. **使用 IAM 最小權限原則**
4. **加密 CloudWatch Logs**
5. **定期審計 secret 存取日誌**

### ❌ 不應該做的事

1. **不要**將 token 硬編碼在程式碼中
2. **不要**將 `deploy-parameters.json` 提交到版本控制
3. **不要**在日誌中記錄完整的 token
4. **不要**使用明文環境變數儲存 token
5. **不要**在公開場合分享 secret ARN（雖然 ARN 本身不是敏感資訊，但最好保持隱私）

## 相關文件

- [AWS Secrets Manager 文件](https://docs.aws.amazon.com/secretsmanager/)
- [AWS SAM 參數覆寫](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-using-invoke.html)
- [Telegram Bot API - Webhook](https://core.telegram.org/bots/api#setwebhook)

## 支援

如遇到問題，請檢查：
1. CloudWatch Logs：`/aws/lambda/telegram-adapter-receiver`
2. CloudFormation Events
3. Secrets Manager Audit Logs（透過 CloudTrail）
