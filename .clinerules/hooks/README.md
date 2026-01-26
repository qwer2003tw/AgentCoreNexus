# Hooks 目錄說明

此目錄包含兩種不同類型的 hooks：**Git Hooks** 和 **Cline Hooks**。

---

## 🔀 兩種 Hooks 的區別

### Git Hooks（傳統）

**文件**: `pre-commit`（Git 自動使用）

**觸發時機**: Git commit 時  
**用途**: 在代碼提交前執行質量檢查  
**執行內容**:
- Ruff 代碼質量檢查
- 單元測試
- E2E 測試
- 覆蓋率檢查

**特點**:
- ✅ 強制執行（commit 時自動觸發）
- ✅ 保護代碼庫質量
- ✅ 防止不合格代碼進入版本控制

**安裝方式**:
```bash
./setup-hooks.sh
```

---

### Cline Hooks（新功能）⭐

**文件**: `PreToolUse`, `TaskStart`, `PostToolUse`（Cline 使用）

**觸發時機**: Cline AI 操作時  
**用途**: 在 AI 工作流中注入邏輯和驗證

#### PreToolUse（操作前驗證）
**觸發**: Cline 使用工具前（如 write_file, execute_command）  
**用途**: 
- 阻止錯誤操作（如在 Python 專案創建 .ts 文件）
- 驗證參數
- 注入警告上下文

**範例規則**:
- ❌ 阻止在 Python 專案創建 TypeScript 文件
- ⚠️ 警告測試文件使用 print()
- ⚠️ 提醒測試命令使用 python3.12

---

#### TaskStart（任務開始注入）
**觸發**: 開始新任務時  
**用途**:
- 自動檢測專案類型
- 注入專案規範
- 提供可用工具信息

**注入信息**:
- 專案類型（AgentCoreNexus）
- 當前組件（receiver/processor/web）
- 技術棧（Python 3.12, React 等）
- 可用的 workflows
- Git 狀態

---

#### PostToolUse（操作後學習）
**觸發**: Cline 使用工具後  
**用途**:
- 監控性能（慢操作警告）
- 學習修改模式
- 提供後續建議

**監控內容**:
- 操作執行時間（> 5秒 警告）
- 文件修改類型（handler, template, requirements）
- 命令執行成功/失敗
- 提供相關建議

---

## 🎯 兩者如何協作

```
用戶開始任務
    ↓
TaskStart Hook 觸發 → 注入專案上下文
    ↓
用戶/AI 操作文件
    ↓
PreToolUse Hook → 驗證操作（如創建文件）
    ↓
操作執行
    ↓
PostToolUse Hook → 監控和建議（如提醒測試）
    ↓
... 繼續工作 ...
    ↓
用戶執行 git commit
    ↓
Git pre-commit Hook → 強制質量檢查
    ↓
Commit 完成
```

**協同效果**:
- Cline Hooks = 開發過程中的實時指導
- Git Hooks = 提交前的最後防線

---

## 📂 目錄結構

```
.clinerules/hooks/
├── README.md         # 本說明文件
│
├── pre-commit        # Git Hook（Git 使用）
│                     # 在 git commit 時觸發
│                     # 執行質量檢查和測試
│
├── PreToolUse        # Cline Hook（Cline 使用）
│                     # 在工具執行前觸發
│                     # 驗證操作和阻止錯誤
│
├── TaskStart         # Cline Hook（Cline 使用）
│                     # 在任務開始時觸發
│                     # 注入專案上下文
│
└── PostToolUse       # Cline Hook（Cline 使用）
                      # 在工具執行後觸發
                      # 監控和提供建議
```

---

## 🔧 啟用和管理

### Git Hooks

**安裝** (一次性設置):
```bash
./setup-hooks.sh
```

**檢查狀態**:
```bash
ls -la .git/hooks/pre-commit
```

**臨時跳過** (不推薦):
```bash
git commit --no-verify
```

---

### Cline Hooks

**啟用方式**:
1. 在 Cline 設置中啟用 Hooks 功能
2. Hooks 會自動被 Cline 發現和使用
3. 可在 Cline UI 的 Hooks 面板中管理

**查看狀態**:
- 在 Cline 中打開 Hooks 面板
- 查看每個 hook 的啟用狀態
- 可以切換開關來啟用/禁用

**修改 Hook**:
- 直接編輯 `.clinerules/hooks/PreToolUse` 等文件
- Cline 會自動重新載入
- 確保文件有執行權限（`chmod +x`）

---

## 🎓 開發指南

### 修改現有 Hook

1. 編輯對應的 hook 文件
2. 測試修改（觸發相應操作）
3. 確保 JSON 輸出格式正確

**JSON 格式**:
```json
{
  "cancel": false,
  "contextModification": "YOUR_CONTEXT",
  "errorMessage": "ERROR_IF_BLOCKING"
}
```

---

### 添加新的 Cline Hook

**可用的 Hook 類型**:
- PreToolUse - 工具執行前
- PostToolUse - 工具執行後
- TaskStart - 任務開始
- TaskResume - 任務恢復
- TaskCancel - 任務取消
- TaskComplete - 任務完成
- UserPromptSubmit - 用戶提交輸入

**創建步驟**:
1. 創建文件：`.clinerules/hooks/[HookType]`（無擴展名）
2. 添加 shebang：`#!/usr/bin/env bash`
3. 實現邏輯（接收 JSON，返回 JSON）
4. 設置執行權限：`chmod +x`

---

## 📚 參考資料

### Cline 官方文檔
- [Hooks Overview](https://docs.cline.bot/features/hooks)
- [Hook Reference](https://docs.cline.bot/features/hooks/hook-reference)
- [Hook Samples](https://docs.cline.bot/features/hooks/samples)

### 專案文檔
- `setup-hooks.sh` - Git hooks 安裝腳本
- `.clinerules/rules/` - 始終活動的規則
- `.clinerules/workflows/` - 手動調用的任務腳本

---

## 💡 最佳實踐

### 設計 Hook 時

**應該做**:
- ✅ 提供清晰的錯誤訊息
- ✅ 使用描述性的上下文前綴（PERFORMANCE:, TESTING: 等）
- ✅ 考慮性能（hooks 有 30 秒超時）
- ✅ 處理邊界情況

**避免**:
- ❌ 過於嚴格（阻止所有操作）
- ❌ 模糊的錯誤訊息
- ❌ 長時間運行的操作
- ❌ 依賴不穩定的外部服務

---

### 測試 Hook

**手動測試**:
```bash
# 模擬 Cline 輸入
echo '{
  "clineVersion": "1.0.0",
  "hookName": "PreToolUse",
  "preToolUse": {
    "toolName": "write_to_file",
    "parameters": {"path": "test.ts"}
  }
}' | .clinerules/hooks/PreToolUse
```

**在實際使用中測試**:
- 嘗試觸發 hook 的操作
- 檢查 Cline UI 中的 hook 執行狀態
- 驗證上下文注入是否有效

---

## ⚠️ 注意事項

### 安全性
- Hooks 以 VS Code 權限執行
- 可以訪問整個文件系統
- 謹慎對待從不信任來源的 hooks

### 維護
- 定期檢查 hooks 是否仍然適用
- 根據專案演進更新規則
- 記錄重要的修改

### 故障排除
- 如果 hook 失敗，Cline 會繼續執行（不會中斷任務）
- 只有 `"cancel": true` 才會阻止操作
- 檢查 Cline UI 的 Hooks 面板查看執行狀態

---

**目錄版本**: v1.0  
**最後更新**: 2026-01-14  
**維護者**: AgentCoreNexus Team

**重要提醒**: 這兩種 hooks 互補而非替代，共同確保代碼質量！