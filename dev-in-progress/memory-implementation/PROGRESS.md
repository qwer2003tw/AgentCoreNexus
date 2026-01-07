# Feature: Bedrock AgentCore Memory 長期記憶實作

**狀態**: 🔄 調查完成，等待確認  
**開始時間**: 2026-01-07  
**負責 Agent**: Cline

---

## 📋 任務清單

### Phase 1: 調查與規劃 ✅
- [x] 透過 MCP 查詢 AWS Bedrock AgentCore Memory 文檔
- [x] 理解短期記憶（Short-term Memory）vs 長期記憶（Long-term Memory）
- [x] 確認 Memory Strategies 的運作方式
- [x] 研究 Memory 創建方法（Starter Toolkit + Python API）
- [x] 規劃符合需求的架構（短期 session + 長期記憶）
- [x] 創建完整的調查報告

### Phase 2: Memory 資源創建（待開始）
- [ ] 安裝 bedrock-agentcore-starter-toolkit
- [ ] 使用 Python 創建 Memory 資源
- [ ] 配置 3 種 Memory Strategies：
  - [ ] UserPreferencesStrategy（用戶偏好）
  - [ ] SemanticStrategy（事實資訊）
  - [ ] SessionSummariesStrategy（對話摘要）
- [ ] 驗證 Memory 創建成功
- [ ] 記錄實際的 Memory ID

### Phase 3: 代碼整合（待開始）
- [ ] 更新 Lambda 環境變數（使用真實 Memory ID）
- [ ] 修改 processor_entry.py 支援動態 session
- [ ] 實現 session ID 生成邏輯
- [ ] 測試 Memory 整合

### Phase 4: /new 命令實現（待開始）
- [ ] 創建 new_handler.py
- [ ] 實現 session ID 生成
- [ ] 整合到命令路由器
- [ ] 添加用戶友好的回應訊息
- [ ] 測試 /new 命令

### Phase 5: 測試與驗證（待開始）
- [ ] 測試長期記憶（跨 session）
- [ ] 測試短期記憶（session 內）
- [ ] 測試 /new 命令功能
- [ ] 驗證記憶提取是否正常
- [ ] 性能測試

---

## 🎯 目標

### 用戶需求
1. 用 `/new` 開始新的短期記憶 session
2. 在全部對話中自動記憶長期資訊
3. 無需用戶手動管理記憶

### 技術目標
- 短期記憶：當前 session 的對話歷史
- 長期記憶：用戶資訊、偏好、過往摘要
- /new 命令：清空短期，保留長期

---

## 🔍 關鍵發現

### 1. Bedrock AgentCore Memory 完全符合需求
- **短期記憶**：以 events 形式儲存當前 session 對話
- **長期記憶**：自動從對話提取關鍵資訊（非同步）
- **Session 隔離**：原生支援多個 session，互不干擾
- **跨 session**：長期記憶在所有 session 之間共享

### 2. Memory Strategies 提供智能提取
- `UserPreferencesStrategy`：自動識別用戶偏好
- `SemanticStrategy`：自動提取事實資訊
- `SessionSummariesStrategy`：自動生成對話摘要

### 3. 當前代碼已完全準備好
- `memory_service.py`：完整實現
- `processor_entry.py`：已修改支援動態 Agent 建立
- `template.yaml`：IAM 權限完整
- **只差**：創建實際的 Memory 資源

### 4. Memory ID 格式要求
- 格式：`[字母開頭][字母數字-_最多99個]-[10個字母數字]`
- 我們的 `telegrambot-1767717327` ✅ 格式正確
- 但需要先創建資源才能使用

---

## 🤝 待確認問題

### 技術問題
1. **AWS 權限**：帳戶是否能創建 Bedrock AgentCore Memory？
2. **Starter Toolkit**：是否需要在本地安裝，還是在 Lambda 中？
3. **Memory ID 產生**：創建後會獲得實際 ID，需要更新到 Lambda

### 設計問題
1. **Session 策略**：
   - 每日自動新 session？
   - 完全由用戶控制（只有 /new 才新建）？
   - 智能判斷（超時自動新建）？

2. **長期記憶範圍**：
   - 用戶基本資訊 ✅
   - 用戶偏好 ✅
   - Session 摘要 ✅
   - 特定領域知識？
   - 其他？

3. **Session 存儲**：
   - 需要在 DynamoDB 存儲當前 session_id 嗎？
   - 還是每次都生成新的？

---

## 📝 下一步

### 立即行動（需要用戶確認）
1. 確認上述問題的答案
2. 測試 Memory 創建權限
3. 執行 Memory 創建腳本

### 後續實作（確認後進行）
1. 整合真實的 Memory ID
2. 實現 /new 命令
3. 測試完整功能
4. 創建使用文檔

---

**目前狀態**: ✅ 調查完成，等待用戶確認需求細節  
**預估完成時間**: 確認後 90 分鐘可完成所有實作
