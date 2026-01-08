#!/bin/bash
# Setup Git Hooks for AgentCoreNexus
#
# 此腳本會自動安裝 pre-commit hook
# Pre-commit hook 強制執行 clinerules 中定義的所有質量檢查

set -e

echo "🔧 設置 Git Hooks..."
echo ""

# 檢查是否在 Git 倉庫中
if [ ! -d ".git" ]; then
    echo "❌ 錯誤：不在 Git 倉庫根目錄中"
    echo "   請在專案根目錄執行此腳本"
    exit 1
fi

# 檢查 hook 源文件是否存在
if [ ! -f ".clinerules/hooks/pre-commit" ]; then
    echo "❌ 錯誤：找不到 .clinerules/hooks/pre-commit"
    exit 1
fi

# 複製 pre-commit hook
echo "📋 安裝 pre-commit hook..."
cp .clinerules/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

echo "✅ Pre-commit hook 已安裝"
echo ""

# 顯示 hook 功能說明
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Pre-commit Hook 功能"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "此 hook 會在每次 commit 前自動執行："
echo ""
echo "1. 🔍 Ruff 代碼質量檢查（自動修復 + 格式化）"
echo "2. 🧪 單元測試（pytest）"
echo "3. 🎭 E2E 測試（如果已安裝依賴）"
echo "4. 📊 覆蓋率檢查（新代碼 ≥ 80%）"
echo ""
echo "預計執行時間：2-5 分鐘"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 檢查測試依賴
echo "🔍 檢查測試環境..."
if command -v python3.11 &> /dev/null; then
    echo "✅ Python 3.11 已安裝"
else
    echo "⚠️  未找到 python3.11，測試可能失敗"
fi

if command -v ruff &> /dev/null; then
    echo "✅ Ruff 已安裝"
else
    echo "⚠️  未找到 ruff，請安裝：pip install ruff"
fi

if command -v pytest &> /dev/null; then
    echo "✅ Pytest 已安裝"
else
    echo "⚠️  未找到 pytest，請安裝：pip install pytest pytest-cov"
fi

if command -v diff-cover &> /dev/null; then
    echo "✅ diff-cover 已安裝（可選）"
else
    echo "ℹ️  diff-cover 未安裝（可選）"
    echo "   安裝以啟用新代碼覆蓋率檢查：pip install diff-cover"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Git Hooks 設置完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 提示："
echo "   - Pre-commit hook 會在每次 commit 前自動運行"
echo "   - 如遇緊急情況需要跳過，使用：git commit --no-verify"
echo "   - 但建議始終讓 hook 執行，確保代碼質量"
echo ""