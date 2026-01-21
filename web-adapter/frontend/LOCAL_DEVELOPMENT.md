# 本地開發指南

## 🚀 快速開始

### 啟動本地開發伺服器

```bash
cd web-adapter/frontend
npm run dev
```

訪問：**http://localhost:5173**

## 🔧 環境配置

### .env.local（已配置）

本地開發使用真實的 AWS 後端：

```bash
VITE_API_ENDPOINT=https://dr614rh1s6.execute-api.us-west-2.amazonaws.com/prod
VITE_WS_ENDPOINT=wss://c8921qtrs8.execute-api.us-west-2.amazonaws.com/prod
VITE_DEBUG=true
```

**注意**：`.env.local` 已在 `.gitignore` 中，不會提交到 Git。

## 📝 開發工作流程

### 修改代碼 → 測試 → 部署

#### Step 1: 本地開發和測試

```bash
# 啟動開發伺服器（如果還沒啟動）
npm run dev

# 修改代碼（例如 src/stores/chatStore.ts）
# 瀏覽器會自動熱重載（<1 秒）

# 在瀏覽器測試功能
# http://localhost:5173
```

#### Step 2: 確認修復後部署到生產環境

```bash
# 構建生產版本
npm run build

# 部署到 S3
aws s3 sync dist/ s3://agentcore-web-adapter-frontend-190825685292 \
  --delete --region us-west-2

# 失效 CloudFront 緩存
aws cloudfront create-invalidation \
  --distribution-id E38PYJE66F9ZOW \
  --paths "/*" \
  --region us-west-2
```

#### Step 3: 驗證生產環境

等待 3-5 分鐘後訪問：
- **CloudFront**: https://d3hplgekizttn1.cloudfront.net
- **S3 直接**（繞過緩存）: https://agentcore-web-adapter-frontend-190825685292.s3.us-west-2.amazonaws.com/index.html

## 🧪 測試當前修復（多對話路由）

### 測試場景：回覆應該顯示在正確的對話中

**步驟**：

1. **創建兩個對話**
   - 點擊「新對話」創建對話 A
   - 再點擊「新對話」創建對話 B

2. **在對話 A 發送消息**
   - 切換到對話 A
   - 輸入「測試 A」並發送

3. **立即切換到對話 B**
   - 在 AI 回覆之前點擊對話 B

4. **驗證結果**
   - ✅ **預期**：等待 5-10 秒後，切換回對話 A，可以看到 AI 回覆
   - ✅ **預期**：對話 B 保持乾淨，沒有對話 A 的消息
   - ❌ **錯誤**（修復前）：AI 回覆會顯示在對話 B

### 調試技巧

打開瀏覽器開發者工具（F12）查看：

**Console 標籤**：
- 應該看到：`WebSocket message received: {conversation_id: "xxx", ...}`
- `conversation_id` 應該與發送消息的對話 ID 匹配

**Network 標籤**：
- 查看 WebSocket 消息（WS frame）
- 確認收到的消息包含正確的 `conversation_id`

## 💻 開發環境優勢

### 為什麼本地開發更快？

| 操作 | 本地開發 | S3 部署 |
|------|----------|---------|
| 修改代碼 | 1 秒 | - |
| 看到效果 | 立即（熱重載）| 需要部署 |
| 部署時間 | 無 | 2-3 分鐘 |
| 緩存失效 | 無 | 3-5 分鐘 |
| **總時間** | **<1 秒** | **5-8 分鐘** |

### 開發效率提升

**場景：修復一個 bug**

**使用本地開發**：
```
發現 bug (0 分鐘)
  ↓
修改代碼 (1 分鐘)
  ↓
測試驗證 (立即)  ← 這裡節省 5-8 分鐘！
  ↓
確認修復 → 部署到 S3 (3 分鐘)
總計：4 分鐘
```

**直接修改 S3**（舊方式）：
```
發現 bug (0 分鐘)
  ↓
修改代碼 (1 分鐘)
  ↓
部署 S3 (2 分鐘)
  ↓
等 CloudFront (3-5 分鐘)  ← 每次都要等！
  ↓
測試驗證
  ↓
如果還有問題 → 重複以上流程
總計：6-8 分鐘（每次迭代）
```

## 📚 其他有用的開發命令

### 類型檢查
```bash
npm run build  # TypeScript 會檢查類型
```

### 查看構建大小
```bash
npm run build
# 查看 dist/ 目錄
ls -lh dist/assets/
```

### 清理構建
```bash
rm -rf dist/ node_modules/.vite
npm run build
```

## ⚠️ 注意事項

### CORS
- AWS API Gateway 已配置 CORS，允許 `localhost`
- 本地開發不會有 CORS 問題

### 認證
- JWT token 存儲在 `localStorage`
- 本地和 S3 環境共享同一個 token
- 在一個環境登入，另一個環境也會登入

### WebSocket
- 本地開發直接連接到 AWS WebSocket API
- 無需額外配置

## 🎯 立即開始測試

**現在就可以測試修復**：

1. 打開瀏覽器訪問：**http://localhost:5173**
2. 登入（使用現有帳號）
3. 按照上面的測試場景測試多對話路由
4. 如果正確，說明修復有效！
5. 等 CloudFront 緩存失效後，S3 環境也會正常

**開發伺服器已在後台運行，隨時可以測試！** 🚀