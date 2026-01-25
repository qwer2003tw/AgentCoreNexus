# Phase 2 身份綁定測試指南

**目的**：驗證 Telegram 和 Web 端的身份綁定功能完整運作

---

## 📋 測試前確認

### 1. 確認所有部署狀態
```bash
# 檢查 5 個 stacks 都正常
aws cloudformation list-stacks \
  --region us-west-2 \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  --query 'StackSummaries[?contains(StackName, `agentcore`)].StackName'

# 預期看到：
# - agentcore-telegram-adapter
# - agentcore-ai-processor
# - agentcore-web-adapter
# - agentcore-conversation-storage
# - agentcore-identity-binding
```

### 2. 確認 Lambda 狀態
```bash
# telegram-adapter
aws lambda get-function \
  --function-name agentcore-telegram-adapter-receiver \
  --region us-west-2 \
  --query 'Configuration.{State:State,Layer:Layers[0].Arn}'

# web-adapter
aws lambda get-function \
  --function-name agentcore-web-adapter-binding-api \
  --region us-west-2 \
  --query 'Configuration.{State:State,Layer:Layers[0].Arn}'

# 預期：都是 Active，都使用 shared-services:2
```

---

## 🧪 測試 1: Telegram /bind 命令

### 執行步驟
1. 在 Telegram 與 Bot 的私人對話中輸入：`/bind`
2. 等待回應（約 2-3 秒）

### 預期結果
```
🔗 身份綁定碼

您的綁定碼：123456
⏰ 有效期限：10 分鐘

請在 Web 介面的「綁定」選單輸入此綁定碼

⚠️ 注意：
• 此綁定碼只能使用一次
• 綁定後將共享跨通道對話歷史
• 綁定碼將在 10 分鐘後自動失效
```

### 驗證點
- [x] 收到 6 位數字（全數字）
- [x] 有效期限顯示為 10 分鐘
- [x] 訊息格式正確
- [x] 回應時間 < 3 秒

### 檢查 DynamoDB
```bash
# 應該看到新記錄
aws dynamodb scan \
  --table-name agentcore-binding-codes-prod \
  --region us-west-2 \
  --limit 1

# 預期看到：
# - code: "123456"（你收到的碼）
# - telegram_user_id: "316743844"
# - used: false
# - expires_at: timestamp（約 10 分鐘後）
```

### 如果失敗
```bash
# 檢查 CloudWatch 日誌
aws logs tail /aws/lambda/agentcore-telegram-adapter-receiver \
  --region us-west-2 \
  --since 5m \
  --filter-pattern "IdentityService\|Bind\|ERROR"
```

---

## 🧪 測試 2: Telegram /mybindings 命令

### 執行步驟
1. 在 Telegram 輸入：`/mybindings`

### 預期結果（未綁定時）
```
🔗 我的身份綁定

目前沒有綁定其他身份

💡 想要綁定 Web 帳號？
使用 /bind 命令生成綁定碼
```

### 驗證點
- [x] 顯示「沒有綁定」
- [x] 提示使用 /bind

---

## 🧪 測試 3: Web 端綁定

### 前提
- 已在 Telegram 執行 /bind 並獲得綁定碼（例如：123456）
- 綁定碼未過期（10 分鐘內）

### 執行步驟
1. 打開 Web 介面：https://d1acz2ktx0n1il.cloudfront.net
2. 登入（test1@test.com / Test123!）
3. 點擊左側邊欄的「綁定 Telegram」按鈕
4. 在彈出的對話框中：
   - 閱讀綁定步驟說明
   - 輸入從 Telegram 獲得的 6 位綁定碼
   - 點擊「驗證並綁定」按鈕
5. 等待回應（約 1-2 秒）

### 預期結果
```
✅ 綁定成功！您的 Telegram 和 Web 帳號已連結。
```

### 驗證點
- [x] 看到成功訊息
- [x] 對話框切換到「已綁定」狀態
- [x] 顯示已綁定的身份列表
- [x] 顯示 unified_conversation_id

### 檢查 DynamoDB
```bash
# 1. 綁定碼應該已標記為使用
aws dynamodb get-item \
  --table-name agentcore-binding-codes-prod \
  --region us-west-2 \
  --key '{"code":{"S":"123456"}}'

# 預期：used: true, used_by: "test1@test.com"

# 2. identity_map 應該有兩條記錄
aws dynamodb scan \
  --table-name agentcore-identity-map-prod \
  --region us-west-2 \
  --limit 5

# 預期看到：
# - identity_id: "tg:316743844", unified_conversation_id: "unified:xxx"
# - identity_id: "web:test1@test.com", unified_conversation_id: "unified:xxx"（相同）
```

### 如果失敗
```bash
# 檢查 Web binding Lambda 日誌
aws logs tail /aws/lambda/agentcore-web-adapter-binding-api \
  --region us-west-2 \
  --since 5m \
  --filter-pattern "ERROR\|Exception\|Failed"
```

---

## 🧪 測試 4: 驗證雙向綁定狀態

### 4A: Telegram 端查看
```
在 Telegram 輸入: /mybindings
```

**預期結果**：
```
🔗 我的身份綁定

📱 Telegram ID: 316743844
🌐 統一對話 ID: unified:xxx-xxx-xxx

已綁定的身份：
  • 🖥️ Web: test1@test.com
    綁定時間: 2026-01-25 18:00

（共 2 個身份綁定）

💡 提示：綁定後的對話在所有通道同步
```

### 4B: Web 端查看
```
1. 重新載入 Web 頁面
2. 點擊「綁定 Telegram」按鈕
```

**預期結果**：
```
✅ 已綁定

您的 Telegram 帳號已經與此 Web 帳號綁定

已綁定的身份：
  📱 telegram: 316743844

統一對話 ID: unified:xxx-xxx-xxx

[解除綁定] 按鈕
```

---

## 🧪 測試 5: 錯誤場景測試

### 5A: 無效綁定碼
```
Web: 輸入隨機 6 位數字（例如：999999）
預期: "Invalid binding code"
```

### 5B: 過期綁定碼
```
等待 >10 分鐘後輸入舊碼
預期: "Binding code has expired"
```

### 5C: 已使用的綁定碼
```
綁定成功後，再次輸入相同的碼
預期: "Binding code has already been used"
```

### 5D: 重複綁定
```
已綁定後，再次嘗試綁定（用新碼）
預期: 重用相同的 unified_conversation_id
```

---

## 🧪 測試 6: 解除綁定

### 6A: Telegram 端解綁
```
1. /unbind
   預期: 顯示確認訊息，列出已綁定身份

2. /unbind confirm
   預期: 顯示「已解除身份綁定」

3. /mybindings
   預期: 顯示「沒有綁定」
```

### 6B: Web 端解綁
```
1. 點擊「綁定 Telegram」按鈕
2. 點擊「解除綁定」按鈕
3. 確認對話框 → 確認
4. 重新載入頁面
   預期: 顯示未綁定狀態
```

### 驗證 DynamoDB
```bash
# identity_map 中的 unified_conversation_id 應該被移除
aws dynamodb get-item \
  --table-name agentcore-identity-map-prod \
  --region us-west-2 \
  --key '{"identity_id":{"S":"tg:316743844"}}'

# 預期：沒有 unified_conversation_id 欄位
```

---

## 🎯 完整 E2E 流程測試

### 完整綁定流程（約 5 分鐘）
```
Step 1: Telegram /bind
   ↓ 收到碼: 123456

Step 2: 檢查 DynamoDB binding_codes
   ↓ 確認碼存在且 used=false

Step 3: Web 登入並點擊「綁定 Telegram」
   ↓ 輸入 123456

Step 4: Web 點擊「驗證並綁定」
   ↓ 看到成功訊息

Step 5: 檢查 DynamoDB binding_codes
   ↓ used=true

Step 6: 檢查 DynamoDB identity_map
   ↓ 兩個身份都有相同的 unified_conversation_id

Step 7: Telegram /mybindings
   ↓ 看到 Web 帳號

Step 8: Web 重新載入
   ↓ 看到「已綁定」狀態

✅ 所有步驟通過 = 綁定功能完全正常！
```

---

## 📊 測試檢查清單

### 基本功能
- [ ] Telegram `/bind` 生成碼
- [ ] Telegram `/mybindings` 顯示狀態
- [ ] Telegram `/unbind` 解除綁定
- [ ] Web 輸入碼驗證並綁定
- [ ] Web 查看綁定狀態
- [ ] Web 解除綁定

### 錯誤處理
- [ ] 無效碼測試
- [ ] 過期碼測試
- [ ] 已使用碼測試
- [ ] 重複綁定測試

### 數據驗證
- [ ] binding_codes 表記錄正確
- [ ] identity_map 表記錄正確
- [ ] TTL 機制運作
- [ ] GSI 查詢正常

### 日誌檢查
- [ ] Telegram Lambda 無錯誤
- [ ] Web Lambda 無錯誤
- [ ] 初始化訊息正確

---

## 🚨 常見問題排查

### 問題 A: Telegram /bind 無反應
**檢查**：
```bash
aws logs tail /aws/lambda/agentcore-telegram-adapter-receiver \
  --region us-west-2 \
  --since 10m
```
**尋找**：ImportModuleError, IdentityService, ERROR

### 問題 B: Web 綁定失敗
**檢查**：
```bash
aws logs tail /aws/lambda/agentcore-web-adapter-binding-api \
  --region us-west-2 \
  --since 10m
```
**尋找**：Failed to verify, AccessDeniedException

### 問題 C: 綁定碼無效
- 確認在 10 分鐘內使用
- 確認只使用一次
- 確認碼是正確的 6 位數字

---

## ✅ 成功標準

**所有測試通過後**：
- ✅ Telegram 3 個命令都正常運作
- ✅ Web 可以成功綁定
- ✅ DynamoDB 資料正確
- ✅ 日誌無錯誤
- ✅ 雙向查詢狀態一致

**達成後進入 Day 6：文檔和清理階段**