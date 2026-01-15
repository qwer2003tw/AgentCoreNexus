# Memory 跨通道驗證計劃

**創建時間**: 2026-01-15 14:15 PM UTC  
**目標**: 驗證跨通道 Memory 功能（AgentCore Nexus 核心特色）

---

## 🔍 代碼檢查結果（關鍵發現）

### ❌ 發現嚴重問題：跨通道 Memory 未實現

**檢查項目**：
- [x] processor_entry.py 是否查詢 user_bindings？
- [x] memory_service.py 是否使用 unified_user_id？
- [x] template.yaml 是否有 BINDINGS_TABLE 環境變數？

**檢查結果**：
```bash
# processor_entry.py
grep "user_bindings\|unified_user_id" processor_entry.py
# 結果：無匹配 ❌

# memory_service.py  
grep "unified_user_id" memory_service.py
# 結果：無匹配 ❌

# template.yaml
grep "BINDINGS_TABLE" template.yaml
# 結果：無匹配 ❌
```

**結論**：
- ❌ Processor 沒有查詢 bindings 表
- ❌ Memory Service 不使用 unified_user_id
- ❌ 環境變數未配置 BINDINGS_TABLE
- ❌ **跨通道 Memory 功能尚未實現**

---

## 🚨 當前實現分析

### processor_entry.py 當前邏輯

```python
# 提取用戶 ID（從標準化訊息）
user_id = str(user.get("id", "unknown"))  # 例如："tg:316743844" 或 "web:user@email.com"
session_id = context_info.get("sessionId", user_id)

# 直接使用 user_id 作為 actor_id
secure_user_id = secure_actor_id(user_id)  # hash(user_id)

# 建立 Memory context（沒有查詢 bindings）
memory_context = type("MemoryContext", (), {
    "session_id": session_id,
    "headers": {
        "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id": secure_user_id
    }
})()
```

**問題**：
- Telegram 用戶使用：`hash("tg:316743844")` 作為 actor_id
- Web 用戶使用：`hash("web:user@email.com")` 作為 actor_id
- **即使綁定後，兩個通道仍使用不同的 actor_id**
- **Memory 不會共享**

### memory_service.py 當前邏輯

```python
def _extract_actor_id(self, context: Any) -> str:
    actor_id = "user"  # 預設
    
    if hasattr(context, "headers"):
        actor_id = context.headers.get(
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id", 
            "user"
        )
    
    return actor_id
```

**問題**：
- 直接使用傳入的 actor_id
- 沒有查詢 unified_user_id
- 沒有處理跨通道場景

---

## 🎯 需要實現的功能

### 1. Bindings 表查詢邏輯

**新增函數**（processor_entry.py）：
```python
import boto3

dynamodb = boto3.resource('dynamodb')
BINDINGS_TABLE = os.environ.get('BINDINGS_TABLE', '')

def get_unified_user_id(user_info: dict) -> str:
    """
    查詢 unified_user_id，如果未綁定則返回通道特定 ID
    
    Args:
        user_info: 標準化訊息的 user 物件
        
    Returns:
        unified_user_id 或 fallback ID
    """
    if not BINDINGS_TABLE:
        # 如果沒有配置 bindings 表，使用通道特定 ID
        return user_info.get("id", "unknown")
    
    user_id = user_info.get("id", "")
    
    # 根據 ID 格式判斷通道
    if user_id.startswith("tg:"):
        # Telegram: 查詢 telegram_chat_id
        chat_id = user_id.split(":")[1]
        return query_binding_by_telegram(chat_id)
        
    elif user_id.startswith("web:") or "@" in user_id:
        # Web: 查詢 web_email
        email = user_id.replace("web:", "")
        return query_binding_by_email(email)
    
    # 未知格式，返回原 ID
    return user_id

def query_binding_by_telegram(chat_id: str) -> str:
    """通過 telegram_chat_id 查詢 binding"""
    table = dynamodb.Table(BINDINGS_TABLE)
    
    try:
        response = table.query(
            IndexName='telegram_chat_id-index',
            KeyConditionExpression='telegram_chat_id = :chat_id',
            ExpressionAttributeValues={':chat_id': int(chat_id)}
        )
        
        items = response.get('Items', [])
        if items and items[0].get('binding_status') == 'complete':
            return items[0]['unified_user_id']
    except:
        pass
    
    # 未綁定，返回 Telegram 特定 ID
    return f"tg:{chat_id}"

def query_binding_by_email(email: str) -> str:
    """通過 web_email 查詢 binding"""
    table = dynamodb.Table(BINDINGS_TABLE)
    
    try:
        response = table.query(
            IndexName='web_email-index',
            KeyConditionExpression='web_email = :email',
            ExpressionAttributeValues={':email': email}
        )
        
        items = response.get('Items', [])
        if items and items[0].get('binding_status') == 'complete':
            return items[0]['unified_user_id']
    except:
        pass
    
    # 未綁定，返回 Web 特定 ID
    return f"web:{email}"
```

### 2. Processor Entry 整合

**修改 process_normalized_message**：
```python
# 提取用戶資訊
user = normalized.get("user", {})
user_id_original = str(user.get("id", "unknown"))

# 🆕 查詢 unified_user_id（如果已綁定）
unified_user_id = get_unified_user_id(user)

logger.info(
    f"User ID mapping: {user_id_original} → {unified_user_id}",
    extra={
        "original_id": user_id_original,
        "unified_id": unified_user_id,
        "is_bound": unified_user_id != user_id_original
    }
)

# 使用 unified_user_id 作為 actor_id
secure_user_id = secure_actor_id(unified_user_id)
```

### 3. 環境變數配置

**template.yaml 修改**：
```yaml
Environment:
  Variables:
    EVENT_BUS_NAME: !Ref EventBusName
    BEDROCK_MODEL_ID: !Ref BedrockModelId
    BEDROCK_AGENTCORE_MEMORY_ID: !Ref BedrockAgentCoreMemoryId
    BINDINGS_TABLE: agentcore-web-adapter-user-bindings  # 🆕 新增
    BROWSER_ENABLED: 'true'
    FILE_ENABLED: 'true'

Policies:
  - Statement:
      # 🆕 新增 Bindings 表讀取權限
      - Effect: Allow
        Action:
          - dynamodb:Query
          - dynamodb:GetItem
        Resource:
          - 'arn:aws:dynamodb:*:*:table/agentcore-web-adapter-user-bindings'
          - 'arn:aws:dynamodb:*:*:table/agentcore-web-adapter-user-bindings/index/*'
```

---

## 📋 實施計劃

### Task 1: 實現跨通道 Memory（2-3h）

#### 1.1 添加 bindings 查詢函數
- [ ] 在 processor_entry.py 添加 `get_unified_user_id()`
- [ ] 添加 `query_binding_by_telegram()`
- [ ] 添加 `query_binding_by_email()`
- [ ] 添加錯誤處理和日誌

#### 1.2 修改消息處理邏輯
- [ ] 在 `process_normalized_message` 中調用 `get_unified_user_id()`
- [ ] 使用 unified_user_id 建立 Memory context
- [ ] 添加綁定狀態日誌

#### 1.3 更新配置
- [ ] template.yaml 添加 BINDINGS_TABLE 環境變數
- [ ] template.yaml 添加 DynamoDB 讀取權限
- [ ] 重新部署 Processor

---

### Task 2: 測試驗證（1-2h）

#### 2.1 綁定流程測試
```bash
# Step 1: Web 生成綁定碼
- 登入 Web
- 生成綁定碼
- 記錄碼和 unified_user_id

# Step 2: Telegram 綁定
- 發送 /bind 123456
- 驗證成功訊息

# Step 3: 資料庫驗證
aws dynamodb get-item \
  --table-name agentcore-web-adapter-user-bindings \
  --key '{"unified_user_id":{"S":"[ID]"}}'
```

#### 2.2 Memory 共享測試
```bash
# Telegram → Web
Telegram: "我叫 Test User，我正在測試 Memory"
Web: "我叫什麼名字？"
預期: "Test User"

# Web → Telegram  
Web: "我今天完成了跨通道 Memory 實現"
Telegram: "我今天做了什麼？"
預期: 提到"Memory 實現"
```

#### 2.3 日誌驗證
```bash
# 查看 Processor 日誌
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 --since 10m --follow

# 尋找：
# - "User ID mapping: xxx → yyy"
# - "unified_id"
# - "is_bound: true"
# - Memory session created
```

---

## ⚠️ 當前狀況評估

### 跨通道 Memory 狀態：❌ 未實現

**README 宣稱**：
> 🌐 跨通道記憶：在任何平台與 AI 對話，上下文完整保留

**實際狀況**：
- ✅ Telegram 有 Memory（但只在 Telegram 內）
- ✅ Web 有 Memory（但只在 Web 內）
- ❌ **兩者不共享**（未實現 unified_user_id 查詢）

**影響**：
- 核心特色未完全實現
- 綁定功能存在但不完整
- 需要補完實現

---

## 🎯 行動優先級

### 🔴 立即（阻礙 Phase 5 完成）

**Task**: 實現跨通道 Memory 查詢邏輯（2-3h）
- 添加 bindings 表查詢
- 使用 unified_user_id
- 測試驗證

**如果不做**：
- Phase 5 無法說「完成」
- 核心特色不work
- 部署後用戶會失望

---

## 📝 需要你的決定

### 選項 A：立即實現（推薦）⭐

**今天完成**：
- 實現代碼（2-3h）
- 測試驗證（1-2h）
- Phase 5 完成（100%）

**優點**：
- ✅ 核心特色完整
- ✅ 可以自信說「完成」
- ✅ 用戶獲得完整體驗

---

### 選項 B：標記為已知限制

**文檔中說明**：
- 當前版本：Memory 在各通道獨立
- 跨通道共享：規劃中（Phase 6）

**優點**：
- 快速完成 Phase 5
- 透明化當前限制

**缺點**：
- ❌ 核心特色不完整
- ❌ README 需要修改（移除跨通道宣稱）

---

## 💡 我的強烈建議

**選擇選項 A（立即實現）**

**原因**：
1. 這是核心賣點，必須實現
2. 代碼量不大（約 100-150 行）
3. 技術上可行（所有組件都ready）
4. 今天可以完成

**如果你同意**，請告訴我，我將立即開始實現：
1. 添加 bindings 查詢邏輯
2. 修改 Processor 使用 unified_user_id
3. 更新配置和權限
4. 部署並測試
5. 驗證跨通道 Memory 成功

**準備好開始 Phase 5 的最後衝刺了嗎？**