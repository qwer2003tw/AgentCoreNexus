#!/bin/bash
# 創建 E2E 測試帳號腳本

set -e

# 顏色輸出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🚀 創建 E2E 測試帳號"
echo "========================="
echo ""

# 檢查環境變數
if [ -z "$ADMIN_TOKEN" ]; then
  echo -e "${RED}❌ 錯誤：ADMIN_TOKEN 環境變數未設置${NC}"
  echo ""
  echo "使用方式："
  echo "  1. 先登入獲取 admin token："
  echo "     ADMIN_TOKEN=\$(curl -X POST https://dr614rh1s6.execute-api.us-west-2.amazonaws.com/prod/auth/login \\"
  echo "       -H 'Content-Type: application/json' \\"
  echo "       -d '{\"email\":\"admin@example.com\",\"password\":\"YourAdminPassword\"}' | jq -r .token)"
  echo ""
  echo "  2. 然後執行此腳本："
  echo "     ADMIN_TOKEN=\$ADMIN_TOKEN ./create-test-accounts.sh"
  exit 1
fi

API_ENDPOINT="https://dr614rh1s6.execute-api.us-west-2.amazonaws.com/prod"

echo "API Endpoint: $API_ENDPOINT"
echo "測試帳號數量: 4"
echo ""

# 創建 4 個測試帳號
for i in {1..4}; do
  EMAIL="test${i}@test.com"
  echo -e "${YELLOW}📝 創建帳號 ${i}/4: $EMAIL${NC}"
  
  # 調用 createUser API
  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_ENDPOINT/admin/users" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d "{
      \"email\": \"$EMAIL\",
      \"role\": \"user\"
    }")
  
  HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
  BODY=$(echo "$RESPONSE" | sed '$d')
  
  if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
    TEMP_PASSWORD=$(echo "$BODY" | jq -r .temporary_password)
    echo -e "${GREEN}✅ 帳號創建成功${NC}"
    echo "   臨時密碼: $TEMP_PASSWORD"
    
    # 登入並修改為永久密碼
    echo "   🔄 設置永久密碼..."
    
    # 先用臨時密碼登入
    LOGIN_RESPONSE=$(curl -s -X POST "$API_ENDPOINT/auth/login" \
      -H "Content-Type: application/json" \
      -d "{
        \"email\": \"$EMAIL\",
        \"password\": \"$TEMP_PASSWORD\"
      }")
    
    TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r .token)
    
    if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
      # 修改密碼為 Test123!
      PASSWORD_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_ENDPOINT/auth/change-password" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d "{
          \"old_password\": \"$TEMP_PASSWORD\",
          \"new_password\": \"Test123!\"
        }")
      
      PW_HTTP_CODE=$(echo "$PASSWORD_RESPONSE" | tail -n1)
      
      if [ "$PW_HTTP_CODE" -eq 200 ]; then
        echo -e "${GREEN}   ✅ 密碼設置成功: Test123!${NC}"
      else
        echo -e "${RED}   ❌ 密碼設置失敗${NC}"
        echo "$PASSWORD_RESPONSE" | sed '$d'
      fi
    else
      echo -e "${RED}   ❌ 登入失敗，無法設置密碼${NC}"
    fi
    
  elif [ "$HTTP_CODE" -eq 409 ]; then
    echo -e "${YELLOW}⚠️  帳號已存在，跳過${NC}"
  else
    echo -e "${RED}❌ 創建失敗 (HTTP $HTTP_CODE)${NC}"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
  fi
  
  echo ""
done

echo "========================="
echo -e "${GREEN}🎉 測試帳號創建完成！${NC}"
echo ""
echo "測試帳號列表："
for i in {1..4}; do
  echo "  - test${i}@test.com / Test123!"
done
echo ""
echo "下一步："
echo "  1. 驗證帳號可以登入"
echo "  2. 設置 GitHub Secrets"
echo "  3. Push 並測試"