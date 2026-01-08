#!/bin/bash
# Backend 部署腳本

set -e

echo "🚀 開始部署 Web Channel Backend..."

# 定位到專案根目錄
cd "$(dirname "$0")/.."

# 1. 安裝 Lambda 依賴
echo "📦 安裝 Lambda 依賴..."

cd lambdas/websocket
pip3.11 install -r requirements.txt -t . --quiet
cd ../..

cd lambdas/rest
pip3.11 install -r requirements.txt -t . --quiet
cd ../..

cd lambdas/router
pip3.11 install -r requirements.txt -t . --quiet
cd ../..

# 2. 驗證 template
echo "✅ 驗證 SAM template..."
cd infrastructure
sam validate -t web-channel-template.yaml

# 3. 建構
echo "🔨 建構 Lambda 函數..."
sam build -t web-channel-template.yaml

# 4. 部署
echo "🚀 部署到 AWS..."
sam deploy \
  --template-file web-channel-template.yaml \
  --stack-name agentcore-web-channel \
  --region us-west-2 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --parameter-overrides \
    Environment=dev \
    ExistingEventBusName=telegram-lambda-receiver-events \
    ExistingProcessorFunctionName=telegram-unified-bot-processor \
  --no-confirm-changeset

# 5. 驗證部署
echo "🔍 驗證部署..."
STACK_STATUS=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].StackStatus' \
  --output text)

if [ "$STACK_STATUS" == "CREATE_COMPLETE" ] || [ "$STACK_STATUS" == "UPDATE_COMPLETE" ]; then
    echo "✅ 部署成功！"
    
    # 顯示 outputs
    echo ""
    echo "📋 Stack Outputs:"
    aws cloudformation describe-stacks \
      --region us-west-2 \
      --stack-name agentcore-web-channel \
      --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
      --output table
    
    # 保存 outputs 到文件
    aws cloudformation describe-stacks \
      --region us-west-2 \
      --stack-name agentcore-web-channel \
      --query 'Stacks[0].Outputs' > ../outputs.json
    
    echo ""
    echo "✅ Outputs 已保存到 outputs.json"
else
    echo "❌ 部署失敗，狀態: $STACK_STATUS"
    exit 1
fi

echo ""
echo "🎉 Backend 部署完成！"
echo ""
echo "下一步："
echo "1. 運行 ./scripts/deploy-frontend.sh 部署前端"
echo "2. 運行 ./scripts/create-admin-user.sh <email> 創建管理員帳號"