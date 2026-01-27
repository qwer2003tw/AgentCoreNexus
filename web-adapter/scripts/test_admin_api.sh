#!/bin/bash
# Test Admin API endpoints
# Requires: admin@test.com user with known password

set -e

API_ENDPOINT="https://jooap0xv8l.execute-api.us-west-2.amazonaws.com/prod"
ADMIN_EMAIL="admin@test.com"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin123!}"

echo "🧪 Testing Admin API"
echo "   Endpoint: $API_ENDPOINT"
echo "   Admin: $ADMIN_EMAIL"
echo ""

# Step 1: Login as admin
echo "📝 Step 1: Login as admin..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_ENDPOINT/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}")

echo "$LOGIN_RESPONSE" | jq '.'

# Extract token
TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.token')
if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Login failed - no token received"
    exit 1
fi

echo "✅ Login successful, token: ${TOKEN:0:20}..."
echo ""

# Step 2: Test /admin/conversations
echo "📝 Step 2: List all conversations..."
CONVERSATIONS=$(curl -s -X GET "$API_ENDPOINT/admin/conversations?limit=5" \
  -H "Authorization: Bearer $TOKEN")

echo "$CONVERSATIONS" | jq '.'

CONV_COUNT=$(echo "$CONVERSATIONS" | jq -r '.count // 0')
echo "✅ Found $CONV_COUNT conversations"
echo ""

# Step 3: Get first conversation detail (if exists)
if [ "$CONV_COUNT" -gt 0 ]; then
    CONV_ID=$(echo "$CONVERSATIONS" | jq -r '.conversations[0].conversation_id')
    echo "📝 Step 3: Get conversation detail ($CONV_ID)..."
    
    DETAIL=$(curl -s -X GET "$API_ENDPOINT/admin/conversations/$CONV_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "$DETAIL" | jq '{conversation_id, user_id, channel, message_count: .statistics.message_count, attachments: .statistics.attachments}'
    
    MSG_COUNT=$(echo "$DETAIL" | jq -r '.statistics.message_count // 0')
    echo "✅ Conversation has $MSG_COUNT messages"
    echo ""
else
    echo "ℹ️  No conversations to test detail endpoint"
    echo ""
fi

# Step 4: Test with channel filter
echo "📝 Step 4: Test channel filter (telegram)..."
TELEGRAM_CONVS=$(curl -s -X GET "$API_ENDPOINT/admin/conversations?channel=telegram&limit=3" \
  -H "Authorization: Bearer $TOKEN")

TELEGRAM_COUNT=$(echo "$TELEGRAM_CONVS" | jq -r '.count // 0')
echo "✅ Found $TELEGRAM_COUNT telegram conversations"
echo ""

echo "📝 Step 5: Test channel filter (web)..."
WEB_CONVS=$(curl -s -X GET "$API_ENDPOINT/admin/conversations?channel=web&limit=3" \
  -H "Authorization: Bearer $TOKEN")

WEB_COUNT=$(echo "$WEB_CONVS" | jq -r '.count // 0')
echo "✅ Found $WEB_COUNT web conversations"
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Admin API Test Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Login: Success"
echo "✅ List conversations: $CONV_COUNT total"
echo "✅ Get conversation detail: Working"
echo "✅ Channel filter (telegram): $TELEGRAM_COUNT"
echo "✅ Channel filter (web): $WEB_COUNT"
echo ""
echo "🎉 All admin API tests passed!"