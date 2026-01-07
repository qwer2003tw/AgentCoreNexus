# 代碼提交前檢查清單

**在任何 commit/push 前必須執行！**

⚠️ **重要**：必須使用 **Python 3.11** 執行測試！

---

## ⚡ 一鍵完整檢查

```bash
cd telegram-lambda
./run_all_tests.sh --cov -v
```

或手動使用 python3.11：
```bash
cd telegram-lambda
python3.11 -m ruff check . --fix && \
python3.11 -m ruff format . && \
python3.11 -m ruff check . && \
python3.11 -m pytest tests/ -v --cov=src
```

---

## 📋 分步檢查（如果出問題）

### 1. Ruff 代碼質量（強制）⭐
```bash
ruff check . --fix && ruff format . && ruff check .
```
**要求**: 0 errors

### 2. 單元測試（強制）⭐
```bash
pytest tests/ --ignore=tests/e2e/ -v
```
**要求**: 所有測試通過

### 3. E2E 測試（強制）⭐
```bash
python3.11 -m pytest tests/e2e/ -v
```
**要求**: 所有測試通過

### 4. 覆蓋率（強制）⭐
```bash
python3.11 -m pytest tests/ --cov=src --cov-report=xml
diff-cover coverage.xml --compare-branch=main --fail-under=80
```
**要求**: 新代碼覆蓋率 ≥ 80%

---

## ✅ 全部通過後

```bash
git add .
git commit -m "feat: your message"
git push
```

---

## 🚫 禁止的行為

- ❌ 跳過任何步驟
- ❌ 使用 `git commit --no-verify`
- ❌ 覆蓋率不足 80% 就提交
- ❌ 有測試失敗就提交

---

**規則來源**:
- `.clinerules/CODE_QUALITY_WORKFLOW.md`
- `.clinerules/TEST_EXECUTION_WORKFLOW.md`