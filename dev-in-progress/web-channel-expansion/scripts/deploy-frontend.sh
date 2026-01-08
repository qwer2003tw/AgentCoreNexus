#!/bin/bash
# Frontend 部署腳本

set -e

echo "🚀 開始部署 Web Channel Frontend..."

# 定位到專案根目錄
cd "$(dirname "$0")/.."

# 1. 檢查 backend 是否已部署
echo "🔍 檢查 backend 部署狀態..."
if ! aws cloudformation describe-stacks --region us-west-2 --stack-name agentcore-web-channel &>/dev/null; then
    echo "❌ Backend 尚未部署！"
    echo "請先運行: ./scripts/deploy-backend.sh"
    exit 1
fi

# 2. 獲取 API endpoints
echo "📡 獲取 API endpoints..."
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

echo "REST API: $REST_API"
echo "WebSocket API: $WS_API"

# 3. 配置環境變數
echo "⚙️  配置環境變數..."
cd frontend
cat > .env << EOF
VITE_API_ENDPOINT=$REST_API
VITE_WS_ENDPOINT=$WS_API
VITE_DEBUG=false
EOF

# 4. 安裝依賴
echo "📦 安裝依賴..."
npm install --quiet

# 5. 建構
echo "🔨 建構生產版本..."
npm run build

# 6. 創建 S3 bucket
echo "🪣 創建 S3 bucket..."
BUCKET_NAME="agentcore-web-frontend-$(date +%s)"

aws s3 mb s3://$BUCKET_NAME --region us-west-2

# 配置為靜態網站
aws s3 website s3://$BUCKET_NAME \
  --index-document index.html \
  --error-document index.html

# 設置公開讀取權限
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy "$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
  }]
}
EOF
)"

# 7. 上傳前端
echo "📤 上傳到 S3..."
aws s3 sync dist/ s3://$BUCKET_NAME/ --delete --quiet

# 設置 cache control
aws s3 cp dist/ s3://$BUCKET_NAME/ \
  --recursive \
  --cache-control "public, max-age=31536000" \
  --exclude "index.html" \
  --quiet

# index.html 不要 cache
aws s3 cp dist/index.html s3://$BUCKET_NAME/ \
  --cache-control "no-cache" \
  --quiet

# 8. 保存配置
cat > ../frontend-config.json << EOF
{
  "bucket_name": "$BUCKET_NAME",
  "frontend_url": "http://$BUCKET_NAME.s3-website-us-west-2.amazonaws.com",
  "rest_api": "$REST_API",
  "ws_api": "$WS_API"
}
EOF

echo ""
echo "✅ Frontend 部署完成！"
echo ""
echo "📋 訪問資訊："
echo "Frontend URL: http://$BUCKET_NAME.s3-website-us-west-2.amazonaws.com"
echo "REST API: $REST_API"
echo "WebSocket API: $WS_API"
echo ""
echo "配置已保存到 frontend-config.json"
echo ""
echo "下一步："
echo "運行 ./scripts/create-admin-user.sh <email> 創建管理員帳號"