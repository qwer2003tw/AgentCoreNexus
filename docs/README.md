# 文檔索引

AgentCoreNexus 專案的完整文檔目錄。

---

## 📖 核心文檔

### 架構與設計
- **[系統架構指南](architecture-guide.md)** - 完整的技術架構、EventBridge 整合與實作細節
  - EventBridge 事件驅動架構
  - 雙 Stack 設計說明
  - 消息流程與路由
  - 技術決策記錄

### 部署與配置
- **[部署指南](deployment-guide.md)** - 完整 AWS 部署步驟與最佳實踐
  - CloudFormation/SAM 部署
  - 環境配置與權限設定
  - 部署驗證步驟
  - 故障排除指南

### 使用指南
- **[管理員命令](admin-commands.md)** - 管理員功能與操作說明
  - Admin 命令完整列表
  - 權限管理
  - 操作範例

- **[瀏覽器實現](browser-implementation.md)** - AWS Browser Sandbox 功能使用
  - Browser Sandbox 整合
  - API 使用方法
  - 權限配置
  - 故障排除

---

## 📦 組件文檔

### telegram-agentcore-bot
AI 處理器組件的詳細文檔：
- [README](../telegram-agentcore-bot/README.md) - 組件概覽與使用

### telegram-lambda
Webhook 接收器組件的詳細文檔：
- [README](../telegram-lambda/README.md) - 組件概覽
- [完整文檔目錄](../telegram-lambda/docs/README.md) - 詳細技術文檔
  - Changelog（變更記錄）
  - Deployment（部署指南）
  - Features（功能說明）
  - Troubleshooting（故障排除）

---

## 📚 開發報告

查看 [dev-reports](../dev-reports/) 目錄了解已完成功能的開發過程：
- [2026-01 Browser Sandbox](../dev-reports/2026-01-browser-sandbox/REPORT.md)
- [2026-01 Memory 功能](../dev-reports/2026-01-memory-feature/REPORT.md)
- [2026-01 系統升級](../dev-reports/2026-01-system-upgrade/REPORT.md)

---

## 🔧 開發中功能

查看 [dev-in-progress](../dev-in-progress/) 目錄了解正在開發的功能（供多平台 agents 協作）。

---

## 🚀 快速開始

1. **閱讀架構指南**：了解系統整體設計
2. **查看部署指南**：進行 AWS 部署
3. **參考組件文檔**：深入了解各組件

---

## 📝 文檔維護

- **核心文檔**（docs/）：永久保留，隨專案演進更新
- **開發報告**（dev-reports/）：功能完成後歸檔，記錄開發過程
- **開發中文檔**（dev-in-progress/）：功能開發期間的臨時文件

---

**最後更新**：2026-01-07  
**維護者**：AgentCoreNexus Team
