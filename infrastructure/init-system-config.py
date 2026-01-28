#!/usr/bin/env python3
"""
初始化系統配置
設置審計日誌保留期限的默認值
"""

import time

import boto3

# 配置
REGION = "us-west-2"
TABLE_NAME = "agentcore-admin-system-config-dev"

# 默認配置
DEFAULT_CONFIGS = [
    {
        "config_key": "audit_log_retention_critical",
        "config_value": 365,
        "description": "審計日誌保留期限（critical 敏感度） - 1 年",
    },
    {
        "config_key": "audit_log_retention_high",
        "config_value": 180,
        "description": "審計日誌保留期限（high 敏感度） - 6 個月",
    },
    {
        "config_key": "audit_log_retention_medium",
        "config_value": 90,
        "description": "審計日誌保留期限（medium 敏感度） - 3 個月",
    },
    {
        "config_key": "audit_log_retention_low",
        "config_value": 30,
        "description": "審計日誌保留期限（low 敏感度） - 1 個月",
    },
]


def init_config():
    """初始化系統配置"""
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    print(f"📋 Initializing system config in {TABLE_NAME}")
    print()

    for config in DEFAULT_CONFIGS:
        config["updated_at"] = int(time.time())
        config["updated_by"] = "system-init"

        print(f"   Setting {config['config_key']}: {config['config_value']} days")

        try:
            table.put_item(Item=config)
            print(f"   ✅ {config['config_key']}")
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")

    print()
    print("🎉 System config initialized!")
    print()
    print("Default retention policies:")
    print("  - Critical: 365 days (delete_user, unauthorized_access, etc.)")
    print("  - High: 180 days (password_reset, role_change, exports, etc.)")
    print("  - Medium: 90 days (view_conversation, generate_summary, etc.)")
    print("  - Low: 30 days (view_dashboard, view_stats, etc.)")


if __name__ == "__main__":
    init_config()
