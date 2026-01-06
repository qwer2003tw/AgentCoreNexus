# Debug 命令日誌功能

## 概述

當使用 `/debug` 命令時，系統會記錄詳細的日誌來追蹤遮蔽過程，方便在 CloudWatch Logs 中監控和除錯。

## 日誌類型

### 1. 開始遮蔽日誌 (INFO)
**Event Type:** `debug_redaction_start`

當開始處理 debug 請求時記錄。

```json
{
  "timestamp": "2025-11-05 08:58:30",
  "level": "INFO",
  "logger": "src.telegram_client",
  "message": "Starting debug info redaction",
  "function": "send_debug_info",
  "line": 317,
  "chat_id": 316743844,
  "event_type": "debug_redaction_start",
  "sensitive_fields_count": 3
}
```

**包含資訊：**
- `chat_id`: 請求的聊天 ID
- `event_type`: debug_redaction_start
- `sensitive_fields_count`: 需要遮蔽的敏感欄位數量

### 2. 完成遮蔽日誌 (INFO)
**Event Type:** `debug_redaction_complete`

當遮蔽完成時記錄，包含實際被遮蔽的欄位清單。

```json
{
  "timestamp": "2025-11-05 08:58:30",
  "level": "INFO",
  "logger": "src.telegram_client",
  "message": "Debug info redaction completed",
  "function": "send_debug_info",
  "line": 348,
  "chat_id": 316743844,
  "event_type": "debug_redaction_complete",
  "redacted_fields": [
    "headers.X-Telegram-Bot-Api-Secret-Token",
    "multiValueHeaders.X-Telegram-Bot-Api-Secret-Token",
    "requestContext.accountId"
  ],
  "redacted_count": 3
}
```

**包含資訊：**
- `chat_id`: 請求的聊天 ID
- `event_type`: debug_redaction_complete
- `redacted_fields`: 實際被遮蔽的欄位路徑清單
- `redacted_count`: 被遮蔽的欄位數量

### 3. 訊息準備日誌 (DEBUG)
**Event Type:** `debug_message_prepared`

當 debug 訊息準備完成、即將發送時記錄。

```json
{
  "timestamp": "2025-11-05 08:58:30",
  "level": "DEBUG",
  "logger": "src.telegram_client",
  "message": "Debug message prepared for sending",
  "function": "send_debug_info",
  "line": 355,
  "chat_id": 316743844,
  "event_type": "debug_message_prepared",
  "message_length": 420
}
```

**包含資訊：**
- `chat_id`: 請求的聊天 ID
- `event_type`: debug_message_prepared
- `message_length`: 訊息長度（字元數）

## 在 CloudWatch Logs 中查詢

### 查詢所有 debug 相關日誌
```
fields @timestamp, message, event_type, chat_id
| filter event_type like /debug_redaction/
| sort @timestamp desc
```

### 查詢特定聊天的 debug 日誌
```
fields @timestamp, message, event_type, redacted_fields
| filter event_type like /debug_redaction/ and chat_id = 316743844
| sort @timestamp desc
```

### 查詢遮蔽完成日誌
```
fields @timestamp, chat_id, redacted_fields, redacted_count
| filter event_type = "debug_redaction_complete"
| sort @timestamp desc
```

## 日誌級別配置

- 預設日誌級別：**INFO**
- 要查看 `debug_message_prepared` 日誌，需要將環境變數 `LOG_LEVEL` 設定為 `DEBUG`

在 Lambda 函數中設定環境變數：
```yaml
Environment:
  Variables:
    LOG_LEVEL: DEBUG  # 設定為 DEBUG 以查看所有日誌
```

## 測試

所有日誌功能都有完整的測試覆蓋：

```bash
# 執行日誌測試
python -m pytest tests/test_debug_integration.py -v

# 執行所有遮蔽相關測試
python -m pytest tests/test_telegram_client_redaction.py \
                 tests/test_debug_redaction_actual_event.py \
                 tests/test_debug_integration.py -v
```

## 相關文件

- [Debug 命令遮蔽功能](DEBUG_COMMAND_REDACTION.md)
- [變更紀錄](../changelog/CHANGELOG_DEBUG_REDACTION.md)
