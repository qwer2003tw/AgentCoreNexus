# AgentCore Nexus

**多通道 AI 助理平台** - 基於 AWS Bedrock AgentCore 和 EventBridge 的事件驅動架構

## 🎯 專案簡介

AgentCore Nexus 是一個可擴展的多通道 AI 助理平台，整合了三個核心組件：
- **Universal Message Adapter** (telegram-lambda): 通道無關的訊息接收與標準化層
- **Agent Processor** (telegram-agentcore-bot): 基於 AgentCore 的智能處理引擎
- **Web Channel** (web-channel): Web UI 與 REST/WebSocket API ✨

透過 AWS EventBridge 事件驅動架構，支援 Telegram、Web 等多種通道，未來可擴展至 Discord、Slack 等平台。

## 🏗️ 架構概覽

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Telegram   │  │     Web     │  │   Discord   │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │ HTTPS        │ WebSocket        │
       ▼              ▼                  ▼
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
              └──────┬───────────┘
                     │ EventBridge
                     │ message.completed
                     ▼
              ┌──────────────────┐
              │ Response Router  │
              │ - 通道格式化       │
              │ - 訊息送達        │
              └──────────────────┘
```

## 📦 專案結構

```
AgentCoreNexus/
├── README.md                              # 本文件
├── AGENT.md                               # AI Agent 工作規範（由 .clinerules 整理）
├── Makefile                               # 統一部署管理
├── .clinerules/                           # AI Agent 行為規則與工作流
├── docs/                                  # 核心文檔（架構/部署/測試）
├── dev-in-progress/                       # 開發中文檔
├── dev-reports/                           # 開發報告歸檔
│
├── telegram-lambda/                       # Universal Message Adapter
│   ├── src/                               # Lambda 函數代碼
│   │   ├── handler.py                     # 主處理器（通道檢測/標準化/EventBridge）
│   │   ├── allowlist.py                   # 白名單驗證
│   │   ├── sqs_client.py                  # SQS 客戶端（向後兼容）
│   │   └── ...
│   ├── router/                            # Response Router
│   │   └── response_router.py            # 通道回應路由
│   ├── tests/                             # 測試套件（153/160 通過 96%）
│   │   ├── test_eventbridge_integration.py # EventBridge 功能測試（18 個）
│   │   └── ...
│   ├── template.yaml                      # SAM 部署模板
│   ├── DEPLOYMENT_GUIDE_EventBridge.md    # 部署指南
│   └── docs/                              # 詳細文件
│
├── telegram-agentcore-bot/                # Agent Processor
│   ├── agents/                            # AgentCore 對話代理
│   │   └── conversation_agent.py
│   ├── services/                          # 核心服務
│   │   ├── memory_service.py              # 記憶管理
│   │   └── browser_service.py             # 瀏覽器整合
│   ├── tools/                             # Agent 工具集
│   │   ├── calculator.py
│   │   ├── weather.py
│   │   └── ...
│   ├── processor_entry.py                 # EventBridge 事件處理入口
│   ├── telegram_agent.py                  # 原 Telegram bot 入口
│   ├── tests/                             # 測試套件
│   │   ├── test_processor_entry.py        # Processor 測試（15 個）
│   │   └── ...
│   ├── template.yaml                      # SAM 部署模板
│   └── requirements.txt                   # Python 依賴
│
└── web-channel/                           # Web Channel（前端 + 後端）
    ├── frontend/                          # React PWA 前端
    │   ├── src/
    │   │   ├── pages/                     # 頁面（Login/Chat/ChangePassword）
    │   │   ├── components/                # 組件（Chat/History/Binding/Export）
    │   │   ├── services/                  # API & WebSocket
    │   │   └── stores/                    # 狀態管理
    │   └── package.json
    ├── lambdas/                           # Backend Lambda 函數
    │   ├── websocket/                     # WebSocket handlers
    │   ├── rest/                          # REST API handlers
    │   └── router/                        # Response router
    ├── infrastructure/
    │   └── web-channel-template.yaml      # SAM 部署模板
    ├── e2e-tests/                         # Playwright E2E
    ├── scripts/                           # 部署腳本
    ├── README.md                          # 組件說明
    └── QUICKSTART.md                      # 快速開始
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

### AWS 部署（使用 Makefile）

```bash
# 使用 Makefile 統一管理 3 個 stacks
make deploy-all      # 首次部署所有 stacks（含 Web Channel）
make deploy-telegram # 部署 Telegram 接收層
make deploy-processor # 部署 AI 處理層
make deploy-web      # 部署 Web 通道層（含前端）
make update-frontend # 快速更新前端（開發用）
make status          # 檢查所有 stacks 狀態
make info            # 顯示詳細資訊
```

**Web Channel 快速開始**：
```bash
# 1. 部署 Backend + Frontend 基礎設施
make deploy-web

# 2. 建構並上傳前端
make update-frontend

# 3. 創建 Admin 用戶
./web-channel/scripts/create-admin-user.sh admin@example.com

# 詳細步驟請參閱 web-channel/QUICKSTART.md
```

詳細部署指南請參閱：
- `Makefile` - 統一部署管理
- `docs/STACK_MANAGEMENT.md` - Multi-Stack 管理指南
- `web-channel/QUICKSTART.md` - Web Channel 快速開始

## 📋 功能特性

### ✅ 已實現（Phase 0-5）

**核心架構**：
- ✅ 多通道架構與 EventBridge 整合
- ✅ Universal Message Schema（通道無關標準化訊息格式）
- ✅ 事件驅動的鬆耦合設計
- ✅ AgentCore 智能處理（Bedrock Claude 3.5 Sonnet）
- ✅ Response Router 與送達確認
- ✅ 雙軌運行（EventBridge + SQS 並存，零風險遷移）

**Telegram 通道（完整功能）**：
- ✅ Webhook 接收與白名單驗證
- ✅ 完整對話功能與 AgentCore Memory 管理
- ✅ Browser Sandbox 整合（AWS 管理的瀏覽器服務）
- ✅ 管理員命令系統
- ✅ 檔案處理功能
- ✅ 跨通道綁定（/bind 指令）

**Web 通道（MVP 完成 - 85%）**：✨
- ✅ 認證系統（Email + JWT + Bcrypt）
- ✅ WebSocket 即時通訊（自動重連、狀態管理）
- ✅ React PWA 前端（響應式設計、暗色主題）
- ✅ 對話歷史（90天保存，按時間/通道篩選，分頁載入）
- ✅ 跨通道綁定（6位數驗證碼，5分鐘有效期）
- ✅ 導出功能（JSON/Markdown）
- ✅ CloudFront + S3 託管
- ✅ DynamoDB 存儲（5 tables）
- ✅ Lambda Authorizer 安全驗證
- ✅ 完整部署腳本與文檔
- ✅ Rate limiting 防暴力破解

### 🔄 開發中（持續優化）

- Web Channel E2E 測試完善
- 附件上傳功能（前端 95% 完成）
- 性能優化與監控增強
- 測試覆蓋率提升

### 📅 規劃中（Phase 6+）

- Discord 整合
- Slack 整合
- 統一註冊系統增強
- AI 生成對話標題
- 多設備消息同步
- PDF 導出
- Markdown/代碼高亮渲染

## 🧪 測試

### telegram-lambda
- **總測試數**: 160 個
- **通過率**: 96% (153/160)
- **新增測試**: 18 個 EventBridge 整合測試（100% 通過）

### telegram-agentcore-bot
- **總測試數**: 47 個
- **通過率**: 81% (26/32 原有 + 15 新增)
- **註**: 部分測試需要完整依賴環境

### web-channel
- **Backend**: 完整單元測試
- **Frontend**: React 組件測試
- **E2E**: Playwright 測試（開發中）

## 📊 開發進度

| Phase | 描述 | 狀態 | 完成度 |
|-------|------|------|--------|
| Phase 0 | 架構設計 | ✅ | 100% |
| Phase 1 | 準備階段 | ✅ | 100% |
| Phase 2 | 基礎架構升級 | ✅ | 100% |
| Phase 3 | 處理層整合 | ✅ | 100% |
| Phase 4 | Response Router | ✅ | 100% |
| Phase 5 | Web Channel MVP | ✅ | 85% |
| Phase 6 | 多通道擴展 | ⏳ | 0% |
| Phase 7 | 測試與優化 | 🔄 | 20% |

**整體進度**: 78% (5/7 階段完成，1 階段進行中)

## 🔑 核心技術

- **AWS Services**: Lambda, EventBridge, API Gateway, DynamoDB, Secrets Manager, CloudFront, S3
- **AI/ML**: AWS Bedrock AgentCore, Claude 3.5 Sonnet
- **語言**: Python 3.11, TypeScript
- **框架**: AWS SAM (Serverless Application Model), React 18, Vite
- **測試**: pytest, unittest, Playwright
- **代碼質量**: Ruff (Linter + Formatter)
- **架構**: Event-Driven, Microservices, Serverless

## 📖 文件

### 核心文檔索引
- **[文檔索引](docs/README.md)** - 完整文檔目錄
- **[架構設計指南](docs/architecture-guide.md)** - 系統架構與技術細節
- **[部署指南](docs/deployment-guide.md)** - AWS 部署步驟
- **[Stack 管理指南](docs/STACK_MANAGEMENT.md)** - Multi-Stack 管理
- **[測試指南](docs/TESTING.md)** - 測試流程與工具
- **[代碼質量指南](docs/CODE_QUALITY.md)** - Ruff 與格式化規範
- **[管理員命令](docs/admin-commands.md)** - 管理功能說明
- **[瀏覽器實現](docs/browser-implementation.md)** - Browser Sandbox 使用

### 組件文檔
- **[telegram-lambda 文件](telegram-lambda/docs/)** - Webhook 接收器文檔
- **[telegram-agentcore-bot](telegram-agentcore-bot/)** - AI 處理器文檔
- **[web-channel](web-channel/README.md)** - Web Channel 組件說明
- **[web-channel 快速開始](web-channel/QUICKSTART.md)** - Web Channel 啟動指南
- **[web-channel 前端](web-channel/frontend/README.md)** - Web UI 開發說明
- **[web-channel E2E 測試](web-channel/e2e-tests/README.md)** - Playwright 測試指南

### 開發報告
- **[dev-reports](dev-reports/)** - 已完成功能的開發報告歸檔
  - [2026-01 Browser Sandbox](dev-reports/2026-01-browser-sandbox/REPORT.md)
  - [2026-01 Memory 功能](dev-reports/2026-01-memory-feature/REPORT.md)
  - [2026-01 系統升級](dev-reports/2026-01-system-upgrade/REPORT.md)
  - [2026-01 Web Channel](dev-reports/2026-01-web-channel/REPORT.md)

### 開發中
- **[dev-in-progress](dev-in-progress/)** - 正在開發的功能（多平台 agents 協作）

### 規範與工作流
- **[AGENT.md](AGENT.md)** - AI Agent 工作規範總覽
- **[.clinerules/README.md](.clinerules/README.md)** - Cline Rules 索引
- **[文檔管理規範](.clinerules/rules/documentation.md)** - 文檔生命週期
- **[代碼質量規則](.clinerules/rules/code-quality.md)** - Ruff 檢查規範
- **[測試標準](.clinerules/rules/testing-standards.md)** - 測試要求與覆蓋率
- **[測試快速參考](.clinerules/QUICK_REFERENCE.md)** - 常用測試指令

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

### 代碼質量

本專案使用 [Ruff](https://github.com/astral-sh/ruff) 確保代碼品質：

```bash
# 檢查代碼
ruff check .

# 自動修復
ruff check . --fix

# 格式化
ruff format .
```

詳細說明請參閱 [代碼質量指南](docs/CODE_QUALITY.md)

**代碼改善成果**（2026-01-07）:
- telegram-lambda: 1369 → 5 問題（改善 99.6%）
- telegram-agentcore-bot: 874 → 12 問題（改善 98.6%）
- **總計**: 2243 → 17 問題（**改善 99.2%**）

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

**版本**: v0.8.0-web-mvp  
**最後更新**: 2026-01-15  
**維護者**: AgentCoreNexus Team