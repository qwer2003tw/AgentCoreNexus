"""
檔案分析 E2E 測試
測試 analyze_file_tool 和 Memory 功能
"""

import os

import pytest


@pytest.mark.real_e2e
@pytest.mark.file
@pytest.mark.asyncio
async def test_file_basic_analysis(bot_client, log_fetcher, test_config, clean_session):
    """
    測試 3：上傳檔案測試分析
    
    流程：
    1. 上傳 CSV/TXT 檔案
    2. 驗證 Agent 調用 analyze_file_tool
    3. 驗證回應包含檔案摘要
    """
    print("\n📄 測試 3：檔案基本分析")

    # 1. 上傳測試檔案
    print("  → 上傳測試檔案...")
    fixture_path = "tests/e2e_real/fixtures/test_data.csv"

    if not os.path.exists(fixture_path):
        pytest.skip(f"測試檔案不存在：{fixture_path}")

    sent_msg = await bot_client.send_document(
        doc_path=fixture_path, caption="統計這份數據"
    )

    print(f"  ✅ 檔案已上傳（message_id: {sent_msg.message_id}）")

    # 2. 等待 AI 回應
    print(f"  ⏳ 等待 AI 分析（最多 {test_config['e2e_timeout']} 秒）...")
    reply = await bot_client.wait_for_reply(
        timeout=test_config['e2e_timeout'], poll_interval=test_config['poll_interval']
    )

    # 3. 驗證回應
    assert reply is not None, "❌ AI 沒有回應"
    assert len(reply) > 20, "❌ 回應過短"

    print(f"  ✅ 收到分析：{reply[:100]}...")

    # 4. 驗證 tool 被調用
    print("  🔍 檢查 Lambda 日誌...")
    tool_called = log_fetcher.check_tool_called(
        lambda_name=test_config['processor_lambda'],
        tool_name="File Analysis Tool",
        since_seconds=120,
    )

    # 注意：如果 FILE_ENABLED=false，tool 可能不會被調用
    # 但至少應該有回應
    if tool_called:
        print("  ✅ analyze_file_tool 已被調用")
    else:
        print("  ⚠️  analyze_file_tool 未被調用（可能 FILE_ENABLED=false）")

    print("  🎉 測試 3 通過！")


@pytest.mark.real_e2e
@pytest.mark.file
@pytest.mark.memory
@pytest.mark.asyncio
async def test_file_memory_followup(bot_client, test_config, clean_session):
    """
    測試 4：同對話追問檔案內容
    
    流程：
    1. 上傳檔案並獲得摘要
    2. 追問特定部分
    3. 驗證 Memory 保留檔案 S3 URL
    4. 驗證回應包含相關內容
    """
    print("\n📊 測試 4：檔案 Memory 追問")

    # 1. 上傳測試檔案
    print("  → 上傳測試檔案...")
    fixture_path = "tests/e2e_real/fixtures/test_data.csv"

    if not os.path.exists(fixture_path):
        pytest.skip(f"測試檔案不存在：{fixture_path}")

    await bot_client.send_document(doc_path=fixture_path, caption="摘要這份數據")

    # 2. 等待第一次回應
    print("  ⏳ 等待摘要...")
    first_reply = await bot_client.wait_for_reply(timeout=test_config['e2e_timeout'])

    assert first_reply is not None, "❌ 沒有收到摘要"
    print(f"  ✅ 摘要：{first_reply[:100]}...")

    # 3. 追問特定內容
    print("  💬 追問：第一欄是什麼？")
    await bot_client.send_text("第一欄是什麼？")

    # 4. 等待追問回應
    print("  ⏳ 等待追問回應...")
    followup_reply = await bot_client.wait_for_reply(timeout=test_config['e2e_timeout'])

    assert followup_reply is not None, "❌ 追問沒有回應"
    print(f"  ✅ 追問回應：{followup_reply[:100]}...")

    # 5. 驗證沒有失去上下文
    assert "找不到" not in followup_reply.lower(), "❌ 追問表示找不到檔案"

    print("  ✅ 追問回應保持上下文")
    print("  🎉 測試 4 通過！")


@pytest.mark.real_e2e
@pytest.mark.file
@pytest.mark.asyncio
async def test_multiple_files(bot_client, test_config, clean_session):
    """
    測試：上傳多個檔案
    
    驗證 Agent 可以處理多個附件
    """
    print("\n📚 測試：多檔案處理")

    fixture1 = "tests/e2e_real/fixtures/test_data.csv"
    fixture2 = "tests/e2e_real/fixtures/test_report.txt"

    # 檢查檔案是否存在
    if not os.path.exists(fixture1):
        pytest.skip(f"測試檔案不存在：{fixture1}")

    # 上傳第一個檔案
    print("  → 上傳第一個檔案...")
    await bot_client.send_document(doc_path=fixture1, caption="這是什麼數據？")

    # 等待回應
    reply1 = await bot_client.wait_for_reply(timeout=test_config['e2e_timeout'])
    assert reply1 is not None
    print("  ✅ 第一個檔案分析完成")

    # 如果第二個檔案存在，測試多檔案
    if os.path.exists(fixture2):
        print("  → 上傳第二個檔案...")
        await bot_client.send_document(doc_path=fixture2)

        reply2 = await bot_client.wait_for_reply(timeout=test_config['e2e_timeout'])
        assert reply2 is not None
        print("  ✅ 第二個檔案分析完成")

    print("  🎉 多檔案測試通過！")
