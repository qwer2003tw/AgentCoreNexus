# Feature: 網頁通道擴展

**狀態**: 🔄 進行中  
**開始時間**: 2026-01-08  
**負責 Agent**: Cline AI

---

## 📋 任務清單

### Phase 1: 基礎設施準備（Week 1）
- [ ] 設計統一歷史記錄架構（Telegram + Web 共用）
- [ ] 創建 web_users table（email PK）
- [ ] 保留 allowlist table（Telegram 專用，不修改）
- [ ] 創建 user_bindings table（UUID）
- [ ] 創建 binding_codes table（6位數驗證碼）
- [ ] 創建 conversation_history table（90天 TTL）
- [ ] 創建 websocket_connections table
- [ ] 設置 Secrets Manager（JWT secret）
- [ ] 創建 WebSocket + REST API Gateway

### Phase 2: 認證系統開發（Week 2）
- [ ] 實現 Web Auth Lambda（email/password）
- [ ] 實現 Lambda Authorizer（JWT localStorage）
- [ ] 實現 Admin API（創建 Web 帳號）
- [ ] 實現統一權限檢查（telegram + web）
- [ ] 實現 Rate Limiting（5次失敗鎖15分鐘）
- [ ] 實現密碼安全（bcrypt）
- [ ] 實現 JWT token（7天有效期）

### Phase 3: Backend 核心服務（Week 3-4）
- [ ] 實現 unified_user_id 解析（UUID）
- [ ] 修改 Memory Service（使用 unified_user_id）
- [ ] 修改 Response Router（保存歷史）
- [ ] 開發 History Service（時間分組 + 分頁）
- [ ] 開發 Binding Service（6位數驗證碼 + 5分鐘）
- [ ] 開發 Web Adapter Lambda
- [ ] 開發 Export Service（JSON + Markdown）
- [ ] 新增 Telegram /bind 指令
- [ ] 實現 WebSocket 連接管理（最新連接優先）

### Phase 4: 前端開發（Week 5-6）
- [ ] 設置 React + Vite + TypeScript
- [ ] 實現認證界面（email + password + localStorage）
- [ ] 實現即時聊天（參考 ChatGPT UI）
- [ ] 實現對話列表（時間分組，無 AI 標題）
- [ ] 實現歷史查看（分頁載入）
- [ ] 實現帳號綁定（顯示驗證碼）
- [ ] 實現對話導出（JSON + Markdown + 90天提醒）
- [ ] 實現暗色模式（預設）
- [ ] PWA 基礎（manifest + 離線提示）
- [ ] 響應式設計（mobile-first）
- [ ] WebSocket 重連邏輯
- [ ] 整合 Tailwind CSS + shadcn/ui

### Phase 5: 後台管理界面（Week 6）
- [ ] 用戶管理（Web users）
- [ ] 創建帳號（email + 臨時密碼）
- [ ] 手動密碼重置（Admin only）
- [ ] 權限管理
- [ ] 綁定狀態查看
- [ ] 基本審計日誌

### Phase 6: 整合與測試（Week 7）
- [ ] 認證流程測試
- [ ] 跨通道綁定測試
- [ ] Memory 共享測試
- [ ] 歷史記錄同步測試
- [ ] 導出功能測試
- [ ] PWA 功能測試
- [ ] 暗色模式測試
- [ ] WebSocket 重連測試
- [ ] 單設備連接測試
- [ ] 安全測試（JWT + bcrypt + Rate Limiting）
- [ ] 端到端測試
- [ ] 性能測試

### Phase 7: 部署與監控（Week 8）
- [ ] 編寫 IaC (SAM/CloudFormation)
- [ ] 配置 CloudFront（僅靜態資源）
- [ ] 設置監控和告警
- [ ] 配置錯誤恢復（DLQ）
- [ ] 編寫用戶文檔
- [ ] 編寫管理員文檔
- [ ] 上線部署

---

## 🎯 目標

### 主要目標
- 為 AgentCoreNexus 添加 Web 通道支援
- 實現跨通道（Telegram + Web）的統一用戶體驗
- 提供可回顧的對話歷史記錄
- 支援跨通道帳號綁定，共享 Memory 和歷史

### 技術目標
- 保持現有 Telegram 功能完全不受影響
- 使用 DynamoDB 簡化認證（無需 Cognito）
- 實現 PWA 提供類原生應用體驗
- 確保安全性和性能

---

## 📐 核心架構

### 數據模型

#### 1. web_users (新增)
```python
{
  'email': 'user@example.com',  # PK
  'password_hash': 'bcrypt...',
  'web_session_token': 'jwt...',
  'enabled': True,
  'role': 'user|admin',
  'created_at': timestamp
}
```

#### 2. allowlist (現有，保持不變)
```python
{
  'chat_id': 123456,  # PK - Telegram chat_id
  'username': 'telegram_user',
  'enabled': True,
  'role': 'user|admin'
}
```

#### 3. user_bindings (新增)
```python
{
  'unified_user_id': 'uuid-xxxx',  # PK - UUID
  'telegram_chat_id': 123456,      # 可選
  'web_email': 'user@example.com', # 可選
  'binding_status': 'complete',
  'created_at': timestamp
}
```

#### 4. conversation_history (新增)
```python
{
  'unified_user_id': 'uuid-xxxx',  # PK
  'timestamp_msgid': 'ISO8601#uuid', # SK
  'role': 'user|assistant',
  'content': {...},
  'channel': 'web|telegram',
  'ttl': timestamp + 90days
}
```

### 消息流
```
Web Frontend (React PWA)
  ↓ WebSocket + REST API
API Gateway (Lambda Authorizer)
  ↓
Web Adapter Lambda
  ↓ EventBridge (統一消息格式)
Processor Lambda (AgentCore + Memory)
  ↓ EventBridge
Response Router Lambda
  ↓
WebSocket 回傳 + 歷史記錄保存
```

---

## 📝 關鍵設計決策

### 已確認決策
1. **數據模型**：web_users + allowlist 分開管理，user_bindings 連接
2. **用戶識別**：Web 用 email，Telegram 用 chat_id，統一用 UUID
3. **認證方式**：DynamoDB + JWT（localStorage，7天），無 Cognito
4. **對話分組**：按時間自動分組（今天/昨天/本週/更早）
5. **WebSocket**：MVP 只支援單設備（最新連接優先）
6. **歷史保留**：90天 TTL + 導出提醒
7. **離線支援**：PWA 基礎（manifest + 離線提示）
8. **密碼重置**：MVP 用 Admin 手動重置
9. **前端技術**：React + Vite + TypeScript + Tailwind + shadcn/ui
10. **CloudFront**：僅用於靜態資源

### 延後到 Phase 2
- AI 生成對話標題
- 多設備消息廣播
- 離線消息隊列
- Email 密碼重置
- 檔案上傳功能
- PDF 導出
- 對話永久保存

---

## ⚠️ 問題與風險

### 已識別風險
1. **WebSocket 連接管理**：需要處理斷線重連和清理過期連接
2. **Memory Service 修改**：需要確保不影響現有 Telegram 用戶
3. **多表查詢性能**：web_users + bindings 需要優化查詢路徑
4. **JWT localStorage**：有 XSS 風險，但內部系統可接受

### 緩解措施
- 充分測試 Memory Service 修改
- 實現索引優化多表查詢
- 實施嚴格的輸入驗證防 XSS
- 使用短期 token + 審計日誌

---

## 📊 進度追蹤

**當前階段**: Phase 1 - 基礎設施準備  
**完成進度**: 0/67 項 (0%)  
**預計完成**: 2026-03-08 (8週)

---

## 📝 開發筆記

### 2026-01-08
- ✅ 完成需求分析和技術決策
- ✅ 確定數據模型和架構設計
- ✅ 創建開發目錄和進度追蹤
- 🔄 準備開始 Phase 1 實施