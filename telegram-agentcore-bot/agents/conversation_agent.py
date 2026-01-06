"""
對話 Agent 實作
封裝 Agent 的建立和執行邏輯
"""
from typing import Any, Dict, List
from strands import Agent
from strands.models import BedrockModel
from utils.logger import get_logger
from config.settings import settings
from config.prompts import SYSTEM_PROMPT

logger = get_logger(__name__)

class ConversationAgent:
    """對話 Agent 類"""
    
    def __init__(self, tools: List[Any], session_manager: Any = None):
        """
        初始化對話 Agent
        
        Args:
            tools: 工具列表
            session_manager: Session Manager (可選)
        """
        self.tools = tools
        self.session_manager = session_manager
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """
        建立 Agent 實例
        
        Returns:
            Agent 實例
        """
        try:
            # 建立 Bedrock 模型
            model = BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
                region_name=settings.AWS_REGION
            )
            
            # 建立 Agent
            agent = Agent(
                model=model,
                session_manager=self.session_manager,
                system_prompt=SYSTEM_PROMPT,
                tools=self.tools
            )
            
            logger.info(f"✅ Agent 建立成功 (模型: {settings.BEDROCK_MODEL_ID})")
            return agent
            
        except Exception as e:
            logger.error(f"❌ Agent 建立失敗: {str(e)}", exc_info=True)
            raise
    
    def process_message(self, message: str) -> Dict[str, Any]:
        """
        處理用戶訊息
        
        Args:
            message: 用戶訊息
        
        Returns:
            處理結果字典
        """
        try:
            # 驗證訊息
            message = message.strip() if message else "你好，我需要協助"
            
            logger.info(f"📥 處理訊息: {message[:50]}...")
            
            # 執行 Agent
            result = self.agent(message)
            
            # 提取回應文字
            response_text = self._extract_response(result)
            
            logger.info(f"📤 回應長度: {len(response_text)} 字元")
            
            return {
                "success": True,
                "response": response_text
            }
            
        except Exception as e:
            logger.error(f"❌ 訊息處理錯誤: {str(e)}", exc_info=True)
            return {
                "success": False,
                "response": f"處理訊息時發生錯誤: {str(e)}",
                "error": str(e)
            }
    
    def _extract_response(self, result: Any) -> str:
        """
        從 Agent 結果提取回應文字
        
        Args:
            result: Agent 執行結果
        
        Returns:
            回應文字
        """
        response_text = ""
        
        try:
            # 方法1: 檢查 result.message
            if hasattr(result, 'message') and result.message:
                response_text = self._extract_from_message(result.message)
            
            # 方法2: 檢查 result.content
            if not response_text and hasattr(result, 'content'):
                response_text = self._extract_from_content(result.content)
            
            # 方法3: 嘗試字串化
            if not response_text:
                result_str = str(result)
                if result_str and result_str not in ['', 'None', '{}', '[]']:
                    response_text = result_str
            
            # 清理和驗證
            response_text = response_text.strip() if response_text else ""
            
            # 過濾無意義的回應
            if response_text in ['{}', '[]', 'None', '{"role": "assistant", "content": []}']:
                response_text = ""
            
            # 最終檢查
            if not response_text:
                logger.warning("⚠️ 回應內容為空")
                response_text = "處理完成，但回應內容為空。請嘗試重新描述您的需求。"
            
            return response_text
            
        except Exception as e:
            logger.error(f"❌ 回應提取異常: {str(e)}", exc_info=True)
            return f"回應提取時發生問題: {str(e)}"
    
    def _extract_from_message(self, message: Any) -> str:
        """從 message 提取文字"""
        if isinstance(message, dict):
            # 檢查 content 陣列
            content = message.get('content', [])
            if content and isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        return item['text']
            
            # 檢查 text 鍵
            if 'text' in message:
                return message['text']
            
            # 檢查 role/content 格式
            if message.get('role') == 'assistant':
                msg_content = message.get('content', [])
                if msg_content and isinstance(msg_content, list):
                    for item in msg_content:
                        if isinstance(item, dict) and 'text' in item:
                            return item['text']
        
        return str(message) if message else ""
    
    def _extract_from_content(self, content: Any) -> str:
        """從 content 提取文字"""
        if isinstance(content, list) and content:
            first_item = content[0]
            if isinstance(first_item, dict):
                return first_item.get('text', str(content))
            return str(first_item)
        return str(content) if content else ""
