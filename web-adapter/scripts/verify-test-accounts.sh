#!/bin/bash
# 驗證測試帳號腳本

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

API_ENDPOINT="https://dr614rh1s6.execute-api.us-west-2.amazonaws.com/prod"

echo "🔍 驗證測試帳號"
echo "========================="
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

# 測試 4 個帳號
for i in {1..4}; do
  EMAIL="test${i}@test.com"
  PASSWORD="Test123!"
  
  echo -e "${YELLOW}測試 ${i}/4: $EMAIL${NC}"
  
  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_ENDPOINT/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"$EMAIL\",
      \"password\": \"$PASSWORD\"
    }")
  
  HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
  BODY=$(echo "$RESPONSE" | sed '$d')
  
  if [ "$HTTP_CODE" -eq 200 ]; then
    TOKEN=$(echo "$BODY" | jq -r .token)
    USER_ID=$(echo "$BODY" | jq -r .user.email)
    
    if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
      echo -e "${GREEN}✅ 登入成功${NC}"
      echo "   Token: ${TOKEN:0:20}..."
      echo "   User: $USER_ID"
      SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
      echo -e "${RED}❌ 登入失敗：無 token${NC}"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  else
    echo -e "${RED}❌ 登入失敗 (HTTP $HTTP_CODE)${NC}"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
  
  echo ""
done

echo "========================="
echo "驗證結果："
echo -e "  ${GREEN}成功: $SUCCESS_COUNT${NC}"
echo -e "  ${RED}失敗: $FAIL_COUNT${NC}"
echo ""

if [ $SUCCESS_COUNT -eq 4 ]; then
  echo -e "${GREEN}🎉 所有測試帳號都可以正常登入！${NC}"
  echo ""
  echo "✅ 已準備好設置 GitHub Secrets"
  echo ""
  echo "下一步："
  echo "  1. 前往 GitHub Repository Settings → Secrets"
  echo "  2. 設置 10 個 secrets（參考 GITHUB_SECRETS_SETUP.md）"
  echo "  3. git push 觸發測試"
  exit 0
else
  echo -e "${RED}❌ 有帳號登入失敗，請檢查${NC}"
  echo ""
  echo "可能原因："
  echo "  - 帳號尚未創建"
  echo "  - 密碼不正確"
  echo "  - API endpoint 無法訪問"
  exit 1
fi