# 📚 文件目錄

本目錄包含專案的所有文件，按類別組織。

## 📁 文件結構

```
docs/
├── deployment/           # 部署相關文件
├── features/            # 功能說明文件
├── troubleshooting/     # 故障排除文件
└── changelog/           # 變更日誌文件
```

## 🚀 部署文件

部署相關的完整指南和最佳實踐。

- [**部署指南 (DEPLOYMENT_GUIDE.md)**](deployment/DEPLOYMENT_GUIDE.md)
  - 完整的部署流程說明
  - 包含設定步驟、測試方法和常見問題

- [**部署最佳實踐 (DEPLOYMENT_BEST_PRACTICES.md)**](deployment/DEPLOYMENT_BEST_PRACTICES.md)
  - 部署的最佳實踐建議
  - 安全性和效能優化建議

- [**Secrets Manager 部署 (SECRETS_MANAGER_DEPLOYMENT.md)**](deployment/SECRETS_MANAGER_DEPLOYMENT.md)
  - AWS Secrets Manager 的設定和使用
  - Secret Token 管理最佳實踐

## ✨ 功能說明

專案特殊功能的詳細說明。

- [**指令系統架構 (COMMAND_SYSTEM.md)**](features/COMMAND_SYSTEM.md)
  - Command Handler Pattern 設計
  - 指令路由器機制
  - 如何新增自訂指令
  - 權限系統架構（預留）

- [**除錯指令 (DEBUG_COMMAND.md)**](features/DEBUG_COMMAND.md)
  - `/debug` 指令的使用方法
  - 如何使用除錯功能進行故障排除
  - 安全注意事項

## 🔧 故障排除

遇到問題時的解決方案。

- [**Webhook 設定故障排除 (WEBHOOK_SETUP_TROUBLESHOOTING.md)**](troubleshooting/WEBHOOK_SETUP_TROUBLESHOOTING.md)
  - Webhook 常見問題與解決方案
  - 驗證和測試方法

## 📝 變更日誌

專案的版本更新記錄。

- [**除錯功能更新 (CHANGELOG_DEBUG_FEATURE.md)**](changelog/CHANGELOG_DEBUG_FEATURE.md)
  - 除錯功能的開發歷程

- [**除錯指令更新 (CHANGELOG_DEBUG_COMMAND_UPDATE.md)**](changelog/CHANGELOG_DEBUG_COMMAND_UPDATE.md)
  - 除錯指令的改進記錄

## 🔗 快速導航

### 新手入門
1. [部署指南](deployment/DEPLOYMENT_GUIDE.md) - 開始部署
2. [Webhook 設定](troubleshooting/WEBHOOK_SETUP_TROUBLESHOOTING.md) - 設定 Webhook

### 進階使用
1. [指令系統架構](features/COMMAND_SYSTEM.md) - 了解指令系統設計
2. [除錯指令](features/DEBUG_COMMAND.md) - 使用除錯功能
3. [部署最佳實踐](deployment/DEPLOYMENT_BEST_PRACTICES.md) - 優化部署

### 開發者指南
1. [指令系統架構](features/COMMAND_SYSTEM.md) - 新增自訂指令處理器

### 問題排除
1. [Webhook 故障排除](troubleshooting/WEBHOOK_SETUP_TROUBLESHOOTING.md)
2. [除錯指令](features/DEBUG_COMMAND.md)

---

📍 回到 [專案首頁](../README.md)
