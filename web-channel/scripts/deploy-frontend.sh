#!/bin/bash
# Frontend 快速更新腳本
# 用於開發時快速測試前端修改（不重新部署 stack）

set -e

echo "📦 快速更新前端..."

# 定位到專案根目錄
cd "$(dirname "$0")/.."

# 1. 檢查 backend 是否已部署
echo "🔍 檢查 backend 部署狀態..."
if ! aws cloudformation describe-stacks --region us-west-2 --stack-name agentcore-web-channel &>/dev/null; then
    echo "❌ Backend 尚未部署！"
    echo "請先運行: ./scripts/deploy-backend.sh"
    exit 1
fi

# 2. 獲取 Stack Outputs（S3 bucket、CloudFront、API endpoints）
echo "📡 獲取 Stack Outputs..."

BUCKET_NAME=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text)

DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
  --output text)

FRONTEND_URL=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendUrl`].OutputValue' \
  --output text)

REST_API=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].Outputs[?OutputKey==`RestApiEndpoint`].OutputValue' \
  --output text)

WS_API=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].Outputs[?OutputKey==`WebSocketApiEndpoint`].OutputValue' \
  --output text)

if [ -z "$BUCKET_NAME" ] || [ -z "$DISTRIBUTION_ID" ]; then
    echo "❌ 無法從 Stack 讀取 S3 bucket 或 CloudFront distribution"
    echo "請確認 Stack 已完整部署"
    exit 1
fi

echo "S3 Bucket: $BUCKET_NAME"
echo "CloudFront: $DISTRIBUTION_ID"
echo "Frontend URL: $FRONTEND_URL"

# 3. 配置環境變數
echo "⚙️  配置環境變數..."
cd frontend
cat > .env << EOF
VITE_API_ENDPOINT=$REST_API
VITE_WS_ENDPOINT=$WS_API
VITE_DEBUG=false
EOF

# 4. 安裝依賴（如果需要）
echo "📦 檢查依賴..."
if [ ! -d "node_modules" ]; then
    echo "安裝依賴..."
    npm install --quiet
fi

# 5. 建構
echo "🔨 建構生產版本..."
npm run build

# 6. 上傳到 S3
echo "📤 上傳到 S3..."
aws s3 sync dist/ s3://$BUCKET_NAME/ --delete --quiet

# 設置 cache control（除了 index.html）
aws s3 cp dist/ s3://$BUCKET_NAME/ \
  --recursive \
  --cache-control "public, max-age=31536000" \
  --exclude "index.html" \
  --exclude "*.map" \
  --quiet

# index.html 不要 cache
aws s3 cp dist/index.html s3://$BUCKET_NAME/ \
  --cache-control "no-cache, must-revalidate" \
  --quiet

echo "✅ 上傳完成"

# 7. Invalidate CloudFront cache
echo "🔄 清除 CloudFront cache..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)

echo "Invalidation ID: $INVALIDATION_ID"
echo "⏳ CloudFront cache 清除中（需要 1-2 分鐘生效）..."

echo ""
echo "✅ 前端更新完成！"
echo ""
echo "📋 訪問資訊："
echo "Frontend URL: $FRONTEND_URL"
echo ""
echo "💡 提示："
echo "- CloudFront cache 清除需要 1-2 分鐘"
echo "- 可以強制重新整理瀏覽器（Ctrl+Shift+R）"
echo "- 或等待 CloudFront 自動更新"
