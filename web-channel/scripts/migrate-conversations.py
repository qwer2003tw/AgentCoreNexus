"""
Data Migration Script: Create conversation_id for existing messages

Prerequisites:
1. Backend deployed (conversations table created)
2. Backup existing data (optional but recommended)

Usage:
    python migrate-conversations.py --dry-run  # Preview
    python migrate-conversations.py           # Execute
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

import boto3
from botocore.exceptions import ClientError

# Configuration
REGION = "us-west-2"
HISTORY_TABLE = "agentcore-web-channel-conversation-history"
CONVERSATIONS_TABLE = "agentcore-web-channel-conversations"
BINDINGS_TABLE = "agentcore-web-channel-user-bindings"

# Time gap threshold (new conversation if gap exceeds this)
CONVERSATION_GAP_HOURS = 1

# Initialize
dynamodb = boto3.resource("dynamodb", region_name=REGION)
history_table = dynamodb.Table(HISTORY_TABLE)
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)
bindings_table = dynamodb.Table(BINDINGS_TABLE)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Migrate conversation data")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't execute")
    parser.add_argument("--user-id", help="Migrate specific user only (for testing)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Conversation Data Migration Script")
    print("=" * 60)
    print(f"Mode: {'Preview' if args.dry_run else 'Execute'}")
    print(f"Region: {REGION}")
    print(f"Conversation Gap Threshold: {CONVERSATION_GAP_HOURS} hours")
    print("=" * 60)
    print()
    
    if not args.dry_run:
        confirm = input("⚠️  This will modify production data. Continue? (yes/no): ")
        if confirm.lower() != "yes":
            print("❌ Cancelled")
            return
        print()
    
    # Get all users
    if args.user_id:
        user_ids = [args.user_id]
    else:
        user_ids = get_all_user_ids()
    
    print(f"📊 Found {len(user_ids)} users to migrate")
    print()
    
    total_conversations = 0
    total_messages = 0
    errors = []
    
    for i, user_id in enumerate(user_ids, 1):
        print(f"[{i}/{len(user_ids)}] Processing user: {user_id[:8]}...")
        
        try:
            conv_count, msg_count = migrate_user_conversations(
                user_id, 
                dry_run=args.dry_run
            )
            total_conversations += conv_count
            total_messages += msg_count
            print(f"  ✅ Done: {conv_count} conversations, {msg_count} messages")
            
        except Exception as e:
            error_msg = f"User {user_id[:8]}: {str(e)}"
            errors.append(error_msg)
            print(f"  ❌ Error: {str(e)}")
        
        print()
    
    # Summary
    print("=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"✅ Successfully migrated users: {len(user_ids) - len(errors)}")
    print(f"✅ Conversations created: {total_conversations}")
    print(f"✅ Messages updated: {total_messages}")
    
    if errors:
        print(f"❌ Failures: {len(errors)}")
        print("\nFailure details:")
        for error in errors:
            print(f"  - {error}")
    
    if args.dry_run:
        print("\n💡 This was preview mode, no data modified")
        print("   Remove --dry-run to execute migration")
    
    print("=" * 60)


def get_all_user_ids() -> List[str]:
    """Get all unified_user_id"""
    user_ids = set()
    
    try:
        # Scan bindings table
        response = bindings_table.scan(
            ProjectionExpression="unified_user_id"
        )
        
        for item in response.get("Items", []):
            user_ids.add(item["unified_user_id"])
        
        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = bindings_table.scan(
                ProjectionExpression="unified_user_id",
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            for item in response.get("Items", []):
                user_ids.add(item["unified_user_id"])
        
        return list(user_ids)
        
    except Exception as e:
        print(f"Error: Unable to get user list - {str(e)}")
        sys.exit(1)


def migrate_user_conversations(user_id: str, dry_run: bool = False) -> tuple[int, int]:
    """
    Migrate single user's messages to conversations
    
    Args:
        user_id: unified_user_id
        dry_run: Preview only
    
    Returns:
        (conversations_created, messages_updated)
    """
    # Step 1: Get all messages
    messages = get_all_messages(user_id)
    
    if not messages:
        return 0, 0
    
    # Step 2: Group messages into conversations
    conversations = group_messages_into_conversations(messages)
    
    print(f"  📋 Found {len(conversations)} conversations ({len(messages)} messages total)")
    
    if dry_run:
        # Preview mode: just print stats
        for i, conv in enumerate(conversations, 1):
            print(f"    Conversation {i}: {len(conv['messages'])} messages")
            print(f"      Title: {conv['title']}")
            print(f"      Time: {conv['first_time']} - {conv['last_time']}")
        return len(conversations), len(messages)
    
    # Step 3: Create conversation records
    for conv in conversations:
        try:
            conversations_table.put_item(Item={
                "unified_user_id": user_id,
                "conversation_id": conv["id"],
                "title": conv["title"],
                "created_at": conv["first_time"],
                "last_message_time": conv["last_time"],
                "message_count": len(conv["messages"]),
                "is_pinned": False,
                "is_deleted": False
            })
        except Exception as e:
            print(f"    ⚠️  Unable to create conversation {conv['id']}: {str(e)}")
    
    # Step 4: Update messages with conversation_id
    updated_count = 0
    for conv in conversations:
        for msg in conv["messages"]:
            try:
                history_table.update_item(
                    Key={
                        "unified_user_id": user_id,
                        "timestamp_msgid": msg["timestamp_msgid"]
                    },
                    UpdateExpression="SET conversation_id = :cid",
                    ExpressionAttributeValues={":cid": conv["id"]}
                )
                updated_count += 1
            except Exception as e:
                print(f"    ⚠️  Unable to update message: {str(e)}")
    
    return len(conversations), updated_count


def get_all_messages(user_id: str) -> List[Dict[str, Any]]:
    """Get all messages for user (time-sorted)"""
    messages = []
    last_key = None
    
    try:
        while True:
            kwargs = {
                "KeyConditionExpression": "unified_user_id = :uid",
                "ExpressionAttributeValues": {":uid": user_id},
                "ScanIndexForward": True  # Oldest first
            }
            
            if last_key:
                kwargs["ExclusiveStartKey"] = last_key
            
            result = history_table.query(**kwargs)
            messages.extend(result.get("Items", []))
            
            last_key = result.get("LastEvaluatedKey")
            if not last_key:
                break
        
        return messages
        
    except Exception as e:
        raise Exception(f"Unable to get messages: {str(e)}")


def group_messages_into_conversations(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group messages by time gap into conversations
    
    Rule: adjacent messages with gap > 1 hour = new conversation
    """
    if not messages:
        return []
    
    conversations = []
    current_conv = None
    
    for msg in messages:
        # Extract timestamp
        timestamp_str = msg["timestamp_msgid"].split("#")[0]
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except Exception:
            continue
        
        # Check if should start new conversation
        should_start_new = False
        
        if not current_conv:
            should_start_new = True
        else:
            time_diff = (timestamp - current_conv["last_time"]).total_seconds()
            if time_diff > CONVERSATION_GAP_HOURS * 3600:
                should_start_new = True
        
        if should_start_new:
            # Start new conversation
            conv_id = str(uuid.uuid4())
            content_text = msg.get("content", {}).get("text", "Untitled")
            title = content_text[:30]
            if len(content_text) > 30:
                title += "..."
            
            current_conv = {
                "id": conv_id,
                "title": title,
                "messages": [],
                "first_time": timestamp.isoformat(),
                "last_time": timestamp.isoformat()
            }
            conversations.append(current_conv)
        
        # Add message to current conversation
        current_conv["messages"].append(msg)
        current_conv["last_time"] = timestamp.isoformat()
    
    return conversations


if __name__ == "__main__":
    main()