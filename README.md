# AgentCore Nexus

**多通道 AI 助理平台** - 基於 AWS Bedrock AgentCore 和 EventBridge 的事件驅動架構

## 🎯 專案簡介

AgentCore Nexus 是一個可擴展的多通道 AI 助理平台，整合了兩個核心組件：
- **Universal Message Adapter** (telegram-lambda): 通道無關的訊息接收與標準化層
- **Agent Processor** (telegram-agentcore-bot): 基於 AgentCore 的智能處理引擎

透過 AWS EventBridge 事件驅動架構，支援 Telegram、Discord、Slack、Web 等多種通道。

## 🏗️ 架構概覽

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Telegram   │  │   Discord   │  │    Slack    │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │ HTTPS              │                │
       ▼                    ▼                ▼
     ┌────────────────────────────────────────┐
     │   Universal Message Adapter (Lambda)   │
     │   - 通道檢測與標準化                    │
     │   - EventBridge 發布                   │
     └────────────────┬───────────────────────┘
                      │ EventBridge
                      │ message.received
                      ▼
              ┌──────────────────┐
              │ Agent Processor  │
              │ - AgentCore 整合  │
              │ - 智能對話處理     │
              └──────────────────┘
```

## 📦 專案結構

```
AgentCoreNexus/
├── README.md                              # 本文件
├── AgentCore_Nexus_Integration_Guide.md   # 完整架構設計文件
│
├── telegram-lambda/                       # Universal Message Adapter
│   ├── src/                               # Lambda 函數代碼
│   │   ├── handler.py                     # 主處理器（通道檢測/標準化/EventBridge）
│   │   ├── allowlist.py                   # 白名單驗證
│   │   ├── sqs_client.py                  # SQS 客戶端（向後兼容）
│   │   └── ...
│   ├── tests/                             # 測試套件（153/160 通過 96%）
│   │   ├── test_eventbridge_integration.py # EventBridge 功能測試（18 個）
│   │   └── ...
│   ├── template.yaml                      # SAM 部署模板
│   ├── DEPLOYMENT_GUIDE_EventBridge.md    # 部署指南
│   └── docs/                              # 詳細文件
│
└── telegram-agentcore-bot/                # Agent Processor
    ├── agents/                            # AgentCore 對話代理
    │   └── conversation_agent.py
    ├── services/                          # 核心服務
    │   ├── memory_service.py              # 記憶管理
    │   └── browser_service.py             # 瀏覽器整合
    ├── tools/                             # Agent 工具集
    │   ├── calculator.py
    │   ├── weather.py
    │   └── ...
    ├── processor_entry.py                 # EventBridge 事件處理入口
    ├── telegram_agent.py                  # 原 Telegram bot 入口
    ├── tests/                             # 測試套件
    │   ├── test_processor_entry.py        # Processor 測試（15 個）
    │   └── ...
    ├── template.yaml                      # SAM 部署模板
    └── requirements.txt                   # Python 依賴
```

## 🚀 快速開始

### 本地開發

```bash
# 安裝依賴
cd telegram-agentcore-bot
pip install -r requirements.txt

# 執行測試
cd telegram-lambda
python3 -m pytest tests/ -v

cd telegram-agentcore-bot
python3 run_tests.py
```

### AWS 部署

詳細部署指南請參閱 `telegram-lambda/DEPLOYMENT_GUIDE_EventBridge.md`

```bash
# 1. 部署 Adapter
cd telegram-lambda
sam build && sam deploy --guided

# 2. 部署 Processor
cd telegram-agentcore-bot
sam build && sam deploy --guided
```

## 📋 功能特性

### ✅ 已實現（Phase 0-3）

- **多通道架構**: 統一的訊息接收與處理框架
- **Universal Message Schema**: 通道無關的標準化訊息格式
- **EventBridge 整合**: 事件驅動的鬆耦合設計
- **雙軌運行**: EventBridge + SQS 並存，零風險遷移
- **AgentCore 智能處理**: 基於 Bedrock 的對話能力
- **完整測試**: 96% 測試覆蓋率（153/160）

### 🔄 開發中（Phase 4）

- **Response Router**: 通道特定的回應格式化與送達
- **送達確認**: 訊息送達狀態追蹤

### 📅 規劃中（Phase 5-6）

- **Web UI 通道**: HTTP/WebSocket 介面
- **Discord 整合**: Discord bot webhook
- **Slack 整合**: Slack app events API
- **統一註冊系統**: 跨通道身份映射

## 🧪 測試

### telegram-lambda
- **總測試數**: 160 個
- **通過率**: 96% (153/160)
- **新增測試**: 18 個 EventBridge 整合測試（100% 通過）

### telegram-agentcore-bot
- **總測試數**: 47 個
- **通過率**: 81% (26/32 原有 + 15 新增)
- **註**: 部分測試需要完整依賴環境

## 📊 開發進度

| Phase | 描述 | 狀態 | 完成度 |
|-------|------|------|--------|
| Phase 0 | 架構設計 | ✅ | 100% |
| Phase 1 | 準備階段 | ✅ | 100% |
| Phase 2 | 基礎架構升級 | ✅ | 100% |
| Phase 3 | 處理層整合 | ✅ | 100% |
| Phase 4 | Response Router | 🔄 | 0% |
| Phase 5 | 多通道擴展 | ⏳ | 0% |
| Phase 6 | 測試與優化 | ⏳ | 0% |

**整體進度**: 50% (3/6 階段完成)

## 🔑 核心技術

- **AWS Services**: Lambda, EventBridge, API Gateway, DynamoDB, Secrets Manager
- **AI/ML**: AWS Bedrock AgentCore, Claude 3.5 Sonnet
- **語言**: Python 3.11
- **框架**: AWS SAM (Serverless Application Model)
- **測試**: pytest, unittest
- **架構**: Event-Driven, Microservices, Serverless

## 📖 文件

### 核心文檔
- **[文檔索引](docs/README.md)** - 完整文檔目錄
- **[架構設計指南](docs/architecture-guide.md)** - 系統架構與技術細節
- **[部署指南](docs/deployment-guide.md)** - AWS 部署步驟
- **[管理員命令](docs/admin-commands.md)** - 管理功能說明
- **[瀏覽器實現](docs/browser-implementation.md)** - Browser Sandbox 使用

### 組件文檔
- **[telegram-lambda 文件](telegram-lambda/docs/)** - Webhook 接收器文檔
- **[telegram-agentcore-bot](telegram-agentcore-bot/)** - AI 處理器文檔

### 開發報告
- **[dev-reports](dev-reports/)** - 已完成功能的開發報告歸檔
  - [2026-01 Browser Sandbox](dev-reports/2026-01-browser-sandbox/REPORT.md)
  - [2026-01 Memory 功能](dev-reports/2026-01-memory-feature/REPORT.md)
  - [2026-01 系統升級](dev-reports/2026-01-system-upgrade/REPORT.md)

### 開發中
- **[dev-in-progress](dev-in-progress/)** - 正在開發的功能（多平台 agents 協作）

## 🛠️ 開發指引

### Git 分支策略

- `main`: 穩定的生產代碼
- `feature/*`: 功能開發分支
- `hotfix/*`: 緊急修復分支

### Commit 規範

遵循 Conventional Commits:
- `feat:` 新功能
- `fix:` 錯誤修復
- `docs:` 文件更新
- `test:` 測試相關
- `refactor:` 代碼重構

### 測試要求

- 新功能必須包含測試
- 測試覆蓋率目標: >85%
- 所有 PR 必須通過測試

## 📞 支援與貢獻

### 問題回報

請在 GitHub Issues 中提交問題，包含：
- 詳細的錯誤描述
- 重現步驟
- 環境資訊
- 相關日誌

### 貢獻指南

1. Fork 專案
2. 建立功能分支
3. 提交變更（包含測試）
4. 發送 Pull Request

## 📜 授權

[待定義]

## 🏆 致謝

感謝所有貢獻者的辛勤工作！

---

**版本**: v0.5.0-phase3  
**最後更新**: 2026-01-06  
**維護者**: [您的名稱/團隊]
