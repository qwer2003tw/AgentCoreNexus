#!/usr/bin/env python3
"""
創建 Web 測試帳號腳本
"""

from datetime import datetime

import bcrypt
import boto3

# 配置
TABLE_NAME = "agentcore-web-adapter-web-users"
REGION = "us-west-2"

# 測試帳號列表
TEST_USERS = [
    {"email": "test1@test.com", "password": "Test123!"},
    {"email": "test2@test.com", "password": "Test123!"},
    {"email": "test3@test.com", "password": "Test123!"},
    {"email": "test4@test.com", "password": "Test123!"},
    {"email": "test5@test.com", "password": "Test123!"},
]


def hash_password(password: str) -> str:
    """使用 bcrypt 加密密碼"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_test_users():
    """創建測試帳號"""
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    print(f"🔧 開始創建測試帳號到表: {TABLE_NAME}")
    print("")

    for user in TEST_USERS:
        email = user["email"]
        password = user["password"]

        # 加密密碼
        hashed_password = hash_password(password)

        # 創建帳號
        item = {
            "email": email,
            "password_hash": hashed_password,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        try:
            table.put_item(Item=item)
            print(f"✅ 已創建: {email}")
        except Exception as e:
            print(f"❌ 創建失敗 {email}: {str(e)}")

    print("")
    print("🎉 測試帳號創建完成！")
    print("")
    print("📋 測試帳號列表：")
    print("-" * 50)
    for user in TEST_USERS:
        print(f"Email: {user['email']}")
        print(f"Password: {user['password']}")
        print("-" * 50)


if __name__ == "__main__":
    create_test_users()
