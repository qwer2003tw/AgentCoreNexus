---
name: deployment-iac
description: 強制 Infrastructure as Code，所有基礎設施變更必須通過 SAM/CloudFormation
priority: critical
enforcement: strict
always_active: true
---

# Deployment Infrastructure as Code Rules

**這是始終活動的規則** - 所有 AWS 基礎設施部署必須遵守 IaC 原則。

## 🎯 核心原則

**所有 AWS 基礎設施變更必須通過 SAM（Serverless Application Model）或 CloudFormation。**

**絕無例外** - 無論任何情況，都不使用 AWS CLI 直接更新資源。

---

## 🚫 絕對禁止的命令

### Lambda 部署相關（最常見違規）

❌ `aws lambda update-function-code`  
❌ `aws lambda update-function-configuration`  
❌ `aws lambda publish-version`  
❌ `aws lambda create-alias`  
❌ `aws lambda update-alias`  
❌ `aws lambda put-function-concurrency`

### 其他 AWS 服務（同樣禁止）

❌ `aws dynamodb create-table`（手動創建資源）  
❌ `aws s3api put-bucket-*`（手動配置 S3）  
❌ `aws events put-rule`（手動創建 EventBridge 規則）  
❌ `aws iam create-role`（手動創建 IAM）  
❌ `aws apigateway *`（手動配置 API Gateway）

### 為什麼這些命令被禁止？

1. **狀態不一致**
   - CloudFormation 不知道這些變更
   - 產生 configuration drift
   - 下次 SAM deploy 可能覆蓋或衝突

2. **無法追蹤**
   - Git 中看不到變更
   - 無法審計誰做了什麼
   - 團隊其他成員不知道

3. **無法回滾**
   - 出問題無法快速恢復
   - 需要手動修復

4. **破壞自動化**
   - CI/CD 無法複製
   - 環境不一致

---

## ✅ 允許的命令（查詢/監控）

### Lambda 相關

✅ `aws lambda get-function`（查詢配置）  
✅ `aws lambda get-function-configuration`（查看設置）  
✅ `aws lambda list-functions`（列出函數）  
✅ `aws lambda wait function-updated`（等待更新完成）  
✅ `aws lambda invoke`（測試調用）

### 日誌和監控

✅ `aws logs tail`（查看日誌）  
✅ `aws logs filter-log-events`（搜索日誌）  
✅ `aws cloudwatch get-metric-statistics`（查看指標）

### CloudFormation

✅ `aws cloudformation describe-stacks`（查詢 stack）  
✅ `aws cloudformation list-stacks`（列出 stacks）  
✅ `aws cloudformation get-template`（查看 template）

**原則**：查詢和監控可以，但任何變更都必須通過 SAM。

---

## 📝 正確的部署流程

### 標準流程（所有情況都適用）

#### 1. 修改代碼或配置

```bash
# 編輯 Lambda handler
vim src/handler.py

# 或修改 template.yaml
vim template.yaml
```

---

#### 2. 執行測試（強制）

```bash
# 使用 Workflow（推薦）
/test-full.md

# 或手動
make test
```

**要求**：
- ✅ 所有測試通過
- ✅ 代碼質量檢查通過
- ✅ 覆蓋率達標

---

#### 3. SAM 部署（唯一方法）

```bash
# 使用 Workflow（推薦）
/deploy-lambda.md

# 或手動
cd [component-directory]
sam build
sam deploy --stack-name STACK_NAME \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --region us-west-2
```

---

#### 4. 驗證部署（必須）

```bash
# 使用 Workflow
/check-status.md

# 或手動檢查
aws lambda get-function --function-name FUNCTION_NAME \
  --query 'Configuration.{State:State,LastUpdateStatus:LastUpdateStatus}'
```

---

## 🚨 常見違規場景與正確做法

### 場景 1: 修改 Lambda 代碼

**❌ 錯誤（被 Hook 阻止）**：
```bash
aws lambda update-function-code \
  --function-name my-function \
  --s3-bucket bucket \
  --s3-key key
```

**✅ 正確**：
```bash
# 1. 修改代碼
# 2. 測試
make test
# 3. SAM 部署
sam build && sam deploy
```

---

### 場景 2: 更新環境變數

**❌ 錯誤（被 Hook 阻止）**：
```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --environment "Variables={KEY=value}"
```

**✅ 正確**：
```yaml
# 1. 修改 template.yaml
Environment:
  Variables:
    KEY: value

# 2. SAM 部署
sam deploy
```

---

### 場景 3: 更新 IAM 權限

**❌ 錯誤**：
```bash
aws iam attach-role-policy \
  --role-name lambda-role \
  --policy-arn arn:aws:iam::...
```

**✅ 正確**：
```yaml
# 修改 template.yaml
Policies:
  - Statement:
      - Effect: Allow
        Action: s3:GetObject
        Resource: '*'

# SAM 部署
sam deploy
```

---

### 場景 4: Lambda 緩存問題

**❌ 錯誤思維**：
> "Lambda 還在用舊代碼，我用 aws lambda update 強制更新"

**✅ 正確做法**：
```bash
# 清除 SAM 緩存
rm -rf .aws-sam
sam build --use-container
sam deploy

# 或等待 Lambda 自動更新（幾分鐘內）
```

---

### 場景 5: 「緊急修復」

**❌ 錯誤藉口**：
> "這是緊急情況，來不及 SAM deploy"

**✅ 正確認知**：
- SAM deploy 也很快（2-5 分鐘）
- 緊急情況更需要 IaC（可追蹤、可回滾）
- 使用 `--no-confirm-changeset` 跳過確認
- **絕不**因為「緊急」就違反 IaC

**如果真的超級緊急**：
- 用戶可以手動執行（不透過 Cline）
- 但之後**必須**補 SAM deploy
- Cline 始終遵守 IaC，無例外

---

## 🤖 AI Agent 的責任

作為 Cline Agent，你必須：

### 絕對禁止

- ❌ **永遠不要**建議使用 `aws lambda update-*`
- ❌ **永遠不要**執行繞過 SAM 的命令
- ❌ **永遠不要**說「快速更新可以用 aws lambda...」
- ❌ **永遠不要**因為「緊急」就妥協

### 必須做到

- ✅ **始終**使用 SAM 進行部署
- ✅ **主動**建議使用 `/deploy-lambda.md` workflow
- ✅ 部署前**確保**測試通過
- ✅ 部署後**驗證**狀態正常
- ✅ 遇到緊急情況仍然堅持 SAM

### 正確的表述

**✅ 正確**：
```
我已完成代碼修改並測試通過。

現在使用 SAM 部署到 AWS：
/deploy-lambda.md

或手動執行：
cd ai-processor
sam build
sam deploy --stack-name agentcore-ai-processor --region us-west-2
```

**❌ 禁止**：
```
「我用 aws lambda update 快速更新...」
「緊急情況先用 CLI 更新，之後再 SAM...」
「清除緩存需要 aws lambda update...」
```

---

## 📊 檢查清單

部署前確認：

- [ ] 代碼已修改完成
- [ ] 所有測試通過
- [ ] 使用 SAM build
- [ ] 使用 SAM deploy（**不是** aws lambda update）
- [ ] template.yaml 包含所有變更

部署後驗證：

- [ ] CloudFormation stack 狀態正常
- [ ] Lambda 函數狀態 Active
- [ ] 最近日誌無錯誤
- [ ] 配置符合 template.yaml

---

## 🎯 為什麼 IaC 如此重要？

### 1. 團隊協作

**場景**：
```
Agent A: 用 aws lambda update 改了配置
Agent B: 不知道這個變更
Agent B: SAM deploy 覆蓋了 A 的變更
結果: 配置丟失，功能損壞
```

**IaC 解決**：
- 所有變更在 template.yaml
- Git 追蹤和審查
- 團隊同步狀態

---

### 2. 環境一致性

**場景**：
```
開發環境: 用 SAM deploy
測試環境: 用 aws lambda update 改了配置
生產環境: 用 SAM deploy（但配置不同）
結果: 三個環境行為不一致
```

**IaC 解決**：
- 相同的 template.yaml
- 只有參數不同
- 保證一致性

---

### 3. 災難恢復

**場景**：
```
生產環境掛了，需要重建
但: 部分配置是手動改的
結果: 不知道如何完整恢復
```

**IaC 解決**：
- template.yaml 是唯一真相
- 一個命令完整重建
- 有信心恢復

---

### 4. 審計和合規

**場景**：
```
審計: 「這個權限是誰加的？何時？為什麼？」
沒有 IaC: 不知道，可能是手動加的
```

**IaC 解決**：
- Git commit 記錄一切
- 可以追蹤每個變更
- 符合合規要求

---

## 💡 實用技巧

### SAM 部署優化

**快速部署**（跳過確認）：
```bash
sam deploy --stack-name STACK --no-confirm-changeset
```

**並行部署多個 stack**：
```bash
# Terminal 1
cd telegram-adapter && sam deploy &

# Terminal 2
cd ai-processor && sam deploy &

# 等待兩者完成
wait
```

**增量部署**（只更新代碼）：
```bash
sam build
sam deploy --stack-name STACK --no-execute-changeset
# 檢查 changeset，如果只是代碼更新就執行
```

---

### 緊急情況處理

**如果真的很緊急**：

1. 仍然用 SAM，但加速：
```bash
sam build
sam deploy --stack-name STACK \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset
```

2. 如果是配置錯誤，回滾：
```bash
aws cloudformation cancel-update-stack --stack-name STACK
```

3. 如果必須繞過（極罕見）：
   - 用戶手動執行（不透過 Cline）
   - 立即記錄變更
   - 馬上補 SAM deploy

---

## 📚 相關資源

### Rules 和 Workflows
- `.clinerules/workflows/deploy-lambda.md` - 標準部署流程
- `.clinerules/workflows/check-status.md` - 部署後驗證

### 文檔
- `.clinerules/deployment/lambda-development-best-practices.md` - 詳細最佳實踐
- `.clinerules/deployment/stack-management-best-practices.md` - Stack 管理
- `docs/deployment-guide.md` - 完整部署指南

### 技術強制
- `.clinerules/hooks/PreToolUse` - Hook 會阻止違規命令

---

## 🎓 成功案例

### 正確的工作流程

```
1. Agent 修改 Lambda 代碼
   ↓
2. Agent 執行測試（/test-full.md）
   ↓
3. Agent 使用 SAM 部署（/deploy-lambda.md）
   ↓
4. Agent 驗證部署（/check-status.md）
   ↓
5. ✅ 所有變更在 Git 中，狀態一致
```

### 錯誤會被阻止

```
1. Agent 修改 Lambda 代碼
   ↓
2. Agent 嘗試 aws lambda update-function-code
   ↓
3. ⛔ PreToolUse Hook 阻止
   ↓
4. 顯示錯誤訊息和正確做法
   ↓
5. Agent 改用 SAM deploy
```

---

## ⚠️ 違規後果

如果繞過 IaC：

### 短期影響
- CloudFormation drift（狀態不一致）
- 其他成員不知道變更
- 可能在下次部署時丟失

### 長期影響
- 養成壞習慣
- 增加維護成本
- 團隊協作困難
- 合規問題

### 實際案例
```
場景: Agent 用 aws lambda update 改了配置
結果: 另一個 Agent SAM deploy 覆蓋了變更
影響: 功能損壞，用戶受影響
教訓: 必須始終使用 IaC
```

---

## 🔧 技術強制執行

### PreToolUse Hook

**位置**: `.clinerules/hooks/PreToolUse`

**功能**: 規則 6 會自動檢測並阻止所有 `aws lambda update-*` 命令

**效果**:
- ✅ 100% 阻止違規
- ✅ 即時反饋
- ✅ 提供正確方案

**測試**:
```bash
# 嘗試執行（會被阻止）
aws lambda update-function-code --function-name test

# Hook 會顯示詳細的錯誤訊息
```

---

## 💡 為什麼不允許「緊急例外」？

### 常見藉口

❌ "這是緊急 bug 修復"  
❌ "用戶在等，SAM 太慢"  
❌ "只是清除緩存"  
❌ "這次特殊，下次用 SAM"

### 為什麼都不成立

**SAM 也很快**：
- `sam deploy` 通常 2-5 分鐘
- 使用 `--no-confirm-changeset` 更快
- 並行部署多個 stack

**緊急情況更需要 IaC**：
- 可以快速回滾
- 有完整的變更記錄
- 不會讓情況更糟

**「清除緩存」不是藉口**：
- `rm -rf .aws-sam && sam build` 也能清除
- 不需要 aws lambda update

**「只是一次」的問題**：
- 一次例外 = 永遠的例外
- 破壞規範的完整性
- 養成壞習慣

---

## 🎯 成功標準

### 對 AI Agents
- ✅ 100% 部署使用 SAM
- ✅ 0% 使用 aws lambda update
- ✅ 主動建議使用 workflows
- ✅ 遇到緊急情況仍堅持 IaC

### 對專案
- ✅ 所有基礎設施在 template.yaml
- ✅ Git 記錄所有變更
- ✅ CloudFormation 狀態一致
- ✅ 團隊協作順暢

---

## 📖 延伸閱讀

### AWS 最佳實踐
- [Infrastructure as Code](https://docs.aws.amazon.com/whitepapers/latest/introduction-devops-aws/infrastructure-as-code.html)
- [SAM Best Practices](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-best-practices.html)

### 專案文檔
- `docs/STACK_MANAGEMENT.md` - Stack 管理最佳實踐
- `.clinerules/deployment/lambda-development-best-practices.md` - Lambda 開發

---

**規則版本**: v1.0  
**創建日期**: 2026-01-22  
**基於經驗**: Agent 違反 IaC 原則的實際問題  
**強制執行**: 是（Rule + Hook 雙重保護）  
**優先級**: Critical（最高）

**記住**：Infrastructure as Code 不是建議，是**強制要求**。沒有例外，沒有妥協！