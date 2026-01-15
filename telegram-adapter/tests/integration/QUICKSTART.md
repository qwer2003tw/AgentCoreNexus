# 快速開始：E2E 測試

5 分鐘快速上手 Telegram Bot E2E 測試。

## 1️⃣ 安裝依賴（1 分鐘）

```bash
cd telegram-lambda
pip install -r requirements-test.txt
```

## 2️⃣ 運行第一個測試（30 秒）

```bash
pytest tests/e2e/test_commands.py::TestCommands::test_info_command_success -v
```

**預期輸出**：
```
tests/e2e/test_commands.py::TestCommands::test_info_command_success PASSED [100%]

==================== 1 passed in 0.45s ====================
```

## 3️⃣ 運行所有 E2E 測試（10 秒）

```bash
pytest tests/e2e/ -v
```

**預期輸出**：
```
tests/e2e/test_commands.py::TestCommands::test_info_command_success PASSED
tests/e2e/test_commands.py::TestCommands::test_unknown_command_forwarded_to_processor PASSED
tests/e2e/test_message_flow.py::TestMessageFlow::test_text_message_to_eventbridge PASSED
...

==================== 15 passed in 8.32s ====================
```

## 4️⃣ 查看覆蓋率報告（30 秒）

```bash
pytest tests/e2e/ --cov=src --cov-report=html
open htmlcov/index.html  # macOS
# 或 xdg-open htmlcov/index.html  # Linux
```

## 5️⃣ 修改代碼後測試（1 分鐘）

```bash
# 1. 修改代碼
vim src/handler.py

# 2. 運行相關測試
pytest tests/e2e/ -k "command" -v

# 3. 如果通過，提交代碼
git add .
git commit -m "feat: your feature"
```

## 🎯 日常開發工作流

### 修改代碼前
```bash
# 確保所有測試通過
pytest tests/e2e/ -v
```

### 修改代碼後
```bash
# 只運行相關測試（快速檢查）
pytest tests/e2e/test_commands.py -v

# 通過後運行完整測試
pytest tests/e2e/ -v
```

### 部署前
```bash
# 完整測試 + 覆蓋率
pytest tests/ --cov=src --cov-report=term-missing

# 確保覆蓋率 > 80%
```

## 📝 常用命令速查

| 任務 | 命令 |
|------|------|
| 運行所有 E2E 測試 | `pytest tests/e2e/ -v` |
| 運行特定文件 | `pytest tests/e2e/test_commands.py -v` |
| 運行特定測試 | `pytest tests/e2e/ -k "info" -v` |
| 查看覆蓋率 | `pytest tests/e2e/ --cov=src` |
| 排除慢速測試 | `pytest tests/e2e/ -m "not slow"` |
| 詳細日誌 | `pytest tests/e2e/ -v -s` |
| 失敗時停止 | `pytest tests/e2e/ -x` |
| 重跑失敗測試 | `pytest tests/e2e/ --lf` |

## 🐛 常見問題

### Q: 測試失敗說找不到模組

```bash
# 確保安裝了所有依賴
pip install -r requirements-test.txt

# 確保在正確的目錄
cd telegram-lambda
```

### Q: Import 錯誤

```bash
# 檢查 Python 路徑
python -c "import sys; print(sys.path)"

# 確保 src 目錄在路徑中（conftest.py 會處理）
```

### Q: Moto 相關錯誤

```bash
# 更新 moto
pip install --upgrade 'moto[all]'
```

## 🚀 下一步

- 閱讀 [完整測試指南](./README.md)
- 查看 [測試範例](./test_commands.py)
- 學習 [撰寫新測試](./README.md#撰寫新測試)

## 💡 專業技巧

### 1. 使用 pytest-watch 自動運行測試

```bash
pip install pytest-watch
ptw tests/e2e/ -- -v
```

### 2. 創建測試別名

在 `~/.bashrc` 或 `~/.zshrc` 添加：

```bash
alias test-e2e='cd telegram-lambda && pytest tests/e2e/ -v'
alias test-fast='cd telegram-lambda && pytest tests/e2e/ -m "not slow" -v'
alias test-cov='cd telegram-lambda && pytest tests/e2e/ --cov=src --cov-report=html'
```

### 3. VS Code 整合

安裝 Python Test Explorer 擴展，可以在 IDE 中直接運行和除錯測試。

---

**開始測試吧！** 🎉

如有問題，請查看 [README.md](./README.md) 或開 issue。