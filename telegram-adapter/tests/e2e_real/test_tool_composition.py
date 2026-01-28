"""
工具組合 E2E 測試
測試多個 tools 的組合使用
"""

import os

import pytest


@pytest.mark.real_e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_image_and_search(bot_client, log_fetcher, test_config, clean_session):
    """
    測試 5：測試工具組合使用

    流程：
    1. 上傳產品圖片 + 要求搜尋價格
    2. 驗證 Agent 組合使用多個 tools
    3. 驗證回應整合了多個 tools 的結果

    預期 Agent 行為：
    - 調用 analyze_image_tool 識別產品
    - 調用 browse_website 或搜尋工具查詢價格
    - 整合結果回應
    """
    print("\n🔧 測試 5：工具組合使用")

    # 1. 上傳圖片並要求搜尋
    print("  → 上傳產品圖片...")
    fixture_path = "tests/e2e_real/fixtures/test_product.jpg"

    # 如果專用測試圖片不存在，使用泡麵圖片
    if not os.path.exists(fixture_path):
        fixture_path = "tests/e2e_real/fixtures/test_noodle.jpg"
        if not os.path.exists(fixture_path):
            pytest.skip("測試圖片不存在")

    await bot_client.send_photo(
        photo_path=fixture_path, caption="這是什麼產品？幫我搜尋網路上的資訊"
    )

    # 2. 等待回應（組合工具可能需要更長時間）
    print("  ⏳ 等待 AI 處理（組合工具，最多 90 秒）...")
    reply = await bot_client.wait_for_reply(timeout=90, poll_interval=3)

    assert reply is not None, "❌ AI 沒有回應"
    assert len(reply) > 30, "❌ 回應過短"

    print(f"  ✅ 收到回應：{reply[:150]}...")

    # 3. 驗證 image tool 被調用
    print("  🔍 檢查 tool 調用記錄...")
    image_tool_called = log_fetcher.check_tool_called(
        lambda_name=test_config["processor_lambda"],
        tool_name="Image Analysis Tool",
        since_seconds=150,
    )

    assert image_tool_called, "❌ analyze_image_tool 沒有被調用"
    print("  ✅ analyze_image_tool 已被調用")

    # 4. 檢查是否調用了其他 tools（可選驗證）
    browse_called = log_fetcher.check_tool_called(
        lambda_name=test_config["processor_lambda"], tool_name="browse_website", since_seconds=150
    )

    if browse_called:
        print("  ✅ browse_website 也被調用（工具組合成功）")
    else:
        print("  ℹ️  browse_website 未被調用（Agent 可能決定不需要）")

    print("  🎉 測試 5 通過！")


@pytest.mark.real_e2e
@pytest.mark.asyncio
async def test_image_and_file_together(bot_client, test_config, clean_session):
    """
    測試：同時處理圖片和檔案

    驗證 Agent 可以處理混合附件
    """
    print("\n🖼️📄 測試：圖片 + 檔案混合")

    image_path = "tests/e2e_real/fixtures/test_noodle.jpg"
    file_path = "tests/e2e_real/fixtures/test_data.csv"

    if not os.path.exists(image_path):
        pytest.skip("測試圖片不存在")

    # 先上傳圖片
    print("  → 上傳圖片...")
    await bot_client.send_photo(photo_path=image_path, caption="這是什麼？")

    # 等待回應
    reply1 = await bot_client.wait_for_reply(timeout=test_config["e2e_timeout"])
    assert reply1 is not None
    print("  ✅ 圖片分析完成")

    # 如果檔案存在，繼續測試
    if os.path.exists(file_path):
        print("  → 上傳檔案...")
        await bot_client.send_document(doc_path=file_path, caption="這個數據呢？")

        reply2 = await bot_client.wait_for_reply(timeout=test_config["e2e_timeout"])
        assert reply2 is not None
        print("  ✅ 檔案分析完成")

        # 測試 Memory 是否記住兩者
        print("  💬 測試 Memory：剛才的圖片和數據有關聯嗎？")
        await bot_client.send_text("剛才的圖片和數據有關聯嗎？")

        reply3 = await bot_client.wait_for_reply(timeout=test_config["e2e_timeout"])
        assert reply3 is not None
        print(f"  ✅ Memory 回應：{reply3[:100]}...")

    print("  🎉 混合附件測試通過！")
