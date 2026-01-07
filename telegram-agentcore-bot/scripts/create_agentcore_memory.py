"""
創建 Bedrock AgentCore Memory 資源
用於 Telegram Bot 的長期記憶功能
"""
import sys
import time
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import (
    SemanticStrategy,
    UserPreferenceStrategy,
    SummaryStrategy
)

def create_memory():
    """創建 AgentCore Memory 資源"""
    
    region = "us-west-2"
    
    print("=" * 80)
    print("🚀 創建 Bedrock AgentCore Memory 資源")
    print("=" * 80)
    print()
    
    try:
        # 初始化 Memory Manager
        print(f"📍 Region: {region}")
        print("⏳ 初始化 Memory Manager...")
        memory_manager = MemoryManager(region_name=region)
        print("✅ Memory Manager 初始化成功")
        print()
        
        # 配置 Memory Strategies
        print("📝 配置 Memory Strategies:")
        print("   1. UserPreferencesStrategy - 自動提取用戶偏好")
        print("   2. SemanticStrategy - 自動提取事實資訊")
        print("   3. SessionSummariesStrategy - 自動生成對話摘要")
        print()
        
        strategies = [
            UserPreferenceStrategy(
                name="userPreferences",
                namespaces=['/actors/{actorId}/preferences']
            ),
            SemanticStrategy(
                name="userFacts",
                namespaces=['/actors/{actorId}/facts']
            ),
            SummaryStrategy(
                name="sessionSummaries",
                namespaces=['/actors/{actorId}/sessions/{sessionId}']
            )
        ]
        
        # 創建 Memory
        print("⏳ 創建 Memory 資源...")
        print("   Name: TelegramBotMemory")
        print("   這可能需要 2-3 分鐘...")
        print()
        
        memory = memory_manager.get_or_create_memory(
            name="TelegramBotMemory",
            description="Telegram Bot with short-term sessions and long-term user memory",
            strategies=strategies
        )
        
        print("✅ Memory 創建成功！")
        print()
        print("=" * 80)
        print("📊 Memory 資訊")
        print("=" * 80)
        print(f"Memory ID: {memory.get('id')}")
        print(f"Memory Name: {memory.get('name')}")
        print(f"Status: {memory.get('status')}")
        print(f"Region: {region}")
        print()
        
        # 等待 Memory 變為 ACTIVE
        if memory.get('status') != 'ACTIVE':
            print("⏳ 等待 Memory 狀態變為 ACTIVE...")
            max_wait = 180  # 最多等待 3 分鐘
            waited = 0
            
            while waited < max_wait:
                time.sleep(10)
                waited += 10
                
                # 檢查狀態
                memories = memory_manager.list_memories()
                current_memory = next(
                    (m for m in memories if m.get('id') == memory.get('id')),
                    None
                )
                
                if current_memory and current_memory.get('status') == 'ACTIVE':
                    print("✅ Memory 狀態：ACTIVE")
                    break
                
                print(f"   等待中... ({waited}秒)")
            
            if waited >= max_wait:
                print("⚠️  Memory 仍未變為 ACTIVE，但可以繼續使用")
        
        print()
        print("=" * 80)
        print("📝 下一步操作")
        print("=" * 80)
        print()
        print("1. 複製上面的 Memory ID")
        print()
        print("2. 更新 Lambda 環境變數：")
        print()
        print(f"aws lambda update-function-configuration \\")
        print(f"  --region {region} \\")
        print(f"  --function-name telegram-unified-bot-processor \\")
        print(f"  --environment \"Variables={{")
        print(f"    BEDROCK_AGENTCORE_MEMORY_ID={memory.get('id')},")
        print(f"    EVENT_BUS_NAME=telegram-lambda-receiver-events,")
        print(f"    BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0,")
        print(f"    BROWSER_ENABLED=true,")
        print(f"    LOG_LEVEL=INFO")
        print(f"  }}\"")
        print()
        print("3. 等待 Lambda 更新完成：")
        print()
        print(f"aws lambda wait function-updated \\")
        print(f"  --region {region} \\")
        print(f"  --function-name telegram-unified-bot-processor")
        print()
        print("=" * 80)
        print("✅ 完成！")
        print("=" * 80)
        
        return memory.get('id')
        
    except ImportError as e:
        print()
        print("❌ 錯誤：bedrock-agentcore-starter-toolkit 未安裝")
        print()
        print("請先安裝：")
        print("pip install bedrock-agentcore-starter-toolkit")
        print()
        sys.exit(1)
        
    except Exception as e:
        print()
        print(f"❌ 錯誤：{str(e)}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    memory_id = create_memory()
    
    # 儲存 Memory ID 到文件
    with open('MEMORY_ID.txt', 'w') as f:
        f.write(memory_id)
    
    print()
    print(f"💾 Memory ID 已儲存到：MEMORY_ID.txt")
