# 端到端部署問題修復總結

**時間**: 2026-01-06 12:08 - 12:31 UTC  
**區域**: us-west-2  
**狀態**: ✅ 三個主要問題已修復，正在最終部署

## 架構概覽

```
Telegram Bot
    ↓ (webhook)
API Gateway (vnqlzx6b9f)
    ↓
Receiver Lambda (telegram-lambda-receiver)
    ↓ (發送事件)
EventBridge (telegram-lambda-events)
    ↓ (message.received)
Processor Lambda (telegram-agentcore-bot-processor)
    ↓ (呼叫 Bedrock AI)
Bedrock Claude 3.5 Sonnet
    ↓ (message.completed)
EventBridge
    ↓
Router Lambda (telegram-lambda-response-router)
    ↓ (發送回應)
Telegram Bot
```

## 問題修復歷程

### 🔍 問題 1：Invalid Secret Token

**症狀**:
- 用戶發送測試訊息無回應
- CloudWatch 日誌顯示：`"Invalid secret token"`
- 所有請求返回 403 Forbidden

**根本原因**:
- Telegram webhook 配置時沒有包含 `secret_token` 參數
- Lambda 驗證失敗因為請求中沒有 `X-Telegram-Bot-Api-Secret-Token` header

**修復步驟**:
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://vnqlzx6b9f.execute-api.us-west-2.amazonaws.com/Prod/webhook",
    "allowed_updates": ["message"],
    "secret_token": "M4fAAfPI7fD2ZIbrbszyyzsKrWi1EQZmAEL8OESK1DwYImtVIhifTc2gMccHlVPU"
  }'
```

**結果**: ✅ Receiver Lambda 開始接受請求

---

### 🔍 問題 2：ConversationAgent 初始化失敗

**症狀**:
```python
TypeError: ConversationAgent.__init__() missing 1 required positional argument: 'tools'
```

**根本原因**:
- `processor_entry.py` 第 16 行：`conversation_agent = ConversationAgent()`
- 沒有提供必需的 `tools` 參數

**修復**:
```python
# Before:
conversation_agent = ConversationAgent()

# After:
from tools import AVAILABLE_TOOLS
conversation_agent = ConversationAgent(tools=AVAILABLE_TOOLS)
```

**結果**: ✅ Processor Lambda 成功初始化

---

### 🔍 問題 3：Channel 檢測錯誤

**症狀**:
```
Processing message from web
Processing text message from Unknown
WARNING: Unsupported message type: text
```

**根本原因**:
- `detect_channel()` 函數只檢查 URL path 中是否包含 'telegram'
- 我們的 endpoint 是 `/webhook`，被錯誤識別為 'web'
- 當 channel='web' 時，`normalize_message()` 返回空文本
- Processor 收到 `text: ""` 無法處理

**修復**:
增強 `detect_channel()` 函數邏輯：
```python
def detect_channel(event: Dict[str, Any]) -> str:
    # 1. 檢查 path
    path = (event.get('path') or "").lower()
    if 'telegram' in path:
        return 'telegram'
    
    # 2. 檢查 Telegram 特定標識（update_id）
    try:
        body = json.loads(event.get('body', '{}'))
        if 'update_id' in body:
            return 'telegram'
    except:
        pass
    
    # 3. 檢查 Telegram secret token header
    headers = event.get('headers', {})
    if ('X-Telegram-Bot-Api-Secret-Token' in headers or 
        'x-telegram-bot-api-secret-token' in headers):
        return 'telegram'
    
    return 'web'
```

**結果**: ✅ Telegram 訊息正確識別，文本成功提取

---

### 🔍 問題 4：Bedrock 權限不足

**症狀**:
```
AccessDeniedException: User is not authorized to perform: 
bedrock:InvokeModelWithResponseStream on resource: 
arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0
```

**根本原因**:
- Lambda IAM 角色只有 `bedrock:InvokeModel` 權限
- 缺少 `bedrock:InvokeModelWithResponseStream` 權限
- Strands Agent 使用流式 API

**修復**:
在 `telegram-agentcore-bot/template.yaml` 添加權限：
```yaml
Policies:
  - Statement:
      - Effect: Allow
        Action:
          - bedrock:InvokeModel
          - bedrock:InvokeModelWithResponseStream  # 新增
          - bedrock:InvokeAgent
          - bedrock:Retrieve
        Resource: '*'
```

**結果**: ⏳ 正在部署中...

---

## 測試驗證

### 模擬 Telegram Webhook 請求

```bash
curl -X POST "https://vnqlzx6b9f.execute-api.us-west-2.amazonaws.com/Prod/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: M4fAAfPI7fD2ZIbrbszyyzsKrWi1EQZmAEL8OESK1DwYImtVIhifTc2gMccHlVPU" \
  -d '{
    "update_id": 999999998,
    "message": {
      "message_id": 9998,
      "from": {
        "id": 316743844,
        "is_bot": false,
        "first_name": "Test",
        "username": "qwer2003tw"
      },
      "chat": {"id": 316743844, "type": "private"},
      "text": "請告訴我今天的天氣如何？"
    }
  }'
```

### 日誌驗證

**Receiver Lambda** ✅:
```json
{
  "event_type": "webhook_received",
  "message_id": "02983fef-e355-4277-b5e9-fbccb3670b38",
  "channel": "telegram"
}
```

**Processor Lambda** ✅ (修復前):
```
Processing message from telegram
Processing text message from Test
📥 處理訊息: 請告訴我今天的天氣如何？...
```

**Bedrock 呼叫** ❌ → ⏳:
```
❌ 訊息處理錯誤: AccessDeniedException
⏳ 正在添加 InvokeModelWithResponseStream 權限...
```

---

## 已部署的修復

1. ✅ **Webhook Secret Token**: 重新配置 Telegram webhook
2. ✅ **ConversationAgent Tools**: 更新 processor_entry.py 
3. ✅ **Channel Detection**: 增強 detect_channel() 函數
4. ⏳ **Bedrock Permissions**: 正在部署更新的 IAM 權限

---

## 下一步測試計畫

1. **等待 Processor 部署完成**（約 2-3 分鐘）
2. **發送測試訊息**
3. **驗證完整流程**:
   - ✅ Receiver 接收並發送到 EventBridge
   - ✅ Processor 接收並識別為 telegram
   - ⏳ Bedrock 處理並生成回應
   - ⏳ Router 發送回應到 Telegram
   - ⏳ 用戶收到 AI 回覆

---

## 關鍵學習

1. **Webhook 配置必須完整**：secret_token 不是可選的，它是安全驗證的核心
2. **Channel 檢測需要多重驗證**：不能只依賴 URL path，要檢查多個標識符
3. **IAM 權限要精確**：InvokeModel 和 InvokeModelWithResponseStream 是不同的權限
4. **工具參數必須提供**：Python 類型檢查在開發時就應該捕獲這類錯誤

---

## 文件參考

- **Webhook 修復**: `WEBHOOK_SECRET_TOKEN_FIX.md`
- **部署報告**: `US_WEST_2_DEPLOYMENT_SUCCESS.md`

---

**更新時間**: 2026-01-06 12:31 UTC  
**狀態**: 等待最終部署完成並測試
