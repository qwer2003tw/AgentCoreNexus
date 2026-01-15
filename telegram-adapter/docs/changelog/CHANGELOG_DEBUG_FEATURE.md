# 變更日誌 - `/debug test` 功能

## 版本資訊
- **功能**: 新增 `/debug test` 除錯指令
- **日期**: 2025-11-04
- **類型**: 功能增強

## 變更摘要

新增了一個特殊的除錯指令，允許用戶透過 Telegram 查看 Lambda 收到的完整 API Gateway event，方便開發和故障排除。

## 新增檔案

### 1. `src/telegram_client.py`
- **用途**: Telegram Bot API 客戶端
- **主要功能**:
  - `send_message()` - 發送訊息到 Telegram
  - `send_long_message()` - 自動分段發送長訊息
  - `send_debug_info()` - 格式化並發送除錯資訊
  - `_split_message()` - 訊息分割邏輯
- **依賴**: 使用 Python 內建的 `urllib`，無需額外套件

### 2. `tests/test_telegram_client.py`
- **用途**: Telegram Client 的單元測試
- **測試案例**: 13 個測試，涵蓋：
  - 成功發送訊息
  - 錯誤處理（無 token、API 錯誤、網路錯誤）
  - 訊息分割
  - 除錯資訊發送

### 3. `tests/conftest.py`
- **用途**: Pytest 配置檔案
- **功能**: 設定 Python 模組路徑，修正測試導入問題

### 4. `DEBUG_COMMAND.md`
- **用途**: 除錯功能詳細說明文件
- **內容**: 使用方式、安全注意事項、技術實作、故障排除

### 5. `CHANGELOG_DEBUG_FEATURE.md`
- **用途**: 本變更日誌

## 修改檔案

### 1. `src/handler.py`
**變更內容**:
- 新增 `from telegram_client import send_debug_info`
- 新增 `/debug test` 指令檢測邏輯
- 在驗證 chat_id 後、允許名單檢查前處理除錯指令
- 返回 `debug_sent` 或 `debug_failed` 狀態

**程式碼片段**:
```python
# 檢查是否為 /debug test 指令
if text and text.strip() == '/debug test':
    # 發送除錯資訊
    debug_sent = send_debug_info(chat_id, event)
    if debug_sent:
        return create_response(200, {'status': 'debug_sent'})
    else:
        return create_response(200, {'status': 'debug_failed'})
```

### 2. `template.yaml`
**變更內容**:
- 新增環境變數 `TELEGRAM_BOT_TOKEN: ''`

**程式碼片段**:
```yaml
Environment:
  Variables:
    TELEGRAM_SECRET_TOKEN: ''
    TELEGRAM_BOT_TOKEN: ''        # 新增
    SQS_QUEUE_URL: !Ref TelegramInboundQueue
    ALLOWLIST_TABLE_NAME: !Ref AllowlistTable
```

### 3. `tests/test_handler.py`
**變更內容**:
- 新增 6 個測試案例：
  - `test_debug_command` - 基本除錯指令測試
  - `test_debug_command_with_spaces` - 帶空格的指令
  - `test_debug_command_send_failure` - 發送失敗情況
  - `test_non_debug_command` - 確保非除錯指令正常處理
  - `test_debug_command_missing_chat_id` - 缺少 chat_id 的錯誤處理

### 4. `README.md`
**變更內容**:
- 新增「🐛 除錯功能」章節
- 更新環境變數表格，新增 `TELEGRAM_BOT_TOKEN`
- 更新專案結構，新增 `telegram_client.py` 和 `test_telegram_client.py`

## 測試結果

```
✅ 46 個測試全部通過
- test_allowlist.py: 10 個測試通過
- test_handler.py: 16 個測試通過（含 6 個新測試）
- test_sqs_client.py: 7 個測試通過
- test_telegram_client.py: 13 個測試通過（新增）
```

## 使用方式

1. **設定 Bot Token**:
   ```bash
   aws lambda update-function-configuration \
     --function-name telegram-adapter-receiver \
     --environment Variables="{...TELEGRAM_BOT_TOKEN='YOUR_TOKEN'...}"
   ```

2. **發送指令**:
   在 Telegram 中向 Bot 發送 `/debug test`

3. **查看結果**:
   Bot 會回覆完整的 API Gateway event JSON

## 安全考量

⚠️ **重要**: 當前實作為**完全放行**，任何用戶都可使用此指令。

**建議**:
- 僅在開發/測試環境使用
- 生產環境應移除或加上允許名單限制
- 定期檢視除錯日誌

## 技術細節

### 架構決策
1. **同步處理**: 在 Lambda 中同步發送除錯訊息，不經過 SQS
2. **無額外依賴**: 使用 Python 內建 `urllib`，保持專案輕量
3. **自動分段**: 處理超過 4096 字元的長訊息
4. **優先驗證**: 先驗證 chat_id 存在，再處理除錯指令

### 效能影響
- 增加一個外部 HTTP 請求（Telegram API）
- 預估增加 200-500ms 處理時間
- 僅影響 `/debug test` 指令，不影響正常訊息

## 後續改進建議

1. **短期**:
   - [ ] 加入允許名單限制
   - [ ] 過濾敏感環境變數

2. **中期**:
   - [ ] 支援更多除錯指令（如 `/debug env`、`/debug stats`）
   - [ ] 加入指令權限管理

3. **長期**:
   - [ ] 建立完整的指令系統框架
   - [ ] 支援互動式除錯

## 兼容性

- ✅ 向後兼容：不影響現有功能
- ✅ 可選功能：未設定 Bot Token 時不影響正常運作
- ✅ 測試覆蓋：所有新功能都有完整測試

## 檔案統計

- **新增檔案**: 5 個
- **修改檔案**: 4 個
- **新增程式碼**: ~400 行
- **新增測試**: 19 個測試案例
- **測試通過率**: 100% (46/46)
