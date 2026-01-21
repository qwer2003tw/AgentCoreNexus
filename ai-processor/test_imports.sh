#!/bin/bash
set -e

echo "📋 測試 Processor Lambda 導入..."

echo "1. 測試 processor_entry.py..."
python3 -c "import processor_entry" && echo "  ✅ processor_entry.py"

echo "2. 測試 file_service.py..."
python3 -c "from services.file_service import file_service" && echo "  ✅ file_service.py"

echo "3. 測試 audit.py..."
python3 -c "from utils.audit import audit_log" && echo "  ✅ audit_log 存在"

echo "4. 測試所有工具..."
python3 -c "from tools import AVAILABLE_TOOLS" && echo "  ✅ 所有工具"

echo "✅ 所有導入測試通過"
