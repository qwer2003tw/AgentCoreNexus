# Web Channel Integration Guide

本文檔說明如何將 Web Channel 功能整合到現有的 telegram-adapter 和 ai-processor 專案中。

---

## 🔄 整合概覽

Web Channel 擴展需要對現有系統進行以下整合：

1. **ai-processor（處理器）**
   - 修改 Memory Service 使用 unified_user_id
   - 更新 processor_entry.py 以支援 Web 消息
   
2. **telegram-adapter（接收器）**
   - 添加 /bind 指令
   - 更新環境變數以訪問新的 DynamoDB tables

3. **新增 Web Channel Stack**
   - 獨立部署 WebSocket + REST API
   - 獨立管理 Web 相關資源

---

## 📝 詳細整合步驟

### Step 1: 部署 Web Channel Stack

```bash
# 1. 進入 web-adapter 目錄
cd dev-in-progress/web-adapter-expansion/infrastructure

# 2. 驗證 template
sam validate -t web-adapter-template.yaml

# 3. 部署（首次部署）
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

# 4. 記錄 Outputs
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs'
```

---

### Step 2: 整合 ai-processor（處理器）

#### 2.1 修改 Memory Service

**檔案**: `ai-processor/services/memory_service.py`

**目的**: 使用 unified_user_id 而非 chat_id

**修改內容**:

```python
# 原本的 get_session_manager
def get_session_manager(self, context: Any) -> Any | None:
    session_id = getattr(context, "session_id", settings.DEFAULT_SESSION_ID)
    actor_id = self._extract_actor_id(context)
    # ...

# 修改為
def get_session_manager(self, user_info: dict[str, Any]) -> Any | None:
    """
    取得 Session Manager
    
    Args:
        user_info: 包含 unified_user_id 的用戶資訊
        
    Returns:
        Session Manager 實例或 None
    """
    if not self.enabled:
        return None
    
    try:
        # 使用 unified_user_id 作為 session_id
        session_id = user_info.get('unified_user_id', settings.DEFAULT_SESSION_ID)
        actor_id = user_info.get('identifier', 'user')
        
        memory_config = self._create_memory_config(session_id, actor_id)
        session_manager = self._session_manager_class(memory_config, settings.AWS_REGION)
        
        return session_manager
        
    except Exception as e:
        logger.error(f"❌ Session Manager 建立失敗: {str(e)}", exc_info=True)
        return None
```

#### 2.2 修改 Processor Entry

**檔案**: `ai-processor/processor_entry.py`

**添加**: 查詢 unified_user_id 邏輯

```python
import boto3

# 在檔案頂部添加
BINDINGS_TABLE = os.environ.get('BINDINGS_TABLE', '')
bindings_table = boto3.resource('dynamodb').Table(BINDINGS_TABLE) if BINDINGS_TABLE else None

def get_unified_user_id(message: dict[str, Any]) -> str:
    """
    從消息中提取或查詢 unified_user_id
    
    Args:
        message: 統一消息格式
        
    Returns:
        unified_user_id
    """
    # 如果消息已包含 unified_user_id（來自 Web）
    user_info = message.get('user', {})
    if 'unified_user_id' in user_info:
        return user_info['unified_user_id']
    
    # Telegram 消息：查詢 bindings
    channel = message.get('channel', {})
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
                return items[0]['unified_user_id']
        except Exception as e:
            print(f"Error querying binding: {str(e)}")
    
    # 未綁定：使用臨時 ID
    return f"telegram:{channel.get('channel_id', 'unknown')}"

# 在 process() 函數中使用
def process(normalized):
    # 獲取 unified_user_id
    unified_user_id = get_unified_user_id(normalized)
    
    # 準備 user_info 給 Memory Service
    user_info = {
        'unified_user_id': unified_user_id,
        'identifier': normalized.get('user', {}).get('identifier', 'user')
    }
    
    # 傳入 user_info 而非 context
    session = memory.get_session_manager(user_info)
    
    # ... 其餘處理邏輯
```

#### 2.3 更新環境變數

**檔案**: `ai-processor/template.yaml`

```yaml
Environment:
  Variables:
    # 現有變數
    EVENT_BUS_NAME: !Ref EventBusName
    BEDROCK_MODEL_ID: !Ref BedrockModelId
    # ... 其他
    
    # 新增變數
    BINDINGS_TABLE: !ImportValue agentcore-web-adapter-UserBindingsTable
```

---

### Step 3: 整合 telegram-adapter（接收器）

#### 3.1 添加 /bind 指令處理器

**檔案**: `telegram-adapter/src/commands/handlers/bind_handler.py`

複製 `dev-in-progress/web-adapter-expansion/telegram-integration/bind_handler.py` 到此位置。

#### 3.2 註冊 /bind 指令

**檔案**: `telegram-adapter/src/commands/router.py`

```python
from commands.handlers.bind_handler import handle_bind_command
from auth.permissions import Permission

# 在 COMMANDS dict 中添加
COMMANDS = {
    # ... 現有指令
    
    "bind": {
        "handler": handle_bind_command,
        "permission": Permission.ALLOWLIST,
        "description": "綁定 Telegram 與 Web 帳號",
        "usage": "/bind <6位數綁定碼>"
    }
}
```

#### 3.3 更新環境變數

**檔案**: `telegram-adapter/template.yaml`

```yaml
# 在 TelegramReceiverFunction 中添加
Environment:
  Variables:
    # 現有變數
    TELEGRAM_SECRETS_ARN: !Ref TelegramSecrets
    # ... 其他
    
    # 新增變數（用於 /bind 指令）
    BINDINGS_TABLE: !ImportValue agentcore-web-adapter-UserBindingsTable
    BINDING_CODES_TABLE: !ImportValue agentcore-web-adapter-BindingCodesTable

# 更新 Policies
Policies:
  # 現有策略
  # ...
  
  # 新增：讀取 bindings 和 binding_codes
  - DynamoDBReadPolicy:
      TableName: !ImportValue agentcore-web-adapter-UserBindingsTable
  - DynamoDBCrudPolicy:
      TableName: !ImportValue agentcore-web-adapter-BindingCodesTable
```

---

### Step 4: 修改現有 Response Router

**選項 A（推薦）**: 使用新的 Web Channel Response Router

修改 `web-adapter-template.yaml` 的 ResponseRouterFunction，使其監聽 message.completed 事件並同時：
- 保存歷史記錄（Telegram + Web 都保存）
- 路由 Web 回應到 WebSocket
- 保留 Telegram 回應給現有 telegram-adapter response router

**選項 B**: 修改現有 telegram-adapter response router

在 `telegram-adapter/router/response_router.py` 中：
1. 添加歷史記錄保存邏輯
2. 添加 Web 消息路由邏輯

**建議**: 先用選項 A（新的獨立 Router），測試穩定後再考慮合併。

---

### Step 5: 環境變數總覽

部署完成後，確認以下環境變數已正確設置：

#### telegram-unified-bot-processor
```bash
EVENT_BUS_NAME=telegram-adapter-receiver-events
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BROWSER_ENABLED=true
BINDINGS_TABLE=agentcore-web-adapter-user-bindings  # 新增
```

#### telegram-adapter-receiver
```bash
TELEGRAM_SECRETS_ARN=arn:aws:secretsmanager:...
EVENT_BUS_NAME=telegram-adapter-receiver-events
ALLOWLIST_TABLE_NAME=telegram-allowlist
BINDINGS_TABLE=agentcore-web-adapter-user-bindings  # 新增
BINDING_CODES_TABLE=agentcore-web-adapter-binding-codes  # 新增
```

---

## 🧪 測試整合

### 測試 1: Web 用戶獨立使用（無綁定）

```bash
# 1. 創建 Web 用戶
curl -X POST https://API_ENDPOINT/admin/users \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{"email": "test@example.com", "role": "user"}'

# 2. 登入
curl -X POST https://API_ENDPOINT/auth/login \
  -d '{"email": "test@example.com", "password": "TEMP_PASSWORD"}'

# 3. 建立 WebSocket 連接
wscat -c "wss://WS_ENDPOINT?token=JWT_TOKEN"

# 4. 發送消息
> {"action": "sendMessage", "message": "Hello"}

# 5. 檢查歷史
curl https://API_ENDPOINT/history \
  -H "Authorization: Bearer JWT_TOKEN"
```

### 測試 2: Telegram 綁定

```bash
# 1. Web 端生成綁定碼
curl -X POST https://API_ENDPOINT/binding/generate-code \
  -H "Authorization: Bearer JWT_TOKEN"

# Response: {"code": "123456"}

# 2. Telegram 端執行
# 在 Telegram 發送: /bind 123456

# 3. 驗證綁定成功
curl https://API_ENDPOINT/binding/status \
  -H "Authorization: Bearer JWT_TOKEN"

# 4. 測試跨通道 Memory 共享
# - 在 Web 發送消息
# - 切換到 Telegram，Agent 應該記得 Web 的對話
```

### 測試 3: 歷史記錄

```bash
# 1. 在 Telegram 發送幾條消息
# 2. 在 Web 發送幾條消息
# 3. 查詢完整歷史（應包含兩邊）
curl https://API_ENDPOINT/history \
  -H "Authorization: Bearer JWT_TOKEN"

# 4. 導出為 Markdown
curl https://API_ENDPOINT/history/export?format=markdown \
  -H "Authorization: Bearer JWT_TOKEN"
```

---

## 🚨 注意事項

### 1. EventBridge 事件格式一致性

確保 Web Adapter 發送的事件格式與 Telegram 完全一致：

```python
# 統一消息格式（必須嚴格遵守）
{
    "message_id": "uuid",
    "timestamp": "ISO8601",
    "channel": {
        "type": "web|telegram",
        "channel_id": "connection_id or chat_id",
        "metadata": {}
    },
    "user": {
        "unified_user_id": "uuid",
        "identifier": "email or username",
        "role": "user|admin"
    },
    "content": {
        "text": "message text",
        "message_type": "text",
        "attachments": []
    },
    "context": {
        "conversation_id": "uuid",
        "session_id": "uuid"
    }
}
```

### 2. Memory Service 相容性

修改 Memory Service 時，必須確保：
- Telegram 現有用戶不受影響
- 向後相容（如果 bindings 表不存在，fallback 到舊邏輯）

```python
# 安全的修改範例
def get_session_manager(self, user_info: dict[str, Any] | Any) -> Any | None:
    # 支援新格式（dict）和舊格式（context object）
    if isinstance(user_info, dict):
        session_id = user_info.get('unified_user_id', settings.DEFAULT_SESSION_ID)
        actor_id = user_info.get('identifier', 'user')
    else:
        # 舊格式：context object
        session_id = getattr(user_info, "session_id", settings.DEFAULT_SESSION_ID)
        actor_id = self._extract_actor_id(user_info)
    
    # ... 其餘邏輯
```

### 3. 部署順序

**重要**：必須按以下順序部署以避免依賴問題

1. ✅ 先部署 Web Channel Stack（創建 tables 和 API）
2. ✅ 再更新 ai-processor（添加 BINDINGS_TABLE 環境變數）
3. ✅ 最後更新 telegram-adapter（添加 /bind 指令）

### 4. 回滾計畫

如果需要回滾：

```bash
# 1. 移除 telegram-adapter 的 /bind 指令（可選）
# 2. 恢復 ai-processor 的 Memory Service
# 3. 刪除 Web Channel Stack
aws cloudformation delete-stack --stack-name agentcore-web-adapter --region us-west-2
```

---

## 📋 整合檢查清單

部署完成後，驗證以下項目：

### 基礎設施
- [ ] Web Channel Stack 狀態：CREATE_COMPLETE
- [ ] 所有 5 個 DynamoDB tables 已創建
- [ ] JWT Secret 已創建
- [ ] WebSocket API 已部署
- [ ] REST API 已部署
- [ ] 所有 Lambda 函數狀態：Active

### 環境變數
- [ ] processor: BINDINGS_TABLE 已設置
- [ ] receiver: BINDINGS_TABLE 和 BINDING_CODES_TABLE 已設置

### 功能測試
- [ ] Admin 可以創建 Web 用戶
- [ ] Web 用戶可以登入
- [ ] WebSocket 連接成功
- [ ] Web 消息可以發送和接收
- [ ] /bind 指令可以執行
- [ ] 綁定後兩邊共享 Memory
- [ ] 歷史記錄正確保存（兩個通道）
- [ ] 導出功能正常運作

---

## 🔧 Troubleshooting

### 問題 1: Lambda 找不到 BINDINGS_TABLE

**症狀**: `KeyError: 'BINDINGS_TABLE'`

**解決**: 
```bash
# 檢查環境變數
aws lambda get-function-configuration \
  --function-name FUNCTION_NAME \
  --query 'Environment.Variables.BINDINGS_TABLE'

# 如果不存在，更新
aws lambda update-function-configuration \
  --function-name FUNCTION_NAME \
  --environment "Variables={...,BINDINGS_TABLE=table-name}"
```

### 問題 2: ImportValue 失敗

**症狀**: `Export agentcore-web-adapter-UserBindingsTable not found`

**解決**: 確認 Web Channel Stack 已成功部署且有 Outputs

```bash
aws cloudformation describe-stacks \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs'
```

### 問題 3: WebSocket 連接失敗

**症狀**: Connection refused or 401 Unauthorized

**解決**:
1. 檢查 JWT token 是否有效
2. 檢查 WebSocket endpoint URL 是否正確
3. 查看 connect Lambda 日誌

```bash
aws logs tail /aws/lambda/agentcore-web-adapter-ws-connect \
  --region us-west-2 --since 5m
```

---

## 📚 相關文件

- `ARCHITECTURE.md` - 完整架構設計
- `PROGRESS.md` - 實施進度追蹤
- `web-adapter-template.yaml` - CloudFormation template
- Lambda 函數代碼在 `lambdas/` 目錄

---

**版本**: 1.0  
**最後更新**: 2026-01-08  
**狀態**: Ready for Integration Testing