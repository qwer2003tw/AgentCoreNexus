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

## 🎯 下一步

1. 創建測試帳號（5 個）
2. 部署前端到 S3
3. 測試 Web 登入
4. 測試身份綁定功能