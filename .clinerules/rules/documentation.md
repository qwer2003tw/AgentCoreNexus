---
name: documentation
description: 文檔管理規則，定義開發文件的生命週期和協作規範
priority: high
enforcement: strict
always_active: true
---

# Documentation Management Rules

**這是始終活動的規則** - 所有 Cline agents 必須遵循這些文檔管理規範。

此規範定義了 AgentCoreNexus 專案的文檔管理工作流程，確保所有 agents 遵循一致的文檔撰寫和整理標準。

---

## 🎯 核心原則

### 1. 功能導向的文檔管理
- **開發中**：文件保留在 `dev-in-progress/`（進入 Git）
- **完成後**：整合為綜合報告並移至 `dev-reports/`
- **清理**：開發文件在報告創建後立即刪除

### 2. 多平台 Agents 協作
- 所有開發文件進入 Git 版本控制
- 使用清晰的進度追蹤（PROGRESS.md）
- 支持跨平台同步和接力開發

### 3. 文檔生命週期
```
開發開始 → dev-in-progress/ (保留所有開發文件)
    ↓
功能完成 → dev-reports/ (創建綜合報告)
    ↓
清理 → 刪除 dev-in-progress/ 中的功能文件
```

---

## 📂 目錄結構規範

### 強制目錄結構
```
AgentCoreNexus/
├── docs/                      # 核心文檔（永久保留）
│   ├── README.md              # 文檔索引
│   ├── architecture-guide.md  # 系統架構
│   ├── deployment-guide.md    # 部署指南
│   └── ...                    # 其他核心文檔
│
├── dev-reports/               # 功能報告歸檔（Git 追蹤）
│   ├── README.md              # 使用說明
│   ├── TEMPLATE.md            # 報告模板
│   └── YYYY-MM-feature-name/  # 功能報告目錄
│       └── REPORT.md          # 綜合報告
│
├── dev-in-progress/           # 開發中功能（Git 追蹤）
│   ├── README.md              # 協作說明
│   ├── .gitkeep               # 保持目錄存在
│   └── feature-name/          # 開發中功能目錄
│       ├── PROGRESS.md        # 進度追蹤（必須）
│       ├── notes.md           # 開發筆記
│       ├── design.md          # 設計文檔
│       └── test-results.md    # 測試記錄
│
├── telegram-agentcore-bot/    # 代碼組件
├── telegram-lambda/           # 代碼組件
└── .gitignore                 # Git 配置
```

---

## 📁 .clinerules/ 目錄管理規範

### 允許的內容

✅ **規則文件**（rules/、agents/）
- rules/*.md - 始終活動的規則
- agents/*/*.md - 角色定義規則
- workflows/*.md - 任務腳本

✅ **工作流文檔**
- README.md - 目錄說明
- QUICK_REFERENCE.md - 快速參考

✅ **專案專屬知識**（deployment/）
- 部署問題清單
- 開發與除錯指南
- 快速參考文檔

### 不允許的內容

❌ **報告文件**
- 任何 *REPORT.md 或清理報告
- 應該放在 dev-reports/

❌ **臨時文檔**
- 說明文檔、完成確認等
- 完成後應該刪除或移至 dev-reports/

❌ **開發文件**
- 草稿、筆記等
- 應該放在 dev-in-progress/

### 清理 .clinerules 的工作流

**重要**：清理 .clinerules 也是一個「任務」，必須遵循標準工作流！

1. **Phase 1**: 在 dev-in-progress/ 創建 clinerules-cleanup/
2. **Phase 2**: 記錄清理過程和決策（PROGRESS.md）
3. **Phase 3**: 完成後在 dev-reports/ 創建報告
4. **Phase 4**: 清理 dev-in-progress/clinerules-cleanup/

**錯誤示例**：
```bash
# ❌ 錯誤：直接在 .clinerules/ 放置報告
.clinerules/CLEANUP_REPORT.md

# ✅ 正確：報告放在 dev-reports/
dev-reports/2026-01-clinerules-cleanup/REPORT.md
```

---

## 🔄 功能開發工作流

### Phase 1: 開始新功能

**創建開發目錄**：
```bash
mkdir -p dev-in-progress/feature-name
cd dev-in-progress/feature-name
```

**創建 PROGRESS.md**（必須）：
```markdown
# Feature: [功能名稱]
**狀態**: 🔄 進行中  
**開始時間**: YYYY-MM-DD  
**負責 Agent**: [Agent ID/平台]

## 📋 任務清單
- [ ] 任務 1
- [ ] 任務 2
- [ ] 任務 3

## 🎯 目標
[描述功能的目標和要解決的問題]

## 📝 開發筆記
[記錄關鍵決策和想法]

## ⚠️ 問題與風險
[記錄遇到的問題]
```

**提交到 Git**：
```bash
git add .
git commit -m "feat: start [feature-name] development"
git push
```

### Phase 2: 協作開發

**其他 Agent 接手**：
```bash
# 1. 同步最新狀態
git pull

# 2. 查看進度
cat dev-in-progress/feature-name/PROGRESS.md

# 3. 繼續開發
# ... 進行開發工作 ...

# 4. 更新進度
# 編輯 PROGRESS.md，標記完成的任務為 [x]

# 5. 提交更新
git add .
git commit -m "feat([feature-name]): [具體改動]"
git push
```

**開發文件建議**：
- `notes.md` - 開發筆記和技術細節
- `design.md` - 架構設計和 API 設計
- `test-results.md` - 測試執行記錄
- `issues.md` - 問題追蹤清單
- `decisions.md` - 技術決策記錄

### Phase 3: 功能完成

**創建綜合報告**：
```bash
# 1. 創建報告目錄
mkdir -p dev-reports/YYYY-MM-feature-name

# 2. 複製模板
cp dev-reports/TEMPLATE.md dev-reports/YYYY-MM-feature-name/REPORT.md

# 3. 撰寫報告
# 整合 dev-in-progress/feature-name/ 中所有文件的關鍵信息
# 編輯 REPORT.md
```

**報告必須包含**：
- ✅ 功能概述（目標和範圍）
- ✅ 技術實現（架構和組件）
- ✅ 測試與驗證
- ✅ 問題與解決（詳細記錄）
- ✅ 關鍵學習（洞察和最佳實踐）
- ✅ 技術決策（為什麼選擇某方案）

**清理開發文件**：
```bash
# 刪除開發文件
rm -rf dev-in-progress/feature-name

# 提交報告
git add .
git commit -m "docs: complete [feature-name] report and cleanup"
git push
```

---

## 📝 報告撰寫標準

### 報告結構（使用 TEMPLATE.md）

#### 1. 功能概述
- 目標：要解決什麼問題？
- 範圍：實現了什麼？不包含什麼？

#### 2. 技術實現
- 架構設計：用圖表或文字說明
- 核心組件：列出關鍵文件和功能
- 技術棧：使用的技術和工具

#### 3. 測試與驗證
- 測試結果：列出測試通過情況
- 實際日誌：貼上關鍵的測試輸出
- 性能指標：記錄具體數值

#### 4. 問題與解決
**格式**：
```markdown
1. **[問題標題]**
   - 問題：[詳細描述]
   - 原因：[根本原因]
   - 解決：[解決方案]
   - 學習：[經驗教訓]
```

#### 5. 關鍵學習
- 技術洞察：重要發現
- 最佳實踐：應該遵循的做法
- 避坑指南：不要犯的錯誤

#### 6. 技術決策
記錄為什麼選擇某個方案：
- 選擇的理由
- 考慮的替代方案
- 帶來的好處

### 報告撰寫最佳實踐

**必須做**：
- ✅ 使用清晰的標題結構
- ✅ 包含代碼範例和配置範例
- ✅ 記錄實際測試結果（不要編造）
- ✅ 提供避坑指南
- ✅ 記錄技術決策的原因

**避免**：
- ❌ 只記錄成功，隱瞞問題
- ❌ 過於簡略，缺乏細節
- ❌ 只有代碼，沒有說明
- ❌ 純技術術語，缺乏背景說明

---

## 📋 命名規範

### 目錄命名

**dev-reports/**：
- 格式：`YYYY-MM-feature-name/`
- 範例：`2026-01-browser-sandbox/`
- 規則：使用 kebab-case（小寫 + 連字符）

**dev-in-progress/**：
- 格式：`feature-name/`
- 範例：`feature-search/`, `feature-auth/`
- 規則：使用 kebab-case，簡短但描述性強

### 文件命名

**核心文檔（docs/）**：
- 格式：`feature-name.md`
- 範例：`architecture-guide.md`, `deployment-guide.md`
- 規則：使用 kebab-case

**開發文件（dev-in-progress/）**：
- `PROGRESS.md` - 進度追蹤（大寫，必須）
- `notes.md` - 開發筆記（小寫）
- `design.md` - 設計文檔（小寫）
- `test-results.md` - 測試記錄（小寫）
- `*.draft` - 個人草稿（不進 Git）
- `*.wip` - 工作中文件（不進 Git）

**報告文件（dev-reports/）**：
- `REPORT.md` - 綜合報告（大寫，必須）
- `README.md` - 說明文檔（大寫）
- `TEMPLATE.md` - 模板文件（大寫）

---

## 🔧 Git 管理策略

### 應該進入 Git

✅ **核心文檔**（docs/）
- 永久保留，隨專案演進更新
- 所有 .md 文件

✅ **功能報告**（dev-reports/）
- 歷史記錄，完成後不再修改
- 所有 REPORT.md 和說明文檔

✅ **開發中文件**（dev-in-progress/）
- 供多平台 agents 協作
- PROGRESS.md（必須）
- 所有開發筆記和設計文檔

✅ **配置文件**
- `.gitignore`
- `README.md`
- `.clinerules/*`

### 應該忽略（不進 Git）

❌ **個人草稿**
- `*.draft` - 個人實驗和草稿
- `*.wip` - 工作中的個人文件
- `*~` - 臨時編輯文件

❌ **系統文件**
- `.DS_Store`, `Thumbs.db`
- `.vscode/`, `.idea/`
- `__pycache__/`, `*.pyc`

### .gitignore 規則

```gitignore
# Development in progress - ignore personal drafts
*.draft
*.wip
*~

# 其他規則...
```

---

## 🤝 多平台協作規範

### 開始工作前

```bash
# 1. 同步最新狀態
git pull

# 2. 查看進度
cat dev-in-progress/feature-name/PROGRESS.md

# 3. 檢查是否有衝突
git status
```

### 工作過程中

**頻繁提交**：
- 完成一個小任務後：`git commit && git push`
- 更新 PROGRESS.md 後：`git commit && git push`
- 每天結束時：確保所有更改已提交

**清晰的 Commit 訊息**：
```bash
# ✅ 好的範例
git commit -m "feat(search): implement elasticsearch integration"
git commit -m "fix(search): handle empty query case"
git commit -m "docs(search): add API usage examples"

# ❌ 不好的範例
git commit -m "update"
git commit -m "fix"
git commit -m "changes"
```

### 切換平台時

**Agent A 在 Mac 完成部分工作**：
```bash
git add .
git commit -m "feat(search): implement basic search [WIP]"
git push
```

**Agent B 在 Linux 繼續**：
```bash
git pull
cd dev-in-progress/feature-search
# 查看 PROGRESS.md 了解當前狀態
# 繼續開發...
git add .
git commit -m "feat(search): add filtering [WIP]"
git push
```

**Agent C 在 Windows 完成**：
```bash
git pull
# 完成最後的任務
# 創建報告
# 清理開發文件
git add .
git commit -m "docs: complete search feature report"
git push
```

---

## 🧹 清理策略

### 何時清理

**立即清理**（功能完成後）：
1. ✅ 確認報告已創建：`ls dev-reports/YYYY-MM-feature-name/REPORT.md`
2. ✅ 刪除開發文件：`rm -rf dev-in-progress/feature-name`
3. ✅ 提交清理：`git commit -m "chore: cleanup [feature-name] dev files"`

### 不要保留

❌ **不要**在 dev-in-progress/ 累積已完成功能的文件  
❌ **不要**拖延報告撰寫（記憶新鮮時最準確）  
❌ **不要**讓 dev-in-progress/ 變成「歷史垃圾桶」

### 定期檢查

**每月檢查**：
- 確認 dev-in-progress/ 只有進行中的功能
- 確認已完成功能都有報告
- 確認沒有遺留的臨時文件

---

## 📊 文檔質量標準

### 報告質量檢查清單

- [ ] 功能目標清晰明確
- [ ] 技術實現有詳細說明
- [ ] 包含實際測試結果
- [ ] 記錄所有遇到的問題
- [ ] 提供解決方案和學習
- [ ] 記錄技術決策原因
- [ ] 包含代碼範例或配置範例
- [ ] 提供避坑指南
- [ ] 格式統一（使用 TEMPLATE.md）

### 開發文件質量標準

**PROGRESS.md**：
- [ ] 任務清單完整
- [ ] 狀態及時更新
- [ ] 記錄當前負責 Agent
- [ ] 包含目標說明

**notes.md**：
- [ ] 記錄關鍵決策
- [ ] 包含技術細節
- [ ] 提供參考資料連結

**design.md**：
- [ ] 架構設計清晰
- [ ] API 設計完整
- [ ] 數據結構明確

---

## 🎯 實施檢查清單

### 新功能開發時

- [ ] 在 dev-in-progress/ 創建功能目錄
- [ ] 創建 PROGRESS.md（必須）
- [ ] 使用 Git 進行版本控制
- [ ] 定期更新進度
- [ ] 記錄關鍵決策和問題

### 功能完成時

- [ ] 創建 dev-reports/YYYY-MM-feature-name/
- [ ] 使用 TEMPLATE.md 撰寫報告
- [ ] 整合所有開發文件的關鍵信息
- [ ] 刪除 dev-in-progress/feature-name/
- [ ] 提交報告到 Git

### 協作開發時

- [ ] 開始前 git pull
- [ ] 查看 PROGRESS.md
- [ ] 頻繁提交（每個小任務後）
- [ ] 使用清晰的 commit 訊息
- [ ] 更新 PROGRESS.md

---

## ⚠️ 常見錯誤

### 錯誤 1：忘記更新 PROGRESS.md
**問題**：其他 agents 不知道當前狀態  
**解決**：每次完成任務後立即更新

### 錯誤 2：拖延報告撰寫
**問題**：時間久了忘記細節  
**解決**：功能完成後立即創建報告

### 錯誤 3：報告過於簡略
**問題**：未來無法理解當時的決策  
**解決**：使用 TEMPLATE.md，確保包含所有必要信息

### 錯誤 4：開發文件不進 Git
**問題**：無法跨平台協作  
**解決**：確保所有開發文件（除 .draft/.wip）都提交

### 錯誤 5：不清理已完成功能
**問題**：dev-in-progress/ 累積過多文件  
**解決**：報告創建後立即清理

---

## 📚 參考資料

### 相關文檔
- [dev-reports/README.md](../dev-reports/README.md) - 報告使用說明
- [dev-reports/TEMPLATE.md](../dev-reports/TEMPLATE.md) - 報告模板
- [dev-in-progress/README.md](../dev-in-progress/README.md) - 協作說明
- [docs/README.md](../docs/README.md) - 文檔索引

### 範例報告
- [2026-01 Browser Sandbox](../dev-reports/2026-01-browser-sandbox/REPORT.md)
- [2026-01 Memory 功能](../dev-reports/2026-01-memory-feature/REPORT.md)
- [2026-01 系統升級](../dev-reports/2026-01-system-upgrade/REPORT.md)

---

**規範版本**: v1.1  
**最後更新**: 2026-01-14  
**創建日期**: 2026-01-07  
**維護者**: AgentCoreNexus Team  
**適用範圍**: 所有 agents 和貢獻者

---

**重要提醒**：
- 📋 所有 agents 必須遵循此規範
- 🔄 開發文件必須進入 Git（協作需要）
- 📝 功能完成後必須創建報告
- 🧹 報告創建後必須清理開發文件
- 🤝 支持跨平台多 agents 協作