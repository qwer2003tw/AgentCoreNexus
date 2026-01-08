# Quick Start Guide - 快速開始

最快速度啟動 Web Channel 功能的指南。

---

## ⚡ 5 分鐘快速部署

### 前置條件
- AWS CLI 已配置
- SAM CLI 已安裝
- Node.js 18+ 已安裝
- Python 3.11 已安裝

---

## 🚀 一鍵部署腳本

### Step 1: 部署 Backend

```bash
cd /home/ec2-user/Projects/AgentCoreNexus/dev-in-progress/web-channel-expansion

# 運行部署腳本
./scripts/deploy-backend.sh
```

### Step 2: 部署 Frontend

```bash
# 運行部署腳本
./scripts/deploy-frontend.sh
```

### Step 3: 創建首個用戶

```bash
# 運行用戶創建腳本
./scripts/create-admin-user.sh admin@example.com
```

---

## 📋 詳細步驟（如果腳本失敗）

### Backend 部署

```bash
# 1. 進入基礎設施目錄
cd infrastructure

# 2. 安裝 Lambda 依賴
cd ../lambdas/websocket && pip3.11 install -r requirements.txt -t . && cd ../../infrastructure
cd ../lambdas/rest && pip3.11 install -r requirements.txt -t . && cd ../../infrastructure  
cd ../lambdas/router && pip3.11 install -r requirements.txt -t . && cd ../../infrastructure

# 3. 部署
sam build -t web-channel-template.yaml
sam deploy \
  --template-file web-channel-template.yaml \
  --stack-name agentcore-web-channel \
  --region us-west-2 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --parameter-overrides \
    Environment=dev \
    ExistingEventBusName=telegram-lambda-receiver-events \
    ExistingProcessorFunctionName=telegram-unified-bot-processor \
  --no-confirm-changeset
```

### Frontend 部署

```bash
cd frontend

# 1. 獲取 API endpoints
REST_API=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].Outputs[?OutputKey==`RestApiEndpoint`].OutputValue' \
  --output text)

WS_API=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].Outputs[?OutputKey==`WebSocketApiEndpoint`].OutputValue' \
  --output text)

# 2. 配置環境
echo "VITE_API_ENDPOINT=$REST_API" > .env
echo "VITE_WS_ENDPOINT=$WS_API" >> .env

# 3. 安裝和建構
npm install
npm run build

# 4. 部署到 S3（需要先創建 bucket）
BUCKET_NAME="agentcore-web-$(date +%s)"
aws s3 mb s3://$BUCKET_NAME --region us-west-2
aws s3 website s3://$BUCKET_NAME --index-document index.html
aws s3 sync dist/ s3://$BUCKET_NAME/

echo "Frontend URL: http://$BUCKET_NAME.s3-website-us-west-2.amazonaws.com"
```

### 創建 Admin 用戶

```bash
# 獲取 table 名稱
WEB_USERS_TABLE=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].Outputs[?OutputKey==`WebUsersTableName`].OutputValue' \
  --output text)

# 生成密碼 hash
python3 << 'EOF'
import bcrypt
password = 'Admin123!'
hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))
print(hash.decode('utf-8'))
EOF

# 複製上面的 hash，然後執行：
ADMIN_HASH="<paste_hash_here>"

aws dynamodb put-item \
  --region us-west-2 \
  --table-name $WEB_USERS_TABLE \
  --item "{
    \"email\": {\"S\": \"admin@example.com\"},
    \"password_hash\": {\"S\": \"$ADMIN_HASH\"},
    \"enabled\": {\"BOOL\": true},
    \"role\": {\"S\": \"admin\"},
    \"require_password_change\": {\"BOOL\": false},
    \"created_at\": {\"S\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}
  }"

echo "✅ Admin 用戶已創建！"
echo "Email: admin@example.com"
echo "Password: Admin123!"
```

---

## 🧪 快速測試

### 1. 測試 API

```bash
REST_API=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].Outputs[?OutputKey==`RestApiEndpoint`].OutputValue' \
  --output text)

# 登入
curl -X POST "$REST_API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin123!"}' \
  | jq '.'

# 保存 token
TOKEN="<paste_token_here>"

# 測試創建用戶
curl -X POST "$REST_API/admin/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","role":"user"}' \
  | jq '.'
```

### 2. 測試 WebSocket

```bash
# 安裝 wscat
npm install -g wscat

# 連接
WS_API=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].Outputs[?OutputKey==`WebSocketApiEndpoint`].OutputValue' \
  --output text)

wscat -c "$WS_API?token=$TOKEN"

# 發送消息
> {"action":"sendMessage","message":"Hello"}
```

### 3. 測試前端

打開瀏覽器：
```
http://<bucket-name>.s3-website-us-west-2.amazonaws.com
```

1. 登入（admin@example.com / Admin123!）
2. 發送消息測試
3. 檢查歷史記錄
4. 測試導出功能
5. 測試綁定功能

---

## 🔍 檢查部署狀態

```bash
# 檢查 stack 狀態
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].StackStatus'

# 檢查所有 Lambda 狀態
aws lambda list-functions --region us-west-2 \
  --query 'Functions[?contains(FunctionName,`agentcore-web-channel`)].{Name:FunctionName,State:State}' \
  --output table

# 檢查 API endpoints
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].Outputs[?contains(OutputKey,`Endpoint`)].{Key:OutputKey,Value:OutputValue}' \
  --output table
```

---

## 🐛 快速 Troubleshooting

### Lambda 錯誤
```bash
# 查看最近日誌
FUNCTION_NAME="agentcore-web-channel-ws-connect"
aws logs tail /aws/lambda/$FUNCTION_NAME --region us-west-2 --since 5m
```

### API 連接問題
```bash
# 測試 CORS
curl -X OPTIONS "$REST_API/auth/login" -v
```

### 前端無法載入
```bash
# 檢查 S3 bucket 政策
aws s3api get-bucket-policy --bucket $BUCKET_NAME
```

---

## 📚 完整文檔

如需詳細資訊，請參考：

- **部署**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **整合**: [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)
- **架構**: [ARCHITECTURE.md](./ARCHITECTURE.md)
- **前端**: [frontend/README.md](./frontend/README.md)

---

## 🎯 成功標準

部署成功後，應該能夠：

✅ 在 Web 界面登入  
✅ 發送消息並收到 AI 回應  
✅ 查看對話歷史  
✅ 導出對話記錄  
✅ 生成綁定碼  
✅ 在 Telegram 執行 /bind 指令  
✅ 綁定後兩邊共享記憶  

---

**預計總時間**: 30-60 分鐘（首次部署）  
**難度**: 🟢 簡單（腳本自動化 + 詳細文檔）  
**風險**: 🟡 中等（需要測試整合）

**最後更新**: 2026-01-08