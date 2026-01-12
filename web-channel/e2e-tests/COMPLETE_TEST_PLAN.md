# Web Channel 完整測試計劃（120 個測試）

**創建時間**：2026-01-12  
**預計完成時間**：1-2 週  
**當前進度**：10+/120（~10%）

---

## 📊 當前狀態

### 已完成的測試（E2E）
- ✅ Chat Core（5/5 通過）- 100%
- ✅ Authentication（5/5 通過）- 100%
- ⏳ Conversations（執行中，預計 3-4/6 通過）

**預期當前完成**：13-15/16 E2E 測試

---

## 📋 完整測試清單（120 個測試）

### Phase 1: E2E 測試（34 個）⏰ 預計 1-2 天

#### 1.1 已撰寫測試（16 個）
- [x] chat.spec.ts（5 個）- ✅ 全部通過
- [x] auth.spec.ts（5 個）- ✅ 全部通過
- [ ] conversations.spec.ts（6 個）- 執行中

**狀態**：10+/16 完成

#### 1.2 錯誤處理測試（10 個）- 需新增
**文件**：`tests/errors.spec.ts`

```typescript
test.describe('Error Handling', () => {
  // API 錯誤（5 個）
  test('handles 500 server error')
  test('handles 401 unauthorized')
  test('handles 403 forbidden')
  test('handles 404 not found')
  test('handles network timeout')
  
  // WebSocket 錯誤（3 個）
  test('handles WebSocket connection failure')
  test('retries failed message send')
  test('reconnects after disconnect')
  
  // UI 錯誤（2 個）
  test('displays error messages to user')
  test('recovers from error state')
})
```

**時間**：2 小時

#### 1.3 邊界情況測試（8 個）- 需新增
**文件**：`tests/edge-cases.spec.ts`

```typescript
test.describe('Edge Cases', () => {
  // 空狀態（3 個）
  test('handles empty conversation list')
  test('handles empty message history')
  test('handles search with no results')
  
  // 極限值（3 個）
  test('handles very long messages (>4000 chars)')
  test('handles many conversations (>50)')
  test('handles rapid clicking')
  
  // 特殊字元（2 個）
  test('handles emoji in messages')
  test('prevents XSS with HTML/script tags')
})
```

**時間**：1.5 小時

**Phase 1 總計**：34 個 E2E 測試

---

### Phase 2: Backend 單元測試（35 個）⏰ 預計 3-4 天

#### 2.1 WebSocket Lambda 測試（12 個）
**文件**：`lambdas/websocket/tests/`

```
tests/
├── test_connect.py
│   ├── test_jwt_validation
│   ├── test_create_connection_record
│   ├── test_get_unified_user_id
│   ├── test_ttl_calculation
│   └── test_error_handling (3 個場景)
├── test_default.py
│   ├── test_parse_message
│   ├── test_handle_conversation_id
│   ├── test_send_to_eventbridge
│   └── test_error_handling (2 個場景)
└── test_disconnect.py
    ├── test_cleanup_connection
    └── test_error_handling
```

**時間**：1 天

#### 2.2 REST API Lambda 測試（15 個）
**文件**：`lambdas/rest/tests/`

```
tests/
├── test_auth.py
│   ├── test_login_success
│   ├── test_login_failure
│   ├── test_jwt_generation
│   ├── test_bcrypt_validation
│   ├── test_change_password
│   └── test_get_current_user
├── test_authorizer.py
│   ├── test_jwt_decode
│   ├── test_policy_generation
│   ├── test_expired_token
│   └── test_invalid_token
└── test_conversations.py
    ├── test_list_conversations
    ├── test_create_conversation
    ├── test_update_conversation
    ├── test_delete_conversation
    └── test_get_messages
```

**時間**：1.5 天

#### 2.3 Response Router 測試（8 個）
**文件**：`lambdas/router/tests/test_router.py`

```python
def test_parse_eventbridge_event()
def test_extract_conversation_id()
def test_generate_title()
def test_send_to_websocket()
def test_save_history()
def test_update_conversation_metadata()
def test_handle_telegram_channel()
def test_error_handling()
```

**時間**：1 天

**Phase 2 總計**：35 個 Backend 單元測試

---

### Phase 3: Frontend 單元測試（37 個）⏰ 預計 3-4 天

#### 3.1 Store 測試（12 個）
**工具**：Vitest + Testing Library

**文件**：`frontend/src/stores/__tests__/`

```
__tests__/
├── authStore.test.ts
│   ├── test login
│   ├── test logout
│   ├── test token management
│   ├── test user state
│   └── test error handling
└── chatStore.test.ts
    ├── test load conversations
    ├── test create conversation
    ├── test switch conversation
    ├── test send message
    ├── test add message with routing
    ├── test update title
    └── test search/filter
```

**時間**：1.5 天

#### 3.2 Service 測試（10 個）
**文件**：`frontend/src/services/__tests__/`

```
__tests__/
├── api.test.ts
│   ├── test auth endpoints (4 個)
│   ├── test conversation endpoints (4 個)
│   └── test error handling (2 個)
└── websocket.test.ts
    ├── test connect
    ├── test disconnect
    ├── test send message
    ├── test on message
    └── test reconnection
```

**時間**：1 天

#### 3.3 Component 測試（15 個）- 可選
**文件**：`frontend/src/components/__tests__/`

```
__tests__/
├── Chat/
│   ├── ChatWindow.test.tsx (3 個)
│   ├── MessageList.test.tsx (4 個)
│   └── Sidebar.test.tsx (3 個)
├── ConversationList.test.tsx (3 個)
└── LoginPage.test.tsx (2 個)
```

**時間**：1.5 天

**Phase 3 總計**：37 個 Frontend 單元測試

---

### Phase 4: 整合測試（14 個）⏰ 預計 2-3 天

#### 4.1 Backend 整合測試（8 個）
```
tests/integration/backend/
├── test_lambda_dynamodb.py (3 個)
├── test_eventbridge_flow.py (3 個)
└── test_api_gateway_lambda.py (2 個)
```

#### 4.2 Frontend 整合測試（6 個）
```
tests/integration/frontend/
├── test_api_integration.ts (3 個)
└── test_store_integration.ts (3 個)
```

**Phase 4 總計**：14 個整合測試

---

### Phase 5: CI/CD 設置⏰ 預計 1 天

```
.github/workflows/
└── test.yml
    ├── Run E2E tests on PR
    ├── Run unit tests on PR
    ├── Upload test reports
    └── Coverage tracking
```

---

## 🎯 執行時間表

### Week 1: E2E 測試完成
- **Day 1**（今天）：
  - [x] 執行已撰寫測試（10/16）
  - [ ] 修復失敗測試
  - [ ] 添加錯誤處理測試（10 個）
  
- **Day 2-3**：
  - [ ] 添加邊界測試（8 個）
  - [ ] 執行完整 E2E 套件
  - [ ] 34/34 E2E 測試完成

### Week 2: Backend 單元測試
- **Day 4-5**：WebSocket + REST Lambda（27 個）
- **Day 6**：Response Router（8 個）
- **目標**：35/35 Backend 單元測試

### Week 3: Frontend 單元測試
- **Day 7-8**：Store + Service 測試（22 個）
- **Day 9**：Component 測試（15 個）- 可選
- **目標**：37/37 Frontend 單元測試

### Week 4: 整合測試和 CI/CD
- **Day 10-11**：整合測試（14 個）
- **Day 12**：CI/CD 設置
- **目標**：完整測試管線

---

## ⚠️ 重要說明

**這是一個 1-2 週的大型任務**，無法在單個會話中完成所有 120 個測試。

### 建議的執行方式

**今天（會話中）**：
1. 完成所有已撰寫的 E2E 測試
2. 添加錯誤處理測試框架
3. 執行並驗證

**後續（分多個會話）**：
1. 逐步添加新測試
2. 每完成一個 Phase 驗證
3. 持續更新進度

---

## 📈 當前進度追蹤

**E2E 測試**：10-13/34（~35%）  
**Backend 單元**：0/35（0%）  
**Frontend 單元**：0/37（0%）  
**整合測試**：0/14（0%）  
**總進度**：10-13/120（~10%）

**預期本會話完成**：20-25/120（E2E 部分）  
**剩餘工作**：需要額外 1-2 週時間

---

**當前執行**：Conversations 測試中...