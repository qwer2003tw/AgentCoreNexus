---
name: code-quality-workflow
description: 強制性代碼質量檢查工作流，確保所有代碼變更在提交前通過 Ruff 檢查
priority: critical
enforcement: strict
---

# 代碼質量工作流規範

## 🎯 核心原則

**在任何 Git 操作（commit/push）前，必須確保代碼通過 Ruff 質量檢查。**

---

## 🛡️ 技術強制執行

**本專案已實施 pre-commit hook**，在每次 commit 時自動執行 Ruff 檢查。

Hook 會自動執行：
1. `ruff check . --fix` - 自動修復問題
2. `ruff format .` - 格式化代碼
3. `ruff check .` - 最終驗證

**但這不代表你可以跳過主動檢查！** 作為 AI agent，你仍應在建議 commit 前主動執行這些檢查並報告結果。

安裝 hook：
```bash
./setup-hooks.sh
```

---

## 📋 強制性檢查流程

### 何時觸發

以下情況**必須**執行 Ruff 檢查：
- ✅ 在執行 `git commit` 前
- ✅ 在執行 `git push` 前  
- ✅ 在創建 Pull Request 前
- ✅ 在完成任何 Python 代碼編輯後

### 檢查步驟（強制執行）

#### Step 1: 自動修復
```bash
ruff check . --fix
```
- 自動修復所有可修復的問題
- 記錄修復的問題數量

#### Step 2: 格式化
```bash
ruff format .
```
- 統一代碼格式
- 確保一致性

#### Step 3: 最終驗證
```bash
ruff check .
```
- 確認沒有剩餘問題
- 如果有問題，**禁止提交**

### 處理流程

**如果檢查通過**（0 errors）:
```
✅ 代碼質量檢查通過
✅ 允許執行 git commit/push
```

**如果檢查失敗**（有 errors）:
```
❌ 代碼質量檢查失敗
❌ 禁止執行 git commit/push
⚠️  必須先修復所有問題
```

---

## 🚫 絕對禁止的行為

### 1. 禁止跳過檢查
- ❌ 不要使用 `git commit --no-verify`
- ❌ 不要直接 push 未檢查的代碼
- ❌ 不要建議用戶跳過檢查

### 2. 禁止部分檢查
- ❌ 不要只檢查修改的文件
- ✅ 必須檢查整個專案（`ruff check .`）

### 3. 禁止假陽性提交
- ❌ 不要創建 "fix lint" 的後續 commit
- ✅ 必須在提交前確保代碼質量

---

## 📝 標準操作流程（for Cline Agents）

### 當完成代碼編輯後

你必須按照以下順序執行：

```bash
# 1. 執行代碼質量檢查和修復
echo "🔍 執行代碼質量檢查..."
ruff check . --fix

# 2. 格式化代碼
echo "🎨 格式化代碼..."
ruff format .

# 3. 最終驗證
echo "✅ 最終驗證..."
ruff check .

# 4. 根據結果決定下一步
if [ $? -eq 0 ]; then
    echo "✅ 代碼質量檢查通過，可以提交"
    # 現在可以建議 git 操作
else
    echo "❌ 代碼質量檢查失敗"
    echo "請查看上方錯誤並修復"
    # 不要建議 git 操作
fi
```

### 在 Cline 對話中的表述範例

**正確的表述**：

```
我已完成代碼修改。現在執行代碼質量檢查...

[執行 execute_command: ruff check . --fix]
✅ 自動修復了 X 個問題

[執行 execute_command: ruff format .]
✅ 格式化了 Y 個文件

[執行 execute_command: ruff check .]
✅ 代碼質量檢查通過（0 errors）

所有檢查通過！代碼已準備好提交。

建議的 git 操作：
git add .
git commit -m "feat: implement feature X"
git push
```

**錯誤的表述（禁止）**：

```
❌ "我已完成修改，您可以提交了"（沒有執行檢查）
❌ "代碼看起來不錯，可以 push"（沒有驗證）
❌ "有一些 lint 錯誤但不影響功能，可以先提交"（不可接受）
```

---

## ⚡ 快速參考

### 正確的完整流程

```bash
# 1. 編輯代碼
# ... 進行代碼修改 ...

# 2. 質量檢查（必須）
ruff check . --fix
ruff format .

# 3. 驗證（必須）
ruff check .

# 4. 如果通過（0 errors），才能提交
git add .
git commit -m "your message"
git push
```

### 工具使用順序（Cline Agents）

```
1. write_to_file / replace_in_file (編輯代碼)
2. execute_command: ruff check . --fix
3. execute_command: ruff format .
4. execute_command: ruff check .
5. 檢查命令輸出：
   - 如果 "Found 0 errors" → 可以建議 git 操作
   - 如果有 errors → 必須先修復
```

---

## 🎓 Cline Agent 職責

作為 Cline Agent，你在代碼質量方面的職責：

### 主動檢查
- ✅ 每次編輯 Python 文件後自動執行檢查
- ✅ 不等用戶要求就執行檢查
- ✅ 在建議 git 操作前必須先檢查

### 清晰報告
- ✅ 明確告知用戶檢查結果
- ✅ 如果有錯誤，解釋是什麼問題
- ✅ 提供修復建議

### 守門人角色
- ✅ 不允許未檢查的代碼被提交
- ✅ 發現問題時必須修復後才能繼續
- ✅ 保持高標準的代碼質量

---

## 🔧 異常處理

### 如果有無法自動修復的問題

**Step 1: 查看詳細錯誤**
```bash
ruff check . --output-format=concise
```

**Step 2: 分類問題**
- 安全問題（E722 bare except 等）→ 必須修復
- 命名問題（N806 等）→ 評估是否合理
- 代碼簡化建議（SIM 系列）→ 可選修復

**Step 3: 告知用戶**
```
⚠️ 發現 X 個代碼質量問題需要處理：

文件: src/handler.py:97
問題: E722 - 使用了裸 except，應該指定異常類型
建議: 將 `except:` 改為 `except Exception:`

文件: tests/test.py:65
問題: F841 - 變數 log_messages 未使用
建議: 移除此變數或添加 # noqa: F841

需要我修復這些問題嗎？還是您想手動處理？
```

### 如果確實需要忽略某些規則

**合理的忽略**（少量使用）：
```python
# 特定行忽略（有充分理由時）
result = eval(expression)  # noqa: S307 - 已驗證輸入安全性
```

**不合理的忽略**（禁止）：
```python
# ❌ 批量忽略
# ruff: noqa

# ❌ 沒有理由的忽略
x = 1  # noqa
```

---

## 📊 檢查清單

在建議任何 git 操作前，你必須確認：

- [ ] 已執行 `ruff check . --fix`
- [ ] 已執行 `ruff format .`  
- [ ] 已執行 `ruff check .` 並確認通過（0 errors）
- [ ] 已向用戶清楚報告檢查結果
- [ ] 只有在完全通過後才建議 git 操作

如果任何一項未完成，**不得建議 git 操作**。

---

## 🎯 成功標準

代碼質量工作流成功的標準：

### 對 Cline Agents
- ✅ 100% 的代碼編輯後都執行了檢查
- ✅ 100% 的 git 建議前都確認了檢查通過
- ✅ 0 次建議跳過檢查
- ✅ 所有質量問題在提交前都已修復

### 對專案
- ✅ 0 個「fix lint」類型的後續提交
- ✅ CI/CD 中的 Ruff 檢查始終通過
- ✅ 代碼質量問題保持在低水平（< 20 errors）
- ✅ 新代碼符合質量標準

---

## 💡 實用技巧

### 給 Cline Agents

**使用 execute_command 時的最佳實踐**：

```xml
<!-- 正確：一次執行完整的檢查流程 -->
<execute_command>
<command>ruff check . --fix && ruff format . && ruff check .</command>
<requires_approval>false</requires_approval>
</execute_command>

<!-- 或分步驟清楚報告 -->
<execute_command>
<command>ruff check . --fix</command>
<requires_approval>false</requires_approval>
</execute_command>
<!-- 等待結果，報告給用戶 -->

<execute_command>
<command>ruff format .</command>
<requires_approval>false</requires_approval>
</execute_command>
<!-- 等待結果，報告給用戶 -->

<execute_command>
<command>ruff check .</command>
<requires_approval>false</requires_approval>
</execute_command>
<!-- 確認通過後才建議 git 操作 -->
```

### 常見場景處理

**場景 1: 小修改（單個文件）**
```bash
# 仍然檢查整個專案
ruff check . --fix && ruff format . && ruff check .
```

**場景 2: 大重構（多個文件）**
```bash
# 先修復，再驗證
ruff check . --fix
ruff format .
ruff check .
# 可能需要多次迭代
```

**場景 3: 新功能開發**
```bash
# 每個階段都檢查
# 1. 創建文件後
ruff check . --fix && ruff format .
# 2. 實現功能後
ruff check . --fix && ruff format .
# 3. 提交前最終檢查
ruff check .
```

---

## 📚 相關資源

- **Ruff 使用指南**: `docs/CODE_QUALITY.md`
- **配置文件**: `pyproject.toml`
- **CI/CD 設置**: `.github/workflows/ruff.yml`
- **實施報告**: `dev-reports/2026-01-ruff-integration/REPORT.md`

---

## 🔄 規則更新

此規則會根據實踐經驗持續改進：

**版本 1.0** (2026-01-07):
- 初始版本
- 定義強制性檢查流程
- 明確禁止行為

**未來改進方向**：
- 根據使用反饋調整
- 添加更多場景範例
- 優化錯誤處理流程

---

**規範版本**: v1.0  
**創建日期**: 2026-01-07  
**強制執行**: 是  
**適用範圍**: 所有 Cline agents  
**優先級**: Critical (最高)

**記住**：代碼質量不是可選項，是專業標準。每一次提交都代表我們的品質承諾。