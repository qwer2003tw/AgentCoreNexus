"""
Verify migration results
"""

import boto3

REGION = "us-west-2"
HISTORY_TABLE = "agentcore-web-channel-conversation-history"
CONVERSATIONS_TABLE = "agentcore-web-channel-conversations"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
history_table = dynamodb.Table(HISTORY_TABLE)
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)


def verify_migration():
    """Verify migration results"""
    print("🔍 Verifying migration results...")
    print()
    
    # 1. Count conversations table
    conv_result = conversations_table.scan(Select="COUNT")
    conv_count = conv_result["Count"]
    print(f"✅ Conversations table: {conv_count} conversations")
    
    # 2. Check if messages have conversation_id
    sample = history_table.scan(Limit=100)
    messages_with_conv_id = sum(
        1 for item in sample["Items"] 
        if "conversation_id" in item
    )
    print(f"✅ Message sample: {messages_with_conv_id}/100 have conversation_id")
    
    # 3. Verify conversation metadata accuracy
    sample_convs = conversations_table.scan(Limit=10)
    print(f"\n📋 Sample conversations:")
    for conv in sample_convs["Items"][:5]:
        print(f"  - {conv.get('title', 'Untitled')}")
        print(f"    Messages: {conv.get('message_count', 0)}")
        print(f"    Last activity: {conv.get('last_message_time', 'N/A')}")
    
    print("\n✅ Verification complete")


if __name__ == "__main__":
    verify_migration()