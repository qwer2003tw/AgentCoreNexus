# 📊 Memory 審計日誌查詢指南

**創建時間**: 2026-01-07 03:32 UTC  
**Log Group**: `/aws/lambda/telegram-unified-bot-processor`

---

## ✅ 你的審計日誌確認

**找到了！你在 03:28:55 UTC (11:28 UTC+8) 的訊息已被記錄**

```
2026-01-07 03:28:55 - utils.audit - INFO - Memory operation: create_session
```

**完整處理流程**:
```
03:28:54 - Processor invoked
03:28:54 - Processing message from telegram
03:28:54 - Processing text message from Steven Peng
03:28:55 - Session Manager 建立成功 (Actor: actor-3544f0d54239dacf)
03:28:55 - Memory operation: create_session ⭐ 審計日誌
03:28:55 - Memory session created with secure actor_id
03:28:55 - Agent 建立成功
03:28:55 - 處理訊息: 我叫什麼名字...
03:29:00 - Message processed successfully
```

---

## 🔍 如何查詢審計日誌

### 方法 1: 快速查看（最簡單）

**查看最近 10 分鐘的審計日誌**:
```bash
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 \
  --since 10m \
  --format short | grep "audit"
```

**只看 Memory 操作**:
```bash
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 \
  --since 10m \
  --format short | grep "Memory operation"
```

### 方法 2: 按時間範圍查詢

**查看今天的所有審計日誌**:
```bash
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/telegram-unified-bot-processor \
  --filter-pattern "memory_audit" \
  --start-time $(($(date -d 'today 00:00' +%s)))000
```

**查看最近 1 小時**:
```bash
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/telegram-unified-bot-processor \
  --filter-pattern "memory_audit" \
  --start-time $(($(date +%s) - 3600))000
```

**指定時間範圍（UTC 時間）**:
```bash
# 例如：查詢 03:20 到 03:30 之間
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/telegram-unified-bot-processor \
  --filter-pattern "memory_audit" \
  --start-time 1767755200000 \
  --end-time 1767755800000
```

### 方法 3: 查看特定用戶

**查找特定 actor_id 的操作**:
```bash
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 \
  --since 1h \
  --format short | grep "actor-3544f0d54239dacf"
```

**你的 actor_id**: `actor-3544f0d54239dacf`

---

## 📋 審計日誌內容解讀

### 你的實際日誌

**時間**: 2026-01-07 03:28:55 UTC (11:28 UTC+8)  
**操作**: create_session  
**結果**: 成功 ✅

**完整資訊**:
- Actor ID: `actor-3544f0d54239dacf`（你的安全 ID）
- Session ID: `316743844`
- Memory ID: `TelegramBotMemory-6UH9fyDyIf`
- 訊息: "我叫什麼名字"

### 日誌欄位說明

```json
{
  "event_type": "memory_audit",           // 審計事件
  "operation": "create_session",          // 操作類型
  "user_id_hash": "a1b2c3d4",            // 你的 ID 雜湊（隱私保護）
  "actor_id": "actor-3544f0d54239dacf",  // 你的安全 actor ID
  "session_id": "316743844",              // Session ID
  "success": true,                        // 成功
  "timestamp": "2026-01-07T03:28:55Z",   // UTC 時間
  "details": {
    "memory_id": "TelegramBotMemory-6UH9fyDyIf"
  }
}
```

---

## 🎯 常用查詢場景

### 場景 1: 查看我的所有 Memory 操作

```bash
# 查看最近 1 天你的所有操作
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 \
  --since 1d \
  --format short | grep "actor-3544f0d54239dacf"
```

### 場景 2: 檢查是否有失敗的操作

```bash
# 查看失敗的審計記錄
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/telegram-unified-bot-processor \
  --filter-pattern "memory_audit" | \
  grep "success.*false"
```

### 場景 3: 統計操作次數

```bash
# 統計最近 1 小時的 Session 創建次數
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/telegram-unified-bot-processor \
  --filter-pattern "create_session" \
  --start-time $(($(date +%s) - 3600))000 | \
  grep -c "Memory operation"
```

### 場景 4: 查看詳細的 Session 資訊

```bash
# 查看所有 Session 創建的詳細資訊
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 \
  --since 1h | \
  grep -A 2 "Session Manager 建立成功"
```

---

## 🔎 為什麼你可能沒看到

### 原因 1: 查詢時間範圍
你可能使用了：
```bash
--since 5m  # 只查最近 5 分鐘
```

但你的訊息在 03:28，如果現在是 03:35，就超過 5 分鐘了。

**解決**: 使用 `--since 10m` 或 `--since 1h`

### 原因 2: grep 關鍵字
你可能搜尋：
```bash
grep "memory_audit"  # 小寫
```

但實際日誌可能是：
```
Memory operation  # 大寫 M
```

**解決**: 使用 `-i` 忽略大小寫，或搜尋 "audit"

### 原因 3: 日誌格式
CloudWatch 的 `--format short` 會簡化輸出，可能隱藏了某些資訊。

**解決**: 不使用 `--format short`，或使用 `filter-log-events`

---

## 📝 推薦的查詢方式

### 最簡單（適合日常使用）

```bash
# 一行命令看所有審計日誌
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 \
  --since 1h | \
  grep -i "memory operation\|audit"
```

### 最詳細（適合深入分析）

```bash
# 使用 filter-log-events 查詢完整資訊
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/telegram-unified-bot-processor \
  --filter-pattern "memory_audit" \
  --start-time $(($(date +%s) - 3600))000 \
  --query 'events[*].[timestamp, message]' \
  --output table
```

### 實時監控（適合觀察即時操作）

```bash
# 實時顯示審計日誌
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 \
  --follow | \
  grep --line-buffered -i "audit\|memory operation"
```

---

## 🎯 給你的專屬查詢命令

基於你的 actor_id，這些命令可以查看你的所有操作：

```bash
# 查看你的所有 Memory 操作
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 \
  --since 1d | \
  grep "actor-3544f0d54239dacf"

# 查看你的 Session 創建記錄
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 \
  --since 1d | \
  grep "Session: 316743844"

# 查看你的審計日誌
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/telegram-unified-bot-processor \
  --filter-pattern "actor-3544f0d54239dacf"
```

---

## ✅ 確認

**你的審計日誌是存在的！**

在 03:28:55 UTC (11:28 UTC+8)：
```
✅ Memory operation: create_session
✅ Actor: actor-3544f0d54239dacf
✅ Session: 316743844
✅ 操作成功
```

之後我可以為你創建一個便捷的查詢腳本，或者幫你設定 CloudWatch Dashboard 來可視化這些日誌。需要嗎？
</response>
<task_progress>
- [x] 找到用戶的審計日誌（03:28:55 UTC）
- [x] 確認審計功能正常運作
- [x] 提供完整的查詢指南
- [ ] 等待用戶確認是否需要便捷腳本或 Dashboard
</task_progress>
</attempt_completion>
