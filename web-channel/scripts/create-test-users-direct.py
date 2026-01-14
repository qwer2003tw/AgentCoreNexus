#!/usr/bin/env python3
"""
直接操作 DynamoDB 創建測試帳號
不需要管理員 token，使用 AWS CLI 憑證即可
"""

import sys
from datetime import UTC, datetime

import bcrypt
import boto3
from botocore.exceptions import ClientError

# DynamoDB table name
STACK_NAME = "agentcore-web-channel"
TABLE_NAME = f"{STACK_NAME}-web-users"
REGION = "us-west-2"

# 測試帳號配置
TEST_USERS = [
    {"email": "test1@test.com", "password": "Test123!"},
    {"email": "test2@test.com", "password": "Test123!"},
    {"email": "test3@test.com", "password": "Test123!"},
    {"email": "test4@test.com", "password": "Test123!"},
]


def create_test_users():
    """創建測試帳號"""
    print("🚀 創建 E2E 測試帳號")
    print("=" * 60)
    print(f"Table: {TABLE_NAME}")
    print(f"Region: {REGION}")
    print(f"帳號數量: {len(TEST_USERS)}")
    print()

    # Initialize DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    success_count = 0
    skip_count = 0
    error_count = 0

    for i, user in enumerate(TEST_USERS, 1):
        email = user["email"]
        password = user["password"]

        print(f"📝 [{i}/{len(TEST_USERS)}] 創建: {email}")

        try:
            # 檢查是否已存在
            try:
                response = table.get_item(Key={"email": email})
                if "Item" in response:
                    print("   ⚠️  帳號已存在，跳過")
                    skip_count += 1
                    print()
                    continue
            except ClientError as e:
                if e.response["Error"]["Code"] != "ResourceNotFoundException":
                    raise

            # Hash password
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))

            # 創建用戶
            now = datetime.now(UTC).isoformat()

            table.put_item(
                Item={
                    "email": email,
                    "password_hash": password_hash.decode("utf-8"),
                    "enabled": True,
                    "role": "user",
                    "require_password_change": False,  # 已設定為永久密碼
                    "created_at": now,
                    "last_login": None,
                }
            )

            print("   ✅ 創建成功")
            print(f"   密碼: {password}")
            success_count += 1

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            print(f"   ❌ 創建失敗: {error_code}")
            print(f"      {e.response['Error']['Message']}")
            error_count += 1

        except Exception as e:
            print(f"   ❌ 創建失敗: {str(e)}")
            error_count += 1

        print()

    # 總結
    print("=" * 60)
    print("創建結果：")
    print(f"  ✅ 成功: {success_count}")
    print(f"  ⚠️  跳過: {skip_count}")
    print(f"  ❌ 失敗: {error_count}")
    print()

    if success_count + skip_count == len(TEST_USERS):
        print("🎉 所有測試帳號已準備好！")
        print()
        print("測試帳號列表：")
        for user in TEST_USERS:
            print(f"  - {user['email']} / {user['password']}")
        print()
        print("下一步：")
        print("  1. 執行驗證腳本：./verify-test-accounts.sh")
        print("  2. git push 觸發測試")
        return 0
    else:
        print("❌ 部分帳號創建失敗，請檢查錯誤")
        return 1


def verify_table_exists():
    """驗證 DynamoDB table 是否存在"""
    try:
        dynamodb = boto3.client("dynamodb", region_name=REGION)
        dynamodb.describe_table(TableName=TABLE_NAME)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"❌ Table 不存在: {TABLE_NAME}")
            print()
            print("可能的原因：")
            print(f"  1. Stack 名稱不正確（當前：{STACK_NAME}）")
            print("  2. Stack 尚未部署")
            print("  3. AWS CLI 憑證未配置")
            print()
            print("檢查方式：")
            print(f"  aws dynamodb list-tables --region {REGION}")
            return False
        raise


if __name__ == "__main__":
    try:
        # 檢查 bcrypt 是否安裝
        import bcrypt  # noqa: F401
    except ImportError:
        print("❌ bcrypt 未安裝")
        print()
        print("安裝方式：")
        print("  pip install bcrypt")
        sys.exit(1)

    # 檢查 table 是否存在
    print("🔍 檢查 DynamoDB table...")
    if not verify_table_exists():
        sys.exit(1)

    print(f"✅ Table 存在: {TABLE_NAME}")
    print()

    # 創建測試帳號
    exit_code = create_test_users()
    sys.exit(exit_code)
