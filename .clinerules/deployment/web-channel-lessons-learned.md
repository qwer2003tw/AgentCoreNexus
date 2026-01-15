# Web Channel 開發經驗與教訓

**基於專案**: AgentCore Nexus Web Channel Attachments  
**日期**: 2026-01-14  
**重要性**: ⭐⭐⭐ 關鍵經驗

---

## 🎯 核心教訓總結

### 1. S3 Presigned URL 307 Redirect 問題 ⭐⭐⭐

**問題**：不指定 region 的 S3 client 生成的 presigned URL 會導致 HTTP 307 Temporary Redirect

**症狀**：
- `curl` 需要 `-L` flag 才能上傳成功
- 瀏覽器 XMLHttpRequest 上傳失敗（不會自動 follow 307）
- 前端顯示「網絡錯誤」

**根本原因**：
```python
# ❌ 錯誤：沒有指定 region
s3_client = boto3.client("s3")

# 生成的 URL 格式：
# https://bucket.s3.amazonaws.com/key...
# S3 返回 307 redirect 到區域特定 endpoint
```

**解決方案**：
```python
# ✅ 正確：指定 region 和配置
from botocore.client import Config

s3_client = boto3.client(
    "s3",
    region_name="us-west-2",  # 明確指定 region
    config=Config(
        signature_version='s3v4',
        s3={'addressing_style': 'virtual'}
    )
)

# 生成的 URL 格式：
# https://bucket.s3.us-west-2.amazonaws.com/key...
# 直接 HTTP 200，無 redirect
```

**驗證方法**：
```bash
# 測試 presigned URL
curl -v -X PUT "PRESIGNED_URL" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @test.file

# 應該看到：
# HTTP/1.1 200 OK  (不是 307)
```

**何時使用**：
- 任何生成 presigned URL 的 Lambda
- 特別是給瀏覽器使用的 URL
- PUT/POST 操作更容易遇到

---

### 2. Infrastructure as Code 原則 ⭐⭐⭐

**教訓**：所有 AWS 配置都應該在 CloudFormation/SAM template 中，不要手動配置

**錯誤示例**：
```bash
# ❌ 手動配置 S3 CORS
aws s3api put-bucket-cors --bucket my-bucket --cors-configuration file://cors.json
```

**問題**：
- Stack 重新部署時可能丟失
- 其他人部署時不知道需要手動配置
- 違反 IaC 原則
- 難以追蹤和審計

**正確做法**：
```yaml
# ✅ 在 template 中配置
AttachmentsBucket:
  Type: AWS::S3::Bucket
  Properties:
    CorsConfiguration:
      CorsRules:
        - AllowedOrigins: ['*']
          AllowedMethods: [PUT, POST, GET, HEAD]
          AllowedHeaders: ['*']
          ExposedHeaders: [ETag]
          MaxAge: 3000
```

**檢查清單**：
- [ ] 所有 S3 bucket 配置在 template
- [ ] 所有 IAM 權限在 template
- [ ] 所有環境變數在 template
- [ ] 沒有「部署後手動執行」的步驟

---

### 3. 前端部署完整流程 ⭐⭐

**教訓**：前端代碼變更後，必須重新 build 並部署

**常見錯誤**：
- 修改了前端代碼
- 但沒有重新 build
- 用戶看到的是舊版本

**完整流程**：
```bash
# 1. Build（跳過 TS 類型檢查可加速）
cd web-channel/frontend
npx vite build  # 或 npm run build

# 2. 上傳到 S3
BUCKET=$(aws cloudformation describe-stacks ... | jq -r ...)
aws s3 sync dist/ s3://$BUCKET/ --delete

# 3. 清除 CloudFront cache（必須）
DIST_ID=$(aws cloudformation describe-stacks ... | jq -r ...)
aws cloudfront create-invalidation \
  --distribution-id $DIST_ID \
  --paths "/*"

# 4. 等待 2-5 分鐘生效
```

**驗證**：
- 檢查 dist/ 目錄時間戳
- 使用無痕模式測試
- 檢查 CloudFront invalidation 狀態

---

### 4. 跨服務資料格式統一 ⭐⭐⭐

**教訓**：不同來源的資料必須轉換為統一格式，才能被下游服務處理

**問題示例**：
```python
# Web 附件格式
{
    "id": "att-123",
    "name": "test.jpg",
    "key": "attachments/user/att-123/test.jpg"  # ❌ 只有 key
}

# Processor 期望格式
{
    "type": "photo",           # ❌ 缺少
    "s3_url": "s3://bucket/key",  # ❌ 缺少
    "task": "請描述這張圖片"  # ❌ 缺少
}
```

**解決方案**：
```python
def convert_web_attachments(web_attachments: list, user_message: str = "") -> list:
    """轉換 Web 格式為統一格式"""
    result = []
    bucket = "agentcore-web-channel-attachments-190825685292"
    
    for att in web_attachments:
        # 1. 構建完整 S3 URL（關鍵！）
        s3_url = f"s3://{bucket}/{att['key']}"
        
        # 2. 添加類型
        content_type = att.get("content_type", "")
        att_type = "photo" if content_type.startswith("image/") else "document"
        
        # 3. 添加任務
        if not user_message:
            task = "請描述這張圖片" if att_type == "photo" else "請摘要檔案"
        else:
            task = user_message
        
        result.append({
            "type": att_type,
            "s3_url": s3_url,
            "task": task,
            # ... 其他欄位
        })
    
    return result
```

**原則**：
- 在邊界處轉換格式（adapter 層）
- 核心處理器使用統一格式
- 明確記錄格式規範

---

### 5. 跨服務權限管理 ⭐⭐

**教訓**：當一個服務需要訪問另一個服務的資源時，必須明確配置權限

**問題**：
- Processor Lambda 需要讀取 Web bucket
- 但最初只有 Telegram bucket 權限

**檢查方法**：
```bash
# 查看 Lambda IAM role
aws lambda get-function --function-name FUNCTION \
  --query 'Configuration.Role'

# 檢查 IAM policy
aws iam get-role-policy --role-name ROLE --policy-name POLICY \
  | jq '.PolicyDocument.Statement[] | select(.Action[] | contains("s3:"))'
```

**解決方案**：
```yaml
# 在 template 中添加權限
Policies:
  - Statement:
      - Effect: Allow
        Action: s3:GetObject
        Resource:
          - 'arn:aws:s3:::telegram-bot-files-*/*'
          - 'arn:aws:s3:::agentcore-web-channel-attachments-*/*'
```

**原則**：
- 明確列出所有需要訪問的資源
- 使用最小權限原則
- 在 template 中記錄權限用途

---

### 6. E2E 測試診斷流程 ⭐⭐

**教訓**：當測試失敗時，需要系統性診斷

**診斷流程**：
1. **添加詳細日誌**
   ```typescript
   // 前端添加詳細日誌
   console.log('Upload response:', {
       status: xhr.status,
       statusText: xhr.statusText,
       responseText: xhr.responseText
   })
   ```

2. **檢查 Lambda 日誌**
   ```bash
   aws logs tail /aws/lambda/FUNCTION --since 10m
   ```

3. **手動測試 API**
   ```bash
   # 測試完整流程
   curl -X POST API/endpoint ...
   ```

4. **檢查權限**
   ```bash
   aws iam get-role-policy ...
   ```

5. **測試 presigned URL**
   ```bash
   curl -v -X PUT "PRESIGNED_URL" ...
   ```

**原則**：
- 從外到內逐層診斷
- 每一層都驗證
- 記錄發現的問題

---

### 7. 完成標準不妥協 ⭐⭐⭐

**教訓**：97.6% ≠ 100%，必須完全達成目標才能說「完成」

**錯誤示例**：
- E2E 測試 41/42 passed (97.6%)
- 報告「任務完成」❌

**正確做法**：
- 目標：42/42 passed
- 實際：42/42 passed ✅
- 才能報告完成

**為什麼重要**：
- 那 1 個失敗可能隱藏關鍵 bug
- 降低標準會養成壞習慣
- 專業標準需要堅持

---

### 8. 測試環境與生產環境差異 ⭐⭐

**教訓**：Mock API 測試通過不代表真實環境會通過

**經驗**：
- E2E 用 Mock API：41/42 passed
- E2E 用真實 AWS：42/42 passed（修復後）

**原因**：
- Mock API 不會產生 307 redirect
- Mock API 不需要 CORS
- Mock API 不需要真實權限

**建議**：
- 早期用 Mock 快速開發
- 部署前必須用真實 AWS 測試
- CI/CD 應該用真實環境

---

### 9. 測試覆蓋的盲點 ⭐⭐⭐

**問題**：E2E 測試沒有發現 `content_type.startsWith()` 的 undefined bug

**為什麼測試沒發現**：
```typescript
// E2E 測試做了
test('upload attachment', async ({ page }) => {
    await fileInput.setInputFiles('sample.txt')
    await page.waitForSelector('text=sample.txt')  // ✅ 上傳成功
    await page.click('button[aria-label="發送訊息"]')  // ✅ 發送成功
    // ❌ 但沒有等待 AI 回覆
    // ❌ 沒有檢查回覆中的附件顯示
})
```

**Bug 觸發條件**：
1. 用戶上傳附件並發送
2. AI 處理並回覆
3. **回覆被保存到歷史**（包含附件資訊）
4. 前端嘗試顯示歷史消息中的附件
5. `AttachmentItem` 讀取 `content_type` → undefined → 崩潰

**教訓**：
- E2E 測試應該覆蓋**完整流程**，不只是功能入口
- 應該等待異步操作完成
- 應該測試資料顯示，不只是資料輸入

**正確的測試**：
```typescript
test('attachment full flow with AI reply', async ({ page }) => {
    await createNewConversation(page)
    await fileInput.setInputFiles('sample.txt')
    await page.click('button[aria-label="發送訊息"]')
    
    // ⭐ 等待 AI 回覆
    await waitForAIReply(page, 30000)
    
    // ⭐ 重新載入（從歷史載入附件）
    await page.reload()
    
    // ⭐ 驗證附件顯示正常
    const attachments = page.locator('.attachment-item')
    await expect(attachments).toBeVisible()
    
    // ⭐ 檢查沒有 JS 錯誤
    const errors = await page.evaluate(() => 
        performance.getEntriesByType('navigation')
    )
    // 頁面應該成功載入
})
```

---

### 10. 防禦性編程必要性 ⭐⭐⭐

**教訓**：永遠不要假設資料完整性

**錯誤示例**：
```typescript
const isImage = attachment.content_type.startsWith('image/')
// ❌ 假設 content_type 一定存在
```

**正確做法**：
```typescript
const isImage = attachment.content_type?.startsWith('image/') ?? false
// ✅ 使用 optional chaining
// ✅ 提供預設值
```

**何時使用防禦性編程**：
- ✅ 所有外部資料（API、資料庫、用戶輸入）
- ✅ 可選欄位
- ✅ 跨服務通訊
- ✅ 歷史資料（格式可能改變）

**檢查清單**：
- [ ] 所有 `.` 存取都考慮 undefined
- [ ] 使用 `?.` optional chaining
- [ ] 提供合理的預設值
- [ ] 在邊界處驗證資料

**範例**：
```typescript
// ❌ 危險
user.profile.name
attachment.content_type.startsWith()

// ✅ 安全
user?.profile?.name ?? 'Unknown'
attachment.content_type?.startsWith('image/') ?? false
```

---

## 📋 Web Channel 部署檢查清單

### Template 配置
- [ ] S3 bucket 包含 CORS 配置
- [ ] S3 client 指定 region
- [ ] 所有跨服務權限已配置
- [ ] 環境變數完整

### 部署流程
- [ ] 後端：sam build && sam deploy
- [ ] 前端：npm run build
- [ ] 前端：s3 sync
- [ ] 前端：cloudfront invalidation

### 測試驗證
- [ ] 單元測試 100% pass
- [ ] E2E 測試 100% pass
- [ ] 手動測試 presigned URL
- [ ] 驗證前端顯示正確

---

## 🔧 快速故障排除

### 問題：前端看不到新功能
**檢查**：
1. dist/ 時間戳是否最新？
2. S3 檔案是否已上傳？
3. CloudFront cache 是否已清除？
4. 瀏覽器是否已硬刷新？

### 問題：附件上傳失敗
**檢查**：
1. presigned URL 格式（是否包含 region）？
2. S3 CORS 是否配置？
3. 瀏覽器控制台錯誤？
4. Lambda 日誌有無錯誤？

### 問題：附件無法被 AI 分析
**檢查**：
1. 附件格式是否包含 s3_url？
2. Processor 是否有 S3 讀取權限？
3. s3_url 格式是否正確（s3://bucket/key）？
4. 附件是否包含 task 欄位？

---

## 💡 最佳實踐

### S3 Presigned URL
```python
# 始終指定 region 和配置
s3_client = boto3.client(
    "s3",
    region_name=os.environ.get("AWS_REGION", "us-west-2"),
    config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'})
)
```

### CORS 配置
```yaml
# 始終在 template 中定義
CorsConfiguration:
  CorsRules:
    - AllowedOrigins: ['*']  # 生產環境應限制
      AllowedMethods: [PUT, POST, GET, HEAD]
      AllowedHeaders: ['*']
      ExposedHeaders: [ETag]  # 重要：讓瀏覽器能讀取 ETag
      MaxAge: 3000
```

### 附件格式轉換
```python
# 在邊界處（adapter）轉換格式
def convert_to_unified_format(source_format):
    return {
        "type": ...,      # 必須
        "s3_url": ...,    # 必須（完整格式）
        "task": ...,      # 必須
        "file_name": ..., # 建議
        "mime_type": ..., # 建議
    }
```

### 前端部署
```bash
# 完整流程腳本
#!/bin/bash
set -e

# Build
npm run build

# Upload
aws s3 sync dist/ s3://$BUCKET/ --delete

# Invalidate（必須）
aws cloudfront create-invalidation \
  --distribution-id $DIST_ID \
  --paths "/*"

echo "✅ 部署完成，等待 2-5 分鐘生效"
```

---

## 🚨 避免的錯誤

### ❌ 不要：手動配置後忘記更新 template
**後果**：重新部署時配置丟失

### ❌ 不要：前端修改後不重新 build
**後果**：用戶看到舊版本

### ❌ 不要：跳過真實環境測試
**後果**：生產環境才發現問題

### ❌ 不要：97.6% 就說完成
**後果**：那 2.4% 可能是關鍵功能

### ❌ 不要：不同服務用不同的資料格式
**後果**：難以整合和維護

---

## 📚 相關文檔

- [Lambda 開發最佳實踐](./lambda-development-best-practices.md)
- [AWS Lambda 部署問題](./aws-lambda-telegram-bot-deployment-issues.md)
- [開發與除錯指南](./development-and-debugging-guide.md)

---

## 🔄 持續改進

這個文檔應該隨著新經驗持續更新：
- 發現新問題時添加
- 找到更好解決方案時更新
- 定期回顧並精煉

---

**文檔版本**: 1.0  
**創建日期**: 2026-01-14  
**基於經驗**: Web Channel 附件功能開發（2.5 小時診斷和修復）  
**維護者**: AgentCoreNexus Team