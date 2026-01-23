# Feature: 對話紀錄系統

**狀態**: 🔄 進行中  
**開始時間**: 2026-01-23  
**負責 Agent**: Cline (ACT MODE)

## 📋 任務清單

### Phase 1: 基礎功能（優先）
- [ ] 設計並創建 DynamoDB 表
  - [ ] conversation_history 表（訊息主表）
  - [ ] conversation_metadata 表（對話元數據）
  - [ ] 在 SAM template 中配置
- [ ] 實作對話儲存服務（conversation_service.py）
  - [ ] save_message() - 儲存訊息
  - [ ] get_messages() - 查詢訊息
  - [ ] delete_conversation() - 軟刪除
- [ ] Telegram 整合
  - [ ] 私人對話記錄
  - [ ] 群組對話記錄（追蹤發送者）
  - [ ] 群組觸發邏輯（@ bot）
- [ ] Web 整合
  - [ ] REST API: GET /conversations/{id}/messages
  - [ ] REST API: DELETE /conversations/{id}
  - [ ] WebSocket 訊息記錄
- [ ] Memory Service 雙寫
  - [ ] processor_entry.py 整合
  - [ ] 錯誤恢復機制
- [ ] 測試
  - [ ] 單元測試
  - [ ] 整合測試
  - [ ] E2E 測試

### Phase 2: 進階功能（後續）
- [ ] identity_map 表（跨通道綁定）
- [ ] 綁定流程實作
- [ ] 進階查詢和過濾

### Phase 3: 分析功能（未來）
- [ ] 用戶行為統計
- [ ] 對話品質分析
- [ ] 監控 Dashboard

## 🎯 設計決策

### 核心原則
1. **群組對話**：混合模式（選項C）
   - 群組共享 conversation_id
   - 記錄每條訊息的 sender_id/name
   - AI 掌握完整群組上下文
   - 只有 allowlist 成員能觸發（@ bot 或關鍵字）

2. **資料保留**：永久保留 + TTL
   - Session 結束前持續保留
   - Web 刪除功能：軟刪除 + 30天後硬刪除（TTL）

3. **跨通道綁定**：選項B（綁定後共享）
   - 需要明確綁定
   - 綁定後使用 unified conversation_id

4. **Web 用戶**：必須登入
   - 使用 UUID + JWT
   - 無匿名用戶

### conversation_id 格式
- Telegram 私人：`tg:{user_id}`
- Telegram 群組：`tg:group:{group_id}`
- Web 登入：`web:{user_id}`
- 跨通道綁定：`unified:{uuid}`

### DynamoDB 表結構

#### conversation_history
```
PK: conversation_id (String)
SK: timestamp (Number)
Attributes:
  - message_id (String)
  - sender_id (String)
  - sender_name (String)
  - content (String)
  - message_type (String)
  - channel (String)
  - delete_at (Number, TTL)
  - metadata (Map)
```

#### conversation_metadata
```
PK: conversation_id (String)
Attributes:
  - created_at (Number)
  - last_message_at (Number)
  - message_count (Number)
  - participant_ids (List)
  - channel (String)
  - is_group (Boolean)
  - deleted_at (Number)
```

### Memory Service 整合
- **雙寫架構**：
  1. 用戶訊息 → 寫入 DynamoDB
  2. AI 處理 → 使用 Bedrock Memory Service
  3. AI 回應 → 寫入 DynamoDB
- **優點**：各司其職，可容錯

## 📝 開發筆記

### 2026-01-23
- ✅ 完成規劃階段（Plan Mode）
- ✅ 確認所有核心決策
- ✅ 通過 8 維度完善性檢查（95% 完整）
- ✅ 開始實施 Phase 1

#### 實施完成項目：
1. ✅ 創建 DynamoDB 表定義（conversation-storage.yaml）
   - conversation_history 表（PK+SK，TTL 啟用，PITR）
   - conversation_metadata 表（統計和設定）
   - identity_map 表（Phase 2 跨通道綁定）

2. ✅ 實作對話儲存服務
   - shared/services/conversation_service.py
   - save_message(), get_messages(), delete_conversation()
   - format_messages_for_ai()（群組上下文）

3. ✅ Telegram 整合
   - handler.py 添加對話記錄功能
   - 支援私人和群組對話
   - 群組記錄所有訊息（追蹤發送者）

4. ✅ AI Processor 整合
   - processor_entry.py 雙寫架構
   - 群組對話讀取完整上下文
   - AI 回應寫入對話歷史

5. ✅ Web API 創建
   - web-adapter/lambdas/rest/history.py
   - GET /conversations/{id}/messages
   - DELETE /conversations/{id}（軟刪除）
   - POST /conversations/{id}/restore

6. ✅ Lambda Layer 配置
   - infrastructure/layers/conversation-layer/
   - 共享 conversation_service.py
   - requirements.txt

7. ✅ SAM Templates 更新
   - telegram-adapter/template.yaml（環境變數+權限）
   - ai-processor/template.yaml（環境變數+權限）

8. ✅ 部署腳本和文檔
   - infrastructure/deploy-conversation-storage.sh
   - infrastructure/layers/build-layer.sh
   - dev-in-progress/conversation-history/DEPLOYMENT.md

#### 待完成項目：
- [ ] 代碼質量檢查完成（執行中）
- [ ] 單元測試
- [ ] 整合測試
- [ ] 實際部署驗證

## ⚠️ 關鍵考量

1. **群組觸發邏輯**（決策1: B）
   - @ bot 觸發
   - 可配置關鍵字（Phase 1 先實作 @ bot）
   - 記錄所有訊息但只在觸發時回應

2. **查詢限制**（決策3）
   - 初始載入：50 條
   - 分頁大小：20-30 條
   - 最大限制：500 條

3. **實施優先級**（決策4）
   - Phase 1：基礎對話紀錄（2-3 天）
   - Phase 2：跨通道綁定
   - Phase 3：進階分析

## 🔗 相關資源

- `docs/DYNAMODB_DESIGN.md` - DynamoDB 設計文檔
- `docs/architecture-guide.md` - 架構指南
- `telegram-adapter/src/handler.py` - Telegram handler
- `ai-processor/processor_entry.py` - AI 處理器入口
- `web-adapter/lambdas/rest/` - Web REST API

## 📊 預期成果

Phase 1 完成後：
- ✅ 所有對話永久保留在 DynamoDB
- ✅ Telegram 私人和群組對話完整記錄
- ✅ Web 對話可查詢和刪除
- ✅ AI 透過 Memory Service 保持上下文
- ✅ 為 Phase 2/3 打好基礎