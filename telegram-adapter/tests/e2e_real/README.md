# 真實環境 E2E 測試

本目錄包含真實環境的端對端測試，測試完整的 Telegram Bot → AWS Lambda → AI 處理 → 回應流程。

## 🎯 測試目的

驗證在真實 AWS 環境中：
- ✅ 圖片分析 tool 正確運作
- ✅ 檔案分析 tool 正確運作  
- ✅ Memory 在同一對話內保留附件 S3 URL
- ✅ Agent 可以追問之前的圖片/檔案
- ✅ 多個 tools 可以組合使用

## ⚙️ 前置需求

### 1. AWS Lambda 已部署

```bash
cd ai-processor
sam build
sam deploy --stack-name agentcore-ai-processor \
  --region us-west-2 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3
```

### 2. 環境變數設置

複製範例檔案：
```bash
cp .env.test.example .env.test
```

編輯 `.env.test`：
```bash
# 從 Secrets Manager 獲取 bot token
aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-adapter-receiver-secrets \
  --query SecretString --output text | jq -r .bot_token

# 填入 .env.test
TELEGRAM_BOT_TOKEN=你的_bot_token
TEST_CHAT_ID=316743844  # 你的 Telegram ID
```

### 3. 測試用戶在 Allowlist

```bash
# 檢查
aws dynamodb get-item \
  --region us-west-2 \
  --table-name telegram-allowlist \
  --key '{"chat_id":{"N":"316743844"}}'

# 如果不存在，添加
aws dynamodb put-item \
  --region us-west-2 \
  --table-name telegram-allowlist \
  --item '{"chat_id":{"N":"316743844"},"username":{"S":"qwer2003tw"}}'
```

### 4. 安裝測試依賴

```bash
cd telegram-adapter
pip install -r requirements-test.txt
```

確保包含：
- `pytest-asyncio>=0.23.0`
- `python-dotenv>=1.0.0`
- `aiogram>=3.0.0`
- `boto3>=1.28.0`

## 🚀 運行測試

### 運行所有 E2E 測試

```bash
cd telegram-adapter
pytest tests/e2e_real/ -v -s
```

### 運行特定測試

```bash
# 只測試圖片
pytest tests/e2e_real/test_image_tools.py -v -s

# 只測試檔案
pytest tests/e2e_real/test_file_tools.py -v -s

# 只測試工具組合
pytest tests/e2e_real/test_tool_composition.py -v -s
```

### 運行特定測試案例

```bash
# 測試 1：圖片基本分析
pytest tests/e2e_real/test_image_tools.py::test_image_basic_analysis -v -s

# 測試 2：Memory 追問
pytest tests/e2e_real/test_image_tools.py::test_image_memory_followup -v -s
```

### 使用 pytest markers

```bash
# 只運行圖片測試
pytest tests/e2e_real/ -m image -v -s

# 只運行 Memory 測試
pytest tests/e2e_real/ -m memory -v -s

# 排除慢速測試
pytest tests/e2e_real/ -m "not slow" -v -s
```

## 📁 測試結構

```
tests/e2e_real/
├── README.md                    # 本文件
├── .env.test.example            # 環境變數範例
├── .env.test                    # 實際環境變數（不進 Git）
├── conftest.py                  # pytest 配置
├── test_image_tools.py          # 圖片分析測試（3 個）
├── test_file_tools.py           # 檔案分析測試（3 個）
├── test_tool_composition.py     # 工具組合測試（2 個）
├── fixtures/                    # 測試素材
│   ├── test_noodle.jpg          # 測試圖片
│   ├── test_data.csv            # 測試 CSV
│   └── test_report.txt          # 測試文字檔
└── helpers/
    ├── bot_client.py            # Bot 操作封裝
    ├── log_fetcher.py           # CloudWatch 查詢
    └── __init__.py
```

## 📊 測試覆蓋範圍

### 已實現的測試

#### 圖片測試（test_image_tools.py）
- ✅ `test_image_basic_analysis`：基本圖片分析
- ✅ `test_image_memory_followup`：Memory 追問功能
- ✅ `test_image_no_caption`：無說明圖片主動分析

#### 檔案測試（test_file_tools.py）
- ✅ `test_file_basic_analysis`：基本檔案分析
- ✅ `test_file_memory_followup`：檔案 Memory 追問
- ✅ `test_multiple_files`：多檔案處理

#### 工具組合測試（test_tool_composition.py）
- ✅ `test_image_and_search`：圖片 + 搜尋組合
- ✅ `test_image_and_file_together`：圖片 + 檔案混合

## ⏱️ 預期時間

- **單個測試**：10-60 秒（取決於 AI 處理時間）
- **完整套件**：5-10 分鐘（8 個測試）
- **建議**：分批運行，避免過長等待

## 💰 成本估算

- **每個測試**：約 $0.001-0.01（Bedrock API 費用）
- **完整套件**：約 $0.05-0.10
- **建議**：在 CI/CD 中限制執行頻率

## 🐛 故障排除

### 問題 1：測試超時

**症狀**：`AI 沒有回應（超時）`

**檢查**：
```bash
# 查看 Lambda 日誌
aws logs tail /aws/lambda/agentcore-ai-processor-processor \
  --region us-west-2 --since 5m

# 檢查 Lambda 狀態
aws lambda get-function \
  --function-name agentcore-ai-processor-processor \
  --region us-west-2 \
  --query 'Configuration.State'
```

### 問題 2：Tool 沒有被調用

**症狀**：`analyze_image_tool 沒有被調用`

**檢查**：
- Lambda 環境變數是否正確
- System Prompt 是否已更新
- Tools 是否正確註冊

### 問題 3：Memory 失去上下文

**症狀**：追問時 Agent 說「找不到圖片」

**檢查**：
- BEDROCK_AGENTCORE_MEMORY_ID 是否配置
- Memory 是否啟用
- Session ID 是否一致

## 📚 相關文檔

- [整合測試](../integration/README.md) - Mock 測試
- [部署指南](../../../docs/deployment-guide.md)
- [CloudWatch Logs](../../../docs/monitoring-guide.md)

## ⚠️ 注意事項

### 測試素材

**必須準備**：
- `fixtures/test_noodle.jpg` - 泡麵圖片（用於測試）
- `fixtures/test_data.csv` - 測試 CSV 檔案
- `fixtures/test_report.txt` - 測試文字檔案

**可以使用任何圖片/檔案**，但：
- 圖片：< 5MB，JPG/PNG 格式
- 檔案：< 20MB，常見格式

### Telegram API 限制

- 每秒最多 30 個請求
- 每分鐘最多 20 個圖片
- 測試間隔建議 > 2 秒

### Memory Session

- 每個測試使用 `clean_session` fixture 確保獨立
- 測試完畢會自動清理（`/clearsession`）
- 如果測試中斷，手動發送 `/clearsession` 清理

## 🎓 撰寫新測試

### 基本模板

```python
@pytest.mark.real_e2e
@pytest.mark.asyncio
async def test_my_feature(bot_client, log_fetcher, test_config, clean_session):
    """測試描述"""
    print("\n📝 測試：我的功能")
    
    # 1. 發送訊息
    await bot_client.send_text("測試訊息")
    
    # 2. 等待回應
    reply = await bot_client.wait_for_reply(timeout=test_config['e2e_timeout'])
    
    # 3. 驗證
    assert reply is not None
    print(f"  ✅ 回應：{reply[:100]}")
    
    # 4. 檢查日誌（可選）
    tool_called = log_fetcher.check_tool_called(
        lambda_name=test_config['processor_lambda'],
        tool_name="My Tool",
        since_seconds=120
    )
    
    print("  🎉 測試通過！")
```

---

**版本**: 1.0  
**創建日期**: 2026-01-22  
**維護者**: AgentCoreNexus Team