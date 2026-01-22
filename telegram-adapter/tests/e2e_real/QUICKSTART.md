# E2E 測試快速開始指南

本指南幫助你快速設置並運行真實環境 E2E 測試。

## 🚀 5 分鐘快速開始

### Step 1: 確認 Lambda 已部署 ✅

```bash
# 檢查 Lambda 狀態
aws lambda get-function \
  --function-name agentcore-ai-processor-main \
  --region us-west-2 \
  --query 'Configuration.State'

# 應該返回：Active
```

### Step 2: 設置環境變數

```bash
cd telegram-adapter/tests/e2e_real

# 複製範例
cp .env.test.example .env.test

# 編輯 .env.test
nano .env.test
```

填入以下內容：
```bash
# 1. 獲取 Bot Token
aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-adapter-receiver-secrets \
  --query SecretString --output text | jq -r .bot_token

# 2. 填入 .env.test
TELEGRAM_BOT_TOKEN=你剛獲取的_token
TEST_CHAT_ID=316743844  # 你的 Telegram ID
```

### Step 3: 準備測試圖片

**選項 A：使用你自己的圖片**
```bash
# 將任何圖片複製並重命名
cp ~/Downloads/my_photo.jpg fixtures/test_noodle.jpg
```

**選項 B：從網路下載測試圖片**
```bash
# 下載任何公開圖片
curl -o fixtures/test_noodle.jpg https://example.com/noodle.jpg
```

**檔案已創建**：
- ✅ `fixtures/test_data.csv` - 測試數據
- ✅ `fixtures/test_report.txt` - 測試報告

### Step 4: 安裝依賴

```bash
cd telegram-adapter
pip install pytest-asyncio python-dotenv aiogram
```

### Step 5: 運行測試

```bash
# 運行所有測試
pytest tests/e2e_real/ -v -s

# 或只運行一個測試
pytest tests/e2e_real/test_image_tools.py::test_image_basic_analysis -v -s
```

## 📊 預期輸出

```
tests/e2e_real/test_image_tools.py::test_image_basic_analysis 
📸 測試 1：圖片基本分析
  → 上傳測試圖片...
  ✅ 圖片已上傳（message_id: 123）
  ⏳ 等待 AI 回應（最多 60 秒）...
  ✅ 收到回應：這是一碗泡麵...
  🔍 檢查 Lambda 日誌...
  ✅ analyze_image_tool 已被調用
  ✅ 無錯誤日誌
  🎉 測試 1 通過！
PASSED

======================== 1 passed in 35s ========================
```

## 🎯 測試涵蓋的 5 個場景

1. ✅ **圖片基本分析** - `test_image_basic_analysis`
2. ✅ **同對話追問圖片** - `test_image_memory_followup`
3. ✅ **檔案基本分析** - `test_file_basic_analysis`
4. ✅ **同對話追問檔案** - `test_file_memory_followup`
5. ✅ **工具組合使用** - `test_image_and_search`

## ⚠️ 常見問題

### Q: 測試超時怎麼辦？

**A**: 增加超時時間
```bash
export E2E_TIMEOUT=90
pytest tests/e2e_real/ -v -s
```

### Q: 找不到測試圖片？

**A**: 準備測試素材
```bash
# 方法 1：使用你的圖片
cp ~/your_photo.jpg fixtures/test_noodle.jpg

# 方法 2：跳過圖片測試
pytest tests/e2e_real/ -k "not image" -v -s
```

### Q: 測試會產生多少費用？

**A**: 
- 每個測試：約 $0.001-0.01
- 完整套件：約 $0.05-0.10
- 建議每天最多運行 5 次

### Q: 測試會弄亂我的對話嗎？

**A**: 不會影響正常使用
- 測試使用獨立的 session
- 測試完會自動清理（`/clearsession`）
- 或手動發送 `/clearsession` 清理

## 🔍 驗證部署

在運行測試前，先驗證部署是否正確：

```bash
# 1. 檢查 Lambda 函數
aws lambda list-functions --region us-west-2 \
  --query 'Functions[?contains(FunctionName, `agentcore`)].FunctionName'

# 2. 檢查環境變數
aws lambda get-function-configuration \
  --function-name agentcore-ai-processor-main \
  --region us-west-2 \
  --query 'Environment.Variables'

# 3. 測試 Lambda（手動發送訊息到 Telegram）
# 在 Telegram 發送：「你好」
# 應該收到回應

# 4. 查看日誌
aws logs tail /aws/lambda/agentcore-ai-processor-main \
  --region us-west-2 --since 5m
```

## 📚 更多資訊

- [完整 README](./README.md) - 詳細文檔
- [測試素材說明](./fixtures/README.md) - 素材準備
- [部署指南](../../../docs/deployment-guide.md) - 部署說明

---

**開始測試吧！** 🚀

如果遇到問題，查看 [README.md](./README.md) 的故障排除章節。