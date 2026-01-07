# 測試執行指南

本文檔說明如何執行完整的測試流程，確保代碼質量和測試覆蓋率。

---

## 🎯 強制性要求

根據 `.clinerules/TEST_EXECUTION_WORKFLOW.md`，在任何 commit/push 前必須：

1. ✅ **Ruff 代碼質量檢查通過**（0 errors）
2. ✅ **所有測試通過**（單元 + 整合 + E2E）
3. ✅ **新代碼覆蓋率 ≥ 80%**

---

## 🚀 快速開始

### 一鍵執行所有檢查

```bash
cd telegram-lambda
./run_all_tests.sh --cov -v
```

這將執行：
- Step 1: Ruff 代碼質量檢查
- Step 2: 單元測試和整合測試
- Step 3: E2E 測試
- Step 4: 覆蓋率報告生成
- Step 5: 新代碼覆蓋率檢查（≥ 80%）

---

## 📋 分步執行

### Step 1: 代碼質量檢查

```bash
cd telegram-lambda
ruff check . --fix
ruff format .
ruff check .
```

**必須通過**（0 errors）才能繼續。

### Step 2: 單元測試和整合測試

```bash
pytest tests/ --ignore=tests/e2e/ -v
```

**所有測試必須通過。**

### Step 3: E2E 測試

```bash
# 首次使用：安裝依賴
pip install -r requirements-test.txt

# 運行 E2E 測試
pytest tests/e2e/ -v
```

**所有測試必須通過。**

### Step 4: 覆蓋率檢查

```bash
# 生成覆蓋率報告
pytest tests/ --cov=src --cov-report=html --cov-report=xml

# 查看 HTML 報告
open htmlcov/index.html  # macOS
# 或 xdg-open htmlcov/index.html  # Linux
```

### Step 5: 新代碼覆蓋率檢查

```bash
# 安裝 diff-cover（首次使用）
pip install diff-cover

# 檢查新代碼覆蓋率（與 main 分支比較）
diff-cover coverage.xml --compare-branch=main --fail-under=80
```

**新代碼覆蓋率必須 ≥ 80%。**

---

## 🔧 常用選項

### 快速測試（開發中）

```bash
# 只運行快速測試（排除 slow 標記）
./run_all_tests.sh --fast

# 只運行特定測試文件
pytest tests/e2e/test_commands.py -v
```

**注意**：commit 前仍需運行完整測試！

### 詳細輸出

```bash
# 詳細模式
./run_all_tests.sh --cov -v

# 或手動
pytest tests/ -v --tb=long
```

### 覆蓋率報告

```bash
# 生成 HTML 報告
./run_all_tests.sh --cov

# 查看報告
open htmlcov/index.html
```

---

## 📊 覆蓋率要求

### 整體覆蓋率 vs 新代碼覆蓋率

- **整體覆蓋率**：所有代碼的測試覆蓋率（目標 > 70%，不強制）
- **新代碼覆蓋率**：本次變更新增/修改代碼的覆蓋率（**強制 ≥ 80%**）

### 為什麼是 80%？

- 確保新功能有充分測試
- 防止測試覆蓋率逐漸降低
- 符合業界最佳實踐

### 如何達到 80%？

1. **查看未覆蓋的代碼**：
   ```bash
   pytest tests/ --cov=src --cov-report=html
   open htmlcov/index.html
   ```

2. **為未覆蓋的代碼添加測試**：
   - 查看紅色標記的行
   - 創建或更新測試文件
   - 確保測試覆蓋關鍵邏輯

3. **重新驗證**：
   ```bash
   pytest tests/ --cov=src --cov-report=xml
   diff-cover coverage.xml --compare-branch=main --fail-under=80
   ```

---

## 🐛 故障排除

```

**解決**：
```bash
pip install -r requirements-test.txt
```

### 問題 2: diff-cover 未安裝

**錯誤**：
```
command not found: diff-cover
```

**解決**：
```bash
pip install diff-cover
```

### 問題 3: 覆蓋率不足 80%

**錯誤**：
```
❌ 新代碼覆蓋率: 75%
```

**解決**：
```bash
# 1. 查看未覆蓋的代碼
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html

# 2. 添加測試覆蓋未測試的代碼

# 3. 重新驗證
diff-cover coverage.xml --compare-branch=main --fail-under=80
```

### 問題 4: 測試失敗

**解決流程**：
```bash
# 1. 查看詳細錯誤
pytest tests/test_failed.py -v --tb=long

# 2. 修復代碼或測試

# 3. 重新運行所有測試
./run_all_tests.sh
```

---

## 📚 相關資源

### 專案文檔
- `.clinerules/TEST_EXECUTION_WORKFLOW.md` - 測試執行規範
- `.clinerules/CODE_QUALITY_WORKFLOW.md` - 代碼質量規範
- `tests/e2e/README.md` - E2E 測試完整指南
- `tests/e2e/QUICKSTART.md` - E2E 測試快速開始

### 外部資源
- [pytest 官方文檔](https://docs.pytest.org/)
- [diff-cover 文檔](https://github.com/Bachmann1234/diff_cover)
- [Ruff 文檔](https://docs.astral.sh/ruff/)

---

## ✅ 檢查清單

提交代碼前確認：

- [ ] Ruff 檢查通過（0 errors）
- [ ] 所有單元測試通過
- [ ] 所有整合測試通過
- [ ] 所有 E2E 測試通過（17 個測試）
- [ ] 整體覆蓋率 > 70%
- [ ] **新代碼覆蓋率 ≥ 80%**（強制）

---

**最後更新**: 2026-01-07  
**版本**: 1.0  
**適用範圍**: telegram-lambda 專案