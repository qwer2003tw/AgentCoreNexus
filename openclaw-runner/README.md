# OpenClaw Runner

> OpenClaw-style 執行環境 for AgentCoreNexus

---

## 概述

這個模組實現了 OpenClaw 風格的命令執行架構，在 100% Serverless (Fargate) 環境下運行。

## 架構

```
┌─────────────────────────────────────────────────────────┐
│                     ECS Fargate                         │
│  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   Main Runner   │  │     Sandbox Sidecar         │  │
│  │                 │  │                             │  │
│  │  ┌───────────┐  │  │  ┌───────────────────────┐  │  │
│  │  │ WebSocket │◄─┼──┼─►│ Session Workspace     │  │  │
│  │  │ Exec Agent│  │  │  │ /workspace/{session}  │  │  │
│  │  └───────────┘  │  │  └───────────────────────┘  │  │
│  │                 │  │                             │  │
│  │  ┌───────────┐  │  │  ┌───────────────────────┐  │  │
│  │  │ Sandbox   │  │  │  │ EFS Mount             │  │  │
│  │  │ Allocator │  │  │  │ /efs                  │  │  │
│  │  └───────────┘  │  │  └───────────────────────┘  │  │
│  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 核心元件

### 1. WebSocket Exec Agent (`src/exec_agent.py`)
- 接收命令執行請求
- HMAC 認證
- stdout/stderr 串流回傳
- 延遲目標: P95 < 500ms

### 2. Sandbox Allocator (`src/sandbox.py`)
- 建立/銷毀 session workspace
- 目錄級隔離 (POSIX permissions)
- EFS Access Point 整合

### 3. Health Check (`src/health.py`)
- ALB 健康檢查 endpoint
- 內部狀態監控

## 安全

- 所有密鑰從 Secrets Manager 取得
- Container image 只用 ECR
- 遵循 `reference/acn-security-checklist.md`

## 測試

```bash
# Unit tests
pytest tests/ -v --cov=src --cov-report=term-missing

# Integration tests (需要 AWS 環境)
pytest tests/integration/ -v
```

## 驗收標準

參考 `reference/acn-phase1-acceptance-criteria.md`

---

## 目錄結構

```
openclaw-runner/
├── src/
│   ├── __init__.py
│   ├── exec_agent.py      # WebSocket 命令執行
│   ├── sandbox.py         # Sandbox 配置器
│   ├── health.py          # 健康檢查
│   └── config.py          # 設定管理
├── tests/
│   ├── __init__.py
│   ├── test_exec_agent.py
│   ├── test_sandbox.py
│   └── integration/
│       └── test_e2e.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── template.yaml          # SAM template
├── requirements.txt
└── README.md
```

---

*Phase 1 目標: 基本 exec + sandbox 隔離*
