# 記憶功能實作筆記

**時間**: 2026-01-07 03:05 UTC

---

## ✅ Memory 資源創建

### Memory 資訊
- **Memory ID**: `TelegramBotMemory-6UH9fyDyIf`
- **Name**: TelegramBotMemory
- **Region**: us-west-2
- **Status**: CREATING → 等待 ACTIVE

### Memory Strategies 配置
1. **UserPreferenceStrategy** (`userPreferences`)
   - Namespace: `/actors/{actorId}/preferences`
   - 用途：自動提取用戶偏好

2. **SemanticStrategy** (`userFacts`)
   - Namespace: `/actors/{actorId}/facts`
   - 用途：自動提取事實資訊

3. **SummaryStrategy** (`sessionSummaries`)
   - Namespace: `/actors/{actorId}/sessions/{sessionId}`
   - 用途：自動生成對話摘要

---

## ✅ /new 命令實作

### 已完成
- ✅ 創建 `new_handler.py`
- ✅ 註冊到 `handler.py` 的命令路由器
- ✅ 生成 session ID 邏輯
- ✅ 用戶友好的回應訊息

### 功能
- 生成格式：`session-YYYYMMDDHHmmss-random8`
- 回應訊息包含：
  - Session ID 預覽
  - 長期記憶保留說明
  - 短期記憶清空說明
  - 使用提示

---

## 📋 待完成步驟

### 1. 等待 Memory ACTIVE（進行中）
預計還需要 1-2 分鐘

### 2. 更新 processor Lambda 環境變數
```bash
aws lambda update-function-configuration \
  --region us-west-2 \
  --function-name telegram-unified-bot-processor \
  --environment "Variables={
    BEDROCK_AGENTCORE_MEMORY_ID=TelegramBotMemory-6UH9fyDyIf,
    EVENT_BUS_NAME=telegram-lambda-receiver-events,
    BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0,
    BROWSER_ENABLED=true,
    LOG_LEVEL=INFO
  }"
```

### 3. 部署接收器 Lambda（包含 /new 命令）
```bash
cd telegram-lambda
sam build
sam deploy --stack-name telegram-lambda-receiver \
  --resolve-s3 --capabilities CAPABILITY_IAM \
  --region us-west-2 --no-confirm-changeset
```

### 4. 測試
- 測試長期記憶（跨 session）
- 測試 /new 命令
- 測試短期記憶清空

---

## 📝 技術要點

### Session ID 生成
- 格式：`session-{timestamp}-{random}`
- 例子：`session-20260107030500-a1b2c3d4`
- 確保唯一性和可讀性

### Memory 架構
```
用戶 316743844
├─ Long-term Memory（永久）
│  ├─ /actors/316743844/preferences
│  ├─ /actors/316743844/facts
│  └─ /actors/316743844/sessions
│
└─ Short-term Sessions
   ├─ session-1（當前）
   ├─ session-2（/new 後）
   └─ session-3（下一個）
```

### /new 命令流程
1. 用戶發送 `/new`
2. 接收器直接處理並回應
3. 生成新的 session ID
4. 下次對話使用新 session
5. 長期記憶自動保留

---

## 🎯 預期效果

### 長期記憶測試
```
對話 1: "我叫 Steven，30歲"
→ 提取到長期記憶

對話 2（使用 /new 後）: "你記得我的名字嗎？"
→ Bot: "是的，你叫 Steven，30歲"
→ 即使在新 session，仍然記得
```

### 短期記憶測試
```
Session 1:
User: "今天天氣如何？"
Bot: "今天天氣晴朗"
User: "明天呢？"
Bot: "明天天氣..." (記得指的是天氣)

[使用 /new]

Session 2:
User: "明天呢？"
Bot: "你是指什麼的明天？" (不記得之前談的是天氣)
```

---

**當前狀態**: Memory 創建中，/new 命令已準備好
