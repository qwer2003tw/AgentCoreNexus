"""
Unit tests for ConversationService
使用 moto mock DynamoDB
"""

import time

import boto3
import conversation_service as conv_module
from moto import mock_aws


def setup_mock_tables():
    """設置 mock DynamoDB tables"""
    # 創建 DynamoDB resource（在 mock 上下文中）
    dynamodb = boto3.resource("dynamodb", region_name="us-west-2")

    # 創建 history table
    dynamodb.create_table(
        TableName="test-conversation-history",
        KeySchema=[
            {"AttributeName": "conversation_id", "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "conversation_id", "AttributeType": "S"},
            {"AttributeName": "timestamp", "AttributeType": "N"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # 創建 metadata table
    dynamodb.create_table(
        TableName="test-conversation-metadata",
        KeySchema=[{"AttributeName": "conversation_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "conversation_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # 創建並返回 ConversationService（傳入 mock resource）
    return conv_module.ConversationService(
        history_table_name="test-conversation-history",
        metadata_table_name="test-conversation-metadata",
        dynamodb_resource=dynamodb,  # 關鍵：傳入 mock resource
    )


@mock_aws
def test_save_message():
    """測試訊息儲存"""
    # 在 mock context 中創建 service
    service = setup_mock_tables()

    # 測試儲存
    result = service.save_message(
        conversation_id="tg:12345",
        sender_id="tg:12345",
        sender_name="Test User",
        content="Hello World",
        message_type="text",
        channel="telegram",
    )

    # 驗證結果
    assert result["success"] is True, f"Save failed: {result.get('error')}"
    assert "message_id" in result
    assert "timestamp" in result

    # 額外驗證：讀取剛儲存的訊息
    get_result = service.get_messages("tg:12345", limit=1)
    assert get_result["success"] is True
    assert get_result["count"] == 1


@mock_aws
def test_get_messages():
    """測試訊息查詢"""
    service = setup_mock_tables()

    # 先儲存幾條訊息
    for i in range(5):
        service.save_message(
            conversation_id="tg:12345",
            sender_id="tg:12345",
            sender_name="Test User",
            content=f"Message {i}",
            message_type="text",
            channel="telegram",
        )
        time.sleep(0.001)  # 確保不同的 timestamp

    # 查詢訊息
    result = service.get_messages(conversation_id="tg:12345", limit=10)

    assert result["success"] is True
    assert result["count"] == 5
    assert len(result["messages"]) == 5
    assert result["has_more"] is False


@mock_aws
def test_get_messages_with_pagination():
    """測試分頁查詢"""
    service = setup_mock_tables()

    # 儲存 10 條訊息
    for i in range(10):
        service.save_message(
            conversation_id="tg:12345",
            sender_id="tg:12345",
            sender_name="Test User",
            content=f"Message {i}",
            message_type="text",
            channel="telegram",
        )
        time.sleep(0.001)

    # 第一頁（取 5 條）
    result1 = service.get_messages(conversation_id="tg:12345", limit=5)

    assert result1["success"] is True
    assert result1["count"] == 5
    assert result1["has_more"] is True
    assert result1["next_key"] is not None

    # 第二頁（使用 next_key）
    result2 = service.get_messages(
        conversation_id="tg:12345", limit=5, last_evaluated_key=result1["next_key"]
    )

    assert result2["success"] is True
    assert result2["count"] == 5
    assert result2["has_more"] is False


@mock_aws
def test_format_messages_for_ai_group():
    """測試群組對話格式化"""
    service = setup_mock_tables()

    # 模擬群組對話
    service.save_message(
        conversation_id="tg:group:-12345",
        sender_id="tg:111",
        sender_name="Alice",
        content="今天天氣如何？",
    )
    time.sleep(0.001)

    service.save_message(
        conversation_id="tg:group:-12345",
        sender_id="ai",
        sender_name="AI",
        content="今天晴朗溫暖",
    )
    time.sleep(0.001)

    service.save_message(
        conversation_id="tg:group:-12345",
        sender_id="tg:222",
        sender_name="Bob",
        content="明天呢？",
    )

    # 格式化為 AI 上下文
    formatted = service.format_messages_for_ai(
        conversation_id="tg:group:-12345", limit=10, include_sender_name=True
    )

    assert "[Alice] 今天天氣如何？" in formatted
    assert "[AI] 今天晴朗溫暖" in formatted
    assert "[Bob] 明天呢？" in formatted


@mock_aws
def test_format_messages_for_ai_private():
    """測試私人對話格式化（無發送者名稱）"""
    service = setup_mock_tables()

    service.save_message(
        conversation_id="tg:12345",
        sender_id="tg:12345",
        sender_name="User",
        content="你好",
    )
    time.sleep(0.001)

    service.save_message(
        conversation_id="tg:12345",
        sender_id="ai",
        sender_name="AI",
        content="你好！有什麼可以幫助你？",
    )

    # 格式化（不包含發送者名稱）
    formatted = service.format_messages_for_ai(
        conversation_id="tg:12345", limit=10, include_sender_name=False
    )

    assert "你好" in formatted
    assert "你好！有什麼可以幫助你？" in formatted
    assert "[User]" not in formatted
    assert "[AI]" not in formatted


@mock_aws
def test_soft_delete_conversation():
    """測試軟刪除"""
    service = setup_mock_tables()

    # 儲存訊息
    service.save_message(
        conversation_id="tg:12345",
        sender_id="tg:12345",
        sender_name="User",
        content="Test message",
    )

    # 軟刪除
    result = service.delete_conversation(conversation_id="tg:12345", hard_delete=False)

    assert result["success"] is True
    assert "deleted_at" in result
    assert "recoverable_until" in result
    assert result["recovery_days"] == 30

    # 查詢應該失敗（已刪除）
    get_result = service.get_messages(conversation_id="tg:12345")
    assert get_result["success"] is False
    assert "deleted" in get_result["error"].lower()


@mock_aws
def test_restore_conversation():
    """測試恢復對話"""
    service = setup_mock_tables()

    # 儲存並刪除
    service.save_message(
        conversation_id="tg:12345",
        sender_id="tg:12345",
        sender_name="User",
        content="Test message",
    )

    service.delete_conversation(conversation_id="tg:12345", hard_delete=False)

    # 恢復
    restore_result = service.restore_conversation(conversation_id="tg:12345")
    assert restore_result["success"] is True

    # 查詢應該成功
    get_result = service.get_messages(conversation_id="tg:12345")
    assert get_result["success"] is True
    assert get_result["count"] == 1


@mock_aws
def test_metadata_update():
    """測試元數據自動更新"""
    service = setup_mock_tables()

    # 儲存第一條訊息
    service.save_message(
        conversation_id="tg:12345",
        sender_id="tg:12345",
        sender_name="User",
        content="Message 1",
    )

    # 檢查 metadata
    metadata = service.get_conversation_metadata("tg:12345")
    assert metadata is not None
    assert metadata["message_count"] == 1
    assert metadata["is_group"] is False
    assert "tg:12345" in metadata["participant_ids"]

    # 儲存第二條訊息（不同發送者）
    service.save_message(
        conversation_id="tg:12345", sender_id="ai", sender_name="AI", content="Response"
    )

    # 再次檢查 metadata
    metadata = service.get_conversation_metadata("tg:12345")
    assert metadata["message_count"] == 2
    assert len(metadata["participant_ids"]) == 2
    assert "ai" in metadata["participant_ids"]


@mock_aws
def test_group_conversation_detection():
    """測試群組對話自動檢測"""
    service = setup_mock_tables()

    # 儲存群組訊息
    service.save_message(
        conversation_id="tg:group:-12345",
        sender_id="tg:111",
        sender_name="Alice",
        content="Group message",
    )

    # 檢查 metadata
    metadata = service.get_conversation_metadata("tg:group:-12345")
    assert metadata is not None
    assert metadata["is_group"] is True
    assert metadata["channel"] == "telegram"
