# 創建新 Lambda 函數

快速創建新的 Lambda 函數，包含 handler、測試文件和 template.yaml 配置。

## 使用方式

在 Cline 中輸入：`/create-lambda.md`

---

## 執行步驟

### 1. 收集需求信息 📋

詢問用戶以下信息：

```
請提供以下信息來創建 Lambda 函數：

1. Lambda 名稱（例如: message-processor）
2. 用途描述（簡短說明功能）
3. 屬於哪個 stack？
   - telegram-adapter（接收器）
   - ai-processor（處理器）
4. 是否需要環境變數？（Y/N）
5. 是否需要特殊 IAM 權限？（Y/N）
```

**驗證輸入**：
- Lambda 名稱必須使用 kebab-case
- 名稱不能與現有函數衝突

---

### 2. 創建 Handler 文件 📝

根據 stack 類型創建 handler 文件：

#### 如果是 telegram-adapter（接收器）

**文件路徑**: `telegram-adapter/src/[function_name]_handler.py`

**基礎模板**：
```python
"""
[功能描述]
"""
import json
import logging
from typing import Any

# 設置日誌
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Lambda 入口函數
    
    Args:
        event: Lambda event 物件
        context: Lambda context 物件
    
    Returns:
        Lambda 響應物件
    """
    try:
        logger.info(f"Processing event: {json.dumps(event, default=str)}")
        
        # TODO: 實現核心邏輯
        
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'success'})
        }
        
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

#### 如果是 ai-processor（處理器）

**文件路徑**: `ai-processor/[function_name].py`

**基礎模板**：
```python
"""
[功能描述]
"""
import logging
from typing import Any

from utils.logger import get_logger

# 設置日誌
logger = get_logger(__name__)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Lambda 入口函數
    
    Args:
        event: Lambda event 物件
        context: Lambda context 物件
    
    Returns:
        Lambda 響應物件
    """
    try:
        logger.info("Processing event", extra={'event': event})
        
        # TODO: 實現核心邏輯
        
        return {
            'statusCode': 200,
            'body': {'status': 'success'}
        }
        
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }
```

---

### 3. 創建測試文件 🧪

**文件路徑**: `[stack]/tests/test_[function_name].py`

**基礎測試模板**：
```python
"""
測試 [function_name] handler
"""
import json
import pytest
from [module_path] import lambda_handler


class Test[FunctionName]Handler:
    """[FunctionName] Handler 測試"""
    
    def test_successful_processing(self):
        """測試成功處理"""
        event = {
            # TODO: 添加測試 event
        }
        context = None
        
        result = lambda_handler(event, context)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['status'] == 'success'
    
    def test_error_handling(self):
        """測試錯誤處理"""
        event = {
            # TODO: 添加會導致錯誤的 event
        }
        context = None
        
        result = lambda_handler(event, context)
        
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
    
    def test_missing_required_fields(self):
        """測試缺少必要欄位"""
        event = {}
        context = None
        
        result = lambda_handler(event, context)
        
        # TODO: 根據實際需求調整
        assert result['statusCode'] in [400, 500]
```

---

### 4. 更新 template.yaml ⚙️

在相應的 template.yaml 中添加 Lambda 函數定義：

```yaml
  [FunctionName]Function:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: [code_path]/
      Handler: [handler_file].lambda_handler
      Runtime: python3.11
      Timeout: 30
      MemorySize: 256
      Environment:
        Variables:
          LOG_LEVEL: INFO
          # TODO: 添加其他環境變數
      Policies:
        - Statement:
            - Effect: Allow
              Action:
                # TODO: 添加必要的 IAM 權限
              Resource: '*'
      Events:
        # TODO: 添加觸發器（如 API Gateway、EventBridge 等）
```

**根據用戶回答調整**：
- 添加必要的環境變數
- 配置 IAM 策略
- 設置適當的 timeout 和 memory
- 添加觸發器配置

---

### 5. 驗證創建結果 ✅

#### 5.1 測試導入

```bash
cd [stack_directory]
python3.11 -c "import [handler_module]"
```

**預期結果**：
- 無 ImportError
- 無 SyntaxError

---

#### 5.2 運行測試

```bash
python3.11 -m pytest tests/test_[function_name].py -v
```

**預期結果**：
- 所有測試通過（即使是基礎測試）

---

#### 5.3 驗證 SAM Template

```bash
sam validate
```

**預期結果**：
- Template 格式正確
- 無語法錯誤

---

### 6. 提供總結和下一步 📊

```
✅ Lambda 函數創建完成！

📝 創建的文件：
- Handler: [path/to/handler.py]
- 測試: [path/to/test_handler.py]
- 配置: [path/to/template.yaml]（已更新）

🔍 驗證結果：
✅ 導入測試通過
✅ 基礎測試通過
✅ SAM template 驗證通過

📋 下一步建議：
1. 實現 handler 核心邏輯
2. 添加更多測試案例（邊界情況、錯誤處理）
3. 更新 template.yaml 的 TODO 項目
4. 本地測試：sam local invoke [FunctionName]Function
5. 執行完整測試：/test-full.md
6. 部署：/deploy-lambda.md

💡 開發提示：
- 使用 logger 而非 print()
- 確保錯誤處理完整
- 添加充分的測試覆蓋
- 遵循現有代碼風格
```

---

## 使用範例

### 範例 1: 創建消息處理器

**輸入**：
```
1. 名稱: message-processor
2. 用途: 處理 Telegram 消息
3. Stack: telegram-adapter
4. 環境變數: Y (TELEGRAM_BOT_TOKEN)
5. IAM 權限: Y (DynamoDB 讀取)
```

**結果**：
- 創建 `telegram-adapter/src/message_processor_handler.py`
- 創建 `telegram-adapter/tests/test_message_processor.py`
- 更新 `telegram-adapter/template.yaml`

---

### 範例 2: 創建工具函數

**輸入**：
```
1. 名稱: data-transformer
2. 用途: 轉換數據格式
3. Stack: ai-processor
4. 環境變數: N
5. IAM 權限: N
```

**結果**：
- 創建 `ai-processor/data_transformer.py`
- 創建 `ai-processor/tests/test_data_transformer.py`
- 更新 `ai-processor/template.yaml`

---

## 注意事項

### 命名規範
- 使用 kebab-case 作為函數名稱
- Python 文件使用 snake_case
- 類名使用 PascalCase

### 必須包含
- ✅ 完整的錯誤處理
- ✅ 日誌記錄
- ✅ 類型注解
- ✅ Docstrings
- ✅ 基礎測試

### 避免
- ❌ 硬編碼敏感信息
- ❌ 缺少錯誤處理
- ❌ 沒有日誌
- ❌ 沒有測試

---

## 相關資源

### 參考文檔
- `.clinerules/deployment/lambda-development-best-practices.md`
- `docs/deployment-guide.md`

### 現有範例
- `telegram-adapter/src/handler.py` - 主要 webhook handler
- `telegram-adapter/src/file_handler.py` - 文件處理 handler
- `ai-processor/processor_entry.py` - AI 處理器入口

---

**Workflow 版本**: v1.0  
**創建日期**: 2026-01-14  
**適用範圍**: 所有 Lambda 開發  
**預計執行時間**: 5-10 分鐘