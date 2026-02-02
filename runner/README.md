# Runner - OpenClaw-style 執行環境

> 取代原本的 Lambda 執行，提供 OpenClaw 風格的命令執行能力

## 架構變更

```
Before (Lambda-only):
┌──────────────┐     ┌──────────────┐
│   Telegram   │────▶│ AI Processor │
│   Adapter    │     │   (Lambda)   │
└──────────────┘     └──────────────┘

After (Lambda + ECS Runner):
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Telegram   │────▶│ AI Processor │────▶│   Runner     │
│   Adapter    │     │   (Lambda)   │     │   (Fargate)  │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                           ┌──────┴──────┐
                                           │    EFS      │
                                           │ (workspace) │
                                           └─────────────┘
```

## 核心功能

1. **WebSocket Exec Agent** - 低延遲命令執行 (<500ms P95)
2. **Sandbox Allocator** - Session 級別工作空間隔離
3. **EFS 持久化** - 跨重啟保留檔案

## 目錄結構

```
runner/
├── src/
│   ├── exec_agent.py    # WebSocket 命令執行
│   ├── sandbox.py       # Sandbox 配置器
│   ├── health.py        # 健康檢查
│   ├── server.py        # HTTP/WS Server
│   └── config.py        # 設定管理
├── tests/
├── docker/
│   └── Dockerfile
└── README.md

infrastructure/runner/
├── template.yaml        # SAM: VPC, ECS, EFS, ALB
└── ecr-setup.sh         # ECR repo + base image mirror
```

## 與現有架構整合

- **ai-processor** 透過 HTTP 呼叫 Runner 執行命令
- 新增 `exec` tool 給 Agent 使用
- Session ID 對應 conversation ID

## 安全

參考 `docs/SECURITY_CHECKLIST.md`
