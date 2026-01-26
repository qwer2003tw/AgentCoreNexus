# Web Adapter 部署信息

**部署時間**: 2026-01-25 13:49:08 UTC  
**Stack 名稱**: agentcore-web-adapter  
**狀態**: CREATE_COMPLETE ✅

## 🔗 API Endpoints

### REST API
```
https://jooap0xv8l.execute-api.us-west-2.amazonaws.com/prod
```

### WebSocket API
```
wss://356rrmw4pg.execute-api.us-west-2.amazonaws.com/prod
```

### Frontend URL
```
https://d1p3mmbx4pyq2j.cloudfront.net
```

## 📊 DynamoDB Tables

| Table | Name |
|-------|------|
| Web Users | agentcore-web-adapter-web-users |
| User Bindings | agentcore-web-adapter-user-bindings |
| Conversations | agentcore-web-adapter-conversations |
| Conversation History | agentcore-web-adapter-conversation-history |
| Binding Codes | agentcore-web-adapter-binding-codes |
| WebSocket Connections | agentcore-web-adapter-websocket-connections |

## 🔑 Secrets

**JWT Secret ARN**:
```
arn:aws:secretsmanager:us-west-2:190825685292:secret:agentcore-web-adapter/jwt-secret-cAxduI
```

## ☁️ CloudFront

**Distribution ID**: ECXFNSJ8U745V  
**Domain**: d1p3mmbx4pyq2j.cloudfront.net

## 📦 S3 Buckets

**Frontend Bucket**: agentcore-web-adapter-frontend-190825685292  
**Attachments Bucket**: agentcore-web-adapter-attachments-190825685292

## 👥 測試帳號（6 個）

### E2E 測試帳號（4 個）- 用於並行測試
```
aws-e2e-test1@test.com / Test123! (role: user) - Playwright Worker 0
aws-e2e-test2@test.com / Test123! (role: user) - Playwright Worker 1
aws-e2e-test3@test.com / Test123! (role: user) - Playwright Worker 2
aws-e2e-test4@test.com / Test123! (role: user) - Playwright Worker 3
```

### 綁定功能測試帳號（1 個）
```
binding@test.com / Test123! (role: user)
```
用途：測試 Telegram-Web 身份綁定流程

### 管理員測試帳號（1 個）
```
admin@test.com / Admin123! (role: admin)
```
用途：測試管理員權限功能

## 🧪 測試腳本

**創建測試帳號**: `web-adapter/scripts/create_test_users.py`
**測試綁定 API**: `web-adapter/scripts/test_web_binding.sh`
