#!/usr/bin/env python3
"""
回填 global_partition 屬性到現有的 Telegram 對話記錄

這個腳本會：
1. Scan agentcore-conversation-history-prod 表
2. 為每條記錄添加 global_partition='ALL' 屬性
3. 保持其他屬性不變
"""


import boto3

# 初始化 DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('agentcore-conversation-history-prod')

def backfill_global_partition():
    """回填 global_partition 屬性"""

    print("🔍 掃描表中的記錄...")

    # Scan 所有記錄
    response = table.scan()
    items = response.get('Items', [])

    # 處理分頁
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    print(f"📊 找到 {len(items)} 條記錄")

    # 統計
    updated = 0
    skipped = 0
    errors = 0

    for item in items:
        conversation_id = item.get('conversation_id')
        timestamp = item.get('timestamp')

        # 檢查是否已有 global_partition
        if 'global_partition' in item:
            skipped += 1
            continue

        try:
            # 更新記錄，添加 global_partition
            table.update_item(
                Key={
                    'conversation_id': conversation_id,
                    'timestamp': timestamp
                },
                UpdateExpression='SET global_partition = :gp',
                ExpressionAttributeValues={
                    ':gp': 'ALL'
                }
            )
            updated += 1

            if updated % 10 == 0:
                print(f"  已更新 {updated} 條記錄...")

        except Exception as e:
            print(f"❌ 更新失敗 {conversation_id}:{timestamp} - {str(e)}")
            errors += 1

    print("\n✅ 回填完成！")
    print(f"  更新: {updated} 條")
    print(f"  跳過: {skipped} 條（已有 global_partition）")
    print(f"  錯誤: {errors} 條")

    return updated, skipped, errors

if __name__ == '__main__':
    print("🚀 開始回填 global_partition 屬性...")
    print("表名: agentcore-conversation-history-prod")
    print("屬性: global_partition = 'ALL'")
    print()

    updated, skipped, errors = backfill_global_partition()

    if errors > 0:
        print("\n⚠️ 有錯誤發生，請檢查日誌")
        exit(1)
    else:
        print("\n🎉 所有記錄已成功更新！")
        exit(0)
