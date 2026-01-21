# AgentCore 檔案讀取功能 - 測試指南

**版本**: 1.0  
**日期**: 2026-01-07  
**狀態**: ✅ 部署完成，準備測試

---

## ✅ 部署驗證

### 已完成的配置

#### 1. Lambda 函數
- ✅ **Receiver**: `telegram-adapter-receiver` (UPDATE_COMPLETE)
- ✅ **Processor**: `telegram-unified-bot-processor` (UPDATE_COMPLETE)

#### 2. S3 Bucket
- ✅ **Bucket**: `telegram-bot-files-190825685292-prod`
- ✅ **生命週期**: 30 天自動刪除
- ✅ **加密**: AES256 啟用

#### 3. 環境變數
**Receiver Lambda**:
- ✅ FILE_STORAGE_BUCKET: `telegram-bot-files-190825685292-prod`
- ✅ ENVIRONMENT: `prod`

**Processor Lambda**:
- ✅ FILE_ENABLED: `true`
- ✅ FILE_STORAGE_BUCKET: `telegram-bot-files-190825685292-prod`

#### 4. 用戶權限
- ✅ Chat ID: `316743844`
- ✅ Username: `qwer2003tw`
- ✅ permissions.file_reader: `True`

---

## 🧪 測試計畫

### 測試 1: 上傳文字檔（無 Caption）

**步驟**：
1. 透過 Telegram 上傳一個 `.txt` 檔案
2. 不添加 Caption
3. 等待 Bot 回應

**預期結果**：
```
📁 檔案：filename.txt
📄 檔案摘要
檔案名稱: filename.txt
總行數: XX
總字元數: XXX
檔案大小: XXX bytes

📝 前 15 行內容:
1. [內容]
2. [內容]
...
```

**驗證點**：
- [ ] 檔案成功下載
- [ ] 檔案上傳到 S3
- [ ] Code Interpreter 成功處理
- [ ] 返回摘要結果

---

### 測試 2: 上傳 CSV（有 Caption）

**步驟**：
1. 準備一個 CSV 檔案（包含標題行和數據）
2. 上傳到 Telegram
3. 添加 Caption: "分析這個檔案"

**預期結果**：
```
📁 檔案：data.csv
📊 檔案分析: data.csv
檔案類型: .csv

✅ CSV 檔案分析
總行數: XX

欄位清單:
  1. column1
  2. column2
  ...

前 5 筆資料:
第 1 筆:
  - column1: value1
  - column2: value2
...
```

**驗證點**：
- [ ] Caption 被正確識別
- [ ] 執行分析模式（不是摘要）
- [ ] CSV 結構正確解析
- [ ] 顯示欄位和數據

---

### 測試 3: 上傳 JSON（Caption: "統計"）

**步驟**：
1. 準備一個 JSON 檔案
2. 上傳到 Telegram
3. 添加 Caption: "統計"

**預期結果**：
```
📁 檔案：config.json
📈 統計分析: config.json

✅ JSON 統計資訊
陣列長度: XX / 物件鍵數量: XX
...
```

**驗證點**：
- [ ] 統計模式被觸發
- [ ] JSON 結構正確識別
- [ ] 顯示統計資訊

---

### 測試 4: 無權限用戶測試

**注意**：需要另一個測試用戶（無 file_reader 權限）

**步驟**：
1. 使用無權限用戶上傳檔案
2. 觀察 Bot 行為

**預期結果**：
- 檔案不被處理
- 沒有下載動作
- 日誌記錄權限拒絕

**驗證點**：
- [ ] 檢查 CloudWatch Logs 有 `file_permission_denied` 事件
- [ ] S3 bucket 沒有對應檔案
- [ ] 不消耗處理資源

---

## 📋 監控檢查清單

### CloudWatch Logs 驗證

#### Receiver Lambda 日誌
```bash
aws logs tail /aws/lambda/telegram-adapter-receiver --region us-west-2 --since 5m --follow
```

**尋找的日誌**：
- ✅ `File permission check: True` - 權限通過
- ✅ `Got file_path` - 檔案路徑獲取
- ✅ `Downloaded file: X bytes` - 檔案下載
- ✅ `Uploaded to S3` - S3 上傳
- ✅ `File processing completed` - 處理完成

#### Processor Lambda 日誌
```bash
aws logs tail /aws/lambda/telegram-unified-bot-processor --region us-west-2 --since 5m --follow
```

**尋找的日誌**：
- ✅ `Processing file: filename` - 開始處理
- ✅ `Read from S3: X bytes` - S3 讀取
- ✅ `Code Interpreter session 已啟動` - Session 創建
- ✅ `檔案已上傳到 session` - 檔案上傳
- ✅ `File processed successfully` - 處理成功
- ✅ `Session 已清理` - Session 清理

### S3 Bucket 驗證

```bash
# 檢查上傳的檔案
aws s3 ls s3://telegram-bot-files-190825685292-prod/ --recursive --region us-west-2

# 預期結構：316743844/MESSAGE_ID/filename
```

### 審計日誌驗證

```bash
# 搜索審計日誌
aws logs filter-log-events \
  --region us-west-2 \
  --log-group-name /aws/lambda/telegram-unified-bot-processor \
  --filter-pattern "FILE_PROCESS" \
  --start-time $(date -u -d '10 minutes ago' +%s)000
```

**尋找的事件**：
- `FILE_PROCESS_START`
- `FILE_PROCESS_SUCCESS`
- （如果失敗）`FILE_PROCESS_FAILURE`

---

## 🎯 測試場景

### 場景 A: 成功的檔案處理
1. 上傳 `test.txt`（內容：Hello World）
2. 無 Caption
3. 預期：返回檔案摘要

### 場景 B: Caption 任務執行
1. 上傳 `data.csv`（簡單的 2x3 表格）
2. Caption: "分析"
3. 預期：返回 CSV 分析（欄位、數據）

### 場景 C: 統計模式
1. 上傳 `config.json`（包含物件或陣列）
2. Caption: "統計"
3. 預期：返回統計資訊

### 場景 D: 大檔案測試
1. 上傳接近 20MB 的檔案
2. 觀察處理時間
3. 預期：成功處理（可能較慢）

---

## 🐛 故障排除

### 如果檔案沒有被處理

#### 檢查 1: 權限
```bash
aws dynamodb get-item --region us-west-2 \
  --table-name telegram-allowlist \
  --key '{"chat_id":{"N":"YOUR_CHAT_ID"}}' \
  --query 'Item.permissions.M.file_reader.BOOL'
```
應該返回：`True`

#### 檢查 2: Receiver Lambda 日誌
```bash
aws logs tail /aws/lambda/telegram-adapter-receiver \
  --region us-west-2 --since 5m | grep -i "file"
```
尋找：`file_permission_check`, `file_processing`

#### 檢查 3: S3 上傳
```bash
aws s3 ls s3://telegram-bot-files-190825685292-prod/YOUR_CHAT_ID/ --recursive
```
應該看到上傳的檔案

#### 檢查 4: Processor Lambda 日誌
```bash
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 --since 5m | grep -i "file"
```
尋找：`Processing file`, `File processed successfully`

---

## 📊 成功指標

### 技術指標
- [ ] 檔案上傳成功率 100%
- [ ] S3 儲存成功率 100%  
- [ ] Code Interpreter 處理成功率 >90%
- [ ] 平均響應時間 <25 秒
- [ ] 權限檢查準確率 100%

### 功能指標
- [ ] 摘要模式正常工作
- [ ] 分析模式正常工作（CSV, JSON）
- [ ] 統計模式正常工作
- [ ] Caption 任務正確執行
- [ ] 無權限用戶被正確拒絕

---

## 🚀 快速測試命令

### 準備測試檔案
```bash
# 創建測試文字檔
echo "Hello World\nThis is a test file\nLine 3" > test.txt

# 創建測試 CSV
echo "name,age,city\nAlice,30,NY\nBob,25,LA" > test.csv

# 創建測試 JSON
echo '{"users":[{"name":"Alice","age":30},{"name":"Bob","age":25}]}' > test.json
```

### 監控命令（在測試時執行）
```bash
# 終端 1: Receiver 日誌
aws logs tail /aws/lambda/telegram-adapter-receiver \
  --region us-west-2 --follow

# 終端 2: Processor 日誌
aws logs tail /aws/lambda/telegram-unified-bot-processor \
  --region us-west-2 --follow

# 終端 3: S3 監控
watch -n 5 'aws s3 ls s3://telegram-bot-files-190825685292-prod/ --recursive'
```

---

## ✅ 部署完成檢查清單

### 基礎設施
- [x] S3 Bucket 已創建
- [x] Receiver Lambda 已部署
- [x] Processor Lambda 已部署
- [x] EventBridge Rules 正確配置

### 配置
- [x] 環境變數設定正確
- [x] IAM 權限已添加
- [x] 用戶權限已啟用

### 準備測試
- [x] 測試用戶已配置
- [ ] 測試檔案已準備
- [ ] 監控命令已就緒

---

## 🎉 功能已就緒！

**系統狀態**: ✅ 完全部署並配置完成  
**測試用戶**: `@qwer2003tw` (chat_id: 316743844)  
**權限**: `file_reader: True`

**下一步**: 透過 Telegram 上傳檔案開始測試！

---

**指南版本**: 1.0  
**最後更新**: 2026-01-07 06:30 UTC  
**作者**: AgentCoreNexus Team
