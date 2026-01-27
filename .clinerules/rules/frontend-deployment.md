# Frontend Deployment Rules

**這是始終活動的規則** - 所有前端部署必須遵守這些標準

`always_active: true`

---

## 🎯 核心原則

**API Endpoint 配置的唯一真相來源：CloudFormation Stack Outputs**

任何時候修改 API endpoint，必須：
1. 從 CloudFormation 獲取正確值
2. 更新 `.env` 文件
3. 重新 build
4. 驗證 bundle
5. 然後部署

---

## 📋 強制性檢查清單

### 1. API Endpoint 配置

**✅ 正確做法**：
```bash
# 從 CloudFormation 獲取
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`RestApiEndpoint`].OutputValue' \
  --output text)

# 更新 .env
echo "VITE_API_ENDPOINT=$API_ENDPOINT" > web-adapter/frontend/.env
```

**❌ 禁止做法**：
- 手動編輯 .env 並猜測 endpoint
- 不檢查就使用 env.ts 的 fallback
- 假設 endpoint 沒變

---

### 2. Build 流程（強制）

**每次 build 前必須**：

```bash
# Step 1: 清除緩存
rm -rf dist/ node_modules/.vite

# Step 2: 驗證配置
cat .env | grep VITE_API_ENDPOINT

# Step 3: Build
npm run build

# Step 4: 驗證 bundle（必須！）
grep -o "https://.*execute-api.*amazonaws.com" dist/assets/index-*.js

# 如果輸出不包含預期的 endpoint，停止！不要部署！
```

---

### 3. 部署流程（強制）

**❌ 絕對禁止**：
```bash
# 不要這樣做！
npm run build
aws s3 sync dist/ s3://bucket/  # 沒有驗證
```

**✅ 正確流程**：
```bash
# 1. Build
npm run build

# 2. 驗證（必須）
EXPECTED_ENDPOINT="jooap0xv8l"  # 從 CloudFormation 獲取
grep "$EXPECTED_ENDPOINT" dist/assets/index-*.js || {
  echo "❌ Bundle 包含錯誤的 endpoint！"
  exit 1
}

# 3. 上傳
aws s3 sync dist/ s3://bucket/ --delete

# 4. 清除 CDN
aws cloudfront create-invalidation ...

# 5. 等待並驗證
sleep 120
curl https://d1p3mmbx4pyq2j.cloudfront.net | grep "$EXPECTED_ENDPOINT"
```

---

### 4. .env 文件管理

**檢查清單**：
- [ ] 確認 `.env` 存在且配置正確
- [ ] 確認 `.env.local` 不覆蓋錯誤值
- [ ] 確認 `.env` 在 .gitignore 中（包含敏感配置時）
- [ ] 提供 `.env.example` 作為模板

**正確的 .env**：
```bash
VITE_API_ENDPOINT=https://jooap0xv8l.execute-api.us-west-2.amazonaws.com/prod
VITE_WS_ENDPOINT=wss://356rrmw4pg.execute-api.us-west-2.amazonaws.com/prod
```

---

### 5. 後端更新時的前端檢查

**當執行以下操作時，必須考慮前端**：

```bash
# 如果執行：
sam deploy --stack-name agentcore-web-adapter ...

# 必須檢查：
# 1. API Gateway 是否重新部署？
# 2. Endpoint 是否改變？
# 3. 如果改變，必須更新前端 .env
```

---

## 🚫 常見錯誤和預防

### 錯誤 1：Build 緩存導致使用舊配置

**預防**：
- 每次 build 前 `rm -rf dist/ node_modules/.vite`
- 使用環境變數明確設置

### 錯誤 2：.env 文件包含錯誤值

**預防**：
- 定期從 CloudFormation 同步
- Build 後驗證 bundle

### 錯誤 3：部署後沒有清除 CDN

**預防**：
- 使用 workflow 自動化
- 強制等待 invalidation 完成

### 錯誤 4：瀏覽器緩存

**預防**：
- 文檔中說明使用無痕模式測試
- 使用 versioned URLs

---

## 🎓 AI Agent 職責

作為 Cline Agent，在前端部署時你必須：

### Build 前
- ✅ 提醒檢查 .env 配置
- ✅ 提醒清除 build 緩存
- ✅ 建議使用環境變數

### Build 後
- ✅ 強制要求驗證 bundle
- ✅ 不允許未驗證就上傳
- ✅ 提供驗證命令

### 部署後
- ✅ 確認 CloudFront invalidation
- ✅ 提醒等待生效時間
- ✅ 提供測試方法

---

## 📊 檢查清單模板

```markdown
## 前端部署檢查清單

### 配置階段
- [ ] 從 CloudFormation 獲取最新 endpoints
- [ ] 更新 .env 文件
- [ ] 檢查 .env.local 沒有衝突

### Build 階段
- [ ] 清除緩存：rm -rf dist/ node_modules/.vite
- [ ] 執行 build：npm run build
- [ ] 驗證 bundle：grep endpoint dist/assets/*.js
- [ ] 確認輸出包含正確的 endpoint

### 部署階段
- [ ] 上傳到 S3：aws s3 sync dist/ ...
- [ ] 驗證 S3：aws s3 cp s3://... - | grep endpoint
- [ ] CloudFront invalidation
- [ ] 等待 2-5 分鐘

### 測試階段
- [ ] 使用無痕模式測試
- [ ] 檢查開發者工具 Network tab
- [ ] 確認請求使用正確的 endpoint
```

---

**規則版本**: v1.0  
**創建日期**: 2027-01-27  
**基於經驗**: Admin Panel 部署 endpoint 錯誤  
**強制執行**: 是  
**適用範圍**: 所有 Cline agents  
**優先級**: Critical（最高）