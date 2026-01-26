# Adding a New Channel Adapter

Complete guide for adding support for new communication channels (Discord, Slack, Line, WhatsApp, etc.) to AgentCoreNexus.

## 🎯 Overview

AgentCoreNexus uses a **channel adapter pattern** where each communication platform has its own adapter that:
1. Receives messages from the platform
2. Converts to Universal Message format
3. Sends to AI processor via EventBridge
4. Routes responses back to the platform

**Existing Adapters**:
- ✅ **telegram-adapter**: Telegram Bot API
- ✅ **web-adapter**: WebSocket + REST API

---

## 📋 Prerequisites

Before starting, ensure you have:
- [ ] AWS account with appropriate permissions
- [ ] Understanding of the target platform's API
- [ ] API credentials for the platform
- [ ] Knowledge of Python 3.12 and AWS Lambda
- [ ] Familiarity with AgentCoreNexus architecture

---

## 🏗️ Architecture Pattern

### Standard Components

Every channel adapter should include:

1. **Webhook Receiver** (or equivalent)
   - Receives messages from platform
   - Validates authenticity
   - Converts to Universal Message format

2. **Response Router**
   - Listens to EventBridge for `message.completed`
   - Converts response to platform format
   - Sends back to user

3. **CloudFormation Template**
   - API Gateway (if needed)
   - Lambda functions
   - DynamoDB tables (if needed)
   - Proper IAM roles

---

## 🚀 Step-by-Step Guide

### Step 1: Create Directory Structure

```bash
mkdir -p discord-adapter/src/{commands,utils}
mkdir -p discord-adapter/router
mkdir -p discord-adapter/tests/{unit,integration,e2e}

cd discord-adapter
```

**Directory Structure**:
```
discord-adapter/
├── template.yaml          # CloudFormation/SAM template
├── requirements.txt       # Python dependencies
├── README.md              # Component documentation
├── src/                   # Main receiver code
│   ├── handler.py         # Lambda entry point
│   ├── discord_client.py  # Platform API client
│   ├── converter.py       # Message format converter
│   ├── commands/          # Platform-specific commands
│   └── utils/             # Utilities
├── router/                # Response router
│   └── response_router.py
└── tests/                 # Tests
    ├── unit/
    ├── integration/
    └── e2e/
```

---

### Step 2: Implement Message Converter

**File**: `src/converter.py`

```python
"""Convert Discord messages to Universal Message format"""
import json
from datetime import datetime
from typing import Dict, Any

def convert_discord_to_universal(discord_message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Discord message to Universal Message format.
    
    See: schemas/message.schema.json
    """
    return {
        "messageId": discord_message["id"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "channel": {
            "type": "discord",
            "channelId": discord_message["channel_id"],
            "metadata": {
                "guild_id": discord_message.get("guild_id"),
                "channel_type": discord_message.get("channel_type")
            }
        },
        "user": {
            "id": get_unified_user_id(discord_message["author"]["id"]),
            "channelUserId": discord_message["author"]["id"],
            "username": discord_message["author"]["username"],
            "displayName": discord_message["author"].get("global_name", 
                          discord_message["author"]["username"])
        },
        "content": {
            "text": discord_message["content"],
            "messageType": determine_message_type(discord_message),
            "attachments": convert_attachments(discord_message.get("attachments", []))
        }
    }

def get_unified_user_id(discord_user_id: str) -> str:
    """Get or create unified user ID for Discord user"""
    # Query user bindings table
    # Return existing or create new unified ID
    pass

def determine_message_type(message: Dict[str, Any]) -> str:
    """Determine message type from Discord message"""
    if message.get("attachments"):
        first_attachment = message["attachments"][0]
        content_type = first_attachment.get("content_type", "")
        if content_type.startswith("image/"):
            return "image"
        elif content_type.startswith("video/"):
            return "video"
        elif content_type.startswith("audio/"):
            return "audio"
        return "file"
    return "text"

def convert_attachments(discord_attachments: list) -> list:
    """Convert Discord attachments to universal format"""
    return [
        {
            "type": att.get("content_type", "").split("/")[0],
            "url": att["url"],
            "filename": att["filename"],
            "mimeType": att.get("content_type"),
            "size": att.get("size")
        }
        for att in discord_attachments
    ]
```

---

### Step 3: Create Webhook Handler

**File**: `src/handler.py`

```python
"""Discord webhook receiver Lambda function"""
import json
import os
import boto3
from aws_lambda_powertools import Logger
from converter import convert_discord_to_universal

logger = Logger()
events_client = boto3.client('events')

def handler(event, context):
    """
    Handle Discord webhooks (Interactions API)
    """
    try:
        # 1. Parse Discord event
        body = json.loads(event.get('body', '{}'))
        
        # 2. Verify signature (Discord security)
        if not verify_discord_signature(event):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Invalid signature'})
            }
        
        # 3. Handle Discord interaction types
        interaction_type = body.get('type')
        
        if interaction_type == 1:  # PING
            return {'statusCode': 200, 'body': json.dumps({'type': 1})}
        
        # 4. Convert to Universal Message
        universal_message = convert_discord_to_universal(body)
        
        # 5. Validate against schema (optional but recommended)
        # validate_message_schema(universal_message)
        
        # 6. Send to EventBridge
        response = events_client.put_events(
            Entries=[{
                'Source': 'discord-adapter',
                'DetailType': 'message.received',
                'Detail': json.dumps(universal_message),
                'EventBusName': os.environ['EVENT_BUS_NAME']
            }]
        )
        
        logger.info("Message sent to EventBridge", extra={
            "message_id": universal_message["messageId"],
            "user_id": universal_message["user"]["id"]
        })
        
        # 7. Return success to Discord
        return {
            'statusCode': 200,
            'body': json.dumps({
                'type': 4,  # CHANNEL_MESSAGE_WITH_SOURCE
                'data': {
                    'content': 'Processing your message...'
                }
            })
        }
        
    except Exception as e:
        logger.exception("Error handling Discord webhook")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def verify_discord_signature(event: dict) -> bool:
    """Verify Discord request signature"""
    # Implement Discord signature verification
    # See: https://discord.com/developers/docs/interactions/receiving-and-responding
    pass
```

---

### Step 4: Create Response Router

**File**: `router/response_router.py`

```python
"""Route AI responses back to Discord"""
import json
import os
import boto3
import requests
from aws_lambda_powertools import Logger

logger = Logger()

def handler(event, context):
    """
    Handle message.completed events and send to Discord
    """
    try:
        detail = event['detail']
        
        # Extract response data
        message_id = detail['messageId']
        response_text = detail['response']['text']
        channel_id = detail['channel']['channelId']
        
        # Get Discord bot token
        secrets_client = boto3.client('secretsmanager')
        secret = secrets_client.get_secret_value(
            SecretId=os.environ['DISCORD_SECRETS_ARN']
        )
        bot_token = json.loads(secret['SecretString'])['bot_token']
        
        # Send to Discord
        discord_api_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        response = requests.post(
            discord_api_url,
            headers={'Authorization': f'Bot {bot_token}'},
            json={'content': response_text}
        )
        
        response.raise_for_status()
        logger.info("Response sent to Discord", extra={"message_id": message_id})
        
    except Exception as e:
        logger.exception("Error routing response to Discord")
        raise
```

---

### Step 5: Create CloudFormation Template

**File**: `template.yaml`

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: AgentCoreNexus - Discord Channel Adapter

Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]

Resources:
  # EventBridge Bus (or use existing)
  DiscordEventBus:
    Type: AWS::Events::EventBus
    Properties:
      Name: !Sub '${AWS::StackName}-events'

  # Webhook Receiver Lambda
  DiscordReceiverFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub '${AWS::StackName}-receiver'
      CodeUri: src/
      Handler: handler.handler
      Runtime: python3.12
      Timeout: 30
      Environment:
        Variables:
          EVENT_BUS_NAME: !Ref DiscordEventBus
          DISCORD_SECRETS_ARN: !Ref DiscordSecrets
      Policies:
        - EventBridgePutEventsPolicy:
            EventBusName: !Ref DiscordEventBus
        - AWSSecretsManagerGetSecretValuePolicy:
            SecretArn: !Ref DiscordSecrets
      Events:
        WebhookApi:
          Type: Api
          Properties:
            Path: /webhook
            Method: POST

  # Response Router Lambda
  DiscordResponseRouterFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub '${AWS::StackName}-response-router'
      CodeUri: router/
      Handler: response_router.handler
      Runtime: python3.12
      Timeout: 60
      Environment:
        Variables:
          DISCORD_SECRETS_ARN: !Ref DiscordSecrets
      Policies:
        - AWSSecretsManagerGetSecretValuePolicy:
            SecretArn: !Ref DiscordSecrets
      Events:
        MessageCompleted:
          Type: EventBridgeRule
          Properties:
            EventBusName: !ImportValue agentcore-telegram-adapter-EventBusName
            Pattern:
              source: [agent-processor]
              detail-type: [message.completed]
              detail:
                channel:
                  type: [discord]

  # Secrets
  DiscordSecrets:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: !Sub '${AWS::StackName}-secrets'
      Description: Discord bot credentials

Outputs:
  WebhookUrl:
    Description: Discord webhook URL
    Value: !Sub 'https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/Prod/webhook'
    Export:
      Name: !Sub '${AWS::StackName}-WebhookUrl'
```

---

### Step 6: Testing

**Create**: `tests/unit/test_converter.py`

```python
import pytest
from src.converter import convert_discord_to_universal

def test_text_message_conversion():
    discord_msg = {
        "id": "123456",
        "channel_id": "789",
        "author": {
            "id": "user123",
            "username": "testuser",
            "global_name": "Test User"
        },
        "content": "Hello world"
    }
    
    result = convert_discord_to_universal(discord_msg)
    
    assert result["messageId"] == "123456"
    assert result["channel"]["type"] == "discord"
    assert result["user"]["username"] == "testuser"
    assert result["content"]["text"] == "Hello world"
```

---

### Step 7: Deploy

```bash
# Build and deploy
cd discord-adapter
sam build
sam deploy \
  --stack-name agentcore-discord-adapter \
  --region us-west-2 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3
```

---

### Step 8: Configure Platform

**For Discord**:
1. Go to Discord Developer Portal
2. Create application and bot
3. Copy bot token to Secrets Manager
4. Set webhook URL in Discord settings
5. Subscribe to necessary events

---

## ✅ Checklist

### Implementation
- [ ] Message converter implements Universal Message schema
- [ ] Webhook handler validates platform signatures
- [ ] Response router handles platform-specific formatting
- [ ] Proper error handling and logging
- [ ] IAM permissions configured correctly

### Testing
- [ ] Unit tests for converter (>80% coverage)
- [ ] Integration tests with mock platform API
- [ ] E2E tests with real platform (if possible)
- [ ] Load testing for scalability

### Documentation
- [ ] README.md with setup instructions
- [ ] Update main docs/README.md
- [ ] Add to docs/architecture-guide.md
- [ ] Update schemas/README.md with example

### Deployment
- [ ] CloudFormation template validates
- [ ] Secrets properly configured
- [ ] EventBridge connections work
- [ ] Cross-stack imports correct
- [ ] Monitoring and alarms set up

---

## 🎨 Platform-Specific Considerations

### Discord
- Uses Interactions API (webhooks)
- Requires signature verification
- 3-second response timeout
- Supports slash commands

### Slack
- Multiple webhook types (Events API, Slash Commands)
- Requires challenge-response for verification
- Uses Block Kit for rich messages
- Rate limiting considerations

### WhatsApp Business API
- Webhook verification token
- Template messages required
- Media handling specifics
- Phone number as user ID

### Line
- Webhook signature verification
- Rich messages and carousels
- User ID format considerations
- Reply token system

---

## 📊 Universal Message Format

All adapters must produce messages following `schemas/message.schema.json`:

```python
def convert_platform_to_universal(platform_message):
    return {
        "messageId": "...",        # Platform's message ID
        "timestamp": "...",         # ISO 8601 format
        "channel": {
            "type": "discord",      # Your platform type
            "channelId": "...",     # Platform channel/chat ID
            "metadata": {}          # Platform-specific data
        },
        "user": {
            "id": "...",            # Unified user ID (from bindings)
            "channelUserId": "...", # Platform user ID
            "username": "...",      # Display name
            "displayName": "..."    # Friendly name
        },
        "content": {
            "text": "...",
            "messageType": "text",  # text|image|file|video|audio
            "attachments": []
        }
    }
```

**Validate** with jsonschema:
```python
import jsonschema

with open('schemas/message.schema.json') as f:
    schema = json.load(f)

jsonschema.validate(instance=universal_message, schema=schema)
```

---

## 🔗 Integration Points

### 1. Send Messages to AI Processor

```python
events_client.put_events(
    Entries=[{
        'Source': 'discord-adapter',  # Your adapter name
        'DetailType': 'message.received',
        'Detail': json.dumps(universal_message),
        'EventBusName': os.environ['EVENT_BUS_NAME']
    }]
)
```

### 2. Receive Responses

Listen for EventBridge events:
```yaml
Events:
  MessageCompleted:
    Type: EventBridgeRule
    Properties:
      EventBusName: !ImportValue agentcore-telegram-adapter-EventBusName
      Pattern:
        source: [agent-processor]
        detail-type: [message.completed]
        detail:
          channel:
            type: [discord]  # Your platform type
```

### 3. Update Makefile

Add your adapter to root Makefile:
```makefile
DISCORD_STACK = agentcore-discord-adapter

deploy-discord:
	cd discord-adapter && \
	sam build && \
	sam deploy --stack-name $(DISCORD_STACK) ...

test-discord:
	cd discord-adapter && \
	python3.12 -m pytest tests/ -v
```

---

## 🧪 Testing Strategy

### Unit Tests
- Test message conversion
- Test validation logic
- Test error handling
- Mock all AWS services

### Integration Tests
- Test with mock platform API
- Test EventBridge publishing
- Test IAM permissions
- Use moto for AWS mocks

### E2E Tests
- Test complete message flow
- Use real platform (test bot)
- Verify response routing
- Test all message types

---

## 📚 Example: Minimal Viable Adapter

See `telegram-adapter/` for a complete reference implementation.

**Key Files to Reference**:
- `telegram-adapter/src/handler.py` - Webhook receiver pattern
- `telegram-adapter/router/response_router.py` - Response routing
- `telegram-adapter/template.yaml` - CloudFormation structure
- `telegram-adapter/tests/` - Testing approach

---

## 🚨 Common Pitfalls

### 1. Forgetting Signature Verification
**Risk**: Security vulnerability  
**Solution**: Always verify platform signatures

### 2. Not Using Universal Message Format
**Risk**: Can't integrate with AI processor  
**Solution**: Follow schemas/message.schema.json exactly

### 3. Hardcoding Values
**Risk**: Not portable across environments  
**Solution**: Use environment variables and parameters

### 4. Missing IAM Permissions
**Risk**: Lambda fails at runtime  
**Solution**: Test permissions thoroughly

### 5. Not Handling Platform Rate Limits
**Risk**: API calls fail  
**Solution**: Implement exponential backoff

---

## 📈 Going to Production

### Pre-Launch Checklist
- [ ] Load testing completed
- [ ] Security review passed
- [ ] Monitoring and alarms configured
- [ ] Runbook created
- [ ] Cost estimation done
- [ ] Rollback plan ready

### Post-Launch Monitoring
- Track message volume and latency
- Monitor error rates
- Watch costs
- Gather user feedback
- Plan optimizations

---

## 🤝 Contributing Your Adapter

Once your adapter is complete:
1. Create PR to main repository
2. Include comprehensive tests
3. Update documentation
4. Add usage examples
5. Follow naming standards (`.clinerules/rules/naming-standards.md`)

---

## 📚 Related Documentation

- [Architecture Guide](./architecture-guide.md)
- [Universal Message Schema](../schemas/README.md)
- [Environment Variables](./ENV.md)
- [Deployment Guide](./deployment-guide.md)
- [Naming Standards](../.clinerules/rules/naming-standards.md)

---

## 💡 Need Help?

- Review existing adapters (telegram-adapter, web-adapter)
- Check platform documentation
- Test incrementally
- Ask in discussions

---

**Version**: 1.0.0  
**Last Updated**: 2026-01-15  
**Maintained by**: AgentCoreNexus Team