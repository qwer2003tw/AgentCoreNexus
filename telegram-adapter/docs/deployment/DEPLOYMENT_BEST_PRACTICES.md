# 部署最佳實踐指南

本文件說明如何安全地部署 Telegram Lambda 專案，並遵循最佳安全實踐。

## 📋 目錄

- [快速開始](#快速開始)
- [部署方法比較](#部署方法比較)
- [使用 deploy.sh 腳本](#使用-deploysh-腳本)
- [手動部署](#手動部署)
- [安全考量](#安全考量)
- [常見問題](#常見問題)
- [相關文件](#相關文件)

## 快速開始

### 首次部署

1. **準備 bot token**
   ```bash
   # 從 BotFather 獲取 bot token
   # 註：Webhook secret token 將由 CloudFormation 自動生成（64 字元，僅 A-Z/a-z/0-9）
   ```

2. **創建參數檔案**（`deploy-parameters.json`）
   ```json
   {
     "Parameters": {
       "TelegramBotToken": "your-bot-token-here"
     }
   }
   ```

3. **執行部署**
   ```bash
   # 賦予腳本執行權限
   chmod +x deploy.sh
   
   # 執行部署
   ./deploy.sh
   ```

### 後續部署（更新代碼）

```bash
# 腳本會自動從 Secrets Manager 讀取現有 bot token
# Webhook secret token 維持不變（CloudFormation 管理）
./deploy.sh
```

就這麼簡單！

## 部署方法比較

### 方法 1：使用 deploy.sh 腳本（✅ 強烈推薦）

**優點：**
- ✅ 自動判斷首次或更新部署
- ✅ 自動從 Secrets Manager 讀取現有 token
- ✅ 完整的錯誤處理和日誌
- ✅ 顯示彩色輸出，易於閱讀
- ✅ 自動驗證 AWS 憑證和工具
- ✅ 部署後自動顯示重要輸出

**缺點：**
- ⚠️ 需要 bash shell（Linux/macOS，Windows 需 WSL 或 Git Bash）

**適用情境：**
- 本地開發環境
- 手動部署流程

### 方法 2：使用 SAM CLI（進階使用者）

**優點：**
- ✅ 更細緻的控制
- ✅ 可用於 CI/CD pipeline
- ✅ 支援更多 SAM 選項

**缺點：**
- ⚠️ 需要手動管理參數
- ⚠️ 需要記住命令選項
- ⚠️ 每次都要提供參數（除非使用環境變數）

**適用情境：**
- CI/CD 自動化部署
- 需要特殊 SAM 選項的情況

### 方法 3：使用 AWS Console（不推薦）

**優點：**
- ✅ 視覺化界面

**缺點：**
- ❌ 手動操作，容易出錯
- ❌ 不適合頻繁部署
- ❌ 難以自動化
- ❌ 參數管理困難

## 使用 deploy.sh 腳本

### 腳本功能

`deploy.sh` 腳本提供以下功能：

1. **環境檢查**
   - 檢查必要工具（sam, aws, jq）
   - 驗證 AWS 憑證
   - 顯示 AWS Account ID 和 User ARN

2. **智能 Token 管理**
   - 首次部署：從 `deploy-parameters.json` 讀取 bot token，secret token 由 CloudFormation 自動生成
   - 更新部署：從 Secrets Manager 讀取現有 bot token
   - Fallback：如果 Secrets Manager 讀取失敗，改用參數檔案

3. **部署流程**
   - 執行 `sam build`
   - 執行 `sam deploy` 並傳遞參數
   - 顯示部署輸出和 Webhook URL

4. **錯誤處理**
   - 遇到錯誤立即停止（`set -e`）
   - 彩色日誌輸出，易於識別問題
   - 清晰的錯誤訊息

### 腳本配置

您可以在腳本開頭修改配置：

```bash
# 配置
STACK_NAME="telegram-adapter"      # CloudFormation stack 名稱
REGION="ap-northeast-1"           # AWS 區域
PARAM_FILE="deploy-parameters.json"  # 參數檔案路徑
```

### 使用範例

**首次部署：**
```bash
# 1. 創建參數檔案（只需 bot token，secret token 會自動生成）
cat > deploy-parameters.json <<EOF
{
  "Parameters": {
    "TelegramBotToken": "123456:ABC-DEF..."
  }
}
EOF

# 2. 執行部署
chmod +x deploy.sh
./deploy.sh
```

**更新代碼後重新部署：**
```bash
# 修改代碼後
git add .
git commit -m "Update handler logic"

# 重新部署（自動從 Secrets Manager 讀取 bot token）
./deploy.sh
```

**更新 Bot Token：**
```bash
# 如果想要更新 bot token，確保 deploy-parameters.json 有新值
# 然後刪除現有 stack 後重新部署（會重新生成 secret token）
aws cloudformation delete-stack --stack-name telegram-adapter
./deploy.sh
```

## 手動部署

如果您偏好手動控制部署流程，可以使用以下方法：

### 使用環境變數

```bash
# 設定環境變數（只需 bot token，secret token 會自動生成）
export TELEGRAM_BOT_TOKEN="your-bot-token"

# 建置
sam build

# 部署
sam deploy \
  --stack-name telegram-adapter \
  --region ap-northeast-1 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    TelegramBotToken="$TELEGRAM_BOT_TOKEN"
```

### 使用參數檔案

```bash
# 建置
sam build

# 部署（首次）
sam deploy \
  --guided \
  --parameter-overrides file://deploy-parameters.json

# 後續部署
sam deploy \
  --parameter-overrides file://deploy-parameters.json
```

### 從 Secrets Manager 讀取（後續部署）

```bash
# 讀取現有 bot token
BOT_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id telegram-adapter-bot-token \
  --region ap-northeast-1 \
  --query 'SecretString' --output text | jq -r .token)

# 部署（secret token 由 CloudFormation 管理，無需提供）
sam build
sam deploy \
  --stack-name telegram-adapter \
  --region ap-northeast-1 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    TelegramBotToken="$BOT_TOKEN"
```

## 安全考量

### ✅ 應該做的事

1. **保護敏感檔案**
   ```bash
   # 確保這些檔案在 .gitignore 中
   deploy-parameters.json
   *.sh
   samconfig.toml  # 如果包含敏感資訊
   ```

2. **自動生成強密碼**
   ```bash
   # Webhook secret token 已由 CloudFormation 自動生成
   # 使用 64 字元，僅包含 A-Z/a-z/0-9
   # 無需手動產生
   ```

3. **定期輪替 Token**
   ```bash
   # 更新 Secrets Manager 中的 token
   aws secretsmanager update-secret \
     --secret-id telegram-adapter-bot-token \
     --secret-string '{"token": "NEW_TOKEN"}'
   ```

4. **啟用 CloudTrail**
   - 記錄所有 Secrets Manager 存取
   - 定期審計存取日誌

5. **使用最小權限原則**
   - Lambda 只有讀取 Secrets Manager 的權限
   - 不要給予不必要的權限

6. **加密日誌**
   ```yaml
   # 在 template.yaml 中啟用 CloudWatch Logs 加密
   TelegramReceiverLogGroup:
     Type: AWS::Logs::LogGroup
     Properties:
       KmsKeyId: !Ref LogsKmsKey  # 使用 KMS 加密
   ```

### ❌ 不應該做的事

1. **不要**將 token 硬編碼在程式碼中
   ```python
   # ❌ 錯誤
   BOT_TOKEN = "123456:ABC-DEF..."
   
   # ✅ 正確
   from secrets_manager import get_telegram_bot_token
   bot_token = get_telegram_bot_token()
   ```

2. **不要**將 `deploy-parameters.json` 提交到版本控制
   ```bash
   # 確認檔案被忽略
   git check-ignore deploy-parameters.json
   # 應該輸出: deploy-parameters.json
   ```

3. **不要**在日誌中記錄完整 token
   ```python
   # ❌ 錯誤
   logger.info(f"Using token: {token}")
   
   # ✅ 正確
   logger.info(f"Using token: {token[:10]}...")
   ```

4. **不要**在 samconfig.toml 中儲存 token
   ```toml
   # ❌ 錯誤
   parameter_overrides = "TelegramBotToken=\"123456:ABC...\""
   
   # ✅ 正確
   # 不包含任何 parameter_overrides，或使用環境變數
   ```

5. **不要**分享 Secrets Manager ARN（雖然不是敏感資訊，但最好保密）

## 常見問題

### Q1: 每次部署都要提供參數嗎？

**A:** 不需要。使用 `deploy.sh` 腳本：
- 首次部署：從 `deploy-parameters.json` 讀取 bot token（secret token 自動生成）
- 後續部署：自動從 Secrets Manager 讀取現有 bot token

### Q2: 如何更新 token？

**A:** 有兩種方法：

**方法 1：直接更新 Secrets Manager（推薦）**
```bash
aws secretsmanager update-secret \
  --secret-id telegram-adapter-bot-token \
  --secret-string '{"token": "NEW_TOKEN"}'
```
不需要重新部署 stack。

**方法 2：透過重新部署**
```bash
# 更新 deploy-parameters.json
# 然後執行
./deploy.sh
```

### Q3: samconfig.toml 是否安全？

**A:** 我們提供的 `samconfig.toml` 是安全的，因為：
- 只包含非敏感資訊（stack name, region 等）
- 不包含任何 token
- 已在 `.gitignore` 中（以防萬一被誤用）

### Q4: 如何在 CI/CD 中使用？

**A:** 在 CI/CD pipeline 中（如 GitHub Actions）：

**方法 1：使用 GitHub Secrets（首次部署）**
```yaml
# .github/workflows/deploy.yml
- name: Deploy to AWS
  env:
    TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
  run: |
    sam build
    sam deploy \
      --no-confirm-changeset \
      --parameter-overrides \
        TelegramBotToken="$TELEGRAM_BOT_TOKEN"
    # 註：Secret token 由 CloudFormation 自動生成
```

**方法 2：從 AWS Secrets Manager 讀取（後續部署）**
```yaml
- name: Get bot token from AWS Secrets Manager
  run: |
    BOT_TOKEN=$(aws secretsmanager get-secret-value \
      --secret-id telegram-adapter-bot-token \
      --query 'SecretString' --output text | jq -r .token)
    echo "::add-mask::$BOT_TOKEN"
    echo "BOT_TOKEN=$BOT_TOKEN" >> $GITHUB_ENV

- name: Deploy to AWS
  run: |
    sam build
    sam deploy \
      --no-confirm-changeset \
      --parameter-overrides \
        TelegramBotToken="$BOT_TOKEN"
```

### Q5: 部署腳本失敗怎麼辦？

**A:** 檢查以下項目：

1. **檢查工具是否安裝**
   ```bash
   sam --version
   aws --version
   jq --version
   ```

2. **檢查 AWS 憑證**
   ```bash
   aws sts get-caller-identity
   ```

3. **檢查參數檔案**
   ```bash
   cat deploy-parameters.json
   jq . deploy-parameters.json  # 驗證 JSON 格式
   ```

4. **查看詳細錯誤**
   ```bash
   # 腳本會顯示彩色的錯誤訊息
   # 紅色 [ERROR] 表示錯誤
   # 黃色 [WARNING] 表示警告
   ```

5. **查看 CloudFormation Events**
   ```bash
   aws cloudformation describe-stack-events \
     --stack-name telegram-adapter \
     --max-items 20
   ```

### Q6: 如何切換到不同的 AWS 帳號？

**A:** 修改 AWS profile 或憑證：

```bash
# 方法 1：使用不同的 profile
export AWS_PROFILE=production
./deploy.sh

# 方法 2：臨時使用不同的憑證
AWS_ACCESS_KEY_ID=xxx AWS_SECRET_ACCESS_KEY=yyy ./deploy.sh

# 方法 3：修改腳本中的 region
# 編輯 deploy.sh，修改 REGION 變數
```

### Q7: deploy.sh 和 samconfig.toml 的關係？

**A:** 
- `deploy.sh`：主要用於本地開發，提供智能參數管理
- `samconfig.toml`：SAM CLI 的配置檔，儲存非敏感設定
- 兩者可以同時使用，`deploy.sh` 會使用 `samconfig.toml` 中的設定

### Q8: 如何獲取自動生成的 webhook secret token？

**A:** Webhook secret token 是由 CloudFormation 自動生成的，您可以通過以下方式獲取：

```bash
# 從 Secrets Manager 讀取
aws secretsmanager get-secret-value \
  --secret-id telegram-adapter-secret-token \
  --region ap-northeast-1 \
  --query 'SecretString' --output text | jq -r .token

# 或使用 CloudFormation 輸出（部署後會自動顯示）
aws cloudformation describe-stacks \
  --stack-name telegram-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookSecretTokenArn`].OutputValue' \
  --output text
```

**注意：** 這個 token 在首次部署時生成，後續更新部署時會保持不變。

### Q9: 如何驗證部署成功？

**A:** 使用以下命令：

```bash
# 1. 檢查 Lambda 函數
aws lambda get-function --function-name telegram-adapter-receiver

# 2. 檢查環境變數（應該只有 ARN，沒有 token）
aws lambda get-function-configuration \
  --function-name telegram-adapter-receiver \
  --query 'Environment.Variables'

# 3. 測試 Secrets Manager 存取
aws secretsmanager get-secret-value \
  --secret-id telegram-adapter-bot-token \
  --query 'SecretString' --output text | jq .

# 4. 檢查 CloudWatch Logs
aws logs tail /aws/lambda/telegram-adapter-receiver --follow

# 5. 測試 webhook
curl -X POST https://YOUR_API_GATEWAY_URL/Prod/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: YOUR_SECRET_TOKEN" \
  -d @test_payload.json
```

## 相關文件

- [SECRETS_MANAGER_DEPLOYMENT.md](./SECRETS_MANAGER_DEPLOYMENT.md) - Secrets Manager 詳細部署指南
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - 一般部署指南
- [README.md](./README.md) - 專案總覽
- [AWS SAM 官方文件](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Secrets Manager 文件](https://docs.aws.amazon.com/secretsmanager/)

## 總結

**推薦的部署流程：**

1. ✅ 首次部署使用 `./deploy.sh`
2. ✅ 後續部署繼續使用 `./deploy.sh`（自動從 Secrets Manager 讀取）
3. ✅ 所有敏感檔案都在 `.gitignore` 中
4. ✅ Token 儲存在 Secrets Manager，不在環境變數或程式碼中
5. ✅ 定期輪替 token，使用 `aws secretsmanager update-secret`

遵循這些最佳實踐，您的部署將會既安全又便利！
