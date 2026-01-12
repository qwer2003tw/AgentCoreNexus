#!/bin/bash

# E2E 快速測試腳本
# 用途：快速設置並執行本地 E2E 測試

set -e  # 遇到錯誤立即停止

echo "🚀 E2E 測試快速啟動腳本"
echo "================================"
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 檢查當前目錄
if [ ! -d "tests" ]; then
  echo -e "${RED}❌ 錯誤：請在 web-channel/e2e-tests 目錄下執行此腳本${NC}"
  echo "當前目錄：$(pwd)"
  exit 1
fi

echo -e "${BLUE}📍 步驟 1: 檢查環境${NC}"
echo "--------------------------------"

# 檢查 Node.js
if ! command -v node &> /dev/null; then
  echo -e "${RED}❌ Node.js 未安裝${NC}"
  exit 1
fi
NODE_VERSION=$(node --version)
echo -e "${GREEN}✅ Node.js: ${NODE_VERSION}${NC}"

# 檢查 npm
if ! command -v npm &> /dev/null; then
  echo -e "${RED}❌ npm 未安裝${NC}"
  exit 1
fi
NPM_VERSION=$(npm --version)
echo -e "${GREEN}✅ npm: ${NPM_VERSION}${NC}"

echo ""

# 檢查依賴
echo -e "${BLUE}📍 步驟 2: 檢查依賴${NC}"
echo "--------------------------------"

if [ ! -d "node_modules" ]; then
  echo -e "${YELLOW}⚠️  E2E 測試依賴未安裝，開始安裝...${NC}"
  npm install
  echo -e "${GREEN}✅ 依賴安裝完成${NC}"
else
  echo -e "${GREEN}✅ E2E 測試依賴已安裝${NC}"
fi

# 檢查前端依賴
if [ ! -d "../frontend/node_modules" ]; then
  echo -e "${YELLOW}⚠️  前端依賴未安裝，開始安裝...${NC}"
  cd ../frontend
  npm install
  cd ../e2e-tests
  echo -e "${GREEN}✅ 前端依賴安裝完成${NC}"
else
  echo -e "${GREEN}✅ 前端依賴已安裝${NC}"
fi

echo ""

# 檢查 Playwright 瀏覽器
echo -e "${BLUE}📍 步驟 3: 檢查 Playwright 瀏覽器${NC}"
echo "--------------------------------"

if ! npx playwright --version &> /dev/null; then
  echo -e "${YELLOW}⚠️  Playwright 瀏覽器未安裝，開始安裝...${NC}"
  npx playwright install --with-deps
  echo -e "${GREEN}✅ Playwright 瀏覽器安裝完成${NC}"
else
  echo -e "${GREEN}✅ Playwright 已安裝${NC}"
fi

echo ""

# 檢查環境變數
echo -e "${BLUE}📍 步驟 4: 檢查測試配置${NC}"
echo "--------------------------------"

# 檢查前端環境配置
if [ ! -f "../frontend/.env.local" ]; then
  echo -e "${YELLOW}⚠️  前端環境配置 (.env.local) 不存在${NC}"
  echo ""
  echo "請創建 web-channel/frontend/.env.local 文件："
  echo ""
  echo "VITE_API_ENDPOINT=https://your-api-endpoint.amazonaws.com"
  echo "VITE_WS_ENDPOINT=wss://your-ws-endpoint.amazonaws.com"
  echo ""
  echo -e "${RED}❌ 請先配置環境變數後再執行測試${NC}"
  exit 1
else
  echo -e "${GREEN}✅ 前端環境配置存在${NC}"
  echo "配置內容："
  cat ../frontend/.env.local | sed 's/^/  /'
fi

echo ""

# 檢查測試帳號環境變數
if [ -z "$TEST_USER_1_EMAIL" ]; then
  echo -e "${YELLOW}⚠️  測試帳號環境變數未設置${NC}"
  echo ""
  echo "請設置測試帳號："
  echo ""
  echo "export TEST_USER_1_EMAIL=test1@test.com"
  echo "export TEST_USER_1_PASSWORD=Test123!"
  echo ""
  
  # 詢問是否使用默認值
  read -p "是否使用默認測試帳號 (test1@test.com / Test123!)? [y/N] " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    export TEST_USER_1_EMAIL=test1@test.com
    export TEST_USER_1_PASSWORD=Test123!
    echo -e "${GREEN}✅ 使用默認測試帳號${NC}"
  else
    echo -e "${RED}❌ 請手動設置測試帳號後再執行${NC}"
    exit 1
  fi
else
  echo -e "${GREEN}✅ 測試帳號已配置: ${TEST_USER_1_EMAIL}${NC}"
fi

echo ""

# 選擇測試模式
echo -e "${BLUE}📍 步驟 5: 選擇測試模式${NC}"
echo "--------------------------------"
echo ""
echo "請選擇測試模式："
echo "  1) Headless 模式（快速，無 UI）"
echo "  2) Headed 模式（可見瀏覽器，推薦 Debug）"
echo "  3) UI 模式（互動式 Debug）"
echo "  4) 只測試 Auth（登入功能）"
echo "  5) Debug 模式（逐步執行）"
echo ""
read -p "請選擇 [1-5]: " -n 1 -r
echo ""

case $REPLY in
  1)
    echo -e "${GREEN}🚀 執行 Headless 測試${NC}"
    echo "================================"
    npm test
    ;;
  2)
    echo -e "${GREEN}🚀 執行 Headed 測試（可見瀏覽器）${NC}"
    echo "================================"
    npm test -- --headed
    ;;
  3)
    echo -e "${GREEN}🚀 啟動 UI 模式${NC}"
    echo "================================"
    npm run test:ui
    ;;
  4)
    echo -e "${GREEN}🚀 只測試 Auth（登入功能）${NC}"
    echo "================================"
    npm run test:auth
    ;;
  5)
    echo -e "${GREEN}🚀 Debug 模式${NC}"
    echo "================================"
    npm test -- --debug tests/auth.spec.ts
    ;;
  *)
    echo -e "${RED}❌ 無效選擇，默認執行 Headless 測試${NC}"
    npm test
    ;;
esac

# 測試完成
echo ""
echo "================================"
echo -e "${GREEN}✅ 測試執行完成${NC}"
echo ""
echo "查看詳細報告："
echo "  npm run test:report"
echo ""
echo "如果有失敗，查看截圖："
echo "  ls -la test-results/"
echo ""