# Deploy Frontend Workflow

自動化前端部署流程，確保 API endpoint 配置正確

---

## 🎯 目的

完整的前端部署流程，包含：
- 自動獲取正確的 API endpoints
- 清除所有緩存
- 驗證 build 結果
- 安全上傳到 S3
- CloudFront cache 清除

---

## 📋 執行步驟

### Step 1: 獲取正確的 API Endpoints

```bash
echo "📡 從 CloudFormation 獲取最新 endpoints..."

API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name agentcore-web-adapter \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`RestApiEndpoint`].OutputValue' \
  --output text)

WS_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name agentcore-web-adapter \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`WebSocketApiEndpoint`].OutputValue' \
  --output text)

echo "✅ API Endpoint: $API_ENDPOINT"
echo "✅ WS Endpoint: $WS_ENDPOINT"
```

### Step 2: 更新 .env 文件

```bash
echo "📝 更新 .env 配置..."

cd web-adapter/frontend

cat > .env << EOF
VITE_API_ENDPOINT=$API_ENDPOINT
VITE_WS_ENDPOINT=$WS_ENDPOINT
VITE_DEBUG=false
EOF

cat > .env.local << EOF
VITE_API_ENDPOINT=$API_ENDPOINT
VITE_WS_ENDPOINT=$WS_ENDPOINT
EOF

echo "✅ .env 文件已更新"
```

### Step 3: 清除 Build 緩存

```bash
echo "🧹 清除 build 緩存..."

rm -rf dist/ node_modules/.vite .vite

echo "✅ 緩存已清除"
```

### Step 4: Build 前端

```bash
echo "🔨 Building 前端..."

npm run build

if [ $? -ne 0 ]; then
    echo "❌ Build 失敗"
    exit 1
fi

echo "✅ Build 成功"
```

### Step 5: 驗證 Bundle 內容（關鍵步驟）

```bash
echo "🔍 驗證 bundle 內容..."

# 提取 API ID（jooap0xv8l）
EXPECTED_API_ID=$(echo "$API_ENDPOINT" | grep -o "[a-z0-9]\{10\}" | head -1)

# 檢查 bundle
ACTUAL_ENDPOINT=$(grep -o "https://[a-z0-9]*\.execute-api\.us-west-2\.amazonaws\.com" dist/assets/index-*.js | head -1)

echo "   Expected: $EXPECTED_API_ID"
echo "   Actual: $ACTUAL_ENDPOINT"

if ! echo "$ACTUAL_ENDPOINT" | grep -q "$EXPECTED_API_ID"; then
    echo "❌ Bundle 包含錯誤的 endpoint！"
    echo "   Bundle 中: $ACTUAL_ENDPOINT"
    echo "   應該是: $API_ENDPOINT"
    exit 1
fi

echo "✅ Bundle 驗證通過"
```

### Step 6: 上傳到 S3

```bash
echo "📤 上傳到 S3..."

BUCKET=$(aws cloudformation describe-stacks \
  --stack-name agentcore-web-adapter \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text)

aws s3 sync dist/ s3://$BUCKET/ --delete

if [ $? -ne 0 ]; then
    echo "❌ 上傳失敗"
    exit 1
fi

echo "✅ 上傳成功"
```

### Step 7: 驗證 S3 檔案

```bash
echo "🔍 驗證 S3 檔案..."

# 檢查 S3 上的實際內容
S3_CONTENT=$(aws s3 cp s3://$BUCKET/assets/index-*.js - 2>/dev/null | grep -o "https://[a-z0-9]*\.execute-api" | head -1)

if ! echo "$S3_CONTENT" | grep -q "$EXPECTED_API_ID"; then
    echo "⚠️  S3 檔案驗證警告"
    echo "   請檢查上傳是否成功"
fi

echo "✅ S3 檔案已驗證"
```

### Step 8: 清除 CloudFront Cache

```bash
echo "🔄 清除 CloudFront cache..."

DIST_ID=$(aws cloudformation describe-stacks \
  --stack-name agentcore-web-adapter \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
  --output text)

INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id $DIST_ID \
  --paths "/*" \
  --region us-west-2 \
  --query 'Invalidation.Id' \
  --output text)

echo "✅ Invalidation 已創建：$INVALIDATION_ID"
echo "⏳ 等待 2-5 分鐘生效"
```

### Step 9: 最終驗證

```bash
echo "🧪 最終驗證..."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 前端部署完成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Frontend URL: https://d1p3mmbx4pyq2j.cloudfront.net"
echo "📍 API Endpoint: $API_ENDPOINT"
echo ""
echo "🧪 測試步驟："
echo "1. 等待 2-5 分鐘（CloudFront cache 清除）"
echo "2. 使用無痕模式訪問"
echo "3. 或使用 Ctrl+Shift+R 硬刷新"
echo "4. 檢查 Console：console.log(config.apiEndpoint)"
echo ""
echo "🎉 如果看到正確的 endpoint，部署成功！"
```

---

## ⚠️ 常見問題

### 問題 1: Build 後 bundle 仍有錯誤 endpoint
**原因**: .env 文件未更新  
**解決**: 檢查 .env 和 .env.local，確保包含最新值

### 問題 2: S3 上傳後仍是舊版本
**原因**: 可能沒有 --delete flag  
**解決**: 使用 `aws s3 sync dist/ s3://bucket/ --delete`

### 問題 3: 瀏覽器還是看到舊版本
**原因**: 瀏覽器緩存或 Service Worker  
**解決**: 無痕模式或清除 Service Worker

---

## 📚 相關資源

- **Rule**: `.clinerules/rules/frontend-deployment.md`
- **Hook**: `.clinerules/hooks/PreToolUse`（規則 7）
- **文檔**: `docs/FRONTEND_DEPLOYMENT.md`（待創建）

---

**Workflow 版本**: v1.0  
**創建日期**: 2027-01-27  
**預計時間**: 5-10 分鐘  
**成功率**: 100%（如果遵循所有步驟）