---
name: testing-standards
description: 完整的測試標準、覆蓋率要求和 AI Agent 操作規範
priority: critical
enforcement: strict
always_active: true
---

# Testing Standards and Rules

**這是始終活動的規則** - 所有 Cline agents 必須遵守這些測試標準，確保代碼質量。

---

## 🚀 快速開始

### 一鍵測試（推薦）

```bash
make test           # 完整測試（所有組件）
make test-quick     # 快速測試（跳過 Web E2E，2-3 分鐘）
```

### 組件測試

```bash
make test-agentcore   # AI 處理器
make test-lambda      # Webhook 接收器  
make test-web         # Web 前端
```

---

## 🎯 核心原則

### 強制性要求

**在任何 Git 操作（commit/push）前，必須確保：**
1. ✅ 所有測試通過（單元、整合、E2E）
2. ✅ **新代碼覆蓋率 ≥ 80%**（強制）
3. ✅ 整體覆蓋率 > 70%

### 覆蓋率標準

| 項目 | 要求 | 當前狀態 |
|------|------|---------|
| **新代碼覆蓋率** | **≥ 80%** | 強制檢查 |
| telegram-adapter | > 70% | 74% ✅ |
| ai-processor | > 70% | 87.84% ✅ |

### Pre-commit Hook（雙重保險）

本專案已實施 pre-commit hook，自動執行：
1. 🔍 Ruff 代碼質量檢查
2. 🧪 單元測試和整合測試
3. 🎭 E2E 測試
4. 📊 覆蓋率檢查（新代碼 ≥ 80%）

**安裝**：`./setup-hooks.sh`

**重要**：AI agent 仍必須**主動執行測試**！
- Hook 是「備用保險」
- 主動執行是「第一道防線」

---

## 📋 標準測試流程

### Step 1: 代碼質量檢查 ⭐
```bash
ruff check . --fix && ruff format . && ruff check .
```
**要求**：0 errors

### Step 2: 單元測試 ⭐
```bash
python3.11 -m pytest tests/ -v
```
**要求**：所有測試通過

### Step 3: E2E 測試 ⭐
```bash
python3.11 -m pytest tests/e2e/ -v  # 如適用
```

### Step 4: 覆蓋率檢查 ⭐
```bash
pytest tests/ --cov=. --cov-report=xml
diff-cover coverage.xml --compare-branch=main --fail-under=80
```
**要求**：新代碼 ≥ 80%

---

## 🤖 AI Agent 操作規範

### 代碼修改前 - 自問清單

```xml
<thinking>
1. 我要修改什麼檔案？
2. 這些是 Python 檔案嗎？
3. 如果是，修改後要做什麼？
   答案：立即執行測試！
4. 我準備好承諾會執行測試嗎？
</thinking>
```

### 代碼修改後 - 執行順序

**推薦方式**：
```bash
make test  # 一鍵執行所有檢查
```

**手動方式**：
```bash
# 1. 代碼質量
ruff check . --fix && ruff format . && ruff check .

# 2. 測試
python3.11 -m pytest tests/ -v

# 3. 覆蓋率
pytest tests/ --cov=. --cov-report=xml
diff-cover coverage.xml --compare-branch=main --fail-under=80
```

### AI Agent 自檢協議

**在使用 `attempt_completion` 前，必須確認**：

```xml
<thinking>
自檢清單：
1. ✅ 我修改了 Python 檔案？ → 是
2. ✅ 我執行了 ruff check？ → 是，0 errors
3. ✅ 我執行了 pytest？ → 是，X passed
4. ✅ 所有測試通過？ → 是，0 failed
5. ✅ 覆蓋率 ≥ 80%？ → 是

→ 全部 ✅？可以使用 attempt_completion
→ 有任何 ❌？必須先完成該步驟
</thinking>
```

### 報告格式

**✅ 正確**：
```
已完成代碼修改。執行測試流程...

[execute_command: make test]
✅ 代碼質量：0 errors
✅ 單元測試：31 passed
✅ 覆蓋率：88%（新代碼 92%）

所有檢查通過！可以提交。
```

**❌ 禁止**：
```
❌ 「已完成修改，可以提交了」（沒測試）
❌ 「應該沒問題」（沒驗證）
❌ 「測試有點失敗但不重要」（不可接受）
```

---

## 🚫 絕對禁止的行為

### 禁止的想法
❌ 「改動小，不用測試」  
❌ 「看起來沒問題，直接提交」  
❌ 「測試太慢，先提交」  

### 正確的想法
✅ 「不管多小都要測試」  
✅ 「測試失敗 = 不能提交」  
✅ 「測試是專業標準」  

### 禁止的行為
1. ❌ 不要使用 `git commit --no-verify`
2. ❌ 不要跳過任何測試步驟
3. ❌ 不要降低覆蓋率標準
4. ❌ 不要創建 "fix tests" 後續 commit

---

## ⚙️ 環境配置

### Python 版本要求 ⭐

**必須使用 Python 3.11**：
```bash
python3.11 -m pytest tests/ -v  # ✅ 正確
pytest tests/ -v                 # ❌ 可能用錯版本
```

### 首次設置

```bash
# telegram-adapter
cd telegram-adapter
pip3.11 install -r requirements-test.txt

# ai-processor  
cd ai-processor
pip3.11 install pytest pytest-cov pytest-asyncio coverage diff-cover

# web-adapter
cd web-adapter/e2e-tests
npm install && npx playwright install --with-deps
```

---

## 💡 故障排除

### 覆蓋率不足 80%
```bash
# 查看未覆蓋代碼
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html

# 添加測試後重新檢查
diff-cover coverage.xml --compare-branch=main --fail-under=80
```

### 測試失敗
```bash
# 詳細模式查看
pytest tests/test_failed.py -v --tb=long

# 修復後重新測試
make test
```

### Python 版本錯誤
```bash
# 檢查版本
python3.11 --version

# 使用正確版本
python3.11 -m pytest tests/ -v
```

---

## 🎯 成功標準

### 對 AI Agents
- ✅ 100% 代碼修改後執行測試
- ✅ 100% commit 前有測試證據
- ✅ 100% 新代碼覆蓋率 ≥ 80%
- ✅ 0% 跳過測試情況

### 對專案
- ✅ 所有 commit 經過測試驗證
- ✅ 新功能覆蓋率 ≥ 80%
- ✅ CI/CD 始終綠燈
- ✅ 生產環境 bug 大幅減少

---

## 📚 參考資料

### 專案文檔
- `docs/TESTING.md` - 完整測試指南
- `.clinerules/QUICK_REFERENCE.md` - 快速參考
- `telegram-adapter/tests/e2e/README.md` - E2E 測試

### 其他規範
- `.clinerules/rules/code-quality.md` - 代碼質量規則
- `.clinerules/deployment/lambda-development-best-practices.md`

### 外部資源
- [pytest](https://docs.pytest.org/)
- [Playwright](https://playwright.dev/)
- [Ruff](https://docs.astral.sh/ruff/)
- [diff-cover](https://pypi.org/project/diff-cover/)

---

## 🔄 版本歷史

**版本 2.1** (2026-01-14):
- 重新組織為 rules/ 結構
- 添加 `always_active: true` 標記
- 簡化內容保留核心規範

**版本 2.0** (2026-01-12):
- 整合 TEST_EXECUTION_WORKFLOW 和 MANDATORY_CHECKLIST
- 消除重複內容（減少 43%）

**版本 1.0** (2026-01-07):
- 初始版本

---

**規則版本**: v2.1  
**最後更新**: 2026-01-14  
**強制執行**: 是  
**適用範圍**: 所有 Cline agents  
**優先級**: Critical (最高)

**記住**：
- 測試不是可選的，是強制要求
- 測試不是負擔，是品質保證
- Pre-commit Hook 是備用保險，主動遵守才是目標
- 測試是專業標準，不是可選項