# Debug Command - Sensitive Data Redaction

## 概述

`/debug` 命令現在會自動遮蔽敏感資料，以防止敏感資訊洩露。這個功能確保在除錯時不會意外暴露 API 密鑰、token 或其他機密資訊。

## 功能說明

### 遮蔽的敏感欄位

目前自動遮蔽以下欄位：

1. **X-Telegram-Bot-Api-Secret-Token**
   - 位置：`headers['X-Telegram-Bot-Api-Secret-Token']`
   - 位置：`multiValueHeaders['X-Telegram-Bot-Api-Secret-Token']`
   - 說明：Telegram Bot API 的 Secret Token

2. **AWS Account ID**
   - 位置：`requestContext['accountId']`
   - 說明：AWS 帳戶 ID

### 遮蔽效果

所有敏感欄位的值會被替換為 `[REDACTED]`，例如：

**原始值：**
```json
{
  "headers": {
    "X-Telegram-Bot-Api-Secret-Token": "QDJxJf37waXXxacORJXtPYEJ3JTjxRH1pcarospeAAfn8pJC0dfPHfOqcgJqGkPd"
  }
}
```

**遮蔽後：**
```json
{
  "headers": {
    "X-Telegram-Bot-Api-Secret-Token": "[REDACTED]"
  }
}
```

## 使用方式

使用 `/debug` 命令時，系統會自動執行遮蔽：

```
使用者: /debug
Bot: 🔍 **Debug Information**
     _Note: Sensitive fields have been redacted_
     
     [JSON with redacted sensitive fields]
```

## 技術實現

### 核心函數

#### `redact_sensitive_data(data: dict, sensitive_paths: List[tuple]) -> dict`

遮蔽敏感資料的主要函數。

**參數：**
- `data`: 原始資料字典
- `sensitive_paths`: 需要遮蔽的路徑列表，每個路徑是一個 tuple

**返回：**
- 已遮蔽敏感資料的深拷貝副本

**範例：**
```python
from telegram_client import redact_sensitive_data

event = {
    'headers': {
        'X-Telegram-Bot-Api-Secret-Token': 'secret123'
    }
}

paths = [('headers', 'X-Telegram-Bot-Api-Secret-Token')]
redacted = redact_sensitive_data(event, paths)

# redacted['headers']['X-Telegram-Bot-Api-Secret-Token'] == '[REDACTED]'
# event['headers']['X-Telegram-Bot-Api-Secret-Token'] == 'secret123' (原始資料未被修改)
```

#### `_redact_path(data: dict, path: tuple) -> None`

遞迴遮蔽指定路徑的值。

**特性：**
- 支援巢狀路徑
- 支援列表值（會遮蔽列表中的所有元素）
- 直接修改傳入的字典

### 配置

敏感欄位在 `src/telegram_client.py` 中定義：

```python
SENSITIVE_FIELDS = [
    ('headers', 'X-Telegram-Bot-Api-Secret-Token'),
    ('multiValueHeaders', 'X-Telegram-Bot-Api-Secret-Token'),
    ('requestContext', 'accountId'),
]
```

## 安全考量

### Deep Copy 保護

系統使用 `copy.deepcopy()` 創建資料的深拷貝，確保：
- 原始 event 物件不會被修改
- 避免意外修改共享資料
- Lambda 日誌中的原始資料保持不變（但不會輸出到 Telegram）

### 列表值處理

對於列表形式的敏感值（如 `multiValueHeaders`），系統會遮蔽列表中的每一個元素：

```python
# 原始
['secret1', 'secret2', 'secret3']

# 遮蔽後
['[REDACTED]', '[REDACTED]', '[REDACTED]']
```

## 擴展遮蔽規則

如需添加更多敏感欄位，請修改 `SENSITIVE_FIELDS` 配置：

```python
SENSITIVE_FIELDS = [
    # 現有欄位
    ('headers', 'X-Telegram-Bot-Api-Secret-Token'),
    ('multiValueHeaders', 'X-Telegram-Bot-Api-Secret-Token'),
    ('requestContext', 'accountId'),
    
    # 新增欄位
    ('headers', 'Authorization'),  # 遮蔽 Authorization header
    ('requestContext', 'identity', 'apiKey'),  # 遮蔽巢狀欄位
]
```

## 測試

完整的測試套件位於 `tests/test_telegram_client_redaction.py`，包含：

- ✅ 單一值遮蔽
- ✅ 列表值遮蔽
- ✅ 巢狀值遮蔽
- ✅ 多欄位同時遮蔽
- ✅ 不存在欄位的處理
- ✅ 實際 API Gateway event 結構測試
- ✅ JSON 序列化測試
- ✅ 多次呼叫測試

執行測試：
```bash
pytest tests/test_telegram_client_redaction.py -v
```

## 版本歷史

- **v1.0** (2025-01-05)
  - 初始實現
  - 支援三個高優先級敏感欄位遮蔽
  - 完整測試覆蓋
  - Deep copy 保護

## 相關文檔

- [Debug Command](DEBUG_COMMAND.md) - Debug 命令完整說明
- [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md) - 部署指南
- [Security Best Practices](../deployment/DEPLOYMENT_BEST_PRACTICES.md) - 安全最佳實踐
