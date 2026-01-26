# conversation_summaries Table Schema

**表名**: `agentcore-conversation-summaries-dev`  
**用途**: 存儲 AI 生成的對話摘要（快取）  
**計費模式**: PAY_PER_REQUEST

---

## 📋 Schema 定義

### Primary Key
- **Partition Key**: `conversation_id` (String)

### Attributes

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| conversation_id | String | ✅ | 對話 ID（主鍵）|
| summary_text | String | ✅ | AI 生成的摘要文字 |
| key_points | List | ❌ | 關鍵討論點（陣列）|
| sentiment | String | ❌ | 情感傾向（positive/neutral/negative）|
| attachment_stats | Map | ✅ | 附件統計 |
| generated_at | Number | ✅ | 生成時間（毫秒時間戳）|
| model_used | String | ✅ | 使用的模型（claude-3-haiku 等）|
| token_count | Number | ❌ | Token 使用量 |
| generation_time_ms | Number | ❌ | 生成耗時（毫秒）|
| cached | Boolean | ❌ | 標記（總是 false，用於 API 響應）|

---

## 📝 範例數據

```json
{
  "conversation_id": "user-abc123",
  "summary_text": "【對話摘要】\n本對話包含 3 張圖片和 1 個文件。\n\n主題：網站部署問題排查\n關鍵討論點：\n1. 用戶遇到 CORS 錯誤\n2. 配置 CloudFront 分發\n3. 更新 S3 bucket 策略\n\n用戶需求：解決網站無法正常訪問的問題\n解決方案：修改 CORS 配置並重新部署，問題已解決。",
  "key_points": [
    "用戶遇到 CORS 錯誤",
    "配置 CloudFront 分發",
    "更新 S3 bucket 策略"
  ],
  "sentiment": "positive",
  "attachment_stats": {
    "images": 3,
    "documents": 1,
    "total": 4
  },
  "generated_at": 1706280000000,
  "model_used": "anthropic.claude-3-haiku-20240307-v1:0",
  "token_count": 500,
  "generation_time_ms": 8500
}
```

---

## 🔍 查詢模式

### Pattern 1：檢查摘要是否存在
```python
response = table.get_item(
    Key={'conversation_id': conversation_id}
)
```

**頻率**: 高（每次查看對話詳情）  
**性能**: < 10ms（單項查詢）

### Pattern 2：保存新摘要
```python
table.put_item(Item={
    'conversation_id': conversation_id,
    'summary_text': summary,
    'generated_at': now,
    # ...
})
```

**頻率**: 中（手動觸發）  
**性能**: < 20ms

### Pattern 3：更新摘要（重新生成）
```python
table.update_item(
    Key={'conversation_id': conversation_id},
    UpdateExpression='SET summary_text = :text, generated_at = :time',
    ExpressionAttributeValues={
        ':text': new_summary,
        ':time': now
    }
)
```

**頻率**: 低（強制重新生成）  
**性能**: < 20ms

---

## 💰 成本估算

### 假設
- 每天生成 50 個摘要
- 平均每個摘要 500 bytes
- 保留 90 天（可配置 TTL，未來功能）

### 月度成本
- **寫入**: 50 × 30 × $1.25/1M = **$0.001875/月**
- **讀取**: 50 × 30 × 2 × $0.25/1M = **$0.00075/月**（假設每個摘要查看 2 次）
- **儲存**: 50 × 90 × 0.5KB × $0.25/GB = **$0.0005/月**

**總計**: < **$0.01/月**（幾乎可忽略）

---

## 🔒 安全特性

- ✅ **加密**: SSE 自動啟用
- ✅ **備份**: PITR 已啟用（35 天）
- ✅ **訪問控制**: IAM 最小權限
- ✅ **審計**: 所有訪問都記錄

---

## 🎯 優化建議

### 未來可選
- **TTL**: 添加自動清理舊摘要（如 90 天後）
- **版本控制**: 保留摘要歷史版本
- **批量操作**: 批量生成摘要的優化

---

**表狀態**: ✅ 已創建（Day 1-2）  
**Schema 版本**: 1.0  
**準備使用**: ✅