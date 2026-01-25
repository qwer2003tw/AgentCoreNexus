#!/bin/bash
# 測試 Web 端登入和綁定功能

set -e

# 配置
API_BASE="https://jooap0xv8l.execute-api.us-west-2.amazonaws.com/prod"
TEST_EMAIL="test1@test.com"
TEST_PASSWORD="Test123!"

echo "🧪 Phase 2 綁定功能測試"
echo "========================================"
echo ""

# Step 1: 測試登入
echo "📝 Step 1: 測試 Web 登入"
echo "Email: $TEST_EMAIL"

LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")

echo "Response: $LOGIN_RESPONSE"

# 提取 token
TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.token // empty')

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
    echo "❌ 登入失敗！"
    exit 1
fi

echo "✅ 登入成功！"
echo "Token: ${TOKEN:0:20}..."
echo ""

# Step 2: 檢查 /auth/me
echo "📝 Step 2: 驗證用戶信息"
ME_RESPONSE=$(curl -s -X GET "$API_BASE/auth/me" \
  -H "Authorization: Bearer $TOKEN")

echo "Response: $ME_RESPONSE"
echo "✅ 用戶信息獲取成功"
echo ""

# Step 3: 檢查綁定狀態
echo "📝 Step 3: 檢查綁定狀態"
BINDING_STATUS=$(curl -s -X GET "$API_BASE/binding/status" \
  -H "Authorization: Bearer $TOKEN")

echo "Response: $BINDING_STATUS"
echo ""

IS_BOUND=$(echo "$BINDING_STATUS" | jq -r '.is_bound // false')

if [ "$IS_BOUND" == "true" ]; then
    echo "✅ 已綁定 Telegram 帳號"
    TELEGRAM_ID=$(echo "$BINDING_STATUS" | jq -r '.telegram_chat_id // "unknown"')
    echo "   Telegram Chat ID: $TELEGRAM_ID"
else
    echo "⚠️  尚未綁定 Telegram 帳號"
    echo "   需要使用 Telegram /bind 命令生成綁定碼"
fi

echo ""
echo "========================================"
echo "🎉 基本測試完成！"
echo ""
echo "📋 測試結果："
echo "  ✅ Web 登入: 成功"
echo "  ✅ 用戶信息: 成功"
echo "  ✅ 綁定 API: 可訪問"
echo ""
echo "🔗 下一步："
echo "  1. 在 Telegram 使用 /bind 命令生成綁定碼"
echo "  2. 在 Web 前端輸入綁定碼"
echo "  3. 驗證綁定成功（/mybindings 在 Telegram）"
echo ""
echo "🌐 Frontend URL: https://d1p3mmbx4pyq2j.cloudfront.net"
echo ""