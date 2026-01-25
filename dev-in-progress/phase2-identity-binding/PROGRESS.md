# Phase 2: 跨通道身份綁定

**狀態**: 🔄 進行中  
**開始時間**: 2026-01-25  
**預計完成**: 2026-01-30 到 2026-02-02（5-8天）  
**負責**: AI Agent

---

## 🎯 目標

實作跨通道身份綁定功能，讓用戶能夠：
1. 在 Telegram 生成綁定碼
2. 在 Web 介面輸入綁定碼完成綁定
3. 綁定後共享 unified conversation_id
4. 查看和管理已綁定的身份

---

## 📋 任務清單

### Day 1: 設計和基礎設施 ✅
- [x] 創建 dev-in-progress 目錄和 PROGRESS.md
- [x] 設計綁定流程（綁定碼機制）
- [x] 創建 binding_codes DynamoDB 表（SAM template）
- [x] 實作 IdentityService 骨架
- [x] 實作 generate_binding_code() 和 verify_and_bind()

### Day 2-3: Telegram 命令整合
- [ ] 實作 /bind 命令（生成綁定碼）
- [ ] 實作 /mybindings 命令（查看已綁定身份）
- [ ] 實作 /unbind 命令（解除綁定）
- [ ] 添加命令測試

### Day 4-5: Web API 整合
- [ ] 實作 POST /bind 端點（Web 綁定 API）
- [ ] 實作 GET /bindings 端點（查詢綁定狀態）
- [ ] 實作 DELETE /bindings/{identity_id} 端點（解除綁定）
- [ ] 添加 API 測試

### Day 6-7: 整合測試和部署
- [ ] 單元測試（IdentityService）
- [ ] 整合測試（Telegram + Web）
- [ ] E2E 測試（完整綁定流程）
- [ ] 部署到 AWS
- [ ] 實際驗證功能

### Day 8: 文檔和清理
- [ ] 創建使用文檔（docs/identity-binding.md）
- [ ] 更新 API 文檔
- [ ] 創建 Phase 2 報告
- [ ] 清理 dev-in-progress

---

## 🏗️ 架構設計

### 綁定碼機制
```
1. 用戶在 Telegram 執行 /bind
2. 系統生成 6 位數字碼（有效期 10 分鐘）
3. 用戶在 Web 輸入綁定碼
4. 系統驗證碼並創建 unified:{uuid}
5. 更新 identity_map 表
```

### DynamoDB Schema: binding_codes
```
PK: code (String, 6位數字)
SK: - (固定 "CODE")
Attributes:
  - telegram_user_id (String)
  - created_at (Number, timestamp)
  - expires_at (Number, timestamp)
  - used (Boolean)
  - ttl (Number, 自動刪除)
```

### IdentityService Methods
```python
class IdentityService:
    def generate_binding_code(telegram_user_id: str) -> str
    def verify_and_bind(code: str, web_user_id: str) -> dict
    def get_bindings(identity_id: str) -> list
    def unbind(identity_id: str, target_id: str) -> bool
    def get_unified_conversation_id(identity_id: str) -> str
```

---

## 📝 開發筆記

### 2026-01-25
- ✅ 創建 Phase 2 開發目錄
- ✅ 設計完成綁定流程（6位數字碼，10分鐘過期）
- ✅ 創建 binding_codes DynamoDB 表定義（infrastructure/binding-codes-table.yaml）
- ✅ 實作 IdentityService（shared/services/identity_service.py）
  - generate_binding_code(): 生成綁定碼
  - verify_and_bind(): 驗證並綁定身份
  - get_bindings(): 查詢已綁定身份
  - unbind(): 解除綁定
  - get_unified_conversation_id(): 獲取統一對話 ID
- ✅ 創建單元測試（shared/services/test_identity_service.py）
  - 15+ 測試案例覆蓋所有核心功能
  - Mock DynamoDB 測試（使用 moto）
  - 測試邊界條件和錯誤處理

---

## ⚠️ 問題與風險

### 已知風險
1. **綁定碼安全性**: 6 位數字可能被暴力破解
   - 緩解：10 分鐘過期 + 一次性使用 + rate limiting
2. **併發綁定**: 多個用戶同時使用相同綁定碼
   - 緩解：DynamoDB conditional write
3. **綁定後資料遷移**: unified conversation_id 建立後的歷史對話
   - 決策：Phase 2 只處理新訊息，Phase 4 提供 UI 選項遷移歷史

---

## 🎓 學習與決策

### 技術決策
1. **綁定碼格式**: 6 位數字（易輸入）vs UUID（更安全）
   - 選擇：6 位數字，因為用戶體驗優先，安全性用過期和一次性解決
2. **綁定碼儲存**: DynamoDB vs Redis
   - 選擇：DynamoDB with TTL，符合現有架構
3. **unified_conversation_id 格式**: unified:{uuid} vs unified:{hash}
   - 選擇：UUID，保證全域唯一性

---

## 📊 進度追蹤

- **總進度**: 1/8 天完成（12.5%）
- **當前階段**: Day 1 完成 ✅
- **下一步**: Day 2 - Telegram 命令整合（實作 /bind, /mybindings, /unbind）

## 🎉 Day 1 完成總結

已完成：
1. ✅ 綁定流程設計（6位數字碼機制）
2. ✅ DynamoDB binding_codes 表定義
3. ✅ IdentityService 完整實作（5個主要方法）
4. ✅ 15+ 單元測試（涵蓋所有功能和邊界條件）

下一步（Day 2-3）：
1. 實作 Telegram /bind 命令
2. 實作 /mybindings 命令
3. 實作 /unbind 命令
4. 添加命令測試
