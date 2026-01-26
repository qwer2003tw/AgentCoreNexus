# Web Channel Deployment Guide

完整的部署指南，從零開始部署 Web Channel 功能。

---

## 📋 部署前準備

### 1. 確認現有系統正常運作

```bash
# 檢查 telegram-adapter stack
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name telegram-adapter-receiver \
  --query 'Stacks[0].StackStatus'

# 檢查 telegram-unified-bot stack  
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name telegram-unified-bot \
  --query 'Stacks[0].StackStatus'

# 結果應該是: CREATE_COMPLETE 或 UPDATE_COMPLETE
```

### 2. 記錄現有資源名稱

```bash
# EventBridge Bus 名稱
aws events list-event-buses --region us-west-2 \
  --query 'EventBuses[?contains(Name, `telegram`)].Name'

# Processor Lambda 名稱
aws lambda list-functions --region us-west-2 \
  --query 'Functions[?contains(FunctionName, `processor`)].FunctionName'
```

---

## 🚀 Phase 1: 部署 Web Channel Stack

### Step 1.1: 準備 Lambda 代碼

```bash
cd /home/ec2-user/Projects/AgentCoreNexus/dev-in-progress/web-adapter-expansion

# 為每個 Lambda 目錄安裝依賴
cd lambdas/websocket
pip3.12 install -r requirements.txt -t .

cd ../rest
pip3.12 install -r requirements.txt -t .

cd ../router
pip3.12 install -r requirements.txt -t .
```

### Step 1.2: 驗證 SAM Template

```bash
cd infrastructure
sam validate -t web-adapter-template.yaml
```

### Step 1.3: 建構和部署

```bash
sam build -t web-adapter-template.yaml

sam deploy \
  --template-file web-adapter-template.yaml \
  --stack-name agentcore-web-adapter \
  --region us-west-2 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --parameter-overrides \
    Environment=dev \
    ExistingEventBusName=telegram-adapter-receiver-events \
    ExistingProcessorFunctionName=telegram-unified-bot-processor
```

### Step 1.4: 記錄 Outputs

```bash
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs' > web-adapter-outputs.json

cat web-adapter-outputs.json
```

記下以下值：
- `WebSocketApiEndpoint` - WebSocket URL
- `RestApiEndpoint` - REST API URL
- `JWTSecretArn` - JWT Secret ARN
- 所有 Table 名稱

---

## 🔄 Phase 2: 整合 ai-processor

### Step 2.1: 修改 Memory Service

**檔案**: `ai-processor/services/memory_service.py`

```python
# 在 get_session_manager 方法中添加類型檢查
def get_session_manager(self, user_info: dict[str, Any] | Any) -> Any | None:
    """
    取得 Session Manager
    
    Args:
        user_info: 包含 unified_user_id 的字典或 context 物件
    """
    if not self.enabled:
        logger.info("ℹ️ Memory 未啟用")
        return None
    
    try:
        # 支援新格式（dict）和舊格式（context object）
        if isinstance(user_info, dict):
            # 新格式：來自 Web 或已綁定的 Telegram
            session_id = user_info.get('unified_user_id', settings.DEFAULT_SESSION_ID)
            actor_id = user_info.get('identifier', 'user')
        else:
            # 舊格式：context object（向後相容）
            session_id = getattr(user_info, "session_id", settings.DEFAULT_SESSION_ID)
            actor_id = self._extract_actor_id(user_info)
        
        # 建立 Memory 配置
        memory_config = self._create_memory_config(session_id, actor_id)
        session_manager = self._session_manager_class(memory_config, settings.AWS_REGION)
        
        logger.info(f"✅ Session Manager 建立成功 (Session: {session_id})")
        return session_manager
        
    except Exception as e:
        logger.error(f"❌ Session Manager 建立失敗: {str(e)}", exc_info=True)
        return None
```

### Step 2.2: 修改 Processor Entry

**檔案**: `ai-processor/processor_entry.py`

在檔案頂部添加：

```python
import uuid
import boto3

# 環境變數
BINDINGS_TABLE = os.getenv('BINDINGS_TABLE', '')

# 初始化 bindings table（可選）
bindings_table = None
if BINDINGS_TABLE:
    try:
        bindings_table = boto3.resource('dynamodb').Table(BINDINGS_TABLE)
        logger.info(f"✅ Bindings table initialized: {BINDINGS_TABLE}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize bindings table: {str(e)}")
```

添加函數：

```python
def get_unified_user_id(normalized: dict) -> str:
    """
    獲取或生成 unified_user_id
    
    Args:
        normalized: 統一消息格式
        
    Returns:
        unified_user_id (UUID string)
    """
    # 如果消息已包含 unified_user_id（來自 Web）
    user_info = normalized.get('user', {})
    if 'unified_user_id' in user_info:
        return user_info['unified_user_id']
    
    # Telegram 消息：嘗試從 bindings 查詢
    channel = normalized.get('channel', {})
    if channel.get('type') == 'telegram' and bindings_table:
        telegram_chat_id = int(channel.get('channel_id', 0))
        
        try:
            response = bindings_table.query(
                IndexName='telegram_chat_id-index',
                KeyConditionExpression='telegram_chat_id = :chat_id',
                ExpressionAttributeValues={':chat_id': telegram_chat_id}
            )
            
            items = response.get('Items', [])
            if items:
                unified_user_id = items[0]['unified_user_id']
                logger.info(f"✅ Found binding: Telegram {telegram_chat_id} -> {unified_user_id}")
                return unified_user_id
        except Exception as e:
            logger.warning(f"⚠️ Error querying binding: {str(e)}")
    
    # 未綁定或查詢失敗：生成臨時 ID
    # 使用通道類型 + ID 作為臨時識別
    temp_id = f"{channel.get('type', 'unknown')}:{channel.get('channel_id', str(uuid.uuid4()))}"
    logger.info(f"ℹ️ Using temporary ID: {temp_id}")
    return temp_id
```

修改 `process` 函數：

```python
def process(normalized):
    channel_type = normalized["channel"]["type"]
    user_text = normalized["content"]["text"]
    
    # 獲取 unified_user_id
    unified_user_id = get_unified_user_id(normalized)
    
    try:
        # 準備 user_info
        user_info = {
            'unified_user_id': unified_user_id,
            'identifier': normalized.get('user', {}).get('identifier', 'user')
        }
        
        # 取得 session manager（使用新格式）
        session = memory.get_session_manager(user_info)
        
        # 呼叫 Agent
        response = agent.process_message(user_text)
        
        # 發布完成事件
        completed = {
            "original": normalized,
            "response": response,
            "channel": channel_type
        }
        evb.put_events(Entries=[{
            "Source": "agent-processor",
            "DetailType": "message.completed",
            "Detail": json.dumps(completed),
            "EventBusName": EVENT_BUS_NAME
        }])
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        # 錯誤處理...
```

### Step 2.3: 更新環境變數

```bash
# 獲取 bindings table 名稱
BINDINGS_TABLE=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`UserBindingsTableName`].OutputValue' \
  --output text)

# 更新 processor Lambda
aws lambda update-function-configuration \
  --region us-west-2 \
  --function-name telegram-unified-bot-processor \
  --environment Variables="{
    BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0,
    BROWSER_ENABLED=true,
    EVENT_BUS_NAME=telegram-adapter-receiver-events,
    LOG_LEVEL=INFO,
    BINDINGS_TABLE=$BINDINGS_TABLE
  }"

# 等待更新完成
aws lambda wait function-updated \
  --region us-west-2 \
  --function-name telegram-unified-bot-processor
```

### Step 2.4: 重新部署 processor（應用代碼變更）

```bash
cd ai-processor
sam build
sam deploy --stack-name telegram-unified-bot \
  --region us-west-2 \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --no-confirm-changeset
```

---

## 📱 Phase 3: 整合 telegram-adapter

### Step 3.1: 複製 bind 指令處理器

```bash
cp dev-in-progress/web-adapter-expansion/telegram-integration/bind_handler.py \
   telegram-adapter/src/commands/handlers/bind_handler.py
```

### Step 3.2: 註冊指令

編輯 `telegram-adapter/src/commands/router.py`：

```python
from commands.handlers.bind_handler import handle_bind_command

COMMANDS = {
    # ... 現有指令
    
    "bind": {
        "handler": lambda chat_id, username, args: handle_bind_command(chat_id, username, args),
        "permission": Permission.ALLOWLIST,
        "description": "綁定 Telegram 與 Web 帳號"
    }
}
```

### Step 3.3: 更新環境變數

獲取 table 名稱：

```bash
BINDINGS_TABLE=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`UserBindingsTableName`].OutputValue' \
  --output text)

BINDING_CODES_TABLE=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`BindingCodesTableName`].OutputValue' \
  --output text) 

echo "BINDINGS_TABLE=$BINDINGS_TABLE"
echo "BINDING_CODES_TABLE=$BINDING_CODES_TABLE"
```

修改 `telegram-adapter/template.yaml`：

```yaml
TelegramReceiverFunction:
  Type: AWS::Serverless::Function
  Properties:
    # ... 現有配置
    Environment:
      Variables:
        # 現有變數
        TELEGRAM_SECRETS_ARN: !Ref TelegramSecrets
        EVENT_BUS_NAME: telegram-adapter-receiver-events
        ALLOWLIST_TABLE_NAME: !Ref AllowlistTable
        STACK_NAME: !Ref AWS::StackName
        # 新增變數
        BINDINGS_TABLE: !ImportValue agentcore-web-adapter-UserBindingsTable
        BINDING_CODES_TABLE: !ImportValue agentcore-web-adapter-BindingCodesTable
    
    Policies:
      # ... 現有策略
      # 新增 DynamoDB 權限
      - DynamoDBReadPolicy:
          TableName: !ImportValue agentcore-web-adapter-UserBindingsTable
      - DynamoDBCrudPolicy:
          TableName: !ImportValue agentcore-web-adapter-BindingCodesTable
```

### Step 3.4: 重新部署 telegram-adapter

```bash
cd telegram-adapter
sam build
sam deploy --stack-name telegram-adapter-receiver \
  --region us-west-2 \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --no-confirm-changeset
```

---

## 🌐 Phase 4: 部署前端

### Step 4.1: 配置環境變數

```bash
cd dev-in-progress/web-adapter-expansion/frontend

# 複製環境變數範本
cp .env.example .env

# 獲取 API endpoints
REST_API=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`RestApiEndpoint`].OutputValue' \
  --output text)

WS_API=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`WebSocketApiEndpoint`].OutputValue' \
  --output text)

# 更新 .env
echo "VITE_API_ENDPOINT=$REST_API" > .env
echo "VITE_WS_ENDPOINT=$WS_API" >> .env
```

### Step 4.2: 建構前端

```bash
# 安裝依賴
npm install

# 建構生產版本
npm run build

# 結果在 dist/ 目錄
```

### Step 4.3: 創建 S3 Bucket

```bash
# 創建 bucket（名稱必須全球唯一）
BUCKET_NAME="agentcore-web-frontend-$(date +%s)"

aws s3 mb s3://$BUCKET_NAME --region us-west-2

# 配置為靜態網站
aws s3 website s3://$BUCKET_NAME \
  --index-document index.html \
  --error-document index.html

# 設置公開讀取權限（僅用於靜態資源）
aws s3api put-bucket-policy \
  --bucket $BUCKET_NAME \
  --policy "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Sid\": \"PublicReadGetObject\",
      \"Effect\": \"Allow\",
      \"Principal\": \"*\",
      \"Action\": \"s3:GetObject\",
      \"Resource\": \"arn:aws:s3:::$BUCKET_NAME/*\"
    }]
  }"
```

### Step 4.4: 上傳前端

```bash
# 上傳到 S3
aws s3 sync dist/ s3://$BUCKET_NAME/ --delete

# 設置 cache control
aws s3 cp dist/ s3://$BUCKET_NAME/ \
  --recursive \
  --cache-control "public, max-age=31536000" \
  --exclude "index.html"

# index.html 不要 cache
aws s3 cp dist/index.html s3://$BUCKET_NAME/ \
  --cache-control "no-cache"
```

### Step 4.5: 設置 CloudFront（可選但推薦）

創建 CloudFront distribution：

```bash
# 創建 distribution（簡化版，實際應該用 CloudFormation）
aws cloudfront create-distribution \
  --origin-domain-name $BUCKET_NAME.s3.us-west-2.amazonaws.com \
  --default-root-object index.html

# 獲取 distribution domain name
CLOUDFRONT_DOMAIN=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[0].DomainName=='$BUCKET_NAME.s3.us-west-2.amazonaws.com'].DomainName" \
  --output text)

echo "前端 URL: https://$CLOUDFRONT_DOMAIN"
```

---

## 🧪 Phase 5: 測試部署

### Test 1: 創建 Web 用戶

```bash
# 首先需要一個 admin token（從現有 Telegram admin 用戶獲取或手動創建）

# 手動創建第一個 admin 用戶
WEB_USERS_TABLE=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`WebUsersTableName`].OutputValue' \
  --output text)

# 生成 bcrypt hash（需要 Python）
python3 -c "
import bcrypt
password = 'InitialAdmin123!'
hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))
print(hash.decode('utf-8'))
" > admin_hash.txt

ADMIN_HASH=$(cat admin_hash.txt)

# 插入 admin 用戶
aws dynamodb put-item \
  --region us-west-2 \
  --table-name $WEB_USERS_TABLE \
  --item "{
    \"email\": {\"S\": \"admin@agentcore.local\"},
    \"password_hash\": {\"S\": \"$ADMIN_HASH\"},
    \"enabled\": {\"BOOL\": true},
    \"role\": {\"S\": \"admin\"},
    \"require_password_change\": {\"BOOL\": false},
    \"created_at\": {\"S\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}
  }"

echo "✅ Admin 用戶已創建"
echo "Email: admin@agentcore.local"
echo "Password: InitialAdmin123!"
```

### Test 2: 登入測試

```bash
REST_API=$(cat web-adapter-outputs.json | grep RestApiEndpoint)

# 登入
curl -X POST "$REST_API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@agentcore.local",
    "password": "InitialAdmin123!"
  }' | jq '.'

# 應該返回 token 和用戶資訊
```

### Test 3: WebSocket 連接測試

```bash
# 安裝 wscat
npm install -g wscat

# 使用獲得的 token 連接
WS_API=$(cat web-adapter-outputs.json | grep WebSocketApiEndpoint)
TOKEN="YOUR_JWT_TOKEN"

wscat -c "$WS_API?token=$TOKEN"

# 連接成功後，發送消息
> {"action": "sendMessage", "message": "Hello from Web"}
```

### Test 4: /bind 指令測試

```bash
# 1. 在 Web 生成綁定碼
curl -X POST "$REST_API/binding/generate-code" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# 應該返回: {"code": "123456", ...}

# 2. 在 Telegram 發送
# /bind 123456

# 3. 檢查綁定狀態
curl "$REST_API/binding/status" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### Test 5: 前端測試

在瀏覽器打開：
- S3 URL: `http://$BUCKET_NAME.s3-website-us-west-2.amazonaws.com`
- 或 CloudFront URL: `https://$CLOUDFRONT_DOMAIN`

測試流程：
1. 登入
2. 發送消息
3. 檢查是否收到 AI 回應
4. 檢查歷史記錄

---

## 📊 部署驗證檢查清單

### 基礎設施
- [ ] Web Channel Stack: CREATE_COMPLETE
- [ ] 所有 5 個 DynamoDB tables 已創建
- [ ] WebSocket API 可訪問
- [ ] REST API 可訪問
- [ ] JWT Secret 已創建

### Lambda 函數
- [ ] 所有 Lambda 狀態：Active
- [ ] 所有 Lambda LastUpdateStatus: Successful
- [ ] CloudWatch Logs 無錯誤

### 整合
- [ ] processor Lambda 有 BINDINGS_TABLE 環境變數
- [ ] receiver Lambda 有 BINDINGS_TABLE 和 BINDING_CODES_TABLE
- [ ] Response Router 監聽 message.completed 事件

### 功能
- [ ] Admin 可登入 Web 界面
- [ ] 可創建新用戶
- [ ] WebSocket 連接成功
- [ ] 消息可以發送和接收
- [ ] /bind 指令可執行
- [ ] 綁定後 Memory 共享
- [ ] 歷史記錄正確保存

---

## 🔧 Troubleshooting

### 問題 1: SAM deploy 失敗

**檢查**：
```bash
# 查看詳細錯誤
sam deploy --debug

# 常見問題：
# 1. 權限不足
# 2. ImportValue 找不到（檢查 telegram-adapter stack）
# 3. 資源名稱衝突
```

### 問題 2: Lambda 更新後仍有舊行為

**解決**：
```bash
# 清除 Lambda 緩存
aws lambda update-function-code \
  --region us-west-2 \
  --function-name FUNCTION_NAME \
  --s3-bucket BUCKET \
  --s3-key KEY \
  --publish

# 等待更新
aws lambda wait function-updated \
  --region us-west-2 \
  --function-name FUNCTION_NAME
```

### 問題 3: 前端無法連接 API

**檢查**：
1. `.env` 檔案配置正確
2. CORS 設置正確
3. Lambda Authorizer 運作正常

```bash
# 測試 REST API
curl "$REST_API/auth/login" -v

# 應該看到 CORS headers
```

### 問題 4: WebSocket 連接失敗

**檢查**：
```bash
# 查看 connect Lambda 日誌
aws logs tail /aws/lambda/agentcore-web-adapter-ws-connect \
  --region us-west-2 --since 10m --follow

# 常見原因：
# 1. JWT token 無效
# 2. 用戶未啟用
# 3. DynamoDB 權限問題
```

---

## 🔄 回滾流程

如果需要回滾：

```bash
# 1. 恢復 telegram-adapter（移除 bind 指令）
cd telegram-adapter
git checkout HEAD~1 src/commands/handlers/bind_handler.py
git checkout HEAD~1 src/commands/router.py
sam deploy --stack-name telegram-adapter-receiver ...

# 2. 恢復 ai-processor（Memory Service）
cd ai-processor
git checkout HEAD~1 services/memory_service.py
git checkout HEAD~1 processor_entry.py
sam deploy --stack-name telegram-unified-bot ...

# 3. 刪除 Web Channel Stack
aws cloudformation delete-stack \
  --region us-west-2 \
  --stack-name agentcore-web-adapter

# 4. 刪除前端 S3 bucket
aws s3 rb s3://$BUCKET_NAME --force
```

---

## 📝 部署後配置

### 1. 創建第一個普通用戶

使用 admin 帳號在 Web 界面或 API：

```bash
curl -X POST "$REST_API/admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "role": "user"
  }' | jq '.'

# 記下 temporary_password
```

### 2. 設置 CloudWatch Alarms

```bash
# Lambda 錯誤率告警
aws cloudwatch put-metric-alarm \
  --alarm-name web-adapter-lambda-errors \
  --alarm-description "Web Channel Lambda error rate > 1%" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold

# 其他告警...
```

### 3. 更新文檔

記錄實際的：
- API endpoints
- S3 bucket 名稱
- CloudFront domain
- Admin 帳號資訊（安全保存）

---

## 🎉 部署完成

完成以上所有步驟後，Web Channel 功能已完全部署並可使用！

**後續工作**：
- 監控系統運作
- 收集用戶反饋
- 持續優化性能
- 實現 Phase 2 功能

---

**版本**: 1.0  
**最後更新**: 2026-01-08  
**狀態**: Ready for Deployment