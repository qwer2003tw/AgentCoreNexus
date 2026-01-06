# AWS Lambda Telegram Bot 部署問題清單

本文檔記錄在部署 Telegram Bot 時遇到的常見問題及解決方案。

## 🗑️ CloudFormation Stack 刪除問題

### 問題 1: EventBridge Rules 阻塞 EventBus 刪除

**錯誤訊息**：
```
EventBus can't be deleted since it has rules.
```

**根本原因**：
- EventBus 上有未刪除的 rules
- CloudFormation 無法自動清理這些 rules

**解決方案**：
```bash
# 1. 列出 EventBus 上的所有 rules
aws events list-rules --region REGION --event-bus-name EVENT_BUS_NAME

# 2. 移除 rule 的 targets
aws events remove-targets --region REGION --rule RULE_NAME --event-bus-name EVENT_BUS_NAME --ids TARGET_ID

# 3. 刪除 rule
aws events delete-rule --region REGION --name RULE_NAME --event-bus-name EVENT_BUS_NAME

# 4. 重新嘗試刪除 stack
aws cloudformation delete-stack --region REGION --stack-name STACK_NAME
```

**預防措施**：
- 在 template 中避免創建 EventBridge rules 時硬編碼 targets
- 考慮使用 DependsOn 確保正確的刪除順序

---

## 🔐 IAM 策略配置問題

### 問題 2: IAM 角色 ARN 格式錯誤

**錯誤訊息**：
```
Resource must be in ARN format or "*"
CREATE_FAILED: AWS::IAM::Role
```

**根本原因**：
- Template 參數默認值為空字符串 `''`
- 在 IAM 策略中使用 `!Ref EmptyParameter` 導致空 ARN

**錯誤示例**：
```yaml
Parameters:
  EventBusArn:
    Type: String
    Default: ''  # ❌ 空字符串

Resources:
  MyRole:
    Type: AWS::IAM::Role
    Properties:
      Policies:
        - Statement:
            - Effect: Allow
              Action: events:PutEvents
              Resource: !Ref EventBusArn  # ❌ 空 ARN
```

**解決方案**：
```yaml
# 選項 1: 使用萬用字元
Policies:
  - Statement:
      - Effect: Allow
        Action: events:PutEvents
        Resource: '*'  # ✅

# 選項 2: 使用條件判斷
Policies:
  - Statement:
      - Effect: Allow
        Action: events:PutEvents
        Resource: !If 
          - HasEventBusArn
          - !Ref EventBusArn
          - '*'
```

**預防措施**：
- 避免在必須的資源參數中使用空字符串默認值
- 使用 '*' 或條件邏輯處理可選資源

---

## 🔗 Lambda 函數引用問題

### 問題 3: 硬編碼 ARN 無法通過 ResourceExistenceCheck

**錯誤訊息**：
```
AWS::EarlyValidation::ResourceExistenceCheck failed
```

**根本原因**：
- 在 template 中硬編碼 Lambda ARN
- AWS 驗證資源是否存在時失敗

**錯誤示例**：
```yaml
Resources:
  MyRule:
    Type: AWS::Events::Rule
    Properties:
      Targets:
        - Arn: arn:aws:lambda:us-west-2:123456789:function:my-function  # ❌ 硬編碼
          Id: MyTarget
```

**解決方案**：
```yaml
# 使用 ImportValue 引用已導出的 ARN
Resources:
  MyRule:
    Type: AWS::Events::Rule
    Properties:
      Targets:
        - Arn: !ImportValue other-stack-FunctionArn  # ✅
          Id: MyTarget

# 同時需要添加 Permission
  MyPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !ImportValue other-stack-FunctionName
      Action: lambda:InvokeFunction
      Principal: events.amazonaws.com
      SourceArn: !GetAtt MyRule.Arn
```

**預防措施**：
- 使用 ImportValue 引用跨 stack 資源
- 確保 Outputs 中正確導出 ARN
- 添加對應的 Lambda Permission

---

## 💾 DynamoDB Table 問題

### 問題 4: Retain 策略導致資源衝突

**錯誤訊息**：
```
Resource already exists
```

**根本原因**：
- 舊 stack 使用 `DeletionPolicy: Retain`
- Table 在 stack 刪除後仍存在
- 新 stack 無法創建同名 table

**解決方案**：
```yaml
# 從 template 中移除 table 創建，直接使用現有的
Resources:
  # AllowlistTable 已存在，不需要創建
  # 直接使用 table 名稱

  MyFunction:
    Type: AWS::Serverless::Function
    Properties:
      Environment:
        Variables:
          TABLE_NAME: existing-table-name  # ✅ 使用固定名稱
      Policies:
        - DynamoDBReadPolicy:
            TableName: existing-table-name  # ✅
```

**Outputs 修改**：
```yaml
Outputs:
  TableName:
    Description: DynamoDB Table Name (existing table)
    Value: existing-table-name  # ✅ 固定值
```

**預防措施**：
- 謹慎使用 Retain 策略
- 記錄哪些資源使用了 Retain
- 考慮使用不同的 table 名稱或條件創建

---

## 🔄 SAM 部署問題

### 問題 5: SAM 使用舊的緩存模板

**症狀**：
- 修改了 template.yaml
- 部署時仍使用舊配置
- "File with same data already exists, skipping upload"

**解決方案**：
```bash
# 清除 SAM 構建緩存
cd project-directory
rm -rf .aws-sam
sam build
sam deploy
```

**預防措施**：
- 重大更改後清除緩存
- 使用 `sam build --use-container` 確保環境一致

---

## 🔑 Secrets Manager 問題

### 問題 6: Lambda Secret 緩存

**症狀**：
- 更新了 Secrets Manager 中的值
- Lambda 仍讀取到舊的（空的）值

**根本原因**：
- Lambda 緩存了環境變數和 secret 值
- 需要觸發更新才能清除緩存

**解決方案**：
```bash
# 方法 1: 強制更新 Lambda 代碼
aws lambda update-function-code \
  --region REGION \
  --function-name FUNCTION_NAME \
  --s3-bucket BUCKET \
  --s3-key KEY \
  --publish

# 方法 2: 更新環境變數
aws lambda update-function-configuration \
  --region REGION \
  --function-name FUNCTION_NAME \
  --environment "Variables={KEY1=value1,KEY2=value2}"

# 方法 3: 重新部署整個 stack
sam deploy --no-confirm-changeset
```

**預防措施**：
- 更新 secrets 後立即重啟或重新部署 Lambda
- 在代碼中不要過度緩存 secrets

---

## 🔌 EventBridge 配置問題

### 問題 7: EVENT_BUS_NAME 未配置

**症狀**：
- 處理器處理消息成功
- 但回應無法返回給用戶
- 日誌：`EVENT_BUS_NAME not configured, skipping completion event`

**根本原因**：
- Lambda 環境變數中缺少 EVENT_BUS_NAME
- 無法發送 `message.completed` event
- 響應路由器收不到消息

**解決方案**：
```yaml
# Template 中添加環境變數
Resources:
  ProcessorFunction:
    Type: AWS::Serverless::Function
    Properties:
      Environment:
        Variables:
          EVENT_BUS_NAME: !Ref EventBusName  # ✅ 或使用 ImportValue
```

**驗證**：
```bash
# 檢查環境變數
aws lambda get-function-configuration \
  --region REGION \
  --function-name FUNCTION_NAME \
  --query 'Environment.Variables.EVENT_BUS_NAME'
```

**預防措施**：
- 在 template 中明確列出所有必要的環境變數
- 在代碼中檢查關鍵環境變數是否存在

---

## 💬 Telegram 消息格式問題

### 問題 8: Markdown 轉義但未設置 parse_mode

**症狀**：
- /info 輸出有大量跳脫字元（如 `\-`, `\:`, `\.`）

**根本原因**：
- 代碼使用 `escape_markdown_v2()` 轉義特殊字符
- 但發送時沒有設置 `parse_mode='MarkdownV2'`
- Telegram 將轉義字元視為普通文字

**錯誤示例**：
```python
# 錯誤：轉義但不使用 Markdown
text = escape_markdown_v2("Stack: my-stack")  # "Stack\\: my\\-stack"
send_message(chat_id, text)  # ❌ 顯示轉義字元
```

**解決方案**：
```python
# 選項 1: 移除不必要的轉義（推薦簡單信息）
text = "Stack: my-stack"
send_message(chat_id, text)  # ✅

# 選項 2: 使用正確的 parse_mode
text = escape_markdown_v2("*Stack*: my-stack")
send_message(chat_id, text, parse_mode='MarkdownV2')  # ✅
```

**預防措施**：
- 如果不需要 Markdown 格式，不要轉義
- 如果轉義了，必須設置對應的 parse_mode

---

## 🌐 瀏覽器功能實現問題

### 問題 9: 錯誤的瀏覽器 API 導入路徑

**錯誤訊息**：
```
No module named 'bedrock_agentcore.tools.browser'
'NoneType' object has no attribute 'browser'
```

**根本原因**：
- 使用了不存在的導入路徑
- browser_tool 沒有正確初始化

**錯誤示例**：
```python
# ❌ 錯誤的導入
from bedrock_agentcore.tools.browser import BrowserTool

# ❌ 未初始化就使用
self.browser_tool = None
result = self.browser_tool.browser({...})  # NoneType error
```

**正確實現**：
```python
# ✅ 正確的導入
from bedrock_agentcore.tools.browser_client import browser_session, BrowserClient

# ✅ 正確的使用
with browser_session(region='us-west-2') as client:
    ws_url, headers = client.generate_ws_headers()
    # 使用 WebSocket 執行瀏覽器操作
```

**關鍵理解**：
- Bedrock AgentCore 使用 AWS Browser sandbox 服務
- 不需要本地 Playwright
- 通過 WebSocket 連接執行操作

**預防措施**：
- 參考官方 bedrock-agentcore 文檔
- 使用 browser_session 上下文管理器
- 測試導入是否成功

---

## 🔐 IAM 權限問題

### 問題 10: Browser Sandbox 權限缺失

**錯誤訊息**：
```
AccessDeniedException: not authorized to perform: bedrock-agentcore:StartBrowserSession
```

**根本原因**：
- Lambda 執行角色缺少 Browser sandbox 操作權限

**必要權限**：
```yaml
Policies:
  - Statement:
      - Effect: Allow
        Action:
          - bedrock-agentcore:StartBrowserSession
          - bedrock-agentcore:StopBrowserSession
          - bedrock-agentcore:GetBrowserSession
          - bedrock-agentcore-control:*
        Resource: '*'
```

**完整的 AgentCore Lambda 權限模板**：
```yaml
Policies:
  - Statement:
      # EventBridge
      - Effect: Allow
        Action:
          - events:PutEvents
        Resource: '*'
      
      # Bedrock AI
      - Effect: Allow
        Action:
          - bedrock:InvokeModel
          - bedrock:InvokeModelWithResponseStream
          - bedrock:InvokeAgent
          - bedrock:Retrieve
        Resource: '*'
      
      # Browser Sandbox
      - Effect: Allow
        Action:
          - bedrock-agentcore:StartBrowserSession
          - bedrock-agentcore:StopBrowserSession
          - bedrock-agentcore:GetBrowserSession
          - bedrock-agentcore-control:*
        Resource: '*'
```

**測試權限**：
```bash
# 測試瀏覽器權限
aws bedrock-agentcore start-browser-session \
  --region us-west-2 \
  --identifier aws.browser.v1
```

**預防措施**：
- 在使用 bedrock-agentcore 瀏覽器時，立即添加所需權限
- 參考完整權限模板

---

## 🔄 Lambda 更新最佳實踐

### 問題 11: 配置更新後功能仍不正常

**常見原因**：
1. Lambda 緩存未清除
2. 環境變數更新未生效
3. 代碼部署不完整

**解決流程**：
```bash
# 1. 更新環境變數
aws lambda update-function-configuration ...

# 2. 等待更新完成
aws lambda wait function-updated \
  --region REGION \
  --function-name FUNCTION_NAME

# 3. 檢查狀態
aws lambda get-function \
  --region REGION \
  --function-name FUNCTION_NAME \
  --query 'Configuration.{State:State,LastUpdateStatus:LastUpdateStatus}'

# 應該看到：State: Active, LastUpdateStatus: Successful

# 4. 觸發新的請求測試
```

**預防措施**：
- 更新後等待 Lambda 狀態變為 Active
- 檢查 LastUpdateStatus 為 Successful
- 測試前清除舊的執行上下文

---

## 🧪 測試與驗證

### 問題 12: Allowlist Username 驗證

**症狀**：
- API Gateway 返回 `{"status": "ignored"}`
- 日誌顯示 "Username mismatch"

**根本原因**：
- DynamoDB 中存儲的 username 與請求中的不匹配
- Allowlist 進行嚴格的 username 驗證

**解決方案**：
```bash
# 檢查 allowlist 中的 username
aws dynamodb get-item \
  --region REGION \
  --table-name telegram-allowlist \
  --key '{"chat_id":{"N":"CHAT_ID"}}' \
  --query 'Item.username.S'

# 使用正確的 username 測試
curl -X POST API_GATEWAY_URL \
  -H "X-Telegram-Bot-Api-Secret-Token: SECRET" \
  -d '{"message": {"from": {"id": CHAT_ID, "username": "correct_username"}, ...}}'
```

**預防措施**：
- 測試前確認 allowlist 中的數據
- 使用真實的 Telegram update 格式測試

---

## 📋 部署檢查清單

### 部署前檢查
- [ ] 所有參數默認值不為空字符串（或使用萬用字元）
- [ ] IAM 策略包含所有必要權限
- [ ] 跨 stack 引用使用 ImportValue
- [ ] EventBridge rules 有對應的 Lambda Permission
- [ ] 環境變數完整配置

### 部署後驗證
- [ ] 所有 stacks 狀態為 CREATE_COMPLETE 或 UPDATE_COMPLETE
- [ ] 所有 Lambda 函數狀態為 Active
- [ ] Lambda LastUpdateStatus 為 Successful
- [ ] Secrets Manager 中的值正確
- [ ] EventBridge rules 和 targets 正確配置

### 功能測試
- [ ] 使用正確的 webhook secret 測試 API Gateway
- [ ] 使用正確的 username 和 chat_id 測試
- [ ] 檢查所有 Lambda 日誌無錯誤
- [ ] 驗證消息完整流程（接收 → 處理 → 回應）
- [ ] 測試特殊功能（如瀏覽器）

---

## 🚀 快速故障排除指南

### Lambda 沒有回應
1. 檢查 EventBridge rule 是否有 targets
2. 檢查 Lambda Permission 是否存在
3. 檢查 Lambda 日誌是否有錯誤
4. 驗證 EVENT_BUS_NAME 是否配置

### 權限錯誤（AccessDeniedException）
1. 檢查 IAM 角色策略
2. 添加缺少的權限
3. 重新部署 stack 或更新 function configuration
4. 等待狀態變為 Active 後測試

### Stack 刪除失敗
1. 檢查 EventBridge rules（list-rules）
2. 手動刪除 rule targets（remove-targets）
3. 手動刪除 rules（delete-rule）
4. 檢查 Retain 資源（如 DynamoDB tables）
5. 重新嘗試刪除 stack

### 瀏覽器功能失敗
1. 檢查 BROWSER_ENABLED 環境變數
2. 驗證 browser_client 導入正確
3. 確認 IAM 權限包含 bedrock-agentcore 操作
4. 檢查 Browser sandbox 服務在該 region 是否可用

---

## 📝 最佳實踐總結

### Template 設計
1. ✅ 避免空字符串默認值用於 ARN
2. ✅ 使用 ImportValue 引用跨 stack 資源
3. ✅ 明確定義所有 Lambda Permissions
4. ✅ 使用描述性的 Output 名稱

### 權限管理
1. ✅ 使用完整的權限模板
2. ✅ 測試前驗證所有必要權限
3. ✅ 記錄自定義服務的權限需求

### 部署流程
1. ✅ 重大更改前清除緩存
2. ✅ 更新配置後等待 Lambda Active
3. ✅ 逐步測試每個組件
4. ✅ 保留完整的部署日誌

### 測試策略
1. ✅ 使用 API Gateway 直接測試
2. ✅ 檢查每個 Lambda 的日誌
3. ✅ 驗證完整的消息流程
4. ✅ 使用真實的數據格式

---

**文檔版本**: 1.0  
**最後更新**: 2026-01-06  
**基於項目**: AgentCoreNexus Telegram Bot  
**經驗來源**: 57分鐘的完整部署與troubleshooting
