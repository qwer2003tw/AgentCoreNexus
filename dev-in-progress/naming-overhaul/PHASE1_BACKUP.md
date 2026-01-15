# Phase 1: 數據備份

**開始時間**: 2026-01-15 15:17 PM  
**目標**: 完整備份所有數據，確保可恢復

---

## 📋 備份清單

### 1. DynamoDB 表（5個）

#### 1.1 telegram-allowlist
- [ ] 掃描並導出數據
- [ ] 保存到 backup/telegram-allowlist.json
- [ ] 驗證數據完整性

#### 1.2 agentcore-web-channel-web-users
- [ ] 掃描並導出
- [ ] 保存到 backup/web-users.json

#### 1.3 agentcore-web-channel-user-bindings
- [ ] 掃描並導出
- [ ] 保存到 backup/user-bindings.json

#### 1.4 agentcore-web-channel-conversations
- [ ] 掃描並導出
- [ ] 保存到 backup/conversations.json

#### 1.5 agentcore-web-channel-conversation-history
- [ ] 掃描並導出（可能很大）
- [ ] 保存到 backup/conversation-history.json

### 2. Secrets Manager

- [ ] telegram-lambda-receiver-secrets
- [ ] agentcore-web-channel JWT secret

### 3. Stack Outputs

- [ ] telegram-lambda-receiver
- [ ] telegram-unified-bot
- [ ] agentcore-web-channel

### 4. S3 前端

- [ ] sync agentcore-web-channel-frontend-xxx

---

## 執行記錄

（記錄備份過程和結果）

