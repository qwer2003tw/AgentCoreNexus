#!/bin/bash
# 清理部署腳本（用於開發測試）

set -e

echo "🧹 開始清理 Web Channel 部署..."

# 1. 詢問確認
read -p "確定要刪除 Web Channel Stack 嗎？ (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ 取消清理"
    exit 0
fi

# 2. 獲取 frontend bucket 名稱（如果存在）
if [ -f "../frontend-config.json" ]; then
    BUCKET_NAME=$(cat ../frontend-config.json | grep bucket_name | cut -d'"' -f4)
    
    if [ ! -z "$BUCKET_NAME" ]; then
        echo "🪣 刪除 S3 bucket: $BUCKET_NAME"
        aws s3 rb s3://$BUCKET_NAME --force
    fi
fi

# 3. 刪除 CloudFormation stack
echo "🗑️  刪除 CloudFormation stack..."
aws cloudformation delete-stack \
  --region us-west-2 \
  --stack-name agentcore-web-channel

echo "⏳ 等待 stack 刪除..."
aws cloudformation wait stack-delete-complete \
  --region us-west-2 \
  --stack-name agentcore-web-channel

# 4. 清理本地檔案
echo "🧹 清理本地檔案..."
rm -f ../outputs.json
rm -f ../frontend-config.json

echo ""
echo "✅ 清理完成！"
echo ""
echo "如需重新部署，請運行："
echo "./scripts/deploy-backend.sh"