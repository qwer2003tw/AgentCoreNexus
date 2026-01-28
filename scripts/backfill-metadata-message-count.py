#!/usr/bin/env python3
"""
Backfill Metadata Message Count Script

修復 conversation_metadata 表中的 message_count，
使其反映實際的消息總數
"""

import boto3
from boto3.dynamodb.conditions import Key

# 初始化
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

METADATA_TABLE = 'agentcore-conversation-metadata-prod'
HISTORY_TABLE = 'agentcore-conversation-history-prod'

metadata_table = dynamodb.Table(METADATA_TABLE)
history_table = dynamodb.Table(HISTORY_TABLE)


def get_actual_message_count(conversation_id: str) -> int:
    """查詢對話的實際消息數"""
    try:
        response = history_table.query(
            KeyConditionExpression=Key('conversation_id').eq(conversation_id),
            Select='COUNT'
        )
        return response['Count']
    except Exception as e:
        print(f"  ❌ 查詢失敗 {conversation_id}: {e}")
        return 0


def backfill_metadata():
    """回填 metadata 表的 message_count"""
    print("🔄 開始回填 metadata 表的 message_count...\n")

    updated = 0
    errors = 0
    skipped = 0
    correct = 0

    # 掃描所有對話
    scan_kwargs = {}

    while True:
        response = metadata_table.scan(**scan_kwargs)
        items = response.get('Items', [])

        print(f"📋 處理 {len(items)} 個對話...")

        for conv in items:
            conversation_id = conv.get('conversation_id')
            current_count = conv.get('message_count', 0)

            if not conversation_id:
                skipped += 1
                continue

            # 查詢實際消息數
            actual_count = get_actual_message_count(conversation_id)

            if actual_count == 0:
                print(f"  ⚠️  {conversation_id}: 無消息，跳過")
                skipped += 1
                continue

            # 如果不一致，更新
            if actual_count != current_count:
                try:
                    metadata_table.update_item(
                        Key={'conversation_id': conversation_id},
                        UpdateExpression='SET message_count = :count',
                        ExpressionAttributeValues={':count': actual_count}
                    )
                    print(f"  ✅ {conversation_id}: {current_count} → {actual_count}")
                    updated += 1
                except Exception as e:
                    print(f"  ❌ 更新失敗 {conversation_id}: {e}")
                    errors += 1
            else:
                print(f"  ✓  {conversation_id}: {current_count} (正確)")
                correct += 1

        # 分頁
        if 'LastEvaluatedKey' not in response:
            break
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    # 統計
    print("\n📊 統計：")
    print(f"  ✅ 更新：{updated} 個對話")
    print(f"  ✓  正確：{correct} 個")
    print(f"  ⚠️  跳過：{skipped} 個")
    print(f"  ❌ 錯誤：{errors} 個")

    return updated


if __name__ == '__main__':
    print("=" * 60)
    print("Backfill Metadata Message Count Script")
    print("=" * 60)
    print()

    try:
        updated_count = backfill_metadata()
        print(f"\n🎉 完成！更新了 {updated_count} 個對話")
    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()
