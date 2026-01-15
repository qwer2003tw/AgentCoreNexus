# API Reference

Complete API reference for all AgentCoreNexus REST and WebSocket endpoints.

## 🌐 Base URLs

### REST API
```
https://{api-id}.execute-api.us-west-2.amazonaws.com/prod
```

### WebSocket API
```
wss://{ws-id}.execute-api.us-west-2.amazonaws.com/prod
```

Get actual URLs from CloudFormation outputs:
```bash
aws cloudformation describe-stacks --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`RestApiEndpoint`].OutputValue' --output text
```

---

## 🔐 Authentication

### Login

**Endpoint**: `POST /auth/login`  
**Auth**: None  
**Body**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "Bearer",
  "expires_in": 604800,
  "user": {
    "email": "user@example.com",
    "unified_user_id": "uuid-here"
  }
}
```

### Get Current User

**Endpoint**: `GET /auth/me`  
**Auth**: Bearer token  
**Response**:
```json
{
  "email": "user@example.com",
  "unified_user_id": "uuid-here",
  "created_at": "2026-01-15T10:00:00Z"
}
```

### Logout

**Endpoint**: `POST /auth/logout`  
**Auth**: Bearer token  
**Response**: `204 No Content`

### Change Password

**Endpoint**: `POST /auth/change-password`  
**Auth**: Bearer token  
**Body**:
```json
{
  "old_password": "old123",
  "new_password": "new456"
}
```

---

## 💬 Conversations

### List Conversations

**Endpoint**: `GET /conversations`  
**Auth**: Bearer token  
**Query Parameters**:
- `limit`: Number of results (default: 20, max: 100)
- `offset`: Pagination offset

**Response**:
```json
{
  "conversations": [
    {
      "conversation_id": "conv-123",
      "title": "My Conversation",
      "created_at": "2026-01-15T10:00:00Z",
      "last_message_time": "2026-01-15T12:00:00Z",
      "message_count": 42
    }
  ],
  "total": 5
}
```

### Create Conversation

**Endpoint**: `POST /conversations`  
**Auth**: Bearer token  
**Body**:
```json
{
  "title": "New Conversation"
}
```

**Response**:
```json
{
  "conversation_id": "conv-456",
  "title": "New Conversation",
  "created_at": "2026-01-15T15:00:00Z"
}
```

### Update Conversation

**Endpoint**: `PUT /conversations/{id}`  
**Auth**: Bearer token  
**Body**:
```json
{
  "title": "Updated Title"
}
```

### Delete Conversation

**Endpoint**: `DELETE /conversations/{id}`  
**Auth**: Bearer token  
**Response**: `204 No Content`

### Get Conversation Messages

**Endpoint**: `GET /conversations/{id}/messages`  
**Auth**: Bearer token  
**Query Parameters**:
- `limit`: Number of messages (default: 50, max: 200)
- `before`: Get messages before timestamp

**Response**:
```json
{
  "messages": [
    {
      "message_id": "msg-123",
      "role": "user",
      "content": "Hello",
      "timestamp": "2026-01-15T10:00:00Z",
      "attachments": []
    },
    {
      "message_id": "msg-124",
      "role": "assistant",
      "content": "Hi! How can I help?",
      "timestamp": "2026-01-15T10:00:05Z"
    }
  ],
  "has_more": false
}
```

---

## 📎 Attachments

### Generate Upload URL

**Endpoint**: `POST /attachments/presign`  
**Auth**: Bearer token  
**Body**:
```json
{
  "file_name": "document.pdf",
  "file_size": 102400,
  "content_type": "application/pdf"
}
```

**Response**:
```json
{
  "upload_url": "https://bucket.s3.amazonaws.com/...",
  "attachment_id": "att-789",
  "key": "attachments/user-123/att-789/document.pdf",
  "expires_in": 300
}
```

**Usage**:
```javascript
// 1. Get presigned URL
const response = await fetch('/attachments/presign', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + token,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    file_name: file.name,
    file_size: file.size,
    content_type: file.type
  })
});

const { upload_url, attachment_id } = await response.json();

// 2. Upload file to S3
await fetch(upload_url, {
  method: 'PUT',
  headers: { 'Content-Type': file.type },
  body: file
});

// 3. Use attachment_id in message
```

### Generate Download URL

**Endpoint**: `POST /attachments/download`  
**Auth**: Bearer token  
**Body**:
```json
{
  "key": "attachments/user-123/att-789/document.pdf"
}
```

**Response**:
```json
{
  "download_url": "https://bucket.s3.amazonaws.com/...",
  "expires_in": 300
}
```

---

## 🔌 WebSocket API

### Connection

**URL**: `wss://{ws-id}.execute-api.us-west-2.amazonaws.com/prod`

**Connection Flow**:
```javascript
// 1. Connect with JWT token
const ws = new WebSocket(`${WS_URL}?token=${jwt_token}`);

// 2. Handle events
ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  handleMessage(data);
};
ws.onerror = (error) => console.error('WebSocket error:', error);
ws.onclose = () => console.log('Disconnected');
```

### Send Message

**Action**: `send_message`

```json
{
  "action": "send_message",
  "conversation_id": "conv-123",
  "message": "Hello, AI!",
  "attachments": [
    {
      "id": "att-789",
      "key": "attachments/user-123/att-789/file.pdf",
      "name": "file.pdf",
      "content_type": "application/pdf"
    }
  ]
}
```

### Receive Message

**From Server**:
```json
{
  "type": "message",
  "conversation_id": "conv-123",
  "message_id": "msg-456",
  "role": "assistant",
  "content": "Here's my response...",
  "timestamp": "2026-01-15T15:00:00Z"
}
```

### Error Response

```json
{
  "type": "error",
  "error": "Invalid conversation ID",
  "code": "INVALID_CONVERSATION"
}
```

---

## 📊 Response Codes

### Success Codes

| Code | Description |
|------|-------------|
| `200` | OK - Request succeeded |
| `201` | Created - Resource created |
| `204` | No Content - Success, no body |

### Client Error Codes

| Code | Description |
|------|-------------|
| `400` | Bad Request - Invalid input |
| `401` | Unauthorized - Missing/invalid token |
| `403` | Forbidden - No permission |
| `404` | Not Found - Resource doesn't exist |
| `409` | Conflict - Resource already exists |
| `429` | Too Many Requests - Rate limited |

### Server Error Codes

| Code | Description |
|------|-------------|
| `500` | Internal Server Error |
| `502` | Bad Gateway |
| `503` | Service Unavailable |
| `504` | Gateway Timeout |

---

## 🔒 Rate Limiting

### REST API Limits

- **Per User**: 100 requests/minute
- **Authentication**: 10 login attempts/minute
- **Uploads**: 20 files/hour

### WebSocket Limits

- **Messages**: 60 messages/minute
- **Connections**: 5 concurrent connections per user
- **Data**: 1MB per message

---

## 🧪 Testing Endpoints

### Using cURL

```bash
# Login
curl -X POST https://api-url/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Get conversations (with auth)
curl https://api-url/conversations \
  -H "Authorization: Bearer YOUR_TOKEN"

# Send message via WebSocket
# Use wscat: npm install -g wscat
wscat -c "wss://ws-url?token=YOUR_TOKEN"
> {"action":"send_message","conversation_id":"conv-123","message":"Hello"}
```

### Using Postman

1. Import collection from `postman/AgentCoreNexus.postman_collection.json` (if available)
2. Set environment variables:
   - `API_URL`: REST API endpoint
   - `WS_URL`: WebSocket endpoint
   - `TOKEN`: JWT token after login

---

## 🐛 Common Issues

### 401 Unauthorized
- Check token is valid and not expired
- Verify Authorization header format: `Bearer {token}`
- Ensure token includes all required claims

### 403 Forbidden
- User doesn't have permission for this resource
- Check user bindings in DynamoDB
- Verify conversation ownership

### 500 Internal Server Error
- Check Lambda logs in CloudWatch
- Verify environment variables are set
- Check IAM permissions

### WebSocket Connection Fails
- Verify token is passed in query string
- Check CORS configuration
- Ensure WebSocket Lambda has proper permissions

---

## 📚 Related Documentation

- [Architecture Guide](./architecture-guide.md)
- [Deployment Guide](./deployment-guide.md)
- [Environment Variables](./ENV.md)

---

**API Version**: 1.0.0  
**Last Updated**: 2026-01-15  
**Maintained by**: AgentCoreNexus Team