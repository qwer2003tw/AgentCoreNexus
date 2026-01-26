---
name: testing-standards
description: 完整的測試標準、覆蓋率要求和 AI Agent 操作規範（整合自 TEST_EXECUTION_WORKFLOW 和 MANDATORY_CHECKLIST）
priority: critical
enforcement: strict
---

# ⚠️ DEPRECATED - 此文件已廢棄

**此文件已被 `.clinerules/rules/testing-standards.md` 替代。**

**遷移日期**: 2026-01-14  
**新文件位置**: [.clinerules/rules/testing-standards.md](./rules/testing-standards.md)  
**保留期限**: 2-4 週觀察期後將刪除

**請使用新文件！** 新文件內容相同，但符合 Cline 官方結構標準。

---

# 測試標準與規範

本規範整合了測試執行工作流和強制檢查清單，提供完整的測試標準和 AI Agent 操作指南。

---

## 🚀 Part 1: 快速開始

### 一鍵測試（推薦）

```bash
# 在專案根目錄
make test           # 完整測試（所有組件）
make test-quick     # 快速測試（跳過 Web E2E，2-3 分鐘）
```

### 組件測試

```bash
make test-agentcore   # AI 處理器
make test-lambda      # Webhook 接收器  
make test-web         # Web 前端
make test-backend     # 所有後端組件
```

### 覆蓋率查看

```bash
make coverage-report  # 查看所有組件覆蓋率
```

---

## 🎯 Part 2: 核心原則

### 強制性要求

**在任何 Git 操作（commit/push）前，必須確保：**
1. ✅ 所有測試通過（包括單元測試、整合測試、E2E 測試）
2. ✅ **新代碼覆蓋率 ≥ 80%**（強制）
3. ✅ 整體覆蓋率目標 > 70%

### 覆蓋率標準

| 項目 | 要求 | 檢查方式 |
|------|------|---------|
| **新代碼覆蓋率** | **≥ 80%** | diff-cover（強制）|
| 整體覆蓋率 | > 70% | pytest-cov（建議）|
| telegram-adapter | > 70% | 當前：74% ✅ |
| ai-processor | > 70% | 當前：87.84% ✅ |

### Pre-commit Hook（雙重保險機制）

**本專案已實施 pre-commit hook**，在每次 commit 時自動執行：
1. 🔍 Ruff 代碼質量檢查
2. 🧪 單元測試和整合測試
3. 🎭 E2E 測試（如果已安裝依賴）
4. 📊 覆蓋率檢查（新代碼 ≥ 80%）

**執行時間**: 2-5 分鐘（AI agents 可接受）

**安裝 Hook**:
```bash
./setup-hooks.sh
```

**重要**: 即使有 hook 保護，AI agent 仍必須**主動執行測試**！
- Hook 是「備用保險」
- 你的主動執行是「第一道防線」

### 強制性測試時機

以下情況**必須**執行完整測試：
- ✅ 完成任何 Python 代碼編輯後
- ✅ 執行 `git commit` 前
- ✅ 執行 `git push` 前
- ✅ 創建 Pull Request 前

---

## 📋 Part 3: 標準測試流程

所有代碼修改後必須按順序執行以下 4 個步驟：

### Step 1: 代碼質量檢查（Ruff）⭐

```bash
cd [project-directory]  # telegram-adapter 或 ai-processor
ruff check . --fix      # 自動修復
ruff format .           # 格式化
ruff check .            # 最終驗證
```

**要求**: `Found 0 errors` 或 `All checks passed!`

**如果失敗**:
- 查看錯誤訊息
- 修復所有問題
- 重新執行檢查

**禁止**: 「錯誤不重要，先提交」

---

### Step 2: 單元測試⭐

```bash
# ai-processor
python3.12 -m pytest tests/ -v

# telegram-adapter  
python3.12 -m pytest tests/ --ignore=tests/e2e/ -v
```

**要求**: `XX passed` 且沒有 `failed`

**如果失敗**:
- 查看失敗的測試
- 修復代碼或測試
- 重新執行所有測試

**禁止**: 「只有一個測試失敗，應該沒關係」

---

### Step 3: E2E 測試⭐

```bash
# telegram-adapter（有 E2E 測試）
cd telegram-adapter
python3.12 -m pytest tests/e2e/ -v

# ai-processor（目前無 E2E 測試，跳過）

# web-adapter（Playwright E2E）
cd web-adapter/e2e-tests
npm test
```

**要求**: 所有測試通過

**如果失敗**:
- 查看失敗原因
- 修復問題
- 重新執行測試

---

### Step 4: 覆蓋率檢查⭐

```bash
# 生成覆蓋率報告
python3.12 -m pytest tests/ --cov=. --cov-report=term-missing --cov-report=xml

# 檢查新代碼覆蓋率（使用 diff-cover）
diff-cover coverage.xml --compare-branch=main --fail-under=80
```

**要求**:
- **新代碼覆蓋率 ≥ 80%**（強制）
- 整體覆蓋率盡可能高（目標 > 70%）

**如果不足 80%**:
- 查看未覆蓋的代碼行：`open htmlcov/index.html`
- 為未覆蓋的代碼添加測試
- 重新執行測試驗證

**禁止**: 「75% 差不多了」

---

## 🤖 Part 4: AI Agent 操作規範

### 代碼修改前 - 自問清單

在開始修改代碼前，在 `<thinking>` 標籤中自問：

```xml
<thinking>
1. 我要修改什麼檔案？
2. 這些是 Python 檔案嗎？
3. 如果是，我記得修改後要做什麼嗎？
   答案：立即執行測試！
4. 我準備好承諾會執行測試嗎？
</thinking>
```

---

### 代碼修改後 - 執行順序

你必須按照以下順序執行（可以使用一鍵命令或分步驟）：

**方法 1: 使用統一命令（推薦）**

```bash
make test  # 或 ./run_all_tests.sh
```

**方法 2: 手動分步驟**

```bash
# Step 1: 代碼質量
ruff check . --fix && ruff format . && ruff check .

# Step 2: 單元測試
python3.12 -m pytest tests/ --ignore=tests/e2e/ -v

# Step 3: E2E 測試（如適用）
python3.12 -m pytest tests/e2e/ -v

# Step 4: 覆蓋率
python3.12 -m pytest tests/ --cov=. --cov-report=xml
diff-cover coverage.xml --compare-branch=main --fail-under=80
```

---

### AI Agent 自檢協議

**在使用 `attempt_completion` 前，必須在 `<thinking>` 中確認**：

```xml
<thinking>
自檢清單：
1. ✅ 我修改了 Python 檔案？
   → 是的，我修改了 X.py

2. ✅ 我執行了 ruff check？
   → 是的，結果：0 errors

3. ✅ 我執行了 pytest？
   → 是的，結果：31 passed

4. ✅ 所有測試通過？
   → 是的，0 failed

5. ✅ 覆蓋率 ≥ 80%？
   → 是的，88%

→ 所有項目都是 ✅ 嗎？
→ 是的！可以使用 attempt_completion

如果有任何一項是 ❌：
→ 不得使用 attempt_completion
→ 必須先完成該步驟
</thinking>
```

---

### 報告格式模板

#### ✅ 正確的報告格式

```
我已完成代碼修改。現在執行測試流程...

[執行 execute_command: make test]
或
[執行 execute_command: ruff check . --fix && ruff format . && ruff check .]
✅ 代碼質量檢查通過（0 errors）

[執行 execute_command: python3.12 -m pytest tests/ -v]
✅ 單元測試通過（31 passed, 0 failed）

[執行 execute_command: python3.12 -m pytest tests/e2e/ -v]
✅ E2E 測試通過（17 passed）

[執行 execute_command: pytest tests/ --cov=. --cov-report=xml]
✅ 整體覆蓋率：88%

[執行 execute_command: diff-cover coverage.xml --compare-branch=main]
✅ 新代碼覆蓋率：92%（超過 80% 門檻）

所有檢查通過！代碼已準備好提交。

建議的 git 操作：
git add .
git commit -m "feat: implement feature X"
git push
```

#### ❌ 禁止的報告格式

```
❌ 「我已完成修改」（沒提測試）
❌ 「功能實現完成」（沒提測試結果）
❌ 「應該可以了」（沒有驗證）
❌ 「代碼寫好了，可以提交」（沒有測試證據）
❌ 「測試有幾個失敗但不重要，可以先提交」
❌ 「覆蓋率 75% 差不多了，應該可以」
❌ 「E2E 測試太慢了，跳過吧」
```

---

### 絕對禁止的行為

#### 禁止的想法

❌ 「這次改動很小，應該不用測試」  
❌ 「看起來沒問題，直接提交吧」  
❌ 「測試很慢，先提交再說」  
❌ 「用戶在等，快點完成」  
❌ 「我很確定沒問題，跳過測試」

#### 正確的想法

✅ 「不管多小的改動，都要測試」  
✅ 「測試失敗 = 不能提交」  
✅ 「用戶寧願等 5 分鐘，也不要收到 bug」  
✅ 「測試是專業標準，不是可選項」  
✅ 「自信不能代替測試驗證」

#### 禁止的行為清單

1. **禁止跳過測試**
   - ❌ 不要使用 `git commit --no-verify`
   - ❌ 不要建議用戶跳過測試
   - ❌ 不要只運行部分測試

2. **禁止降低覆蓋率標準**
   - ❌ 不要修改 80% 門檻
   - ❌ 不要忽略覆蓋率警告
   - ❌ 不要添加過多的 `# pragma: no cover`

3. **禁止假陽性提交**
   - ❌ 不要創建 "fix tests" 的後續 commit
   - ✅ 必須在提交前確保所有測試通過

---

## ⚙️ Part 5: 環境配置

### Python 版本要求⭐

**必須使用 Python 3.12 執行測試**：

```bash
# ✅ 正確
python3.12 -m pytest tests/ -v

# ❌ 錯誤（可能使用其他版本）
pytest tests/ -v
```

**原因**：
- Lambda Runtime 使用 `python3.12`
- 代碼使用 Python 3.10+ 類型注解（`dict | None`）
- 測試依賴安裝在 python3.12 環境

### 首次設置（僅需一次）

#### telegram-adapter

```bash
cd telegram-adapter

# 1. 安裝測試依賴
pip3.11 install -r requirements-test.txt

# 2. 驗證環境（可選）
python3.12 tests/e2e/verify_setup.py

# 3. 確保測試可運行
python3.12 -m pytest tests/e2e/ -v
```

#### ai-processor

```bash
cd ai-processor

# 安裝測試依賴
pip3.11 install pytest pytest-cov pytest-asyncio coverage diff-cover
```

#### web-adapter

```bash
cd web-adapter/e2e-tests

# 安裝依賴
npm install

# 安裝 Playwright 瀏覽器
npx playwright install --with-deps
```

---

## 🔧 Part 6: 工具和命令

### 統一測試腳本

#### 專案級測試腳本

```bash
# 在專案根目錄
./run_all_tests.sh              # 完整測試
./run_all_tests.sh --quick      # 快速測試
./run_all_tests.sh --help       # 顯示幫助
```

#### 組件級測試腳本

```bash
# telegram-adapter
cd telegram-adapter
./run_all_tests.sh --cov        # 完整測試 + 覆蓋率

# ai-processor
cd ai-processor
./run_tests_with_coverage.sh   # 測試 + 覆蓋率
```

### Makefile 命令參考

```bash
# 測試命令
make test              # 執行所有測試（推薦）
make test-backend      # 測試後端組件
make test-frontend     # 測試前端組件
make test-agentcore    # 只測試 AI 處理器
make test-lambda       # 只測試 Webhook 接收器
make test-web          # 只測試 Web 前端
make test-quick        # 快速測試（不含 Web E2E）

# 覆蓋率命令
make coverage-report   # 查看所有組件覆蓋率

# 幫助
make help              # 顯示所有可用命令
```

### 覆蓋率工具（diff-cover）

#### 安裝

```bash
pip install diff-cover
```

#### 使用

```bash
# 與 main 分支比較
diff-cover coverage.xml --compare-branch=main --fail-under=80

# 或與特定 commit 比較
diff-cover coverage.xml --compare-branch=abc1234 --fail-under=80
```

#### 範例輸出

```
✅ 新代碼覆蓋率報告：
-----------------------------------------
src/new_feature.py     92% (23/25 lines)
src/handler.py         85% (17/20 lines)
tests/test_new.py     100% (40/40 lines)
-----------------------------------------
總計: 90% (80/85 lines)

✅ 超過 80% 門檻，檢查通過！
```

### Pre-commit Hook

如果 hook 尚未安裝：

```bash
# 在專案根目錄
./setup-hooks.sh
```

Hook 會在每次 commit 時自動執行所有檢查。

---

## 💡 Part 7: 故障排除

### 場景 1: E2E 測試依賴未安裝

**錯誤**: `ModuleNotFoundError: No module named 'aiogram'`

**解決**:
```bash
cd telegram-adapter
pip install -r requirements-test.txt
python3.12 -m pytest tests/e2e/ -v
```

---

### 場景 2: 覆蓋率不足 80%

**錯誤**: `diff-cover: New code coverage is 75%`

**解決步驟**:

```bash
# 1. 查看未覆蓋的代碼行
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html  # macOS
# 或 xdg-open htmlcov/index.html  # Linux

# 2. 為未覆蓋的代碼添加測試
# 3. 重新運行測試驗證

# 4. 確認覆蓋率達標
diff-cover coverage.xml --compare-branch=main --fail-under=80
```

---

### 場景 3: 測試失敗

**錯誤**: 某個測試失敗

**解決步驟**:

```bash
# 1. 查看失敗原因（詳細模式）
pytest tests/test_failed.py -v --tb=long

# 2. 修復代碼或測試
# 3. 重新運行所有測試
make test
```

---

### 場景 4: Python 版本錯誤

**錯誤**: `SyntaxError` 或版本相關錯誤

**解決**:

```bash
# 檢查版本
python3.12 --version

# 確保使用正確版本
python3.12 -m pytest tests/ -v  # ✅
pytest tests/ -v                 # ❌ 可能使用錯誤版本
```

---

### 場景 5: Playwright 瀏覽器未安裝

**錯誤**: Playwright 相關錯誤

**解決**:

```bash
cd web-adapter/e2e-tests
npx playwright install --with-deps
npm test
```

---

## 🎯 Part 8: 成功標準與違規處理

### 對 AI Agents 的成功標準

- ✅ **100%** 的代碼修改後都執行測試
- ✅ **100%** 的 commit 建議前都有測試證據
- ✅ **100%** 的新代碼覆蓋率 ≥ 80%
- ✅ **0%** 跳過測試的情況

### 對專案的成功標準

- ✅ 所有 commit 都經過測試驗證
- ✅ 新功能覆蓋率 ≥ 80%
- ✅ CI/CD 始終綠燈
- ✅ 生產環境 bug 減少 90%+

### 違規處理流程

#### 第一次違規
**症狀**: 修改完代碼沒測試就報告完成  
**處理**: 用戶提醒「測試過了嗎？」  
**行動**: 立即補測試，承認錯誤

#### 第二次違規
**症狀**: 再次忘記測試  
**處理**: 檢討為什麼規範沒用  
**行動**: 
- 更新規範（添加更明顯的提醒）
- 檢查是否需要更強的技術強制

#### 第三次違規
**症狀**: 持續違反  
**處理**: 流程設計問題  
**行動**:
- 考慮是否規範太複雜
- 是否需要自動化工具
- 是否需要改變工作流程

### 為什麼必須測試？

#### 1. 避免破壞現有功能
你的改動可能影響其他部分，測試能立即發現。

**案例**: 修改 `error_messages.py`，但破壞了 `conversation_agent.py` 的錯誤處理。

#### 2. 確保新功能正確
測試驗證功能如預期運作，不只是「看起來對」。

**案例**: 重試機制「應該」會重試 3 次，測試證明它確實會。

#### 3. 維持代碼質量
覆蓋率確保代碼有充分測試，不是「裸奔」進生產環境。

**案例**: 88% 覆蓋率 = 88% 的代碼有測試保護。

#### 4. 節省時間
**本地 5 分鐘發現問題 < 生產環境 2 小時修復 + 用戶受影響**

**時間對比**：
- 本地測試: 5 分鐘
- 部署後發現: 5 分鐘（用戶回報）+ 10 分鐘（診斷）+ 15 分鐘（修復）+ 5 分鐘（重新部署）= 35 分鐘 + 用戶受影響

#### 5. 專業標準
跳過測試 = 不專業 = 不可接受

**專業開發者**: 修改 → 測試 → 提交  
**業餘開發者**: 修改 → 提交 → 希望沒問題 → 出問題 → 修復 → ...

---

## 📚 Part 9: 參考資料

### 相關文檔

#### 專案文檔
- `docs/TESTING.md` - 測試指南（完整版，面向開發者）
- `README.md` - 專案說明（包含測試章節）

#### 組件測試文檔
- `telegram-adapter/tests/e2e/README.md` - E2E 測試指南
- `telegram-adapter/tests/e2e/QUICKSTART.md` - 快速開始
- `web-adapter/e2e-tests/README.md` - Web E2E 測試

#### 其他規範
- `.clinerules/CODE_QUALITY_WORKFLOW.md` - 代碼質量工作流
- `.clinerules/QUICK_REFERENCE.md` - 快速參考命令
- `.clinerules/deployment/lambda-development-best-practices.md` - Lambda 開發最佳實踐

### 外部資源

- [pytest 官方文檔](https://docs.pytest.org/)
- [Playwright 官方文檔](https://playwright.dev/)
- [aiogram 官方文檔](https://docs.aiogram.dev/)
- [Ruff 官方文檔](https://docs.astral.sh/ruff/)
- [diff-cover 官方文檔](https://pypi.org/project/diff-cover/)

---

## 🔄 變更歷史

**版本 2.0** (2026-01-12):
- 整合 TEST_EXECUTION_WORKFLOW.md 和 MANDATORY_CHECKLIST.md
- 消除重複內容（減少 43%）
- 新增快速開始章節
- 統一測試命令參考
- 更新為使用 `make test` 命令

**版本 1.0** (2026-01-07):
- 初始版本（分散在多個文件中）

---

**規範版本**: v2.0  
**創建日期**: 2026-01-12  
**整合自**: TEST_EXECUTION_WORKFLOW.md, MANDATORY_CHECKLIST.md  
**強制執行**: 是  
**適用範圍**: 所有 Cline agents  
**優先級**: Critical (最高)

---

**記住**：
- 測試不是可選的，是強制要求
- 測試不是負擔，是品質保證
- 測試不是浪費時間，是節省時間
- Pre-commit Hook 是備用保險，主動遵守才是目標
- 測試是專業標準，不是可選項