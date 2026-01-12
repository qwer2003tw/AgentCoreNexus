#!/bin/bash
# AgentCoreNexus 完整測試套件
# 執行所有三個組件的測試
#
# 用法:
#   ./run_all_tests.sh              # 完整測試
#   ./run_all_tests.sh --quick      # 快速測試（跳過 web-channel）
#   ./run_all_tests.sh --help       # 顯示幫助

set -e  # 遇到錯誤立即退出

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 時間追蹤
START_TIME=$(date +%s)

# 錯誤計數
ERRORS=0

# 模式設定
QUICK_MODE=false

# 解析命令行參數
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        -h|--help)
            echo "AgentCoreNexus 測試套件"
            echo ""
            echo "用法: $0 [選項]"
            echo ""
            echo "選項:"
            echo "  --quick       快速模式（跳過 web-channel E2E 測試）"
            echo "  -h, --help    顯示此幫助訊息"
            echo ""
            echo "範例:"
            echo "  $0              # 完整測試（推薦）"
            echo "  $0 --quick      # 快速測試"
            exit 0
            ;;
        *)
            echo -e "${RED}未知選項: $1${NC}"
            echo "使用 --help 查看幫助"
            exit 1
            ;;
    esac
done

# 錯誤處理函數
handle_error() {
    local component=$1
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ $component 測試失敗${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    ERRORS=$((ERRORS + 1))
    return 1
}

# 成功處理函數
handle_success() {
    local component=$1
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ $component 測試通過${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# 顯示標題
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  AgentCoreNexus 完整測試套件              ║${NC}"
echo -e "${BLUE}║  Testing all components...                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

if [ "$QUICK_MODE" = true ]; then
    echo -e "${CYAN}ℹ️  快速模式：跳過 web-channel E2E 測試${NC}"
    echo ""
fi

# ========================================
# 測試組件 1/3: telegram-agentcore-bot
# ========================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🤖 [1/3] telegram-agentcore-bot (AI 處理器)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ ! -d "telegram-agentcore-bot" ]; then
    echo -e "${RED}錯誤: 找不到 telegram-agentcore-bot 目錄${NC}"
    handle_error "telegram-agentcore-bot"
else
    cd telegram-agentcore-bot || exit 1
    
    if [ -f "run_tests.py" ]; then
        echo "執行 unittest 測試..."
        if python3.11 run_tests.py; then
            handle_success "telegram-agentcore-bot"
        else
            handle_error "telegram-agentcore-bot"
        fi
    else
        echo -e "${RED}錯誤: 找不到 run_tests.py${NC}"
        handle_error "telegram-agentcore-bot"
    fi
    
    cd ..
fi

echo ""

# ========================================
# 測試組件 2/3: telegram-lambda
# ========================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📱 [2/3] telegram-lambda (Webhook 接收器)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ ! -d "telegram-lambda" ]; then
    echo -e "${RED}錯誤: 找不到 telegram-lambda 目錄${NC}"
    handle_error "telegram-lambda"
else
    cd telegram-lambda || exit 1
    
    # 檢查測試腳本
    if [ -f "run_all_tests.sh" ]; then
        # 給腳本執行權限
        chmod +x run_all_tests.sh
        
        echo "執行完整測試（Ruff + Unit + E2E + Coverage）..."
        if ./run_all_tests.sh --cov; then
            handle_success "telegram-lambda"
        else
            handle_error "telegram-lambda"
        fi
    else
        echo -e "${YELLOW}⚠️  未找到 run_all_tests.sh，使用 pytest...${NC}"
        if python3.11 -m pytest tests/ -v; then
            handle_success "telegram-lambda"
        else
            handle_error "telegram-lambda"
        fi
    fi
    
    cd ..
fi

echo ""

# ========================================
# 測試組件 3/3: web-channel
# ========================================
if [ "$QUICK_MODE" = true ]; then
    echo -e "${CYAN}⏭️  跳過 web-channel（快速模式）${NC}"
else
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}🌐 [3/3] web-channel (Web 前端)${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    if [ ! -d "web-channel/e2e-tests" ]; then
        echo -e "${YELLOW}⚠️  找不到 web-channel/e2e-tests 目錄${NC}"
        echo -e "${YELLOW}   跳過 web-channel 測試${NC}"
    else
        cd web-channel/e2e-tests || exit 1
        
        # 檢查 Node.js 是否安裝
        if ! command -v npm &> /dev/null; then
            echo -e "${YELLOW}⚠️  npm 未安裝，跳過 web-channel 測試${NC}"
            cd ../..
        else
            # 檢查依賴
            if [ ! -d "node_modules" ]; then
                echo "安裝 Node.js 依賴..."
                npm install --silent
            fi
            
            # 檢查 Playwright 瀏覽器
            if ! npx playwright --version &> /dev/null; then
                echo "安裝 Playwright 瀏覽器..."
                npx playwright install --with-deps
            fi
            
            echo "執行 Playwright E2E 測試..."
            if npm test; then
                handle_success "web-channel"
            else
                handle_error "web-channel"
            fi
            
            cd ../..
        fi
    fi
fi

echo ""

# ========================================
# 總結報告
# ========================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           測試完成摘要                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "執行時間: ${CYAN}${MINUTES}${NC} 分 ${CYAN}${SECONDS}${NC} 秒"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ 所有測試通過！                        ║${NC}"
    echo -e "${GREEN}║  專案處於健康狀態，可以安全部署            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ❌ 發現 $ERRORS 個組件測試失敗           ║${NC}"
    echo -e "${RED}║  請修復後再提交代碼                        ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════╝${NC}"
    echo ""
    exit 1
fi