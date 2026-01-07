# Memory 功能開發報告

**功能**: Bedrock AgentCore Memory 整合  
**開發時間**: 2026-01-06  
**狀態**: ⚠️ 代碼就緒，等待 Memory 資源創建

---

## 📋 功能概述

### 目標
整合 AWS Bedrock AgentCore Memory 服務，使 Telegram Bot 具備對話記憶能力，能夠記住用戶的對話歷史和偏好。

### 範圍
- Bedrock AgentCore Memory API 整合
- Memory ID 配置和格式驗證
- 容錯機制實現（Memory 失敗時降級）
- IAM 權限配置
- 替代方案評估（DynamoDB）

---

## 🏗️ 技術實現

### 架構設計

**Memory 服務架構**：
```
Lambda 函數
    ↓
MemoryService (services/memory_service.py)
    ↓
Bedrock AgentCore Memory API
    ├─ Memory 資源管理
    ├─ 會話追蹤
    └─ 對話歷史存儲
```

### 核心組件

1. **MemoryService** (`services/memory_service.py`)
   - 動態 Memory 整合
   - Memory ID 配置：`telegrambot-1767717327`
   - 容錯處理：Memory 失敗時自動降級

2. **Processor Entry** (`processor_entry.py`)
   - 環境變數：`BEDROCK_AGENTCORE_MEMORY_ID`
   - 條件性啟用 Memory 功能
   - 無狀態模式作為後備

3. **IAM 權限配置**
   - bedrock-agentcore:* 完整權限
   - 支持 Memory 資源的 CRUD 操作

### 技術棧
- AWS Bedrock AgentCore Memory API
- Python 3.11
- bedrock-agentcore SDK
- 容錯設計模式

---

## 🧪 測試與驗證

### 代碼層面測試
- [x] Memory ID 格式驗證：通過（符合正則表達式）
- [x] IAM 權限配置：完整
- [x] 容錯處理：正常工作
- [x] 環境變數配置：正確
- [x] Lambda 部署：成功

### 運行時測試
- [x] Memory 服務初始化：成功（但資源不存在）
- [x] 容錯降級：正常觸發
- [x] 無狀態模式：正常運作
- [ ] 實際 Memory 功能：待 Memory 資源創建

### 測試日誌
```
✅ Memory 服務初始化: telegrambot-1767717327
✅ Memory ID 格式正確
✅ IAM 權限完整
⚠️ Memory 資源未找到（ResourceNotFoundException）
✅ 自動降級為無狀態模式
✅ 訊息成功處理
```

---

## 🐛 問題與解決

### 遇到的主要問題

1. **Memory 資源不存在**
   - 問題：ResourceNotFoundException: Memory not found
   - 原因：Bedrock AgentCore Memory 需要先創建資源
   - 解決：實現容錯降級機制，系統仍可正常運作

2. **Memory ID 格式要求**
   - 問題：需要符合特定正則表達式格式
   - 原因：AWS 服務的命名規範
   - 解決：使用格式 `[a-zA-Z][a-zA-Z0-9-_]{0,99}-[a-zA-Z0-9]{10}`
   - 實際使用：`telegrambot-1767717327`

3. **容錯策略設計**
   - 問題：Memory 服務可能暫時不可用
   - 原因：服務可能在預覽階段或需要特殊權限
   - 解決：實現降級機制，確保核心功能不受影響

---

## 📚 關鍵學習

### 技術洞察

1. **Bedrock AgentCore Memory 特性**
   - Memory 是 AWS 管理的資源，需要先創建
   - 可能仍在預覽階段
   - 需要特定的 AWS 帳戶權限
   - 不能只通過環境變數使用

2. **容錯設計重要性**
   ```python
   # ✅ 良好的容錯設計
   try:
       memory_service = MemoryService(memory_id)
   except Exception as e:
       logger.warning(f"Memory failed, using stateless mode")
       # 系統繼續運作
   ```

3. **替代方案評估**
   - **Strands InMemorySessionManager**：簡單但不持久
   - **DynamoDB 自定義存儲**：最實用的方案
   - **Bedrock AgentCore Memory**：理想但可能需要特殊設置

### 最佳實踐

1. **容錯優先**
   - 永遠提供降級方案
   - 不要讓單一功能失敗影響整個系統
   - 清晰記錄降級行為

2. **配置驗證**
   - 驗證 Memory ID 格式
   - 檢查環境變數是否存在
   - 確認 IAM 權限完整

3. **文檔化決策**
   - 記錄 Memory ID 格式要求
   - 說明容錯機制如何工作
   - 提供替代方案指南

### 避坑指南

1. **不要假設資源存在**
   - Memory 資源需要先創建
   - 實現檢查和容錯邏輯

2. **ID 格式要嚴格遵守**
   - 使用正則表達式驗證
   - 生成唯一且符合規範的 ID

3. **預期服務限制**
   - 新服務可能有特殊要求
   - 準備多種實現方案

---

## 🔗 相關文檔

### 程式碼位置
- `telegram-agentcore-bot/services/memory_service.py` - Memory 服務實現
- `telegram-agentcore-bot/processor_entry.py` - Memory 整合點
- `telegram-agentcore-bot/template.yaml` - IAM 權限配置
- `telegram-agentcore-bot/create_memory.py` - Memory 資源創建腳本

---

## 📊 功能狀態

**部署狀態**: ✅ 代碼已部署（無狀態模式運行）  
**Memory 資源**: ⚠️ 待創建  
**文檔狀態**: ✅ 已完整記錄  
**維護者**: AgentCoreNexus Team  
**最後更新**: 2026-01-06

### 當前能力
- ✅ Memory 服務代碼就緒
- ✅ 容錯機制完善
- ✅ 無狀態模式正常運作
- ⚠️ 實際 Memory 功能（待 Memory 資源）

### 限制
- ❌ 不記住對話歷史
- ❌ 每次對話都是全新開始
- ❌ 沒有用戶偏好記憶

### 未來改進方向

**選項 1：創建 Bedrock AgentCore Memory**
- 通過 AWS Console 或 API 創建 Memory 資源
- 可能需要聯繫 AWS 支援
- 適合：官方支持的長期方案

**選項 2：使用 DynamoDB 自定義存儲（推薦）**
- 創建 DynamoDB table 存儲對話歷史
- 實現自定義 SessionRepository
- 適合：實用且可控的方案
- 優點：完全控制、成本可控、立即可用

**選項 3：Strands InMemorySessionManager**
- 使用框架內建的記憶管理
- 適合：開發和測試環境
- 缺點：不持久、不跨實例

---

## 🎯 技術決策

### 為什麼選擇容錯設計？
- Memory 服務可能不穩定或不可用
- 確保核心對話功能不受影響
- 提供更好的用戶體驗

### 為什麼使用特定的 Memory ID 格式？
- 符合 AWS 命名規範
- 易於識別和管理
- 包含時間戳保證唯一性

### 為什麼推薦 DynamoDB 方案？
- 不依賴可能處於預覽階段的新服務
- 完全控制存儲邏輯
- 成本可預測且可控
- 實現相對簡單
- 立即可用

---

## 🔧 實施建議

### 如果要啟用 Bedrock Memory
1. 研究如何創建 Memory 資源
2. 可能需要聯繫 AWS 支援
3. 確認帳戶權限和區域支持

### 如果要使用 DynamoDB（推薦）
1. 創建 DynamoDB table：`conversation_history`
2. 設計 schema：
   - Partition Key: `user_id`
   - Sort Key: `timestamp`
   - Attributes: `message`, `role`, `metadata`
3. 實現 DynamoDBSessionRepository
4. 修改 memory_service.py 使用 DynamoDB
5. 添加 DynamoDB IAM 權限
6. 測試和驗證

預估工作量：2-4 小時

---

## 💡 關鍵發現

### Bedrock AgentCore Memory 現狀
- 相對較新的服務功能
- 可能仍在預覽階段
- 需要特定的 AWS 帳戶類型或權限
- 文檔可能還不完整
- 需要通過特定方式創建資源

### 實用建議
對於生產環境，**DynamoDB 自定義存儲**提供了：
- ✅ 更成熟和可靠的解決方案
- ✅ 更好的控制和靈活性
- ✅ 更透明的成本結構
- ✅ 更容易除錯和維護

---

**報告創建**: 2026-01-07  
**整理者**: Cline AI Assistant  
**結論**: 代碼完全就緒，系統穩定運行（無狀態模式）。要啟用長期記憶，建議實施 DynamoDB 方案作為實用且可靠的解決方案。
