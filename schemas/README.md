# AgentCoreNexus Schemas

This directory contains JSON schemas that define standard data formats for cross-component communication in the AgentCoreNexus system.

## 📋 Available Schemas

### Universal Message Schema (`message.schema.json`)

**Version**: 1.0.0  
**Purpose**: Standardize message format across all channel adapters

This schema defines a universal message format that all channel adapters (Telegram, Web, Discord, Slack, etc.) must follow when sending messages to the AI processor and other components.

#### Key Features

- **Channel Agnostic**: Works with any communication channel
- **Type Safe**: Strongly typed fields with validation
- **Extensible**: Supports custom metadata per channel
- **Multi-modal**: Handles text, images, files, video, and audio

#### Schema Structure

```json
{
  "messageId": "unique-id",
  "timestamp": "2026-01-15T15:00:00Z",
  "channel": {
    "type": "telegram|web|discord|slack",
    "channelId": "channel-specific-id",
    "metadata": {}
  },
  "user": {
    "id": "unified-user-id",
    "channelUserId": "channel-specific-user-id",
    "username": "username",
    "displayName": "Display Name"
  },
  "content": {
    "text": "Message text",
    "messageType": "text|image|file|video|audio",
    "attachments": [...]
  },
  "conversationId": "optional-conversation-id",
  "replyTo": "optional-reply-to-message-id"
}
```

## 🔧 Usage

### Validation

Use a JSON schema validator to ensure messages conform to the schema:

**Python Example**:
```python
import json
import jsonschema

# Load schema
with open('schemas/message.schema.json') as f:
    schema = json.load(f)

# Validate message
message = {...}
jsonschema.validate(instance=message, schema=schema)
```

**TypeScript Example**:
```typescript
import Ajv from 'ajv';
import schema from './schemas/message.schema.json';

const ajv = new Ajv();
const validate = ajv.compile(schema);

const message = {...};
if (validate(message)) {
  // Message is valid
} else {
  console.error(validate.errors);
}
```

### Channel Adapter Implementation

All channel adapters must:
1. Convert incoming channel-specific messages to Universal Message format
2. Send messages to AI processor using this format
3. Handle responses in the same format

**Example: Telegram Adapter**
```python
def convert_telegram_to_universal(telegram_update):
    return {
        "messageId": str(telegram_update.message.message_id),
        "timestamp": telegram_update.message.date.isoformat(),
        "channel": {
            "type": "telegram",
            "channelId": str(telegram_update.message.chat.id),
            "metadata": {
                "chat_type": telegram_update.message.chat.type
            }
        },
        "user": {
            "id": get_unified_user_id(telegram_update.message.from_user.id),
            "channelUserId": str(telegram_update.message.from_user.id),
            "username": telegram_update.message.from_user.username,
            "displayName": telegram_update.message.from_user.first_name
        },
        "content": {
            "text": telegram_update.message.text,
            "messageType": "text",
            "attachments": []
        }
    }
```

## 📐 Design Principles

1. **Consistency**: Same format across all channels
2. **Simplicity**: Easy to understand and implement
3. **Extensibility**: Can add new fields without breaking existing code
4. **Validation**: Schema enforces data quality
5. **Documentation**: Self-documenting through JSON schema

## 🔄 Schema Versioning

- **Current Version**: 1.0.0
- **Version Format**: MAJOR.MINOR.PATCH (Semantic Versioning)
- **Breaking Changes**: Increment MAJOR version
- **New Fields**: Increment MINOR version
- **Bug Fixes**: Increment PATCH version

## 🆕 Adding New Channel Types

To add a new channel type (e.g., Discord, Slack):

1. Add the channel type to the `channel.type` enum in the schema
2. Implement converter functions in your channel adapter
3. Update this README with usage examples
4. Test with schema validation

## 📚 Related Documentation

- [Architecture Guide](../docs/architecture-guide.md)
- [New Channel Guide](../docs/NEW_CHANNEL_GUIDE.md) (when available)
- [API Documentation](../docs/API.md) (when available)

## 🤝 Contributing

When proposing changes to schemas:
1. Follow semantic versioning
2. Update this README
3. Provide migration guide for breaking changes
4. Test with all existing channel adapters

---

**Maintained by**: AgentCoreNexus Team  
**Last Updated**: 2026-01-15