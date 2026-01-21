---
name: naming-standards
description: 組件和資源命名規範，確保一致性和可維護性
priority: high
enforcement: strict
always_active: true
---

# Naming Standards

## 🎯 目的

建立一致的命名規範，確保：
- 組件職責清晰
- 易於理解和維護
- 支持未來擴展

---

## 📁 組件命名

### 目錄名稱

**規則**：
- 使用 kebab-case
- 描述性但簡潔
- 避免技術細節或平台綁定

**✅ 好的範例**：
- `ai-processor`：處理 AI 對話（通道無關）
- `telegram-adapter`：Telegram 通道適配器
- `web-adapter`：Web 通道適配器

**❌ 不好的範例**：
- `agentcore-ai-processor`：混雜技術（agentcore）和平台（telegram）
- `lambda-handler`：技術細節不應在組件名
- `bot-service`：過於通用

---

## 🏗️ CloudFormation Stack 命名

### 規則

**格式**：`agentcore-[component]-[env]`

**組成**：
- 統一前綴：`agentcore-`
- 組件名稱：與目錄名對應
- 環境後綴（可選）：`-dev`, `-staging`, `-prod`

**✅ 範例**：
- `agentcore-ai-processor`
- `agentcore-telegram-adapter-dev`
- `agentcore-web-adapter-prod`

**❌ 避免**：
- `agentcore-ai-processor`（無統一前綴）
- `my-stack`（不描述功能）
- `stack-1`（無意義）

---

## 🔧 Lambda 函數命名

### 規則

**格式**：`${StackName}-[function]`

**使用動態名稱**：
```yaml
FunctionName: !Sub '${AWS::StackName}-main'
FunctionName: !Sub '${AWS::StackName}-receiver'
FunctionName: !Sub '${AWS::StackName}-router'
```

**✅ 結果**：
- `agentcore-ai-processor-main`
- `agentcore-telegram-adapter-receiver`
- `agentcore-web-adapter-ws-connect`

---

## 📤 Export 命名

### 規則

**格式**：`${StackName}-[ResourceType]`

**範例**：
```yaml
Export:
  Name: !Sub '${AWS::StackName}-EventBusArn'
  Name: !Sub '${AWS::StackName}-ProcessorArn'
```

**結果**：
- `agentcore-telegram-adapter-EventBusArn`
- `agentcore-ai-processor-ProcessorArn`

---

## 🧪 測試目錄

### 統一結構

```
component/
└── tests/
    ├── unit/          # 單元測試（Mock 所有外部）
    ├── integration/   # 整合測試（Mock 部分外部）
    └── e2e/          # E2E 測試（真實環境）
```

### 命名準確性

**重要**：測試名稱必須反映實際內容

- ✅ `tests/integration/` - 使用 Mock AWS，測試代碼邏輯
- ✅ `tests/e2e-mock/` - Mock API，測試前端流程
- ✅ `tests/e2e-aws/` - 真實 AWS，測試完整系統

**❌ 誤導性命名**：
- `tests/e2e/` 但全部使用 Mock（應該叫 integration）

---

## 📚 文檔命名

### 規則

- 使用 kebab-case
- 描述性標題
- 放在合適的位置

**✅ 範例**：
- `docs/architecture-guide.md`
- `docs/deployment-guide.md`
- `ai-processor/README.md`

---

## 🔄 重構時的命名更新

### Checklist

當重命名組件時，必須更新：
- [ ] 目錄名稱
- [ ] template.yaml（Stack, Functions, Exports）
- [ ] Makefile
- [ ] 測試腳本
- [ ] 所有文檔（README, docs/, .clinerules/）
- [ ] Import/Export 引用
- [ ] Git 分支名稱（feature/[new-name]-xxx）

---

## ✅ 驗證

### 命名一致性檢查

```bash
# 檢查是否有遺漏的舊名稱
grep -r "agentcore-ai-processor" . --exclude-dir=.git
grep -r "agentcore-telegram-adapter" . --exclude-dir=.git --exclude-dir=backup

# 應該沒有結果（除了 CHANGELOG 和歷史文檔）
```

---

**規則版本**: v1.0  
**創建日期**: 2026-01-15  
**基於經驗**: 完整專案重構  
**維護者**: AgentCoreNexus Team