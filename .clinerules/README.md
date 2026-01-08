# 📋 Cline Rules 目錄

此目錄包含 Cline AI 的行為規則和工作流規範，定義 AI agents 在此專案中的工作方式。

---

## 📂 目錄結構

```
.clinerules/
├── README.md                      # 本說明文件
├── DOCUMENTATION_WORKFLOW.md      # 文檔管理規範
├── PLAN_MODE_METHODOLOGY.md       # Plan Mode 工作方法論
├── CODE_QUALITY_WORKFLOW.md       # 代碼質量檢查工作流（強制）⭐
├── TEST_EXECUTION_WORKFLOW.md     # 測試執行工作流（強制）⭐
│
├── deployment/                    # 專案部署文檔（專案專屬知識）
│   ├── aws-lambda-telegram-bot-deployment-issues.md
│   ├── development-and-debugging-guide.md
│   ├── lambda-development-best-practices.md
│   └── telegram-bot-quick-reference.md
│
└── agents/                        # Agent 行為規則（通用能力）
    ├── engineering/               # 工程開發規則
    │   ├── ai-engineer.md
    │   ├── backend-architect.md
    │   ├── devops-automator.md
    │   ├── frontend-developer.md
    │   ├── mobile-app-builder.md
    │   └── test-writer-fixer.md
    │
    ├── testing/                   # 測試規則
    │   ├── api-tester.md
    │   ├── performance-benchmarker.md
    │   └── test-results-analyzer.md
    │
    └── studio-operations/         # 運維規則
        └── infrastructure-maintainer.md
```

---

## ✅ 應該放在這裡的內容

### 1. Agent 規則文件（agents/*/）
- **用途**：定義 AI agents 的專業能力和行為模式
- **格式**：Markdown 文件（.md）
- **分類**：engineering、testing、studio-operations
- **例如**：ai-engineer.md、backend-architect.md

### 2. 工作流規範文件
- **用途**：定義專案的工作流程和協作規範
- **例如**：
  - `DOCUMENTATION_WORKFLOW.md` - 文檔管理工作流
  - `CODE_QUALITY_WORKFLOW.md` - 代碼質量檢查工作流（⭐ 強制性）
  - `PLAN_MODE_METHODOLOGY.md` - Plan Mode 方法論
- **特點**：適用於所有 agents 的通用規範

### 3. 專案專屬知識（deployment/）
- **用途**：記錄此專案的部署經驗和除錯知識
- **例如**：部署問題清單、快速參考指南
- **特點**：與專案緊密相關，不可移動

---

## 🚫 不應該放在這裡的內容

### ❌ 報告文件
- **錯誤**：在此放置清理報告、完成報告等
- **正確**：所有報告應該放在 `dev-reports/`
- **原因**：報告是「開發成果」，不是「規則定義」

### ❌ 開發文件
- **錯誤**：在此放置開發筆記、設計草稿等
- **正確**：開發中文件應該放在 `dev-in-progress/`
- **原因**：這些是臨時文件，不是長期規則

### ❌ 臨時文檔
- **錯誤**：在此放置說明文檔、完成確認等
- **正確**：完成後應該刪除或移至適當位置
- **原因**：避免累積不必要的文件

---

## 🔄 管理 .clinerules 的正確工作流

當需要清理或更新 .clinerules 時，應該遵循標準的開發工作流：

### Phase 1: 開始任務
```bash
# 1. 創建開發目錄
mkdir -p dev-in-progress/clinerules-cleanup

# 2. 創建進度追蹤
# 在 dev-in-progress/clinerules-cleanup/ 創建 PROGRESS.md

# 3. 記錄清理過程和決策
```

### Phase 2: 執行清理
```bash
# 在 .clinerules/ 中執行清理操作
# 記錄所有改動和決策理由
```

### Phase 3: 完成報告
```bash
# 1. 創建報告目錄
mkdir -p dev-reports/YYYY-MM-clinerules-cleanup

# 2. 撰寫綜合報告
# 使用 dev-reports/TEMPLATE.md

# 3. 移動報告到 dev-reports/
mv report.md dev-reports/YYYY-MM-clinerules-cleanup/REPORT.md

# 4. 清理開發文件
rm -rf dev-in-progress/clinerules-cleanup
```

**重要**：**不要**在 `.clinerules/` 放置報告文件！

---

## 📚 規則文件的管理

### 添加新規則
1. 在適當的子目錄創建 .md 文件
2. 遵循現有規則的格式和風格
3. 提交到 Git 進行版本控制

### 移除舊規則
1. 記錄移除原因（在開發文件中）
2. 執行刪除操作
3. 在完成報告中說明移除決策

### 更新現有規則
1. 記錄更新原因和內容
2. 修改規則文件
3. 在完成報告中記錄變更

---

## 🎯 目錄設計理念

### 為什麼 deployment/ 在 .clinerules 而不是 docs？

**原因**：
1. **專案專屬性**：這些文檔是針對此專案的實戰經驗
2. **AI 優先使用**：AI agents 在工作時優先參考這些文檔
3. **快速迭代**：部署經驗會頻繁更新，與規則一起管理更方便

**與 docs/ 的區別**：
- `docs/` → 面向人類的文檔（架構指南、API 文檔）
- `.clinerules/deployment/` → 面向 AI 的知識（問題解決、快速參考）

---

## 📖 相關文檔

### 核心規範
- [DOCUMENTATION_WORKFLOW.md](./DOCUMENTATION_WORKFLOW.md) - 文檔管理工作流規範
- [CODE_QUALITY_WORKFLOW.md](./CODE_QUALITY_WORKFLOW.md) - 代碼質量檢查工作流（⭐ 強制性）
- [PLAN_MODE_METHODOLOGY.md](./PLAN_MODE_METHODOLOGY.md) - Plan Mode 方法論
- [dev-reports/README.md](../dev-reports/README.md) - 報告使用說明
- [dev-in-progress/README.md](../dev-in-progress/README.md) - 協作開發說明

### 範例
- 查看 `agents/` 子目錄中的任何規則文件，了解規則的格式
- 查看 `deployment/` 中的文檔，了解專案專屬知識的記錄方式

---

## ⚠️ 常見錯誤

### 錯誤 1：在此放置報告
**症狀**：創建了 CLEANUP_REPORT.md、COMPLETION_REPORT.md 等  
**影響**：干擾規則查找，違反文檔管理規範  
**解決**：將報告移至 `dev-reports/`

### 錯誤 2：累積臨時文件
**症狀**：有 .draft、.wip、臨時說明等文件  
**影響**：目錄混亂，難以維護  
**解決**：定期清理臨時文件

### 錯誤 3：規則過度細分
**症狀**：創建過多過細的規則文件  
**影響**：增加認知負擔，難以維護  
**解決**：合併相似規則，保持適度抽象

---

## 🔍 快速檢查清單

定期檢查 `.clinerules/` 是否健康：

- [ ] 只包含規則文件和工作流文檔
- [ ] 沒有報告文件（*.REPORT.md 等）
- [ ] 沒有臨時文件（*.draft、*.wip 等）
- [ ] 規則文件都有明確的用途
- [ ] deployment/ 中的文檔是最新的

---

**目錄版本**: v2.0  
**最後更新**: 2026-01-07  
**維護者**: AgentCoreNexus Team

**重要提醒**：此目錄是 AI agents 的「工作手冊」，保持整潔和聚焦至關重要！