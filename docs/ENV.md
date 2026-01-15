# Environment Variables Reference

Complete reference for all environment variables used in AgentCoreNexus components.

## 🤖 ai-processor

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `EVENT_BUS_NAME` | EventBridge bus for responses | `agentcore-telegram-adapter-events` |
| `BEDROCK_MODEL_ID` | Claude model identifier | `anthropic.claude-3-5-sonnet-20241022-v2:0` |
| `BEDROCK_MEMORY_ID` | Memory store ID | `ABCDEFG12345` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BROWSER_ENABLED` | Enable browser tool | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `AWS_REGION` | AWS region | `us-west-2` |

### Configuration Example

```yaml
# template.yaml
Environment:
  Variables:
    EVENT_BUS_NAME: !ImportValue agentcore-telegram-adapter-EventBusName
    BEDROCK_MODEL_ID: anthropic.claude-3-5-sonnet-20241022-v2:0
    BEDROCK_MEMORY_ID: !Ref MemoryIdParameter
    BROWSER_ENABLED: 'true'
    LOG_LEVEL: INFO
```

---

## 📱 telegram-adapter

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_SECRETS_ARN` | Secrets Manager ARN | `arn:aws:secretsmanager:...` |
| `EVENT_BUS_NAME` | EventBridge bus name | `agentcore-telegram-adapter-events` |
| `ALLOWLIST_TABLE_NAME` | DynamoDB allowlist table | `telegram-allowlist` |
| `STACK_NAME` | Stack name for /info | `agentcore-telegram-adapter` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENABLE_FILE_READER` | Enable file reading | `false` |

### Secrets Format

**Secret Name**: `telegram-adapter-receiver-secrets`

```json
{
  "bot_token": "1550029310:AAG-DV9...",
  "webhook_secret_token": "r1JU5g0F..."
}
```

---

## 🌐 web-adapter

### WebSocket Functions

| Variable | Description | Example |
|----------|-------------|---------|
| `CONNECTIONS_TABLE` | WebSocket connections | `agentcore-web-adapter-websocket-connections` |
| `WEB_USERS_TABLE` | Web users | `agentcore-web-adapter-web-users` |
| `BINDINGS_TABLE` | User bindings | `agentcore-web-adapter-user-bindings` |
| `JWT_SECRET_ARN` | JWT signing secret | `arn:aws:secretsmanager:...` |
| `EVENT_BUS_NAME` | EventBridge bus | `agentcore-telegram-adapter-events` |

### REST API Functions

| Variable | Description | Example |
|----------|-------------|---------|
| `CONVERSATIONS_TABLE` | Conversations | `agentcore-web-adapter-conversations` |
| `HISTORY_TABLE` | Message history | `agentcore-web-adapter-conversation-history` |
| `ATTACHMENTS_BUCKET` | S3 bucket for files | `agentcore-web-adapter-attachments-...` |

### Frontend Environment

**File**: `web-adapter/frontend/.env`

```bash
VITE_API_ENDPOINT=https://xxx.execute-api.us-west-2.amazonaws.com/prod
VITE_WS_ENDPOINT=wss://yyy.execute-api.us-west-2.amazonaws.com/prod
```

---

## 🔧 Local Development

### Setup .env Files

**ai-processor/.env**:
```bash
# Copy from .env.example
AWS_PROFILE=default
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_MEMORY_ID=your-memory-id
LOG_LEVEL=DEBUG
```

**telegram-adapter/.env**:
```bash
# For local testing only
BOT_TOKEN=your-bot-token
WEBHOOK_SECRET=your-webhook-secret
```

**web-adapter/frontend/.env**:
```bash
# API endpoints (from CloudFormation outputs)
VITE_API_ENDPOINT=your-rest-api-endpoint
VITE_WS_ENDPOINT=your-websocket-endpoint
```

---

## 📊 Getting Values from AWS

### From CloudFormation Outputs

```bash
# Get all outputs from a stack
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs'

# Get specific output
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`RestApiEndpoint`].OutputValue' \
  --output text
```

### From Secrets Manager

```bash
# Get bot token
aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-adapter-receiver-secrets \
  --query SecretString --output text | jq -r .bot_token
```

### From DynamoDB

```bash
# Check table name
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-telegram-adapter \
  --query 'Stacks[0].Outputs[?contains(OutputKey,`Table`)].OutputValue'
```

---

## ⚙️ Configuration Best Practices

### 1. Never Hardcode Secrets
```yaml
# ❌ Bad
Environment:
  Variables:
    API_KEY: 'sk-1234567890abcdef'

# ✅ Good
Environment:
  Variables:
    API_KEY_ARN: !Ref MySecret
```

### 2. Use Parameter Store for Non-Secret Config
```yaml
Parameters:
  ModelId:
    Type: String
    Default: anthropic.claude-3-5-sonnet-20241022-v2:0
```

### 3. Use Exports for Cross-Stack References
```yaml
# In stack A
Outputs:
  EventBusName:
    Export:
      Name: !Sub '${AWS::StackName}-EventBusName'

# In stack B
Environment:
  Variables:
    BUS: !ImportValue agentcore-telegram-adapter-EventBusName
```

---

## 🚨 Troubleshooting

### Lambda Can't Access Secret
```bash
# Check IAM policy
aws lambda get-function --function-name FUNCTION_NAME \
  --query 'Configuration.Role'

# Check policy allows secretsmanager:GetSecretValue
```

### Environment Variable Not Set
```bash
# Check current value
aws lambda get-function-configuration \
  --function-name FUNCTION_NAME \
  --query 'Environment.Variables'
```

### Wrong Region
```bash
# All components should use us-west-2
# Check with:
aws configure get region
```

---

## 📚 Related Documentation

- [Deployment Guide](./deployment-guide.md)
- [Stack Management](./STACK_MANAGEMENT.md)
- [Architecture Guide](./architecture-guide.md)

---

**Maintained by**: AgentCoreNexus Team  
**Last Updated**: 2026-01-15