# .clinerules/ 遷移指南

本指南幫助您從舊結構遷移到新的 Cline 官方標準結構。

---

## 🎯 什麼改變了？

### 新增的目錄（v4.0）

#### 1. `rules/` - 始終活動的規則 ⭐
**取代**：根目錄的 *_WORKFLOW.md 文件

**遷移對應**：
- `CODE_QUALITY_WORKFLOW.md` → `rules/code-quality.md`
- `TESTING_STANDARDS.md` → `rules/testing-standards.md`
- `PLAN_MODE_METHODOLOGY.md` → `rules/plan-mode-methodology.md`
- `DOCUMENTATION_WORKFLOW.md` → `rules/documentation.md`

**變化**：
- 添加了 `always_active: true` 標記
- 標題改為「Rules」格式
- 內容保持不變

---

#### 2. `workflows/` - 手動調用的任務 ⭐⭐⭐
**全新功能**：之前沒有對應的部分

**包含的 Workflows**：
- `test-full.md` - 完整測試流程
- `deploy-lambda.md` - Lambda 部署
- `fix-linting.md` - 修復 linting
- `create-lambda.md` - 創建新 Lambda
- `check-status.md` - 檢查部署狀態

**使用方式**：在 Cline 中輸入 `/workflow.md`

**範例**：
```
用戶: /test-full.md
Cline: 執行完整測試流程...
```

---

#### 3. Cline Hooks - 工作流鉤子 ⭐⭐
**擴展**：原有 Git hook (pre-commit)，新增 Cline hooks

**新增的 Cline Hooks**：
- `PreToolUse` - 工具執行前驗證
- `TaskStart` - 任務開始注入
- `PostToolUse` - 工具執行後學習

**與 Git Hook 的區別**：
- Git Hook: 在 git commit 時觸發
- Cline Hooks: 在 Cline 操作時觸發
- 互補而非替代

---

### 保留的目錄

#### `agents/` ✅
**不變**：10+ 專業角色定義保持原樣

**為什麼不轉為 Skills**：
- 運作良好
- 內容適中
- 始終相關
- 風險最小

---

#### `deployment/` ✅
**不變**：專案專屬知識保持原樣

**為什麼保留**：
- 實戰經驗寶貴
- 快速問題查找
- AI 優先參考

---

## 📖 如何使用新結構

### 1. 使用 Rules（自動）

**Rules 始終活動** - 無需任何操作，AI 自動遵循。

**位置**：`.clinerules/rules/`

**何時參考**：
- AI 在任何時候都會遵守這些規則
- 定義了強制性的行為準則

---

### 2. 使用 Workflows（手動）

**Workflows 需要手動調用** - 使用斜杠命令。

**調用方式**：
```
在 Cline 聊天中輸入：/workflow-name.md
```

**範例**：
```
# 執行測試
/test-full.md

# 部署
/deploy-lambda.md

# 修復 linting
/fix-linting.md

# 檢查狀態
/check-status.md

# 創建新 Lambda
/create-lambda.md
```

**優勢**：
- 自動化重複任務
- 步驟一致性
- 錯誤處理完善
- 節省時間

---

### 3. 使用 Cline Hooks（自動）

**Cline Hooks 自動觸發** - 在 Cline 操作時執行。

**啟用方式**：
1. 在 Cline 設置中啟用 Hooks 功能
2. Hooks 自動被發現
3. 在 Cline UI 管理

**測試 Hooks**：
- **PreToolUse**: 嘗試在 Python 專案創建 .ts 文件（會被阻止）
- **TaskStart**: 開始新任務（自動注入專案信息）
- **PostToolUse**: 修改 Python 文件（自動提醒測試）

**查看狀態**：
- Cline UI → Hooks 面板
- 查看執行記錄和狀態

---

### 4. 使用 Agents（參考）

**Agents 保持不變** - 繼續按原方式使用。

**無需任何改變** - AI 會根據任務參考相應角色。

---

## 🔄 遷移步驟（用戶視角）

### 步驟 1: 了解新結構（5 分鐘）

閱讀：
- `.clinerules/README.md` - 總覽
- `.clinerules/hooks/README.md` - Hooks 說明

---

### 步驟 2: 啟用 Cline Hooks（2 分鐘）

1. 打開 Cline 設置
2. 啟用 Hooks 功能
3. 打開 Hooks 面板驗證

---

### 步驟 3: 試用 Workflows（5 分鐘）

嘗試執行：
```
/test-full.md
```

觀察 Cline 如何執行步驟化的測試流程。

---

### 步驟 4: 觀察 Hooks 運作（10 分鐘）

**測試 PreToolUse**：
```
用戶: "在 telegram-lambda 創建一個 test.ts 文件"
預期: Hook 阻止此操作，顯示錯誤訊息
```

**測試 TaskStart**：
```
開始新任務 → 自動注入專案信息
查看 Cline 的回應中是否包含 PROJECT: AgentCoreNexus...
```

**測試 PostToolUse**：
```
修改任何 .py 文件 → 自動提醒測試
查看是否有 REMINDER: 已修改 Python 文件...
```

---

### 步驟 5: 繼續正常工作（無感知）

新結構是**添加式增強**：
- ✅ 所有舊功能仍然有效
- ✅ Rules 自動生效
- ✅ 可以選擇使用 Workflows
- ✅ Hooks 在背景保護

---

## 📊 新舊對比

| 功能 | 舊方式 | 新方式 | 改進 |
|------|--------|--------|------|
| 強制規範 | *_WORKFLOW.md | rules/*.md | 更清晰 ✅ |
| 任務自動化 | 手動命令 | workflows/*.md | 新功能 ⭐ |
| 質量控制 | Git hooks | Git + Cline hooks | 雙重保護 ⭐ |
| 角色定義 | agents/*.md | 保持不變 | 無需學習 ✅ |

---

## ⚡ 快速參考卡

### 我應該用哪個？

**想執行測試**：
```
/test-full.md
```

**想部署到 AWS**：
```
/deploy-lambda.md
```

**想快速修復 linting**：
```
/fix-linting.md
```

**想檢查系統狀態**：
```
/check-status.md
```

**想創建新 Lambda**：
```
/create-lambda.md
```

---

## 🤔 常見問題

### Q1: 舊文件還能用嗎？
**A**: 可以！舊文件被標記為 deprecated 但仍然存在。不過建議使用新版本。

### Q2: 我需要做什麼嗎？
**A**: 不需要！Rules 自動生效。Workflows 是可選的，用了會更方便。

### Q3: Cline Hooks 會影響我的工作嗎？
**A**: 不會！它們只是提供建議和保護。PreToolUse 可能阻止明顯錯誤的操作。

### Q4: agents/ 怎麼辦？
**A**: 完全不變！繼續正常使用。

### Q5: 什麼時候刪除舊文件？
**A**: 2-4 週觀察期後，確認新結構運作良好。

---

## 💡 使用技巧

### 提升效率
1. **記住常用 Workflows**：
   - `/test-full.md` - 最常用
   - `/deploy-lambda.md` - 部署時
   - `/fix-linting.md` - 快速修復

2. **信任 Hooks**：
   - PreToolUse 阻止錯誤 = 好事
   - PostToolUse 提醒 = 有用的建議
   - TaskStart 注入 = 自動上下文

3. **探索 Workflows**：
   - 查看 `.clinerules/workflows/` 
   - 了解每個 workflow 的用途
   - 根據需求調用

---

## 🎯 成功指標

觀察期（2-4 週）後評估：

### 效率指標
- [ ] Workflows 使用頻率 > 5 次/週
- [ ] 重複命令輸入減少 > 50%
- [ ] 任務執行時間縮短 > 30%

### 質量指標
- [ ] Cline hooks 攔截錯誤 > 3 次
- [ ] 代碼質量問題減少
- [ ] 測試遺漏減少

### 滿意度
- [ ] 使用者感覺更方便
- [ ] AI 行為更一致
- [ ] 文檔結構更清晰

---

## 📞 需要幫助？

### 問題排查

**Workflows 無法調用**：
- 確認文件在 `.clinerules/workflows/`
- 確認文件名以 `.md` 結尾
- 使用 `/` 開頭調用

**Cline Hooks 不生效**：
- 檢查 Cline 設置是否啟用 Hooks
- 確認 hooks 文件有執行權限（`chmod +x`）
- 查看 Cline Hooks 面板的狀態

**找不到新的 Rules**：
- Rules 自動生效，無需手動操作
- 舊的 *_WORKFLOW.md 仍然存在（觀察期）
- 新的 rules/*.md 優先級更高

---

## 📚 更多資源

### Cline 官方文檔
- [Rules](https://docs.cline.bot/features/cline-rules)
- [Workflows](https://docs.cline.bot/features/slash-commands/workflows)
- [Hooks](https://docs.cline.bot/features/hooks)

### 專案文檔
- `.clinerules/README.md` - 目錄總覽
- `.clinerules/hooks/README.md` - Hooks 詳細說明
- `dev-in-progress/clinerules-reorg/PROGRESS.md` - 重構進度

---

**遷移指南版本**: v1.0  
**創建日期**: 2026-01-14  
**適用範圍**: 所有 AgentCoreNexus 用戶和貢獻者

**記住**：這是**添加式增強**，不是破壞性改變！所有舊功能仍然可用。