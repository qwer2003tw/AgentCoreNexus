# 重構續接指南 - Phase 7-11 執行

**創建時間**: 2026-01-15 15:58 PM UTC  
**當前進度**: 90% 完成（Day 1 完成）  
**最新 Commit**: 3404508

---

## 🎯 當前狀態

### Day 1 已完成 ✅

**Git 分支**: `refactor/complete-naming-overhaul`  
**完成**: Phase 1-6（90% 總進度）  
**狀態**: ✅ 所有非破壞性工作完成

### 已完成的工作

✅ **Phase 1**: 數據備份（100%）
- 9 個備份文件在 `dev-in-progress/naming-overhaul/backup/`
- DynamoDB: 5 表
- Secrets: 1 個
- Stacks: 3 個配置

✅ **Phase 2**: 目錄重組（100%）
- ai-processor ✓
- telegram-adapter ✓
- web-adapter ✓

✅ **Phase 3**: 代碼更新（100%）
- web-adapter template 參數
- .clinerules 全局更新（42 處）
- docs/ 更新
- 所有 README.md 更新

✅ **Phase 4**: Schema 管理（50%）
- schemas/message.schema.json ✓
- schemas/README.md ✓
- Tags/DLQ 延後至 Stack 重建

✅ **Phase 5**: 專業化文檔（100%）
- ENV.md ✓
- API.md ✓
- NEW_CHANNEL_GUIDE.md ✓

✅ **Phase 6**: .clinerules 更新（100%）
- workflows/backup-restore.md ✓
- deployment/stack-management-best-practices.md ✓

---

## 🚀 下一步：Phase 7-11（Stack 重建）

**預計時間**: 6-8 小時  
**完成度**: 90% → 100%  
**風險**: ⚠️ 高（破壞性變更）

### ⚠️ 執行前必讀

**這是破壞性變更區域！**

1. **不可逆操作**：Stack 刪除無法撤銷
2. **服務中斷**：刪除期間功能不可用（預計 3-4 小時）
3. **需要時間**：完整執行需要 6-8 小時
4. **需要專注**：可能遇到意外問題需要處理

**確認清單**：
- [ ] 選擇非高峰時段
- [ ] 預留充足時間（至少 8 小時）
- [ ] 網路穩定
- [ ] 心理準備（耐心和細心）

---

## 📋 Phase 7-11 執行計劃

### Phase 7: Stack 重建準備（30 分鐘）

#### 7.1 檢查當前 Stack 狀態
```bash
cd /home/ec2-user/Projects/AgentCoreNexus
git checkout refactor/complete-naming-overhaul

# 確認所有 Stacks 狀態
make status

# 或
aws cloudformation describe-stacks --region us-west-2 \
  --query 'Stacks[?contains(StackName,`telegram`) || contains(StackName,`agentcore`)].{Name:StackName,Status:StackStatus}' \
  --output table
```

#### 7.2 Disable EventBridge Rules
```bash
# 列出所有 rules
aws events list-rules \
  --event-bus-name telegram-adapter-receiver-events \
  --region us-west-2

# Disable 每個 rule
aws events disable-rule \
  --name telegram-adapter-receiver-message-received \
  --event-bus-name telegram-adapter-receiver-events \
  --region us-west-2

# 確認已 disabled
aws events describe-rule \
  --name telegram-adapter-receiver-message-received \
  --event-bus-name telegram-adapter-receiver-events \
  --region us-west-2 \
  --query 'State'
# 應該返回: "DISABLED"
```

#### 7.3 記錄當前 Exports（供參考）
```bash
# 保存所有 Exports
aws cloudformation list-exports --region us-west-2 > current-exports.json

# 查看
cat current-exports.json | jq '.Exports[] | select(.Name | contains("telegram") or contains("agentcore"))'
```

#### 7.4 最終備份驗證
```bash
cd dev-in-progress/naming-overhaul/backup/

# 檢查文件
ls -lh *.json
wc -l *.json

# 應該看到：
# 9 個 .json 文件
# 總大小 2-3 MB
# 各文件有合理的行數（不是空文件）

# 驗證可以解析
for f in *.json; do
  echo "檢查 $f..."
  jq . "$f" > /dev/null && echo "  ✅ Valid JSON"
done
```

---

### Phase 8: Stack 刪除（1 小時）

**⚠️ 重要**：必須按反向依賴順序刪除！

#### 8.1 刪除 Web Adapter
```bash
# 刪除
aws cloudformation delete-stack \
  --stack-name agentcore-web-adapter \
  --region us-west-2

# 等待完成（可能需要 10-20 分鐘）
aws cloudformation wait stack-delete-complete \
  --stack-name agentcore-web-adapter \
  --region us-west-2

# 確認刪除
aws cloudformation describe-stacks \
  --stack-name agentcore-web-adapter \
  --region us-west-2 2>&1 | grep "does not exist" && echo "✅ 已刪除"
```

#### 8.2 刪除 AI Processor
```bash
# 當前 Stack 名稱是 telegram-unified-bot
aws cloudformation delete-stack \
  --stack-name telegram-unified-bot \
  --region us-west-2

# 等待
aws cloudformation wait stack-delete-complete \
  --stack-name telegram-unified-bot \
  --region us-west-2

# 確認
aws cloudformation describe-stacks \
  --stack-name telegram-unified-bot \
  --region us-west-2 2>&1 | grep "does not exist" && echo "✅ 已刪除"
```

#### 8.3 刪除 Telegram Adapter（需要手動清理）
```bash
# 刪除
aws cloudformation delete-stack \
  --stack-name telegram-adapter-receiver \
  --region us-west-2

# 可能會卡住！如果 5 分鐘後還是 DELETE_IN_PROGRESS：

# 檢查是否有殘留的 EventBridge rules
aws events list-rules \
  --event-bus-name telegram-adapter-receiver-events \
  --region us-west-2

# 如果有 rules，手動刪除：
# 1. 列出 targets
aws events list-targets-by-rule \
  --rule RULE_NAME \
  --event-bus-name telegram-adapter-receiver-events \
  --region us-west-2

# 2. 刪除 targets
aws events remove-targets \
  --rule RULE_NAME \
  --event-bus-name telegram-adapter-receiver-events \
  --ids TARGET_ID \
  --region us-west-2

# 3. 刪除 rule
aws events delete-rule \
  --name RULE_NAME \
  --event-bus-name telegram-adapter-receiver-events \
  --region us-west-2

# 4. 重試 Stack 刪除
aws cloudformation delete-stack \
  --stack-name telegram-adapter-receiver \
  --region us-west-2
```

#### 8.4 驗證所有刪除完成
```bash
# 應該沒有任何 Stack
aws cloudformation describe-stacks --region us-west-2 \
  --query 'Stacks[?contains(StackName,`telegram`) || contains(StackName,`agentcore`)].StackName'

# 應該返回空陣列：[]
```

---

### Phase 9: Stack 重建（2-3 小時）

**⚠️ 重要**：必須按正向依賴順序部署！

#### 9.1 部署 Telegram Adapter（新名稱）
```bash
cd /home/ec2-user/Projects/AgentCoreNexus/telegram-adapter

# Build
sam build

# Deploy（新 Stack 名稱）
sam deploy \
  --stack-name agentcore-telegram-adapter \
  --region us-west-2 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset

# 等待完成並驗證
aws cloudformation describe-stacks \
  --stack-name agentcore-telegram-adapter \
  --region us-west-2 \
  --query 'Stacks[0].{Status:StackStatus,Updated:LastUpdatedTime}'

# 應該看到: StackStatus: CREATE_COMPLETE
```

#### 9.2 部署 AI Processor（新名稱）
```bash
cd /home/ec2-user/Projects/AgentCoreNexus/ai-processor

# Build
sam build

# Deploy（新 Stack 名稱）
sam deploy \
  --stack-name agentcore-ai-processor \
  --region us-west-2 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --parameter-overrides \
    MemoryId=YOUR_MEMORY_ID \
  --no-confirm-changeset

# 驗證
aws cloudformation describe-stacks \
  --stack-name agentcore-ai-processor \
  --region us-west-2 \
  --query 'Stacks[0].StackStatus'
```

#### 9.3 部署 Web Adapter（已經是新名稱）
```bash
cd /home/ec2-user/Projects/AgentCoreNexus/web-adapter/infrastructure

# Build
sam build -t web-channel-template.yaml

# Deploy
sam deploy \
  --template-file web-channel-template.yaml \
  --stack-name agentcore-web-adapter \
  --region us-west-2 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --parameter-overrides \
    Environment=dev \
    ExistingEventBusName=agentcore-telegram-adapter-events \
  --no-confirm-changeset

# 驗證
make status
```

#### 9.4 驗證所有 Stacks 健康
```bash
# 檢查所有 Stacks
aws cloudformation describe-stacks --region us-west-2 \
  --query 'Stacks[?contains(StackName,`agentcore`)].{Name:StackName,Status:StackStatus}' \
  --output table

# 所有應該是 CREATE_COMPLETE

# 檢查所有 Lambda 狀態
aws lambda list-functions --region us-west-2 \
  --query 'Functions[?contains(FunctionName,`agentcore`)].{Name:FunctionName,State:State}' \
  --output table

# 所有應該是 Active
```

---

### Phase 10: 數據恢復（1-2 小時）

#### 10.1 恢復 DynamoDB 表
```bash
cd /home/ec2-user/Projects/AgentCoreNexus/dev-in-progress/naming-overhaul/backup/

# 1. telegram-allowlist
aws dynamodb batch-write-item \
  --request-items file://telegram-allowlist.json \
  --region us-west-2

# 2. web-users
aws dynamodb batch-write-item \
  --request-items file://web-users.json \
  --region us-west-2

# 3. user-bindings
aws dynamodb batch-write-item \
  --request-items file://user-bindings.json \
  --region us-west-2

# 4. conversations
aws dynamodb batch-write-item \
  --request-items file://conversations.json \
  --region us-west-2

# 5. conversation-history（可能需要分批，如果超過 25 項）
aws dynamodb batch-write-item \
  --request-items file://conversation-history.json \
  --region us-west-2
```

#### 10.2 驗證數據恢復
```bash
# 檢查每個表的 item 數量
aws dynamodb scan --table-name telegram-allowlist --region us-west-2 --select COUNT
aws dynamodb scan --table-name agentcore-web-adapter-web-users --region us-west-2 --select COUNT
aws dynamodb scan --table-name agentcore-web-adapter-conversations --region us-west-2 --select COUNT

# 抽查一些數據
aws dynamodb scan --table-name telegram-allowlist --region us-west-2 --limit 5
```

#### 10.3 重新配置 Telegram Webhook
```bash
# 獲取新的 Webhook URL
WEBHOOK_URL=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-telegram-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' \
  --output text)

# 獲取 bot token 和 secret
BOT_TOKEN=$(aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-adapter-receiver-secrets \
  --query SecretString --output text | jq -r .bot_token)

WEBHOOK_SECRET=$(aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-adapter-receiver-secrets \
  --query SecretString --output text | jq -r .webhook_secret_token)

# 設置 Webhook
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"${WEBHOOK_URL}\",\"secret_token\":\"${WEBHOOK_SECRET}\"}"

# 驗證
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
# 檢查 pending_update_count 應該是 0
```

#### 10.4 重新部署前端（如需要）
```bash
cd /home/ec2-user/Projects/AgentCoreNexus/web-adapter

# 方法 1: 使用腳本
./scripts/deploy-frontend.sh

# 方法 2: 手動
cd frontend
npm run build

# 獲取新 bucket 名稱
BUCKET=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text)

# 上傳
aws s3 sync dist/ s3://$BUCKET/ --delete

# 清除 CloudFront cache
DIST_ID=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
  --output text)

aws cloudfront create-invalidation \
  --distribution-id $DIST_ID \
  --paths "/*"
```

---

### Phase 11: 完整測試驗證（1-2 小時）

#### 11.1 Lambda 健康檢查
```bash
# 檢查所有 Lambda 函數
aws lambda list-functions --region us-west-2 \
  --query 'Functions[?contains(FunctionName,`agentcore`)].{Name:FunctionName,State:State,LastUpdateStatus:LastUpdateStatus}' \
  --output table

# 所有應該是：
# State: Active
# LastUpdateStatus: Successful
```

#### 11.2 EventBridge 驗證
```bash
# 檢查 EventBridge Rules
aws events list-rules \
  --event-bus-name agentcore-telegram-adapter-events \
  --region us-west-2

# 檢查每個 rule 的 targets
aws events list-targets-by-rule \
  --rule message-received \
  --event-bus-name agentcore-telegram-adapter-events \
  --region us-west-2

# 應該有正確的 Lambda target
```

#### 11.3 執行單元測試
```bash
cd /home/ec2-user/Projects/AgentCoreNexus

# 快速測試（不含 E2E）
make test-quick

# 應該全部通過
```

#### 11.4 手動功能測試

**Telegram Bot**:
```bash
# 發送測試消息到 Bot
# 應該收到 AI 回覆（6-30 秒）
```

**Web Channel**:
```bash
# 獲取前端 URL
aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendUrl`].OutputValue' \
  --output text

# 訪問 URL，測試：
# 1. 登入
# 2. 創建對話
# 3. 發送消息
# 4. 接收 AI 回覆
```

#### 11.5 執行完整測試
```bash
cd /home/ec2-user/Projects/AgentCoreNexus

# 完整測試（包含 E2E）
make test

# 目標：100% 通過
```

#### 11.6 檢查 CloudWatch Logs
```bash
# 檢查最近 10 分鐘的錯誤
for func in agentcore-telegram-adapter-receiver agentcore-ai-processor-main agentcore-web-adapter-ws-connect; do
  echo "=== $func ==="
  aws logs filter-log-events \
    --region us-west-2 \
    --log-group-name /aws/lambda/$func \
    --filter-pattern "ERROR" \
    --start-time $(date -u -d '10 minutes ago' +%s)000 \
    --max-items 10
done

# 應該沒有錯誤（或只有預期的錯誤）
```

---

## ✅ 完成標準

**所有以下條件都滿足才算完成**：

### Infrastructure
- [ ] 所有 Stacks 狀態：CREATE_COMPLETE
- [ ] 所有 Lambda 狀態：Active
- [ ] EventBridge Rules 配置正確
- [ ] 所有 Exports 可用

### Data
- [ ] DynamoDB 表數據完整
- [ ] Secrets 可訪問
- [ ] 前端可訪問
- [ ] Webhook 已連接

### Testing
- [ ] 單元測試 100% 通過
- [ ] E2E 測試 100% 通過
- [ ] Telegram Bot 功能正常
- [ ] Web Channel 功能正常
- [ ] CloudWatch 無異常錯誤

### Documentation
- [ ] 更新 CHANGELOG.md（記錄此次重構）
- [ ] 更新 MASTER_PROGRESS.md（標記 100%）
- [ ] 創建最終完成報告

---

## 🔄 如果遇到問題

### Stack 刪除失敗
→ 參考 `.clinerules/deployment/stack-management-best-practices.md`

### Stack 創建失敗
→ 檢查 CloudFormation 事件，修復 template，重試

### 數據恢復失敗
→ 使用 backup/ 中的數據，參考 `.clinerules/workflows/backup-restore.md`

### 測試失敗
→ 檢查 Lambda logs，修復問題，重新測試

---

## 🎯 執行摘要

**Day 1 完成** ✅（90%）：
- 所有代碼和文檔更新
- Schema 和規則完善
- 完整備份就緒

**Day 2 任務**（10%）：
- Stack 重建
- 數據恢復
- 完整驗證

**預計總時間**：
- Day 1: 9 分鐘（已完成）
- Day 2: 6-8 小時（待執行）

---

## 📞 緊急聯絡

如果 Stack 重建過程中遇到無法解決的問題：

1. **停止操作**（不要繼續刪除）
2. **保留備份**（不要刪除 backup/）
3. **記錄錯誤**（截圖和日誌）
4. **尋求協助**（提供詳細錯誤信息）

---

**準備好了？開始執行 Phase 7！** 🚀

**提醒**：
- ⏰ 預留 6-8 小時
- 🕐 選擇非高峰時段
- 💪 保持耐心和細心
- 📋 逐步執行，不要跳步驟

**加油！最後 10% 了！** 💪

---

**版本**: v2.0  
**最後更新**: 2026-01-15 15:58 PM UTC  
**下一步**: Phase 7（Stack 重建準備）