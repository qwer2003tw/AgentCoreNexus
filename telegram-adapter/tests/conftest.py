"""
Pytest configuration file
配置測試環境的 Python 路徑
"""

import sys
from pathlib import Path

# 將 src 目錄加入 Python 路徑
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
