#!/bin/bash
# 創建 Admin 用戶腳本

set -e

# 檢查參數
if [ -z "$1" ]; then
    echo "用法: $0 <email> [password]"
    echo "範例: $0 admin@example.com MyPassword123"
    exit 1
fi

EMAIL=$1
PASSWORD=${2:-"Admin123!"}

echo "👤 創建 Admin 用戶..."
echo "Email: $EMAIL"

# 獲取 table 名稱
echo "🔍 獲取 DynamoDB table 名稱..."
WEB_USERS_TABLE=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-channel \
  --query 'Stacks[0].Outputs[?OutputKey==`WebUsersTableName`].OutputValue' \
  --output text)

if [ -z "$WEB_USERS_TABLE" ]; then
    echo "❌ 找不到 web_users table"
    echo "請確認 backend 已部署"
    exit 1
fi

echo "Table: $WEB_USERS_TABLE"

# 檢查用戶是否已存在
echo "🔍 檢查用戶是否已存在..."
EXISTING=$(aws dynamodb get-item \
  --region us-west-2 \
  --table-name $WEB_USERS_TABLE \
  --key "{\"email\":{\"S\":\"$EMAIL\"}}" \
  --query 'Item' \
  --output text)

if [ ! -z "$EXISTING" ] && [ "$EXISTING" != "None" ]; then
    echo "⚠️  用戶已存在: $EMAIL"
    echo "如需重置密碼，請使用 Admin API"
    exit 1
fi

# 生成密碼 hash
echo "🔐 生成密碼 hash..."
ADMIN_HASH=$(python3 << EOF
import bcrypt
password = '$PASSWORD'
hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))
print(hash.decode('utf-8'))
EOF
)

# 創建用戶
echo "💾 創建用戶記錄..."
aws dynamodb put-item \
  --region us-west-2 \
  --table-name $WEB_USERS_TABLE \
  --item "{
    \"email\": {\"S\": \"$EMAIL\"},
    \"password_hash\": {\"S\": \"$ADMIN_HASH\"},
    \"enabled\": {\"BOOL\": true},
    \"role\": {\"S\": \"admin\"},
    \"require_password_change\": {\"BOOL\": false},
    \"created_at\": {\"S\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}
  }"

echo ""
echo "✅ Admin 用戶創建成功！"
echo ""
echo "📋 登入資訊："
echo "Email: $EMAIL"
echo "Password: $PASSWORD"
echo ""
echo "⚠️  請妥善保管此資訊！"
echo ""
echo "下一步："
echo "1. 打開前端 URL（查看 frontend-config.json）"
echo "2. 使用上述資訊登入"
echo "3. 在設定中可創建其他用戶"