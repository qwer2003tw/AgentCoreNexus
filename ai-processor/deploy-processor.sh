#!/bin/bash
# AgentCore AI Processor 自動化部署腳本
# 使用 SSM Parameter Store 和 ImportValue 實現完全自動化

set -e

echo "🚀 AgentCore AI Processor 部署腳本"
echo "=================================="
echo ""

# 1. 檢查 SSM Parameter 是否存在
echo "📋 檢查 Memory ID SSM Parameter..."
MEMORY_ID=$(aws ssm get-parameter \
  --region us-west-2 \
  --name /agentcore/memory/telegram-bot \
  --query 'Parameter.Value' \
  --output text 2>/dev/null || echo "")

if [ -z "$MEMORY_ID" ]; then
    echo "⚠️  SSM Parameter 不存在，正在設置..."
    
    # 從文件讀取
    if [ -f MEMORY_ID.txt ]; then
        MEMORY_ID=$(cat MEMORY_ID.txt)
        echo "✅ 從 MEMORY_ID.txt 讀取: $MEMORY_ID"
    else
        echo "❌ ERROR: MEMORY_ID.txt 不存在！"
        echo ""
        echo "請先創建 Memory："
        echo "  cd ai-processor"
        echo "  python create_memory.py"
        exit 1
    fi
    
    # 存到 SSM
    aws ssm put-parameter \
      --region us-west-2 \
      --name /agentcore/memory/telegram-bot \
      --value "$MEMORY_ID" \
      --type String \
      --description "Bedrock AgentCore Memory ID for Telegram Bot" \
      --overwrite > /dev/null
    
    echo "✅ Memory ID 已存到 SSM Parameter Store"
else
    echo "✅ Memory ID 已存在於 SSM: $MEMORY_ID"
fi

# 2. 驗證 Telegram Stack 是否存在
echo ""
echo "📋 檢查 Telegram Adapter Stack..."
TELEGRAM_STACK=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-telegram-adapter \
  --query 'Stacks[0].StackStatus' \
  --output text 2>/dev/null || echo "")

if [ -z "$TELEGRAM_STACK" ]; then
    echo "❌ ERROR: agentcore-telegram-adapter Stack 不存在！"
    echo ""
    echo "請先部署 Telegram Adapter Stack："
    echo "  cd telegram-adapter"
    echo "  sam build && sam deploy ..."
    exit 1
fi

if [[ "$TELEGRAM_STACK" != *"COMPLETE" ]]; then
    echo "⚠️  WARNING: Telegram Stack 狀態: $TELEGRAM_STACK"
    echo "請確保 Stack 部署完成後再繼續"
    exit 1
fi

echo "✅ Telegram Stack 狀態: $TELEGRAM_STACK"

# 3. Build
echo ""
echo "🔨 Building..."
sam build

if [ $? -ne 0 ]; then
    echo "❌ Build 失敗！"
    exit 1
fi

echo "✅ Build 完成"

# 4. 部署
echo ""
echo "🚀 部署中..."
sam deploy \
  --stack-name agentcore-ai-processor \
  --region us-west-2 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset \
  --parameter-overrides \
    BedrockAgentCoreMemoryId=/agentcore/memory/telegram-bot

if [ $? -ne 0 ]; then
    echo "❌ 部署失敗！"
    exit 1
fi

# 5. 等待 Lambda 更新完成
echo ""
echo "⏳ 等待 Lambda 更新完成..."
aws lambda wait function-updated \
  --region us-west-2 \
  --function-name agentcore-ai-processor-main

# 6. 驗證環境變數
echo ""
echo "✅ 部署完成！驗證環境變數..."

ENV_VARS=$(aws lambda get-function-configuration \
  --region us-west-2 \
  --function-name agentcore-ai-processor-main \
  --query 'Environment.Variables' \
  --output json)

EVENT_BUS=$(echo "$ENV_VARS" | jq -r '.EVENT_BUS_NAME')
MEMORY=$(echo "$ENV_VARS" | jq -r '.BEDROCK_AGENTCORE_MEMORY_ID')
FILE_BUCKET=$(echo "$ENV_VARS" | jq -r '.FILE_STORAGE_BUCKET')

echo ""
echo "📊 環境變數配置："
echo "  EVENT_BUS_NAME: $EVENT_BUS"
echo "  MEMORY_ID: $MEMORY"
echo "  FILE_BUCKET: $FILE_BUCKET"
echo ""

# 7. 驗證配置正確性
ERRORS=0

if [ "$EVENT_BUS" != "agentcore-telegram-adapter-events" ]; then
    echo "❌ ERROR: EVENT_BUS_NAME 不正確"
    ERRORS=$((ERRORS + 1))
fi

if [ -z "$MEMORY" ] || [ "$MEMORY" = "null" ]; then
    echo "❌ ERROR: MEMORY_ID 為空"
    ERRORS=$((ERRORS + 1))
fi

if [ -z "$FILE_BUCKET" ] || [ "$FILE_BUCKET" = "null" ]; then
    echo "❌ ERROR: FILE_BUCKET 為空"
    ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -eq 0 ]; then
    echo "🎉 部署成功！所有環境變數正確配置。"
    echo ""
    echo "📱 下一步："
    echo "1. 在 Telegram 發送測試消息"
    echo "2. 檢查 Bot 是否在 5-10 秒內回覆"
    echo ""
    echo "如需查看日誌："
    echo "  aws logs tail /aws/lambda/agentcore-ai-processor-main --region us-west-2 --follow"
else
    echo ""
    echo "⚠️  警告：發現 $ERRORS 個配置錯誤！"
    echo "請檢查並手動修復。"
    exit 1
fi