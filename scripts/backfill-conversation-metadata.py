#!/usr/bin/env python3
"""
回填 conversation_metadata 表

從 conversation_history 表提取對話摘要資訊，創建 metadata 記錄
"""

from collections import defaultdict

import boto3

# 初始化 DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
history_table = dynamodb.Table('agentcore-conversation-history-prod')
metadata_table = dynamodb.Table('agentcore-conversation-metadata-prod')

def scan_conversations():
    """掃描 history 表，按對話分組"""
    print("🔍 掃描 history 表...")

    conversations = defaultdict(list)

    # Scan 所有記錄
    response = history_table.scan()
    items = response.get('Items', [])

    # 處理分頁
    while 'LastEvaluatedKey' in response:
        response = history_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    print(f"📊 找到 {len(items)} 條消息記錄")

    # 按 conversation_id 分組
    for item in items:
        conv_id = item.get('conversation_id')
        if conv_id:
            conversations[conv_id].append(item)

    print(f"📊 找到 {len(conversations)} 個唯一對話")
    return conversations

def create_metadata_record(conversation_id, messages):
    """為一個對話創建 metadata 記錄（支持 Telegram 和 Web 兩種格式）"""

    # 排序消息（按 timestamp）
    messages.sort(key=lambda x: x.get('timestamp', 0))

    # 提取資訊
    first_msg = messages[0]
    last_msg = messages[-1]

    # 處理兩種格式：Telegram 用 sender_id，Web 用 unified_user_id
    unified_user_id = first_msg.get('unified_user_id') or first_msg.get('sender_id', '')
    channel = first_msg.get('channel', 'unknown')
    created_at = first_msg.get('timestamp')
    last_message_time = last_msg.get('timestamp')
    message_count = len(messages)

    # 生成標題（從第一條消息的內容）
    title = "Untitled Chat"
    for msg in messages:
        content = msg.get('content')

        # Telegram 格式：content 是字符串
        if isinstance(content, str) and content:
            title = content[:30]
            break
        # Web 格式：content 是對象 {text: ...}
        elif isinstance(content, dict):
            text = content.get('text', '')
            if text:
                title = text[:30]
                break

    # 創建 metadata 記錄
    metadata = {
        'conversation_id': conversation_id,
        'unified_user_id': unified_user_id,
        'channel': channel,
        'title': title,
        'created_at': created_at,
        'last_message_time': last_message_time,
        'message_count': message_count,
        'is_pinned': False,
        'is_deleted': False
    }

    return metadata

def backfill_metadata():
    """執行回填"""

    # 掃描並分組
    conversations = scan_conversations()

    print("\n🚀 開始回填 metadata 表...")

    created = 0
    skipped = 0
    errors = 0

    for conv_id, messages in conversations.items():
        try:
            # 檢查是否已存在
            response = metadata_table.get_item(
                Key={'conversation_id': conv_id}
            )

            if 'Item' in response:
                skipped += 1
                continue

            # 創建 metadata 記錄
            metadata = create_metadata_record(conv_id, messages)
            metadata_table.put_item(Item=metadata)

            created += 1

            if created % 10 == 0:
                print(f"  已創建 {created} 條 metadata 記錄...")

        except Exception as e:
            print(f"❌ 創建失敗 {conv_id} - {str(e)}")
            errors += 1

    print("\n✅ 回填完成！")
    print(f"  創建: {created} 條")
    print(f"  跳過: {skipped} 條（已存在）")
    print(f"  錯誤: {errors} 條")

    return created, skipped, errors

if __name__ == '__main__':
    print("🚀 開始回填 conversation metadata...")
    print("源表: agentcore-conversation-history-prod")
    print("目標表: agentcore-conversation-metadata-prod")
    print()

    created, skipped, errors = backfill_metadata()

    if errors > 0:
        print("\n⚠️ 有錯誤發生，請檢查日誌")
        exit(1)
    else:
        print("\n🎉 所有 metadata 記錄已成功創建！")
        exit(0)
