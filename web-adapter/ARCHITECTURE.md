# Web Channel Architecture Design

## 📐 系統架構

### 整體架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React PWA)                     │
│  - Vite + TypeScript + Tailwind CSS + shadcn/ui            │
│  - WebSocket client + REST API client                       │
│  - JWT token in localStorage                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ HTTPS (WebSocket + REST)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Amazon API Gateway                              │
│  - WebSocket API: wss://domain/ws                           │
│  - REST API: https://domain/api                             │
│  - Lambda Authorizer (JWT validation)                       │
└─────────┬──────────────────────┬────────────────────────────┘
          │                      │
          │ WebSocket            │ REST
          ▼                      ▼
┌──────────────────┐   ┌──────────────────────────┐
│ WebSocket Lambda │   │  REST API Lambdas        │
│  - $connect      │   │  - Auth (login/logout)   │
│  - $disconnect   │   │  - History (query/export)│
│  - $default      │   │  - Admin (user mgmt)     │
└────────┬─────────┘   └─────────┬────────────────┘
         │                       │
         │ EventBridge event     │ DynamoDB
         ▼                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    Amazon EventBridge                         │
│  Event Bus: agentcore-nexus-events                           │
│  - message.received (from Web/Telegram)                      │
│  - message.completed (to Response Router)                    │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          │ trigger
                          ▼
┌─────────────────────────────────────────────────────────────┐
│            Processor Lambda (AgentCore)                      │
│  - Receive unified message format                           │
│  - Query user binding → get unified_user_id                 │
│  - Access Memory Service with unified_user_id               │
│  - Process with Bedrock Claude                              │
│  - Send message.completed event                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          │ EventBridge
                          ▼
┌─────────────────────────────────────────────────────────────┐
│            Response Router Lambda                            │
│  - Receive message.completed event                          │
│  - Save to conversation_history                             │
│  - Route to channel (WebSocket or Telegram)                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          │ API Gateway Management API
                          ▼
                    User receives response
```

---

## 🗄️ DynamoDB Tables 設計

### 1. web_users

**用途**：存儲 Web 用戶的認證和基本信息

**Schema**：
```python
{
    'email': 'user@example.com',           # PK (String)
    'password_hash': 'bcrypt_hash...',     # String
    'enabled': True,                       # Boolean
    'role': 'user',                        # String: 'user' | 'admin'
    'created_at': '2026-01-08T12:00:00Z', # String (ISO8601)
    'last_login': '2026-01-08T12:00:00Z', # String (ISO8601)
    'require_password_change': False       # Boolean
}
```

**Indexes**：
- Primary Key: `email` (String)

**Settings**：
- Billing: On-demand
- Encryption: SSE enabled

---

### 2. user_bindings

**用途**：管理跨通道用戶綁定關係

**Schema**：
```python
{
    'unified_user_id': 'uuid-xxxx-xxxx',      # PK (String - UUID)
    'web_email': 'user@example.com',          # String (optional)
    'telegram_chat_id': 123456,               # Number (optional)
    'binding_status': 'complete',             # String: 'pending' | 'complete'
    'created_at': '2026-01-08T12:00:00Z',    # String
    'updated_at': '2026-01-08T12:00:00Z'     # String
}
```

**Indexes**：
- Primary Key: `unified_user_id` (String)
- GSI-1: `web_email` (PK) - for quick lookup by email
- GSI-2: `telegram_chat_id` (PK) - for quick lookup by Telegram ID

**Settings**：
- Billing: On-demand
- Encryption: SSE enabled

---

### 3. conversation_history

**用途**：存儲所有通道的對話歷史

**Schema**：
```python
{
    'unified_user_id': 'uuid-xxxx',           # PK (String)
    'timestamp_msgid': '2026-01-08T12:00:00Z#uuid', # SK (String)
    'role': 'user',                           # String: 'user' | 'assistant'
    'content': {                              # Map
        'text': 'Hello world',
        'attachments': []
    },
    'channel': 'web',                         # String: 'web' | 'telegram'
    'metadata': {                             # Map
        'model': 'claude-3-5-sonnet',
        'tokens': 150
    },
    'ttl': 1704672000                        # Number (Unix timestamp + 90 days)
}
```

**Indexes**：
- Primary Key: `unified_user_id` (String)
- Sort Key: `timestamp_msgid` (String) - enables time-based queries
- GSI-1: `channel` (PK) + `timestamp_msgid` (SK) - for channel-specific queries

**Settings**：
- Billing: On-demand
- TTL: Enabled on `ttl` attribute (90 days)
- Encryption: SSE enabled

---

### 4. websocket_connections

**用途**：管理活躍的 WebSocket 連接

**Schema**：
```python
{
    'connection_id': 'abc123',                # PK (String)
    'unified_user_id': 'uuid-xxxx',          # String
    'email': 'user@example.com',             # String
    'connected_at': '2026-01-08T12:00:00Z',  # String
    'last_activity': '2026-01-08T12:05:00Z', # String
    'ttl': 1704672000                        # Number (Unix timestamp + 2 hours)
}
```

**Indexes**：
- Primary Key: `connection_id` (String)
- GSI-1: `unified_user_id` (PK) + `connected_at` (SK) - find all connections for a user

**Settings**：
- Billing: On-demand
- TTL: Enabled on `ttl` attribute (2 hours)
- Encryption: SSE enabled

---

### 5. binding_codes

**用途**：臨時存儲帳號綁定驗證碼

**Schema**：
```python
{
    'code': '123456',                        # PK (String - 6 digits)
    'web_email': 'user@example.com',         # String
    'created_at': '2026-01-08T12:00:00Z',   # String
    'expires_at': '2026-01-08T12:05:00Z',   # String (5 minutes)
    'status': 'pending',                     # String: 'pending' | 'used' | 'expired'
    'ttl': 1704672000                       # Number (Unix timestamp + 10 minutes)
}
```

**Indexes**：
- Primary Key: `code` (String)
- GSI-1: `web_email` (PK) - find active codes for an email

**Settings**：
- Billing: On-demand
- TTL: Enabled on `ttl` attribute (10 minutes cleanup)
- Encryption: SSE enabled

---

## 🔐 Secrets Manager

### JWT Secret

**Secret Name**: `agentcore-nexus/web-adapter/jwt-secret`

**Content**:
```json
{
  "jwt_secret": "base64-encoded-256-bit-random-key",
  "jwt_algorithm": "HS256",
  "jwt_expiry_days": 7
}
```

**Usage**: Lambda Authorizer 和 Auth Lambda 使用此 secret 簽名和驗證 JWT tokens

---

## 🌐 API Gateway 設計

### WebSocket API

**Endpoint**: `wss://[api-id].execute-api.us-west-2.amazonaws.com/prod`

**Routes**:
- `$connect`: 建立連接，驗證 JWT token，記錄到 websocket_connections
- `$disconnect`: 清理連接記錄
- `$default`: 接收用戶消息，發送到 EventBridge

**Authorization**: Lambda Authorizer (JWT validation)

---

### REST API

**Endpoint**: `https://[api-id].execute-api.us-west-2.amazonaws.com/prod`

**Routes**:

#### Authentication
- `POST /auth/login` - 登入
- `POST /auth/logout` - 登出
- `POST /auth/change-password` - 修改密碼
- `GET /auth/me` - 獲取當前用戶資訊

#### History
- `GET /history` - 查詢對話歷史（分頁）
- `GET /history/export` - 導出對話（JSON/Markdown）
- `GET /history/stats` - 獲取統計資訊

#### Binding
- `POST /binding/generate-code` - 生成綁定驗證碼
- `GET /binding/status` - 查詢綁定狀態

#### Admin (需要 admin 權限)
- `POST /admin/users` - 創建 Web 用戶
- `GET /admin/users` - 列出用戶
- `PUT /admin/users/:email/password` - 重置密碼
- `PUT /admin/users/:email/role` - 修改角色
- `GET /admin/bindings` - 查看所有綁定

**Authorization**: Lambda Authorizer (JWT validation)

---

## 🔄 消息流程

### Web 用戶發送消息

```
1. User types message in frontend
2. Frontend sends via WebSocket: 
   {
     "action": "sendMessage",
     "message": "Hello"
   }

3. WebSocket Lambda ($default route):
   - Extract connection_id
   - Query websocket_connections → get unified_user_id
   - Create unified message format
   - Send to EventBridge: message.received

4. Processor Lambda (triggered by EventBridge):
   - Receive message.received event
   - Extract unified_user_id
   - Query Memory Service with unified_user_id
   - Process with AgentCore + Bedrock
   - Send to EventBridge: message.completed

5. Response Router Lambda (triggered by EventBridge):
   - Receive message.completed event
   - Save to conversation_history
   - Query websocket_connections by unified_user_id
   - Send response via API Gateway Management API

6. User receives response via WebSocket
```

---

### 統一消息格式 (EventBridge)

```python
{
    'message_id': 'uuid-xxxx',
    'timestamp': '2026-01-08T12:00:00Z',
    'channel': {
        'type': 'web',  # 'web' | 'telegram'
        'channel_id': 'connection_id or chat_id',
        'metadata': {}
    },
    'user': {
        'unified_user_id': 'uuid-xxxx',
        'identifier': 'user@example.com or telegram_username',
        'role': 'user'
    },
    'content': {
        'text': 'Hello',
        'message_type': 'text',
        'attachments': []
    },
    'context': {
        'conversation_id': 'uuid-xxxx',
        'session_id': 'uuid-xxxx'
    }
}
```

---

## 🔒 安全考量

### JWT Token
- Algorithm: HS256
- Expiry: 7 days
- Storage: localStorage (XSS risk mitigated by input validation)
- Refresh: Manual re-login after expiry

### Password Security
- Algorithm: bcrypt
- Rounds: 12
- Min length: 8 characters
- Complexity: Required (uppercase + lowercase + number)

### Rate Limiting
- Login attempts: 5 per 15 minutes per email
- API calls: 100 per minute per user
- WebSocket messages: 10 per second per connection

### Input Validation
- Email: RFC 5322 validation
- All user inputs: XSS prevention (escape HTML)
- SQL injection: Not applicable (using DynamoDB)

---

## 📊 性能目標

### API Response Times (p95)
- Authentication: < 200ms
- History query: < 500ms
- WebSocket message: < 100ms

### WebSocket
- Connection limit: 500 concurrent (default, can request increase)
- Message size: < 128KB
- Idle timeout: 2 hours

### DynamoDB
- Read capacity: On-demand (auto-scale)
- Write capacity: On-demand (auto-scale)
- Query latency: < 10ms (single item)

---

## 🔄 錯誤處理

### Lambda Error Handling
- Retry: 2 times with exponential backoff
- DLQ: SQS queue for failed events
- Logging: CloudWatch Logs with structured JSON

### WebSocket Disconnect
- Client reconnect: Exponential backoff (1s, 2s, 4s, 8s, max 30s)
- Server cleanup: TTL-based automatic cleanup

### EventBridge Failures
- DLQ: Failed events sent to SQS
- Monitoring: CloudWatch alarms on failure count

---

## 📈 監控指標

### CloudWatch Metrics
- Lambda invocations and errors
- API Gateway 4xx/5xx errors
- DynamoDB throttling events
- WebSocket connections count
- EventBridge failed deliveries

### Custom Metrics
- Active users count
- Messages per minute
- Average response time
- Binding success rate

### Alarms
- Lambda error rate > 1%
- API Gateway 5xx > 0.5%
- WebSocket disconnect rate > 10%
- DynamoDB throttling > 0

---

## 🚀 部署策略

### Infrastructure as Code
- Tool: AWS SAM (Serverless Application Model)
- Format: YAML templates
- Version control: Git

### Deployment Stages
1. Development: Manual SAM deploy
2. Staging: Automated on push to `develop` branch
3. Production: Manual approval after staging validation

### Rollback Strategy
- CloudFormation stack rollback on failure
- Lambda version aliases for instant rollback
- Blue-green deployment for zero-downtime

---

**Version**: 1.0  
**Last Updated**: 2026-01-08  
**Status**: Design Complete, Ready for Implementation