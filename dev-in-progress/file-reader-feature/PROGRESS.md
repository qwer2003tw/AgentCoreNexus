# Feature: AgentCore 檔案讀取功能

**狀態**: 🔄 進行中  
**開始時間**: 2026-01-07  
**負責 Agent**: Cline AI

## 📋 任務清單

### Phase 0: SAM Template 更新（✅ 完成！）
- [x] 更新 `telegram-lambda/template.yaml` 添加 S3 bucket 定義
- [x] 更新 `telegram-lambda/template.yaml` 添加 S3 權限和環境變數
- [x] 更新 `telegram-lambda/template.yaml` 添加 Outputs
- [x] 更新 `telegram-agentcore-bot/template.yaml` 添加 Parameters
- [x] 更新 `telegram-agentcore-bot/template.yaml` 添加環境變數和 ImportValue
- [x] 更新 `telegram-agentcore-bot/template.yaml` 添加 Code Interpreter 權限
- [x] 修正 SAM 驗證錯誤（BucketEncryption 屬性名稱）
- [x] 測試 SAM 驗證：`sam validate` ✅ 兩個 templates 都通過

### Phase 1: Receiver Lambda 更新（2 天）
- [ ] 創建 `file_handler.py`
- [ ] 更新 `secrets_manager.py` 添加 `get_bot_token()`
- [ ] 更新 `handler.py` 的 `normalize_message()`
- [ ] 添加檔案權限檢查
- [ ] 測試檔案下載和 S3 上傳

### Phase 2: Processor Lambda 更新（2 天）
- [ ] 創建 `file_service.py`
- [ ] 實作從 S3 讀取檔案
- [ ] 實作 Code Interpreter 整合
- [ ] 添加審計日誌
- [ ] 單元測試

### Phase 3: 權限系統（1 天）
- [ ] 更新 `allowlist.py`
- [ ] 手動更新 DynamoDB 測試資料
- [ ] 測試權限檢查

### Phase 4: 工具註冊（1 天）
- [ ] 創建 `file_reader.py`
- [ ] 註冊到 Agent
- [ ] 端到端測試

### Phase 5: 文件與部署（1 天）
- [ ] 撰寫使用文檔
- [ ] 部署到生產環境
- [ ] 監控和調整

## 🎯 目標

實作完整的檔案讀取功能，讓 Telegram Bot 能夠：
1. 接收用戶上傳的檔案（文字檔、CSV、JSON、圖片等）
2. 使用 AWS Code Interpreter 處理檔案
3. 根據 Caption 或預設執行摘要
4. 返回處理結果給用戶

## 🔑 關鍵決策

- **檔案來源**：僅支援 Telegram 上傳（20MB 限制）
- **Session 管理**：每次新建 session
- **權限控制**：DynamoDB `permissions.file_reader` 欄位
- **檔案傳遞**：Receiver Lambda 下載 → 上傳到 S3 → 傳遞 URL
- **Caption 處理**：有則執行任務，無則執行預設摘要
- **S3 管理**：使用 SAM Template 定義（IaC）

## 📝 開發筆記

### 2026-01-07 04:47 - 06:17 UTC（1.5 小時）

#### Phase 0: SAM Template 更新 ✅
- 更新 `telegram-lambda/template.yaml`
  - 添加 S3 Bucket 資源定義（FileStorageBucket）
  - 添加環境變數（FILE_STORAGE_BUCKET, ENVIRONMENT）
  - 添加 S3 權限（PutObject, GetObject）
  - 導出 Bucket 名稱和 ARN
- 更新 `telegram-agentcore-bot/template.yaml`
  - 添加 ReceiverStackName 參數
  - 使用 ImportValue 引用 S3 bucket
  - 添加 Code Interpreter 權限
  - 添加 S3 讀取權限
- SAM 驗證：兩個 templates 都通過 ✅

#### Phase 1: Receiver Lambda 更新 ✅
- 創建 `telegram-lambda/src/file_handler.py`
  - `get_bot_token()`: 從 Secrets Manager 獲取 token
  - `download_telegram_file()`: 從 Telegram API 下載檔案
  - `upload_to_s3()`: 上傳檔案到 S3
  - `process_file_attachment()`: 完整的檔案處理流程
  - `validate_file_size()`: 檔案大小驗證
- 更新 `telegram-lambda/src/allowlist.py`
  - `check_file_permission()`: 檢查檔案讀取權限
  - `update_file_permission()`: 更新權限（管理員使用）
- 更新 `telegram-lambda/src/handler.py`
  - 導入 file_handler 和權限檢查
  - 更新 `normalize_message()` 處理檔案附件
  - 整合權限檢查和 S3 上傳
- 添加 `requests>=2.31.0` 到 requirements.txt

#### Phase 2: Processor Lambda 更新 ✅
- 更新 `telegram-agentcore-bot/config/settings.py`
  - 添加 FILE_ENABLED, FILE_STORAGE_BUCKET, FILE_SESSION_TIMEOUT
- 創建 `telegram-agentcore-bot/services/file_service.py`
  - `FileService`: 主要服務類
  - `read_from_s3()`: 從 S3 讀取檔案
  - `process_file()`: 使用 Code Interpreter 處理檔案
  - 三種處理模式：摘要、分析、統計
- 創建 `telegram-agentcore-bot/tools/file_reader.py`
  - `read_file()`: 檔案讀取工具函數
  - 延遲初始化檔案服務
- 註冊到 `telegram-agentcore-bot/tools/__init__.py`
- 更新 `telegram-agentcore-bot/processor_entry.py`
  - 導入 file_service
  - 添加 `process_file_attachments()` 函數
  - 整合檔案處理到訊息處理流程

#### 實作亮點
1. **權限精細控制**：DynamoDB `permissions.file_reader` 欄位
2. **完整的審計日誌**：所有檔案操作都記錄
3. **錯誤處理完善**：優雅處理各種失敗情境
4. **S3 自動管理**：30天自動清理，啟用加密和版本控制
5. **Caption 支援**：用戶可透過 Caption 指定處理任務
