# 管理員 API 規範

**版本**: 1.0  
**創建時間**: 2026-01-26  
**Base URL**: `https://{api-domain}/prod/admin`

---

## 🔐 認證和權限

### 認證方式
```
Authorization: Bearer {jwt_token}
```

### 權限要求
所有管理員 API 需要以下角色之一：
- `admin` - 基本管理權限
- `auditor` - 審計員（只讀）
- `super_admin` - 超級管理員（所有權限）

---

## 📋 API Endpoints

### 1. 對話列表 API

#### Request
```http
GET /admin/conversations?page=1&limit=50&channel=web&start_date=2026-01-01&end_date=2026-01-26&user_email=user@example.com&keyword=test

Query Parameters:
- page (int, optional): 頁碼，默認 1
- limit (int, optional): 每頁數量，默認 50，最大 100
- channel (string, optional): 通道篩選（web/telegram/all），默認 all
- start_date (string, optional): 起始日期（YYYY-MM-DD）
- end_date (string, optional): 結束日期（YYYY-MM-DD）
- user_email (string, optional): 用戶 email 篩選
- keyword (string, optional): 關鍵字搜尋（在消息內容中搜尋）
```

#### Response (200 OK)
```json
{
  "success": true,
  "conversations": [
    {
      "conversation_id": "user-abc123",
      "unified_user_id": "uuid-xxx",
      "user_identifier": "user@example.com",  // email 或 telegram username
      "channel": "web",
      "message_count": 15,
      "first_message_at": 1706000000000,
      "last_message_at": 1706280000000,
      "last_message_preview": "這是最後一條消息的前50個字...",
      "has_summary": false,
      "is_deleted": false
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total_count": 150,
    "total_pages": 3,
    "has_more": true,
    "next_page": 2
  },
  "filters_applied": {
    "channel": "web",
    "start_date": "2026-01-01",
    "end_date": "2026-01-26"
  }
}
```

#### Response (403 Forbidden)
```json
{
  "success": false,
  "error": "Permission denied",
  "required_permission": "view_all_conversations",
  "user_role": "user"
}
```

---

### 2. 對話詳情 API

#### Request
```http
GET /admin/conversations/{conversation_id}?include_messages=true&limit=100

Path Parameters:
- conversation_id (string, required): 對話 ID

Query Parameters:
- include_messages (boolean, optional): 是否包含消息，默認 true
- limit (int, optional): 消息數量限制，默認 100，最大 500
- start_time (int, optional): 起始時間戳（毫秒）
```

#### Response (200 OK)
```json
{
  "success": true,
  "conversation": {
    "conversation_id": "user-abc123",
    "unified_user_id": "uuid-xxx",
    "user_identifier": "user@example.com",
    "channel": "web",
    "created_at": 1706000000000,
    "last_message_at": 1706280000000,
    "message_count": 15,
    "is_deleted": false,
    "metadata": {
      "participant_count": 2,
      "total_attachments": 3,
      "attachment_types": {
        "images": 2,
        "documents": 1
      }
    }
  },
  "messages": [
    {
      "message_id": "msg-123",
      "timestamp": 1706280000000,
      "sender_id": "user",
      "sender_name": "User Name",
      "role": "user",  // "user" or "assistant"
      "content": {
        "text": "Hello world",
        "attachments": [
          {
            "type": "photo",
            "s3_key": "attachments/...",
            "file_name": "image.jpg",
            "mime_type": "image/jpeg",
            "size": 102400
          }
        ]
      },
      "channel": "web"
    }
  ],
  "summary": {
    "exists": false,
    "summary_text": null,
    "generated_at": null
  },
  "pagination": {
    "has_more": false,
    "last_evaluated_key": null
  }
}
```

---

### 3. 關鍵字搜尋 API

#### Request
```http
GET /admin/conversations/search?keyword=deployment&days=30&limit=50

Query Parameters:
- keyword (string, required): 搜尋關鍵字
- days (int, optional): 搜尋範圍（天數），默認 30，最大 90
- channel (string, optional): 通道篩選
- limit (int, optional): 結果數量，默認 50，最大 100
```

#### Response (200 OK)
```json
{
  "success": true,
  "keyword": "deployment",
  "search_scope": {
    "days": 30,
    "channel": "all"
  },
  "results": [
    {
      "conversation_id": "user-abc123",
      "user_identifier": "user@example.com",
      "channel": "web",
      "matched_count": 3,  // 關鍵字出現次數
      "first_match_at": 1706000000000,
      "last_match_at": 1706280000000,
      "preview": "...discussing deployment strategies for..."  // 包含關鍵字的片段
    }
  ],
  "result_count": 15,
  "search_time_ms": 450
}
```

---

### 4. 附件預覽 API

#### Request
```http
GET /admin/attachments/{s3_key}/preview

Path Parameters:
- s3_key (string, required): 附件的 S3 key（URL encoded）

Query Parameters:
- expires_in (int, optional): 有效期（秒），默認 3600（1小時），最大 86400（24小時）
```

#### Response (200 OK)
```json
{
  "success": true,
  "presigned_url": "https://bucket.s3.amazonaws.com/...",
  "expires_in": 3600,
  "expires_at": 1706283600000,
  "attachment_info": {
    "file_name": "image.jpg",
    "mime_type": "image/jpeg",
    "size": 102400
  }
}
```

---

### 5. AI 摘要生成 API

#### Request
```http
POST /admin/conversations/{conversation_id}/summarize

Path Parameters:
- conversation_id (string, required): 對話 ID

Body (optional):
{
  "force_regenerate": false,  // 強制重新生成（忽略快取）
  "model": "claude-3-haiku"   // 使用的模型（haiku/sonnet）
}
```

#### Response (200 OK)
```json
{
  "success": true,
  "conversation_id": "user-abc123",
  "summary": {
    "summary_text": "【對話摘要】\n本對話包含 3 張圖片和 1 個文件。\n\n主題：網站部署問題排查\n關鍵討論點：...",
    "key_points": [
      "用戶遇到 CORS 錯誤",
      "配置 CloudFront 分發",
      "更新 S3 bucket 策略"
    ],
    "sentiment": "positive",  // positive/neutral/negative
    "attachment_stats": {
      "images": 3,
      "documents": 1
    },
    "generated_at": 1706280000000,
    "model_used": "claude-3-haiku",
    "token_count": 500,
    "cached": false  // 是否從快取讀取
  },
  "generation_time_ms": 8500
}
```

#### Response (202 Accepted) - 異步處理
```json
{
  "success": true,
  "status": "processing",
  "conversation_id": "user-abc123",
  "estimated_time_seconds": 20,
  "check_status_url": "/admin/conversations/user-abc123/summary"
}
```

---

### 6. 審計日誌查詢 API

#### Request
```http
GET /admin/audit-logs?admin_email=admin@example.com&action=view_conversation&start_time=1706000000000&end_time=1706280000000&limit=100

Query Parameters:
- admin_email (string, optional): 按管理員篩選
- action (string, optional): 按操作類型篩選
- resource_id (string, optional): 按資源 ID 篩選
- start_time (int, optional): 起始時間（毫秒時間戳）
- end_time (int, optional): 結束時間（毫秒時間戳）
- limit (int, optional): 結果數量，默認 100，最大 500
- last_key (string, optional): 分頁標記（base64 encoded）
```

#### Response (200 OK)
```json
{
  "success": true,
  "logs": [
    {
      "log_id": "uuid-xxx",
      "timestamp": 1706280000123,
      "admin_email": "admin@example.com",
      "admin_role": "super_admin",
      "action": "view_conversation",
      "action_category": "read",
      "action_sensitivity": "medium",
      "resource_type": "conversation",
      "resource_id": "user-abc123",
      "resource_owner": "user@example.com",
      "status": "success",
      "details": {
        "query": {
          "include_messages": "true",
          "limit": "100"
        }
      },
      "ip_address": "1.2.3.4",
      "request_duration_ms": 150
    }
  ],
  "count": 50,
  "pagination": {
    "has_more": true,
    "last_evaluated_key": "base64_encoded_key"
  },
  "filters_applied": {
    "admin_email": "admin@example.com",
    "start_time": 1706000000000,
    "end_time": 1706280000000
  }
}
```

---

## 🔒 安全考量

### 所有 API 共同特性

**自動審計**：
- 使用 `@audit_log` 裝飾器
- 記錄管理員、操作、資源、耗時
- 記錄成功和失敗

**權限檢查**：
- 使用 `@require_permission` 裝飾器
- 未授權自動返回 403
- 記錄權限拒絕事件

**錯誤處理**：
- 統一的錯誤響應格式
- 詳細的錯誤訊息
- HTTP 狀態碼正確

---

## 📊 性能目標

| API | 目標延遲 (p95) | 實現方式 |
|-----|---------------|---------|
| 對話列表 | < 200ms | GlobalTimestampIndex GSI |
| 對話詳情 | < 300ms | Direct Query by conversation_id |
| 關鍵字搜尋 | < 500ms | GSI + Lambda 過濾 |
| 附件預覽 | < 100ms | S3 presigned URL |
| AI 摘要 | < 30s | Bedrock Claude (async) |
| 審計日誌 | < 300ms | AdminEmailIndex/ResourceIdIndex GSI |

---

## 🧪 測試策略

### 單元測試
- 測試每個 handler 函數
- Mock DynamoDB 和 Bedrock
- 測試錯誤處理

### 整合測試
- 測試 API + DynamoDB
- 測試審計日誌記錄
- 測試權限檢查

### E2E 測試
- 使用 requests 或 Postman
- 完整流程測試

---

**版本**: 1.0  
**狀態**: 設計完成，準備實施