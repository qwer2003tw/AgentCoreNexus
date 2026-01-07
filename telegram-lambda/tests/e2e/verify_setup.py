#!/usr/bin/env python3
"""
驗證 E2E 測試環境設置
運行此腳本以確保所有依賴都已正確安裝
"""

import sys
from importlib import import_module

# 必須的依賴列表
REQUIRED_PACKAGES = [
    ("pytest", "pytest"),
    ("pytest_asyncio", "pytest-asyncio"),
    ("pytest_mock", "pytest-mock"),
    ("pytest_cov", "pytest-cov"),
    ("aiogram", "aiogram"),
    ("moto", "moto"),
    ("boto3", "boto3"),
    ("telegram", "python-telegram-bot"),
]


def check_package(module_name: str, package_name: str) -> bool:
    """檢查套件是否已安裝"""
    try:
        mod = import_module(module_name)
        version = getattr(mod, "__version__", "unknown")
        print(f"✅ {package_name:25s} {version}")
        return True
    except ImportError:
        print(f"❌ {package_name:25s} 未安裝")
        return False


def check_test_files() -> bool:
    """檢查測試文件是否存在"""
    from pathlib import Path

    test_dir = Path(__file__).parent
    required_files = [
        "conftest.py",
        "test_commands.py",
        "test_message_flow.py",
        "helpers/telegram_factory.py",
        "helpers/aws_mocks.py",
    ]

    print("\n📁 檢查測試文件...")
    all_exist = True
    for file in required_files:
        file_path = test_dir / file
        if file_path.exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} 不存在")
            all_exist = False

    return all_exist


def main():
    print("🔍 驗證 E2E 測試環境設置\n")
    print("=" * 50)

    # 檢查 Python 版本
    print(f"\n🐍 Python 版本: {sys.version.split()[0]}")
    # Python 3.9+ 是當前最低要求

    # 檢查套件
    print("\n📦 檢查依賴套件...")
    missing_packages = []
    for module_name, package_name in REQUIRED_PACKAGES:
        if not check_package(module_name, package_name):
            missing_packages.append(package_name)

    # 檢查測試文件
    files_ok = check_test_files()

    # 總結
    print("\n" + "=" * 50)
    if missing_packages:
        print(f"\n❌ 缺少 {len(missing_packages)} 個套件:")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        print("\n安裝方法:")
        print("   pip install -r requirements-test.txt")
        return 1
    elif not files_ok:
        print("\n❌ 測試文件不完整")
        return 1
    else:
        print("\n✅ 環境設置完成！可以開始測試了。")
        print("\n快速開始:")
        print("   pytest tests/e2e/ -v")
        print("   pytest tests/e2e/ --cov=src")
        print("\n或使用腳本:")
        print("   ./run_e2e_tests.sh")
        return 0


if __name__ == "__main__":
    sys.exit(main())
