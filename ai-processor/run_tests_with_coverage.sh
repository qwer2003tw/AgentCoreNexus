#!/bin/bash
# telegram-agentcore-bot 測試 + 覆蓋率檢查
#
# 用法:
#   ./run_tests_with_coverage.sh        # 完整測試 + 覆蓋率
#   ./run_tests_with_coverage.sh -v     # 詳細輸出

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  telegram-agentcore-bot 測試套件${NC}"
echo -e "${GREEN}  Pytest + Coverage + Diff-Cover${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 檢查依賴
if ! python3.12 -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  pytest 未安裝，正在安裝測試依賴...${NC}"
    python3.12 -m pip install pytest pytest-cov pytest-asyncio coverage diff-cover
fi

# 解析參數
VERBOSE=""
if [[ "$1" == "-v" ]] || [[ "$1" == "--verbose" ]]; then
    VERBOSE="-v"
fi

# Step 1: 運行測試 + 覆蓋率
echo -e "${YELLOW}📊 Step 1: 運行測試並生成覆蓋率報告...${NC}"
echo ""

python3.12 -m pytest tests/ $VERBOSE \
    --cov=. \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=xml

PYTEST_EXIT=$?

if [ $PYTEST_EXIT -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ 測試失敗${NC}"
    exit 1
fi

echo ""

# Step 2: 檢查整體覆蓋率
echo -e "${YELLOW}📈 Step 2: 檢查整體覆蓋率...${NC}"

# 使用 coverage report 獲取總覆蓋率
COVERAGE=$(python3.12 -m coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')

echo -e "整體覆蓋率: ${CYAN}${COVERAGE}%${NC}"

if (( $(echo "$COVERAGE >= 70" | bc -l) )); then
    echo -e "${GREEN}✅ 達到目標（≥ 70%）${NC}"
else
    echo -e "${YELLOW}⚠️  低於目標 70%${NC}"
    echo -e "${YELLOW}   建議添加更多測試以提升覆蓋率${NC}"
fi

echo ""

# Step 3: 檢查新代碼覆蓋率（如果有 diff-cover）
if command -v diff-cover &> /dev/null; then
    echo -e "${YELLOW}🔍 Step 3: 檢查新代碼覆蓋率...${NC}"
    
    # 檢查是否在 git 倉庫中
    if git rev-parse --git-dir > /dev/null 2>&1; then
        # 檢查是否有 main 分支
        if git show-ref --verify --quiet refs/heads/main; then
            if diff-cover coverage.xml --compare-branch=main --fail-under=80 2>/dev/null; then
                echo -e "${GREEN}✅ 新代碼覆蓋率 ≥ 80%${NC}"
            else
                echo -e "${YELLOW}⚠️  新代碼覆蓋率 < 80%${NC}"
                echo -e "${YELLOW}   這是建議，不會阻止測試通過${NC}"
            fi
        else
            echo -e "${CYAN}ℹ️  main 分支不存在，跳過新代碼覆蓋率檢查${NC}"
        fi
    else
        echo -e "${CYAN}ℹ️  不在 git 倉庫中，跳過新代碼覆蓋率檢查${NC}"
    fi
else
    echo -e "${YELLOW}ℹ️  diff-cover 未安裝，跳過新代碼覆蓋率檢查${NC}"
    echo "   安裝: pip install diff-cover"
fi

echo ""
echo -e "${GREEN}✅ 測試完成！${NC}"
echo -e "${GREEN}📊 HTML 覆蓋率報告: ${CYAN}htmlcov/index.html${NC}"
echo -e "${GREEN}📄 XML 覆蓋率報告: ${CYAN}coverage.xml${NC}"
echo ""