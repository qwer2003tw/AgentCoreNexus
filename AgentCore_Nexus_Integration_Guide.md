# AgentCore Nexus 整合改造指南

本文件說明如何將現有兩個專案：
- [telegram-lambda] — 接收層（Webhook + Allowlist + SQS）
- [telegram-agentcore-bot] — 處理層（AgentCore 整合 + 對話代理 + 工具）
整合並演進為多通道、事件驅動、可擴展的 AgentCore Nexus 架構。

參考現況：
- telegram-lambda 具備 API Gateway、Lambda、SQS、DynamoDB allowlist、Secrets、CloudWatch 監控與 SAM 基礎設施（template.yaml）
- telegram-agentcore-bot 具備清晰分層（config/utils/tools/services/agents）、完整單元測試與 Memory/Browser 整合

---

## 目標

- 多通道輸入：Telegram、Web UI、Discord、Slack（可擴張）
- 通道無關處理：統一訊息結構、通道適配器
- 事件驅動：EventBridge 為核心事件總線；DLQ、重試策略
- AgentCore 增強：統一會話與記憶、跨通道上下文
- 回應分發：通道格式化與送達回報
- 註冊模式：支援個體註冊與群組註冊

---

## 高階架構

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Telegram    │  │   Web UI    │  │  Discord    │  │   Slack     │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │ HTTPS/Webhook         HTTP/WS          HTTPS           HTTPS
       ▼                      ▼                 ▼               ▼
               ┌──────────────────────────────────────────┐
               │ AWS API Gateway (多路由)                  │
               │ /telegram/webhook /web/api ...           │
               └───────────────┬──────────────────────────┘
                               ▼
                 ┌───────────────────────────────┐
                 │ Universal Message Adapter     │  ← 改造自 telegram-lambda
                 │ - 檢測通道/標準化/統一驗證        │
                 └───────────────┬───────────────┘
                                 ▼ Event
                     ┌─────────────────────────┐
                     │ Amazon EventBridge      │  ← 中央事件總線
                     │ message.received ...    │
                     └───────────────┬─────────┘
                                     ▼
                 ┌────────────────────────────────┐
                 │ Agent Processor (Lambda/ECS)   │  ← 整合 telegram-agentcore-bot
                 │ - AgentCore Orchestrator       │
                 │ - Conversation/Multi-channel   │
                 └───────────────┬────────────────┘
                                 ▼
                     ┌─────────────────────────┐
                     │ Response Router         │
                     │ - 通道格式化/送達/回報      │
                     └────────┬────────────────┘
                              ▼
            ┌─────────┬───────────┬───────────┬───────────┐
            ▼         ▼           ▼           ▼           ▼
          Telegram    Web         Discord     Slack       Email/SMS...
```

---

## 漸進式整合路線

- 保留並重用：現有 SAM 基礎設施、白名單、安全機制、測試、AgentCore 集成
- 以最小變動，先打通 Telegram → EventBridge → Processor → Telegram 回送
- 再逐步加入 Web/Discord/Slack 通道

---

## 代碼與資源改造

### 1) telegram-lambda → Universal Message Adapter

目標：從「單一 Telegram Receiver + SQS」升級為「多通道 Adapter + EventBridge」。

關鍵變更：
- 新增通道自動檢測與抽取
- 引入統一訊息結構（Universal Message Schema）
- 保留 Allowlist/DynamoDB，擴展為通道無關的統一驗證
- 將輸出從 SQS 轉為 EventBridge message.received（保留 SQS 作為備援或特定批次流程）

範例程式（示意，置於 src/handler.py）：

```python
import json, os, uuid, boto3
from utils.logger import get_logger
from allowlist import check_allowed
logger = get_logger(__name__)

evb = boto3.client('events')
EVENT_BUS_NAME = os.getenv('EVENT_BUS_NAME', 'agentcore-nexus-events')

def lambda_handler(event, context):
    logger.info("Incoming event", extra={"event": event})

    channel = detect_channel(event)
    raw = extract_platform_payload(event, channel)
    normalized = normalize_message(raw, channel)

    if not unified_allow_check(normalized):
        return response(403, {"message": "Forbidden"})

    publish_message_received(normalized)
    return response(200, {"status": "ok"})

def detect_channel(event):
    path = (event.get('path') or "").lower()
    if 'telegram' in path:
        return 'telegram'
    if 'discord' in path:
        return 'discord'
    if 'slack' in path:
        return 'slack'
    return 'web'

def extract_platform_payload(event, channel):
    body = event.get('body') or "{}"
    try:
        data = json.loads(body)
    except Exception:
        data = {}
    return {"channel": channel, "data": data, "headers": event.get('headers', {})}

def normalize_message(raw, channel):
    if channel == 'telegram':
        msg = raw['data'].get('message') or {}
        from_user = msg.get('from') or {}
        chat = msg.get('chat') or {}
        text = msg.get('text', '')
        return {
            "messageId": str(uuid.uuid4()),
            "timestamp": event_time_iso(),
            "channel": {"type": "telegram", "channelId": str(chat.get('id')), "metadata": {}},
            "user": {
                "id": f"tg:{from_user.get('id')}",
                "channelUserId": str(from_user.get('id')),
                "username": from_user.get('username', ''),
                "displayName": (from_user.get('first_name','') + ' ' + from_user.get('last_name','')).strip()
            },
            "content": {"text": text, "attachments": [], "messageType": "text"},
            "context": {"conversationId": str(chat.get('id')), "sessionId": str(from_user.get('id'))},
            "routing": {"priority": "normal", "tags": []}
        }
    return {
        "messageId": str(uuid.uuid4()),
        "timestamp": event_time_iso(),
        "channel": {"type": channel, "channelId": "unknown", "metadata": {}},
        "user": {"id": "unknown", "channelUserId": "unknown", "username": "", "displayName": ""},
        "content": {"text": "", "attachments": [], "messageType": "text"},
        "context": {"conversationId": "unknown", "sessionId": "unknown"},
        "routing": {"priority": "normal", "tags": []}
    }

def unified_allow_check(normalized):
    ch = normalized["channel"]["type"]
    if ch == 'telegram':
        chat_id = int(normalized["channel"]["channelId"])
        username = normalized["user"]["username"]
        return check_allowed(chat_id, username)
    return True

def publish_message_received(normalized):
    evb.put_events(Entries=[{
        "Source": "universal-adapter",
        "DetailType": "message.received",
        "Detail": json.dumps(normalized),
        "EventBusName": EVENT_BUS_NAME
    }])

def event_time_iso():
    import datetime
    return datetime.datetime.utcnow().isoformat() + "Z"

def response(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }
```

SAM 模板（template.yaml）增補重點：

```yaml
Resources:
  UniversalEventBus:
    Type: AWS::Events::EventBus
    Properties:
      Name: agentcore-nexus-events

  TelegramReceiverFunction:
    Type: AWS::Serverless::Function
    Properties:
      Environment:
        Variables:
          EVENT_BUS_NAME: !Ref UniversalEventBus
      Policies:
        - Statement:
            - Effect: Allow
              Action: events:PutEvents
              Resource: !GetAtt UniversalEventBus.Arn

  # API Gateway 可新增多路由指向同一 Lambda
  # /telegram/webhook, /discord/webhook, /web/api ...
```

---

### 2) telegram-agentcore-bot → Agent Processor

目標：接收 EventBridge message.received 事件，透過 AgentCore 產生回應，發布 message.completed 或 message.failed。

擴展點：
- 新增事件觸發入口（Lambda handler 或 ECS 消費者）
- ConversationAgent 擴展為通道感知（formatter）
- Memory/Session 維持跨通道一致

事件處理入口（新檔案：processor_entry.py）：

```python
import json, os, boto3
from agents.conversation_agent import ConversationAgent
from services.memory_service import MemoryService
from utils.logger import get_logger

logger = get_logger(__name__)
evb = boto3.client('events')
EVENT_BUS_NAME = os.getenv('EVENT_BUS_NAME', 'agentcore-nexus-events')

agent = ConversationAgent()
memory = MemoryService()

def handler(event, context):
    # 支援 EventBridge (detail) 或 SQS (body) 的觸發格式
    records = event.get('Records') or []
    if records:
        for r in records:
            detail = json.loads(r.get('body', '{}'))
            process(detail)
    else:
        detail = event.get('detail') or {}
        process(detail)

def process(normalized):
    channel_type = normalized["channel"]["type"]
    user_text = normalized["content"]["text"]

    try:
        # 1) 取得上下文（可使用記憶）
        session = memory.get_session_manager()
        # 2) 呼叫既有 ConversationAgent
        response = agent.process_message(user_text)
        # 3) 發布完成事件
        completed = {
            "original": normalized,
            "response": response,
            "channel": channel_type
        }
        evb.put_events(Entries=[{
            "Source": "agent-processor",
            "DetailType": "message.completed",
            "Detail": json.dumps(completed),
            "EventBusName": EVENT_BUS_NAME
        }])

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        evb.put_events(Entries=[{
            "Source": "agent-processor",
            "DetailType": "message.failed",
            "Detail": json.dumps({"original": normalized, "error": str(e)}),
            "EventBusName": EVENT_BUS_NAME
        }])
```

EventBridge 規則（SAM 增補）：

```yaml
Resources:
  MessageReceivedRule:
    Type: AWS::Events::Rule
    Properties:
      EventBusName: !Ref UniversalEventBus
      EventPattern:
        source: ["universal-adapter"]
        detail-type: ["message.received"]
      Targets:
        - Arn: !GetAtt AgentProcessorFunction.Arn
          Id: "AgentProcessorTarget"

  AgentProcessorPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref AgentProcessorFunction
      Action: lambda:InvokeFunction
      Principal: events.amazonaws.com
      SourceArn: !GetAtt MessageReceivedRule.Arn
```

---

### 3) Response Router（回應分發）

目標：將 Agent Processor 的回應送回原通道（Telegram/Web/Discord/Slack），並處理通道特定格式化。

Router 示意（新服務 response_router.py）：

```python
import json, os, boto3
from utils.logger import get_logger
from delivery.telegram import TelegramDelivery
# from delivery.discord import DiscordDelivery
# from delivery.web import WebDelivery
logger = get_logger(__name__)

deliveries = {
    "telegram": TelegramDelivery(),
    # "discord": DiscordDelivery(),
    # "web": WebDelivery(),
    # "slack": SlackDelivery()
}

def handler(event, context):
    records = event.get('Records') or []
    if records:
        for r in records:
            detail = json.loads(r.get('body', '{}'))
            route(detail)
    else:
        route(event.get('detail') or {})

def route(completed):
    original = completed["original"]
    channel = completed["channel"]
    client = deliveries.get(channel)
    if not client:
        logger.warning(f"No delivery client for channel={channel}")
        return

    formatted = format_for_channel(completed["response"], channel)
    client.send(
        channel_id=original["channel"]["channelId"],
        message=formatted,
        metadata=original["channel"]["metadata"]
    )

def format_for_channel(response, channel):
    # 針對 markdown/段落/按鈕/長度限制等做格式化
    return response
```

EventBridge 規則（message.completed → ResponseRouter）：

```yaml
Resources:
  MessageCompletedRule:
    Type: AWS::Events::Rule
    Properties:
      EventBusName: !Ref UniversalEventBus
      EventPattern:
        source: ["agent-processor"]
        detail-type: ["message.completed"]
      Targets:
        - Arn: !GetAtt ResponseRouterFunction.Arn
          Id: "ResponseRouterTarget"

  ResponseRouterPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref ResponseRouterFunction
      Action: lambda:InvokeFunction
      Principal: events.amazonaws.com
      SourceArn: !GetAtt MessageCompletedRule.Arn
```

---

## 資料模型

### Universal Message Schema

```json
{
  "messageId": "uuid",
  "timestamp": "ISO8601",
  "channel": { "type": "telegram|web|discord|slack", "channelId": "string", "metadata": {} },
  "user": { "id": "unified", "channelUserId": "string", "username": "string", "displayName": "string" },
  "content": { "text": "string", "attachments": [], "messageType": "text|image|file|command" },
  "context": { "conversationId": "string", "sessionId": "string", "threadId": "string" },
  "routing": { "priority": "normal", "tags": [], "targetAgent": "" }
}
```

### 註冊與許可（個體/群組）

- 表一：allowlist（沿用，擴展字段）
  - PK: chat_id (N) 或 composite key（通道+ID）
  - username, enabled, type: user|group, channel: telegram|discord|slack|web
- 表二：identity_map（新）
  - PK: unified_user_id（如 user:tg:12345）
  - attributes: {telegram_id, discord_id, slack_id, web_id, groups: [...]}
- 表三：group_registry（新）
  - PK: group_id
  - members: [unified_user_id]
  - policies/roles: {admin, member}
- 規則：telegram 仍以 chat_id + username 雙重驗證；其他通道按平台特性補充驗證

---

## 測試策略

- 保留 telegram-agentcore-bot 下現有 69+ 測試
- 新增：
  - Adapter: 通道檢測、標準化、允許名單、事件發佈
  - Processor: 事件處理、AgentCore 回傳格式、錯誤分支
  - Router: 通道格式化、送達成功/失敗與重試
- 使用 pytest + botocore stub/moto 模擬 AWS 相依

---

## 安全與治理

- 沿用 Secrets Manager 儲存 Bot Token/Webhook Secret
- EventBridge/Lambda/SQS/DynamoDB 全面加密與最小權限
- CloudWatch Dashboard 延伸：新增事件流量、Router 送達成功率、重試與 DLQ 指標
- Telegram 特性：訊息長度限制、分段傳送、格式清理；其他通道亦採相應限制處理

---

## 專案目錄重組建議

新 mono-repo 結構（可先用子模組保留兩個 repo）：

```
agentcore-nexus/
├── adapters/                 # 改造自 telegram-lambda
│   ├── universal_adapter/
│   │   ├── src/
│   │   └── template.yaml
├── processor/                # 整合 telegram-agentcore-bot
│   ├── src/ (沿用 agents/services/tools/utils/config)
│   ├── processor_entry.py
│   └── template.yaml
├── router/
│   ├── src/ (delivery/telegram, discord, web, slack)
│   └── template.yaml
├── infra/
│   ├── eventbridge.yaml
│   ├── iam_policies.yaml
│   └── dashboards.yaml
└── docs/
    └── architecture.md
```

也可先維持兩個獨立 repo，以 EventBridge glue 鬆耦合串接，穩定後再合併。

---

## 部署與遷移建議

- 先在相同 AWS 帳號/Region 內增設 EventBridge 與新的 Processor/Router，保留現有 Telegram 流程
- 切換 telegram-lambda 的輸出至 EventBridge（同時保留 SQS 作為回退）
- 建立最小閉環（Telegram → Adapter → EventBridge → Processor → Router → Telegram）
- 通道擴展（Web/Discord/Slack）逐步導入，並增加 allowlist/identity 映射

---

## 具體實施步驟

### Step 1: 準備階段
1. 備份現有專案
2. 建立開發分支
3. 設置測試環境

### Step 2: 基礎架構升級
1. 在 telegram-lambda 中新增 EventBridge 支援
2. 修改 SAM 模板加入 UniversalEventBus
3. 實作通道檢測和訊息標準化

### Step 3: 處理層整合
1. 在 telegram-agentcore-bot 中新增 processor_entry.py
2. 建立 EventBridge 事件處理邏輯
3. 實作跨通道上下文管理

### Step 4: 回應路由實作
1. 建立 Response Router 服務
2. 實作通道特定格式化
3. 建立送達確認機制

### Step 5: 多通道擴展
1. 新增 Web API 端點
2. 實作 Discord/Slack webhook 處理
3. 建立統一註冊系統

### Step 6: 測試與優化
1. 端到端測試
2. 效能優化
3. 監控系統完善

---

## FAQ

**Q: 必須立刻合併 repo 嗎？**
A: 否。可透過 EventBridge 先鬆耦合，待穩定後再整併代碼庫

**Q: 會破壞既有 Telegram 流程嗎？**
A: 不會。保留路徑與 allowlist；切換輸出目標即可

**Q: 個體/群組註冊如何落地？**
A: 在 DynamoDB 擴增三張表（allowlist/identity_map/group_registry）與簡單後台管理 API

**Q: 成本會增加多少？**
A: EventBridge 每百萬事件約 $1，Lambda 按執行計費，整體成本增加有限

**Q: 如何確保訊息不會遺失？**
A: 透過 EventBridge 的 DLQ、重試機制和詳細的 CloudWatch 監控

---

## 結論

透過這個漸進式的整合方案，可以在保持現有功能穩定的前提下，逐步將 telegram-lambda 和 telegram-agentcore-bot 整合為一個強大的多通道 AI 助理平台。架構的事件驅動設計確保了良好的擴展性和維護性，為未來的功能擴展奠定了堅實的基礎。

---

## 附錄

### A. 完整 SAM 模板範例

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: AgentCore Nexus - Multi-channel AI Assistant Platform

Parameters:
  TelegramBotToken:
    Type: String
    NoEcho: true
    Description: Telegram Bot Token
    Default: ''

  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]

Globals:
  Function:
    Timeout: 30
    MemorySize: 256
    Runtime: python3.11
    Environment:
      Variables:
        LOG_LEVEL: INFO
        ENVIRONMENT: !Ref Environment

Resources:
  # EventBridge Bus
  UniversalEventBus:
    Type: AWS::Events::EventBus
    Properties:
      Name: !Sub '${AWS::StackName}-events'

  # Secrets Manager
  TelegramSecrets:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: !Sub '${AWS::StackName}-secrets'
      Description: Telegram Bot Token and Webhook Secret Token
      GenerateSecretString:
        SecretStringTemplate: !Sub '{"bot_token": "${TelegramBotToken}"}'
        GenerateStringKey: 'webhook_secret_token'
        PasswordLength: 64
        ExcludeCharacters: '!@#$%^&*()_+-=[]{}|;:,.<>?/~`"''\ '

  # Universal Message Adapter
  UniversalAdapterFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub '${AWS::StackName}-adapter'
      CodeUri: adapters/universal_adapter/src/
      Handler: handler.lambda_handler
      Environment:
        Variables:
          TELEGRAM_SECRETS_ARN: !Ref TelegramSecrets
          ALLOWLIST_TABLE_NAME: !Ref AllowlistTable
          EVENT_BUS_NAME: !Ref UniversalEventBus
      Policies:
        - DynamoDBReadPolicy:
            TableName: !Ref AllowlistTable
        - Statement:
            - Effect: Allow
              Action: 
                - secretsmanager:GetSecretValue
                - events:PutEvents
              Resource:
                - !Ref TelegramSecrets
                - !GetAtt UniversalEventBus.Arn
      Events:
        TelegramWebhook:
          Type: Api
          Properties:
            Path: /telegram/webhook
            Method: POST
            RestApiId: !Ref MultiChannelApi
        WebApi:
          Type: Api
          Properties:
            Path: /web/api
            Method: POST
            RestApiId: !Ref MultiChannelApi

  # Agent Processor
  AgentProcessorFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub '${AWS::StackName}-processor'
      CodeUri: processor/src/
      Handler: processor_entry.handler
      Timeout: 300
      MemorySize: 512
      Environment:
        Variables:
          EVENT_BUS_NAME: !Ref UniversalEventBus
          BEDROCK_AGENTCORE_MEMORY_ID: !Ref AWS::NoValue
      Policies:
        - Statement:
            - Effect: Allow
              Action: 
                - events:PutEvents
                - bedrock:InvokeAgent
                - bedrock:Retrieve
              Resource: '*'

  # Response Router
  ResponseRouterFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub '${AWS::StackName}-router'
      CodeUri: router/src/
      Handler: response_router.handler
      Environment:
        Variables:
          TELEGRAM_SECRETS_ARN: !Ref TelegramSecrets
      Policies:
        - Statement:
            - Effect: Allow
              Action: secretsmanager:GetSecretValue
              Resource: !Ref TelegramSecrets

  # API Gateway
  MultiChannelApi:
    Type: AWS::Serverless::Api
    Properties:
      Name: !Sub '${AWS::StackName}-api'
      StageName: Prod
      Description: Multi-channel API Gateway

  # DynamoDB Tables
  AllowlistTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub '${AWS::StackName}-allowlist'
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: chat_id
          AttributeType: N
      KeySchema:
        - AttributeName: chat_id
          KeyType: HASH
      SSESpecification:
        SSEEnabled: true

  IdentityMapTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub '${AWS::StackName}-identity-map'
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: unified_user_id
          AttributeType: S
      KeySchema:
        - AttributeName: unified_user_id
          KeyType: HASH
      SSESpecification:
        SSEEnabled: true

  GroupRegistryTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub '${AWS::StackName}-groups'
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: group_id
          AttributeType: S
      KeySchema:
        - AttributeName: group_id
          KeyType: HASH
      SSESpecification:
        SSEEnabled: true

  # EventBridge Rules
  MessageReceivedRule:
    Type: AWS::Events::Rule
    Properties:
      EventBusName: !Ref UniversalEventBus
      EventPattern:
        source: ["universal-adapter"]
        detail-type: ["message.received"]
      Targets:
        - Arn: !GetAtt AgentProcessorFunction.Arn
          Id: "AgentProcessorTarget"

  MessageCompletedRule:
    Type: AWS::Events::Rule
    Properties:
      EventBusName: !Ref UniversalEventBus
      EventPattern:
        source: ["agent-processor"]
        detail-type: ["message.completed"]
      Targets:
        - Arn: !GetAtt ResponseRouterFunction.Arn
          Id: "ResponseRouterTarget"

  # Lambda Permissions for EventBridge
  AgentProcessorPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref AgentProcessorFunction
      Action: lambda:InvokeFunction
      Principal: events.amazonaws.com
      SourceArn: !GetAtt MessageReceivedRule.Arn

  ResponseRouterPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref ResponseRouterFunction
      Action: lambda:InvokeFunction
      Principal: events.amazonaws.com
      SourceArn: !GetAtt MessageCompletedRule.Arn

Outputs:
  ApiGatewayUrl:
    Description: API Gateway URL
    Value: !Sub 'https://${MultiChannelApi}.execute-api.${AWS::Region}.amazonaws.com/Prod'

  TelegramWebhookUrl:
    Description: Telegram Webhook URL
    Value: !Sub 'https://${MultiChannelApi}.execute-api.${AWS::Region}.amazonaws.com/Prod/telegram/webhook'

  EventBusArn:
    Description: EventBridge Bus ARN
    Value: !GetAtt UniversalEventBus.Arn

  SecretsArn:
    Description: Secrets Manager ARN
    Value: !Ref TelegramSecrets
```

### B. 測試程式範例

```python
# tests/test_universal_adapter.py
import json
import pytest
from unittest.mock import Mock, patch
from src.handler import lambda_handler, detect_channel, normalize_message

class TestUniversalAdapter:

    def test_detect_channel_telegram(self):
        event = {"path": "/telegram/webhook"}
        assert detect_channel(event) == "telegram"

    def test_detect_channel_web(self):
        event = {"path": "/web/api"}
        assert detect_channel(event) == "web"

    def test_normalize_telegram_message(self):
        raw = {
            "channel": "telegram",
            "data": {
                "message": {
                    "from": {"id": 12345, "username": "testuser", "first_name": "Test"},
                    "chat": {"id": 67890},
                    "text": "Hello World"
                }
            },
            "headers": {}
        }

        result = normalize_message(raw, "telegram")

        assert result["channel"]["type"] == "telegram"
        assert result["channel"]["channelId"] == "67890"
        assert result["user"]["username"] == "testuser"
        assert result["content"]["text"] == "Hello World"

    @patch('src.handler.check_allowed')
    @patch('src.handler.evb')
    def test_lambda_handler_success(self, mock_evb, mock_check_allowed):
        mock_check_allowed.return_value = True
        mock_evb.put_events.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

        event = {
            "path": "/telegram/webhook",
            "body": json.dumps({
                "message": {
                    "from": {"id": 12345, "username": "testuser"},
                    "chat": {"id": 67890},
                    "text": "test message"
                }
            })
        }

        result = lambda_handler(event, {})

        assert result["statusCode"] == 200
        mock_evb.put_events.assert_called_once()

    @patch('src.handler.check_allowed')
    def test_lambda_handler_forbidden(self, mock_check_allowed):
        mock_check_allowed.return_value = False

        event = {
            "path": "/telegram/webhook",
            "body": json.dumps({
                "message": {
                    "from": {"id": 12345, "username": "blocked_user"},
                    "chat": {"id": 67890},
                    "text": "test message"
                }
            })
        }

        result = lambda_handler(event, {})

        assert result["statusCode"] == 403
```

---

本文件提供了完整的 AgentCore Nexus 整合改造指南，包含架構設計、實作細節、部署步驟和測試策略。可作為專案開發的藍圖和參考文件。
