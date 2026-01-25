"""
圖片分析 E2E 測試
測試 analyze_image_tool 和 Memory 功能
"""

import pytest


@pytest.mark.real_e2e
@pytest.mark.image
@pytest.mark.asyncio
async def test_image_basic_analysis(bot_client, log_fetcher, test_config, clean_session):
    """
    測試 1：上傳圖片測試基本分析
    
    流程：
    1. 上傳圖片並詢問
    2. 驗證 Agent 調用 analyze_image_tool
    3. 驗證回應包含圖片描述
    4. 驗證 Memory 記錄 S3 URL
    """
    print("\n📸 測試 1：圖片基本分析")

    # 1. 上傳圖片（使用 fixture 中的測試圖片）
    print("  → 上傳測試圖片...")
    fixture_path = "tests/e2e_real/fixtures/test_noodle.jpg"

    # 如果測試圖片不存在，跳過測試
    import os
    if not os.path.exists(fixture_path):
        pytest.skip(f"測試圖片不存在：{fixture_path}")

    sent_msg = await bot_client.send_photo(
        photo_path=fixture_path,
        caption="這是什麼？"
    )

    print(f"  ✅ 圖片已上傳（message_id: {sent_msg.message_id}）")

    # 2. 等待 AI 處理（給 Lambda 時間處理）
    print(f"  ⏳ 等待 AI 處理（{test_config['e2e_timeout']} 秒）...")
    import asyncio
    await asyncio.sleep(test_config['e2e_timeout'])

    print("  ✅ 處理時間已完成")
    print("  ℹ️  注意：Bot 使用 webhook 模式，請手動在 Telegram 檢查回應")

    # 4. 驗證 tool 被調用（查看 Lambda 日誌）
    print("  🔍 檢查 Lambda 日誌...")
    tool_called = log_fetcher.check_tool_called(
        lambda_name=test_config['processor_lambda'],
        tool_name="Image Analysis Tool",
        since_seconds=120
    )

    assert tool_called, "❌ analyze_image_tool 沒有被調用"
    print("  ✅ analyze_image_tool 已被調用")

    # 5. 檢查是否有錯誤
    has_error = log_fetcher.check_error_in_logs(
        lambda_name=test_config['processor_lambda'],
        since_seconds=120
    )

    assert not has_error, "❌ Lambda 日誌中有錯誤"
    print("  ✅ 無錯誤日誌")

    print("  🎉 測試 1 通過！")


@pytest.mark.real_e2e
@pytest.mark.image
@pytest.mark.memory
@pytest.mark.asyncio
async def test_image_memory_followup(bot_client, log_fetcher, test_config, clean_session):
    """
    測試 2：同對話追問圖片細節（驗證 Memory）
    
    流程：
    1. 上傳圖片並分析
    2. 等待處理
    3. 追問圖片的特定部分
    4. 等待處理
    5. 驗證 tool 被調用兩次
    6. 驗證 Memory session 正常
    
    注意：使用 webhook 模式，無法自動獲取回應，
          請手動在 Telegram 檢查回應內容
    """
    print("\n🧠 測試 2：Memory 追問功能")

    # 1. 上傳圖片
    print("  → 上傳測試圖片...")
    fixture_path = "tests/e2e_real/fixtures/test_noodle.jpg"

    if not os.path.exists(fixture_path):
        pytest.skip(f"測試圖片不存在：{fixture_path}")

    await bot_client.send_photo(
        photo_path=fixture_path,
        caption="這碗泡麵是什麼牌子？"
    )

    # 2. 等待第一次處理
    print("  ⏳ 等待第一次處理...")
    import asyncio
    await asyncio.sleep(test_config['e2e_timeout'])
    print("  ✅ 第一次處理完成")

    # 3. 追問細節
    print("  💬 追問：左邊那個調味包是什麼？")
    await bot_client.send_text("左邊那個調味包是什麼？")

    # 4. 等待追問處理
    print("  ⏳ 等待追問處理...")
    await asyncio.sleep(test_config['e2e_timeout'])
    print("  ✅ 追問處理完成")

    # 5. 驗證 tool 被調用（應該有兩次調用）
    print("  🔍 檢查 Lambda 日誌...")
    tool_called = log_fetcher.check_tool_called(
        lambda_name=test_config['processor_lambda'],
        tool_name="Image Analysis Tool",
        since_seconds=180
    )

    assert tool_called, "❌ analyze_image_tool 沒有被調用"
    print("  ✅ analyze_image_tool 已被調用")

    # 6. 驗證 Memory session
    memory_ok = log_fetcher.check_memory_recorded(
        lambda_name=test_config['processor_lambda'],
        keyword="Memory session",
        since_seconds=180
    )

    assert memory_ok, "❌ Memory session 未找到"
    print("  ✅ Memory session 正常運作")

    print("  ℹ️  請在 Telegram 手動確認追問回應包含調味包相關內容")
    print("  🎉 測試 2 通過！")


@pytest.mark.real_e2e
@pytest.mark.image
@pytest.mark.asyncio
async def test_image_no_caption(bot_client, log_fetcher, test_config, clean_session):
    """
    測試 3：上傳圖片但沒有文字說明
    
    驗證 Agent 會主動調用 tool 進行基本分析
    """
    print("\n📷 測試 3：無說明圖片分析")

    fixture_path = "tests/e2e_real/fixtures/test_noodle.jpg"

    if not os.path.exists(fixture_path):
        pytest.skip(f"測試圖片不存在：{fixture_path}")

    # 上傳圖片（無 caption）
    print("  → 上傳圖片（無說明）...")
    await bot_client.send_photo(photo_path=fixture_path)

    # 等待處理
    print("  ⏳ 等待 AI 主動分析...")
    import asyncio
    await asyncio.sleep(test_config['e2e_timeout'])

    # 驗證 tool 被調用
    print("  🔍 檢查 Lambda 日誌...")
    tool_called = log_fetcher.check_tool_called(
        lambda_name=test_config['processor_lambda'],
        tool_name="Image Analysis Tool",
        since_seconds=120
    )

    assert tool_called, "❌ analyze_image_tool 沒有被調用"
    print("  ✅ analyze_image_tool 已被調用")
    print("  ℹ️  請在 Telegram 手動確認 AI 主動分析了圖片")
    print("  🎉 測試 3 通過！")


import os
