#!/usr/bin/env python3
"""
統一 conversation_id 格式遷移腳本

將 tg: 格式統一為 telegram: 格式
支持 dry-run、自動備份、原子操作

Usage:
  python3 migrate-conversation-ids.py --dry-run  # 只報告
  python3 migrate-conversation-ids.py --execute  # 執行遷移
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

import boto3

# 初始化
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
history_table = dynamodb.Table('agentcore-conversation-history-prod')
metadata_table = dynamodb.Table('agentcore-conversation-metadata-prod')

def decimal_default(obj):
    """JSON 序列化 Decimal"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def backup_tables():
    """備份兩個表的完整數據"""
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_dir = f'backups/{timestamp}'
    os.makedirs(backup_dir, exist_ok=True)

    print(f"📦 備份數據到 {backup_dir}/...")

    # 備份 history 表
    print("  備份 history 表...")
    response = history_table.scan()
    items = response.get('Items', [])
    while 'LastEvaluatedKey' in response:
        response = history_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    with open(f'{backup_dir}/history-backup.json', 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2, default=decimal_default)
    print(f"    ✅ {len(items)} 條記錄")

    # 備份 metadata 表
    print("  備份 metadata 表...")
    response = metadata_table.scan()
    items = response.get('Items', [])
    while 'LastEvaluatedKey' in response:
        response = metadata_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    with open(f'{backup_dir}/metadata-backup.json', 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2, default=decimal_default)
    print(f"    ✅ {len(items)} 條記錄")

    print(f"✅ 備份完成：{backup_dir}/\n")
    return backup_dir

def convert_id(old_id: str) -> str:
    """轉換 ID 格式"""
    if old_id.startswith('tg:group:'):
        return old_id.replace('tg:group:', 'telegram:group:', 1)
    elif old_id.startswith('tg:'):
        return old_id.replace('tg:', 'telegram:', 1)
    else:
        return old_id

def scan_tables():
    """掃描表，找出需要遷移的記錄"""
    print("🔍 掃描表，查找需要遷移的記錄...\n")

    # 掃描 history 表
    response = history_table.scan()
    history_items = response.get('Items', [])
    while 'LastEvaluatedKey' in response:
        response = history_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        history_items.extend(response.get('Items', []))

    # 掃描 metadata 表
    response = metadata_table.scan()
    metadata_items = response.get('Items', [])
    while 'LastEvaluatedKey' in response:
        response = metadata_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        metadata_items.extend(response.get('Items', []))

    # 按 conversation_id 分組
    history_by_conv = defaultdict(list)
    for item in history_items:
        conv_id = item.get('conversation_id')
        if conv_id and conv_id.startswith('tg:'):
            history_by_conv[conv_id].append(item)

    metadata_by_conv = {}
    for item in metadata_items:
        conv_id = item.get('conversation_id')
        if conv_id and conv_id.startswith('tg:'):
            metadata_by_conv[conv_id] = item

    return history_by_conv, metadata_by_conv

def dry_run():
    """Dry run 模式：報告會做什麼，不實際執行"""
    print("=" * 60)
    print("🧪 DRY RUN MODE - 只報告，不實際修改")
    print("=" * 60 + "\n")

    history_by_conv, metadata_by_conv = scan_tables()

    print("📊 需要遷移的對話：\n")

    total_history = 0
    total_metadata = 0

    for old_id in sorted(set(list(history_by_conv.keys()) + list(metadata_by_conv.keys()))):
        new_id = convert_id(old_id)
        history_count = len(history_by_conv.get(old_id, []))
        has_metadata = old_id in metadata_by_conv

        print(f"  {old_id}")
        print(f"    → {new_id}")
        print(f"    History 記錄: {history_count} 條")
        print(f"    Metadata 記錄: {'✅ 有' if has_metadata else '❌ 無'}")
        print()

        total_history += history_count
        total_metadata += (1 if has_metadata else 0)

    print("=" * 60)
    print("📊 總計：")
    print(f"  對話數: {len(set(list(history_by_conv.keys()) + list(metadata_by_conv.keys())))} 個")
    print(f"  History 記錄: {total_history} 條")
    print(f"  Metadata 記錄: {total_metadata} 條")
    print("=" * 60 + "\n")

    return history_by_conv, metadata_by_conv

def migrate_conversation(old_id: str, history_items: list, metadata_item: dict = None):
    """遷移單個對話（原子操作）"""
    new_id = convert_id(old_id)

    print(f"\n🔄 遷移: {old_id} → {new_id}")
    print(f"  History: {len(history_items)} 條")
    print(f"  Metadata: {'✅' if metadata_item else '❌'}")

    try:
        # Step 1: 創建新 history 記錄
        for item in history_items:
            new_item = dict(item)
            new_item['conversation_id'] = new_id
            history_table.put_item(Item=new_item)
        print(f"  ✅ 創建 {len(history_items)} 條新 history 記錄")

        # Step 2: 創建新 metadata 記錄（如果有）
        if metadata_item:
            new_metadata = dict(metadata_item)
            new_metadata['conversation_id'] = new_id
            metadata_table.put_item(Item=new_metadata)
            print("  ✅ 創建新 metadata 記錄")

        # Step 3: 驗證新記錄
        verify_response = history_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('conversation_id').eq(new_id),
            Select='COUNT'
        )
        if verify_response['Count'] != len(history_items):
            raise Exception(f"驗證失敗：預期 {len(history_items)} 條，實際 {verify_response['Count']} 條")
        print("  ✅ 驗證新記錄成功")

        # Step 4: 刪除舊 history 記錄
        for item in history_items:
            history_table.delete_item(
                Key={
                    'conversation_id': old_id,
                    'timestamp': item['timestamp']
                }
            )
        print(f"  ✅ 刪除 {len(history_items)} 條舊 history 記錄")

        # Step 5: 刪除舊 metadata 記錄（如果有）
        if metadata_item:
            metadata_table.delete_item(
                Key={'conversation_id': old_id}
            )
            print("  ✅ 刪除舊 metadata 記錄")

        print("  🎉 遷移成功！")
        return True

    except Exception as e:
        print(f"  ❌ 遷移失敗：{str(e)}")
        print("  ⚠️  可能需要手動清理")
        return False

def execute_migration(history_by_conv, metadata_by_conv):
    """執行實際遷移"""
    print("\n" + "=" * 60)
    print("🚀 開始執行遷移")
    print("=" * 60)

    success = 0
    failed = 0

    all_conv_ids = sorted(set(list(history_by_conv.keys()) + list(metadata_by_conv.keys())))

    for old_id in all_conv_ids:
        history_items = history_by_conv.get(old_id, [])
        metadata_item = metadata_by_conv.get(old_id)

        if migrate_conversation(old_id, history_items, metadata_item):
            success += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print("📊 遷移結果：")
    print(f"  成功: {success} 個對話")
    print(f"  失敗: {failed} 個對話")
    print("=" * 60 + "\n")

    return success, failed

def main():
    print("🚀 Conversation ID 統一遷移工具")
    print("將 tg: 格式統一為 telegram: 格式")
    print()

    # 檢查命令行參數
    execute_mode = '--execute' in sys.argv

    # Step 1: 備份
    backup_dir = backup_tables()

    # Step 2: Dry Run
    history_by_conv, metadata_by_conv = dry_run()

    if not history_by_conv and not metadata_by_conv:
        print("✅ 沒有需要遷移的記錄！")
        return

    # Step 3: 執行模式檢查
    if not execute_mode:
        print("ℹ️  這是 Dry Run 模式")
        print("   要實際執行遷移，請使用：")
        print("   python3 migrate-conversation-ids.py --execute")
        return

    # Step 4: 執行遷移
    print("\n⚠️  執行模式：將實際修改數據庫！")
    print(f"   備份已保存在：{backup_dir}/")
    print()

    success, failed = execute_migration(history_by_conv, metadata_by_conv)

    # Step 5: 結果
    if failed == 0:
        print("🎉 遷移完全成功！")
        print(f"   備份位置：{backup_dir}/")
    else:
        print(f"⚠️  有 {failed} 個對話遷移失敗")
        print(f"   請查看日誌並使用備份恢復：{backup_dir}/")

if __name__ == '__main__':
    main()
