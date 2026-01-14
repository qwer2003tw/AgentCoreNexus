# .clinerules/ 重構專案

**狀態**: 🔄 進行中  
**開始時間**: 2026-01-14  
**方案**: A - 漸進式重構（不包含 skills 轉換）

## 🎯 目標

將 `.clinerules/` 目錄重構為符合 Cline 官方標準的結構，同時保留運作良好的現有部分。

## 📋 任務清單

### Phase 1: 準備階段
- [x] 創建開發目錄
- [x] 創建 PROGRESS.md

### Phase 2: 創建 Rules 目錄
- [x] 創建 `.clinerules/rules/` 目錄
- [x] 轉換 CODE_QUALITY_WORKFLOW.md → rules/code-quality.md
- [x] 轉換 TESTING_STANDARDS.md → rules/testing-standards.md
- [x] 轉換 PLAN_MODE_METHODOLOGY.md → rules/plan-mode-methodology.md
- [x] 轉換 DOCUMENTATION_WORKFLOW.md → rules/documentation.md

### Phase 3: 創建 Workflows 目錄
- [x] 創建 `.clinerules/workflows/` 目錄
- [x] 編寫 workflows/test-full.md
- [x] 編寫 workflows/deploy-lambda.md
- [x] 編寫 workflows/fix-linting.md
- [x] 編寫 workflows/create-lambda.md
- [x] 編寫 workflows/check-status.md

### Phase 4: 添加 Cline Hooks
- [x] 創建 hooks/PreToolUse（操作前驗證）
- [x] 創建 hooks/TaskStart（任務開始注入）
- [x] 創建 hooks/PostToolUse（操作後監控）
- [x] 創建 hooks/README.md（說明 Git vs Cline hooks）

### Phase 5: 測試驗證（需要用戶參與）
- [ ] 測試 /test-full.md 調用
- [ ] 測試 /deploy-lambda.md 流程
- [ ] 驗證 PreToolUse hook 正確觸發
- [ ] 驗證 TaskStart hook 正確注入
- [ ] 確認 rules 被 AI 讀取

### Phase 6: 文檔更新
- [x] 更新 .clinerules/README.md
- [x] 標記舊文件為 deprecated（4個文件）
- [x] 創建遷移指南（MIGRATION_GUIDE.md）

### Phase 7: 完成報告
- [ ] 創建 dev-reports/2026-01-clinerules-reorg/REPORT.md
- [ ] 清理 dev-in-progress/clinerules-reorg/

## 🎯 重構原則

1. **添加式增強** - 不刪除運作良好的部分
2. **零破壞性** - 新舊並存，可隨時回滾
3. **漸進驗證** - 每個階段都測試
4. **保留精華** - agents/ 和 deployment/ 不動

## 📊 目標結構

```
.clinerules/
├── rules/              # ⭐ 新增：始終活動的準則
├── workflows/          # ⭐ 新增：手動調用的任務
├── hooks/              # ⭐ 擴展：Git + Cline hooks
├── agents/             # ✅ 保留：角色定義
├── deployment/         # ✅ 保留：專案知識
├── README.md           # 📝 更新：說明新結構
└── QUICK_REFERENCE.md  # ✅ 保留：快速參考
```

## 💡 關鍵決策記錄

### 為什麼不轉換 agents/ 為 skills？
- agents/ 運作良好（10+ 角色清晰定義）
- 內容大小適中（不需要按需加載）
- 始終相關（AI 開發工作）
- 風險最小化

### 為什麼採用漸進式？
- 新舊並存，可回滾
- 分階段驗證
- 最小化風險
- 實際測試價值後再決定是否完全遷移

## 📝 開發筆記

[記錄實施過程中的發現和決策]

## ⚠️ 問題與風險

[記錄遇到的問題和解決方案]