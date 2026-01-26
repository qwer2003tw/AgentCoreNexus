# 管理員功能 - CloudFormation 基礎設施計劃

**版本**: 1.0  
**創建時間**: 2026-01-26

---

## 🎯 目標

為管理員 API 添加必要的 Lambda Functions 和配置到 `web-adapter/infrastructure/web-channel-template.yaml`

---

## 📦 需要添加的 Lambda Functions

### 1. AdminConversationsFunction

**用途**: 對話列表和詳情 API

```yaml
AdminConversationsFunction:
  Type: AWS::Serverless::Function
  Properties:
    FunctionName: !Sub '${AWS::StackName}-admin-conversations'
    CodeUri: ../lambdas/rest/
    Handler: admin.conversations_handler.handler
    Description: Admin API for viewing and searching conversations
    MemorySize: 512  # 較大，用於查詢和過濾
    Timeout: 30
    Layers:
      - arn:aws:lambda:us-west-2:190825685292:layer:agentcore-shared-services:2
    Environment:
      Variables:
        # 必要的環境變數
        CONVERSATION_HISTORY_TABLE: !ImportValue agentcore-conversation-storage-dev-ConversationHistoryTableName
        CONVERSATION_METADATA_TABLE: !ImportValue agentcore-conversation-storage-dev-ConversationMetadataTableName
        USER_BINDINGS_TABLE: !Ref UserBindingsTable
        ADMIN_AUDIT_LOGS_TABLE: !ImportValue agentcore-admin-panel-dev-AdminAuditLogsTableName
        ADMIN_SYSTEM_CONFIG_TABLE: !ImportValue agentcore-admin-panel-dev-AdminSystemConfigTableName
    Policies:
      - Statement:
          # Conversation History（讀取）
          - Effect: Allow
            Action:
              - dynamodb:Query
              - dynamodb:GetItem
              - dynamodb:Scan  # 用於搜尋（謹慎使用）
            Resource:
              - !Sub 'arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/agentcore-conversation-history-*'
              - !Sub 'arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/agentcore-conversation-history-*/index/*'
              - !Sub 'arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/agentcore-conversation-metadata-*'
          # User Bindings（讀取）
          - Effect: Allow
            Action:
              - dynamodb:Query
              - dynamodb:GetItem
            Resource:
              - !GetAtt UserBindingsTable.Arn
              - !Sub '${UserBindingsTable.Arn}/index/*'
          # Audit Logs（寫入）
          - Effect: Allow
            Action:
              - dynamodb:PutItem
            Resource:
              - !Sub 'arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/agentcore-admin-audit-logs-*'
          # System Config（讀取）
          - Effect: Allow
            Action:
              - dynamodb:GetItem
            Resource:
              - !Sub 'arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/agentcore-admin-system-config-*'
    Events:
      GetConversations:
        Type: Api
        Properties:
          RestApiId: !Ref RestApi
          Path: /admin/conversations
          Method: GET
          Auth:
            Authorizer: MyLambdaTokenAuthorizer
      GetConversationDetail:
        Type: Api
        Properties:
          RestApiId: !Ref RestApi
          Path: /admin/conversations/{id}
          Method: GET
          Auth:
            Authorizer: MyLambdaTokenAuthorizer
      SearchConversations:
        Type: Api
        Properties:
          RestApiId: !Ref RestApi
          Path: /admin/conversations/search
          Method: GET
          Auth:
            Authorizer: MyLambdaTokenAuthorizer
```

---

### 2. AdminAttachmentsFunction

**用途**: 附件預覽 API

```yaml
AdminAttachmentsFunction:
  Type: AWS::Serverless::Function
  Properties:
    FunctionName: !Sub '${AWS::StackName}-admin-attachments'
    CodeUri: ../lambdas/rest/
    Handler: admin.attachments_handler.handler
    Description: Admin API for attachment preview
    MemorySize: 256
    Timeout: 15
    Layers:
      - arn:aws:lambda:us-west-2:190825685292:layer:agentcore-shared-services:2
    Environment:
      Variables:
        ATTACHMENTS_BUCKET: !Ref AttachmentsBucket
        TELEGRAM_FILES_BUCKET: !ImportValue agentcore-telegram-adapter-FileStorageBucket
        ADMIN_AUDIT_LOGS_TABLE: !ImportValue agentcore-admin-panel-dev-AdminAuditLogsTableName
    Policies:
      - Statement:
          # S3 讀取（生成 presigned URL）
          - Effect: Allow
            Action:
              - s3:GetObject
            Resource:
              - !Sub '${AttachmentsBucket.Arn}/*'
              - !Sub 'arn:aws:s3:::telegram-bot-files-${AWS::AccountId}-*/*'
          # Audit Logs
          - Effect: Allow
            Action:
              - dynamodb:PutItem
            Resource:
              - !Sub 'arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/agentcore-admin-audit-logs-*'
    Events:
      GetAttachmentPreview:
        Type: Api
        Properties:
          RestApiId: !Ref RestApi
          Path: /admin/attachments/{key}/preview
          Method: GET
          Auth:
            Authorizer: MyLambdaTokenAuthorizer
```

---

### 3. AdminSummaryFunction

**用途**: AI 摘要生成 API

```yaml
AdminSummaryFunction:
  Type: AWS::Serverless::Function
  Properties:
    FunctionName: !Sub '${AWS::StackName}-admin-summary'
    CodeUri: ../lambdas/rest/
    Handler: admin.summary_handler.handler
    Description: Admin API for generating AI summaries
    MemorySize: 1024  # 較大，用於處理長對話
    Timeout: 60       # 較長，等待 Bedrock
    Layers:
      - arn:aws:lambda:us-west-2:190825685292:layer:agentcore-shared-services:2
    Environment:
      Variables:
        CONVERSATION_HISTORY_TABLE: !ImportValue agentcore-conversation-storage-dev-ConversationHistoryTableName
        CONVERSATION_SUMMARIES_TABLE: !ImportValue agentcore-admin-panel-dev-ConversationSummariesTableName
        ADMIN_AUDIT_LOGS_TABLE: !ImportValue agentcore-admin-panel-dev-AdminAuditLogsTableName
        BEDROCK_MODEL_ID: anthropic.claude-3-haiku-20240307-v1:0  # 使用 Haiku（便宜）
    Policies:
      - Statement:
          # Conversation History（讀取）
          - Effect: Allow
            Action:
              - dynamodb:Query
              - dynamodb:GetItem
            Resource:
              - !Sub 'arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/agentcore-conversation-history-*'
              - !Sub 'arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/agentcore-conversation-history-*/index/*'
          # Conversation Summaries（讀寫）
          - Effect: Allow
            Action:
              - dynamodb:GetItem
              - dynamodb:PutItem
              - dynamodb:UpdateItem
            Resource:
              - !Sub 'arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/agentcore-conversation-summaries-*'
          # Bedrock（調用 AI）
          - Effect: Allow
            Action:
              - bedrock:InvokeModel
            Resource: '*'
          # Audit Logs
          - Effect: Allow
            Action:
              - dynamodb:PutItem
            Resource:
              - !Sub 'arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/agentcore-admin-audit-logs-*'
    Events:
      GenerateSummary:
        Type: Api
        Properties:
          RestApiId: !Ref RestApi
          Path: /admin/conversations/{id}/summarize
          Method: POST
          Auth:
            Authorizer: MyLambdaTokenAuthorizer
      GetSummary:
        Type: Api
        Properties:
          RestApiId: !Ref RestApi
          Path: /admin/conversations/{id}/summary
          Method: GET
          Auth:
            Authorizer: MyLambdaTokenAuthorizer
```

---

### 4. AdminAuditLogsFunction

**用途**: 審計日誌查詢 API

```yaml
AdminAuditLogsFunction:
  Type: AWS::Serverless::Function
  Properties:
    FunctionName: !Sub '${AWS::StackName}-admin-audit-logs'
    CodeUri: ../lambdas/rest/
    Handler: admin.audit_logs_handler.handler
    Description: Admin API for querying audit logs
    MemorySize: 256
    Timeout: 30
    Layers:
      - arn:aws:lambda:us-west-2:190825685292:layer:agentcore-shared-services:2
    Environment:
      Variables:
        ADMIN_AUDIT_LOGS_TABLE: !ImportValue agentcore-admin-panel-dev-AdminAuditLogsTableName
    Policies:
      - Statement:
          # Audit Logs（讀取和記錄查看操作）
          - Effect: Allow
            Action:
              - dynamodb:Query
              - dynamodb:GetItem
              - dynamodb:PutItem
            Resource:
              - !Sub 'arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/agentcore-admin-audit-logs-*'
              - !Sub 'arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/agentcore-admin-audit-logs-*/index/*'
    Events:
      GetAuditLogs:
        Type: Api
        Properties:
          RestApiId: !Ref RestApi
          Path: /admin/audit-logs
          Method: GET
          Auth:
            Authorizer: MyLambdaTokenAuthorizer
```

---

## 📊 總結

### 需要添加的資源
- **4 個新 Lambda Functions**
- **9 個新 API Gateway Routes**
- **環境變數配置**（連接到現有 tables）
- **IAM 權限配置**（最小權限原則）

### CloudWatch Log Groups（自動創建）
- /aws/lambda/{FunctionName}（14 天保留）

---

## 🚀 部署策略

### 部署步驟
1. 更新 `web-adapter/infrastructure/web-channel-template.yaml`
2. `cd web-adapter/infrastructure && sam build -t web-channel-template.yaml`
3. `sam deploy --stack-name agentcore-web-adapter ...`
4. 驗證新 Lambda 狀態
5. 測試新 API endpoints

### 回滾策略
- CloudFormation 自動回滾（如果失敗）
- Lambda 版本別名（如需要）
- Git 回退代碼

### 預計時間
- 配置更新：30 分鐘
- 部署：5-10 分鐘
- 驗證：15 分鐘
- **總計**：1 小時

---

**版本**: 1.0  
**狀態**: 設計完成，準備實施
