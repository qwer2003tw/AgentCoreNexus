# CloudFormation Stack 管理指南

AgentCoreNexus 使用多個 CloudFormation Stacks 實現模組化架構。

---

## 🏗️ Stack 架構概覽

```
┌─────────────────────────────────────────────────────────┐
│         telegram-adapter-receiver (接收層)                │
│  - API Gateway (Telegram webhook)                       │
│  - Receiver Lambda                                       │
│  - Response Router Lambda                               │
│  - EventBridge Bus (telegram-adapter-receiver-events)    │
│  - Allowlist DynamoDB Table                             │
│  - Secrets Manager (bot token)                          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ EventBridge Events
                       ↓
┌─────────────────────────────────────────────────────────┐
│         telegram-unified-bot (AI 處理層)                 │
│  - Processor Lambda (AgentCore)                         │
│  - Memory Service                                        │
│  - Browser Service                                       │
│  - Tools (calculator, weather, etc.)                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ EventBridge Events
                       ↓
┌─────────────────────────────────────────────────────────┐
│         agentcore-web-adapter (Web 通道層)               │
│  - WebSocket API Gateway                                │
│  - REST API Gateway                                     │
│  - Web Adapter Lambdas (connect/disconnect/default)    │
│  - Auth/Admin/History/Binding Lambdas                  │
│  - Response Router Lambda                               │
│  - Web Users Table                                      │
│  - User Bindings Table                                  │
│  - Conversation History Table                           │
│  - S3 Bucket (前端)                                     │
│  - CloudFront Distribution (CDN)                        │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Stack 職責劃分

### 1. telegram-adapter-receiver（接收層）
**職責**: Telegram 入口點
- 接收 Telegram webhook
- 驗證 allowlist
- 處理命令（/info, /bind 等）
- 發送 EventBridge events

**主要資源**:
- Lambda: telegram-adapter-receiver
- Lambda: telegram-adapter-response-router
- DynamoDB: telegram-allowlist
- EventBridge Bus: telegram-adapter-receiver-events

**部署**:
```bash
make deploy-telegram
# 或
cd telegram-adapter
sam deploy --stack-name telegram-adapter-receiver ...
```

---

### 2. telegram-unified-bot（處理層）
**職責**: AI 核心處理
- 監聽 EventBridge events
- 處理 AI 對話（Bedrock Claude）
- 管理 Memory（AgentCore）
- 執行工具（Browser, Calculator 等）
- 發送回應 events

**主要資源**:
- Lambda: telegram-unified-bot-processor
- AgentCore Memory
- Bedrock Integration

**部署**:
```bash
make deploy-processor
# 或
cd ai-processor
sam deploy --stack-name telegram-unified-bot ...
```

---

### 3. agentcore-web-adapter（Web 層）
**職責**: Web 入口點 + 前端
- 提供 Web 認證（email + password）
- WebSocket 即時通訊
- REST API（歷史、綁定、管理）
- 對話歷史存儲
- 跨通道用戶綁定
- 前端託管（S3 + CloudFront）

**主要資源**:
- API Gateway: WebSocket + REST
- Lambda: 10 個（ws-*, auth, admin, history, binding, router）
- DynamoDB: 5 個 tables
- S3: Frontend bucket
- CloudFront: CDN distribution
- Secrets Manager: JWT secret

**部署**:
```bash
make deploy-web
# 或
cd dev-in-progress/web-adapter-expansion/infrastructure
sam deploy --stack-name agentcore-web-adapter ...
```

---

## 🔗 Stack 之間的連接

### EventBridge（核心通訊機制）

```
telegram-adapter-receiver
  └─ 發送: message.received (Telegram 消息)
      ↓
telegram-unified-bot-processor  
  └─ 監聽: message.received
  └─ 發送: message.completed (AI 回應)
      ↓
├─ telegram-adapter-response-router (Telegram 回應)
└─ agentcore-web-adapter-response-router (Web 回應)
```

### ImportValue（Stack 輸出共享）

```yaml
# web-adapter-template.yaml
ExistingEventBusName:
  Default: telegram-adapter-receiver-events  # 從 Stack 1 來

# 使用
EVENT_BUS_NAME: !Ref ExistingEventBusName
```

---

## 📦 部署順序

### 首次部署（全新環境）

**必須按順序**：

```bash
# Step 1: Telegram 層（創建 EventBridge）
make deploy-telegram

# Step 2: Processor 層（需要 EventBridge）
make deploy-processor

# Step 3: Web 層（需要 EventBridge）
make deploy-web

# 或一鍵部署
make deploy-all
```

**原因**: Web 和 Processor 都依賴 Telegram 層創建的 EventBridge Bus

---

### 更新部署（已有環境）

**可以獨立更新**：

```bash
# 只更新 Web 層
make deploy-web

# 只更新 Processor
make deploy-processor

# 只更新 Telegram
make deploy-telegram
```

**原因**: 使用 ImportValue 和 EventBridge 鬆耦合，互不影響

---

## 🔄 日常操作

### 查看所有 Stacks 狀態
```bash
make status
```

### 查看詳細資訊
```bash
make info
```

### 查看日誌
```bash
# Telegram 層
make logs STACK=telegram

# Processor 層
make logs STACK=processor

# Web 層
make logs STACK=web
```

### 快速更新前端（開發迭代）
```bash
# 修改前端代碼後
make update-frontend

# 等同於
cd dev-in-progress/web-adapter-expansion
./scripts/deploy-frontend.sh
```

---

## 🧪 測試部署

### 驗證 Telegram 層
```bash
# 在 Telegram 發送
/info

# 應該看到系統資訊（包含所有 3 個 stacks）
```

### 驗證 Processor 層
```bash
# 在 Telegram 發送任意消息
你好

# 應該收到 AI 回應
```

### 驗證 Web 層
```bash
# 1. 獲取前端 URL
make info | grep "前端 URL"

# 2. 打開瀏覽器訪問
# 3. 測試登入、聊天、歷史等功能
```

---

## 🐛 Troubleshooting

### Stack 部署失敗

**檢查**：
```bash
# 查看 stack events
aws cloudformation describe-stack-events \
  --region us-west-2 \
  --stack-name STACK_NAME \
  --max-items 20

# 查看詳細錯誤
sam deploy --debug
```

**常見問題**：
1. **ImportValue 錯誤** - 確認依賴的 stack 已部署
2. **權限錯誤** - 檢查 IAM 權限
3. **資源名稱衝突** - 檢查是否有重複資源

### Lambda 更新不生效

**解決**：
```bash
# 清除緩存
rm -rf .aws-sam

# 強制重新 build
sam build --use-container

# 重新部署
make deploy-STACK
```

### CloudFront 更新慢

**說明**: CloudFront 部署需要 15-20 分鐘

**加速前端更新**：
```bash
# 不重新部署 CloudFront，只更新內容
make update-frontend

# 手動 invalidate（立即生效）
aws cloudfront create-invalidation \
  --distribution-id DISTRIBUTION_ID \
  --paths "/*"
```

---

## 🔐 Stack 依賴關係

### 誰依賴誰？

```
telegram-adapter-receiver (獨立)
  ↓ exports: EventBridge Bus
  
telegram-unified-bot
  ↑ imports: EventBridge Bus
  
agentcore-web-adapter
  ↑ imports: EventBridge Bus
```

### 刪除順序

**必須反向刪除**：
```bash
# 1. 先刪除 Web（依賴 EventBridge）
aws cloudformation delete-stack --stack-name agentcore-web-adapter

# 2. 再刪除 Processor（依賴 EventBridge）
aws cloudformation delete-stack --stack-name telegram-unified-bot

# 3. 最後刪除 Telegram（提供 EventBridge）
aws cloudformation delete-stack --stack-name telegram-adapter-receiver

# 或使用 Makefile（已處理順序）
make clean
```

---

## 📊 成本估算

### 每月預估（小規模 < 1000 用戶）

| Stack | 主要費用 | 月成本 |
|-------|---------|--------|
| telegram-adapter | Lambda + DynamoDB | $5-10 |
| telegram-unified-bot | Lambda + Bedrock | $10-20 |
| agentcore-web-adapter | Lambda + DynamoDB + S3 + CloudFront | $15-30 |
| **總計** | | **$30-60** |

### 主要成本來源
1. **Bedrock API 調用** - 最大成本（依使用量）
2. **CloudFront 流量** - 第二大成本
3. **Lambda 執行時間**
4. **DynamoDB 讀寫**

### 優化建議
- 啟用 CloudFront cache（已設置 1 天）
- Lambda 使用合適的記憶體大小
- DynamoDB 使用 On-Demand（小規模最划算）

---

## 🎯 最佳實踐

### 1. 環境隔離

建議為不同環境使用不同 stack 名稱：
```bash
# 開發環境
make deploy-web STACK_NAME=agentcore-web-adapter-dev

# 生產環境  
make deploy-web STACK_NAME=agentcore-web-adapter-prod
```

### 2. 版本控制

在 Git commit 中標記部署版本：
```bash
git tag -a v1.0.0 -m "Production deployment"
git push --tags
```

### 3. 監控

為每個 stack 設置 CloudWatch Dashboard：
- Lambda 調用次數和錯誤
- API Gateway 請求量
- DynamoDB 讀寫容量
- CloudFront 流量

### 4. 備份

啟用 DynamoDB Point-in-Time Recovery：
- 所有重要 tables 已啟用（在 templates 中）
- 可恢復任意時間點的數據

---

## 📚 相關文檔

- 根目錄 `Makefile` - 統一部署指令
- `telegram-adapter/template.yaml` - Telegram 層 template
- `ai-processor/template.yaml` - Processor 層 template
- `web-adapter/infrastructure/web-adapter-template.yaml` - Web 層 template

---

## 🔄 更新歷史

### 2026-01-08
- 創建 Multi-Stack 管理文檔
- 添加根目錄 Makefile
- 定義 3 個 stacks 的架構和職責

---

**版本**: 1.0  
**最後更新**: 2026-01-08  
**維護者**: AgentCoreNexus Team