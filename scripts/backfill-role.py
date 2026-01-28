#!/usr/bin/env python3
"""
回填 role 欄位到對話歷史記錄

根據 sender_id 判斷角色：
- sender_id = 'ai' → role = 'assistant'
- 其他 → role = 'user'
"""

import boto3

# 初始化 DynamoDB
dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
history_table = dynamodb.Table("agentcore-conversation-history-prod")


def backfill_role():
    """回填 role 欄位"""

    print("🔍 掃描 history 表...")

    # Scan 所有記錄
    response = history_table.scan()
    items = response.get("Items", [])

    # 處理分頁
    while "LastEvaluatedKey" in response:
        response = history_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    print(f"📊 找到 {len(items)} 條記錄")

    # 統計
    updated = 0
    skipped = 0
    errors = 0

    for item in items:
        conversation_id = item.get("conversation_id")
        timestamp = item.get("timestamp")

        # 檢查是否已有 role
        if "role" in item:
            skipped += 1
            continue

        # 根據 sender_id 判斷 role
        sender_id = item.get("sender_id", "")
        if sender_id == "ai":
            role = "assistant"
        else:
            role = "user"

        try:
            # 更新記錄，添加 role
            history_table.update_item(
                Key={"conversation_id": conversation_id, "timestamp": timestamp},
                UpdateExpression="SET #role = :role",
                ExpressionAttributeNames={"#role": "role"},
                ExpressionAttributeValues={":role": role},
            )
            updated += 1

            if updated % 10 == 0:
                print(f"  已更新 {updated} 條記錄...")

        except Exception as e:
            print(f"❌ 更新失敗 {conversation_id}:{timestamp} - {str(e)}")
            errors += 1

    print("\n✅ 回填完成！")
    print(f"  更新: {updated} 條")
    print(f"  跳過: {skipped} 條（已有 role）")
    print(f"  錯誤: {errors} 條")

    # 統計結果
    print("\n📊 角色分布：")
    response = history_table.scan(
        ProjectionExpression="#role", ExpressionAttributeNames={"#role": "role"}
    )
    items = response.get("Items", [])
    while "LastEvaluatedKey" in response:
        response = history_table.scan(
            ProjectionExpression="#role",
            ExpressionAttributeNames={"#role": "role"},
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    role_counts = {}
    for item in items:
        role = item.get("role", "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1

    for role, count in sorted(role_counts.items()):
        print(f"  {role}: {count} 條")

    return updated, skipped, errors


if __name__ == "__main__":
    print("🚀 開始回填 role 欄位...")
    print("表名: agentcore-conversation-history-prod")
    print()

    updated, skipped, errors = backfill_role()

    if errors > 0:
        print("\n⚠️ 有錯誤發生，請檢查日誌")
        exit(1)
    else:
        print("\n🎉 所有記錄已成功更新！")
        exit(0)
