# 圖片分析功能測試指南

## 🧪 測試準備

### 前置條件
- [x] 代碼語法檢查通過
- [ ] SAM 部署完成
- [ ] Lambda 函數狀態正常
- [ ] Telegram webhook 已設置

## 📋 測試場景

### 場景 1: 基礎圖片描述

**測試步驟**：
1. 在 Telegram 上傳一張風景照
2. 不添加任何文字說明

**預期結果**：
```
Bot: 這是一張[詳細的圖片描述]...
```

**驗證點**：
- ✅ Bot 能收到並處理圖片
- ✅ 回應為中文
- ✅ 描述準確且詳細

---

### 場景 2: 帶問題的圖片分析

**測試步驟**：
1. 上傳一張食物照片
2. 添加文字：「這道菜有哪些食材？」

**預期結果**：
```
Bot: 從圖片中可以看到這道菜包含以下食材：
1. [食材1]
2. [食材2]
...
```

**驗證點**：
- ✅ Bot 能同時處理圖片和文字
- ✅ 回應針對具體問題
- ✅ 答案準確

---

### 場景 3: Memory 連續性測試

**測試步驟**：
1. 上傳一張圖片
2. Bot 回應後，發送：「剛才那張圖片裡有幾個人？」

**預期結果**：
```
Bot: 根據剛才的圖片，裡面有 [數量] 個人...
```

**驗證點**：
- ✅ Bot 記得之前分析的圖片
- ✅ 可以回答後續問題
- ✅ Memory 功能正常

---

### 場景 4: 多張圖片（如果支援）

**測試步驟**：
1. 連續上傳多張圖片
2. 觀察 Bot 反應

**預期結果**：
- 每張圖片都能被處理
- 回應清楚標明是哪張圖片

---

### 場景 5: OCR 文字識別

**測試步驟**：
1. 上傳包含文字的圖片（如菜單、告示牌）
2. 問：「這張圖片上寫了什麼？」

**預期結果**：
```
Bot: 圖片上的文字內容是：
[識別出的文字]
```

**驗證點**：
- ✅ 能識別圖片中的文字
- ✅ 中文識別準確
- ✅ 英文識別準確

---

## 🔍 日誌檢查

### 關鍵日誌位置

**Receiver Lambda**：
```bash
aws logs tail /aws/lambda/telegram-adapter-receiver \
  --region us-west-2 --since 5m --follow
```

**查找**：
- ✅ `Processing image: [filename]`
- ✅ `Image converted to base64`
- ✅ `attachment_type: photo`

**Processor Lambda**：
```bash
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 --since 5m --follow
```

**查找**：
- ✅ `處理多模態訊息: 1 張圖片`
- ✅ `構建多模態內容`
- ✅ `傳遞 1 張圖片到 Agent`

---

## ⚠️ 常見問題排除

### 問題 1: 圖片未被識別為 photo 類型

**症狀**：圖片被當作文件處理

**檢查**：
```bash
# 查看 file_handler.py 的日誌
grep "attachment_type" /aws/lambda/telegram-adapter-receiver/logs
```

**解決**：確認 `_detect_attachment_type()` 函數正常工作

---

### 問題 2: Base64 轉換失敗

**症狀**：日誌顯示 "Failed to read image from S3"

**檢查**：
- S3 bucket 權限
- 圖片是否成功上傳到 S3

**解決**：
```bash
# 檢查 S3
aws s3 ls s3://telegram-files-bucket/[chat_id]/[message_id]/
```

---

### 問題 3: Agent 未收到圖片

**症狀**：沒有 "構建多模態內容" 日誌

**檢查**：
```python
# processor_entry.py 是否正確判斷
if attachment.get('type') == 'photo':
```

---

### 問題 4: Claude 回應錯誤

**症狀**：收到錯誤訊息或空回應

**可能原因**：
1. 圖片格式不支援
2. 圖片太大（> 5MB）
3. Base64 編碼錯誤

**檢查**：
```bash
# 查看完整錯誤
aws logs filter-log-events \
  --log-group-name /aws/lambda/telegram-unified-bot-processor \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '10 minutes ago' +%s)000
```

---

## 📊 性能指標

### 預期性能
- **圖片處理時間**：5-15 秒
  - S3 讀取：< 1 秒
  - Base64 轉換：< 1 秒
  - AI 分析：5-30 秒

### Token 消耗
- **基準**：每張圖片 ≈ 1,600 tokens
- **加文字**：1,600 + 文字 tokens

### 監控指標
```bash
# Lambda 執行時間
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=telegram-unified-bot-processor \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --period 300 \
  --statistics Average,Maximum
```

---

## ✅ 測試檢查清單

### 部署前
- [x] 語法檢查通過
- [ ] SAM validate 通過
- [ ] SAM build 成功

### 部署後
- [ ] Lambda 狀態：Active
- [ ] LastUpdateStatus: Successful
- [ ] 環境變數正確配置

### 功能測試
- [ ] 場景 1: 基礎圖片描述
- [ ] 場景 2: 帶問題的圖片分析
- [ ] 場景 3: Memory 連續性
- [ ] 場景 4: 多張圖片
- [ ] 場景 5: OCR 文字識別

### 性能測試
- [ ] 回應時間 < 30 秒
- [ ] 無錯誤日誌
- [ ] Memory 使用正常

---

## 🎯 驗收標準

功能完成的標準：

1. ✅ **基礎功能**
   - 能接收並分析圖片
   - 能用中文回答圖片相關問題

2. ✅ **架構整合**
   - 使用 Strands Agent 架構
   - Memory 功能正常
   - 可以調用其他 Tools

3. ✅ **穩定性**
   - 無語法錯誤
   - 錯誤處理完善
   - 日誌記錄清晰

4. ✅ **用戶體驗**
   - 回應速度可接受
   - 回應內容準確
   - 中文表達自然

---

**測試指南版本**: v1.0  
**創建日期**: 2026-01-07  
**適用範圍**: 圖片分析功能初版測試
