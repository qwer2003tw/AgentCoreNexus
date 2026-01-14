# 📋 Cline Rules 目錄

此目錄包含 Cline AI 的行為規則、workflows 和 hooks，定義 AI agents 在此專案中的工作方式。

---

## 📂 目錄結構（v4.0 - 2026-01-14 更新）

```
.clinerules/
├── README.md                      # 本說明文件
│
├── rules/                         # ⭐ 新增：始終活動的準則
│   ├── code-quality.md            #   代碼質量規則（強制）
│   ├── testing-standards.md       #   測試標準（強制）
│   ├── plan-mode-methodology.md   #   Plan Mode 方法論
│   └── documentation.md           #   文檔管理規則
│
├── workflows/                     # ⭐ 新增：手動調用的任務腳本
│   ├── test-full.md              #   /test-full.md - 完整測試
│   ├── deploy-lambda.md          #   /deploy-lambda.md - 部署
│   ├── fix-linting.md            #   /fix-linting.md - 修復質量問題
│   ├── create-lambda.md          #   /create-lambda.md - 創建新函數
│   └── check-status.md           #   /check-status.md - 檢查狀態
│
├── hooks/                         # ⭐ 擴展：Git + Cline Hooks
│   ├── README.md                  #   說明兩種 hooks 的區別
│   ├── pre-commit                 #   Git Hook（commit 時觸發）
│   ├── PreToolUse                 #   Cline Hook（工具執行前）
│   ├── TaskStart                  #   Cline Hook（任務開始時）
│   └── PostToolUse                #   Cline Hook（工具執行後）
│
├── agents/                        # ✅ 保留：角色定義規則
│   ├── engineering/               #   工程開發角色
│   ├── testing/                   #   測試角色
│   └── studio-operations/         #   運維角色
│
├── deployment/                    # ✅ 保留：專案專屬知識
│   ├── aws-lambda-telegram-bot-deployment-issues.md
│   ├── development-and-debugging-guide.md
│   ├── lambda-development-best-practices.md
│   └── telegram-bot-quick-reference.md
│
├── QUICK_REFERENCE.md             # ✅ 保留：快速參考
│
└── [已廢棄的文件]                  # 🟡 觀察期後可刪除
    ├── CODE_QUALITY_WORKFLOW.md
    ├── TESTING_STANDARDS.md
    ├── PLAN_MODE_METHODOLOGY.md
    └── DOCUMENTATION_WORKFLOW.md
```

---

## 🆕 v4.0 更新說明（2026-01-14）

### 新增功能

#### 1. Rules 目錄 ⭐
**用途**：存放始終活動的規則，替代原有的 *_WORKFLOW.md 文件

**包含**：
- `code-quality.md` - 代碼質量規則
- `testing-standards.md` - 測試標準
- `plan-mode-methodology.md` - Plan Mode 方法論
- `documentation.md` - 文檔管理規則

**特點**：
- 添加了 `always_active: true` 標記
- 更清晰的分類
- 符合 Cline 官方標準

---

#### 2. Workflows 目錄 ⭐⭐⭐
**用途**：存放可手動調用的任務腳本

**使用方式**：在 Cline 中輸入 `/workflow-name.md`

**可用 Workflows**：
- `/test-full.md` - 執行完整測試流程（5-8 分鐘）
- `/deploy-lambda.md` - 部署 Lambda 到 AWS（5-10 分鐘）
- `/fix-linting.md` - 快速修復代碼質量問題（1-2 分鐘）
- `/create-lambda.md` - 創建新 Lambda 函數（5-10 分鐘）
- `/check-status.md` - 檢查 AWS 資源狀態（2-3 分鐘）

**優勢**：
- 自動化重複任務
- 一致的執行流程
- 清晰的步驟指導
- 內建錯誤處理

---

#### 3. Cline Hooks 擴展 ⭐⭐
**用途**：在 Cline 工作流關鍵時刻注入邏輯

**新增的 Cline Hooks**：
- `PreToolUse` - 工具執行前驗證（阻止錯誤操作）
- `TaskStart` - 任務開始注入（自動檢測專案）
- `PostToolUse` - 工具執行後學習（監控和建議）

**與 Git Hook 的區別**：
- Git Hook (pre-commit) = 在 git commit 時觸發
- Cline Hooks = 在 Cline 操作時觸發
- 兩者互補，提供多層保護

**詳細說明**：查看 `hooks/README.md`

---

### 保留的結構

#### agents/ 目錄 ✅
**為什麼保留**：
- 運作良好（10+ 專業角色定義清晰）
- 內容適中（不需要按需加載）
- 始終相關（AI 開發任務）
- 風險最小化

**不轉換為 Skills**：
- 官方 Skills 需要按需加載
- agents/ 的內容始終有用
- 保持現狀更穩定

---

#### deployment/ 目錄 ✅
**為什麼保留**：
- 專案專屬的實戰經驗
- 快速查找問題解決方案
- AI agents 優先參考

---

### 廢棄的文件 🟡

以下文件已被 `rules/` 目錄中的新版本替代：

- ~~`CODE_QUALITY_WORKFLOW.md`~~ → `rules/code-quality.md`
- ~~`TESTING_STANDARDS.md`~~ → `rules/testing-standards.md`
- ~~`PLAN_MODE_METHODOLOGY.md`~~ → `rules/plan-mode-methodology.md`
- ~~`DOCUMENTATION_WORKFLOW.md`~~ → `rules/documentation.md`

**處理計劃**：
- 保留 2-4 週觀察期
- 確認新結構運作良好後刪除
- 創建清理報告記錄變更

---

## 📖 使用指南

### 如何使用 Rules
**Rules 始終活動** - AI agents 會自動遵循這些規則。

無需手動調用，只需要將規則文件放在 `rules/` 目錄中即可。

---

### 如何使用 Workflows
**Workflows 需要手動調用** - 使用斜杠命令。

**範例**：
```
用戶: /test-full.md
Cline: 執行完整測試流程...
```

**最佳實踐**：
- 用於重複性任務
- 確保步驟一致性
- 節省時間和精力

---

### 如何使用 Hooks

#### Git Hooks（已有）
**自動觸發** - 在 git commit 時執行。

**安裝**：
```bash
./setup-hooks.sh
```

---

#### Cline Hooks（新增）
**自動觸發** - 在 Cline 操作時執行。

**啟用**：
1. 在 Cline 設置中啟用 Hooks 功能
2. Hooks 會自動被發現和使用
3. 在 Cline UI 的 Hooks 面板中管理

**測試**：
- PreToolUse: 嘗試創建 .ts 文件在 Python 專案
- TaskStart: 開始新任務時自動觸發
- PostToolUse: 修改文件後自動觸發

---

### 如何使用 Agents
**Agents 定義專業角色** - AI 理解不同領域的最佳實踐。

無需手動調用，AI 會根據任務需求參考相應的角色定義。

---

## 🎯 功能對比表

| 功能 | 何時觸發 | 用途 | 是否強制 |
|------|---------|------|---------|
| **Rules** | 始終活動 | 定義行為準則 | 是 |
| **Workflows** | 手動調用 `/file.md` | 自動化任務 | 否 |
| **Cline Hooks** | Cline 操作時 | 驗證和監控 | 部分強制 |
| **Git Hooks** | git commit 時 | 質量檢查 | 是 |
| **Agents** | 始終活動 | 角色定義 | 否 |

---

## 🚀 快速開始

### 新用戶入門

1. **閱讀核心規則**：
   - `.clinerules/rules/code-quality.md`
   - `.clinerules/rules/testing-standards.md`

2. **了解可用 Workflows**：
   - 查看 `.clinerules/workflows/` 目錄
   - 嘗試 `/test-full.md`

3. **啟用 Hooks**：
   - 安裝 Git hooks: `./setup-hooks.sh`
   - 在 Cline 設置中啟用 Cline Hooks

4. **探索 Agents**：
   - 查看 `.clinerules/agents/` 了解可用角色

---

### 常見任務快速參考

```bash
# 執行完整測試
/test-full.md

# 快速修復代碼質量
/fix-linting.md

# 部署到 AWS
/deploy-lambda.md

# 檢查系統狀態
/check-status.md

# 創建新 Lambda
/create-lambda.md
```

---

## 📚 相關文檔

### 核心規範（在 rules/）
- [code-quality.md](./rules/code-quality.md) - 代碼質量規則（⭐ 強制性）
- [testing-standards.md](./rules/testing-standards.md) - 測試標準（⭐ 強制性）
- [plan-mode-methodology.md](./rules/plan-mode-methodology.md) - Plan Mode 方法論
- [documentation.md](./rules/documentation.md) - 文檔管理規則

### 其他文檔
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - 快速參考命令
- [hooks/README.md](./hooks/README.md) - Hooks 詳細說明
- [dev-reports/README.md](../dev-reports/README.md) - 報告使用說明
- [dev-in-progress/README.md](../dev-in-progress/README.md) - 協作開發說明

---

## 🔄 版本歷史

**版本 4.0** (2026-01-14):
- ⭐ 新增 rules/ 目錄（始終活動的準則）
- ⭐ 新增 workflows/ 目錄（手動調用的任務腳本）
- ⭐ 擴展 hooks/ 目錄（添加 Cline hooks）
- ✅ 保留 agents/ 和 deployment/（運作良好）
- 🟡 標記舊文件為 deprecated（觀察期）

**版本 3.0** (2026-01-12):
- 整合 TEST_EXECUTION_WORKFLOW 和 MANDATORY_CHECKLIST
- 創建統一的 TESTING_STANDARDS.md
- 簡化 QUICK_REFERENCE.md
- 消除 43% 重複內容

**版本 2.0** (2026-01-07):
- 初始結構化組織
- 創建 agents/ 子目錄
- 添加 deployment/ 專案知識

---

## ⚠️ 常見錯誤（更新）

### 錯誤 1：混淆 Workflows 和 Rules
**症狀**：將任務腳本放在 rules/ 或將規則放在 workflows/  
**影響**：功能分類混亂  
**解決**：
- Rules = 始終活動的準則
- Workflows = 手動調用的任務

### 錯誤 2：忘記調用 Workflows
**症狀**：手動執行重複的命令序列  
**影響**：浪費時間，容易出錯  
**解決**：使用 `/workflow.md` 自動化任務

### 錯誤 3：禁用 Hooks
**症狀**：關閉 Git hooks 或 Cline hooks  
**影響**：失去質量保護  
**解決**：保持 hooks 啟用，它們是安全網

---

## 🔍 快速檢查清單（更新）

定期檢查 `.clinerules/` 是否健康：

- [ ] rules/ 目錄有 4 個核心規則文件
- [ ] workflows/ 目錄有 5 個任務腳本
- [ ] hooks/ 目錄有 3 個 Cline hooks（可執行）
- [ ] hooks/pre-commit 已安裝（`.git/hooks/pre-commit` 存在）
- [ ] 沒有報告文件（*.REPORT.md 等）
- [ ] 沒有臨時文件（*.draft、*.wip 等）
- [ ] agents/ 和 deployment/ 內容完整

---

## 💡 使用技巧

### 提升效率
1. **善用 Workflows** - 不要手動重複執行命令
2. **信任 Hooks** - 讓它們自動保護代碼質量
3. **參考 Agents** - 了解不同角色的最佳實踐
4. **查閱 Deployment** - 快速解決部署問題

### 維護規範
1. **定期檢查** - 每月檢查目錄健康度
2. **更新文檔** - 發現問題時及時更新
3. **清理臨時** - 不累積不需要的文件
4. **版本控制** - 所有變更都提交到 Git

---

## 🎓 給 AI Agents 的指引

### Rules（必須遵守）
所有 rules/ 中的規則都是**強制性**的，必須始終遵守。

### Workflows（主動使用）
當遇到重複性任務時，**主動建議**用戶使用相關 workflow。

範例：
```
用戶：「幫我測試所有代碼」
AI：「我建議使用 /test-full.md workflow，它會執行完整的測試流程。
     要我執行嗎？」
```

### Hooks（自動觸發）
Hooks 會自動工作，你只需要：
- 遵守 PreToolUse 的阻止決定
- 注意 PostToolUse 的建議
- 利用 TaskStart 注入的上下文

### Agents（參考指導）
根據任務類型參考相應的 agent 定義，但不是強制的。

---

## 📚 參考資源

### Cline 官方文檔
- [Cline Rules](https://docs.cline.bot/features/cline-rules)
- [Workflows](https://docs.cline.bot/features/slash-commands/workflows)
- [Hooks](https://docs.cline.bot/features/hooks)
- [Skills](https://docs.cline.bot/features/skills)（未來可能使用）

### 專案文檔
- [docs/](../docs/) - 面向人類的完整文檔
- [dev-reports/](../dev-reports/) - 功能開發報告歸檔
- [dev-in-progress/](../dev-in-progress/) - 開發中功能

---

## 🎯 設計理念

### 為什麼採用這個結構？

**符合官方標準**：
- rules/, workflows/, hooks/ 是 Cline 官方推薦的結構
- 更容易被其他 Cline 用戶理解
- 利用 Cline 的原生功能

**保留現有優勢**：
- agents/ 運作良好，無需改變
- deployment/ 是寶貴的實戰經驗
- 不破壞已經有效的部分

**漸進式演進**：
- 新舊並存，降低風險
- 逐步驗證新功能價值
- 根據實際使用調整

---

## 🔄 遷移指南

### 從舊結構遷移到新結構

**規則使用者（AI Agents）**：
- 新規則在 `rules/` 目錄
- 內容與舊文件相同，只是位置改變
- 舊文件暫時保留，但優先使用新版本

**Workflow 使用者**：
- 新的任務腳本在 `workflows/` 目錄
- 使用 `/workflow.md` 調用
- 比手動執行命令更方便

**Hook 使用者**：
- Git hooks 保持不變（`./setup-hooks.sh`）
- 新增 Cline hooks 提供額外保護
- 在 Cline 設置中啟用即可

---

## 📊 效果評估

### 預期改進

**效率提升**：
- Workflows 節省重複命令輸入時間
- 一致的執行流程減少錯誤
- 自動化提高生產力

**質量提升**：
- Cline hooks 提供實時驗證
- 多層防護減少錯誤
- 主動建議改善決策

**可維護性**：
- 更清晰的功能分類
- 符合官方標準
- 更容易擴展

### 測量指標

觀察期（2-4 週）後評估：
- [ ] Workflows 使用頻率
- [ ] Cline hooks 攔截的錯誤數
- [ ] 開發效率提升
- [ ] 代碼質量改善

---

**目錄版本**: v4.0  
**最後更新**: 2026-01-14  
**維護者**: AgentCoreNexus Team

**重要提醒**：
- 🆕 使用新的 workflows/ 提升效率
- 🛡️ Cline hooks 提供額外保護
- ✅ 舊功能仍然可用（向後兼容）
- 📊 觀察期後評估並決定是否刪除舊文件