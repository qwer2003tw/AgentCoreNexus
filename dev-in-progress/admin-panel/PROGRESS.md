# Feature: 管理員對話記錄管理系統

**狀態**: 🔄 進行中  
**開始時間**: 2026-01-26  
**負責 Agent**: Cline (ACT MODE)

---

## 📋 任務清單

### Week 1：後端核心（7天）

#### Day 1-2：DynamoDB 基礎設施
- [ ] 更新 conversation_history 表（添加雙 GSI）
- [ ] 創建 conversation_summaries 表
- [ ] 創建 admin_audit_logs 表
- [ ] 創建 admin_system_config 表
- [ ] 配置 PITR（Point-in-Time Recovery）
- [ ] 部署並驗證

#### Day 3-4：核心服務實現
- [ ] 實現 AuditService（shared/services/audit_service.py）
- [ ] 實現審計裝飾器（auto logging）
- [ ] 更新 ConversationService（添加 global_partition）
- [ ] 實現權限檢查中間件

#### Day 5-6：對話管理 API
- [ ] 對話列表 API（使用 GlobalTimestampIndex）
- [ ] 對話詳情 API
- [ ] 關鍵字搜尋 API
- [ ] 附件預覽 API

#### Day 7：AI 摘要和審計 API
- [x] AI 摘要生成 API（含附件統計）✅ 2026-01-27
- [x] 審計日誌查詢 API ✅ 已實現（Day 5-6）
- [ ] 單元測試（覆蓋率 > 80%）

### Week 2：前端介面（7天）
- [ ] 待實施...

---

## 🎯 當前目標

**Day 1-2: 創建 DynamoDB 基礎設施**

### 需要創建/更新的表

1. **conversation_history**（更新）
   - 添加 GlobalTimestampIndex GSI
   - 添加 ChannelTimestampIndex GSI
   - 配置 PITR

2. **conversation_summaries**（新建）
   - 存儲 AI 生成的摘要
   - 包含附件統計

3. **admin_audit_logs**（新建）
   - 記錄所有管理員操作
   - 支持多種查詢模式（by admin, by resource, by action）

4. **admin_system_config**（新建）
   - 存儲系統配置（如審計日誌 TTL）

---

## 🔍 技術決策

### DynamoDB GSI 方案
- **GSI-1**: global_partition (固定 'ALL') + timestamp
- **GSI-2**: channel + timestamp
- **查詢延遲目標**: < 50ms

### AI 摘要策略
- 手動觸發（按鈕）
- 快取結果避免重複生成
- 註明附件數量（X 張圖片、Y 個文件）

### 審計日誌
- 43+ 操作類型
- 可調整 TTL（默認 90 天）
- 4 角色權限系統

---

## 📝 開發筆記

**2026-01-26 15:20**：開始實施，創建進度追蹤文件

**2026-01-26 15:25**：✅ DynamoDB 基礎設施完成
- 創建 3 個新表：conversation_summaries, admin_audit_logs, admin_system_config
- 更新 conversation_history：添加 GlobalTimestampIndex 和 ChannelTimestampIndex
- 所有 GSI 狀態：ACTIVE
- 部署用時：~5 分鐘

**2026-01-26 15:25**：✅ 核心服務實現完成
- 實現 AuditService（43+ 操作類型，可調整 TTL，3 個 GSI）
- 實現審計裝飾器（自動記錄，權限檢查）
- 更新 ConversationService（添加 global_partition 支持 GSI）

**2026-01-26 15:34**：✅ Day 1-4 核心組件全部完成
- 所有服務導入測試通過
- Python 3.9 兼容性修復完成
- 代碼質量檢查通過（Ruff）

**完成統計（Day 1-4）**：
- ✅ 5 DynamoDB tables（全部 ACTIVE）
- ✅ 5 Global Secondary Indexes（全部 ACTIVE）
- ✅ 53 審計操作類型定義
- ✅ 4 角色權限系統（user/admin/auditor/super_admin）
- ✅ 4 系統配置（保留策略可調整）
- ✅ 2 核心服務（AuditService + ConversationService 更新）
- ✅ 2 輔助模組（審計裝飾器 + 權限檢查）

**2026-01-27 13:08**：✅ Day 7 AI 摘要功能完成
- 實現 `generate_summary()` API endpoint
- 添加 Bedrock 權限到 AdminApiFunction
- 實現 24 小時摘要緩存機制
- 支持附件統計（圖片 + 文件）
- 使用 Claude 3 Haiku 模型（快速 + 便宜）
- 部署時間：~3 分鐘

**部署資訊**：
- Stack: `agentcore-web-adapter`
- Lambda: `agentcore-web-adapter-admin-api`
- API Endpoint: `https://jooap0xv8l.execute-api.us-west-2.amazonaws.com/prod`
- 摘要 Endpoint: `POST /admin/conversations/{conversation_id}/summary`

---

## ⚠️ 問題與風險

（目前無）

---

## 🧪 測試指引

### API 測試（使用 curl）

```bash
# 替換 YOUR_JWT_TOKEN 和 CONVERSATION_ID
curl -X POST "https://jooap0xv8l.execute-api.us-west-2.amazonaws.com/prod/admin/conversations/telegram:316743844/summary" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

### 前端測試

1. 登入管理面板
2. 進入對話詳情頁
3. 點擊「生成 AI 摘要」按鈕
4. 等待 5-10 秒
5. 應該看到摘要內容顯示

### 預期響應

```json
{
  "conversation_id": "telegram:316743844",
  "summary_text": "【對話摘要】\n...",
  "attachment_stats": {
    "images": 3,
    "documents": 1,
    "total": 4
  },
  "generated_at": 1738065600000,
  "model_used": "anthropic.claude-3-haiku-20240307-v1:0",
  "cached": false
}
```

### 驗證緩存

- 第一次調用：`cached: false`（生成新摘要，約 5-10 秒）
- 24 小時內再次調用：`cached: true`（立即返回，< 1 秒）

---

## 🎓 學習記錄

（待記錄）