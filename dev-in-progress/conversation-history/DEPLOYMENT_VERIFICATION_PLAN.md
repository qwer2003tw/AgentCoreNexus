# 部署驗證計劃

**前提**: ✅ 單元測試全部通過（9/9）

---

## Phase 1: 部署基礎設施（30-40 分鐘）

### Step 1.1: 部署 DynamoDB Tables（5-10 分鐘）

```bash
cd infrastructure
sam validate -t conversation-storage.yaml
./deploy-conversation-storage.sh
```

**驗證檢查點**：
```bash
# 檢查 Stack 狀態
aws cloudformation describe-stacks \
  --stack-name agentcore-conversation-storage \
  --region us-west-2 \
  --query 'Stacks[0].StackStatus'
# 預期：CREATE_COMPLETE

# 列出創建的表
aws dynamodb list-tables --region us-west-2 | grep conversation
# 預期看到：
# - agentcore-conversation-history-prod
# - agentcore-conversation-metadata-prod
# - agentcore-identity-map-prod
```

---

### Step 1.2: 建立並發布 Lambda Layer（10-15 分鐘）

```bash
cd infrastructure/layers

# 建立 Layer
./build-layer.sh

# 打包
cd conversation-layer
zip -r ../conversation-layer.zip python/

# 發布
cd ..
aws lambda publish-layer-version \
  --layer-name agentcore-conversation-service \
  --description "Shared conversation storage service" \
  --zip-file fileb://conversation-layer.zip \
  --compatible-runtimes python3.11 \
  --region us-west-2

# 記錄 Layer ARN
LAYER_ARN=$(aws lambda list-layer-versions \
  --layer-name agentcore-conversation-service \
  --region us-west-2 \
  --query 'LayerVersions[0].LayerVersionArn' \
  --output text)

echo "Layer ARN: $LAYER_ARN"
```

**驗證檢查點**：
```bash
# 確認 Layer 存在
aws lambda list-layer-versions \
  --layer-name agentcore-conversation-service \
  --region us-west-2
# 預期：有版本列表
```

---

### Step 1.3: 更新 Lambda Functions（15-20 分鐘）

```bash
# 添加 Layer 到 Telegram Adapter
aws lambda update-function-configuration \
  --function-name agentcore-telegram-adapter-receiver \
  --layers "$LAYER_ARN" \
  --region us-west-2

# 等待更新完成
aws lambda wait function-updated \
  --function-name agentcore-telegram-adapter-receiver \
  --region us-west-2

# 添加 Layer 到 AI Processor
aws lambda update-function-configuration \
  --function-name agentcore-ai-processor-main \
  --layers "$LAYER_ARN" \
  --region us-west-2

aws lambda wait function-updated \
  --function-name agentcore-ai-processor-main \
  --region us-west-2

# 重新部署（包含代碼更新）
cd telegram-adapter
sam build
sam deploy --no-confirm-changeset

cd ../ai-processor
sam build
sam deploy --no-confirm-changeset
```

**驗證檢查點**：
```bash
# 檢查 Lambda 狀態
aws lambda get-function \
  --function-name agentcore-telegram-adapter-receiver \
  --region us-west-2 \
  --query 'Configuration.{State:State,LastUpdateStatus:LastUpdateStatus}'
# 預期：State=Active, LastUpdateStatus=Successful

# 檢查環境變數
aws lambda get-function-configuration \
  --function-name agentcore-telegram-adapter-receiver \
  --region us-west-2 \
  --query 'Environment.Variables' | grep CONVERSATION
# 預期看到 CONVERSATION_HISTORY_TABLE 和 CONVERSATION_METADATA_TABLE

# 檢查 Layer
aws lambda get-function-configuration \
  --function-name agentcore-telegram-adapter-receiver \
  --query 'Layers'
# 預期看到 agentcore-conversation-service Layer
```

---

## Phase 2: 功能驗證（15-20 分鐘）

### Step 2.1: 檢查日誌（初始化）

```bash
# Telegram receiver 日誌
aws logs tail /aws/lambda/agentcore-telegram-adapter-receiver \
  --region us-west-2 --since 2m

# 尋找：
# ✅ "ConversationService initialized"
# ✅ history_table: agentcore-conversation-history-prod
# ✅ metadata_table: agentcore-conversation-metadata-prod
# ❌ 無 ImportError 或其他錯誤
```

---

### Step 2.2: 私人對話測試

**操作**: 發送訊息到 Telegram bot
```
你好，測試對話記錄功能
```

**驗證**: 
```bash
# 1. 檢查 DynamoDB
aws dynamodb query \
  --table-name agentcore-conversation-history-prod \
  --key-condition-expression "conversation_id = :id" \
  --expression-attribute-values '{":id":{"S":"tg:YOUR_CHAT_ID"}}' \
  --region us-west-2

# 預期看到：
# - 用戶訊息（sender_id: tg:YOUR_ID, content: "你好..."）
# - AI 回應（sender_id: ai, content: "..."）

# 2. 檢查 metadata
aws dynamodb get-item \
  --table-name agentcore-conversation-metadata-prod \
  --key '{"conversation_id":{"S":"tg:YOUR_CHAT_ID"}}' \
  --region us-west-2

# 預期看到：
# - message_count: 2（用戶+AI）
# - is_group: false
# - participant_ids: ["tg:YOUR_ID", "ai"]
```

**檢查清單**：
- [ ] 用戶訊息成功儲存
- [ ] sender_id 格式正確（tg:數字）
- [ ] AI 回應成功儲存
- [ ] sender_id 為 "ai"
- [ ] metadata 自動更新
- [ ] message_count 正確

---

### Step 2.3: 群組對話測試（如果有測試群組）

**操作**: 在群組中發送訊息
```
測試群組對話記錄
```

**驗證**:
```bash
# 查詢群組對話
aws dynamodb query \
  --table-name agentcore-conversation-history-prod \
  --key-condition-expression "conversation_id = :id" \
  --expression-attribute-values '{":id":{"S":"tg:group:GROUP_ID"}}' \
  --region us-west-2

# 預期看到：
# - 所有成員的訊息都被記錄
# - 每條訊息有正確的 sender_id 和 sender_name
# - AI 回應也被記錄
```

**檢查清單**：
- [ ] 群組訊息成功儲存
- [ ] conversation_id 格式正確（tg:group:負數）
- [ ] sender_name 正確記錄
- [ ] AI 看到完整群組上下文
- [ ] AI 回應成功儲存

---

### Step 2.4: 日誌驗證（無錯誤）

```bash
# 檢查 Telegram receiver 錯誤
aws logs filter-log-events \
  --log-group-name /aws/lambda/agentcore-telegram-adapter-receiver \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '10 minutes ago' +%s)000 \
  --region us-west-2

# 預期：無結果或只有無關錯誤

# 檢查 AI processor 錯誤
aws logs filter-log-events \
  --log-group-name /aws/lambda/agentcore-ai-processor-main \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '10 minutes ago' +%s)000 \
  --region us-west-2

# 預期：無結果或只有無關錯誤

# 檢查對話記錄相關日誌
aws logs filter-log-events \
  --log-group-name /aws/lambda/agentcore-telegram-adapter-receiver \
  --filter-pattern "conversation history" \
  --start-time $(date -u -d '10 minutes ago' +%s)000 \
  --region us-west-2

# 預期看到：
# ✅ "Message saved to conversation history"
# ✅ conversation_id 正確
```

---

## Phase 3: 完整驗證檢查清單

### 基礎設施
- [ ] DynamoDB tables 創建成功（3個表）
- [ ] Tables 狀態 = ACTIVE
- [ ] TTL 啟用
- [ ] PITR 啟用

### Lambda 配置
- [ ] Layer 發布成功
- [ ] Layer 附加到 functions
- [ ] 環境變數正確設定
- [ ] IAM 權限無錯誤
- [ ] Functions 狀態 = Active

### 功能測試
- [ ] 私人對話訊息儲存 ✅
- [ ] AI 回應儲存 ✅
- [ ] 群組對話訊息儲存 ✅（如適用）
- [ ] 群組上下文載入 ✅（如適用）
- [ ] Metadata 自動更新 ✅

### 日誌驗證
- [ ] ConversationService 初始化成功
- [ ] 無 ImportError
- [ ] 無 DynamoDB 錯誤
- [ ] 無權限錯誤

---

## 成功標準

**所有檢查項目必須通過**才能進行 Git commit。

如果任何檢查失敗：
1. 記錄錯誤
2. 修復問題
3. 重新驗證
4. 直到所有項目通過

---

**驗證負責人**: [Your Name]  
**預計時間**: 45-60 分鐘  
**完成條件**: 100% 檢查項目通過