# Git Hooks 使用指南

本目錄包含 AgentCoreNexus 專案的 Git hooks，用於強制執行代碼質量標準。

---

## 📋 已實施的 Hooks

### Pre-commit Hook

**目的**：在每次 commit 前自動執行完整的質量檢查

**執行內容**：
1. 🔍 **Ruff 代碼質量檢查**
   - 自動修復可修復的問題
   - 格式化代碼
   - 驗證無剩餘錯誤

2. 🧪 **單元測試**
   - telegram-lambda: `pytest tests/ --ignore=tests/e2e/`
   - telegram-agentcore-bot: `pytest tests/`

3. 🎭 **E2E 測試**
   - telegram-lambda: `pytest tests/e2e/`
   - 如果依賴未安裝會跳過（並顯示警告）

4. 📊 **覆蓋率檢查**
   - 優先使用 `diff-cover` 檢查新代碼（≥ 80%）
   - 如果 diff-cover 不可用，檢查整體覆蓋率（≥ 70%）

**執行時間**：2-5 分鐘

**觸發條件**：只在 Python 文件（.py）被修改時執行

---

## 🔧 安裝

### 自動安裝（推薦）

在專案根目錄執行：
```bash
./setup-hooks.sh
```

腳本會：
- ✅ 複製 hook 到 `.git/hooks/`
- ✅ 設置執行權限
- ✅ 檢查測試環境
- ✅ 顯示安裝狀態

### 手動安裝

```bash
cp .clinerules/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

---

## 🎯 設計理念

### 為什麼執行時間這麼長？

**因為主要執行者是 AI agents（Cline），而非人類開發者**

| 特性 | 人類開發者 | AI Agent |
|------|-----------|----------|
| Commit 頻率 | 頻繁（每 10 分鐘） | 不頻繁（完成任務時） |
| 等待容忍度 | 不願等 > 30 秒 | 可等 5-10 分鐘 |
| 跳過傾向 | 會用 --no-verify | 遵循規範 |

因此，我們可以在 pre-commit 執行完整測試，而不用擔心影響開發效率。

### 為什麼不分成快速 + 完整兩層？

**原因**：
1. AI 不介意等待 → 不需要「快速模式」
2. 簡化架構 → 只需一層即可
3. 與 clinerules 完美對齊 → 規範要求在 commit 前執行所有檢查

---

## 🤖 AI Agent 使用指南

### Hook 是備用保險，不是替代

**你仍然必須主動執行測試！**

```bash
# 1. 完成代碼修改後，主動執行測試
ruff check . --fix && ruff format . && ruff check .
pytest tests/ --ignore=tests/e2e/ -v
pytest tests/e2e/ -v
pytest tests/ --cov=src --cov-report=xml
diff-cover coverage.xml --compare-branch=main --fail-under=80

# 2. 向用戶報告結果
「所有測試通過，覆蓋率 88%」

# 3. 建議 commit
git add .
git commit -m "feat: implement feature X"

# 4. Hook 自動執行（備用驗證）
# [Hook 運行 2-5 分鐘]
# ✅ 所有檢查通過！代碼已準備好 commit
```

### 為什麼要雙重執行？

**主動執行的價值**：
1. **第一道防線**：在建議 commit 前發現問題
2. **用戶溝通**：向用戶報告測試結果是你的職責
3. **提前修復**：比 hook 阻止 commit 後再修復更好

**Hook 的價值**：
1. **備用保險**：如果你忘記測試，hook 會捕捉
2. **防止錯誤**：如果測試沒通過但你仍建議 commit，hook 會阻止
3. **環境驗證**：確保測試環境正常運作

---

## 🚫 跳過 Hook（不推薦）

### 緊急情況

如果確實需要跳過 hook（例如緊急 hotfix）：
```bash
git commit --no-verify -m "hotfix: emergency fix"
```

**⚠️ 警告**：
- 只在緊急情況使用
- 下次 commit 必須補回測試
- 可能導致 CI/CD 失敗

### AI Agent 不應建議跳過

作為 AI agent，你**不應該**建議用戶使用 `--no-verify`，除非：
1. 用戶明確要求
2. 已經解釋了風險
3. 用戶理解後果

---

## 🔍 故障排除

### Hook 執行失敗

**症狀**：Commit 被阻止，顯示錯誤訊息

**解決步驟**：
1. 查看錯誤訊息，確定是哪一步失敗
2. 在專案目錄手動執行失敗的命令
3. 修復問題
4. 重新 commit

### 常見問題

#### Q: E2E 測試被跳過
**A**: 安裝測試依賴：
```bash
cd telegram-lambda
pip install -r requirements-test.txt
```

#### Q: diff-cover 失敗
**A**: Hook 會自動降級到檢查整體覆蓋率（70%）

#### Q: Hook 太慢
**A**: 這是設計如此（2-5 分鐘），因為主要執行者是 AI

#### Q: 想要快速 commit
**A**: 如果是人類開發者且需要快速保存進度，可以使用 `--no-verify`，但記得下次補測試

---

## 📚 相關文檔

- [CODE_QUALITY_WORKFLOW.md](../CODE_QUALITY_WORKFLOW.md) - Ruff 檢查規範
- [TEST_EXECUTION_WORKFLOW.md](../TEST_EXECUTION_WORKFLOW.md) - 測試執行規範
- [MANDATORY_CHECKLIST.md](../MANDATORY_CHECKLIST.md) - AI Agent 檢查清單
- [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) - 快速參考

---

## 🔄 維護

### 更新 Hook

如果 hook 腳本有更新：
```bash
# 重新安裝
./setup-hooks.sh
```

### 驗證 Hook 已安裝

```bash
ls -l .git/hooks/pre-commit
# 應該顯示文件並且有執行權限（x）
```

### 測試 Hook

```bash
# 創建測試 commit
touch test-file.py
git add test-file.py
git commit -m "test: verify hook"
# Hook 應該執行並通過
git reset HEAD~1  # 取消測試 commit
rm test-file.py
```

---

**版本**: v1.0  
**創建日期**: 2026-01-08  
**維護者**: AgentCoreNexus Team  
**適用範圍**: 所有貢獻者（AI agents 和人類開發者）