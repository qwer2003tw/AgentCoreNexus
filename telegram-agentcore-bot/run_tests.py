#!/usr/bin/env python3
"""
測試執行器腳本
執行所有單元測試並生成報告
"""
import unittest
import sys
import os
from io import StringIO

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_all_tests(verbosity=2):
    """
    執行所有測試
    
    Args:
        verbosity: 輸出詳細程度 (0=安靜, 1=正常, 2=詳細)
    
    Returns:
        TestResult 物件
    """
    # 建立測試套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 載入所有測試模組
    test_modules = [
        'tests.test_config',
        'tests.test_tools',
        'tests.test_services',
        'tests.test_agents'
    ]
    
    print("🧪 開始載入測試...")
    print("=" * 70)
    
    for module_name in test_modules:
        try:
            tests = loader.loadTestsFromName(module_name)
            suite.addTests(tests)
            print(f"✅ 載入: {module_name}")
        except Exception as e:
            print(f"❌ 載入失敗 {module_name}: {str(e)}")
    
    print("=" * 70)
    print(f"\n總共載入 {suite.countTestCases()} 個測試\n")
    
    # 執行測試
    print("🚀 開始執行測試...")
    print("=" * 70)
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # 輸出摘要
    print("\n" + "=" * 70)
    print("📊 測試摘要")
    print("=" * 70)
    print(f"執行測試數: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"錯誤: {len(result.errors)}")
    print(f"跳過: {len(result.skipped)}")
    
    # 計算成功率
    if result.testsRun > 0:
        success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
        print(f"成功率: {success_rate:.1f}%")
    
    print("=" * 70)
    
    # 顯示失敗和錯誤詳情
    if result.failures:
        print("\n❌ 失敗的測試:")
        print("-" * 70)
        for test, traceback in result.failures:
            print(f"\n{test}:")
            print(traceback)
    
    if result.errors:
        print("\n💥 錯誤的測試:")
        print("-" * 70)
        for test, traceback in result.errors:
            print(f"\n{test}:")
            print(traceback)
    
    return result


def run_specific_module(module_name, verbosity=2):
    """
    執行特定測試模組
    
    Args:
        module_name: 測試模組名稱 (例如: 'test_config')
        verbosity: 輸出詳細程度
    
    Returns:
        TestResult 物件
    """
    if not module_name.startswith('tests.'):
        module_name = f'tests.{module_name}'
    
    print(f"🧪 執行測試模組: {module_name}")
    print("=" * 70)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(module_name)
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    print(f"完成 - 執行: {result.testsRun}, 失敗: {len(result.failures)}, 錯誤: {len(result.errors)}")
    print("=" * 70)
    
    return result


def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='執行 Telegram AgentCore Bot 的單元測試',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python run_tests.py                    # 執行所有測試
  python run_tests.py -m test_config     # 執行特定模組
  python run_tests.py -v 1               # 較簡潔的輸出
  python run_tests.py -q                 # 安靜模式
        """
    )
    
    parser.add_argument(
        '-m', '--module',
        help='指定要執行的測試模組 (例如: test_config)',
        default=None
    )
    
    parser.add_argument(
        '-v', '--verbosity',
        type=int,
        choices=[0, 1, 2],
        default=2,
        help='輸出詳細程度: 0=安靜, 1=正常, 2=詳細 (預設: 2)'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='安靜模式 (等同於 -v 0)'
    )
    
    args = parser.parse_args()
    
    # 處理安靜模式
    verbosity = 0 if args.quiet else args.verbosity
    
    # 執行測試
    try:
        if args.module:
            result = run_specific_module(args.module, verbosity)
        else:
            result = run_all_tests(verbosity)
        
        # 根據測試結果設定退出碼
        if result.wasSuccessful():
            print("\n✅ 所有測試通過！")
            sys.exit(0)
        else:
            print("\n❌ 有測試失敗或出錯")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 執行測試時發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()
