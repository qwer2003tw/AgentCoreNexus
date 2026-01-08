---
name: mandatory-checklist
description: AI Agent 的強制自檢清單，確保每次代碼修改都遵循正確流程
priority: critical
enforcement: strict
---

# 🚨 強制檢查清單

此檢查清單**必須**在每次修改 Python 代碼後執行。

---

## 📝 代碼修改前 - 自問

在開始修改代碼前，在 `<thinking>` 標籤中自問：

```
<thinking>
1. 我要修改什麼檔案？
2. 這些是 Python 檔案嗎？
3. 如果是，我記得修改後要做什麼嗎？
   答案：立即執行測試！
4. 我準備好承諾會執行測試嗎？
</thinking>
```

---

## ✅ 代碼修改後 - 強制步驟

### Step 1: 代碼質量檢查（❌ 不可跳過）

```bash
cd [project-directory]
ruff check . --fix
ruff format .
ruff check .
```

**必須確認**: `All checks passed!` 或 `Found 0 errors`

**如果失敗**: 
- 查看錯誤訊息
- 修復所有問題
- 重新執行檢查

**禁止**: 「錯誤不重要，先提交」

---

### Step 2: 單元測試（❌ 不可跳過）

```bash
# telegram-agentcore-bot
python3.11 -m pytest tests/ -v

# telegram-lambda
python3.11 -m pytest tests/ --ignore=tests/e2e/ -v
```

**必須確認**: `XX passed` 且沒有 failed

**如果失敗**: 
- 查看失敗的測試
- 修復代碼或測試
- 重新執行所有測試

**禁止**: 「只有一個測試失敗，應該沒關係」

---

### Step 3: E2E 測試（telegram-lambda 專用）

```bash
cd telegram-lambda
python3.11 -m pytest tests/e2e/ -v
```

**必須確認**: 所有測試通過

---

### Step 4: 覆蓋率檢查（❌ 不可跳過）

```bash
python3.11 -m pytest tests/ --cov=. --cov-report=term
```

**必須確認**: 新代碼覆蓋率 ≥ 80%

**如果不足**: 
- 為未覆蓋的代碼添加測試
- 重新執行測試
- 確認覆蓋率達標

**禁止**: 「75% 差不多了」

---

## 🚫 絕對禁止的行為

### 禁止的想法

❌ 「這次改動很小，應該不用測試」  
❌ 「看起來沒問題，直接提交吧」  
❌ 「測試很慢，先提交再說」  
❌ 「用戶在等，快點完成」  
❌ 「我很確定沒問題，跳過測試」

### 正確的想法

✅ 「不管多小的改動，都要測試」  
✅ 「測試失敗 = 不能提交」  
✅ 「用戶寧願等 5 分鐘，也不要收到 bug」  
✅ 「測試是專業標準，不是可選項」  
✅ 「自信不能代替測試驗證」

---

## 🤖 AI Agent 自檢協議

### 在使用 attempt_completion 前

**必須在 `<thinking>` 中確認**：

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

### 報告格式（標準模板）

**必須包含測試結果**：

```
我已完成代碼修改。現在執行測試流程...

[執行 execute_command: ruff check . --fix && ruff format . && ruff check .]
✅ 代碼質量檢查通過（0 errors）

[執行 execute_command: python3.11 -m pytest tests/ -v]
✅ 測試通過（31 passed, 0 failed）

[執行 execute_command: pytest tests/ --cov=. --cov-report=term]
✅ 覆蓋率：88% (超過 80% 門檻)

所有檢查通過！代碼已準備好提交。

建議的 git 操作：
git add .
git commit -m "feat: implement feature X"
git push
```

**禁止的報告格式**：

```
❌ 「我已完成修改」（沒提測試）
❌ 「功能實現完成」（沒提測試結果）
❌ 「應該可以了」（沒有驗證）
❌ 「代碼寫好了，可以提交」（沒有測試證據）
```

---

## 📊 檢查清單（Commit 前）

在使用 `attempt_completion` 建議 commit 前，確認：

- [ ] ✅ 已執行 `ruff check . --fix && ruff format . && ruff check .`
- [ ] ✅ 已執行 `pytest tests/` (或對應的測試命令)
- [ ] ✅ 所有測試通過（0 failed）
- [ ] ✅ 覆蓋率 ≥ 80%（或接近）
- [ ] ✅ 已向用戶清楚報告所有結果
- [ ] ✅ 在 `<thinking>` 中確認所有步驟完成

**如果任何一項是 ❌ 或 ⚠️：不得建議 commit**

---

## 💡 為什麼必須測試？

### 1. 避免破壞現有功能
你的改動可能影響其他部分，測試能立即發現。

**案例**: 修改 `error_messages.py`，但破壞了 `conversation_agent.py` 的錯誤處理。

### 2. 確保新功能正確
測試驗證功能如預期運作，不只是「看起來對」。

**案例**: 重試機制「應該」會重試 3 次，測試證明它確實會。

### 3. 維持代碼質量
覆蓋率確保代碼有充分測試，不是「裸奔」進生產環境。

**案例**: 88% 覆蓋率 = 88% 的代碼有測試保護。

### 4. 節省時間
**本地 5 分鐘發現問題 < 生產環境 2 小時修復 + 用戶受影響**

**時間對比**：
- 本地測試: 5 分鐘
- 部署後發現: 5 分鐘（用戶回報）+ 10 分鐘（診斷）+ 15 分鐘（修復）+ 5 分鐘（重新部署）= 35 分鐘 + 用戶受影響

### 5. 專業標準
跳過測試 = 不專業 = 不可接受

**專業開發者**: 修改 → 測試 → 提交  
**業餘開發者**: 修改 → 提交 → 希望沒問題 → 出問題 → 修復 → ...

---

## 🎯 成功標準

### 對 AI Agents
- ✅ **100%** 的代碼修改後都執行測試
- ✅ **100%** 的 commit 建議前都有測試證據
- ✅ **0%** 跳過測試的情況

### 對專案
- ✅ 所有 commit 都經過測試驗證
- ✅ 新功能覆蓋率 ≥ 80%
- ✅ CI/CD 始終綠燈
- ✅ 生產環境 bug 減少 90%+

---

## ⚠️ 違規處理

### 第一次違規
**症狀**: 修改完代碼沒測試就報告完成  
**處理**: 用戶提醒「測試過了嗎？」  
**行動**: 立即補測試，承認錯誤

### 第二次違規
**症狀**: 再次忘記測試  
**處理**: 檢討為什麼規範沒用  
**行動**: 
- 更新規範（添加更明顯的提醒）
- 檢查是否需要更強的技術強制

### 第三次違規
**症狀**: 持續違反  
**處理**: 流程設計問題  
**行動**:
- 考慮是否規範太複雜
- 是否需要自動化工具
- 是否需要改變工作流程

---

## 🔧 實用工具

### 快速檢查命令

**telegram-agentcore-bot**:
```bash
cd telegram-agentcore-bot && \
  ruff check . --fix && ruff format . && ruff check . && \
  python3.11 -m pytest tests/test_error_handling.py -v && \
  echo "✅ 檢查完成"
```

**telegram-lambda**:
```bash
cd telegram-lambda && \
  ruff check . --fix && ruff format . && ruff check . && \
  python3.11 -m pytest tests/ -v && \
  echo "✅ 檢查完成"
```

### 測試提醒腳本

**remind-test.sh**:
```bash
#!/bin/bash
echo "⚠️  提醒：修改 Python 代碼後必須執行測試！"
echo ""
echo "📋 檢查清單："
echo "  1. ruff check . --fix && ruff format . && ruff check ."
echo "  2. pytest tests/ -v"
echo "  3. 確認覆蓋率 ≥ 80%"
echo ""
```

---

## 📚 相關規範

- `.clinerules/CODE_QUALITY_WORKFLOW.md` - 代碼質量規範
- `.clinerules/TEST_EXECUTION_WORKFLOW.md` - 測試執行規範
- `.git/hooks/pre-commit` - Pre-commit Hook（技術強制）

---

## 🎓 記住這些

1. **測試不是可選的** - 是強制要求
2. **測試不是負擔** - 是品質保證
3. **測試不是浪費時間** - 是節省時間
4. **小改動也要測試** - 不分大小
5. **自信不能代替測試** - 必須驗證

---

## 💬 自我提醒

當你想跳過測試時，問自己：

> 「如果這次改動在生產環境出問題，  
> 影響了用戶，  
> 我能接受嗎？」

**答案如果是「不能」，就不要跳過測試。**

---

**規範版本**: v1.0  
**創建日期**: 2026-01-08  
**強制執行**: 是  
**技術保護**: Pre-commit Hook  
**適用範圍**: 所有 AI agents

---

**記住**：規範不只是文字，是團隊的承諾。  
**記住**：Pre-commit Hook 是備用方案，主動遵守才是目標。  
**記住**：測試是專業標準，不是可選項。