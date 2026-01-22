# Infrastructure as Code 強制執行總結

**日期**: 2026-01-22  
**問題**: Agent 使用 `aws lambda update` 違反 IaC 原則  
**解決方案**: 四層防護體系

---

## 🎯 問題描述

**症狀**：
- Agent 在修改 Lambda 代碼後
- 使用 `aws lambda update-function-code` 等 CLI 命令
- 而不是使用 SAM 部署

**影響**：
- 違反 Infrastructure as Code 原則
- CloudFormation 狀態與實際不一致
- 下次 SAM deploy 可能覆蓋變更
- 無法追蹤和審計

---

## 💡 解決方案：四層防護

### 🛡️ 層次 1: PreToolUse Hook（技術阻止）⭐⭐⭐

**位置**: `.clinerules/hooks/PreToolUse`

**實施內容**：添加規則 6
```bash
# 檢測 aws lambda update-function-(code|configuration)
# 硬性阻止，返回 cancel: true
# 提供清晰的錯誤訊息和正確做法
```

**效果**：
- ✅ 100% 阻止違規命令
- ✅ 即時反饋
- ✅ 提供替代方案

**測試方式**：
```bash
# 嘗試執行（會被阻止）
aws lambda update-function-code --function-name test
```

---

### 📋 層次 2: Deployment IaC Rule（規範教育）⭐⭐⭐

**位置**: `.clinerules/rules/deployment-iac.md`

**內容**：
- 明確 IaC 核心原則
- 列出所有禁止的命令
- 說明為什麼重要
- AI Agent 的責任
- 常見場景與正確做法
- 無例外條款

**特點**：
- `always_active: true`（始終活動）
- `priority: critical`（最高優先級）
- `enforcement: strict`（嚴格執行）

---

### 📝 層次 3: Best Practices 更新（指導文檔）⭐⭐

**位置**: `.clinerules/deployment/lambda-development-best-practices.md`

**修改**：
- ❌ 移除「例外情況」章節
- ✅ 改為「絕無例外」
- ⚠️ 強化語氣和要求
- 🔗 引用新的 deployment-iac.md rule

---

### 🔧 層次 4: Workflow 修正（實用工具）⭐

**位置**: `.clinerules/workflows/deploy-lambda.md`

**修改**：
- ❌ 移除「問題 2」中的 aws lambda update 建議
- ✅ 改為使用 SAM 清除緩存
- ⚠️ 明確標記不要使用 aws lambda update

---

## 📊 防護機制對比

| 層次 | 類型 | 強度 | 觸發時機 | 效果 |
|------|------|------|----------|------|
| PreToolUse Hook | 技術阻止 | ⭐⭐⭐ | 命令執行前 | 直接阻止 |
| IaC Rule | 規範教育 | ⭐⭐⭐ | 始終活動 | AI 理解規範 |
| Best Practices | 詳細指導 | ⭐⭐ | AI 參考 | 提供正確方法 |
| Workflow | 實用工具 | ⭐ | 手動調用 | 自動化正確流程 |

---

## 🎯 預期效果

### 防護效果
- ✅ **100% 阻止**違規命令（Hook）
- ✅ **持續教育** AI 遵守 IaC（Rule）
- ✅ **提供工具**簡化正確操作（Workflow）
- ✅ **詳細指導**理解最佳實踐（Docs）

### 用戶體驗
- ✅ Agent 不會再違規
- ✅ 清晰的錯誤訊息告知原因
- ✅ 立即提供正確替代方案
- ✅ 學習並理解 IaC 重要性

---

## 🧪 測試驗證

### 必須測試的項目

1. **Hook 阻止測試**
   ```
   嘗試：aws lambda update-function-code --function-name test
   預期：被 Hook 阻止，顯示錯誤訊息
   ```

2. **Rule 教育測試**
   ```
   詢問 AI：「如何快速更新 Lambda？」
   預期：AI 回答使用 SAM，不提及 aws lambda update
   ```

3. **Workflow 正確性**
   ```
   執行：/deploy-lambda.md
   驗證：只使用 SAM 命令，無 aws lambda update
   ```

---

## 📚 相關文檔位置

### 新增/更新的文件
1. `.clinerules/rules/deployment-iac.md` ⭐ 新增
2. `.clinerules/hooks/PreToolUse` 📝 更新（添加規則 6）
3. `.clinerules/deployment/lambda-development-best-practices.md` 📝 更新
4. `.clinerules/workflows/deploy-lambda.md` 📝 更新

### 參考文檔
- `.clinerules/deployment/stack-management-best-practices.md`
- `docs/deployment-guide.md`
- `docs/STACK_MANAGEMENT.md`

---

## 🏆 關鍵成功因素

1. **技術強制**
   - PreToolUse Hook 提供硬性阻止
   - 無法繞過，100% 有效

2. **多層防護**
   - Rule + Hook + Docs + Workflow
   - 即使一層失效，其他層仍保護

3. **無例外條款**
   - 移除所有「緊急情況」的藉口
   - 堅持原則，不妥協

4. **清晰指導**
   - 不只說「不要」
   - 還說「應該怎麼做」

---

## ⚠️ 常見問題處理

### Q: 如果真的很緊急怎麼辦？
**A**: SAM 也很快（2-5 分鐘）。使用 `--no-confirm-changeset` 跳過確認即可。

### Q: Lambda 緩存問題需要 update 嗎？
**A**: 不需要。使用 `rm -rf .aws-sam && sam build --use-container` 解決。

### Q: 用戶堅持要用 aws lambda update？
**A**: 用戶可以手動執行（不透過 Cline），但 Cline 始終遵守 IaC。

---

## 📈 成功指標

### 技術指標
- [ ] Agent 0 次使用 aws lambda update
- [ ] PreToolUse Hook 成功攔截嘗試
- [ ] 所有部署通過 SAM

### 質量指標
- [ ] CloudFormation 狀態始終一致
- [ ] Git 記錄所有變更
- [ ] 團隊協作順暢

---

## 🔄 持續改進

### 短期監控（1-2 週）
- [ ] 觀察 Hook 攔截次數
- [ ] 收集 Agent 反饋
- [ ] 調整錯誤訊息（如需要）

### 長期優化
- [ ] 根據實際使用調整規則
- [ ] 添加更多違規模式檢測
- [ ] 優化錯誤訊息清晰度

---

**總結版本**: v1.0  
**完成日期**: 2026-01-22  
**維護者**: AgentCoreNexus Team

**結論**: 通過四層防護，徹底解決 Agent 違反 IaC 的問題。技術阻止 + 規範教育 + 工具支持，確保 100% 合規！