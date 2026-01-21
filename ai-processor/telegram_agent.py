"""
Telegram Agent with AgentCore
主入口點 - 僅負責 AgentCore 整合
"""

from datetime import datetime

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agents.conversation_agent import ConversationAgent

# 導入配置和工具
from config.settings import settings
from services.memory_service import memory_service
from tools import AVAILABLE_TOOLS
from utils.logger import get_logger

# 初始化日誌
logger = get_logger(__name__)

# 建立 AgentCore 應用
app = BedrockAgentCoreApp()

# 記錄啟動資訊
logger.info("=" * 50)
logger.info("🚀 Telegram Agent 啟動")
logger.info(f"🌍 區域: {settings.AWS_REGION}")
logger.info(f"🤖 模型: {settings.BEDROCK_MODEL_ID}")
logger.info(f"💾 Memory: {'已啟用' if settings.MEMORY_ENABLED else '未啟用'}")
logger.info(f"🔧 工具數量: {len(AVAILABLE_TOOLS)}")
logger.info("=" * 50)


@app.entrypoint
def invoke(payload, context):
    """
    AgentCore 入口點
    處理來自 Telegram 的訊息
    """
    try:
        # 提取用戶訊息
        user_message = payload.get("prompt", "").strip()

        # 取得 Session Manager (如果 Memory 已啟用)
        session_manager = memory_service.get_session_manager(context)

        # 建立對話 Agent
        conversation_agent = ConversationAgent(
            tools=AVAILABLE_TOOLS, session_manager=session_manager
        )

        # 處理訊息
        result = conversation_agent.process_message(user_message)

        # 回傳結果
        return {
            "response": result.get("response", "處理失敗"),
            "success": result.get("success", False),
            "memory_enabled": settings.MEMORY_ENABLED,
            "model": settings.BEDROCK_MODEL_ID,
            "region": settings.AWS_REGION,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ 入口點執行錯誤: {str(e)}", exc_info=True)
        return {
            "response": f"抱歉，處理您的請求時發生錯誤: {str(e)}",
            "error": True,
            "error_type": type(e).__name__,
            "model": settings.BEDROCK_MODEL_ID,
            "region": settings.AWS_REGION,
            "timestamp": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    app.run()
