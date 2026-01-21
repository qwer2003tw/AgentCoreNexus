# Lambda 開發與部署最佳實踐

**目的**: 避免導入錯誤和部署問題，確保代碼品質  
**基於經驗**: 2026-01-07 檔案讀取功能開發  
**重要性**: ⭐⭐⭐ 關鍵規範

---

## 🚨 核心原則

### 原則 1: 只使用 SAM 部署
```bash
# ✅ 正確：使用 SAM
sam build
sam deploy --stack-name STACK_NAME ...

# ❌ 錯誤：繞過 SAM
aws lambda update-function-code ...
aws lambda update-function-configuration ...
```

**為什麼**：
- SAM 管理完整的基礎設施狀態
- 確保配置一致性
- 支援回滾和版本控制
- 符合 Infrastructure as Code 原則

**例外情況**：
- 緊急修復時清除緩存（但之後必須 SAM 部署）
- 調試時的臨時測試（不應該成為常態）

### 原則 2: 部署前必須驗證導入
```bash
# ✅ 正確：部署前測試
python -c "import handler"
python -c "import file_handler"

# ❌ 錯誤：直接部署
sam deploy  # 沒有先測試導入
```

**為什麼**：
- 導入錯誤會導致 Lambda 完全無法啟動
- 在本地發現問題比在生產環境發現好 100 倍
- 節省時間和用戶體驗

### 原則 3: 先檢查現有 API，不要假設
```python
# ❌ 錯誤：假設函數存在
from secrets_manager import get_secret_value  # 沒檢查是否存在

# ✅ 正確：先檢查
# 1. read_file telegram-adapter/src/secrets_manager.py
# 2. 確認有 get_telegram_secrets()
# 3. 然後使用正確的函數
from secrets_manager import get_telegram_secrets
```

---

## 📋 部署前檢查清單（強制執行）

### 階段 1: 代碼驗證

#### 1. Python 語法檢查
```bash
# 檢查所有 Python 檔案
find . -name "*.py" -type f -exec python -m py_compile {} \;

# 或針對特定目錄
cd telegram-adapter/src
python -m py_compile *.py
```

**目的**: 發現語法錯誤（拼寫、縮排等）

#### 2. 導入測試（⭐ 最重要）
```bash
# 測試每個主要模組
cd telegram-adapter/src
python -c "import handler" || echo "❌ handler.py 導入失敗"
python -c "import file_handler" || echo "❌ file_handler.py 導入失敗"
python -c "import allowlist" || echo "❌ allowlist.py 導入失敗"

cd ../../ai-processor
python -c "import processor_entry" || echo "❌ processor_entry.py 導入失敗"
```

**目的**: 發現：
- 導入的模組不存在
- 導入的函數不存在
- 循環導入問題

#### 3. SAM Template 驗證
```bash
cd telegram-adapter
sam validate

cd ../ai-processor
sam validate
```

**目的**: 驗證 CloudFormation 配置正確

### 階段 2: 本地測試（可選但推薦）

#### 4. SAM Local Invoke
```bash
# 準備測試事件
cat > test_event.json << 'EOF'
{
  "body": "{\"message\":{\"from\":{\"id\":316743844},\"text\":\"test\"}}",
  "headers": {"X-Telegram-Bot-Api-Secret-Token": "test"}
}
EOF

# 本地測試
sam local invoke TelegramReceiverFunction --event test_event.json
```

**目的**: 在本地環境模擬執行

### 階段 3: 部署

#### 5. SAM Deploy
```bash
sam build
sam deploy --stack-name STACK_NAME \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --region us-west-2
```

### 階段 4: 部署後驗證（強制）

#### 6. 立即檢查日誌
```bash
# 部署完成後 30 秒內檢查
aws logs tail /aws/lambda/FUNCTION_NAME --region us-west-2 --since 1m

# 尋找：
# ✅ 無 ImportModuleError
# ✅ 無 Runtime.* Error
# ✅ 有正常的初始化日誌
```

**目的**: 立即發現部署問題

---

## 🔍 快速導入測試腳本

### 創建測試腳本

**telegram-adapter/test_imports.sh**:
```bash
#!/bin/bash
set -e

echo "📋 測試 Receiver Lambda 導入..."

cd src

echo "1. 測試 handler.py..."
python -c "import handler" && echo "  ✅ handler.py"

echo "2. 測試 file_handler.py..."
python -c "import file_handler" && echo "  ✅ file_handler.py"

echo "3. 測試 allowlist.py..."
python -c "import allowlist" && echo "  ✅ allowlist.py"

echo "4. 測試 secrets_manager.py..."
python -c "import secrets_manager" && echo "  ✅ secrets_manager.py"

cd ..
echo "✅ 所有導入測試通過"
```

**ai-processor/test_imports.sh**:
```bash
#!/bin/bash
set -e

echo "📋 測試 Processor Lambda 導入..."

echo "1. 測試 processor_entry.py..."
python -c "import processor_entry" && echo "  ✅ processor_entry.py"

echo "2. 測試 file_service.py..."
python -c "from services.file_service import file_service" && echo "  ✅ file_service.py"

echo "3. 測試 audit.py..."
python -c "from utils.audit import audit_log" && echo "  ✅ audit_log 存在"

echo "4. 測試所有工具..."
python -c "from tools import AVAILABLE_TOOLS" && echo "  ✅ 所有工具"

echo "✅ 所有導入測試通過"
```

**使用方式**：
```bash
# 每次部署前執行
chmod +x test_imports.sh
./test_imports.sh || exit 1  # 失敗則停止
```

---

## 📖 這次問題的具體案例

### 案例 1: Receiver Lambda 導入錯誤

**錯誤代碼**：
```python
# file_handler.py
from secrets_manager import get_secret_value  # ❌

def get_bot_token():
    secret = get_secret_value()  # ❌
```

**為什麼發生**：
- 沒有先檢查 `secrets_manager.py` 的實際 API
- 假設有 `get_secret_value()` 函數
- 沒有導入測試

**如何避免**：
```bash
# 1. 先檢查模組
cat telegram-adapter/src/secrets_manager.py | grep "^def"

# 2. 看到只有：
# def get_telegram_secrets()
# def get_telegram_bot_token()
# def get_telegram_secret_token()

# 3. 使用正確的函數
from secrets_manager import get_telegram_secrets  # ✅
```

**修復**：
```python
# 正確的代碼
from secrets_manager import get_telegram_secrets  # ✅

def get_bot_token():
    secrets = get_telegram_secrets()  # ✅
    if secrets:
        return secrets.get('bot_token', '')
    return ''
```

### 案例 2: Processor Lambda 導入錯誤

**錯誤代碼**：
```python
# file_service.py
from utils.audit import audit_log  # ❌ 函數不存在

audit_log(user_id, action, resource, details)  # ❌
```

**為什麼發生**：
- 假設 `utils/audit.py` 有 `audit_log()` 函數
- 實際上只有 `MemoryAuditLogger` 類
- 沒有導入測試

**如何避免**：
```bash
# 1. 先檢查模組
cat ai-processor/utils/audit.py | grep "^def\|^class"

# 2. 看到只有：
# class MemoryAuditLogger:

# 3. 要嘛使用類方法，要嘛添加函數
```

**修復**：
```python
# 添加獨立函數
def audit_log(user_id, action, resource, details=None):
    """通用審計日誌函數"""
    # 實作...
```

---

## ⚠️ 常見錯誤模式

### 錯誤模式 1: 假設函數名稱

```python
# ❌ 憑印象寫
from module import function_name  # 沒檢查是否存在

# ✅ 先驗證
# 1. 檢查模組內容
# 2. 確認函數確實存在
# 3. 然後導入
```

### 錯誤模式 2: 跳過本地測試

```bash
# ❌ 沒有測試就部署
sam build
sam deploy  # 直接部署

# ✅ 測試後再部署
sam build
./test_imports.sh  # 先測試
sam deploy  # 測試通過才部署
```

### 錯誤模式 3: 部署後不檢查日誌

```bash
# ❌ 部署完就以為成功
sam deploy
# 沒有檢查日誌，等用戶回報才發現問題

# ✅ 部署後立即驗證
sam deploy
aws logs tail /aws/lambda/FUNCTION --region us-west-2 --since 1m
# 立即發現並修復問題
```

---

## 🔧 Lambda 緩存問題處理

### 問題：更新後仍使用舊代碼

**症狀**：
- 部署顯示成功
- 但 Lambda 仍執行舊代碼
- 日誌顯示舊的錯誤

**原因**：
- Lambda 緩存了執行環境
- 需要觸發更新

**正確的解決方式**：
```bash
# 選項 1: 清除 SAM 緩存重新部署（推薦）
rm -rf .aws-sam
sam build --use-container  # 強制重新 build
sam deploy ...

# 選項 2: 等待 Lambda 自動更新
# Lambda 會在幾分鐘內自動使用新代碼

# 選項 3: 觸發新請求
# 發送測試訊息，強制 Lambda 重新初始化
```

**不推薦但可接受**（緊急情況）：
```bash
# 僅用於緊急修復，之後必須再次 SAM 部署確認
aws lambda update-function-code \
  --function-name FUNCTION_NAME \
  --s3-bucket BUCKET \
  --s3-key KEY \
  --publish

aws lambda wait function-updated \
  --function-name FUNCTION_NAME
```

---

## 📚 檢查清單模板

### 開發新功能前

- [ ] 閱讀相關模組的現有代碼
- [ ] 確認要使用的函數確實存在
- [ ] 了解函數的參數和返回值

### 寫完代碼後

- [ ] Python 語法檢查（`py_compile`）
- [ ] 導入測試（`python -c "import ..."`）
- [ ] SAM validate
- [ ] （可選）SAM local invoke

### 部署時

- [ ] 使用 SAM deploy（不用 aws lambda update-*）
- [ ] 記錄部署時間
- [ ] 等待 CloudFormation 完成

### 部署後（強制）

- [ ] 立即檢查 CloudWatch Logs（1 分鐘內）
- [ ] 尋找 ImportModuleError
- [ ] 尋找 Runtime.* Error
- [ ] 驗證 Lambda 狀態：Active
- [ ] 驗證 LastUpdateStatus: Successful

### 發現問題時

- [ ] 不要 panic，記錄錯誤
- [ ] 在本地修復
- [ ] 重新測試導入
- [ ] 再次 SAM 部署
- [ ] 驗證修復成功

---

## 🎓 從這次錯誤學到的

### 錯誤 1: `get_secret_value` 不存在

**問題**：
```python
from secrets_manager import get_secret_value  # ❌
```

**根因**：
- 沒有先檢查 `secrets_manager.py`
- 假設函數名稱

**預防**：
```bash
# 應該先做
cat secrets_manager.py | grep "^def"
# 看到實際的函數列表，然後使用正確的
```

**教訓**：
- ✅ 永遠先檢查現有 API
- ✅ 使用 `read_file` 或 `grep` 確認
- ❌ 不要憑記憶或假設

### 錯誤 2: `audit_log` 函數缺失

**問題**：
```python
from utils.audit import audit_log  # ❌ 函數不存在
```

**根因**：
- 假設 `utils/audit.py` 有這個函數
- 實際只有 `MemoryAuditLogger` 類

**預防**：
```bash
# 應該先做
cat utils/audit.py | grep "^def\|^class"
# 看到只有 class，沒有獨立函數
# 要嘛用類方法，要嘛添加新函數
```

**教訓**：
- ✅ 設計 API 時要考慮使用方便性
- ✅ 可以同時提供類方法和獨立函數
- ✅ 添加新函數比修改調用代碼容易

---

## 🛠️ 實用工具腳本

### 1. 快速導入測試（放在項目根目錄）

**quick-import-test.sh**:
```bash
#!/bin/bash
# 快速測試所有 Lambda 的導入

echo "🔍 測試 Receiver Lambda..."
cd telegram-adapter/src
python -c "import handler && import file_handler && import allowlist" \
  && echo "✅ Receiver imports OK" \
  || (echo "❌ Receiver imports FAILED" && exit 1)
cd ../..

echo "🔍 測試 Processor Lambda..."
cd ai-processor
python -c "import processor_entry" \
  && echo "✅ Processor imports OK" \
  || (echo "❌ Processor imports FAILED" && exit 1)
cd ..

echo "🎉 所有導入測試通過"
```

**使用**：
```bash
chmod +x quick-import-test.sh
./quick-import-test.sh || exit 1
sam deploy ...
```

### 2. 部署後自動驗證

**post-deploy-verify.sh**:
```bash
#!/bin/bash
# 部署後自動驗證

FUNCTION_NAME=$1
REGION="us-west-2"

echo "📊 驗證 Lambda: $FUNCTION_NAME"

# 1. 等待更新完成
echo "等待 Lambda 更新..."
aws lambda wait function-updated \
  --region $REGION \
  --function-name $FUNCTION_NAME

# 2. 檢查狀態
STATUS=$(aws lambda get-function \
  --region $REGION \
  --function-name $FUNCTION_NAME \
  --query 'Configuration.{State:State,LastUpdateStatus:LastUpdateStatus}')

echo "Lambda 狀態: $STATUS"

# 3. 檢查日誌（尋找錯誤）
echo "檢查日誌..."
ERRORS=$(aws logs filter-log-events \
  --region $REGION \
  --log-group-name /aws/lambda/$FUNCTION_NAME \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '2 minutes ago' +%s)000 \
  --max-items 5)

if [ ! -z "$ERRORS" ]; then
    echo "❌ 發現錯誤："
    echo "$ERRORS"
    exit 1
fi

echo "✅ 驗證通過"
```

**使用**：
```bash
sam deploy ...
./post-deploy-verify.sh telegram-adapter-receiver
```

---

## 📊 時間成本分析

### 沒有測試（這次實際發生）

| 階段 | 時間 | 累計 |
|------|------|------|
| 開發代碼 | 30 分鐘 | 30 分鐘 |
| SAM deploy | 5 分鐘 | 35 分鐘 |
| **用戶發現問題** | 5 分鐘 | 40 分鐘 |
| 診斷日誌 | 5 分鐘 | 45 分鐘 |
| 修復代碼 | 5 分鐘 | 50 分鐘 |
| 重新部署 | 5 分鐘 | 55 分鐘 |
| 再次驗證 | 3 分鐘 | 58 分鐘 |

**總計**: 58 分鐘 + 用戶受影響 ❌

### 有測試（應該這樣）

| 階段 | 時間 | 累計 |
|------|------|------|
| 開發代碼 | 30 分鐘 | 30 分鐘 |
| **導入測試** | 1 分鐘 | 31 分鐘 |
| **發現問題** | 0 秒 | 31 分鐘 |
| 修復代碼 | 5 分鐘 | 36 分鐘 |
| **再次測試** | 1 分鐘 | 37 分鐘 |
| SAM deploy | 5 分鐘 | 42 分鐘 |
| 驗證 | 2 分鐘 | 44 分鐘 |

**總計**: 44 分鐘，節省 14 分鐘 ✅  
**用戶體驗**: 不受影響 ✅

---

## 🎯 未來改進建議

### 1. 自動化測試整合

**創建 Makefile**:
```makefile
.PHONY: test deploy

test:
	@echo "Running pre-deploy tests..."
	./test_imports.sh
	sam validate

deploy: test
	@echo "Tests passed, deploying..."
	sam build
	sam deploy --stack-name $(STACK_NAME) ...

quick-deploy:
	@echo "⚠️  Skipping tests (not recommended)"
	sam build
	sam deploy ...
```

**使用**：
```bash
# 推薦：帶測試的部署
make deploy STACK_NAME=telegram-adapter-receiver

# 不推薦：跳過測試（緊急時）
make quick-deploy STACK_NAME=telegram-adapter-receiver
```

### 2. Pre-commit Hook

**創建 .git/hooks/pre-commit**:
```bash
#!/bin/bash
# 在 commit 前自動測試導入

echo "🔍 Pre-commit: 測試 Python 導入..."

# 測試 Receiver
cd telegram-adapter/src
python -c "import handler && import file_handler" || {
    echo "❌ Receiver 導入失敗，commit 被阻止"
    exit 1
}
cd ../..

# 測試 Processor
cd ai-processor
python -c "import processor_entry" || {
    echo "❌ Processor 導入失敗，commit 被阻止"
    exit 1
}
cd ..

echo "✅ 導入測試通過，允許 commit"
```

### 3. CI/CD 整合（未來）

**GitHub Actions workflow**:
```yaml
name: Test and Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Test imports
        run: ./test_imports.sh
      - name: SAM validate
        run: sam validate

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: SAM deploy
        run: sam deploy ...
```

---

## 🚀 正確的部署工作流

### 標準流程（必須遵循）

```bash
# 1. 開發完成
# ... 寫代碼 ...

# 2. 本地驗證
./test_imports.sh  # ⭐ 關鍵！

# 3. SAM 驗證
sam validate

# 4. 部署
sam build
sam deploy --stack-name STACK_NAME ...

# 5. 立即驗證
aws logs tail /aws/lambda/FUNCTION --region us-west-2 --since 1m

# 6. 功能測試
# 透過 Telegram 或 API 測試

# 7. 監控
# 持續觀察 CloudWatch Logs
```

### 緊急修復流程

```bash
# 1. 快速修復代碼
# ... 修改文件 ...

# 2. 本地驗證
python -c "import fixed_module"

# 3. SAM 快速部署
sam build
sam deploy --stack-name STACK_NAME --no-confirm-changeset

# 4. 強制清除緩存（可選）
aws lambda update-function-code ... --publish

# 5. 驗證修復
aws logs tail /aws/lambda/FUNCTION --since 30s

# 6. 事後檢討
# 記錄為什麼發生，如何避免
```

---

## 📖 參考資料

### 相關文檔
- [AWS Lambda 最佳實踐](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [SAM CLI 命令參考](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-command-reference.html)
- [CloudFormation 故障排除](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/troubleshooting.html)

### 項目內文檔
- `.clinerules/deployment/aws-lambda-telegram-bot-deployment-issues.md` - 部署問題清單
- `dev-reports/2026-01-file-reader/REPORT.md` - 檔案讀取功能報告（包含這次的錯誤）

---

## ✅ 記住這些

1. **先檢查，再使用** - 不要假設函數存在
2. **測試後，再部署** - 導入測試只需 1 分鐘
3. **SAM 是唯一** - 不繞過部署流程
4. **部署後，立即驗證** - 不要等用戶回報
5. **記錄經驗** - 犯過的錯不要再犯

---

**規範版本**: 1.0  
**創建日期**: 2026-01-07  
**基於案例**: 檔案讀取功能開發的教訓  
**強制執行**: 所有 Lambda 開發都必須遵循
