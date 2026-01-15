# AgentCore Nexus

**事件驅動的多通道 AI 助理平台** - 基於 AWS Bedrock AgentCore 和 EventBridge

## 🎯 專案簡介

AgentCore Nexus 是一個**事件驅動的多通道 AI 助理平台**，讓您的 AI 助理能在 Telegram、Web 等多個平台無縫服務用戶。

### ✨ 核心特色

- **🌐 跨通道記憶**：在任何平台與 AI 對話，上下文完整保留
- **⚡ 事件驅動**：基於 AWS EventBridge 的可擴展架構
- **🤖 企業級 AI**：整合 AWS Bedrock Claude 3.5 Sonnet
- **☁️ Serverless**：零運維、自動擴展、按使用付費
- **📝 完整歷史**：90天對話記錄，可匯出分析
- **🔐 安全第一**：多層驗證、加密存儲、權限控制

### 三層架構

#### 通道適配器層（Channel Adapters）
各通道獨立的訊息接收與適配：
- **telegram-adapter**: Telegram webhook 接收、白名單驗證、訊息標準化
- **web-adapter**: Web REST/WebSocket API、認證系統、訊息標準化
- 未來擴展：Discord、Slack 等通道適配器

#### 統一事件層（Universal Layer）
真正的 Universal 所在：
- **EventBridge**: 統一事件總線（agentcore-nexus-events）
- **Universal Message Schema**: 通道無關的標準化訊息格式
- 所有通道都發送相同格式的 `message.received` 事件

#### AI 處理層（Channel-Agnostic Processor）
- **ai-processor**: AI 智能處理引擎
  - 處理來自**所有通道**的訊息（via EventBridge）
  - 跨通道 Memory 管理（AgentCore）
  - Browser/File 工具整合
  - 發送統一格式的處理結果

**設計理念**：
- 採用多個專用 Adapter（而非單一 Universal Adapter）
- 原因：鬆耦合、獨立部署、故障隔離、專門優化
- EventBridge 提供統一的事件格式和路由機制

## 🏗️ 架構概覽

```
┌─ Telegram ─┐     ┌──── Web ────┐
│  Webhook   │     │ WebSocket   │
└─────┬──────┘     └──────┬──────┘
      │                   │
      ▼                   ▼
┌──────────────┐    ┌──────────────┐
│ Telegram     │    │ Web Channel  │
│ Adapter      │    │ Adapter      │
│(telegram-    │    │(web-adapter) │
│ lambda)      │    │              │
└──────┬───────┘    └──────┬───────┘
       │ EventBridge       │
       │ message.received  │
       └──────────┬─────────┘
                  │
     ┌────────────▼────────────┐
     │   EventBridge Bus       │ ← Universal 層
     │ (統一訊息格式)            │
     └────────────┬────────────┘
                  │
                  ▼
     ┌──────────────────────────┐
     │  AI Processor            │
     │ (ai-processor) │
     │ - AgentCore + Bedrock    │
     │ - 跨通道 Memory          │
     │ - Browser/File Tools     │
     └────────────┬─────────────┘
                  │ EventBridge
                  │ message.completed
     ┌────────────▼─────────────┐
     │   EventBridge Bus        │
     └────────┬──────────────────┘
              │
     ┌────────┴─────────┐
     │                  │
     ▼                  ▼
┌──────────┐      ┌──────────┐
│Telegram  │      │   Web    │
│Router    │      │ Router   │
└──────────┘      └──────────┘
```

**注意**：Discord、Slack 等通道規劃中（Phase 6+）

## 📦 專案結構

```
AgentCoreNexus/
├── README.md                              # 本文件
├── AGENT.md                               # AI Agent 工作規範
├── Makefile                               # 統一部署管理
├── .clinerules/                           # AI Agent 行為規則與工作流
├── docs/                                  # 核心文檔（架構/部署/測試）
├── dev-in-progress/                       # 開發中文檔
├── dev-reports/                           # 開發報告歸檔
│
├── telegram-adapter/                       # Telegram Channel Adapter
│   ├── src/                               # Lambda 函數代碼
│   │   ├── handler.py                     # 主處理器
│   │   │                                  # - Telegram webhook 接收
│   │   │                                  # - 白名單驗證
│   │   │                                  # - 訊息標準化（Universal Schema）
│   │   │                                  # - 發送到 EventBridge
│   │   ├── allowlist.py                   # 白名單驗證邏輯
│   │   ├── file_handler.py                # 檔案處理
│   │   ├── commands/                      # 命令處理器（/info, /bind 等）
│   │   └── ...
│   ├── router/                            # Telegram Response Router
│   │   └── response_router.py            # 接收 EventBridge，格式化並發送到 Telegram
│   ├── tests/                             # 測試套件（153/160 通過 96%）
│   ├── template.yaml                      # SAM 部署模板（Stack: telegram-adapter-receiver）
│   └── docs/                              # 詳細文件
│
├── ai-processor/                # AI Processor (Channel-Agnostic)
│   ├── agents/                            # AgentCore 對話代理
│   │   └── conversation_agent.py
│   ├── services/                          # 核心服務
│   │   ├── memory_service.py              # 跨通道記憶管理
│   │   ├── browser_service.py             # Browser Sandbox 整合
│   │   └── file_service.py                # 檔案處理服務
│   ├── tools/                             # Agent 工具集
│   │   ├── calculator.py, weather.py, browser.py, file_reader.py
│   │   └── ...
│   ├── processor_entry.py                 # EventBridge 事件處理入口
│   │                                      # - 接收 message.received（所有通道）
│   │                                      # - AgentCore + Bedrock 處理
│   │                                      # - 發送 message.completed
│   ├── telegram_agent.py                  # 原 Telegram bot 入口（向後兼容）
│   ├── tests/                             # 測試套件（47 個測試）
│   ├── template.yaml                      # SAM 部署模板（Stack: agentcore-ai-processor）
│   └── requirements.txt                   # Python 依賴
│
└── web-adapter/                           # Web Channel (Frontend + Backend)
    ├── frontend/                          # React PWA 前端
    │   ├── src/
    │   │   ├── pages/                     # 頁面（Login/Chat/ChangePassword）
    │   │   ├── components/                # 組件（Chat/History/Binding/Export）
    │   │   ├── services/                  # API & WebSocket 服務
    │   │   └── stores/                    # 狀態管理（Zustand）
    │   ├── package.json
    │   └── vite.config.ts
    ├── lambdas/                           # Backend Lambda 函數
    │   ├── websocket/                     # WebSocket handlers
    │   │   │                              # - connect/disconnect/default
    │   │   │                              # - 發送訊息到 EventBridge
    │   ├── rest/                          # REST API handlers
    │   │   │                              # - auth, admin, history, binding
    │   └── router/                        # Web Response Router
    │       └── router.py                  # 接收 EventBridge，推送到 WebSocket
    ├── infrastructure/
    │   └── web-adapter-template.yaml      # SAM 部署模板（Stack: agentcore-web-adapter）
    ├── e2e-tests/                         # Playwright E2E
    ├── scripts/                           # 部署腳本
    ├── README.md                          # 組件說明
    └── QUICKSTART.md                      # 快速開始
```

## 📋 前置需求

### 必要條件
- ✅ AWS 帳號（需要 Bedrock 權限）
- ✅ AWS CLI 已配置（`aws configure`）
- ✅ SAM CLI 已安裝（[安裝指南](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)）
- ✅ Python 3.11+
- ✅ Node.js 18+（如果開發 Web 前端）

### AWS 準備

#### 1. 申請 Bedrock 模型權限
```bash
# 前往 AWS Console > Bedrock > Model access
# 申請: anthropic.claude-3-5-sonnet-20241022-v2:0
# 區域: us-west-2（推薦）或 us-east-1
# 審核時間: 通常數分鐘內
```

#### 2. Telegram Bot（如果使用 Telegram 通道）
```bash
# 1. Telegram 中找 @BotFather
# 2. 發送 /newbot
# 3. 按指示創建並獲取 Token
# 格式: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 預估成本

| 用戶規模 | 月成本 | 主要費用 |
|---------|--------|---------|
| < 10 用戶 | $5-15 | Bedrock API |
| < 100 用戶 | $15-30 | Bedrock + Lambda |
| < 1000 用戶 | $30-60 | Bedrock + DynamoDB + CloudFront |

詳細成本分析請參閱 [Stack 管理指南](docs/STACK_MANAGEMENT.md#成本估算)

## 🚀 快速開始

### 本地開發

```bash
# 安裝依賴
cd ai-processor
pip install -r requirements.txt

# 執行測試
cd telegram-adapter
python3 -m pytest tests/ -v

cd ai-processor
python3 run_tests.py
```

### AWS 部署（使用 Makefile）

#### ⚠️ 重要：首次部署必須按順序

```bash
# 方式 1：自動化部署（推薦）
make deploy-all      # 自動按正確順序部署所有 stacks

# 方式 2：手動按順序部署
make deploy-telegram  # Step 1: 創建 EventBridge Bus
make deploy-processor # Step 2: 連接到 EventBridge
make deploy-web       # Step 3: 部署 Web 通道

# 後續更新可以獨立部署
make deploy-telegram  # 只更新 Telegram 層
make deploy-processor # 只更新 AI 處理層
make deploy-web       # 只更新 Web 層
```

**為什麼順序重要？**
- telegram-adapter 創建 EventBridge Bus
- processor 和 web 都依賴這個 Bus
- 詳見 [Stack 管理指南](docs/STACK_MANAGEMENT.md)

#### 其他有用指令

```bash
make update-frontend # 快速更新 Web 前端（開發迭代用）
make status          # 檢查所有 stacks 狀態
make info            # 顯示詳細資訊（含前端 URL）
make logs STACK=web  # 查看指定 stack 日誌
```

#### Web Channel 快速開始

```bash
# 1. 部署 Backend + Frontend 基礎設施
make deploy-web

# 2. 建構並上傳前端
make update-frontend

# 3. 創建 Admin 用戶
./web-adapter/scripts/create-admin-user.sh admin@example.com

# 詳細步驟請參閱 web-adapter/QUICKSTART.md
```

詳細部署指南：
- `Makefile` - 統一部署管理指令
- `docs/STACK_MANAGEMENT.md` - Multi-Stack 管理指南
- `docs/deployment-guide.md` - AWS 完整部署步驟
- `web-adapter/QUICKSTART.md` - Web Channel 5分鐘快速開始

## 📋 功能特性

### ✅ 已實現（Phase 0-5）

**核心架構**：
- ✅ 多通道架構（Telegram + Web，事件驅動）
- ✅ EventBridge 統一事件總線
- ✅ Universal Message Schema（通道無關標準化格式）
- ✅ AgentCore 智能處理（Bedrock Claude 3.5 Sonnet）
- ✅ Response Router 與送達確認
- ✅ 雙軌運行（EventBridge 主要路徑，SQS 向後兼容）

**Telegram 通道（完整功能）**：
- ✅ Webhook 接收與白名單驗證（雙重驗證：chat_id + username）
- ✅ 完整對話功能與 AgentCore Memory 管理
- ✅ Browser Sandbox 整合（AWS 管理的瀏覽器服務）
- ✅ 檔案處理功能（photo, document, video, audio）
- ✅ 管理員命令系統（/info, /bind, /new 等）
- ✅ 跨通道綁定（/bind 指令生成驗證碼）

**Web 通道（MVP 完成 - 85%）**：✨
- ✅ 認證系統（Email + JWT (7天) + Bcrypt (12 rounds)）
- ✅ Rate limiting（5次失敗鎖15分鐘，防暴力破解）
- ✅ WebSocket 即時通訊（自動重連、狀態管理）
- ✅ React PWA 前端（響應式設計、暗色主題）
- ✅ 對話歷史（90天保存，按時間/通道篩選，分頁載入）
- ✅ 跨通道綁定（6位數驗證碼，5分鐘有效期）
- ✅ 導出功能（JSON/Markdown）
- ✅ CloudFront + S3 託管（全球 CDN 加速）
- ✅ DynamoDB 存儲（5 tables, On-demand 計費）
- ✅ Lambda Authorizer 安全驗證
- ✅ 完整部署腳本與文檔

### 🔄 開發中（持續優化）

- Web Channel 附件上傳功能（前端 95% 完成，整合測試中）
- Web Channel E2E 測試完善
- 性能優化與監控增強
- 測試覆蓋率提升

### 📅 規劃中（Phase 6+）

- Discord 整合（新的 Channel Adapter）
- Slack 整合（新的 Channel Adapter）
- 統一註冊系統增強
- AI 生成對話標題
- 多設備消息同步
- PDF 導出
- Markdown/代碼高亮渲染

## 🔐 安全特性

### 多層安全防護

**Telegram 通道**：
- ✅ Webhook Secret Token（64字符隨機生成，A-Z/a-z/0-9）
- ✅ 白名單驗證（DynamoDB + chat_id + username 雙重檢查）
- ✅ 自動加密（Secrets Manager, DynamoDB）

**Web 通道**：
- ✅ JWT 認證（HS256, 7天有效期）
- ✅ Bcrypt 密碼（12 rounds）
- ✅ Rate limiting（5次失敗鎖15分鐘）
- ✅ Lambda Authorizer 驗證所有請求
- ✅ XSS 防護（輸入驗證與清理）
- ✅ 首次登入強制修改密碼

**基礎設施**：
- ✅ 所有 API 使用 HTTPS
- ✅ DynamoDB 自動加密（SSE）
- ✅ Secrets Manager 管理敏感資訊
- ✅ IAM 最小權限原則
- ✅ CloudWatch 安全事件追蹤

**監控**：
- ✅ CloudWatch 安全事件追蹤
- ✅ 異常登入嘗試告警
- ✅ API 錯誤率監控
- ✅ DynamoDB 操作審計

## 🧪 測試

### telegram-adapter (Telegram Adapter)
- **總測試數**: 160 個
- **通過率**: 96% (153/160)
- **新增測試**: 18 個 EventBridge 整合測試（100% 通過）
- **覆蓋範圍**: 白名單、命令路由、檔案處理、EventBridge 發布

### ai-processor (AI Processor)
- **總測試數**: 47 個
- **通過率**: 81% (26/32 原有 + 15 新增)
- **覆蓋範圍**: Agent 邏輯、Memory 整合、工具函數、錯誤處理
- **註**: 部分測試需要完整 AWS 環境（Bedrock, AgentCore）

### web-adapter (Web Channel)
- **Backend**: 完整單元測試（Lambda 函數）
- **Frontend**: React 組件測試
- **E2E**: Playwright 測試（開發中）
- **覆蓋範圍**: 認證、WebSocket、歷史查詢、綁定流程

### 測試指令

```bash
# 使用 Makefile（推薦）
make test           # 執行所有測試（5-8 分鐘）
make test-quick     # 快速測試，跳過 Web E2E（2-3 分鐘）
make test-backend   # 只測試後端組件
make coverage-report # 查看覆蓋率報告

# 或使用統一腳本
./run_all_tests.sh          # 完整測試
./run_all_tests.sh --quick  # 快速測試
```

詳細測試說明請參閱 [測試指南](docs/TESTING.md)

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

### Backend
- **AWS Services**: Lambda, EventBridge, API Gateway, DynamoDB, Secrets Manager, S3, CloudFront
- **AI/ML**: AWS Bedrock AgentCore, Claude 3.5 Sonnet
- **語言**: Python 3.11
- **框架**: AWS SAM (Serverless Application Model)
- **測試**: pytest, unittest
- **代碼質量**: Ruff (Linter + Formatter)
- **架構**: Event-Driven, Microservices, Serverless

### Frontend (Web Channel)
- **語言**: TypeScript
- **框架**: React 18
- **建構工具**: Vite
- **樣式**: Tailwind CSS + shadcn/ui
- **狀態管理**: Zustand
- **數據獲取**: TanStack Query
- **PWA**: vite-plugin-pwa
- **測試**: Playwright (E2E)

### 架構模式
- Event-Driven Architecture（事件驅動）
- Microservices（微服務）
- Serverless（無伺服器）
- Backend for Frontend（BFF）- 各通道獨立 Router
- Adapter Pattern（適配器模式）- 各通道獨立 Adapter

## ⚠️ 限制與已知問題

### 當前限制

**通道支援**：
- ✅ 完整支援：Telegram, Web
- ⏳ 規劃中：Discord, Slack, Line, WhatsApp

**Web Channel**：
- ✅ 基礎對話功能完整
- 🔄 開發中：檔案上傳（前端 95% 完成，整合測試中）
- 🔄 開發中：E2E 測試完善

**效能**：
- ⏱️ AI 回應時間：5-30 秒（依問題複雜度）
- 💡 這是 Bedrock Claude 的正常表現，無法顯著縮短
- ✅ 系統處理時間：< 1 秒（已優化）

**擴展性**：
- WebSocket 連接上限：500 concurrent（可申請提升至 10,000）
- Lambda 並發：1000（可申請提升）
- DynamoDB：On-demand 自動擴展

### 已知問題

- 部分 E2E 測試需要完善（telegram-adapter: 7/160 failing, 4.4%）
- Web Channel 附件分析功能需要最終整合測試
- 文檔持續更新中（本次已大幅改善）

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
- **[telegram-adapter 文件](telegram-adapter/docs/)** - Telegram Adapter 文檔
- **[ai-processor](ai-processor/)** - AI Processor 文檔
- **[web-adapter](web-adapter/README.md)** - Web Channel 組件說明
- **[web-adapter 快速開始](web-adapter/QUICKSTART.md)** - Web Channel 啟動指南
- **[web-adapter 前端](web-adapter/frontend/README.md)** - Web UI 開發說明
- **[web-adapter E2E 測試](web-adapter/e2e-tests/README.md)** - Playwright 測試指南

### 開發報告
- **[dev-reports](dev-reports/)** - 已完成功能的開發報告歸檔
  - [2026-01 Browser Sandbox](dev-reports/2026-01-browser-sandbox/REPORT.md)
  - [2026-01 Memory 功能](dev-reports/2026-01-memory-feature/REPORT.md)
  - [2026-01 系統升級](dev-reports/2026-01-system-upgrade/REPORT.md)
  - [2026-01 Web Channel](dev-reports/2026-01-web-adapter/REPORT.md)

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
- 所有 PR 必須通過測試（CI 自動檢查）
- Python 代碼必須通過 Ruff 檢查

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
- telegram-adapter: 1369 → 5 問題（改善 99.6%）
- ai-processor: 874 → 12 問題（改善 98.6%）
- **總計**: 2243 → 17 問題（**改善 99.2%**）

## 📞 支援與貢獻

### 問題回報

請在 [GitHub Issues](https://github.com/qwer2003tw/AgentCoreNexus/issues) 中提交問題，包含：
- 詳細的錯誤描述
- 重現步驟
- 環境資訊（AWS region, Python 版本等）
- 相關日誌（CloudWatch Logs）

### 貢獻指南

1. Fork 專案
2. 建立功能分支（`git checkout -b feature/amazing-feature`）
3. 提交變更（包含測試，遵循 Commit 規範）
4. 執行測試確保通過（`make test`）
5. 執行 Ruff 檢查（`ruff check . --fix && ruff format .`）
6. Push 到分支（`git push origin feature/amazing-feature`）
7. 發送 Pull Request

**PR 要求**：
- ✅ 所有測試通過
- ✅ Ruff 檢查通過
- ✅ 新功能有測試
- ✅ 更新相關文檔

## 📜 授權

[待定義]

## 🏆 致謝

感謝所有貢獻者的辛勤工作！

特別感謝：
- AWS Bedrock AgentCore 團隊
- Telegram