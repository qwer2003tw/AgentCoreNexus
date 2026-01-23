# 對話紀錄系統實施摘要

**完成日期**: 2026-01-23  
**實施階段**: Phase 1（基礎功能）  
**狀態**: ✅ 代碼實施完成，待部署驗證

---

## 🎯 實施內容

### 1. DynamoDB 表設計
**檔案**: `infrastructure/conversation-storage.yaml`

創建了 3 個表：
- **conversation_history**: 儲存所有對話訊息（PK: conversation_id, SK: timestamp）
- **conversation_metadata**: 對話統計和設定（PK: conversation_id）
- **identity_map**: 跨通道身份綁定（Phase 2 使用）

**特性**：
- ✅ TTL 自動清理（delete_at 欄位）
- ✅ PITR 資料保護（35天恢復）
- ✅ 加密（AWS managed key）
- ✅ PAY_PER_REQUEST 計費模式

---

### 2. 對話儲存服務
**檔案**: `shared/services/conversation_service.py`

**核心功能**：
- `save_message()` - 儲存訊息並更新元數據
- `get_messages()` - 查詢訊息（支援分頁、時間範圍）
- `delete_conversation()` - 軟刪除（30天後硬刪除）
- `restore_conversation()` - 恢復已刪除對話
- `format_messages_for_ai()` - 格式化群組上下文

**設計亮點**：
- 連接池優化（10 connections）
- 自動重試（3 次）
- 錯誤容錯（metadata 失敗不影響訊息儲存）

---

### 3. Telegram 整合
**檔案**: `telegram-adapter/src/handler.py`

**實施內容**：
```python
# 判斷私人 vs 群組
is_group = chat_id < 0

# 構建 conversation_id
conversation_id = f"tg:group:{chat_id}" if is_group else f"tg:{chat_id}"

# 儲存用戶訊息
conversation_service.save_message(
    conversation_id=conversation_id,
    sender_id=f"tg:{user_id}",
    sender_name=username,
    content=text,
    ...
)
```

**特性**：
- ✅ 私人對話自動記錄
- ✅ 群組對話記錄所有成員訊息
- ✅ 追蹤發送者 ID 和名稱
- ✅ 失敗不阻止訊息處理（容錯）

---

### 4. AI Processor 雙寫架構
**檔案**: `ai-processor/processor_entry.py`

**實施邏輯**：
```python
# 群組對話：讀取完整上下文
if is_group:
    group_context = conversation_service.format_messages_for_ai(
        conversation_id=f"tg:group:{conversation_id}",
        limit=30,
        include_sender_name=True
    )
    # 格式：[Alice] 你好\n[Bob] 嗨\n[AI] 大家好

# AI 處理後：儲存回應
conversation_service.save_message(
    conversation_id=conv_id,
    sender_id="ai",
    sender_name="AI Assistant",
    content=response_text,
    ...
)
```

**特性**：
- ✅ 群組 AI 看到完整對話（最近 30 條）
- ✅ AI 回應自動記錄
- ✅ 雙寫：DynamoDB + Bedrock Memory
- ✅ 失敗容錯

---

### 5. Web API
**檔案**: `web-adapter/lambdas/rest/history.py`

**端點**：
- `GET /conversations/{conversation_id}/messages` - 取得對話訊息
  - Query params: `limit`, `start_time`, `next_key`（分頁）
- `DELETE /conversations/{conversation_id}` - 刪除對話（軟刪除）
  - Query param: `hard=true`（硬刪除，慎用）
- `POST /conversations/{conversation_id}/restore` - 恢復對話
- `GET /conversations/{conversation_id}` - 取得元數據

**安全**：
- ✅ JWT token 驗證
- ✅ 用戶只能訪問自己的對話

---

### 6. Lambda Layer
**目錄**: `infrastructure/layers/conversation-layer/`

**用途**: 在所有 Lambda 間共享 conversation_service

**部署**：
```bash
cd infrastructure/layers
./build-layer.sh
zip -r conversation-layer.zip conversation-layer/python/
aws lambda publish-layer-version --layer-name agentcore-conversation-service ...
```

---

### 7. SAM Templates 更新

#### telegram-adapter/template.yaml
```yaml
Environment:
  Variables:
    CONVERSATION_HISTORY_TABLE: agentcore-conversation-history-prod
    CONVERSATION_METADATA_TABLE: agentcore-conversation-metadata-prod

Policies:
  - Effect: Allow
    Action: [dynamodb:PutItem, dynamodb:Query]
    Resource: arn:aws:dynamodb:*:table/agentcore-conversation-*
```

#### ai-processor/template.yaml
```yaml
Environment:
  Variables:
    CONVERSATION_HISTORY_TABLE: agentcore-conversation-history-prod
    CONVERSATION_METADATA_TABLE: agentcore-conversation-metadata-prod

Policies:
  - Effect: Allow
    Action: [dynamodb:PutItem, dynamodb:Query, dynamodb:GetItem]
    Resource: arn:aws:dynamodb:*:table/agentcore-conversation-*
```

---

## 📊 技術決策

### 為什麼選擇雙寫架構？

**Bedrock Memory**（AI 上下文）：
- ✅ 專為 AI 對話優化
- ✅ 自動管理 token 限制
- ✅ 快速的上下文檢索

**DynamoDB**（持久化查詢）：
- ✅ 永久保留
- ✅ 強大的查詢能力
- ✅ 支援分頁和過濾
- ✅ 可用於前端顯示

**結論**: 各司其職，互相備份

---

### 群組對話的混合模式

**設計**：
- 群組共享一個 conversation_id
- 每條訊息記錄 sender_id 和 sender_name
- AI 看到格式化的上下文：`[Alice] 內容`

**優點**：
- ✅ AI 理解誰在說話
- ✅ 完整的對話脈絡
- ✅ 實施簡單

**實施**：
```python
# 群組上下文格式化
formatted = conversation_service.format_messages_for_ai(
    conversation_id="tg:group:-12345",
    limit=30,
    include_sender_name=True
)
# 結果：
# [Alice] 今天天氣如何？
# [AI] 今天晴朗溫暖...
# [Bob] 明天呢？
```

---

## 🚀 部署計劃

### Step 1: 部署 DynamoDB Tables
```bash
cd infrastructure
./deploy-conversation-storage.sh
```

### Step 2: 建立並發布 Lambda Layer
```bash
cd infrastructure/layers
./build-layer.sh
# 然後發布 Layer
```

### Step 3: 更新 Lambda Functions
```bash
# Telegram adapter
cd telegram-adapter && sam build && sam deploy

# AI processor
cd ai-processor && sam build && sam deploy
```

### Step 4: 驗證功能
- 發送測試訊息
- 檢查 DynamoDB
- 查看 CloudWatch 日誌

**完整步驟**: 參考 `DEPLOYMENT.md`

---

## 📈 預期效果

### 功能性
- ✅ 對話永久保留
- ✅ 群組完整上下文
- ✅ Web 查詢和刪除
- ✅ 跨裝置同步（Web）

### 效能
- 寫入延遲：< 20ms
- 查詢延遲：< 50ms
- Lambda 額外開銷：< 10ms

### 成本
- DynamoDB：~$2-3/月
- Lambda：無顯著增加
- **總計：可忽略不計**

---

## 🔍 待完成事項

### 必須（Phase 1）
- [ ] 單元測試（conversation_service）
- [ ] 整合測試（Telegram + Processor）
- [ ] 實際部署驗證

### 建議（Phase 2）
- [ ] identity_map 整合
- [ ] 綁定流程實作
- [ ] Web 前端對話歷史顯示

### 可選（Phase 3）
- [ ] 用戶行為統計
- [ ] 對話搜尋功能
- [ ] 監控 Dashboard

---

## 📚 關鍵檔案清單

### 新增檔案
1. `infrastructure/conversation-storage.yaml` - DynamoDB tables
2. `shared/services/conversation_service.py` - 儲存服務
3. `infrastructure/layers/conversation-layer/` - Lambda Layer
4. `web-adapter/lambdas/rest/history.py` - Web API
5. `infrastructure/deploy-conversation-storage.sh` - 部署腳本
6. `dev-in-progress/conversation-history/DEPLOYMENT.md` - 部署文檔

### 修改檔案
1. `telegram-adapter/src/handler.py` - 添加對話記錄
2. `telegram-adapter/template.yaml` - 環境變數+權限
3. `ai-processor/processor_entry.py` - 雙寫架構
4. `ai-processor/template.yaml` - 環境變數+權限

---

## ✅ 品質保證

### 代碼檢查
- ✅ Ruff 檢查全部通過
- ✅ 格式化完成
- ✅ 無 lint 錯誤

### 設計檢查
- ✅ 8 維度完善性檢查通過
- ✅ 向後兼容
- ✅ 錯誤容錯設計
- ✅ 擴展性良好

---

**實施總耗時**: ~2 小時（規劃 + 實作）  
**預計部署時間**: 30-45 分鐘  
**預計測試時間**: 1-2 小時

**下一步**: 執行部署並驗證功能！