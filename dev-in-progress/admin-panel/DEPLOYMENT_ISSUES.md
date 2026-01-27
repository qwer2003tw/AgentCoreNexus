# Admin Panel 部署問題報告

**日期**: 2026-01-26  
**狀態**: 🔧 需要修復  
**嘗試次數**: 5 次

---

## 🎯 目標

部署 Day 5-6 的 Admin Panel 功能到 AWS。

---

## ❌ 遇到的問題

### 問題序列

**嘗試 1-2**: `No module named 'audit_service'`
- **原因**: shared-services layer 缺少 audit_service.py
- **修復**: 複製 audit_service.py 到 layer，發布 version 3

**嘗試 3**: `cannot import name 'AuditAction' from 'audit_service'`
- **原因**: audit_service.py 沒有導出 AuditAction 類
- **修復**: 在 admin_api.py 中直接使用字符串常量

**嘗試 4**: `No module named 'shared'`
- **原因**: audit_decorator.py 中有 `from shared.services.audit_service import`
- **修復**: 修改為 `from audit_service import`，添加 create_audit_service()

**嘗試 5**: `Syntax error in conversation_service.py, line 315`
- **原因**: Layer 中的 conversation_service.py 是舊版本（320 行 vs 512 行）
- **修復**: 複製最新版本到 layer，發布 version 4

**當前（嘗試 6）**: `AuditService.__init__() got multiple values for argument`
- **原因**: AuditService.__init__() 簽名是 `(audit_table_name, config_table_name)`，不需要 dynamodb 參數
- **修復**: 移除 dynamodb 參數，只傳表名
- **狀態**: 正在部署測試中...

---

## 🔍 根本原因分析

### 核心問題

**Layer 管理混亂**：
- Layer 中的文件版本不一致
- 缺少完整的更新流程
- 沒有驗證 layer 內容的機制

### 具體問題

1. **audit_service.py 缺失**
   - Day 4 創建在 `shared/services/`
   - 忘記同步到 layer

2. **conversation_service.py 版本不一致**
   - `shared/services/`: 512 行（最新）
   - `layer/python/`: 320 行（舊版，有語法錯誤）

3. **導入路徑不匹配**
   - `audit_decorator.py` 使用 `from shared.services...`
   - Lambda 環境沒有 `shared` 模組

4. **API 簽名理解錯誤**
   - 沒有先檢查 AuditService 的 __init__ 簽名
   - 假設需要 dynamodb 參數

---

## ✅ 已完成的修復

### Layer Updates
- ✅ Layer version 3: 添加 audit_service.py
- ✅ Layer version 4: 更新 conversation_service.py（修復語法）
- 📋 Version 5: 待測試（修復 AuditService 初始化）

### Code Fixes
- ✅ admin_api.py: 移除不存在的類導入
- ✅ audit_decorator.py: 修改導入路徑
- ✅ audit_decorator.py: 添加 create_audit_service()
- ✅ admin_api.py: 修復 AuditService 初始化參數

---

## 📋 正確的 Layer 更新流程（學習）

### Step 1: 同步所有服務文件
```bash
cp shared/services/*.py infrastructure/layers/shared-services/python/
```

### Step 2: 驗證語法
```bash
cd infrastructure/layers/shared-services/python
for f in *.py; do
    python3.12 -m py_compile "$f" || echo "❌ $f 有語法錯誤"
done
```

### Step 3: 測試導入
```bash
cd infrastructure/layers/shared-services/python
python3.12 -c "from audit_service import AuditService; print('✅ audit_service OK')"
python3.12 -c "from conversation_service import ConversationService; print('✅ conversation_service OK')"
```

### Step 4: 發布 Layer
```bash
cd infrastructure/layers/shared-services
zip -r layer.zip python/ -q
aws lambda publish-layer-version \
  --layer-name agentcore-shared-services \
  --description "Version X with all services" \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.12 \
  --region us-west-2
```

### Step 5: 更新所有使用 Layer 的 Lambda
```yaml
Layers:
  - arn:aws:lambda:us-west-2:190825685292:layer:agentcore-shared-services:X
```

---

## 🎯 下一步行動

### 如果測試成功
1. ✅ 驗證 admin API 可以正常工作
2. ✅ 檢查審計日誌是否記錄
3. ✅ Git commit 所有修復
4. ✅ 創建部署成功報告
5. ✅ 繼續 Day 7-8（AI 摘要）

### 如果測試失敗
1. 📋 查看最新日誌
2. 📋 識別新錯誤
3. 📋 考慮替代方案：
   - **選項 A**: 簡化 admin_api.py（移除審計裝飾器，只保留核心功能）
   - **選項 B**: 創建獨立的 audit_service 模組在 lambdas/rest/ 中
   - **選項 C**: 重新設計 Layer 結構

---

## 💡 經驗教訓

### 1. Layer 管理最佳實踐
- ✅ 使用自動化腳本同步文件
- ✅ 版本號管理（記錄每個版本包含什麼）
- ✅ 部署前驗證語法和導入

### 2. 依賴管理
- ✅ 明確記錄所有依賴關係
- ✅ 使用環境變數傳遞配置
- ✅ 檢查 API 簽名後再使用

### 3. 快速迭代
- ⚠️ 5 次部署嘗試 = 時間浪費
- ✅ 應該本地模擬 Lambda 環境測試
- ✅ 使用 `sam local invoke` 在部署前驗證

---

## 🔄 改進建議

### 短期（本週）
1. 完成當前部署（修復 AuditService 參數）
2. 如果繼續失敗，考慮簡化方案
3. 完成基礎功能即可（審計可選）

### 長期（下週）
1. 創建 Layer 管理腳本
2. 添加 CI/CD 驗證
3. 本地測試環境設置

---

## 📊 時間追蹤

| 活動 | 用時 |
|------|------|
| Day 5: 開發 | 15 分鐘 |
| Day 6: API 整合 | 13 分鐘 |
| 部署嘗試 1-5 | 30+ 分鐘 |
| **總計** | ~60 分鐘 |

**本應用時**: ~30 分鐘（如果 layer 正確）  
**實際用時**: ~60 分鐘（多花 100%）

---

## 📝 當前部署狀態

**最後一次嘗試**（#6）：
- Template: layer version 4
- admin_api.py: AuditService 不傳 dynamodb
- audit_decorator.py: 修復導入
- **狀態**: 正在部署...

**測試命令**（部署完成後）:
```bash
cd web-adapter/scripts
ADMIN_PASSWORD="Admin123!" ./test_admin_api.sh
```

**預期結果**:
- ✅ Login: Success
- ✅ List conversations: 有數據或空（取決於是否有對話）
- ✅ 無 "Internal server error"

---

**報告創建時間**: 2026-01-26 18:03  
**下次繼續**: 檢查背景任務結果，決定下一步