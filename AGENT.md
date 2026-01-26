# AGENT 工作規範（摘錄自 .clinerules）

本文件是給 AI Agent 的「快速工作手冊」，內容整理自 `.clinerules/` 的正式規範。**如有歧異，以 `.clinerules/` 內容為準。**

## ✅ 必讀來源

- `.clinerules/README.md`：規則目錄說明與定位
- `.clinerules/DOCUMENTATION_WORKFLOW.md`：文檔生命週期與整理規範
- `.clinerules/CODE_QUALITY_WORKFLOW.md`：Ruff 代碼質量工作流（強制）
- `.clinerules/TESTING_STANDARDS.md`：測試標準與覆蓋率要求（強制）
- `.clinerules/QUICK_REFERENCE.md`：常用測試指令速查

## 📂 文檔與資料夾整理規範

- **docs/**：核心文檔（長期保留，持續更新）。
- **dev-in-progress/**：開發中資料（必須進 Git，需有 `PROGRESS.md`）。
- **dev-reports/**：功能完成後的綜合報告（使用 `TEMPLATE.md`）。
- **.clinerules/**：AI Agent 規則與工作流（禁止放報告/草稿）。

**文檔生命週期：**
```
開發中 → dev-in-progress/
完成後 → dev-reports/
清理 → 刪除 dev-in-progress/ 中該功能資料
```

## 🧹 文檔整理基本要求

- 開發中必須建立 `PROGRESS.md` 並持續更新。
- 功能完成後必須撰寫 `dev-reports/YYYY-MM-feature-name/REPORT.md`。
- 報告完成後，**必須清理**對應的 `dev-in-progress/feature-name/`。
- 不要在 `.clinerules/` 放報告或臨時文檔。

## 🛡️ Code Quality（強制）

**任何 commit/push 前必須完成 Ruff 檢查**：

```bash
ruff check . --fix
ruff format .
ruff check .
```

- 禁止使用 `git commit --no-verify`。
- 禁止只檢查部分文件（必須全專案）。

## 🧪 Testing 標準（強制）

- **Python 3.12** 執行測試（Lambda Runtime 一致）。
- **新代碼覆蓋率 ≥ 80%**（強制）。
- 建議使用一鍵測試：

```bash
make test
# 或
./run_all_tests.sh
```

## 🚫 禁止行為（節錄）

- 跳過 Ruff 檢查或測試就提交。
- 提交後再補「fix lint / fix tests」。
- 降低覆蓋率門檻或忽略測試失敗。

## 🔗 延伸閱讀

- `docs/README.md`：完整文檔索引
- `docs/TESTING.md`：測試細節（面向開發者）
- `docs/CODE_QUALITY.md`：Ruff 使用與規範

---

**最後更新**：2026-01-12（同步 .clinerules 版本）
