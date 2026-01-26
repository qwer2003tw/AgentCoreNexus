# 測試快速參考

**在任何 commit/push 前必須執行！**

⚠️ **重要**：必須使用 **Python 3.12** 執行測試！

---

## ⚡ 一鍵測試（推薦）

```bash
make test        # 所有組件（5-8 分鐘）
make test-quick  # 跳過 Web E2E（2-3 分鐘）
```

或使用腳本：
```bash
./run_all_tests.sh          # 完整測試
./run_all_tests.sh --quick  # 快速測試
```

---

## 📦 組件測試

```bash
make test-agentcore   # AI 處理器
make test-lambda      # Webhook 接收器
make test-web         # Web 前端
make test-backend     # 所有後端組件
```

---

## 📊 覆蓋率

```bash
make coverage-report  # 查看所有組件覆蓋率
```

---

## 🚫 記住

- ✅ 提交前必須測試
- ✅ 新代碼覆蓋率 ≥ 80%
- ❌ 禁止使用 `git commit --no-verify`
- ❌ 禁止跳過任何步驟

---

## 📚 詳細說明

完整的測試規範、AI Agent 操作指南、故障排除，請參閱：
→ **`.clinerules/TESTING_STANDARDS.md`**

測試指南（面向開發者）：
→ `docs/TESTING.md`