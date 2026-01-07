# 開發中功能文件

✅ **此目錄進入 Git 版本控制**（供多平台 agents 協作）

---

## 🎯 用途

存放正在開發中功能的文件，供不同平台的 agents 協作開發：
- 📋 開發進度追蹤
- 📝 開發筆記和設計決策
- 🧪 測試結果記錄
- 🐛 問題追蹤清單
- 💡 臨時想法和實驗

---

## 🤝 多 Agent 協作工作流

### 開始新功能
```bash
# 創建功能目錄
mkdir -p dev-in-progress/feature-name
cd dev-in-progress/feature-name

# 創建進度文件
cat > PROGRESS.md << 'EOF'
# Feature: [功能名稱]
**狀態**: 🔄 進行中  
**開始時間**: $(date +%Y-%m-%d)  
**負責 Agent**: [Your Agent ID]

## 📋 任務清單
- [ ] 任務 1
- [ ] 任務 2
- [ ] 任務 3

## 🎯 目標
[描述功能目標]

## 📝 開發筆記
[記錄關鍵決策和想法]
EOF

# 提交到 Git
git add .
git commit -m "feat: start [feature-name] development"
git push
```

### 協作開發
```bash
# 其他 agent 接手時
git pull  # 獲取最新進度

# 查看當前狀態
cat dev-in-progress/feature-name/PROGRESS.md

# 繼續開發並更新進度
# ... 進行開發 ...

# 更新 PROGRESS.md
# 標記完成的任務為 [x]
# 添加新的發現或問題

# 提交更新
git add .
git commit -m "feat([feature-name]): [your changes]"
git push
```

### 功能完成
```bash
# 1. 確認所有任務完成
# 2. 創建綜合報告
mkdir -p dev-reports/YYYY-MM-feature-name

# 3. 使用模板創建報告
cp dev-reports/TEMPLATE.md dev-reports/YYYY-MM-feature-name/REPORT.md

# 4. 整理內容到報告
# ... 編輯 REPORT.md，整合所有開發文件的關鍵信息 ...

# 5. 清理開發文件
rm -rf dev-in-progress/feature-name

# 6. 提交
git add .
git commit -m "docs: complete [feature-name] report"
git push
```

---

## 📂 建議的文件結構

```
dev-in-progress/feature-name/
├── PROGRESS.md              # ✅ 進度追蹤（必須）
├── notes.md                 # ✅ 開發筆記
├── design.md                # ✅ 設計文檔
├── test-results.md          # ✅ 測試記錄
├── issues.md                # ✅ 問題列表
├── decisions.md             # ✅ 技術決策
└── experiments.draft        # ❌ 個人實驗（不進 Git）
```

### 文件說明

**PROGRESS.md** （必須）
- 追蹤開發進度和任務完成狀態
- 記錄當前負責的 Agent
- 提供快速狀態概覽

**notes.md** （推薦）
- 開發過程中的想法和發現
- 技術細節和實現筆記
- 參考資料連結

**design.md** （推薦）
- 架構設計說明
- API 設計
- 數據結構設計

**test-results.md** （推薦）
- 測試執行記錄
- 測試覆蓋率
- 已知問題和 bug

**issues.md** （推薦）
- 待解決的問題清單
- 問題狀態追蹤
- 解決方案討論

**decisions.md** （推薦）
- 重要技術決策記錄
- 選擇某方案的原因
- 替代方案比較

---

## ⚠️ 注意事項

### ✅ 應該提交的文件
- 進度追蹤文件（PROGRESS.md）
- 設計文檔和筆記
- 測試結果記錄
- 問題追蹤清單
- 對其他 agents 有用的任何信息

### ❌ 不應提交的文件
- 個人草稿（使用 `.draft` 後綴）
- 本地測試臨時文件
- 個人的 scratchpad（使用 `.wip` 後綴）
- 敏感信息（應該用 `.env` 並加入 .gitignore）

### 文件命名規範
- ✅ 使用描述性名稱：`api-design.md`
- ✅ 使用 kebab-case：`test-results.md`
- ✅ 個人草稿：`scratch.draft`
- ❌ 避免：`temp.md`, `test.md`, `asdf.md`

---

## 🔄 清理策略

### 何時清理
功能開發完成並創建綜合報告後，應立即清理開發文件。

### 如何清理
```bash
# 1. 確認報告已創建
ls dev-reports/YYYY-MM-feature-name/REPORT.md

# 2. 刪除開發文件
rm -rf dev-in-progress/feature-name

# 3. 提交清理
git add .
git commit -m "chore: cleanup [feature-name] development files"
git push
```

### 不要保留
❌ 不要在 dev-in-progress/ 保留已完成功能的文件  
❌ 不要累積大量過期的開發記錄  
❌ 不要讓此目錄變成「歷史垃圾桶」

---

## 📊 當前開發狀態

**進行中的功能**: 0 個  
**最後更新**: 2026-01-07

```
dev-in-progress/
└── .gitkeep           # 保持目錄存在
```

---

## 💡 最佳實踐

### 1. **經常同步**
- 開始工作前：`git pull`
- 完成一個小任務後：`git commit && git push`
- 每天結束時：確保所有更改已提交

### 2. **清晰的 Commit 訊息**
```bash
# ✅ 好的範例
git commit -m "feat(search): implement basic search API"
git commit -m "fix(search): handle empty query case"
git commit -m "docs(search): add API usage examples"

# ❌ 不好的範例
git commit -m "update"
git commit -m "fix bug"
git commit -m "changes"
```

### 3. **保持 PROGRESS.md 更新**
- 每次完成任務後更新狀態
- 遇到問題時記錄在 PROGRESS.md
- 定期總結當前進度

### 4. **及時創建報告**
- 功能完成後立即創建報告
- 不要拖延報告撰寫
- 記憶新鮮時整理最準確

---

## 🎯 協作示例

### Agent A（Mac）開始功能
```bash
mkdir -p dev-in-progress/feature-search
echo "# Feature: Search" > dev-in-progress/feature-search/PROGRESS.md
git add . && git commit -m "feat: start search feature" && git push
```

### Agent B（Linux）繼續開發
```bash
git pull
cd dev-in-progress/feature-search
# ... 開發 ...
git add . && git commit -m "feat(search): add elasticsearch" && git push
```

### Agent C（Windows）完成功能
```bash
git pull
# ... 完成最後的任務 ...
# 創建報告
mkdir -p dev-reports/2026-01-search-feature
# ... 撰寫 REPORT.md ...
rm -rf dev-in-progress/feature-search
git add . && git commit -m "docs: complete search feature report" && git push
```

---

**最後更新**：2026-01-07  
**維護者**：AgentCoreNexus Team  
**協作模式**：✅ 多平台 multi-agent 協作
