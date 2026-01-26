# Python 3.12 升級計劃

**開始時間**: 2026-01-26 15:52  
**預計用時**: 2-3 小時  
**策略**: 保守升級（保留 Optional 語法）

---

## 🎯 升級目標

**從**: Python 3.11  
**到**: Python 3.12  
**影響範圍**: 所有 Lambda functions 和 Layer

---

## 📋 需要更新的組件

### 配置文件
- [ ] `pyproject.toml` - target-version
- [ ] `ai-processor/template.yaml` - Runtime
- [ ] `telegram-adapter/template.yaml` - Runtime
- [ ] `web-adapter/template.yaml` - Runtime（如果存在）
- [ ] `.github/workflows/*.yml` - CI/CD Python 版本

### Lambda Layer
- [ ] `infrastructure/layers/shared-services` - 重建為 Python 3.12
- [ ] 上傳新版本（version 3）
- [ ] 更新所有 template.yaml 中的 layer ARN

### Lambda Functions（預估 6-8 個）
- [ ] agentcore-ai-processor-main
- [ ] agentcore-telegram-adapter-receiver
- [ ] agentcore-telegram-adapter-router
- [ ] web-adapter websocket handlers
- [ ] web-adapter REST API handlers
- [ ] web-adapter router

### 文檔
- [ ] README.md
- [ ] docs/ENV.md
- [ ] docs/deployment-guide.md
- [ ] CHANGELOG.md
- [ ] 開發環境升級指南（新建）

---

## ⚠️ 關鍵注意事項

### Lambda Layer 依賴
- **當前版本**: version 2（Python 3.11）
- **新版本**: version 3（Python 3.12）
- **ARN 格式**: `arn:aws:lambda:us-west-2:190825685292:layer:agentcore-shared-services:3`

### 部署順序
1. 先構建和部署 Layer
2. 再部署 Lambda（按依賴順序）
3. telegram-adapter → ai-processor → web-adapter

### 回滾策略
- Lambda 版本別名可快速切回
- CloudFormation stack 可回滾
- Git 可回退代碼

---

## 📊 風險評估

| 風險 | 等級 | 緩解措施 |
|------|------|---------|
| Layer 未更新 | 🔴 高 | 先構建 layer |
| 遺漏 Lambda | 🟠 中 | 完整清單檢查 |
| 部署失敗 | 🟡 低 | 版本回滾 |
| 測試失敗 | 🟡 低 | 完整測試 |

---

## ✅ 成功標準

- [ ] 所有 Lambda runtime: python3.12
- [ ] 所有 Lambda 狀態: Active
- [ ] 所有測試通過
- [ ] 文檔更新完成
- [ ] 性能無倒退（或更好）

---

**Status**: 準備開始執行