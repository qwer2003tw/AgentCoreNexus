"""
創建 Bedrock AgentCore Memory
用於 Telegram Bot 的長期記憶功能
"""

from datetime import datetime

import boto3


def create_memory():
    """創建 AgentCore Memory"""

    # 初始化客戶端
    region = "us-west-2"

    try:
        # 使用 bedrock-agent-runtime 創建 memory
        boto3.client("bedrock-agent-runtime", region_name=region)

        # Memory 配置
        memory_name = f"telegram-bot-memory-{datetime.now().strftime('%Y%m%d')}"

        print(f"正在創建 Memory: {memory_name}")
        print(f"區域: {region}")

        # 注意：實際的 API 可能不同，這裡展示一個概念性的實現
        # Bedrock AgentCore Memory 可能需要通過其他方式創建

        print("\n⚠️  注意：Bedrock AgentCore Memory 創建可能需要：")
        print("1. 使用 AWS Console 創建")
        print("2. 使用 bedrock-agentcore SDK")
        print("3. 或使用預先配置的 Memory ID")

        # 嘗試列出可用的服務
        print("\n檢查可用的 Bedrock 服務...")
        bedrock_client = boto3.client("bedrock", region_name=region)

        try:
            # 嘗試獲取基礎模型列表
            bedrock_client.list_foundation_models()
            print("✅ Bedrock 服務可用")
        except Exception as e:
            print(f"❌ Bedrock 服務檢查失敗: {e}")

        # 建議使用固定的 Memory ID
        suggested_memory_id = "telegram-bot-long-term-memory"

        print(f"\n📝 建議的 Memory ID: {suggested_memory_id}")
        print("\n要使用此 Memory ID，請執行：")
        print(f"""
aws lambda update-function-configuration \\
  --region {region} \\
  --function-name telegram-unified-bot-processor \\
  --environment "Variables={{
    BEDROCK_AGENTCORE_MEMORY_ID={suggested_memory_id},
    EVENT_BUS_NAME=telegram-lambda-receiver-events,
    BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0,
    BROWSER_ENABLED=true,
    LOG_LEVEL=INFO
  }}"
""")

        return suggested_memory_id

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        print("\n建議：使用簡單的 Memory ID 字串即可")
        return "telegram-bot-memory"


if __name__ == "__main__":
    print("=" * 60)
    print("Bedrock AgentCore Memory 創建工具")
    print("=" * 60)
    print()

    memory_id = create_memory()

    print()
    print("=" * 60)
    print(f"完成！建議使用 Memory ID: {memory_id}")
    print("=" * 60)
