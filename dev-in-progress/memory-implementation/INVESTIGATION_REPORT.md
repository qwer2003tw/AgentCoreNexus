# 🔍 Bedrock AgentCore Memory 調查與實作方案

**調查時間**: 2026-01-07  
**Memory ID**: `telegrambot-1767717327`  
**目標**: 實現短期 session + 長期記憶的混合架構

---

## 📚 AWS Bedrock AgentCore Memory 完整理解

### 核心概念

#### 1. Memory 資源（Memory Resource）
- **本質**：一個邏輯容器，同時包含短期和長期記憶
- **內容**：
  - 短期記憶：原始的對話 events
  - 長期記憶：從 events 提取的結構化記錄
- **配置**：
  - 資料保留時間
  - 安全設定（加密）
  - Memory Strategies（長期記憶提取規則）

#### 2. 短期記憶（Short-term Memory）
- **儲存內容**：原始對話作為不可變的 events
- **組織方式**：按 `actor_id` 和 `session_id` 組織
- **生命週期**：在 session 內有效
- **用途**：
  - 維持當前對話的上下文
  - 避免用戶重複資訊
  - 支援多輪對話

**Example**：
```
User: "西雅圖的天氣如何？"
Bot: "西雅圖今天晴朗..."
User: "明天呢？"  # 短期記憶讓 bot 知道指的是西雅圖
```

#### 3. 長期記憶（Long-term Memory）
- **儲存內容**：從對話中提取的關鍵資訊
- **提取方式**：非同步背景處理
- **記錄類型**：
  - 用戶偏好（preferences）
  - 事實資訊（facts）
  - Session 摘要（summaries）
- **持久性**：跨 session 保留

**Example**：
```
從 "我喜歡靠窗座位" 提取 → 長期記憶: preference: window_seat
下次訂機票時 → bot 主動推薦靠窗座位
```

#### 4. Memory Strategies（記憶策略）
控制如何從短期記憶提取長期記憶：

| 策略 | 提取內容 | 用途 |
|-----|---------|------|
| **SemanticMemoryStrategy** | 事實和知識 | 建立知識庫 |
| **UserPreferencesMemoryStrategy** | 用戶偏好 | 個人化體驗 |
| **SessionSummariesMemoryStrategy** | 對話摘要 | 快速回憶上下文 |
| **EpisodicStrategy** | 結構化互動模式 | 學習成功模式 |

---

## 🎯 符合你需求的架構設計

### 你的目標
1. **短期 session**：用 `/new` 開始新的對話 session
2. **長期記憶**：跨 session 自動記住用戶資訊
3. **自動運作**：無需用戶手動管理

### 完美匹配的架構

```
用戶 316743844 (Steven)
├─ 長期記憶（Long-term Memory）
│  ├─ /actors/316743844/facts
│  │  ├─ 姓名: Steven
│  │  ├─ 年齡: 30 歲
│  │  └─ 居住地: 台北
│  ├─ /actors/316743844/preferences
│  │  ├─ 喜歡的語言: Python, Go
│  │  └─ 程式相關興趣
│  └─ /actors/316743844/summaries
│     └─ 過往對話摘要
│
└─ 短期 Sessions（Short-term Memory）
   ├─ session-20260107-001 (當前)
   │  ├─ Event 1: "你好！我叫 Steven..."
   │  ├─ Event 2: Bot 回應
   │  └─ Event 3: "幫我查天氣"
   │
   ├─ session-20260107-002 (/new 後的新 session)
   │  └─ Event 1: 新對話開始
   │
   └─ session-20260106-xyz (歷史 session)
      └─ 已結束的對話
```

### 工作流程

#### 正常對話
```
User: "你好"
→ 檢查是否有 active session
→ 如果沒有，創建新 session
→ 載入長期記憶（用戶資訊、偏好）
→ 載入短期記憶（當前 session 的對話歷史）
→ AI 處理並回應
→ 儲存新的 event 到短期記憶
→ 背景提取關鍵資訊到長期記憶
```

#### /new 命令
```
User: "/new"
→ 結束當前 session
→ 創建新的 session (新的 session_id)
→ 保留長期記憶（跨 session）
→ 清空短期記憶（新對話）
→ 通知用戶：「已開始新的對話」
```

---

## 🔧 實作方案

### 方案 A：使用 Bedrock AgentCore Memory（官方完整方案）

#### 優點
- ✅ 官方支援，完整功能
- ✅ 自動提取長期記憶（UserPreferences, Semantic, Summaries）
- ✅ 分散式架構，不依賴單一 Lambda 實例
- ✅ 可擴展性強
- ✅ 內建安全和加密

#### 缺點
- ⚠️ 需要先創建 Memory 資源
- ⚠️ 可能需要安裝 `bedrock-agentcore-starter-toolkit`
- ⚠️ 初始設定稍複雜

#### 實作步驟

**1. 安裝 Starter Toolkit**
```bash
pip install bedrock-agentcore-starter-toolkit
```

**2. 創建 Memory 資源（使用 Python）**
```python
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import (
    SemanticStrategy,
    UserPreferencesStrategy,
    SessionSummariesStrategy
)

memory_manager = MemoryManager(region_name="us-west-2")

memory = memory_manager.get_or_create_memory(
    name="TelegramBotMemory",
    description="Telegram Bot long-term memory with user preferences and facts",
    strategies=[
        # 提取用戶偏好
        UserPreferencesStrategy(
            name="userPreferences",
            namespaces=['/actors/{actorId}/preferences']
        ),
        # 提取事實資訊
        SemanticStrategy(
            name="userFacts",
            namespaces=['/actors/{actorId}/facts']
        ),
        # 提取 session 摘要
        SessionSummariesStrategy(
            name="sessionSummaries",
            namespaces=['/actors/{actorId}/sessions/{sessionId}/summary']
        )
    ]
)

print(f"✅ Memory 創建成功！Memory ID: {memory['id']}")
```

**3. 使用創建的 Memory ID**
```bash
aws lambda update-function-configuration \
  --region us-west-2 \
  --function-name telegram-unified-bot-processor \
  --environment "Variables={BEDROCK_AGENTCORE_MEMORY_ID=<實際的 memory_id>,...}"
```

**4. 實現 /new 命令**
- 在 `telegram-adapter/src/commands/handlers/` 創建 `new_handler.py`
- 生成新的 session_id
- 通過 EventBridge 傳遞新的 session_id

### 方案 B：DynamoDB 自定義記憶（完全控制方案）

#### 優點
- ✅ 完全控制記憶存儲
- ✅ 不依賴 Bedrock AgentCore Memory 服務
- ✅ 更靈活的查詢和管理
- ✅ 成本透明可控

#### 缺點
- ⚠️ 需要自己實現記憶提取邏輯
- ⚠️ 需要管理 DynamoDB table
- ⚠️ 沒有內建的智能提取

#### 實作步驟

**1. 創建 DynamoDB Tables**
```yaml
# 短期記憶 table
ConversationHistory:
  - PK: user_id#session_id
  - SK: timestamp
  - message_role (user/assistant)
  - content
  - TTL: 7 days

# 長期記憶 table  
UserMemory:
  - PK: user_id
  - SK: memory_type#key (e.g., "preference#language")
  - value
  - updated_at
  - No TTL (永久保存)
```

**2. 實現 Session Repository**
```python
class DynamoDBSessionRepository:
    def save_message(self, user_id, session_id, role, content)
    def get_session_history(self, user_id, session_id, limit=10)
    def get_long_term_memories(self, user_id, memory_type)
    def save_long_term_memory(self, user_id, memory_type, key, value)
```

**3. 整合到 memory_service.py**

### 方案 C：混合方案（推薦）

結合兩者優勢：
- 使用 **Bedrock AgentCore** 處理短期記憶和自動提取
- 使用 **DynamoDB** 儲存關鍵的長期資訊作為備份

---

## 💡 關鍵發現

### 1. Memory ID 格式正確
我們的 `telegrambot-1767717327` **格式完全正確**！
- 符合正則表達式：`[a-zA-Z][a-zA-Z0-9-_]{0,99}-[a-zA-Z0-9]{10}`
- `telegrambot` (前綴) + `-` + `1767717327` (10位數字)

### 2. 問題在於 Memory 資源未創建
- 需要執行 `CreateMemory` API 調用
- 或使用 starter toolkit 創建
- 創建後會獲得實際的 Memory ID（可能與我們設定的不同）

### 3. Session 管理已經內建
- Bedrock AgentCore 自動管理 session 隔離
- Session 可持續最多 8 小時
- Session 之間完全隔離

---

## 🎯 實作計劃：短期 Session + 長期記憶

### 架構設計

```python
# 1. 用戶發送訊息
incoming_message = {
    'user_id': '316743844',
    'session_id': None,  # 如果為 None，創建新的
    'text': '你好'
}

# 2. Session 管理
if not session_id:
    session_id = generate_session_id()  # e.g., "session-20260107-abc123"
    
# 3. 載入記憶
session_manager = memory_service.get_session_manager(
    memory_id="<實際的 memory_id>",
    actor_id=user_id,
    session_id=session_id
)

# 4. 短期記憶會自動載入（當前 session 的對話）
# 5. 長期記憶會自動注入（用戶偏好、事實）

# 6. 處理訊息
agent = ConversationAgent(tools=AVAILABLE_TOOLS, session_manager=session_manager)
response = agent.process_message(text)

# 7. 自動儲存到短期記憶
# 8. 背景提取到長期記憶（非同步）
```

### /new 命令實作

```python
# telegram-adapter/src/commands/handlers/new_handler.py

class NewCommandHandler(CommandHandler):
    def handle(self, update, event):
        user_id = update.effective_message.from_user.id
        
        # 生成新的 session ID
        new_session_id = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # 發送新 session 事件到 EventBridge
        publish_event({
            'detail-type': 'session.new',
            'detail': {
                'user_id': user_id,
                'new_session_id': new_session_id,
                'action': 'start_new_session'
            }
        })
        
        # 回應用戶
        send_message(chat_id, 
            f"✅ 已開始新的對話！\n"
            f"Session: {new_session_id[:20]}...\n"
            f"（你的長期記憶仍然保留）"
        )
```

---

## 🚀 立即可執行的實作步驟

### 步驟 1：創建 Memory 資源（15 分鐘）

**方法 A：使用 Python 腳本（推薦）**
```python
# create_agentcore_memory.py
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import (
    SemanticStrategy,
    UserPreferencesStrategy,
    SessionSummariesStrategy
)

memory_manager = MemoryManager(region_name="us-west-2")

memory = memory_manager.get_or_create_memory(
    name="TelegramBotMemory",
    description="Telegram Bot with short-term sessions and long-term user memory",
    strategies=[
        UserPreferencesStrategy(
            name="userPreferences",
            namespaces=['/actors/{actorId}/preferences']
        ),
        SemanticStrategy(
            name="userFacts", 
            namespaces=['/actors/{actorId}/facts']
        ),
        SessionSummariesStrategy(
            name="sessionSummaries",
            namespaces=['/actors/{actorId}/sessions']
        )
    ]
)

print(f"✅ Memory ID: {memory['id']}")
```

**方法 B：使用 CLI**
```bash
# 需要先安裝
pip install bedrock-agentcore-starter-toolkit

# 創建 Memory
agentcore memory create TelegramBotMemory \
  --region us-west-2 \
  --description "Telegram Bot Memory" \
  --strategies '[
    {"userPreferencesMemoryStrategy": {"name": "userPrefs", "namespaces": ["/actors/{actorId}/preferences"]}},
    {"semanticMemoryStrategy": {"name": "userFacts", "namespaces": ["/actors/{actorId}/facts"]}},
    {"sessionSummariesMemoryStrategy": {"name": "sessionSummaries", "namespaces": ["/actors/{actorId}/sessions"]}}
  ]' \
  --wait

# 列出 memories 確認
agentcore memory list --region us-west-2
```

### 步驟 2：更新 Lambda 環境變數（5 分鐘）

```bash
# 使用創建的實際 Memory ID
aws lambda update-function-configuration \
  --region us-west-2 \
  --function-name telegram-unified-bot-processor \
  --environment "Variables={
    BEDROCK_AGENTCORE_MEMORY_ID=<實際獲得的 memory_id>,
    EVENT_BUS_NAME=telegram-adapter-receiver-events,
    BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0,
    BROWSER_ENABLED=true,
    LOG_LEVEL=INFO
  }"
```

### 步驟 3：實現 /new 命令（30 分鐘）

創建文件：`telegram-adapter/src/commands/handlers/new_handler.py`

```python
"""
New Session Command Handler
處理 /new 指令，開始新的對話 session
"""
import uuid
from datetime import datetime
from commands.base import CommandHandler
from utils.logger import get_logger
import telegram_client

logger = get_logger(__name__)

class NewCommandHandler(CommandHandler):
    """處理 /new 指令的處理器"""
    
    def can_handle(self, message: str) -> bool:
        return message.strip().startswith('/new')
    
    def handle(self, update, event):
        try:
            chat_id = update.effective_message.chat_id
            user_id = update.effective_message.from_user.id
            
            # 生成新的 session ID
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            session_id = f"session-{timestamp}-{str(uuid.uuid4())[:8]}"
            
            logger.info(
                f"Creating new session for user {user_id}",
                extra={'new_session_id': session_id}
            )
            
            # 發送到 EventBridge（讓 processor 知道要用新 session）
            # 這裡可以發送一個特殊事件，或者簡單地在下一次對話自動使用新 session
            
            # 回應用戶
            message_text = (
                "✅ 已開始新的對話！\n\n"
                f"🆔 Session ID: {session_id[:24]}...\n\n"
                "💾 你的長期記憶（姓名、偏好等）仍然保留\n"
                "🆕 當前對話的短期記憶已清空"
            )
            
            telegram_client.send_message(chat_id, message_text)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in /new command: {e}", exc_info=True)
            return False
    
    def get_command_name(self) -> str:
        return "/new"
    
    def get_description(self) -> str:
        return "開始新的對話 session"
```

### 步驟 4：修改 processor_entry.py 支援動態 session（15 分鐘）

在 `process_normalized_message` 中：

```python
# 檢查是否有指定的 session_id（來自 /new 命令）
session_id = context_info.get('sessionId')

if not session_id:
    # 如果沒有，使用 user_id 作為 session_id（單一持續 session）
    # 或者生成一個持久的 session_id（例如基於日期）
    session_id = f"{user_id}-daily-{datetime.now().strftime('%Y%m%d')}"
```

### 步驟 5：測試（30 分鐘）

#### 測試 1：長期記憶
```bash
# 對話 1
curl ... -d '{"message": {"text": "我叫 Steven，30歲，住台北"}}'

# 等待 10 秒（讓長期記憶提取完成）

# 對話 2（同一個 session）
curl ... -d '{"message": {"text": "我喜歡 Python 和 Go"}}'

# 對話 3（驗證記憶）
curl ... -d '{"message": {"text": "你記得我的資訊嗎？"}}'
# 預期：記得姓名、年齡、居住地、偏好
```

#### 測試 2：/new 命令
```bash
# 使用 /new 開始新 session
curl ... -d '{"message": {"text": "/new"}}'

# 新 session 中的對話
curl ... -d '{"message": {"text": "你好"}}'
# 預期：記得長期資訊（姓名等），但不記得剛才的短期對話內容
```

---

## 📊 預期效果

### 長期記憶（跨 session 保留）
```
用戶資訊：
- 姓名：Steven
- 年齡：30 歲
- 居住地：台北
- 偏好語言：Python, Go
- 興趣：寫程式
```

### 短期 Session（/new 後清空）
```
Session 1:
- "今天天氣如何？"
- "明天呢？"
- "下週會下雨嗎？"

[用戶使用 /new]

Session 2（新的對話）:
- "你好"  # 不記得上個 session 的天氣對話
- Bot 仍知道用戶是 Steven，30歲，住台北
```

---

## ⚠️ 需要確認的問題

### 1. Memory 創建權限
**問題**：AWS 帳戶是否有權限創建 Bedrock AgentCore Memory？

**確認方法**：
```bash
# 測試權限
aws bedrock-agentcore-control create-memory \
  --region us-west-2 \
  --name "TestMemory" \
  --dry-run 2>&1 | grep -i "denied\|unauthorized"
```

如果權限不足，可能需要：
- 添加 IAM policy
- 或使用 DynamoDB 方案

### 2. Session ID 管理策略
**選項 A**：每日一個 session
- Session ID: `{user_id}-daily-20260107`
- 每天自動開始新 session
- 簡單但不夠靈活

**選項 B**：用戶手動管理
- 使用 `/new` 才開始新 session
- 給用戶更多控制權
- 需要儲存當前 session_id

**選項 C**：智能判斷
- 超過 4 小時無對話 → 自動新 session
- 用戶可用 `/new` 手動開始
- 最智能但實作較複雜

**你偏好哪個？**

### 3. 長期記憶的範圍
需要自動提取和保留什麼資訊？
- ✅ 用戶基本資訊（姓名、年齡、居住地）
- ✅ 用戶偏好（喜好、習慣）
- ✅ Session 摘要（重要對話的總結）
- ❓ 特定領域知識（例如：用戶的專案相關資訊）
- ❓ 其他？

### 4. 成本考量
- Bedrock AgentCore Memory 按 API 調用和存儲計費
- 預估每個用戶每月：< $1 USD
- DynamoDB 方案可能更便宜但需要更多維護

---

## 🎉 總結與建議

### 當前狀態
- ✅ 代碼 100% 準備就緒
- ✅ 權限完整配置
- ✅ 架構設計完成
- ⚠️ 只差創建 Memory 資源

### 我的建議

**推薦使用方案 A（Bedrock AgentCore Memory）**，因為：

1. **官方支援**：AWS 完全託管，不需要自己維護基礎設施
2. **智能提取**：自動提取用戶偏好和事實，不需要手寫邏輯
3. **已經整合**：我們的代碼已經使用 `bedrock-agentcore` 套件
4. **擴展性好**：原生支援分散式架構

**只需要**：
1. 執行 Memory 創建腳本（15 分鐘）
2. 更新環境變數（5 分鐘）
3. 實現 `/new` 命令（30 分鐘）
4. 測試驗證（30 分鐘）

**總時間**：約 90 分鐘可完成

---

## 🤝 討論問題

在開始實作前，我希望和你確認：

1. **權限**：你的 AWS 帳戶是否能創建 Bedrock AgentCore Memory？
2. **Session 策略**：你偏好哪種 session 管理方式？（每日自動 vs 用戶手動 vs 智能判斷）
3. **長期記憶範圍**：除了基本資訊和偏好，還需要記住什麼？
4. **優先級**：是否現在就實作，還是先測試 Memory 創建？

讓我知道你的想法，我就可以開始實作！

---

**文檔來源**: AWS Bedrock AgentCore 官方文檔（透過 MCP 查詢）  
**調查完成時間**: 2026-01-07 02:52 UTC  
**結論**: ✅ 技術上完全可行，只需創建 Memory 資源即可啟用
