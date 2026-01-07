# 代碼質量與 Ruff 使用指南

本專案使用 [Ruff](https://github.com/astral-sh/ruff) 作為 Python 代碼的 linter 和 formatter。

## 🚀 快速開始

### 安裝 Ruff

```bash
# 全局安裝（推薦）
pip install ruff

# 或使用 pipx
pipx install ruff
```

### 基本命令

```bash
# 檢查代碼問題
ruff check .

# 自動修復可修復的問題
ruff check . --fix

# 格式化代碼
ruff format .

# 查看統計
ruff check . --statistics
```

## 📋 開發工作流

### 1. 寫代碼前

確保 Ruff 已安裝並配置好編輯器整合（見下方）。

### 2. 寫代碼時

編輯器會自動：
- 顯示代碼問題（波浪線標記）
- 保存時自動格式化
- 保存時自動修復簡單問題

### 3. 提交前

```bash
# 在專案根目錄執行
ruff check . --fix
ruff format .

# 確認沒有問題
ruff check .
```

### 4. Pull Request

CI 會自動運行 Ruff 檢查。如果失敗：
1. 查看 GitHub Actions 的錯誤訊息
2. 在本地執行相同命令修復
3. 重新提交

## 🔧 編輯器整合

### VS Code（推薦）

1. **安裝擴展**
   - 搜索並安裝 `Ruff` (charliermarsh.ruff)

2. **配置已包含在專案中**
   - `.vscode/settings.json` 已配置完成
   - 打開專案即自動啟用

3. **驗證安裝**
   - 打開任何 `.py` 文件
   - 保存時應該自動格式化
   - 代碼問題會有波浪線標記

### PyCharm / IntelliJ

1. **安裝 Ruff Plugin**
   - Settings → Plugins → 搜索 "Ruff"
   - 安裝並重啟

2. **或配置為 External Tool**
   - Settings → Tools → External Tools → Add
   - Name: `Ruff Check`
   - Program: `ruff`
   - Arguments: `check --fix $FilePath$`
   - Working directory: `$ProjectFileDir$`

### 其他編輯器

參考 [Ruff 官方文檔](https://docs.astral.sh/ruff/integrations/)

## 📚 規則說明

### 啟用的規則集

| 代碼 | 說明 | 範例 |
|------|------|------|
| E | pycodestyle errors | 縮排、空格等格式問題 |
| F | pyflakes | 未使用的 imports、未定義的變數 |
| I | isort | Import 排序 |
| N | pep8-naming | 命名規範 |
| UP | pyupgrade | 現代化 Python 語法 |
| W | pycodestyle warnings | 空白行等警告 |
| B | flake8-bugbear | 常見 bug 模式 |
| C4 | flake8-comprehensions | 列表推導式優化 |
| SIM | flake8-simplify | 代碼簡化建議 |

### Lambda 特定例外

```toml
# Lambda 連接池模式允許使用 global
ignore = ["PLW0603"]
```

### 測試文件例外

測試文件有更寬鬆的規則：
- 允許較長的行（fixtures）
- 允許 assert 語句
- 允許魔術數字

## 🔍 常見問題

### Q: 如何忽略特定行的警告？

```python
# 在行尾添加 noqa 註解
x = 1  # noqa: E501

# 忽略特定規則
result = eval(user_input)  # noqa: S307

# 忽略整個文件
# ruff: noqa
```

### Q: 如何暫時禁用某個規則？

在 `pyproject.toml` 的 `ignore` 列表中添加：

```toml
[tool.ruff.lint]
ignore = [
    "E501",  # line-too-long
    # 添加你要忽略的規則
]
```

### Q: Ruff 和 Black 衝突嗎？

不會。本專案只使用 Ruff：
- Ruff format 替代 Black
- Ruff check 替代 Flake8 + isort + pyupgrade

### Q: 為什麼有些問題無法自動修復？

某些問題需要人工判斷：
- 裸 except（應該指定異常類型）
- 未使用的變數（可能是有意保留）
- 複雜的代碼簡化建議

### Q: CI 失敗了怎麼辦？

```bash
# 1. 拉取最新代碼
git pull

# 2. 運行修復
ruff check . --fix
ruff format .

# 3. 檢查剩餘問題
ruff check .

# 4. 手動修復無法自動修復的問題

# 5. 提交
git add .
git commit -m "fix: resolve ruff issues"
git push
```

## 🎯 最佳實踐

### ✅ 推薦做法

1. **定期運行 Ruff**
   ```bash
   # 每天開始工作前
   ruff check . --fix
   ```

2. **提交前檢查**
   ```bash
   # 加入 git pre-commit hook（可選）
   ruff check . --fix && git commit
   ```

3. **閱讀錯誤訊息**
   - Ruff 的錯誤訊息很詳細
   - 包含問題位置、原因、修復建議

4. **逐步啟用規則**
   - 新規則加入 `select` 列表
   - 觀察影響後決定是否保留

### ❌ 避免做法

1. **不要過度使用 noqa**
   - 只在確實需要時使用
   - 考慮修改規則配置而不是註解

2. **不要忽略所有錯誤**
   ```bash
   # 不推薦
   ruff check . || true
   ```

3. **不要在不同環境使用不同配置**
   - 統一使用 pyproject.toml
   - 確保 CI 和本地一致

## 📊 專案統計

### 當前狀態

```bash
# 查看整體統計
ruff check . --statistics

# 查看特定子專案
cd telegram-lambda && ruff check . --statistics
cd telegram-agentcore-bot && ruff check . --statistics
```

### 改善記錄

**初始導入（2026-01-07）**:
- telegram-lambda: 1369 → 5 問題（改善 99.6%）
- telegram-agentcore-bot: 874 → 12 問題（改善 98.6%）
- 總改善: **2243 → 17 問題（改善 99.2%）**

## 🔗 相關資源

- [Ruff 官方文檔](https://docs.astral.sh/ruff/)
- [規則參考](https://docs.astral.sh/ruff/rules/)
- [配置參考](https://docs.astral.sh/ruff/configuration/)
- [VS Code 整合](https://docs.astral.sh/ruff/editors/setup/#vs-code)

## 💡 提示

- Ruff 非常快（10-100x faster than alternatives）
- 一個工具替代多個工具（Black, isort, Flake8, etc.）
- 與 Python 3.11 完美配合
- 適合 Lambda 的快速 CI/CD

---

**更新日期**: 2026-01-07  
**維護者**: AgentCoreNexus Team